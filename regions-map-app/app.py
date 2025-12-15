"""
وب‌اپ ساده برای آپلود فایل شیپ (Shapefile) و نمایش محدوده‌ها بر روی نقشه ایران.
با پنل ادمین و سیستم تاریخچه آپلودها.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from werkzeug.security import check_password_hash, generate_password_hash
import hashlib

try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError as exc:  # pragma: no cover - fails fast on missing deps
    raise RuntimeError("لطفاً بسته GeoPandas را نصب کنید (pip install geopandas).") from exc
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR / "uploads" / "regions"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
STORAGE_DIR = BASE_DIR / "uploads" / "regions" / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = BASE_DIR / "uploads" / "regions" / "history.json"
LINKS_DIR = BASE_DIR / "uploads" / "regions" / "links"
LINKS_DIR.mkdir(parents=True, exist_ok=True)
LOGO_DIR = BASE_DIR / "uploads" / "regions" / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)
NEIGHBORHOOD_EDITS_DIR = BASE_DIR / "uploads" / "regions" / "neighborhood_edits"
NEIGHBORHOOD_EDITS_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DIR = BASE_DIR / "uploads" / "regions" / "features"
FEATURES_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_INDEX_FILE = BASE_DIR / "uploads" / "regions" / "features_index.json"
USERS_FILE = BASE_DIR / "uploads" / "regions" / "users.json"

ALLOWED_EXTENSIONS = {"zip", "geojson", "json"}
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}
TOOTAPP_BASE_URL = "https://tootapp.ir/join/"

# نقش‌های کاربری
ROLES = {
    "admin": "مدیر کل",
    "editor": "ویرایشگر",
    "viewer": "مشاهده‌کننده"
}

# سطح دسترسی
PERMISSIONS = {
    "admin": ["upload", "delete", "manage_links", "manage_users", "view"],
    "editor": ["upload", "manage_links", "view"],
    "viewer": ["view"]
}

# ساختار نمونه: کلیدها بر اساس (استان/شهر، منطقه، محله) هستند.
TOOTAPP_GROUPS = {
    ("تهران", "3", "داوودیه"): "Tehran3Da",
}

FALLBACK_REGION_NEIGHBOR_SLUGS = {
    ("3", "Davoudiyeh"): "Tehran3Da",
    ("3", "Davoudiyeh".lower()): "Tehran3Da",
}

FALLBACK_NEIGHBORHOOD_SLUGS = {
    "داوودیه": "Tehran3Da",
}

CITY_FIELDS = ["city", "City", "CITY", "ostan", "Ostan", "OSTAN"]
DISTRICT_FIELDS = ["district", "District", "DISTRICT", "mantaghe", "region", "REGION"]
NEIGHBORHOOD_FIELDS = [
    "name",
    "Name",
    "NAME",
    "mahale",
    "Mahale",
    "MAHALE",
    "neighbourhood",
    "neighborhood",
]
SLUG_FIELDS = ["toot_slug", "TootSlug", "TOOT_SLUG"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")


def is_allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _clean_geojson_for_json(geojson: Dict) -> Dict:
    """پاکسازی GeoJSON از انواع غیرقابل JSON serialization (مثل Timestamp)"""
    try:
        import pandas as pd
    except ImportError:
        pd = None
    
    from datetime import datetime, date
    
    if not isinstance(geojson, dict):
        return geojson
    
    # کپی کردن برای عدم تغییر داده اصلی
    try:
        cleaned = json.loads(json.dumps(geojson, default=str))
    except (TypeError, ValueError) as e:
        # اگر هنوز مشکل داشت، دستی پاکسازی کن
        try:
            cleaned = json.loads(json.dumps(geojson, default=lambda x: str(x) if hasattr(x, '__str__') else None))
        except Exception:
            # اگر باز هم خطا داد، GeoJSON اصلی را برگردان
            return geojson
    
    # اگر cleaned یک string است (به خاطر default=str)، دوباره parse کن
    if isinstance(cleaned, str):
        try:
            cleaned = json.loads(cleaned)
        except json.JSONDecodeError:
            return geojson
    
    # پاکسازی عمیق‌تر در features
    if "features" in cleaned and isinstance(cleaned["features"], list):
        for feature in cleaned["features"]:
            if isinstance(feature, dict) and "properties" in feature:
                props = feature["properties"]
                if not isinstance(props, dict):
                    continue
                for key, value in list(props.items()):
                    try:
                        # تبدیل Timestamp و datetime به string
                        if pd and isinstance(value, pd.Timestamp):
                            props[key] = str(value)
                        elif isinstance(value, (datetime, date)):
                            props[key] = str(value)
                        # تبدیل numpy types به Python native types
                        elif hasattr(value, 'item'):  # numpy types
                            try:
                                props[key] = value.item()
                            except (ValueError, AttributeError):
                                props[key] = str(value)
                        # تبدیل float64, int64 و غیره
                        elif pd and isinstance(value, (pd.Series, pd.DataFrame)):
                            props[key] = str(value)
                        # تبدیل numpy.datetime64
                        elif hasattr(value, 'dtype') and 'datetime' in str(value.dtype):
                            props[key] = str(value)
                    except Exception:
                        # اگر خطایی رخ داد، مقدار را به string تبدیل کن
                        try:
                            props[key] = str(value)
                        except Exception:
                            # اگر باز هم خطا داد، فیلد را حذف کن
                            props.pop(key, None)
    
    return cleaned


def _load_geojson_from_geojson(file_obj: FileStorage) -> Dict:
    payload = file_obj.read()
    if not payload:
        raise ValueError("فایل خالی است.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("فایل JSON معتبر نیست.") from exc
    
    # بررسی اینکه آیا این OSM JSON است (از Overpass Turbo)
    if isinstance(data, dict) and "elements" in data:
        # تبدیل OSM JSON به GeoJSON
        return _convert_osm_to_geojson(data)
    elif isinstance(data, dict) and "type" in data:
        # این یک GeoJSON استاندارد است
        return data
    else:
        raise ValueError("فرمت فایل پشتیبانی نمی‌شود. لطفاً از GeoJSON یا خروجی Overpass Turbo استفاده کنید.")


def _convert_osm_to_geojson(osm_data: Dict) -> Dict:
    """تبدیل OSM JSON (از Overpass Turbo) به GeoJSON"""
    from shapely.geometry import Point
    
    elements = osm_data.get("elements", [])
    if not elements:
        raise ValueError("فایل OSM خالی است.")
    
    # ایجاد دیکشنری برای ذخیره node ها
    nodes = {}
    ways = []
    relations = []
    
    # جدا کردن node ها، way ها و relation ها
    for element in elements:
        elem_type = element.get("type")
        if elem_type == "node":
            nodes[element.get("id")] = {
                "lat": element.get("lat"),
                "lon": element.get("lon"),
                "tags": element.get("tags", {})
            }
        elif elem_type == "way":
            ways.append(element)
        elif elem_type == "relation":
            relations.append(element)
    
    features = []
    
    # تبدیل node ها به Point features
    for node_id, node_data in nodes.items():
        if node_data["lat"] is not None and node_data["lon"] is not None:
            point = Point(node_data["lon"], node_data["lat"])
            feature = {
                "type": "Feature",
                "geometry": json.loads(json.dumps(point.__geo_interface__)),
                "properties": node_data["tags"].copy() if node_data["tags"] else {}
            }
            feature["properties"]["osm_id"] = node_id
            feature["properties"]["osm_type"] = "node"
            features.append(feature)
    
    # تبدیل way ها به LineString یا Polygon features
    for way in ways:
        way_nodes = way.get("nodes", [])
        if not way_nodes:
            continue
        
        # جمع‌آوری مختصات
        coordinates = []
        for node_id in way_nodes:
            if node_id in nodes:
                node = nodes[node_id]
                if node["lat"] is not None and node["lon"] is not None:
                    coordinates.append([node["lon"], node["lat"]])
        
        if len(coordinates) < 2:
            continue
        
        tags = way.get("tags", {})
        
        # بررسی اینکه آیا way یک polygon است (closed way با tag area یا building)
        is_closed = coordinates[0] == coordinates[-1]
        is_area = tags.get("area") == "yes" or any(key in tags for key in ["building", "landuse", "leisure", "amenity"])
        
        if is_closed and (is_area or len(coordinates) >= 4):
            # تبدیل به Polygon
            geometry = {
                "type": "Polygon",
                "coordinates": [coordinates]
            }
        else:
            # تبدیل به LineString
            geometry = {
                "type": "LineString",
                "coordinates": coordinates
            }
        
        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": tags.copy()
        }
        feature["properties"]["osm_id"] = way.get("id")
        feature["properties"]["osm_type"] = "way"
        features.append(feature)
    
    # تبدیل relation ها (پیچیده‌تر - فعلاً skip می‌کنیم)
    # برای relation ها نیاز به پردازش پیچیده‌تری است
    
    if not features:
        raise ValueError("هیچ عارضه‌ای در فایل OSM یافت نشد.")
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def _load_geojson_from_shapefile(file_obj: FileStorage) -> Dict:
    work_dir = Path(tempfile.mkdtemp(prefix="regions_", dir=UPLOAD_ROOT))
    archive_path = work_dir / secure_filename(file_obj.filename)
    file_obj.save(archive_path)

    try:
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(work_dir)
    except zipfile.BadZipFile as exc:
        raise ValueError("امکان باز کردن فایل Zip وجود ندارد.") from exc

    shapefiles = list(work_dir.rglob("*.shp"))
    if not shapefiles:
        raise ValueError("هیچ فایل .shp در آرشیو پیدا نشد.")

    try:
        gdf = gpd.read_file(shapefiles[0])
    except Exception as exc:  # noqa: BLE001
        raise ValueError("امکان خواندن فایل Shapefile وجود ندارد.") from exc

    if gdf.empty:
        raise ValueError("لایه بارگذاری شده فاقد عارضه است.")

    if gdf.crs:
        gdf = gdf.to_crs(epsg=4326)
    else:
        gdf = gdf.set_crs(epsg=4326, allow_override=True)

    # تبدیل به GeoJSON - ابتدا فیلدهای غیرقابل JSON serialization را تبدیل کن
    # تبدیل تمام ستون‌های datetime/timestamp به string
    for col in gdf.columns:
        if col != 'geometry':
            if gdf[col].dtype.name.startswith('datetime') or 'date' in gdf[col].dtype.name.lower():
                gdf[col] = gdf[col].astype(str)
            # تبدیل numpy types به Python native types
            elif gdf[col].dtype.name in ['int64', 'float64']:
                gdf[col] = gdf[col].astype('int64' if 'int' in gdf[col].dtype.name else 'float64')
    
    # حالا به GeoJSON تبدیل کن
    geojson_str = gdf.to_json()
    geojson = json.loads(geojson_str)
    
    # پاکسازی بیشتر برای اطمینان
    geojson = _clean_geojson_for_json(geojson)

    shutil.rmtree(work_dir, ignore_errors=True)
    return geojson


def load_geojson(file_obj: FileStorage, attach_links: bool = True) -> Tuple[Dict, Dict]:
    if not file_obj or not file_obj.filename:
        raise ValueError("لطفاً یک فایل انتخاب کنید.")

    if not is_allowed(file_obj.filename):
        raise ValueError("فقط فایل‌های Zip (حاوی Shapefile) یا GeoJSON پذیرفته می‌شوند.")

    extension = file_obj.filename.rsplit(".", 1)[1].lower()

    if extension == "geojson":
        geojson = _load_geojson_from_geojson(file_obj)
        gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")
    else:
        geojson = _load_geojson_from_shapefile(file_obj)
        gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")

    if attach_links:
        _attach_tootapp_links(geojson)

    summary = {
        "feature_count": len(gdf),
        "crs": gdf.crs.to_string() if gdf.crs else "نامشخص",
        "columns": [col for col in gdf.columns if col.lower() != "geometry"],
    }
    return geojson, summary


def _first_nonempty(properties: Dict, keys) -> Optional[str]:
    for key in keys:
        value = properties.get(key)
        if value not in (None, "", " "):
            return str(value).strip()
    return None


def _resolve_group_slug(properties: Dict) -> Optional[str]:
    slug_value = _first_nonempty(properties, SLUG_FIELDS)
    if slug_value:
        return slug_value

    city = _first_nonempty(properties, CITY_FIELDS)
    district = _first_nonempty(properties, DISTRICT_FIELDS)
    neighborhood = _first_nonempty(properties, NEIGHBORHOOD_FIELDS)

    if not neighborhood:
        return None

    key = (city or "", district or "", neighborhood)
    slug = TOOTAPP_GROUPS.get(key)
    if slug:
        return slug

    slug = FALLBACK_NEIGHBORHOOD_SLUGS.get(neighborhood)
    if slug:
        return slug

    e_region = properties.get("Region") or properties.get("region")
    e_name = properties.get("EName") or properties.get("ename")
    key_en = (str(e_region).strip() if e_region else "", str(e_name).strip() if e_name else "")
    return FALLBACK_REGION_NEIGHBOR_SLUGS.get(key_en)


def _attach_tootapp_links(geojson: Dict, map_id: Optional[str] = None) -> None:
    """اتصال لینک‌های توت‌اپ به features"""
    # بارگذاری لینک‌های ذخیره شده اگر map_id موجود باشد
    saved_links = {}
    if map_id:
        saved_links = load_links(map_id)
    
    for feature in geojson.get("features", []):
        props = feature.setdefault("properties", {})
        
        # اول بررسی می‌کنیم که آیا لینک ذخیره شده‌ای وجود دارد
        feature_id = get_feature_identifier(feature)
        if feature_id and feature_id in saved_links:
            saved_link = saved_links[feature_id]
            # اگر لینک کامل نبود، base URL را اضافه می‌کنیم
            if saved_link.startswith("http"):
                props["tootapp_url"] = saved_link
            else:
                props["tootapp_url"] = f"{TOOTAPP_BASE_URL.rstrip('/')}/{saved_link.lstrip('/')}"
        else:
            # اگر لینک ذخیره شده نبود، فقط base URL را استفاده می‌کنیم
            props["tootapp_url"] = TOOTAPP_BASE_URL.rstrip('/')


def load_history() -> List[Dict]:
    """بارگذاری تاریخچه آپلودها از فایل JSON"""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history: List[Dict]) -> None:
    """ذخیره تاریخچه آپلودها در فایل JSON"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_map_data(map_id: str, geojson: Dict, summary: Dict, original_filename: str) -> None:
    """ذخیره داده‌های نقشه در فایل JSON"""
    map_file = STORAGE_DIR / f"{map_id}.json"
    
    # پاکسازی GeoJSON از انواع غیرقابل JSON serialization
    cleaned_geojson = _clean_geojson_for_json(geojson)
    
    data = {
        "geojson": cleaned_geojson,
        "summary": summary,
        "original_filename": original_filename,
        "map_id": map_id,
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def load_map_data(map_id: str) -> Optional[Dict]:
    """بارگذاری داده‌های نقشه از فایل JSON"""
    map_file = STORAGE_DIR / f"{map_id}.json"
    if not map_file.exists():
        return None
    try:
        with open(map_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def find_duplicate_map(map_name: str, filename: str) -> Optional[str]:
    """پیدا کردن نقشه قبلی با همان نام"""
    history = load_history()
    search_name = (map_name or filename).lower().strip()
    
    for item in history:
        item_name = (item.get("map_name") or item.get("original_filename", "")).lower().strip()
        if item_name == search_name:
            return item.get("map_id")
    return None


def transfer_links(old_map_id: str, new_map_id: str) -> None:
    """انتقال لینک‌ها از نقشه قدیمی به نقشه جدید"""
    old_links = load_links(old_map_id)
    if old_links:
        save_links(new_map_id, old_links)


def delete_map(map_id: str, keep_links: bool = False) -> bool:
    """حذف نقشه از تاریخچه و فایل ذخیره شده"""
    try:
        # حذف فایل JSON
        map_file = STORAGE_DIR / f"{map_id}.json"
        if map_file.exists():
            map_file.unlink()

        # حذف فایل لینک‌ها فقط اگر keep_links False باشد
        if not keep_links:
            links_file = LINKS_DIR / f"{map_id}.json"
            if links_file.exists():
                links_file.unlink()

        # حذف از تاریخچه
        history = load_history()
        history = [item for item in history if item.get("map_id") != map_id]
        save_history(history)

        return True
    except Exception:
        return False


def load_links(map_id: str) -> Dict[str, str]:
    """بارگذاری لینک‌های توت‌اپ برای یک نقشه"""
    links_file = LINKS_DIR / f"{map_id}.json"
    if not links_file.exists():
        return {}
    try:
        with open(links_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_links(map_id: str, links: Dict[str, str]) -> None:
    """ذخیره لینک‌های توت‌اپ برای یک نقشه"""
    links_file = LINKS_DIR / f"{map_id}.json"
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def get_neighborhood_key(map_id: str, neighborhood_name: str) -> str:
    """ساخت کلید منحصر به فرد برای محله"""
    key_string = f"{map_id}_{neighborhood_name}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def get_neighborhood_logo_path(map_id: str, neighborhood_name: str) -> Path:
    """مسیر فایل JSON لوگوی محله"""
    key = get_neighborhood_key(map_id, neighborhood_name)
    return LOGO_DIR / f"{key}.json"


def load_neighborhood_logo(map_id: str, neighborhood_name: str) -> Optional[str]:
    """بارگذاری نام فایل لوگوی محله - با جستجوی case-insensitive و partial match"""
    if not neighborhood_name or not neighborhood_name.strip():
        return None
    
    neighborhood_name_clean = neighborhood_name.strip()
    neighborhood_name_normalized = neighborhood_name_clean.lower()
    
    # ابتدا جستجوی exact match
    logo_file = get_neighborhood_logo_path(map_id, neighborhood_name_clean)
    if logo_file.exists():
        try:
            with open(logo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logo_filename = data.get("logo_filename")
                if logo_filename:
                    return logo_filename
        except Exception:
            pass
    
    # اگر پیدا نشد، جستجوی case-insensitive در تمام فایل‌های JSON
    if not LOGO_DIR.exists():
        return None
    
    # جستجوی exact match (case-insensitive)
    for logo_file in LOGO_DIR.glob("*.json"):
        try:
            with open(logo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("map_id") == map_id:
                    saved_name = data.get("neighborhood_name", "").strip()
                    saved_name_normalized = saved_name.lower()
                    if saved_name_normalized == neighborhood_name_normalized:
                        logo_filename = data.get("logo_filename")
                        if logo_filename:
                            return logo_filename
        except Exception:
            continue
    
    # اگر هنوز پیدا نشد، جستجوی partial match (نام درخواستی بخشی از نام ذخیره شده یا برعکس)
    for logo_file in LOGO_DIR.glob("*.json"):
        try:
            with open(logo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("map_id") == map_id:
                    saved_name = data.get("neighborhood_name", "").strip()
                    saved_name_normalized = saved_name.lower()
                    # بررسی partial match
                    if (neighborhood_name_normalized in saved_name_normalized or 
                        saved_name_normalized in neighborhood_name_normalized):
                        logo_filename = data.get("logo_filename")
                        if logo_filename:
                            return logo_filename
        except Exception:
            continue
    
    return None


def save_neighborhood_logo(map_id: str, neighborhood_name: str, logo_filename: str) -> None:
    """ذخیره نام فایل لوگوی محله"""
    logo_file = get_neighborhood_logo_path(map_id, neighborhood_name)
    data = {
        "map_id": map_id,
        "neighborhood_name": neighborhood_name,
        "logo_filename": logo_filename
    }
    with open(logo_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_neighborhood_logos(map_id: str) -> Dict[str, str]:
    """دریافت تمام لوگوهای محلات یک نقشه"""
    logos = {}
    if not LOGO_DIR.exists():
        return logos
    
    for logo_file in LOGO_DIR.glob("*.json"):
        try:
            with open(logo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("map_id") == map_id:
                    neighborhood_name = data.get("neighborhood_name", "")
                    logos[neighborhood_name] = data.get("logo_filename", "")
        except Exception:
            continue
    
    return logos


def get_neighborhood_edits_file(map_id: str) -> Path:
    """مسیر فایل ویرایش‌های محلات یک نقشه"""
    return NEIGHBORHOOD_EDITS_DIR / f"{map_id}.json"


def load_neighborhood_edits(map_id: str) -> Dict[str, Dict]:
    """بارگذاری ویرایش‌های محلات یک نقشه"""
    edits_file = get_neighborhood_edits_file(map_id)
    if not edits_file.exists():
        return {}
    try:
        with open(edits_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_neighborhood_edits(map_id: str, edits: Dict[str, Dict]) -> None:
    """ذخیره ویرایش‌های محلات یک نقشه"""
    edits_file = get_neighborhood_edits_file(map_id)
    with open(edits_file, "w", encoding="utf-8") as f:
        json.dump(edits, f, ensure_ascii=False, indent=2)


def get_neighborhood_edit_key(feature_id: str, original_name: str) -> str:
    """ساخت کلید منحصر به فرد برای ویرایش یک محله
    توجه: برای جلوگیری از مغایرت نام (بعد از ویرایش نام)، فقط feature_id را مبنا قرار می‌دهیم.
    """
    key_string = f"{feature_id}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()


def apply_neighborhood_edits(props: Dict, map_id: str, feature_id: str, original_name: str) -> Dict:
    """اعمال ویرایش‌های محله به properties"""
    if not feature_id:
        return props
    
    edits = load_neighborhood_edits(map_id)
    if not edits:
        return props
    
    # جستجو در تمام ویرایش‌ها برای پیدا کردن ویرایش مربوط به این feature_id
    edit_data = None
    for key, edit_item in edits.items():
        if isinstance(edit_item, dict):
            # مقایسه feature_id (می‌تواند string یا number باشد)
            item_feature_id = str(edit_item.get("feature_id", "")).strip()
            current_feature_id = str(feature_id).strip()
            if item_feature_id and current_feature_id and item_feature_id == current_feature_id:
                edit_data = edit_item.get("edits", {})
                break
    
    # اگر ویرایش پیدا نشد، از کلید مستقیم استفاده کن
    if edit_data is None:
        edit_key = get_neighborhood_edit_key(feature_id, original_name)
        if edit_key in edits:
            edit_data_root = edits[edit_key]
            edit_data = edit_data_root.get("edits", edit_data_root) if isinstance(edit_data_root, dict) else {}
    
    if edit_data:
        # اعمال تغییرات - اضافه کردن به properties (فقط اگر مقدار وجود داشته باشد)
        if "name" in edit_data and edit_data["name"]:
            props["NAME_NEW"] = str(edit_data["name"]).strip()  # استفاده از NAME_NEW برای اولویت
        if "population" in edit_data and edit_data["population"]:
            props["population"] = str(edit_data["population"]).strip()
        if "area" in edit_data and edit_data["area"]:
            props["area"] = str(edit_data["area"]).strip()
        if "district" in edit_data and edit_data["district"]:
            props["district"] = str(edit_data["district"]).strip()
        if "city" in edit_data and edit_data["city"]:
            props["city"] = str(edit_data["city"]).strip()
        if "english_name" in edit_data and edit_data["english_name"]:
            props["english_name"] = str(edit_data["english_name"]).strip()
    
    return props


def load_features_index() -> List[Dict]:
    """بارگذاری فهرست عوارض محله‌ها"""
    if not FEATURES_INDEX_FILE.exists():
        return []
    try:
        with open(FEATURES_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_features_index(index: List[Dict]) -> None:
    """ذخیره فهرست عوارض محله‌ها"""
    with open(FEATURES_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_feature_data(feature_id: str) -> Optional[Dict]:
    """بارگذاری داده‌های یک عارضه"""
    feature_file = FEATURES_DIR / f"{feature_id}.json"
    if not feature_file.exists():
        return None
    try:
        with open(feature_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_feature_data(feature_id: str, geojson: Dict, summary: Dict, original_filename: str, map_id: str, feature_name: str) -> None:
    """ذخیره داده‌های یک عارضه"""
    feature_file = FEATURES_DIR / f"{feature_id}.json"
    
    # پاکسازی GeoJSON از انواع غیرقابل JSON serialization
    cleaned_geojson = _clean_geojson_for_json(geojson)
    
    data = {
        "geojson": cleaned_geojson,
        "summary": summary,
        "original_filename": original_filename,
        "feature_id": feature_id,
        "map_id": map_id,
        "feature_name": feature_name,
        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(feature_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def get_feature_identifier(feature: Dict) -> Optional[str]:
    """ایجاد شناسه منحصر به فرد برای یک feature
    اولویت با فیلدهای ID ثابت، سپس geometry hash برای ثبات
    """
    props = feature.get("properties", {})
    
    # اولویت اول: فیلدهای ID ثابت که تغییر نمی‌کنند
    for id_field in ['feature_id', 'id', 'ID', 'gid', 'GID', 'OBJECTID', 'objectid']:
        if id_field in props:
            value = props[id_field]
            if value is not None and str(value).strip():
                return str(value).strip()
    
    # اولویت دوم: ساخت hash از geometry (ثابت است و تغییر نمی‌کند)
    geometry = feature.get("geometry")
    if geometry:
        import json
        geometry_str = json.dumps(geometry, sort_keys=True)
        return hashlib.md5(geometry_str.encode('utf-8')).hexdigest()
    
    # اولویت سوم: ترکیب فیلدهای مختلف (در صورت نبود geometry)
    keywords = ['name', 'mahalle', 'district', 'region']
    parts = []
    for key in props:
        key_lower = key.lower()
        if any(kw in key_lower for kw in keywords):
            value = props[key]
            if value and str(value).strip():
                parts.append(f"{key}:{value}")
    if parts:
        return "|".join(parts)
    
    return None


def load_users() -> List[Dict]:
    """بارگذاری لیست کاربران از فایل JSON"""
    if not USERS_FILE.exists():
        # ایجاد کاربر پیش‌فرض admin
        default_admin = {
            "username": "admin",
            "password_hash": generate_password_hash("admin123", method="pbkdf2:sha256"),
            "role": "admin",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login": None
        }
        users = [default_admin]
        save_users(users)
        return users
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_users(users: List[Dict]) -> None:
    """ذخیره لیست کاربران در فایل JSON"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_user(username: str) -> Optional[Dict]:
    """دریافت اطلاعات یک کاربر"""
    users = load_users()
    return next((u for u in users if u.get("username") == username), None)


def verify_password(username: str, password: str) -> bool:
    """بررسی صحت رمز عبور کاربر"""
    user = get_user(username)
    if not user:
        return False
    
    password_hash = user.get("password_hash")
    if not password_hash:
        return False
    
    try:
        return check_password_hash(password_hash, password)
    except Exception:
        # Fallback برای hash قدیمی
        return False


def create_user(username: str, password: str, role: str = "viewer") -> Tuple[bool, str]:
    """ایجاد کاربر جدید"""
    if not username or not password:
        return False, "نام کاربری و رمز عبور الزامی است"
    
    if len(password) < 6:
        return False, "رمز عبور باید حداقل 6 کاراکتر باشد"
    
    if role not in ROLES:
        return False, "نقش نامعتبر است"
    
    users = load_users()
    if any(u.get("username") == username for u in users):
        return False, "نام کاربری قبلاً استفاده شده است"
    
    new_user = {
        "username": username,
        "password_hash": generate_password_hash(password, method="pbkdf2:sha256"),
        "role": role,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": None
    }
    
    users.append(new_user)
    save_users(users)
    return True, "کاربر با موفقیت ایجاد شد"


def update_user_password(username: str, new_password: str) -> Tuple[bool, str]:
    """به‌روزرسانی رمز عبور کاربر"""
    if len(new_password) < 6:
        return False, "رمز عبور باید حداقل 6 کاراکتر باشد"
    
    users = load_users()
    user = next((u for u in users if u.get("username") == username), None)
    if not user:
        return False, "کاربر پیدا نشد"
    
    user["password_hash"] = generate_password_hash(new_password, method="pbkdf2:sha256")
    save_users(users)
    return True, "رمز عبور با موفقیت تغییر کرد"


def update_user_role(username: str, new_role: str) -> Tuple[bool, str]:
    """به‌روزرسانی نقش کاربر"""
    if new_role not in ROLES:
        return False, "نقش نامعتبر است"
    
    users = load_users()
    user = next((u for u in users if u.get("username") == username), None)
    if not user:
        return False, "کاربر پیدا نشد"
    
    user["role"] = new_role
    save_users(users)
    return True, "نقش کاربر با موفقیت تغییر کرد"


def delete_user(username: str) -> Tuple[bool, str]:
    """حذف کاربر"""
    users = load_users()
    if len(users) <= 1:
        return False, "حداقل باید یک کاربر وجود داشته باشد"
    
    if username == session.get("username"):
        return False, "نمی‌توانید خودتان را حذف کنید"
    
    users = [u for u in users if u.get("username") != username]
    if len(users) == len(load_users()):
        return False, "کاربر پیدا نشد"
    
    save_users(users)
    return True, "کاربر با موفقیت حذف شد"


def has_permission(permission: str) -> bool:
    """بررسی دسترسی کاربر"""
    username = session.get("username")
    if not username:
        return False
    
    user = get_user(username)
    if not user:
        return False
    
    role = user.get("role", "viewer")
    return permission in PERMISSIONS.get(role, [])


def is_admin() -> bool:
    """بررسی اینکه کاربر ادمین است یا نه"""
    return has_permission("manage_users")


# ========== Templates ==========

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>ورود ادمین - نقشه محلات</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    .container { max-width: 400px; margin: 5rem auto; padding: 2rem; background: #fff; border-radius: 12px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
    h1 { text-align: center; color: #1f4e5f; margin-bottom: 1.5rem; }
    input[type="password"] { width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; margin-bottom: 1rem; box-sizing: border-box; }
    button { width: 100%; padding: 0.75rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; }
    .error { color: #d62828; margin-top: 0.75rem; text-align: center; }
    .back-link { text-align: center; margin-top: 1rem; }
    .back-link a { color: #2a9d8f; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>ورود به پنل مدیریت</h1>
    <form method="post">
      <input type="text" name="username" placeholder="نام کاربری" required autofocus />
      <input type="password" name="password" placeholder="رمز عبور" required />
      <button type="submit">ورود</button>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
    </form>
    <div class="back-link">
      <a href="/">بازگشت به صفحه اصلی</a>
    </div>
  </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>پنل ادمین - آپلود نقشه</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1100px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    input[type="file"], input[type="text"] { width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; margin-bottom: 1rem; box-sizing: border-box; }
    button { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-left: 0.5rem; }
    button.logout { background: #d62828; }
    button.delete { background: #d62828; padding: 0.5rem 1rem; font-size: 0.9rem; }
    .error { color: #d62828; margin-top: 0.75rem; }
    .success { color: #2a9d8f; margin-top: 0.75rem; }
    .back-link { margin-top: 1rem; }
    .back-link a { color: #2a9d8f; text-decoration: none; }
    .history-list { list-style: none; padding: 0; margin-top: 1rem; }
    .history-item { padding: 1rem; margin-bottom: 0.5rem; background: #f8f9fa; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
    .history-item-info { flex: 1; }
    .history-item-actions { margin-right: 1rem; }
    h2 { margin-top: 0; }
  </style>
</head>
<body>
  <header>
    <h1>پنل مدیریت - آپلود نقشه</h1>
    <p>کاربر: {{ current_username }} ({{ current_role_name }})</p>
  </header>
  <main>
    <div class="card">
      <div style="text-align: left; margin-bottom: 1rem;">
        <a href="/" style="color: #2a9d8f; text-decoration: none;">← بازگشت به صفحه اصلی</a>
        {% if has_manage_users %}
        <a href="/admin/users" style="text-decoration: none; margin-right: 1rem;">
          <button type="button" style="background: #6f42c1;">مدیریت کاربران</button>
        </a>
        {% endif %}
        <form method="post" action="/admin/logout" style="display: inline; margin-right: 1rem;">
          <button type="submit" class="logout">خروج</button>
        </form>
      </div>
      <form method="post" enctype="multipart/form-data">
        <label>نام نقشه (اختیاری):</label>
        <input type="text" name="map_name" placeholder="مثلاً: محلات تهران" />
        <label>انتخاب فایل (Zip حاوی Shapefile یا GeoJSON):</label>
        <input type="file" name="shapefile" accept=".zip,.geojson,.json" required />
        <button type="submit">آپلود و ذخیره</button>
        {% if error %}
          <div class="error">{{ error }}</div>
        {% endif %}
        {% if success %}
          <div class="success">{{ success }}</div>
        {% endif %}
      </form>
    </div>
    <div class="card">
      <h2>آپلود عوارض محله</h2>
      <p style="color: #6c757d; margin-bottom: 1rem;">برای آپلود عوارض محله (مثلاً پارک‌ها، مدارس، مراکز خرید و...) ابتدا نقشه را انتخاب کنید:</p>
      <form id="uploadFeatureForm" enctype="multipart/form-data" onsubmit="uploadFeature(event)">
        <label>انتخاب نقشه:</label>
        <select name="map_id" id="featureMapId" required style="width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; margin-bottom: 1rem; box-sizing: border-box;">
          <option value="">-- انتخاب نقشه --</option>
          {% for item in history %}
          <option value="{{ item.map_id }}">{{ item.map_name or item.original_filename }}</option>
          {% endfor %}
        </select>
        <label>نام عارضه (اختیاری):</label>
        <input type="text" name="feature_name" placeholder="مثلاً: پارک‌های تهران" />
        <label>انتخاب فایل (Zip حاوی Shapefile یا GeoJSON):</label>
        <input type="file" name="shapefile" accept=".zip,.geojson,.json" required />
        <button type="submit">آپلود عوارض</button>
      </form>
      <div id="featureUploadStatus" style="margin-top: 1rem;"></div>
    </div>
    <div class="card">
      <h2>تاریخچه نقشه‌ها</h2>
      {% if history %}
      <ul class="history-list">
        {% for item in history %}
        <li class="history-item">
          <div class="history-item-info">
            <strong>{{ item.map_name or item.original_filename }}</strong><br/>
            <small>تاریخ: {{ item.upload_date }} | تعداد عوارض: {{ item.feature_count }} | شناسه: {{ item.map_id }}</small>
          </div>
          <div class="history-item-actions">
            <a href="/admin/links/{{ item.map_id }}" style="text-decoration: none;">
              <button type="button" style="background: #2a9d8f; padding: 0.5rem 1rem; font-size: 0.9rem; margin-left: 0.5rem;">مدیریت لینک‌های محلات</button>
            </a>
            <a href="/admin/neighborhoods/edit/{{ item.map_id }}" style="text-decoration: none;">
              <button type="button" style="background: #17a2b8; padding: 0.5rem 1rem; font-size: 0.9rem; margin-left: 0.5rem;">ویرایش محلات</button>
            </a>
            <a href="/admin/features/links/{{ item.map_id }}" style="text-decoration: none;">
              <button type="button" style="background: #ffc107; color: #000; padding: 0.5rem 1rem; font-size: 0.9rem; margin-left: 0.5rem;">مدیریت لینک‌های عوارض</button>
            </a>
            <form method="post" action="/admin/delete/{{ item.map_id }}" style="display: inline;" onsubmit="return confirm('آیا مطمئن هستید که می‌خواهید این نقشه را حذف کنید؟');">
              <button type="submit" class="delete">حذف</button>
            </form>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
      <p>هنوز نقشه‌ای آپلود نشده است.</p>
      {% endif %}
    </div>
  </main>
  <script>
    async function uploadFeature(event) {
      event.preventDefault();
      const form = document.getElementById('uploadFeatureForm');
      const formData = new FormData(form);
      const statusDiv = document.getElementById('featureUploadStatus');
      
      statusDiv.innerHTML = '<p style="color: #2a9d8f;">در حال آپلود...</p>';
      
      try {
        const response = await fetch('/admin/features/upload', {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          statusDiv.innerHTML = `<div class="success">${data.message}</div>`;
          form.reset();
          setTimeout(() => {
            statusDiv.innerHTML = '';
          }, 3000);
        } else {
          statusDiv.innerHTML = `<div class="error">${data.error}</div>`;
        }
      } catch (error) {
        statusDiv.innerHTML = `<div class="error">خطا در آپلود: ${error.message}</div>`;
      }
    }
  </script>
</body>
</html>
"""

MANAGE_LINKS_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>مدیریت لینک‌های توت‌اپ</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    button { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-left: 0.5rem; }
    button.back { background: #6c757d; }
    button.save { background: #28a745; padding: 0.5rem 1rem; font-size: 0.9rem; }
    button.save-all { background: #28a745; width: 100%; margin-top: 1rem; }
    .error { color: #d62828; margin-top: 0.75rem; }
    .success { color: #28a745; margin-top: 0.75rem; padding: 0.5rem; background: #d4edda; border-radius: 6px; }
    .neighborhood-item { padding: 1rem; margin-bottom: 1rem; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6; }
    .neighborhood-name { font-weight: bold; margin-bottom: 0.5rem; color: #1f4e5f; }
    .link-input-group { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
    .link-prefix { color: #6c757d; }
    input[type="text"] { flex: 1; padding: 0.5rem; border: 1px solid #dde3ea; border-radius: 6px; }
    .neighborhood-info { font-size: 0.9rem; color: #6c757d; margin-bottom: 0.5rem; }
    .neighborhood-form { margin-top: 0.5rem; }
    .save-status { font-size: 0.85rem; margin-top: 0.25rem; }
  </style>
</head>
<body>
  <header>
    <h1>مدیریت لینک‌های توت‌اپ</h1>
    <p>{{ map_name }}</p>
  </header>
  <main>
    <div class="card">
      <div style="margin-bottom: 1rem;">
        <a href="/admin" style="text-decoration: none;">
          <button type="button" class="back">← بازگشت به پنل ادمین</button>
        </a>
      </div>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
      {% if success %}
        <div class="success">{{ success }}</div>
      {% endif %}
      <h3>لینک‌های محلات ({{ neighborhoods|length }} محله)</h3>
      <p style="color: #6c757d; margin-bottom: 1rem;">لینک‌ها باید با <code>tootapp.ir/join/</code> شروع شوند. فقط قسمت بعد از join/ را وارد کنید.</p>
      {% for neighborhood in neighborhoods %}
      <div class="neighborhood-item">
        <div class="neighborhood-name">{{ neighborhood.name }}</div>
        <div class="neighborhood-info">{{ neighborhood.info }}</div>
        
        <!-- بخش لینک توت‌اپ -->
        <form method="post" action="/admin/links/{{ map_id }}/save" class="neighborhood-form">
          <input type="hidden" name="feature_id" value="{{ neighborhood.id }}" />
          <div class="link-input-group">
            <span class="link-prefix">tootapp.ir/join/</span>
            <input type="text" name="link" value="{{ neighborhood.link }}" placeholder="مثلاً: Tehran3Da" required />
            <button type="submit" class="save">ذخیره لینک</button>
          </div>
          <div class="save-status" id="status_{{ neighborhood.id }}"></div>
        </form>
        
        <!-- بخش آپلود لوگو -->
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #dee2e6;">
          <label style="display: block; margin-bottom: 0.5rem; font-weight: bold; color: #1f4e5f;">لوگو/عکس محله:</label>
          <div id="logo_preview_{{ neighborhood.id }}" style="margin-bottom: 0.5rem;">
            {% if neighborhood.logo_filename %}
            <div style="margin-bottom: 0.5rem;">
              <img src="/uploads/logos/{{ neighborhood.logo_filename }}" alt="لوگو" style="max-width: 150px; max-height: 150px; border-radius: 8px; border: 1px solid #dee2e6; object-fit: contain; display: block;" id="logo_img_{{ neighborhood.id }}" />
              <div style="font-size: 0.85rem; color: #6c757d; margin-top: 0.25rem;">لوگوی فعلی</div>
            </div>
            {% else %}
            <div style="font-size: 0.85rem; color: #6c757d; margin-bottom: 0.5rem;">هنوز لوگویی آپلود نشده است</div>
            {% endif %}
          </div>
          <form method="post" action="/admin/neighborhoods/{{ map_id }}/upload-logo" enctype="multipart/form-data" class="logo-upload-form">
            <input type="hidden" name="neighborhood_name" value="{{ neighborhood.name }}" />
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <input type="file" name="logo" accept="image/*" required style="flex: 1; padding: 0.5rem; border: 1px solid #dde3ea; border-radius: 6px;" />
              <button type="submit" class="save" style="background: #17a2b8;">آپلود لوگو</button>
            </div>
            <div class="save-status" id="logo_status_{{ neighborhood.id }}" style="margin-top: 0.5rem;"></div>
          </form>
        </div>
      </div>
      {% endfor %}
    </div>
  </main>
  <script>
    // مدیریت فرم‌های ذخیره
    document.querySelectorAll('.neighborhood-form').forEach(form => {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const featureId = formData.get('feature_id');
        const statusDiv = document.getElementById('status_' + featureId);
        const submitBtn = this.querySelector('button[type="submit"]');
        
        // نمایش loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'در حال ذخیره...';
        statusDiv.textContent = '';
        
        try {
          const response = await fetch(this.action, {
            method: 'POST',
            body: formData
          });
          
          const result = await response.json();
          
          if (result.success) {
            statusDiv.textContent = '✓ ' + result.message;
            statusDiv.style.color = '#28a745';
            submitBtn.textContent = 'ذخیره';
            submitBtn.disabled = false;
            
            // پاک کردن پیام بعد از 3 ثانیه
            setTimeout(() => {
              statusDiv.textContent = '';
            }, 3000);
          } else {
            statusDiv.textContent = '✗ ' + (result.error || 'خطا در ذخیره');
            statusDiv.style.color = '#d62828';
            submitBtn.textContent = 'ذخیره';
            submitBtn.disabled = false;
          }
        } catch (error) {
          statusDiv.textContent = '✗ خطا در ذخیره';
          statusDiv.style.color = '#d62828';
          submitBtn.textContent = 'ذخیره';
          submitBtn.disabled = false;
        }
      });
    });
    
    // نمایش preview فایل قبل از آپلود
    document.querySelectorAll('.logo-file-input').forEach(input => {
      input.addEventListener('change', function(e) {
        const file = this.files[0];
        if (file) {
          const neighborhoodItem = this.closest('.neighborhood-item');
          const featureIdInput = neighborhoodItem ? neighborhoodItem.querySelector('.neighborhood-form input[name="feature_id"]') : null;
          const neighborhoodId = featureIdInput ? featureIdInput.value : 'unknown';
          const logoPreviewDiv = document.getElementById('logo_preview_' + neighborhoodId);
          
          if (logoPreviewDiv) {
            const reader = new FileReader();
            reader.onload = function(e) {
              logoPreviewDiv.innerHTML = `
                <div style="margin-bottom: 0.5rem;">
                  <img src="${e.target.result}" alt="Preview" style="max-width: 150px; max-height: 150px; border-radius: 8px; border: 1px solid #dee2e6; object-fit: contain; display: block;" />
                  <div style="font-size: 0.85rem; color: #6c757d; margin-top: 0.25rem;">پیش‌نمایش (در حال آپلود...)</div>
                </div>
              `;
            };
            reader.readAsDataURL(file);
          }
        }
      });
    });
    
    // مدیریت فرم‌های آپلود لوگو
    document.querySelectorAll('.logo-upload-form').forEach(form => {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const neighborhoodName = formData.get('neighborhood_name');
        
        // پیدا کردن neighborhoodId از form action یا از feature_id در همان neighborhood-item
        const neighborhoodItem = this.closest('.neighborhood-item');
        const featureIdInput = neighborhoodItem ? neighborhoodItem.querySelector('.neighborhood-form input[name="feature_id"]') : null;
        const neighborhoodId = featureIdInput ? featureIdInput.value : 'unknown';
        
        console.log('Uploading logo for neighborhood:', { neighborhoodName, neighborhoodId });
        
        const statusDiv = document.getElementById('logo_status_' + neighborhoodId) || this.querySelector('.save-status');
        const submitBtn = this.querySelector('button[type="submit"]');
        
        // نمایش loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'در حال آپلود...';
        if (statusDiv) {
          statusDiv.textContent = '';
        }
        
        try {
          const response = await fetch(this.action, {
            method: 'POST',
            body: formData
          });
          
          const result = await response.json();
          console.log('Upload result:', result);
          
          if (result.success) {
            if (statusDiv) {
              statusDiv.textContent = '✓ ' + result.message;
              statusDiv.style.color = '#28a745';
            }
            submitBtn.textContent = 'آپلود لوگو';
            submitBtn.disabled = false;
            
            // نمایش لوگوی جدید بدون reload صفحه
            const logoPreviewDiv = document.getElementById('logo_preview_' + neighborhoodId);
            console.log('Looking for logo_preview div:', 'logo_preview_' + neighborhoodId, logoPreviewDiv);
            
            if (logoPreviewDiv && result.logo_filename) {
              const imgUrl = '/uploads/logos/' + result.logo_filename;
              console.log('Setting logo image URL:', imgUrl);
              logoPreviewDiv.innerHTML = `
                <div style="margin-bottom: 0.5rem;">
                  <img src="${imgUrl}?t=${Date.now()}" alt="لوگو" style="max-width: 150px; max-height: 150px; border-radius: 8px; border: 1px solid #dee2e6; object-fit: contain; display: block;" id="logo_img_${neighborhoodId}" onload="console.log('Logo image loaded successfully');" onerror="console.error('Failed to load logo image:', this.src); this.parentElement.parentElement.innerHTML='<div style=\\'font-size: 0.85rem; color: #d62828; margin-bottom: 0.5rem;\\'>خطا در نمایش لوگو. URL: ${imgUrl}</div>';" />
                  <div style="font-size: 0.85rem; color: #6c757d; margin-top: 0.25rem;">لوگوی فعلی</div>
                </div>
              `;
            } else {
              console.warn('Could not find logo_preview div or logo_filename:', { logoPreviewDiv, logo_filename: result.logo_filename });
            }
            
            // پاک کردن فایل input
            const fileInput = this.querySelector('input[type="file"]');
            if (fileInput) {
              fileInput.value = '';
            }
          } else {
            if (statusDiv) {
              statusDiv.textContent = '✗ ' + (result.error || 'خطا در آپلود');
              statusDiv.style.color = '#d62828';
            }
            submitBtn.textContent = 'آپلود لوگو';
            submitBtn.disabled = false;
          }
        } catch (error) {
          if (statusDiv) {
            statusDiv.textContent = '✗ خطا در آپلود';
            statusDiv.style.color = '#d62828';
          }
          submitBtn.textContent = 'آپلود لوگو';
          submitBtn.disabled = false;
        }
      });
    });
  </script>
</body>
</html>
"""

MANAGE_FEATURE_LINKS_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>مدیریت لینک‌های عوارض</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    button { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-left: 0.5rem; }
    button.back { background: #6c757d; }
    button.save { background: #28a745; padding: 0.5rem 1rem; font-size: 0.9rem; }
    .error { color: #d62828; margin-top: 0.75rem; }
    .success { color: #28a745; margin-top: 0.75rem; padding: 0.5rem; background: #d4edda; border-radius: 6px; }
    .feature-item { padding: 1rem; margin-bottom: 1rem; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6; }
    .feature-name { font-weight: bold; margin-bottom: 0.5rem; color: #1f4e5f; }
    .link-input-group { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
    .link-prefix { color: #6c757d; }
    input[type="text"] { flex: 1; padding: 0.5rem; border: 1px solid #dde3ea; border-radius: 6px; }
    .feature-form { margin-top: 0.5rem; }
    .save-status { font-size: 0.85rem; margin-top: 0.25rem; }
  </style>
</head>
<body>
  <header>
    <h1>مدیریت لینک‌های عوارض</h1>
    <p>{{ map_name }}</p>
  </header>
  <main>
    <div class="card">
      <div style="margin-bottom: 1rem;">
        <a href="/admin" style="text-decoration: none;">
          <button type="button" class="back">← بازگشت به پنل ادمین</button>
        </a>
      </div>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
      {% if success %}
        <div class="success">{{ success }}</div>
      {% endif %}
      <h3>لینک‌های عوارض ({{ features|length }} عارضه)</h3>
      <p style="color: #6c757d; margin-bottom: 1rem;">لینک‌ها باید با <code>tootapp.ir/join/</code> شروع شوند. فقط قسمت بعد از join/ را وارد کنید.</p>
      {% for feature in features %}
      <div class="feature-item">
        <div class="feature-name">{{ feature.feature_name or feature.original_filename }}</div>
        <form method="post" action="/admin/features/update-link/{{ feature.feature_id }}" class="feature-form">
          <input type="hidden" name="map_id" value="{{ map_id }}" />
          <div class="link-input-group">
            <span class="link-prefix">tootapp.ir/join/</span>
            <input type="text" name="link" value="{{ feature.link }}" placeholder="مثلاً: Tehran3Da" />
            <button type="submit" class="save">ذخیره</button>
          </div>
          <div class="save-status" id="status_{{ feature.feature_id }}"></div>
        </form>
      </div>
      {% endfor %}
    </div>
  </main>
  <script>
    // مدیریت فرم‌های ذخیره
    document.querySelectorAll('.feature-form').forEach(form => {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const featureId = this.action.split('/').pop();
        const statusDiv = document.getElementById('status_' + featureId);
        const submitBtn = this.querySelector('button[type="submit"]');
        
        // نمایش loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'در حال ذخیره...';
        statusDiv.textContent = '';
        
        try {
          const response = await fetch(this.action, {
            method: 'POST',
            body: formData
          });
          
          const result = await response.json();
          
          if (result.success) {
            statusDiv.textContent = '✓ ' + result.message;
            statusDiv.style.color = '#28a745';
            submitBtn.textContent = 'ذخیره';
            submitBtn.disabled = false;
            
            // پاک کردن پیام بعد از 3 ثانیه
            setTimeout(() => {
              statusDiv.textContent = '';
            }, 3000);
          } else {
            statusDiv.textContent = '✗ ' + (result.error || 'خطا در ذخیره');
            statusDiv.style.color = '#d62828';
            submitBtn.textContent = 'ذخیره';
            submitBtn.disabled = false;
          }
        } catch (error) {
          statusDiv.textContent = '✗ خطا در ذخیره';
          statusDiv.style.color = '#d62828';
          submitBtn.textContent = 'ذخیره';
          submitBtn.disabled = false;
        }
      });
    });
  </script>
</body>
</html>
"""

MANAGE_USERS_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>مدیریت کاربران</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    button { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-left: 0.5rem; }
    button.back { background: #6c757d; }
    button.delete { background: #d62828; padding: 0.5rem 1rem; font-size: 0.9rem; }
    button.edit { background: #ffc107; color: #000; padding: 0.5rem 1rem; font-size: 0.9rem; }
    .error { color: #d62828; margin-top: 0.75rem; padding: 0.5rem; background: #f8d7da; border-radius: 6px; }
    .success { color: #28a745; margin-top: 0.75rem; padding: 0.5rem; background: #d4edda; border-radius: 6px; }
    input[type="text"], input[type="password"], select { width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; margin-bottom: 1rem; box-sizing: border-box; }
    .user-item { padding: 1rem; margin-bottom: 1rem; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center; }
    .user-info { flex: 1; }
    .user-actions { margin-right: 1rem; }
    .user-name { font-weight: bold; color: #1f4e5f; }
    .user-details { font-size: 0.9rem; color: #6c757d; margin-top: 0.25rem; }
    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
    .modal-content { background: #fff; margin: 5% auto; padding: 2rem; border-radius: 12px; max-width: 500px; }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .close { font-size: 2rem; cursor: pointer; }
  </style>
</head>
<body>
  <header>
    <h1>مدیریت کاربران</h1>
  </header>
  <main>
    <div class="card">
      <div style="margin-bottom: 1rem;">
        <a href="/admin" style="text-decoration: none;">
          <button type="button" class="back">← بازگشت به پنل ادمین</button>
        </a>
      </div>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
      {% if success %}
        <div class="success">{{ success }}</div>
      {% endif %}
      
      <h2>ایجاد کاربر جدید</h2>
      <form method="post" action="/admin/users/create">
        <input type="text" name="username" placeholder="نام کاربری" required />
        <input type="password" name="password" placeholder="رمز عبور (حداقل 6 کاراکتر)" required minlength="6" />
        <select name="role" required>
          <option value="viewer">مشاهده‌کننده</option>
          <option value="editor">ویرایشگر</option>
          <option value="admin">مدیر کل</option>
        </select>
        <button type="submit">ایجاد کاربر</button>
      </form>
    </div>
    
    <div class="card">
      <h2>لیست کاربران ({{ users|length }} کاربر)</h2>
      {% for user in users %}
      <div class="user-item">
        <div class="user-info">
          <div class="user-name">{{ user.username }}</div>
          <div class="user-details">
            نقش: {{ role_names[user.role] }} | 
            ایجاد شده: {{ user.created_at }} | 
            آخرین ورود: {{ user.last_login or 'هرگز' }}
          </div>
        </div>
        <div class="user-actions">
          <button type="button" class="edit" onclick="openChangePasswordModal('{{ user.username }}')">تغییر رمز</button>
          {% if user.username != current_username %}
          <form method="post" action="/admin/users/delete/{{ user.username }}" style="display: inline;" onsubmit="return confirm('آیا مطمئن هستید که می‌خواهید کاربر {{ user.username }} را حذف کنید؟');">
            <button type="submit" class="delete">حذف</button>
          </form>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
  </main>
  
  <!-- Modal تغییر رمز عبور -->
  <div id="changePasswordModal" class="modal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>تغییر رمز عبور</h3>
        <span class="close" onclick="closeChangePasswordModal()">&times;</span>
      </div>
      <form method="post" action="/admin/users/change-password" id="changePasswordForm">
        <input type="hidden" name="username" id="changePasswordUsername" />
        <input type="password" name="new_password" placeholder="رمز عبور جدید (حداقل 6 کاراکتر)" required minlength="6" />
        <button type="submit">تغییر رمز</button>
      </form>
    </div>
  </div>
  
  <script>
    function openChangePasswordModal(username) {
      document.getElementById('changePasswordUsername').value = username;
      document.getElementById('changePasswordModal').style.display = 'block';
    }
    
    function closeChangePasswordModal() {
      document.getElementById('changePasswordModal').style.display = 'none';
    }
    
    window.onclick = function(event) {
      const modal = document.getElementById('changePasswordModal');
      if (event.target == modal) {
        closeChangePasswordModal();
      }
    }
  </script>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>نقشه محلات ایران</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1100px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    #map { width: 100%; height: 520px; border-radius: 12px; position: relative; }
    .map-container { position: relative; width: 100%; }
    
    /* Sidebar Styles */
    .sidebar { 
      position: fixed; 
      top: 0; 
      left: -400px; 
      width: 380px; 
      height: 100vh; 
      background: #fff; 
      box-shadow: 2px 0 10px rgba(0,0,0,0.1); 
      transition: left 0.3s ease; 
      z-index: 1000; 
      overflow-y: auto; 
      direction: rtl;
      padding: 1.5rem;
    }
    .sidebar.open { left: 0; }
    .sidebar-header { 
      border-bottom: 2px solid #2a9d8f; 
      padding-bottom: 1rem; 
      margin-bottom: 1.5rem; 
    }
    .sidebar-header h2 { 
      margin: 0 0 0.5rem 0; 
      color: #1f4e5f; 
      font-size: 1.5rem; 
    }
    .sidebar-header .location-info { 
      color: #6c757d; 
      font-size: 0.9rem; 
      margin-top: 0.5rem; 
    }
    .sidebar-close { 
      position: absolute; 
      top: 1rem; 
      left: 1rem; 
      background: #dc3545; 
      color: #fff; 
      border: none; 
      border-radius: 50%; 
      width: 35px; 
      height: 35px; 
      cursor: pointer; 
      font-size: 1.2rem; 
      display: flex; 
      align-items: center; 
      justify-content: center; 
    }
    .sidebar-close:hover { background: #c82333; }
    .sidebar-logo { 
      text-align: center; 
      margin: 1.5rem 0; 
      padding: 1rem; 
      background: #f8f9fa; 
      border-radius: 8px; 
    }
    .sidebar-logo-icon { 
      font-size: 3rem; 
      color: #2a9d8f; 
    }
    .sidebar-content { margin-top: 1rem; }
    .info-item { 
      padding: 0.75rem 0; 
      border-bottom: 1px solid #e9ecef; 
    }
    .info-item:last-child { border-bottom: none; }
    .info-label { 
      font-weight: bold; 
      color: #1f4e5f; 
      margin-bottom: 0.25rem; 
    }
    .info-value { 
      color: #495057; 
      font-size: 0.95rem; 
    }
    .tootapp-link { 
      margin-top: 2rem; 
      padding: 1rem; 
      background: #2a9d8f; 
      border-radius: 8px; 
      text-align: center; 
    }
    .tootapp-link a { 
      color: #fff; 
      text-decoration: none; 
      font-weight: bold; 
      font-size: 1.1rem; 
      display: block; 
    }
    .tootapp-link a:hover { text-decoration: underline; }
    .sidebar-overlay { 
      display: none; 
      position: fixed; 
      top: 0; 
      left: 0; 
      width: 100%; 
      height: 100%; 
      background: rgba(0,0,0,0.5); 
      z-index: 999; 
    }
    .sidebar-overlay.show { display: block; }
    
    /* Responsive design for mobile */
    @media (max-width: 768px) {
      .sidebar { 
        width: 85vw; 
        max-width: 320px;
        padding: 1rem;
      }
      .sidebar-header h2 { 
        font-size: 1.2rem; 
      }
      .sidebar-header .location-info { 
        font-size: 0.8rem; 
      }
      .sidebar-logo-icon { 
        font-size: 2rem; 
      }
      .sidebar-content { 
        font-size: 0.9rem; 
      }
      .info-item { 
        padding: 0.5rem 0; 
      }
      .info-label { 
        font-size: 0.85rem; 
      }
      .info-value { 
        font-size: 0.85rem; 
      }
      .tootapp-link { 
        padding: 0.75rem; 
        font-size: 0.95rem; 
      }
    }
    
    @media (max-width: 480px) {
      .sidebar { 
        width: 90vw; 
        max-width: 300px;
        padding: 0.75rem;
      }
      .sidebar-header h2 { 
        font-size: 1.1rem; 
        margin-bottom: 0.25rem;
      }
      .sidebar-header .location-info { 
        font-size: 0.75rem; 
      }
      .sidebar-close { 
        width: 30px; 
        height: 30px; 
        font-size: 1rem; 
        top: 0.5rem; 
        left: 0.5rem; 
      }
      .sidebar-logo { 
        margin: 1rem 0; 
        padding: 0.75rem; 
      }
      .sidebar-logo-icon { 
        font-size: 1.5rem; 
      }
      .sidebar-content { 
        margin-top: 0.75rem; 
      }
      .info-item { 
        padding: 0.4rem 0; 
      }
      .info-label { 
        font-size: 0.8rem; 
        margin-bottom: 0.2rem; 
      }
      .info-value { 
        font-size: 0.8rem; 
      }
      .tootapp-link { 
        margin-top: 1.5rem; 
        padding: 0.75rem; 
      }
      .tootapp-link a { 
        font-size: 1rem; 
      }
    }
    
    .history-list { list-style: none; padding: 0; margin: 0; max-height: 400px; overflow-y: auto; overflow-x: hidden; }
    .history-list::-webkit-scrollbar { width: 8px; }
    .history-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
    .history-list::-webkit-scrollbar-thumb { background: #888; border-radius: 10px; }
    .history-list::-webkit-scrollbar-thumb:hover { background: #555; }
    .history-item { padding: 1rem; margin-bottom: 0.5rem; background: #f8f9fa; border-radius: 8px; cursor: pointer; transition: background 0.2s; min-height: 80px; }
    .history-item:hover { background: #e9ecef; }
    .history-item.active { background: #2a9d8f; color: #fff; }
    .history-item.hidden { display: none; }
    .admin-link { text-align: center; margin-top: 1rem; }
    .admin-link a { color: #2a9d8f; text-decoration: none; }
    .summary { margin-top: 1rem; line-height: 1.8; }
    .summary-toggle-btn { width: 100%; padding: 0.75rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-bottom: 1rem; }
    .summary-toggle-btn:hover { background: #238a7d; }
    .search-box { width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; margin-bottom: 1rem; box-sizing: border-box; font-size: 1rem; }
    .search-box:focus { outline: none; border-color: #2a9d8f; }
    .no-results { text-align: center; padding: 2rem; color: #6c757d; }
    ul { padding-right: 1.25rem; }
  </style>
</head>
<body>
  <header>
    <h1>مرزبندی محلات شهرهای ایران</h1>
    <p>مشاهده نقشه‌های آپلود شده</p>
  </header>
  <main>
    {% if history %}
    <section class="card">
      <h2>شهر خود را انتخاب کنید</h2>
      <input type="text" id="searchInput" class="search-box" placeholder="جستجوی شهر یا نام نقشه..." onkeyup="filterMaps()" />
      <ul class="history-list" id="historyList">
        {% for item in history %}
        <li class="history-item {% if item.map_id == selected_map_id %}active{% endif %}" 
            data-name="{{ (item.map_name or item.original_filename)|lower }}" 
            data-filename="{{ item.original_filename|lower }}"
            onclick="loadMap('{{ item.map_id }}')">
          <strong>{{ item.map_name or item.original_filename }}</strong><br/>
          <small>تاریخ: {{ item.upload_date }} | تعداد عوارض: {{ item.feature_count }}</small>
        </li>
        {% endfor %}
      </ul>
      <div id="noResults" class="no-results" style="display: none;">
        <p>نتیجه‌ای یافت نشد. لطفاً کلمه دیگری جستجو کنید.</p>
      </div>
    </section>
    {% endif %}
    <section class="card">
      {% if summary %}
      <button onclick="toggleSummary()" class="summary-toggle-btn">اطلاعات محله</button>
      <div class="summary" id="summary-details" style="display: none;">
        <strong>اطلاعات محله:</strong>
        <p>تعداد عوارض: {{ summary.feature_count }}</p>
        <p>سیستم مختصات: {{ summary.crs }}</p>
        {% if summary.columns %}
        <p>ستون‌های توصیفی:</p>
        <ul>
          {% for col in summary.columns %}
          <li>{{ col }}</li>
          {% endfor %}
        </ul>
        {% endif %}
      </div>
      {% endif %}
      {% if selected_map_id %}
      <div class="card" style="margin-bottom: 1rem;">
        <h3>عوارض محله</h3>
        <div id="features-list" style="margin-bottom: 1rem;">
          <p style="color: #6c757d;">در حال بارگذاری...</p>
        </div>
        <div id="selected-features" style="display: none;">
          <strong>عوارض انتخاب شده:</strong>
          <div id="selected-list" style="margin-top: 0.5rem;"></div>
        </div>
      </div>
      {% endif %}
      <div class="map-container">
        <div id="map"></div>
        <!-- Sidebar -->
        <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>
        <div class="sidebar" id="neighborhoodSidebar">
          <button class="sidebar-close" onclick="closeSidebar()">×</button>
          <div class="sidebar-header">
            <h2 id="sidebarNeighborhoodName">نام محله</h2>
            <div class="location-info">
              <div id="sidebarDistrict">منطقه: -</div>
              <div id="sidebarCity">شهر: -</div>
            </div>
          </div>
          <div class="sidebar-logo">
            <div class="sidebar-logo-icon">📍</div>
          </div>
          <div class="sidebar-content" id="sidebarContent">
            <div class="info-item">
              <div class="info-label">نام انگلیسی:</div>
              <div class="info-value" id="sidebarEnglishName">-</div>
            </div>
            <div class="info-item">
              <div class="info-label">مساحت:</div>
              <div class="info-value" id="sidebarArea">-</div>
            </div>
            <div class="info-item">
              <div class="info-label">جمعیت:</div>
              <div class="info-value" id="sidebarPopulation">-</div>
            </div>
          </div>
          <div class="tootapp-link" id="sidebarTootappLink" style="display: none;">
            <a href="#" target="_blank" id="sidebarTootappUrl">پیوند به توت‌اپ</a>
          </div>
        </div>
      </div>
    </section>
    <div class="admin-link">
      <a href="/admin/login">ورود به پنل ادمین</a>
    </div>
  </main>
  <script>
    const map = L.map('map').setView([32.0, 53.0], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    let mainLayer = null; // لایر اصلی محلات
    const geojsonData = {{ geojson|safe if geojson else 'null' }};
    const selectedFeaturesGeojson = {{ selected_features_geojson|safe if selected_features_geojson else '[]' }};
    
    // حذف تمام لایه‌های قبلی
    map.eachLayer(function(layer) {
      if (layer instanceof L.GeoJSON) {
        map.removeLayer(layer);
      }
    });
    
    // بارگذاری لایه محلات
    if (geojsonData) {
      mainLayer = L.geoJSON(geojsonData, {
        style: function() { return { color: '#111', weight: 2, fillOpacity: 0.1, zIndex: 100 }; },
        onEachFeature: function(feature, layer) {
          if (feature.properties) {
            const props = feature.properties;
            
            // ذخیره feature در layer برای دسترسی بعدی
            layer.feature = feature;
            
            // اضافه کردن event handler برای کلیک
            layer.on('click', function() {
              // استفاده از properties به‌روز شده از feature
              openSidebar(layer.feature.properties);
            });
          }
        }
      }).addTo(map);
      
      // تنظیم view روی نقشه محلات بعد از اضافه شدن لایه
      // استفاده از setTimeout برای اطمینان از اینکه نقشه کاملاً render شده است
      setTimeout(function() {
        try {
          if (mainLayer && mainLayer.getBounds) {
            map.fitBounds(mainLayer.getBounds(), { 
              padding: [50, 50], 
              maxZoom: 16,
              animate: true
            });
          }
        } catch (err) {
          console.warn('Cannot fit bounds', err);
        }
      }, 100);
    }
    
    // اگر mainLayer وجود ندارد، view را تنظیم نکن
    if (!mainLayer) {
      // اگر نقشه خالی است، view را روی ایران نگه دار
      map.setView([32.0, 53.0], 5);
    }
    
    // بارگذاری عوارض به صورت خودکار غیرفعال شده است
    // کاربر باید دکمه روبروی هر عارضه را بزند تا آن عارضه لود شود
    
    // کد قدیمی بارگذاری خودکار حذف شده است
    /*
    const featureLayers = [];
    const selectedFeatureIdsForMap = {{ selected_feature_ids|safe if selected_feature_ids else '[]' }};
    
    if (selectedFeaturesGeojson && Array.isArray(selectedFeaturesGeojson) && selectedFeatureIdsForMap.length > 0) {
      selectedFeaturesGeojson.forEach(function(featureGeojsonStr, index) {
        try {
          const featureId = selectedFeatureIdsForMap[index];
          if (!featureId) return;
          
          let featureGeojson = typeof featureGeojsonStr === 'string' ? JSON.parse(featureGeojsonStr) : featureGeojsonStr;
          
          if (featureGeojson && featureGeojson.type === 'FeatureCollection' && featureGeojson.features) {
            const featureLayer = L.geoJSON(featureGeojson, {
              pointToLayer: function(feature, latlng) {
                return L.circleMarker(latlng, {
                  radius: 10,
                  fillColor: '#ff0000',
                  color: '#cc0000',
                  weight: 3,
                  opacity: 1,
                  fillOpacity: 0.9,
                  zIndex: 1000
                });
              },
              style: function(feature) {
                return {
                  color: '#ff0000',
                  weight: 4,
                  opacity: 0.8,
                  fillOpacity: 0.5,
                  fillColor: '#ff6b6b',
                  zIndex: 1000
                };
              },
              onEachFeature: function(feature, layer) {
                if (feature.properties) {
                  const props = feature.properties;
                  const popupItems = [];
                  
                  // نمایش نام یا عنوان عارضه
                  const nameFields = ['name', 'نام', 'title', 'عنوان', 'shop', 'فروشگاه', 'store'];
                  let name = null;
                  for (const field of nameFields) {
                    for (const key in props) {
                      if (key.toLowerCase().includes(field.toLowerCase())) {
                        name = props[key];
                        break;
                      }
                    }
                    if (name) break;
                  }
                  
                  if (name) {
                    popupItems.push(`<strong style="font-size: 1.1em; color: #2a9d8f;">${name}</strong>`);
                  }
                  
                  // نمایش سایر ویژگی‌ها
                  for (const key in props) {
                    if (key.toLowerCase() !== 'geometry') {
                      const value = props[key];
                      if (value !== undefined && value !== null && String(value).trim() !== '') {
                        let skip = false;
                        for (const field of nameFields) {
                          if (key.toLowerCase().includes(field.toLowerCase())) {
                            skip = true;
                            break;
                          }
                        }
                        if (!skip) {
                          popupItems.push(`<strong>${key}:</strong> ${String(value).trim()}`);
                        }
                      }
                    }
                  }
                  
                  if (popupItems.length > 0) {
                    layer.bindPopup(popupItems.join('<br/>'));
                  }
                }
              }
            });
            
            // اضافه کردن featureId به لایه برای شناسایی بعدی
            featureLayer.featureId = featureId;
            
            featureLayer.addTo(map);
            if (featureLayer.bringToFront) {
              featureLayer.bringToFront();
            }
            featureLayers.push(featureLayer);
            
            // ذخیره در featureLayersMap برای حذف بعدی
            featureLayersMap[featureId] = featureLayer;
          }
        } catch (e) {
          console.error('Error loading feature:', e);
        }
      });
    }
    */

    function loadMap(mapId) {
      window.location.href = '/map/' + mapId;
    }
    
    function openSidebar(props) {
      // دیباگ: نمایش properties
      console.log('Sidebar properties:', props);
      
      // استخراج هوشمند نام محله - اولویت با فیلدهای رایج
      const neighborhoodName = getNeighborhoodName(props);
      
      // اولویت اول: فیلدهای ویرایش شده (exact match)
      // منطقه: اول exact match برای district، سپس جستجوی کلمات کلیدی
      let district = (props.district && String(props.district).trim() !== '') ? String(props.district).trim() : null;
      if (!district) {
        district = getFieldValueByKeywords(props, ['منطقه', 'region', 'regio', 'place', 'district']);
      }
      
      // شهر: اول exact match برای city، سپس جستجوی فیلدهای دیگر
      let city = (props.city && String(props.city).trim() !== '') ? String(props.city).trim() : null;
      if (!city) {
        city = getFieldValue(props, ['city', 'shahr', 'City', 'CITY', 'شهر']);
      }
      
      // نام انگلیسی: اول exact match برای english_name، سپس جستجوی فیلدهای دیگر
      let englishName = (props.english_name && String(props.english_name).trim() !== '') ? String(props.english_name).trim() : null;
      if (!englishName) {
        englishName = getFieldValue(props, ['english_name', 'name_en', 'EnglishName', 'NAME_EN', 'Name_EN']);
      }
      
      // مساحت: اول exact match برای area، سپس جستجوی کلمات کلیدی
      let area = (props.area && String(props.area).trim() !== '') ? String(props.area).trim() : null;
      if (!area) {
        area = getFieldValueByKeywords(props, ['مساحت', 'area']);
      }
      
      // جمعیت: اول exact match برای population، سپس جستجوی کلمات کلیدی
      let population = (props.population && String(props.population).trim() !== '') ? String(props.population).trim() : null;
      if (!population) {
        population = getFieldValueByKeywords(props, ['جمعیت', 'pop', 'population']);
      }
      
      // دیباگ: نمایش مقادیر استخراج شده
      console.log('Extracted values:', { neighborhoodName, district, city, englishName, area, population });
      
      const tootappUrl = props.tootapp_url || 'https://tootapp.ir/join/';
      
      // پر کردن sidebar
      document.getElementById('sidebarNeighborhoodName').textContent = neighborhoodName || 'نامشخص';
      document.getElementById('sidebarDistrict').textContent = district ? `منطقه: ${district}` : 'منطقه: -';
      document.getElementById('sidebarCity').textContent = city ? `شهر: ${city}` : 'شهر: -';
      document.getElementById('sidebarEnglishName').textContent = englishName || '-';
      document.getElementById('sidebarArea').textContent = area ? `${area} متر مربع` : '-';
      document.getElementById('sidebarPopulation').textContent = population || '-';
      
      // تنظیم لینک توت‌اپ
      const tootappLinkDiv = document.getElementById('sidebarTootappLink');
      const tootappLink = document.getElementById('sidebarTootappUrl');
      if (tootappUrl && tootappUrl !== 'https://tootapp.ir/join/') {
        tootappLink.href = tootappUrl;
        tootappLinkDiv.style.display = 'block';
      } else {
        tootappLinkDiv.style.display = 'none';
      }
      
      // بارگذاری لوگو از سرور
      const selectedMapId = '{{ selected_map_id if selected_map_id else "" }}';
      const logoContainer = document.querySelector('.sidebar-logo');
      
      // دیباگ: نمایش اطلاعات
      console.log('Loading logo:', { selectedMapId, neighborhoodName });
      
      if (selectedMapId && neighborhoodName) {
        fetch(`/api/neighborhood-logo?map_id=${selectedMapId}&neighborhood_name=${encodeURIComponent(neighborhoodName)}`)
          .then(response => response.json())
          .then(data => {
            console.log('Logo API response:', data);
            if (data.success && data.logo_filename) {
              const imgUrl = `/uploads/logos/${data.logo_filename}`;
              console.log('Loading logo image from:', imgUrl);
              logoContainer.innerHTML = `<img src="${imgUrl}" alt="لوگو" style="max-width: 100%; max-height: 150px; border-radius: 8px;" onerror="console.error('Failed to load logo image:', this.src); this.parentElement.innerHTML='<div class=\\'sidebar-logo-icon\\'>📍</div>';" />`;
            } else {
              console.warn('Logo not found:', data.message || 'Unknown error', data);
              if (data.available_logos && data.available_logos.length > 0) {
                console.log('Available logos for this map:', data.available_logos);
              }
              logoContainer.innerHTML = '<div class="sidebar-logo-icon">📍</div>';
            }
          })
          .catch(error => {
            console.error('Error fetching logo:', error);
            logoContainer.innerHTML = '<div class="sidebar-logo-icon">📍</div>';
          });
      } else {
        console.warn('Missing map_id or neighborhoodName:', { selectedMapId, neighborhoodName });
        logoContainer.innerHTML = '<div class="sidebar-logo-icon">📍</div>';
      }
      
      // باز کردن sidebar
      document.getElementById('neighborhoodSidebar').classList.add('open');
      document.getElementById('sidebarOverlay').classList.add('show');
    }
    
    function closeSidebar() {
      document.getElementById('neighborhoodSidebar').classList.remove('open');
      document.getElementById('sidebarOverlay').classList.remove('show');
    }
    
    function getFieldValue(props, fieldNames) {
      for (const fieldName of fieldNames) {
        for (const key in props) {
          if (key.toLowerCase() === fieldName.toLowerCase()) {
            const value = props[key];
            if (value !== undefined && value !== null && String(value).trim() !== '') {
              return String(value).trim();
            }
          }
        }
      }
      return null;
    }
    
    // تابع بهبود یافته برای جستجوی فیلدها بر اساس کلمات کلیدی (case-insensitive و partial match)
    function getFieldValueByKeywords(props, keywords) {
      // اولویت اول: exact match (case-insensitive)
      for (const keyword of keywords) {
        for (const key in props) {
          if (key.toLowerCase() === keyword.toLowerCase()) {
            const value = props[key];
            if (value !== undefined && value !== null && String(value).trim() !== '') {
              return String(value).trim();
            }
          }
        }
      }
      
      // اولویت دوم: partial match (کلمه کلیدی در نام فیلد باشد)
      for (const keyword of keywords) {
        const keywordLower = keyword.toLowerCase();
        for (const key in props) {
          const keyLower = key.toLowerCase();
          // بررسی اینکه کلمه کلیدی در نام فیلد باشد
          if (keyLower.includes(keywordLower)) {
            const value = props[key];
            if (value !== undefined && value !== null && String(value).trim() !== '') {
              // بررسی که مقدار عددی یا رشته معتبر باشد
              const strValue = String(value).trim();
              if (strValue !== '' && strValue !== 'null' && strValue !== 'undefined') {
                return strValue;
              }
            }
          }
        }
      }
      
      return null;
    }
    
    // تابع هوشمند برای استخراج نام محله
    function getNeighborhoodName(props) {
      // لیست اولویت‌دار فیلدهای احتمالی برای نام محله
      const priorityFields = [
        'NAME_NEW',  // اولویت اول: فیلد جدید
        'Name', 'NAME', 'name',  // اولویت دوم: فیلدهای دقیق
        'mahalle', 'MAHALLE', 'Mahalle',
        'neighborhood', 'NEIGHBORHOOD', 'Neighborhood',
        'neighbourhood', 'NEIGHBOURHOOD', 'Neighbourhood',
        'محله', 'نام محله',
        'title', 'TITLE', 'Title',
        'label', 'LABEL', 'Label'
      ];
      
      // ابتدا بررسی فیلدهای با اولویت
      for (const fieldName of priorityFields) {
        if (props.hasOwnProperty(fieldName)) {
          const value = props[fieldName];
          if (value !== undefined && value !== null && String(value).trim() !== '') {
            return String(value).trim();
          }
        }
      }
      
      // اگر پیدا نشد، بررسی case-insensitive
      for (const fieldName of priorityFields) {
        for (const key in props) {
          if (key.toLowerCase() === fieldName.toLowerCase()) {
            const value = props[key];
            if (value !== undefined && value !== null && String(value).trim() !== '') {
              return String(value).trim();
            }
          }
        }
      }
      
      // اگر هنوز پیدا نشد، اولین فیلد غیرخالی را برگردان (به جز فیلدهای خاص)
      const excludeFields = ['tootapp_url', 'geometry', 'feature_id', 'id', 'ID', 'gid', 'GID'];
      for (const key in props) {
        if (excludeFields.includes(key)) continue;
        const value = props[key];
        if (value !== undefined && value !== null && String(value).trim() !== '') {
          // بررسی که مقدار عددی خالص نباشد (مثل ID)
          const numValue = Number(value);
          if (isNaN(numValue) || String(value).length > 10) {
            return String(value).trim();
          }
        }
      }
      
      return null;
    }

    function toggleSummary() {
      const summaryDiv = document.getElementById('summary-details');
      const btn = document.querySelector('.summary-toggle-btn');
      if (summaryDiv.style.display === 'none') {
        summaryDiv.style.display = 'block';
        btn.textContent = 'مخفی کردن اطلاعات محله';
      } else {
        summaryDiv.style.display = 'none';
        btn.textContent = 'اطلاعات محله';
      }
    }

    function filterMaps() {
      const searchInput = document.getElementById('searchInput');
      const searchTerm = searchInput.value.toLowerCase().trim();
      const historyItems = document.querySelectorAll('.history-item');
      const noResults = document.getElementById('noResults');
      let visibleCount = 0;

      historyItems.forEach(item => {
        const name = item.getAttribute('data-name') || '';
        const filename = item.getAttribute('data-filename') || '';
        const searchText = name + ' ' + filename;

        if (searchTerm === '' || searchText.includes(searchTerm)) {
          item.classList.remove('hidden');
          visibleCount++;
        } else {
          item.classList.add('hidden');
        }
      });

      // نمایش پیام "نتیجه‌ای یافت نشد" اگر هیچ نتیجه‌ای نباشد
      if (visibleCount === 0 && searchTerm !== '') {
        noResults.style.display = 'block';
      } else {
        noResults.style.display = 'none';
      }
    }

    // مدیریت عوارض محله
    const selectedMapId = '{{ selected_map_id if selected_map_id else "" }}';
    const selectedFeatures = new Set();
    
    // عوارض به صورت پیش‌فرض خاموش هستند
    // کاربر باید دکمه روبروی هر عارضه را بزند تا آن عارضه روشن شود

    if (selectedMapId) {
      // بارگذاری لیست عوارض
      fetch(`/api/features/list?map_id=${selectedMapId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success && data.features.length > 0) {
            const featuresList = document.getElementById('features-list');
            featuresList.innerHTML = ''; // پاک کردن محتوای قبلی
            
            data.features.forEach(feature => {
              const isActive = selectedFeatures.has(feature.feature_id);
              
              // ایجاد container برای هر عارضه
              const featureItem = document.createElement('div');
              featureItem.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 0.5rem; margin-bottom: 0.5rem; background: #f8f9fa; border-radius: 6px;';
              
              const featureName = document.createElement('span');
              featureName.textContent = feature.feature_name || feature.original_filename;
              featureName.style.cssText = 'flex: 1; margin-left: 0.5rem;';
              
              // ایجاد دکمه خاموش/روشن
              const toggleBtn = document.createElement('button');
              toggleBtn.type = 'button';
              toggleBtn.id = `toggle-${feature.feature_id}`;
              toggleBtn.className = 'feature-toggle-btn';
              toggleBtn.style.cssText = 'padding: 0.4rem 0.8rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; min-width: 70px; transition: all 0.3s; font-weight: bold;';
              
              // تنظیم استایل و متن بر اساس وضعیت
              if (isActive) {
                toggleBtn.textContent = 'روشن';
                toggleBtn.style.backgroundColor = '#28a745';
                toggleBtn.style.color = '#fff';
              } else {
                toggleBtn.textContent = 'خاموش';
                toggleBtn.style.backgroundColor = '#dc3545';
                toggleBtn.style.color = '#fff';
              }
              
              // اضافه کردن event listener
              toggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const currentState = selectedFeatures.has(feature.feature_id);
                const newState = !currentState;
                
                toggleFeature(feature.feature_id, newState);
                
                // به‌روزرسانی ظاهر دکمه
                if (newState) {
                  this.textContent = 'روشن';
                  this.style.backgroundColor = '#28a745';
                } else {
                  this.textContent = 'خاموش';
                  this.style.backgroundColor = '#dc3545';
                }
              });
              
              featureItem.appendChild(featureName);
              featureItem.appendChild(toggleBtn);
              
              featuresList.appendChild(featureItem);
            });
          } else {
            document.getElementById('features-list').innerHTML = '<p style="color: #6c757d;">هیچ عارضه‌ای برای این نقشه آپلود نشده است.</p>';
          }
        })
        .catch(error => {
          console.error('Error loading features:', error);
          document.getElementById('features-list').innerHTML = '<p style="color: #d32f2f;">خطا در بارگذاری عوارض</p>';
        });
    }

    const featureLayersMap = {}; // نگهداری لایه‌های عوارض
    
    function toggleFeature(featureId, show) {
      if (show) {
        selectedFeatures.add(featureId);
        // بارگذاری عارضه از API و نمایش روی نقشه
        loadFeatureOnMap(featureId).then(() => {
          // بعد از اضافه کردن عارضه، نقشه را مجدداً تنظیم کن
          refreshMapView();
        });
      } else {
        selectedFeatures.delete(featureId);
        // حذف عارضه از نقشه
        removeFeatureFromMap(featureId);
        // بعد از حذف عارضه، نقشه را مجدداً تنظیم کن
        refreshMapView();
      }
      updateSelectedList();
    }
    
    function refreshMapView() {
      // تنظیم view روی نقشه محلات و عوارض فعال
      try {
        const bounds = [];
        
        // اضافه کردن bounds نقشه محلات
        if (mainLayer && mainLayer.getBounds) {
          bounds.push(mainLayer.getBounds());
        }
        
        // اضافه کردن bounds عوارض فعال (فقط آنهایی که روی نقشه هستند)
        Object.keys(featureLayersMap).forEach(function(featureId) {
          // فقط عوارضی که در selectedFeatures هستند و روی نقشه هستند
          if (selectedFeatures.has(featureId)) {
            const layer = featureLayersMap[featureId];
            if (layer && map.hasLayer(layer) && layer.getBounds) {
              try {
                bounds.push(layer.getBounds());
              } catch (e) {
                console.warn('Error getting bounds for feature:', featureId, e);
              }
            }
          }
        });
        
        // تنظیم view
        if (bounds.length > 0) {
          let combinedBounds = bounds[0];
          for (let i = 1; i < bounds.length; i++) {
            combinedBounds = combinedBounds.extend(bounds[i]);
          }
          map.fitBounds(combinedBounds, { padding: [50, 50], maxZoom: 16 });
        } else if (mainLayer && mainLayer.getBounds) {
          // اگر فقط نقشه محلات است
          map.fitBounds(mainLayer.getBounds(), { padding: [20, 20] });
        }
      } catch (err) {
        console.warn('Cannot refresh map view:', err);
      }
    }
    
    function loadFeatureOnMap(featureId) {
      // اگر قبلاً بارگذاری شده و روی نقشه است، نیازی به بارگذاری مجدد نیست
      if (featureLayersMap[featureId] && map.hasLayer(featureLayersMap[featureId])) {
        return Promise.resolve();
      }
      
      // اگر لایه وجود دارد اما از نقشه حذف شده، دوباره اضافه کن
      if (featureLayersMap[featureId] && !map.hasLayer(featureLayersMap[featureId])) {
        featureLayersMap[featureId].addTo(map);
        if (featureLayersMap[featureId].bringToFront) {
          featureLayersMap[featureId].bringToFront();
        }
        return Promise.resolve();
      }
      
      console.log('Loading feature:', featureId);
      
      return fetch(`/api/features/${featureId}`)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data.success && data.geojson) {
            let geojsonData = data.geojson;
            
            // اگر geojson یک string است، parse کن
            if (typeof geojsonData === 'string') {
              try {
                geojsonData = JSON.parse(geojsonData);
              } catch (e) {
                console.error('Error parsing GeoJSON string:', e);
                return;
              }
            }
            
            if (!geojsonData || !geojsonData.type) {
              console.error('Invalid GeoJSON data');
              return;
            }
            
            const featureLayer = L.geoJSON(geojsonData, {
              pointToLayer: function(feature, latlng) {
                return L.circleMarker(latlng, {
                  radius: 10,
                  fillColor: '#ff0000',
                  color: '#cc0000',
                  weight: 3,
                  opacity: 1,
                  fillOpacity: 0.9,
                  zIndex: 1000
                });
              },
              style: function(feature) {
                return {
                  color: '#ff0000',
                  weight: 4,
                  opacity: 0.8,
                  fillOpacity: 0.5,
                  fillColor: '#ff6b6b',
                  zIndex: 1000
                };
              },
              onEachFeature: function(feature, layer) {
                if (feature.properties) {
                  const props = feature.properties;
                  const popupItems = [];
                  
                  const nameFields = ['name', 'نام', 'title', 'عنوان', 'shop', 'فروشگاه', 'store'];
                  let name = null;
                  for (const field of nameFields) {
                    for (const key in props) {
                      if (key.toLowerCase().includes(field.toLowerCase())) {
                        name = props[key];
                        break;
                      }
                    }
                    if (name) break;
                  }
                  
                  if (name) {
                    popupItems.push(`<strong style="font-size: 1.1em; color: #2a9d8f;">${name}</strong>`);
                  }
                  
                  for (const key in props) {
                    if (key.toLowerCase() !== 'geometry' && key.toLowerCase() !== 'tootapp_url') {
                      const value = props[key];
                      if (value !== undefined && value !== null && String(value).trim() !== '') {
                        let skip = false;
                        for (const field of nameFields) {
                          if (key.toLowerCase().includes(field.toLowerCase())) {
                            skip = true;
                            break;
                          }
                        }
                        if (!skip) {
                          popupItems.push(`<strong>${key}:</strong> ${String(value).trim()}`);
                        }
                      }
                    }
                  }
                  
                  // اضافه کردن لینک توت‌اپ به صورت فارسی (استفاده از لینک هر عارضه)
                  const tootappUrl = props.tootapp_url || 'https://tootapp.ir/join/';
                  const displayUrl = tootappUrl.startsWith('http') ? tootappUrl : `https://${tootappUrl}`;
                  popupItems.push(`<strong>پیوست به گروه توت‌اپ:</strong> <a href="${displayUrl}" target="_blank" style="color: #007bff; text-decoration: underline;">پیوند به توت</a>`);
                  
                  if (popupItems.length > 0) {
                    layer.bindPopup(popupItems.join('<br/>'));
                  }
                }
              }
            });
            
            // اضافه کردن featureId به لایه برای شناسایی بعدی
            featureLayer.featureId = featureId;
            
            featureLayer.addTo(map);
            if (featureLayer.bringToFront) {
              featureLayer.bringToFront();
            }
            
            // ذخیره لایه برای حذف بعدی
            featureLayersMap[featureId] = featureLayer;
            
            // view در تابع refreshMapView تنظیم می‌شود
          }
        })
        .catch(error => {
          console.error('Error loading feature:', error);
        });
    }
    
    function removeFeatureFromMap(featureId) {
      console.log('Attempting to remove feature:', featureId);
      
      let removed = false;
      
      // روش 1: استفاده از featureLayersMap
      if (featureLayersMap[featureId]) {
        const layer = featureLayersMap[featureId];
        console.log('Layer found in featureLayersMap:', layer);
        
        // حذف تمام لایه‌های داخلی (برای FeatureCollection)
        if (layer.eachLayer) {
          layer.eachLayer(function(innerLayer) {
            if (map.hasLayer(innerLayer)) {
              map.removeLayer(innerLayer);
              console.log('Removed inner layer');
            }
          });
        }
        
        // حذف لایه اصلی از نقشه
        if (map.hasLayer(layer)) {
          map.removeLayer(layer);
          removed = true;
          console.log('Feature layer removed from map (method 1):', featureId);
        }
      }
      
      // روش 2: جستجو در تمام لایه‌های نقشه
      if (!removed) {
        map.eachLayer(function(l) {
          // بررسی لایه‌های GeoJSON (نه tile layer و نه mainLayer)
          if (l instanceof L.GeoJSON && l !== mainLayer && !(l instanceof L.TileLayer)) {
            // بررسی featureId
            if (l.featureId === featureId) {
              // حذف تمام لایه‌های داخلی
              if (l.eachLayer) {
                l.eachLayer(function(innerLayer) {
                  if (map.hasLayer(innerLayer)) {
                    map.removeLayer(innerLayer);
                  }
                });
              }
              // حذف لایه اصلی
              if (map.hasLayer(l)) {
                map.removeLayer(l);
                removed = true;
                console.log('Feature layer removed from map (method 2):', featureId);
              }
            }
          }
        });
      }
      
      // حذف از featureLayersMap (اما لایه را نگه دار برای اضافه کردن دوباره)
      // featureLayersMap[featureId] را نگه می‌داریم تا بتوان دوباره اضافه کرد
      
      if (removed) {
        console.log('Feature successfully removed:', featureId);
      } else {
        console.warn('Feature layer not found or could not be removed:', featureId);
      }
    }
    
    function updateSelectedList() {
      const selectedDiv = document.getElementById('selected-features');
      const selectedList = document.getElementById('selected-list');
      
      if (selectedFeatures.size > 0) {
        selectedDiv.style.display = 'block';
        selectedList.innerHTML = Array.from(selectedFeatures).map(id => {
          const toggleBtn = document.getElementById(`toggle-${id}`);
          const name = toggleBtn ? toggleBtn.previousSibling.textContent.trim() : id;
          return `<span style="display: inline-block; background: #e3f2fd; padding: 0.25rem 0.5rem; border-radius: 4px; margin: 0.25rem;">${name}</span>`;
        }).join('');
      } else {
        selectedDiv.style.display = 'none';
      }
    }

  </script>
</body>
</html>
"""


EDIT_NEIGHBORHOODS_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa">
<head>
  <meta charset="utf-8" />
  <title>ویرایش محلات</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body { font-family: sans-serif; background: #f4f6f8; margin: 0; padding: 0; direction: rtl; }
    header { padding: 1.5rem; text-align: center; background: #1f4e5f; color: #fff; }
    main { max-width: 1400px; margin: 1.5rem auto; padding: 0 1rem 2rem; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
    button { padding: 0.75rem 1.5rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-left: 0.5rem; }
    button.back { background: #6c757d; }
    button.save { background: #28a745; }
    button.cancel { background: #6c757d; }
    .error { color: #d62828; margin-top: 0.75rem; padding: 0.5rem; background: #f8d7da; border-radius: 6px; }
    .success { color: #28a745; margin-top: 0.75rem; padding: 0.5rem; background: #d4edda; border-radius: 6px; }
    #map { width: 100%; height: 600px; border-radius: 12px; margin-bottom: 1.5rem; }
    .edit-form { display: none; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin-top: 1rem; }
    .edit-form.active { display: block; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; font-weight: bold; margin-bottom: 0.5rem; color: #1f4e5f; }
    .form-group input, .form-group textarea { width: 100%; padding: 0.75rem; border: 1px solid #dde3ea; border-radius: 8px; box-sizing: border-box; }
    .form-actions { margin-top: 1.5rem; display: flex; gap: 0.5rem; }
    .selected-neighborhood { background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
  </style>
</head>
<body>
  <header>
    <h1>ویرایش محلات</h1>
    <p>{{ map_name }}</p>
  </header>
  <main>
    <div class="card">
      <div style="margin-bottom: 1rem;">
        <a href="/admin" style="text-decoration: none;">
          <button type="button" class="back">← بازگشت به پنل ادمین</button>
        </a>
      </div>
      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}
      {% if success %}
        <div class="success">{{ success }}</div>
      {% endif %}
      <h3>راهنما: روی محله مورد نظر کلیک کنید تا مشخصات آن را ویرایش کنید</h3>
      <div id="map"></div>
      <div id="selectedNeighborhood" class="selected-neighborhood" style="display: none;">
        <h4 id="selectedName">محله انتخاب شده</h4>
        <p id="selectedInfo" style="color: #6c757d; font-size: 0.9rem;"></p>
      </div>
      <div id="editForm" class="edit-form">
        <h3>ویرایش مشخصات محله</h3>
        <form id="neighborhoodEditForm">
          <input type="hidden" id="editFeatureId" />
          <input type="hidden" id="editOriginalName" />
          <div class="form-group">
            <label>نام محله:</label>
            <input type="text" id="editName" />
          </div>
          <div class="form-group">
            <label>نام انگلیسی:</label>
            <input type="text" id="editEnglishName" />
          </div>
          <div class="form-group">
            <label>منطقه:</label>
            <input type="text" id="editDistrict" />
          </div>
          <div class="form-group">
            <label>شهر:</label>
            <input type="text" id="editCity" />
          </div>
          <div class="form-group">
            <label>جمعیت:</label>
            <input type="number" id="editPopulation" />
          </div>
          <div class="form-group">
            <label>مساحت (متر مربع):</label>
            <input type="number" id="editArea" />
          </div>
          <div class="form-actions">
            <button type="submit" class="save">ذخیره تغییرات</button>
            <button type="button" class="cancel" onclick="cancelEdit()">انصراف</button>
          </div>
        </form>
      </div>
    </div>
  </main>
  <script>
    const geojsonData = {{ geojson|safe if geojson else 'null' }};
    const existingEdits = {{ edits|safe if edits else '{}' }};
    let map = null;
    let selectedLayer = null;
    let selectedFeature = null;
    const layers = [];
    
    // تابع استخراج نام محله (مشابه JavaScript در sidebar)
    function getNeighborhoodName(props) {
      const priorityFields = ['NAME_NEW', 'Name', 'NAME', 'name', 'mahalle', 'MAHALLE', 'Mahalle',
                             'neighborhood', 'NEIGHBORHOOD', 'Neighborhood', 'neighbourhood', 
                             'NEIGHBOURHOOD', 'Neighbourhood', 'محله', 'نام محله',
                             'title', 'TITLE', 'Title', 'label', 'LABEL', 'Label'];
      
      for (const fieldName of priorityFields) {
        if (props.hasOwnProperty(fieldName)) {
          const value = props[fieldName];
          if (value !== undefined && value !== null && String(value).trim() !== '') {
            return String(value).trim();
          }
        }
      }
      
      for (const fieldName of priorityFields) {
        for (const key in props) {
          if (key.toLowerCase() === fieldName.toLowerCase()) {
            const value = props[key];
            if (value !== undefined && value !== null && String(value).trim() !== '') {
              return String(value).trim();
            }
          }
        }
      }
      
      return 'نامشخص';
    }
    
    // تابع ساخت feature_id (مشابه get_feature_identifier در Python)
    function getFeatureId(feature) {
      const props = feature.properties || {};
      
      // اولویت اول: فیلدهای ID ثابت که تغییر نمی‌کنند
      if (props.feature_id) return props.feature_id;
      if (props.id) return String(props.id);
      if (props.gid) return String(props.gid);
      if (props.OBJECTID) return String(props.OBJECTID);
      
      // اولویت دوم: ساخت hash از geometry (ثابت است و تغییر نمی‌کند)
      if (feature.geometry) {
        // استفاده از یک hash ساده برای geometry
        const geometryStr = JSON.stringify(feature.geometry);
        // MD5 hash (ساده شده - در production از crypto استفاده کنید)
        let hash = 0;
        for (let i = 0; i < geometryStr.length; i++) {
          const char = geometryStr.charCodeAt(i);
          hash = ((hash << 5) - hash) + char;
          hash = hash & hash; // Convert to 32bit integer
        }
        return Math.abs(hash).toString(36); // تبدیل به base36 برای کوتاه‌تر شدن
      }
      
      // اولویت سوم: ساخت شناسه از ترکیب فیلدهای نام
      const keywords = ['name', 'mahalle', 'district', 'region'];
      const parts = [];
      for (const key in props) {
        const keyLower = key.toLowerCase();
        if (keywords.some(kw => keyLower.includes(kw))) {
          const value = props[key];
          if (value && String(value).trim()) {
            parts.push(key + ':' + String(value).trim());
          }
        }
      }
      
      if (parts.length > 0) {
        return parts.join('|');
      }
      
      return 'unknown';
    }
    
    // مقداردهی اولیه نقشه
    window.addEventListener('DOMContentLoaded', function() {
      map = L.map('map').setView([32.0, 53.0], 5);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      
      if (geojsonData && geojsonData.features) {
        const geoJsonLayer = L.geoJSON(geojsonData, {
          style: function() {
            return { color: '#111', weight: 2, fillOpacity: 0.1, zIndex: 100 };
          },
          onEachFeature: function(feature, layer) {
            const props = feature.properties || {};
            const name = getNeighborhoodName(props);
            
            layer.on('click', function() {
              // حذف highlight قبلی
              if (selectedLayer) {
                selectedLayer.setStyle({ color: '#111', weight: 2, fillOpacity: 0.1 });
              }
              
              // highlight محله انتخاب شده
              layer.setStyle({ color: '#ff0000', weight: 4, fillOpacity: 0.3 });
              selectedLayer = layer;
              selectedFeature = feature;
              
              // نمایش اطلاعات محله
              const featureId = getFeatureId(feature);
              const originalName = getNeighborhoodName(props);
              
              document.getElementById('selectedName').textContent = originalName;
              document.getElementById('selectedInfo').textContent = `شناسه: ${featureId}`;
              document.getElementById('selectedNeighborhood').style.display = 'block';
              
              // بارگذاری ویرایش‌های موجود
              // جستجوی ویرایش‌ها - باید با تمام کلیدهای موجود مقایسه کنیم
              let currentEdits = {};
              const editKeyString = featureId + '_' + originalName;
              
              // جستجو در تمام ویرایش‌های موجود
              for (const key in existingEdits) {
                const editData = existingEdits[key];
                if (!editData) continue;
                if (editData.feature_id === featureId) { // تطبیق فقط بر اساس feature_id
                  currentEdits = editData.edits || {};
                  break;
                }
              }
              
              // پر کردن فرم
              document.getElementById('editFeatureId').value = featureId;
              document.getElementById('editOriginalName').value = originalName;
              document.getElementById('editName').value = currentEdits.name || originalName;
              document.getElementById('editEnglishName').value = currentEdits.english_name || props.english_name || props.name_en || '';
              document.getElementById('editDistrict').value = currentEdits.district || props.district || props.region || '';
              document.getElementById('editCity').value = currentEdits.city || props.city || '';
              document.getElementById('editPopulation').value = currentEdits.population || props.population || props.pop || '';
              document.getElementById('editArea').value = currentEdits.area || props.area || '';
              
              // نمایش فرم
              document.getElementById('editForm').classList.add('active');
              
              // زوم به محله
              if (layer.getBounds) {
                map.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 16 });
              }
            });
          }
        }).addTo(map);
        
        // تنظیم view برای نمایش تمام محلات
        setTimeout(() => {
          if (geoJsonLayer.getBounds) {
            map.fitBounds(geoJsonLayer.getBounds(), { padding: [50, 50] });
          }
        }, 100);
      }
    });
    
    // مدیریت فرم
    document.getElementById('neighborhoodEditForm').addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const featureId = document.getElementById('editFeatureId').value;
      const originalName = document.getElementById('editOriginalName').value;
      const edits = {
        name: document.getElementById('editName').value.trim(),
        english_name: document.getElementById('editEnglishName').value.trim(),
        district: document.getElementById('editDistrict').value.trim(),
        city: document.getElementById('editCity').value.trim(),
        population: document.getElementById('editPopulation').value.trim(),
        area: document.getElementById('editArea').value.trim()
      };
      
      try {
        const response = await fetch('/admin/neighborhoods/edit/{{ map_id }}/save', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            feature_id: featureId,
            original_name: originalName,
            edits: edits
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          alert('✓ ' + result.message);
          window.location.reload();
        } else {
          alert('✗ ' + (result.error || 'خطا در ذخیره'));
        }
      } catch (error) {
        alert('✗ خطا در ذخیره: ' + error.message);
      }
    });
    
    function cancelEdit() {
      document.getElementById('editForm').classList.remove('active');
      document.getElementById('selectedNeighborhood').style.display = 'none';
      if (selectedLayer) {
        selectedLayer.setStyle({ color: '#111', weight: 2, fillOpacity: 0.1 });
        selectedLayer = null;
      }
    }
  </script>
</body>
</html>
"""


# ========== Routes ==========

@app.route("/", methods=["GET"])
def index():
    """صفحه اصلی - نمایش لیست نقشه‌ها"""
    history = load_history()
    selected_map_id = request.args.get("map_id")
    geojson = None
    summary = None
    selected_features_geojson = []  # لیست عوارض انتخاب شده
    selected_feature_ids = []  # لیست feature_ids برای checkbox ها

    if selected_map_id:
        map_data = load_map_data(selected_map_id)
        if map_data:
            geojson = map_data.get("geojson")
            summary = map_data.get("summary")
            # اعمال ویرایش‌های محلات
            if geojson and geojson.get("features"):
                for feature in geojson.get("features", []):
                    props = feature.get("properties", {})
                    feature_id = get_feature_identifier(feature)
                    # ذخیره feature_id در properties برای استفاده بعدی
                    if feature_id:
                        props["feature_id"] = feature_id
                    original_name = props.get('NAME_NEW') or props.get('Name') or props.get('name') or 'نامشخص'
                    # اعمال ویرایش‌ها - باید قبل از JSON serialization انجام شود
                    props = apply_neighborhood_edits(props, selected_map_id, feature_id, original_name)
                    # به‌روزرسانی properties در feature
                    feature["properties"] = props
            # اتصال لینک‌های توت‌اپ (با استفاده از لینک‌های ذخیره شده)
            if geojson:
                _attach_tootapp_links(geojson, selected_map_id)
        
        # بارگذاری تمام عوارض مربوط به این نقشه (به صورت خودکار)
        try:
            index = load_features_index()
            all_features_for_map = [item for item in index if item.get("map_id") == selected_map_id]
            
            # بارگذاری GeoJSON تمام عوارض
            for feature_item in all_features_for_map:
                feature_id = feature_item.get("feature_id")
                if feature_id:
                    try:
                        feature_data = load_feature_data(feature_id)
                        if feature_data and feature_data.get("geojson"):
                            selected_features_geojson.append(feature_data.get("geojson"))
                            selected_feature_ids.append(feature_id)
                    except Exception as e:
                        # اگر خطایی در بارگذاری عارضه رخ داد، ادامه بده
                        print(f"Error loading feature {feature_id}: {e}")
                        continue
        except Exception as e:
            # اگر خطایی در بارگذاری index رخ داد، ادامه بده
            print(f"Error loading features index: {e}")
            selected_features_geojson = []
            selected_feature_ids = []

    return render_template_string(
        INDEX_TEMPLATE,
        history=history,
        selected_map_id=selected_map_id,
        geojson=json.dumps(geojson) if geojson else None,
        summary=summary,
        selected_features_geojson=[json.dumps(fg) for fg in selected_features_geojson] if selected_features_geojson else [],
        selected_feature_ids=selected_feature_ids,
    )


@app.route("/map/<map_id>")
def view_map(map_id: str):
    """مشاهده نقشه خاص"""
    # حفظ query string (feature_ids) در redirect
    feature_ids = request.args.get("feature_ids")
    if feature_ids:
        return redirect(url_for("index", map_id=map_id, feature_ids=feature_ids))
    return redirect(url_for("index", map_id=map_id))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """ورود کاربر"""
    if session.get("username"):
        return redirect(url_for("admin_panel"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            error = "لطفاً نام کاربری و رمز عبور را وارد کنید."
        elif verify_password(username, password):
            session["username"] = username
            session["role"] = get_user(username).get("role", "viewer")
            # به‌روزرسانی last_login
            users = load_users()
            for user in users:
                if user.get("username") == username:
                    user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
            save_users(users)
            return redirect(url_for("admin_panel"))
        else:
            error = "نام کاربری یا رمز عبور اشتباه است."

    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    """خروج کاربر"""
    session.pop("username", None)
    session.pop("role", None)
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    """پنل مدیریت - آپلود نقشه"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    # بررسی دسترسی
    if not has_permission("view"):
        return redirect(url_for("admin_login"))

    error = None
    success = None

    # بررسی پیام‌های query string
    if request.args.get("deleted") == "1":
        success = "نقشه با موفقیت حذف شد."
    elif request.args.get("error"):
        error = request.args.get("error")

    if request.method == "POST":
        # بررسی دسترسی upload
        if not has_permission("upload"):
            error = "شما دسترسی آپلود نقشه ندارید."
        else:
            file_obj = request.files.get("shapefile")
            map_name = request.form.get("map_name", "").strip()

            if not file_obj or not file_obj.filename:
                error = "لطفاً یک فایل انتخاب کنید."
            else:
                try:
                    geojson, summary = load_geojson(file_obj)
                    map_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    
                    # بررسی وجود نقشه قبلی با همان نام
                    final_map_name = map_name or file_obj.filename
                    old_map_id = find_duplicate_map(final_map_name, file_obj.filename)
                    
                    if old_map_id:
                        # انتقال لینک‌ها از نقشه قدیمی به جدید
                        transfer_links(old_map_id, map_id)
                        # حذف نقشه قدیمی (با حفظ لینک‌ها - که قبلاً منتقل شدند)
                        delete_map(old_map_id, keep_links=False)
                        success = f"نقشه با موفقیت آپلود شد و نقشه قبلی جایگزین شد! لینک‌های توت‌اپ حفظ شدند. شناسه: {map_id}"
                    else:
                        success = f"نقشه با موفقیت آپلود شد! شناسه: {map_id}"
                    
                    save_map_data(map_id, geojson, summary, file_obj.filename)

                    history = load_history()
                    history.insert(0, {
                        "map_id": map_id,
                        "map_name": final_map_name,
                        "original_filename": file_obj.filename,
                        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "feature_count": summary.get("feature_count", 0),
                    })
                    save_history(history)

                except ValueError as exc:
                    error = str(exc)

    history = load_history()
    current_username = session.get("username", "نامشخص")
    current_role = session.get("role", "viewer")
    current_role_name = ROLES.get(current_role, "نامشخص")
    has_manage_users = has_permission("manage_users")
    
    return render_template_string(
        ADMIN_TEMPLATE, 
        error=error, 
        success=success, 
        history=history,
        current_username=current_username,
        current_role_name=current_role_name,
        has_manage_users=has_manage_users
    )


@app.route("/admin/delete/<map_id>", methods=["POST"])
def admin_delete_map(map_id: str):
    """حذف نقشه از تاریخچه"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("delete"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی حذف نقشه ندارید")

    if delete_map(map_id):
        return redirect(url_for("admin_panel") + "?deleted=1")
    else:
        return redirect(url_for("admin_panel") + "?error=حذف نقشه با خطا مواجه شد")


@app.route("/admin/links/<map_id>", methods=["GET"])
def admin_manage_links(map_id: str):
    """مدیریت لینک‌های توت‌اپ برای یک نقشه"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_links"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت لینک‌ها ندارید")

    # بارگذاری داده‌های نقشه
    map_data = load_map_data(map_id)
    if not map_data:
        return redirect(url_for("admin_panel") + "?error=نقشه پیدا نشد")

    geojson = map_data.get("geojson")
    history = load_history()
    map_info = next((item for item in history if item.get("map_id") == map_id), None)
    map_name = map_info.get("map_name", map_info.get("original_filename", "نقشه")) if map_info else "نقشه"

    error = request.args.get("error")
    success = request.args.get("success")

    # آماده‌سازی لیست محلات برای نمایش
    neighborhoods = []
    saved_links = load_links(map_id)
    saved_logos = get_all_neighborhood_logos(map_id)  # فقط یک بار فراخوانی می‌شود
    
    if geojson and geojson.get("features"):
        for feature in geojson.get("features", []):
            props = feature.get("properties", {}).copy()  # کپی برای اعمال ویرایش‌ها
            feature_id = get_feature_identifier(feature)
            
            # اعمال ویرایش‌های محله
            original_name = props.get('NAME_NEW') or props.get('Name') or props.get('name') or 'نامشخص'
            props = apply_neighborhood_edits(props, map_id, feature_id, original_name)
            
            # پیدا کردن نام محله - استفاده از همان منطق JavaScript (getNeighborhoodName)
            name = None
            # اولویت اول: NAME_NEW
            priority_fields = ['NAME_NEW', 'Name', 'NAME', 'name', 'mahalle', 'MAHALLE', 'Mahalle',
                             'neighborhood', 'NEIGHBORHOOD', 'Neighborhood', 'neighbourhood', 
                             'NEIGHBOURHOOD', 'Neighbourhood', 'محله', 'نام محله',
                             'title', 'TITLE', 'Title', 'label', 'LABEL', 'Label']
            
            # ابتدا بررسی exact match
            for field_name in priority_fields:
                if field_name in props:
                    value = props[field_name]
                    if value and str(value).strip() and str(value).strip() != 'null' and str(value).strip() != 'None':
                        name = str(value).strip()
                        break
            
            # اگر پیدا نشد، بررسی case-insensitive
            if not name:
                for field_name in priority_fields:
                    field_lower = field_name.lower()
                    for key in props:
                        if key.lower() == field_lower:
                            value = props[key]
                            if value and str(value).strip() and str(value).strip() != 'null' and str(value).strip() != 'None':
                                name = str(value).strip()
                                break
                    if name:
                        break
            
            # اگر هنوز پیدا نشد، جستجوی partial match (کلمه کلیدی در نام فیلد)
            if not name:
                keywords = ['name', 'mahalle', 'neighborhood', 'neighbourhood', 'محله']
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    for key in props:
                        key_lower = key.lower()
                        if keyword_lower in key_lower or key_lower in keyword_lower:
                            value = props[key]
                            if value and str(value).strip() and str(value).strip() != 'null' and str(value).strip() != 'None':
                                # بررسی که مقدار عددی خالص نباشد
                                try:
                                    num_value = float(str(value))
                                    if num_value < 0 or num_value > 1000000:  # احتمالاً ID است نه نام
                                        continue
                                except (ValueError, TypeError):
                                    pass
                                name = str(value).strip()
                                break
                    if name:
                        break
            
            if not name:
                name = "نامشخص"
            
            # اطلاعات اضافی
            info_parts = []
            info_keywords = ['name', 'mahalle', 'district', 'region']
            for key in props:
                key_lower = key.lower()
                if any(kw in key_lower for kw in info_keywords) and str(props[key]).strip():
                    info_parts.append(f"{key}: {props[key]}")
            info = " | ".join(info_parts[:3]) if info_parts else "بدون اطلاعات"
            
            # لینک ذخیره شده
            link = saved_links.get(feature_id, "") if feature_id else ""
            
            # لوگوی ذخیره شده - جستجوی دقیق و case-insensitive
            logo_filename = ""
            name_normalized = name.strip()
            # جستجوی exact match
            if name_normalized in saved_logos:
                logo_filename = saved_logos[name_normalized]
            else:
                # جستجوی case-insensitive
                for saved_name, saved_logo in saved_logos.items():
                    if saved_name.strip().lower() == name_normalized.lower():
                        logo_filename = saved_logo
                        break
            
            neighborhoods.append({
                "id": feature_id or f"feature_{len(neighborhoods)}",
                "name": name,
                "info": info,
                "link": link,
                "logo_filename": logo_filename
            })

    return render_template_string(
        MANAGE_LINKS_TEMPLATE,
        map_id=map_id,
        map_name=map_name,
        neighborhoods=neighborhoods,
        error=error,
        success=success
    )


@app.route("/admin/links/<map_id>/save", methods=["POST"])
def admin_save_single_link(map_id: str):
    """ذخیره لینک یک محله خاص"""
    if not session.get("username"):
        return json.dumps({"success": False, "error": "لطفاً وارد شوید"}), 403, {"Content-Type": "application/json"}
    
    if not has_permission("manage_links"):
        return json.dumps({"success": False, "error": "دسترسی غیرمجاز"}), 403, {"Content-Type": "application/json"}

    feature_id = request.form.get("feature_id", "").strip()
    link_value = request.form.get("link", "").strip()

    if not feature_id:
        return json.dumps({"success": False, "error": "شناسه محله نامعتبر است"}), 400, {"Content-Type": "application/json"}

    try:
        # بارگذاری لینک‌های موجود
        links = load_links(map_id)

        if link_value:
            # حذف tootapp.ir/join/ یا tootapp.ir/ اگر کاربر آن را وارد کرده
            if link_value.startswith("tootapp.ir/join/"):
                link_value = link_value.replace("tootapp.ir/join/", "")
            elif link_value.startswith("tootapp.ir/"):
                link_value = link_value.replace("tootapp.ir/", "")
            if link_value.startswith("https://tootapp.ir/join/"):
                link_value = link_value.replace("https://tootapp.ir/join/", "")
            elif link_value.startswith("https://tootapp.ir/"):
                link_value = link_value.replace("https://tootapp.ir/", "")
            if link_value.startswith("http://tootapp.ir/join/"):
                link_value = link_value.replace("http://tootapp.ir/join/", "")
            elif link_value.startswith("http://tootapp.ir/"):
                link_value = link_value.replace("http://tootapp.ir/", "")
            links[feature_id] = link_value
        elif feature_id in links:
            # اگر لینک خالی شد، حذف می‌کنیم
            del links[feature_id]

        save_links(map_id, links)
        return json.dumps({"success": True, "message": "لینک با موفقیت ذخیره شد"}), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}), 500, {"Content-Type": "application/json"}


@app.route("/admin/neighborhoods/<map_id>/upload-logo", methods=["POST"])
def admin_upload_neighborhood_logo(map_id: str):
    """آپلود لوگو برای یک محله"""
    if not session.get("username"):
        return jsonify({"success": False, "error": "نیاز به ورود"}), 401
    
    if not has_permission("manage_links"):
        return jsonify({"success": False, "error": "شما دسترسی ندارید"}), 403
    
    if 'logo' not in request.files:
        return jsonify({"success": False, "error": "فایل لوگو ارسال نشد"}), 400
    
    logo_file = request.files['logo']
    neighborhood_name = request.form.get('neighborhood_name', '').strip()
    
    if not neighborhood_name:
        return jsonify({"success": False, "error": "نام محله مشخص نشد"}), 400
    
    if logo_file.filename == '':
        return jsonify({"success": False, "error": "فایلی انتخاب نشد"}), 400
    
    # بررسی نوع فایل
    filename = logo_file.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"success": False, "error": f"نوع فایل مجاز نیست. انواع مجاز: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"}), 400
    
    try:
        # نرمال‌سازی نام محله (حذف فاصله‌های اضافی)
        neighborhood_name_normalized = neighborhood_name.strip()
        
        # ساخت نام فایل منحصر به فرد
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = get_neighborhood_key(map_id, neighborhood_name_normalized)
        # استخراج نام فایل بدون پسوند و امن کردن آن
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        safe_base_name = secure_filename(base_name)
        # اضافه کردن پسوند به صورت جداگانه برای اطمینان از حفظ آن
        logo_filename = f"{key}_{timestamp}_{safe_base_name}.{ext}"
        logo_path = LOGO_DIR / logo_filename
        
        # حذف لوگوی قبلی اگر وجود داشته باشد (با نام نرمال‌سازی شده)
        old_logo = load_neighborhood_logo(map_id, neighborhood_name_normalized)
        if old_logo:
            old_logo_path = LOGO_DIR / old_logo
            if old_logo_path.exists():
                try:
                    old_logo_path.unlink()
                except Exception:
                    pass
        
        # ذخیره فایل
        logo_file.save(logo_path)
        
        # ذخیره اطلاعات در JSON با نام نرمال‌سازی شده
        save_neighborhood_logo(map_id, neighborhood_name_normalized, logo_filename)
        
        return jsonify({
            "success": True,
            "message": "لوگو با موفقیت آپلود شد",
            "logo_filename": logo_filename
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": f"خطا در آپلود: {str(e)}"}), 500


@app.route("/uploads/logos/<filename>")
def serve_logo(filename: str):
    """سرو کردن فایل‌های لوگو - با پشتیبانی از فایل‌های قدیمی"""
    from flask import send_from_directory
    
    logo_path = LOGO_DIR / filename
    if logo_path.exists() and logo_path.is_file():
        return send_from_directory(str(LOGO_DIR), filename)
    
    # اگر فایل پیدا نشد، برای فایل‌های قدیمی که پسوند ندارند، جستجو کنیم
    # بعضی فایل‌های قدیمی ممکن است پسوند نداشته باشند یا پسوندشان تغییر کرده باشد
    
    # 1. جستجو برای فایل‌هایی که پسوند در انتهای نامشان است (مثل _jpg بدون نقطه)
    # ابتدا بررسی کنیم که آیا فایل با اضافه کردن .jpg به انتهای نام وجود دارد
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        possible_filename = f"{filename}.{ext}"
        possible_path = LOGO_DIR / possible_filename
        if possible_path.exists() and possible_path.is_file():
            return send_from_directory(str(LOGO_DIR), possible_filename)
    
    # اگر پیدا نشد، بررسی کنیم که آیا نام فایل به _jpg ختم می‌شود
    if '_' in filename:
        # اگر نام فایل به _jpg یا _png و غیره ختم می‌شود
        for ext in ALLOWED_IMAGE_EXTENSIONS:
            if filename.endswith(f'_{ext}'):
                # تبدیل _jpg به .jpg - اما فایل واقعی ممکن است _jpg.jpg باشد
                # پس ابتدا بررسی کنیم که آیا فایل با همان نام + .ext وجود دارد
                possible_filename = f"{filename}.{ext}"
                possible_path = LOGO_DIR / possible_filename
                if possible_path.exists() and possible_path.is_file():
                    return send_from_directory(str(LOGO_DIR), possible_filename)
                
                # اگر پیدا نشد، تبدیل _jpg به .jpg
                base_name = filename.rsplit(f'_{ext}', 1)[0]
                possible_filename = f"{base_name}.{ext}"
                possible_path = LOGO_DIR / possible_filename
                if possible_path.exists() and possible_path.is_file():
                    return send_from_directory(str(LOGO_DIR), possible_filename)
    
    # 2. جستجو برای فایل‌هایی که پسوند ندارند (فایل قدیمی)
    if '.' not in filename:
        # جستجو با اضافه کردن پسوندهای مختلف
        for ext in ALLOWED_IMAGE_EXTENSIONS:
            possible_filename = f"{filename}.{ext}"
            possible_path = LOGO_DIR / possible_filename
            if possible_path.exists() and possible_path.is_file():
                return send_from_directory(str(LOGO_DIR), possible_filename)
    
    # 3. جستجو برای فایل‌هایی که بخشی از نامشان مشابه است
    if '_' in filename:
        # استخراج بخش اصلی نام فایل (قبل از آخرین _)
        parts = filename.rsplit('_', 1)
        if len(parts) == 2:
            base_part = parts[0]
            # جستجوی فایل‌های مشابه با پسوندهای مختلف
            for ext in ALLOWED_IMAGE_EXTENSIONS:
                possible_filename = f"{base_part}.{ext}"
                possible_path = LOGO_DIR / possible_filename
                if possible_path.exists() and possible_path.is_file():
                    return send_from_directory(str(LOGO_DIR), possible_filename)
            
            # همچنین جستجو برای فایل‌هایی که پسوند در نامشان است (مثل _jpg)
            for ext in ALLOWED_IMAGE_EXTENSIONS:
                possible_filename = f"{filename}.{ext}"
                possible_path = LOGO_DIR / possible_filename
                if possible_path.exists() and possible_path.is_file():
                    return send_from_directory(str(LOGO_DIR), possible_filename)
    
    # 4. جستجوی فایل‌هایی که با نام فایل شروع می‌شوند (برای فایل‌های قدیمی)
    if LOGO_DIR.exists():
        for ext in ALLOWED_IMAGE_EXTENSIONS:
            # جستجو برای فایل‌هایی که با filename شروع می‌شوند
            for logo_file in LOGO_DIR.glob(f"{filename}*"):
                if logo_file.is_file() and logo_file.suffix.lower() in [f'.{e}' for e in ALLOWED_IMAGE_EXTENSIONS]:
                    return send_from_directory(str(LOGO_DIR), logo_file.name)
    
    return "فایل پیدا نشد", 404


@app.route("/api/neighborhood-logo")
def api_get_neighborhood_logo():
    """دریافت لوگوی یک محله"""
    map_id = request.args.get('map_id', '').strip()
    neighborhood_name = request.args.get('neighborhood_name', '').strip()
    
    if not map_id or not neighborhood_name:
        return jsonify({"success": False, "error": "پارامترهای لازم ارسال نشد"}), 400
    
    try:
        logo_filename = load_neighborhood_logo(map_id, neighborhood_name)
        if logo_filename:
            # بررسی وجود فایل (با پسوند یا بدون پسوند)
            logo_path = LOGO_DIR / logo_filename
            if logo_path.exists() and logo_path.is_file():
                return jsonify({
                    "success": True,
                    "logo_filename": logo_filename
                })
            else:
                # فایل JSON وجود دارد اما فایل عکس نیست - جستجو برای فایل‌های قدیمی
                # جستجو برای فایل‌هایی که با این نام شروع می‌شوند
                found_file = None
                if LOGO_DIR.exists():
                    # اگر نام فایل پسوند ندارد، جستجو با پسوندهای مختلف
                    if '.' not in logo_filename:
                        for ext in ALLOWED_IMAGE_EXTENSIONS:
                            possible_path = LOGO_DIR / f"{logo_filename}.{ext}"
                            if possible_path.exists() and possible_path.is_file():
                                found_file = possible_path.name
                                break
                    # اگر نام فایل به _jpg ختم می‌شود، تبدیل به .jpg
                    elif logo_filename.endswith('_jpg') or logo_filename.endswith('_jpeg') or logo_filename.endswith('_png'):
                        for ext in ALLOWED_IMAGE_EXTENSIONS:
                            if logo_filename.endswith(f'_{ext}'):
                                base_name = logo_filename.rsplit(f'_{ext}', 1)[0]
                                possible_path = LOGO_DIR / f"{base_name}.{ext}"
                                if possible_path.exists() and possible_path.is_file():
                                    found_file = possible_path.name
                                    break
                    # جستجو برای فایل‌هایی که با این نام شروع می‌شوند
                    if not found_file:
                        for logo_file in LOGO_DIR.glob(f"{logo_filename}*"):
                            if logo_file.is_file() and logo_file.suffix.lower() in [f'.{e}' for e in ALLOWED_IMAGE_EXTENSIONS]:
                                found_file = logo_file.name
                                break
                
                if found_file:
                    # به‌روزرسانی JSON با نام فایل صحیح
                    try:
                        # پیدا کردن فایل JSON مربوطه و به‌روزرسانی آن
                        for json_file in LOGO_DIR.glob("*.json"):
                            try:
                                with open(json_file, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                if data.get("logo_filename") == logo_filename and data.get("map_id") == map_id:
                                    data["logo_filename"] = found_file
                                    with open(json_file, 'w', encoding='utf-8') as f:
                                        json.dump(data, f, ensure_ascii=False, indent=2)
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
                    
                    return jsonify({
                        "success": True,
                        "logo_filename": found_file
                    })
                else:
                    # فایل JSON وجود دارد اما فایل عکس نیست
                    all_logos = get_all_neighborhood_logos(map_id)
                    return jsonify({
                        "success": False,
                        "message": f"فایل لوگو پیدا نشد: {logo_filename}",
                        "requested_name": neighborhood_name,
                        "logo_filename_in_db": logo_filename,
                        "available_logos": list(all_logos.keys()) if all_logos else []
                    })
        else:
            # اگر پیدا نشد، لیست تمام لوگوهای موجود را برای debug برگردان
            all_logos = get_all_neighborhood_logos(map_id)
            return jsonify({
                "success": False,
                "message": "لوگویی برای این محله یافت نشد",
                "requested_name": neighborhood_name,
                "requested_map_id": map_id,
                "available_logos": list(all_logos.keys()) if all_logos else [],
                "available_logos_count": len(all_logos) if all_logos else 0
            })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/admin/neighborhoods/edit/<map_id>", methods=["GET"])
def admin_edit_neighborhoods(map_id: str):
    """صفحه ویرایش محلات - با نقشه تعاملی"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_links"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی ویرایش محلات ندارید")
    
    # بارگذاری داده‌های نقشه
    map_data = load_map_data(map_id)
    if not map_data:
        return redirect(url_for("admin_panel") + "?error=نقشه پیدا نشد")
    
    geojson = map_data.get("geojson")
    history = load_history()
    map_info = next((item for item in history if item.get("map_id") == map_id), None)
    map_name = map_info.get("map_name", map_info.get("original_filename", "نقشه")) if map_info else "نقشه"
    
    error = request.args.get("error")
    success = request.args.get("success")
    
    # بارگذاری ویرایش‌های موجود
    edits = load_neighborhood_edits(map_id)
    
    return render_template_string(
        EDIT_NEIGHBORHOODS_TEMPLATE,
        map_id=map_id,
        map_name=map_name,
        geojson=json.dumps(geojson) if geojson else None,
        error=error,
        success=success,
        edits=json.dumps(edits)
    )


@app.route("/admin/neighborhoods/edit/<map_id>/save", methods=["POST"])
def admin_save_neighborhood_edit(map_id: str):
    """ذخیره ویرایش یک محله"""
    if not session.get("username"):
        return jsonify({"success": False, "error": "نیاز به ورود"}), 401
    
    if not has_permission("manage_links"):
        return jsonify({"success": False, "error": "شما دسترسی ندارید"}), 403
    
    try:
        data = request.get_json()
        feature_id = data.get("feature_id", "").strip()
        original_name = data.get("original_name", "").strip()
        edits = data.get("edits", {})
        
        if not feature_id:
            return jsonify({"success": False, "error": "شناسه محله مشخص نشد"}), 400
        
        # بارگذاری ویرایش‌های موجود
        all_edits = load_neighborhood_edits(map_id)
        
        # ساخت کلید
        edit_key = get_neighborhood_edit_key(feature_id, original_name)
        
        # ذخیره ویرایش‌ها
        all_edits[edit_key] = {
            "feature_id": feature_id,
            "original_name": original_name,
            "edits": edits,
            "updated_at": datetime.now().isoformat()
        }
        
        save_neighborhood_edits(map_id, all_edits)
        
        # بررسی که ویرایش درست ذخیره شد
        saved_edits = load_neighborhood_edits(map_id)
        
        return jsonify({
            "success": True,
            "message": "ویرایش‌ها با موفقیت ذخیره شد",
            "feature_id": feature_id,
            "edit_key": edit_key,
            "edits_saved": edit_key in saved_edits
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/admin/users", methods=["GET"])


@app.route("/admin/users", methods=["GET"])
def admin_manage_users():
    """پنل مدیریت کاربران (فقط برای admin)"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_users"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت کاربران ندارید")
    
    users = load_users()
    current_username = session.get("username", "")
    role_names = ROLES
    
    error = request.args.get("error")
    success = request.args.get("success")
    
    return render_template_string(
        MANAGE_USERS_TEMPLATE,
        users=users,
        current_username=current_username,
        role_names=role_names,
        error=error,
        success=success
    )


@app.route("/admin/users/create", methods=["POST"])
def admin_create_user():
    """ایجاد کاربر جدید (فقط برای admin)"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_users"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت کاربران ندارید")
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "viewer")
    
    success, message = create_user(username, password, role)
    
    if success:
        return redirect(url_for("admin_manage_users") + f"?success={message}")
    else:
        return redirect(url_for("admin_manage_users") + f"?error={message}")


@app.route("/admin/users/change-password", methods=["POST"])
def admin_change_password():
    """تغییر رمز عبور کاربر (فقط برای admin)"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_users"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت کاربران ندارید")
    
    username = request.form.get("username", "").strip()
    new_password = request.form.get("new_password", "")
    
    success, message = update_user_password(username, new_password)
    
    if success:
        return redirect(url_for("admin_manage_users") + f"?success={message}")
    else:
        return redirect(url_for("admin_manage_users") + f"?error={message}")


@app.route("/admin/users/delete/<username>", methods=["POST"])
def admin_delete_user(username: str):
    """حذف کاربر (فقط برای admin)"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_users"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت کاربران ندارید")
    
    success, message = delete_user(username)
    
    if success:
        return redirect(url_for("admin_manage_users") + f"?success={message}")
    else:
        return redirect(url_for("admin_manage_users") + f"?error={message}")


@app.route("/api/neighborhood", methods=["GET", "POST"])
def api_get_neighborhood():
    """
    API برای دریافت نام محله بر اساس مختصات جغرافیایی
    
    Parameters:
        - lat: عرض جغرافیایی (latitude)
        - lon: طول جغرافیایی (longitude)
        - map_id: (اختیاری) شناسه نقشه خاص. اگر نباشد، در همه نقشه‌ها جستجو می‌کند
    
    Returns JSON:
        {
            "success": true/false,
            "region": "نام محله",
            "district": "نام منطقه",
            "city": "نام شهر",
            "map_id": "شناسه نقشه",
            "map_name": "نام نقشه",
            "tootapp_url": "لینک توت‌اپ (اگر موجود باشد)"
        }
    """
    try:
        # دریافت پارامترها
        if request.method == "POST":
            data = request.get_json() or request.form
            lat = data.get("lat") or data.get("latitude")
            lon = data.get("lon") or data.get("longitude") or data.get("lng")
            map_id = data.get("map_id")
        else:  # GET
            lat = request.args.get("lat") or request.args.get("latitude")
            lon = request.args.get("lon") or request.args.get("longitude") or request.args.get("lng")
            map_id = request.args.get("map_id")
        
        # بررسی پارامترهای ورودی
        if not lat or not lon:
            return jsonify({
                "success": False,
                "error": "پارامترهای lat و lon الزامی هستند"
            }), 400
        
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "lat و lon باید عدد باشند"
            }), 400
        
        # ایجاد نقطه از مختصات
        point = Point(lon, lat)  # توجه: GeoJSON از [lon, lat] استفاده می‌کند
        
        # جستجو در نقشه‌ها
        history = load_history()
        maps_to_search = []
        
        if map_id:
            # جستجو در نقشه خاص
            map_data = load_map_data(map_id)
            if map_data:
                maps_to_search = [(map_id, map_data)]
        else:
            # جستجو در همه نقشه‌ها
            for item in history:
                item_map_id = item.get("map_id")
                if item_map_id:
                    map_data = load_map_data(item_map_id)
                    if map_data:
                        maps_to_search.append((item_map_id, map_data))
        
        # جستجو در هر نقشه
        for current_map_id, map_data in maps_to_search:
            geojson = map_data.get("geojson")
            if not geojson or not geojson.get("features"):
                continue
            
            # تبدیل GeoJSON به GeoDataFrame برای جستجوی سریع
            try:
                gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")
                
                # پیدا کردن feature که شامل این نقطه است
                mask = gdf.contains(point)
                matching_features = gdf[mask]
                
                if not matching_features.empty:
                    # اولین feature پیدا شده
                    feature_series = matching_features.iloc[0]
                    props = feature_series.to_dict()
                    
                    # تبدیل به dict برای get_feature_identifier
                    feature_dict = {
                        "properties": {k: v for k, v in props.items() if k != "geometry"}
                    }
                    
                    # استخراج اطلاعات
                    neighborhood = None
                    district = None
                    city = None
                    
                    # جستجوی نام محله - ابتدا فیلدهای استاندارد
                    for field in NEIGHBORHOOD_FIELDS:
                        if field in props and props[field]:
                            neighborhood = str(props[field])
                            break
                    
                    # اگر محله پیدا نشد، جستجوی هوشمند در همه فیلدها
                    if not neighborhood:
                        # جستجو برای فیلدهایی که نامشان شامل "name" یا "mahal" است
                        exclude_fields = ['geometry', 'tootapp_url', 'district', 'region', 'city', 'ostan', 'id', 'ID']
                        neighborhood_candidates = []
                        
                        for key, value in props.items():
                            if key.lower() in [f.lower() for f in exclude_fields]:
                                continue
                            
                            key_lower = key.lower()
                            value_str = str(value).strip() if value else ""
                            
                            # بررسی اینکه نام فیلد شامل "name" یا "mahal" باشد
                            if value_str and ('name' in key_lower or 'mahal' in key_lower):
                                # بررسی اینکه مقدار معتبر باشد (نه عدد خالص)
                                if not value_str.replace('.', '').replace('-', '').isdigit():
                                    if len(value_str) > 1 and len(value_str) < 200:
                                        neighborhood_candidates.append((key, value_str))
                        
                        # اگر کاندید پیدا شد، اولی را انتخاب می‌کنیم
                        if neighborhood_candidates:
                            neighborhood = neighborhood_candidates[0][1]
                    
                    # اگر هنوز پیدا نشد، جستجوی عمومی در همه فیلدها
                    if not neighborhood:
                        exclude_fields = ['geometry', 'tootapp_url', 'district', 'region', 'city', 'ostan', 'id', 'ID', 'lat', 'lon', 'longitude', 'latitude']
                        for key, value in props.items():
                            if key.lower() in [f.lower() for f in exclude_fields]:
                                continue
                            value_str = str(value).strip() if value else ""
                            # اگر مقدار خالی نباشد و عدد نباشد (احتمالاً نام است)
                            if value_str and not value_str.replace('.', '').replace('-', '').isdigit():
                                # بررسی اینکه نام محله باشد (نه مختصات یا کد)
                                if len(value_str) > 2 and len(value_str) < 100:
                                    neighborhood = value_str
                                    break
                    
                    # جستجوی منطقه
                    for field in DISTRICT_FIELDS:
                        if field in props and props[field]:
                            district = str(props[field])
                            break
                    
                    # جستجوی شهر
                    for field in CITY_FIELDS:
                        if field in props and props[field]:
                            city = str(props[field])
                            break
                    
                    # پیدا کردن map_name
                    map_info = next((item for item in history if item.get("map_id") == current_map_id), None)
                    map_name = map_info.get("map_name") if map_info else map_info.get("original_filename", "") if map_info else ""
                    
                    # بارگذاری لینک توت‌اپ
                    links = load_links(current_map_id)
                    feature_id = get_feature_identifier(feature_dict)
                    tootapp_url = None
                    
                    if feature_id and feature_id in links:
                        saved_link = links[feature_id]
                        if saved_link.startswith("http"):
                            tootapp_url = saved_link
                        else:
                            tootapp_url = f"{TOOTAPP_BASE_URL.rstrip('/')}/{saved_link.lstrip('/')}"
                    else:
                        # استفاده از base URL فقط
                        tootapp_url = TOOTAPP_BASE_URL.rstrip('/')
                    
                    return jsonify({
                        "success": True,
                        "region": neighborhood,
                        "district": district,
                        "city": city,
                        "map_id": current_map_id,
                        "map_name": map_name,
                        "tootapp_url": tootapp_url,
                        "coordinates": {
                            "lat": lat,
                            "lon": lon
                        }
                    }), 200
                    
            except Exception as e:
                # اگر GeoPandas خطا داد، با روش ساده‌تر امتحان می‌کنیم
                continue
        
        # اگر هیچ محله‌ای پیدا نشد
        return jsonify({
            "success": False,
            "error": "محله‌ای برای این مختصات پیدا نشد",
            "coordinates": {
                "lat": lat,
                "lon": lon
            }
        }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"خطا در پردازش درخواست: {str(e)}"
        }), 500


@app.route("/admin/features/upload", methods=["POST"])
def admin_upload_feature():
    """آپلود عوارض محله (فقط برای admin)"""
    if not session.get("username"):
        return jsonify({"success": False, "error": "لطفاً وارد شوید"}), 403
    
    if not has_permission("upload"):
        return jsonify({"success": False, "error": "شما دسترسی آپلود ندارید"}), 403
    
    try:
        file_obj = request.files.get("shapefile")
        map_id = request.form.get("map_id", "").strip()
        feature_name = request.form.get("feature_name", "").strip()
        
        if not file_obj or not file_obj.filename:
            return jsonify({"success": False, "error": "لطفاً یک فایل انتخاب کنید"}), 400
        
        if not map_id:
            return jsonify({"success": False, "error": "شناسه نقشه الزامی است"}), 400
        
        # بررسی وجود نقشه
        map_data = load_map_data(map_id)
        if not map_data:
            return jsonify({"success": False, "error": "نقشه پیدا نشد"}), 404
        
        # بارگذاری و تبدیل shapefile
        geojson, summary = load_geojson(file_obj)
        feature_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # ذخیره داده‌های عارضه
        final_feature_name = feature_name or file_obj.filename
        save_feature_data(feature_id, geojson, summary, file_obj.filename, map_id, final_feature_name)
        
        # به‌روزرسانی فهرست
        index = load_features_index()
        index.append({
            "feature_id": feature_id,
            "feature_name": final_feature_name,
            "map_id": map_id,
            "original_filename": file_obj.filename,
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "feature_count": summary.get("feature_count", 0),
        })
        save_features_index(index)
        
        return jsonify({
            "success": True,
            "message": "عوارض با موفقیت آپلود شد",
            "feature_id": feature_id
        }), 200
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"خطا در پردازش: {str(e)}"}), 500


@app.route("/api/features/list", methods=["GET"])
def api_list_features():
    """لیست عوارض موجود برای یک نقشه"""
    map_id = request.args.get("map_id")
    
    if not map_id:
        return jsonify({"success": False, "error": "شناسه نقشه الزامی است"}), 400
    
    index = load_features_index()
    features = [item for item in index if item.get("map_id") == map_id]
    
    return jsonify({
        "success": True,
        "features": features
    }), 200


@app.route("/api/features/<feature_id>", methods=["GET"])
def api_get_feature(feature_id: str):
    """دریافت داده‌های یک عارضه"""
    try:
        feature_data = load_feature_data(feature_id)
        
        if not feature_data:
            return jsonify({"success": False, "error": "عارضه پیدا نشد"}), 404
        
        geojson = feature_data.get("geojson")
        
        # اطمینان از اینکه GeoJSON یک dict معتبر است
        if not geojson:
            return jsonify({"success": False, "error": "داده GeoJSON یافت نشد"}), 404
        
        # بررسی ساختار GeoJSON
        if isinstance(geojson, dict):
            # اگر GeoJSON یک dict است، مستقیماً برگردان
            if "type" not in geojson:
                return jsonify({"success": False, "error": "ساختار GeoJSON نامعتبر است - فیلد type وجود ندارد"}), 400
            # بررسی اینکه آیا FeatureCollection است و features دارد
            if geojson.get("type") == "FeatureCollection":
                if "features" not in geojson or not isinstance(geojson["features"], list):
                    return jsonify({"success": False, "error": "ساختار FeatureCollection نامعتبر است"}), 400
        elif isinstance(geojson, str):
            # اگر GeoJSON یک string است، parse کن
            try:
                geojson = json.loads(geojson)
            except json.JSONDecodeError as e:
                return jsonify({"success": False, "error": f"خطا در parse کردن GeoJSON: {str(e)}"}), 400
        else:
            return jsonify({"success": False, "error": f"نوع داده GeoJSON نامعتبر است: {type(geojson)}"}), 400
        
        # attach کردن لینک‌های توت‌اپ به geojson
        map_id = feature_data.get("map_id")
        if map_id:
            # برای عوارض، از feature_id استفاده می‌کنیم
            saved_links = load_links(map_id)
            if feature_id in saved_links:
                saved_link = saved_links[feature_id]
                # attach کردن لینک به تمام features در geojson
                for feature in geojson.get("features", []):
                    props = feature.setdefault("properties", {})
                    if saved_link.startswith("http"):
                        props["tootapp_url"] = saved_link
                    else:
                        props["tootapp_url"] = f"{TOOTAPP_BASE_URL.rstrip('/')}/{saved_link.lstrip('/')}"
            else:
                # اگر لینک ذخیره شده نبود، فقط base URL را استفاده می‌کنیم
                for feature in geojson.get("features", []):
                    props = feature.setdefault("properties", {})
                    props["tootapp_url"] = TOOTAPP_BASE_URL.rstrip('/')
        
        return jsonify({
            "success": True,
            "geojson": geojson,
            "summary": feature_data.get("summary"),
            "feature_name": feature_data.get("feature_name"),
            "upload_date": feature_data.get("upload_date"),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"خطا در پردازش درخواست: {str(e)}"}), 500


@app.route("/api/features/by-location", methods=["GET", "POST"])
def api_get_features_by_location():
    """
    API برای دریافت عوارض موجود در نقشه بر اساس نام محله، منطقه و شهر
    
    Parameters:
        - neighborhood: نام محله (الزامی)
        - district: نام منطقه (اختیاری)
        - city: نام شهر (الزامی)
    
    Returns JSON:
        {
            "success": true/false,
            "city": "نام شهر",
            "neighborhood": "نام محله",
            "district": "نام منطقه",
            "map_id": "شناسه نقشه",
            "map_name": "نام نقشه",
            "features": [
                {
                    "feature_id": "شناسه عارضه",
                    "type": "نوع عارضه (Point, Polygon, etc)",
                    "coordinates": [مختصات جغرافیایی],
                    "properties": {همه فیلدهای موجود در عارضه}
                }
            ]
        }
    """
    try:
        # دریافت پارامترها
        if request.method == "POST":
            data = request.get_json() or request.form
            neighborhood = data.get("neighborhood") or data.get("neighbourhood")
            district = data.get("district")
            city = data.get("city")
        else:  # GET
            neighborhood = request.args.get("neighborhood") or request.args.get("neighbourhood")
            district = request.args.get("district")
            city = request.args.get("city")
        
        # بررسی پارامترهای ورودی
        if not neighborhood or not city:
            return jsonify({
                "success": False,
                "error": "پارامترهای neighborhood و city الزامی هستند"
            }), 400
        
        # جستجوی نقشه مربوط به شهر
        history = load_history()
        map_info = None
        for item in history:
            map_name = (item.get("map_name") or item.get("original_filename", "")).lower()
            if city.lower() in map_name:
                map_info = item
                break
        
        if not map_info:
            return jsonify({
                "success": False,
                "error": f"نقشه‌ای برای شهر '{city}' پیدا نشد"
            }), 404
        
        map_id = map_info.get("map_id")
        map_name = map_info.get("map_name") or map_info.get("original_filename", "نقشه")
        
        # بارگذاری لیست عوارض
        index = load_features_index()
        features_list = [item for item in index if item.get("map_id") == map_id]
        
        # بارگذاری داده‌های هر عارضه
        result_features = []
        for feature_item in features_list:
            feature_id = feature_item.get("feature_id")
            if not feature_id:
                continue
            
            feature_data = load_feature_data(feature_id)
            if not feature_data:
                continue
            
            geojson = feature_data.get("geojson")
            if not geojson:
                continue
            
            # parse کردن geojson اگر string است
            if isinstance(geojson, str):
                try:
                    geojson = json.loads(geojson)
                except json.JSONDecodeError:
                    continue
            
            # پردازش features در geojson
            if geojson.get("type") == "FeatureCollection" and geojson.get("features"):
                for feature in geojson.get("features", []):
                    props = feature.get("properties", {})
                    
                    # بررسی تطابق با neighborhood
                    neighborhood_match = False
                    for field in NEIGHBORHOOD_FIELDS:
                        if field in props:
                            value = str(props[field]).lower().strip()
                            if neighborhood.lower().strip() in value or value in neighborhood.lower().strip():
                                neighborhood_match = True
                                break
                    
                    # اگر district مشخص شده، بررسی تطابق
                    district_match = True
                    if district:
                        district_match = False
                        for field in DISTRICT_FIELDS:
                            if field in props:
                                value = str(props[field]).lower().strip()
                                if district.lower().strip() in value or value in district.lower().strip():
                                    district_match = True
                                    break
                    
                    # اگر تطابق داشت، اضافه کن
                    if neighborhood_match and district_match:
                        geometry = feature.get("geometry", {})
                        result_features.append({
                            "feature_id": feature_id,
                            "type": geometry.get("type", "Unknown"),
                            "coordinates": geometry.get("coordinates", []),
                            "properties": props
                        })
        
        return jsonify({
            "success": True,
            "city": city,
            "neighborhood": neighborhood,
            "district": district if district else None,
            "map_id": map_id,
            "map_name": map_name,
            "features": result_features,
            "count": len(result_features)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"خطا در پردازش درخواست: {str(e)}"
        }), 500


@app.route("/admin/features/delete/<feature_id>", methods=["POST"])
def admin_delete_feature(feature_id: str):
    """حذف عارضه (فقط برای admin)"""
    if not session.get("username"):
        return jsonify({"success": False, "error": "لطفاً وارد شوید"}), 403
    
    if not has_permission("delete"):
        return jsonify({"success": False, "error": "شما دسترسی حذف ندارید"}), 403
    
    try:
        # حذف فایل
        feature_file = FEATURES_DIR / f"{feature_id}.json"
        if feature_file.exists():
            feature_file.unlink()
        
        # حذف از فهرست
        index = load_features_index()
        index = [item for item in index if item.get("feature_id") != feature_id]
        save_features_index(index)
        
        return jsonify({"success": True, "message": "عارضه با موفقیت حذف شد"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": f"خطا در حذف: {str(e)}"}), 500


@app.route("/admin/features/update-link/<feature_id>", methods=["POST"])
def admin_update_feature_link(feature_id: str):
    """آپدیت لینک توت‌اپ یک عارضه"""
    if not session.get("username"):
        return jsonify({"success": False, "error": "لطفاً وارد شوید"}), 403
    
    if not has_permission("upload"):
        return jsonify({"success": False, "error": "شما دسترسی آپدیت ندارید"}), 403
    
    try:
        link_value = request.form.get("link", "").strip()
        map_id = request.form.get("map_id", "").strip()
        
        if not map_id:
            return jsonify({"success": False, "error": "شناسه نقشه الزامی است"}), 400
        
        # بارگذاری لینک‌های موجود
        links = load_links(map_id)
        
        # پاک کردن پیشوندهای مختلف
        if link_value.startswith("tootapp.ir/join/"):
            link_value = link_value.replace("tootapp.ir/join/", "")
        elif link_value.startswith("tootapp.ir/"):
            link_value = link_value.replace("tootapp.ir/", "")
        if link_value.startswith("https://tootapp.ir/join/"):
            link_value = link_value.replace("https://tootapp.ir/join/", "")
        elif link_value.startswith("https://tootapp.ir/"):
            link_value = link_value.replace("https://tootapp.ir/", "")
        if link_value.startswith("http://tootapp.ir/join/"):
            link_value = link_value.replace("http://tootapp.ir/join/", "")
        elif link_value.startswith("http://tootapp.ir/"):
            link_value = link_value.replace("http://tootapp.ir/", "")
        
        # ذخیره لینک (حتی اگر خالی باشد)
        links[feature_id] = link_value
        save_links(map_id, links)
        
        return jsonify({"success": True, "message": "لینک با موفقیت آپدیت شد"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": f"خطا در آپدیت: {str(e)}"}), 500


@app.route("/admin/features/links/<map_id>", methods=["GET"])
def admin_manage_feature_links(map_id: str):
    """مدیریت لینک‌های توت‌اپ برای عوارض یک نقشه"""
    if not session.get("username"):
        return redirect(url_for("admin_login"))
    
    if not has_permission("manage_links"):
        return redirect(url_for("admin_panel") + "?error=شما دسترسی مدیریت لینک‌ها ندارید")
    
    # بارگذاری لیست عوارض
    try:
        index = load_features_index()
        features = [item for item in index if item.get("map_id") == map_id]
    except Exception as e:
        features = []
    
    # بارگذاری لینک‌های ذخیره شده
    try:
        saved_links = load_links(map_id)
    except Exception as e:
        saved_links = {}
    
    # اضافه کردن لینک به هر عارضه
    for feature in features:
        feature_id = feature.get("feature_id")
        if feature_id:
            feature["link"] = saved_links.get(feature_id, "")
        else:
            feature["link"] = ""
        
        # اطمینان از وجود فیلدهای مورد نیاز
        if "feature_name" not in feature:
            feature["feature_name"] = None
        if "original_filename" not in feature:
            feature["original_filename"] = "نامشخص"
    
    history = load_history()
    map_info = next((item for item in history if item.get("map_id") == map_id), None)
    if map_info:
        map_name = map_info.get("map_name") or map_info.get("original_filename", "نقشه")
    else:
        map_name = "نقشه"
    
    error = request.args.get("error")
    success = request.args.get("success")
    
    try:
        return render_template_string(
            MANAGE_FEATURE_LINKS_TEMPLATE,
            map_id=map_id,
            map_name=map_name,
            features=features,
            error=error,
            success=success
        )
    except Exception as e:
        import traceback
        return f"خطا در رندر کردن صفحه: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
