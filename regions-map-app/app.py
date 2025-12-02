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
USERS_FILE = BASE_DIR / "uploads" / "regions" / "users.json"

ALLOWED_EXTENSIONS = {"zip", "geojson"}
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


def _load_geojson_from_geojson(file_obj: FileStorage) -> Dict:
    payload = file_obj.read()
    if not payload:
        raise ValueError("فایل خالی است.")
    try:
        geojson = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("فایل GeoJSON معتبر نیست.") from exc
    return geojson


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

    geojson = json.loads(gdf.to_json())

    shutil.rmtree(work_dir, ignore_errors=True)
    return geojson


def load_geojson(file_obj: FileStorage) -> Tuple[Dict, Dict]:
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
            # اگر لینک ذخیره شده نبود، از منطق قبلی استفاده می‌کنیم
            slug = _resolve_group_slug(props)
            if slug:
                props["tootapp_url"] = f"{TOOTAPP_BASE_URL.rstrip('/')}/{slug.lstrip('/')}"
            else:
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
    data = {
        "geojson": geojson,
        "summary": summary,
        "original_filename": original_filename,
        "map_id": map_id,
    }
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def get_feature_identifier(feature: Dict) -> Optional[str]:
    """ایجاد شناسه منحصر به فرد برای یک feature"""
    props = feature.get("properties", {})
    # استفاده از ترکیب فیلدهای مختلف برای شناسه
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
        <input type="file" name="shapefile" accept=".zip,.geojson" required />
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
              <button type="button" style="background: #2a9d8f; padding: 0.5rem 1rem; font-size: 0.9rem; margin-left: 0.5rem;">مدیریت لینک‌ها</button>
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
        <form method="post" action="/admin/links/{{ map_id }}/save" class="neighborhood-form">
          <input type="hidden" name="feature_id" value="{{ neighborhood.id }}" />
          <div class="link-input-group">
            <span class="link-prefix">tootapp.ir/join/</span>
            <input type="text" name="link" value="{{ neighborhood.link }}" placeholder="مثلاً: Tehran3Da" required />
            <button type="submit" class="save">ذخیره</button>
          </div>
          <div class="save-status" id="status_{{ neighborhood.id }}"></div>
        </form>
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
    #map { width: 100%; height: 520px; border-radius: 12px; }
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
      <div id="map"></div>
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

    const geojsonData = {{ geojson|safe if geojson else 'null' }};
    if (geojsonData) {
      map.eachLayer(function(layer) {
        if (layer instanceof L.GeoJSON) {
          map.removeLayer(layer);
        }
      });
      const layer = L.geoJSON(geojsonData, {
        style: function() { return { color: '#111', weight: 2, fillOpacity: 0.1 }; },
        onEachFeature: function(feature, layer) {
          if (feature.properties) {
            const props = feature.properties;
            
            // کلمات کلیدی برای جستجو در نام فیلدها (case-insensitive)
            const keywords = ['name', 'mahalle', 'district', 'region', 'area'];
            
            // فیلدهایی که باید نادیده گرفته شوند
            const excludeFields = ['tootapp_url', 'geometry'];
            
            // ساخت محتوای پاپ‌آپ
            const popupItems = [];
            
            // بررسی تمام فیلدها و نمایش آنهایی که نامشان شامل کلمات کلیدی است
            for (const key in props) {
              // نادیده گرفتن فیلدهای خاص
              if (excludeFields.includes(key.toLowerCase())) {
                continue;
              }
              
              const value = props[key];
              // بررسی اینکه فیلد خالی نباشد
              if (value === undefined || value === null || String(value).trim() === '') {
                continue;
              }
              
              // بررسی اینکه نام فیلد شامل یکی از کلمات کلیدی باشد
              const keyLower = key.toLowerCase();
              const matchesKeyword = keywords.some(keyword => keyLower.includes(keyword.toLowerCase()));
              
              if (matchesKeyword) {
                // نمایش فیلد با نام اصلی آن
                popupItems.push(`<strong>${key}:</strong> ${String(value).trim()}`);
              }
            }
            
            const link = props.tootapp_url || 'https://tootapp.ir/join/';
            popupItems.push(`<strong>پیوستن به شبکه محله:</strong> <a href="${link}" target="_blank" rel="noopener">ورود به توت‌اپ</a>`);
            
            const popupContent = popupItems.join('<br/>');

            layer.bindPopup(popupContent);
          }
        }
      }).addTo(map);
      try {
        map.fitBounds(layer.getBounds(), { padding: [20, 20] });
      } catch (err) {
        console.warn('Cannot fit bounds', err);
      }
    }

    function loadMap(mapId) {
      window.location.href = '/map/' + mapId;
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

    if selected_map_id:
        map_data = load_map_data(selected_map_id)
        if map_data:
            geojson = map_data.get("geojson")
            summary = map_data.get("summary")
            # اتصال لینک‌های توت‌اپ (با استفاده از لینک‌های ذخیره شده)
            if geojson:
                _attach_tootapp_links(geojson, selected_map_id)

    return render_template_string(
        INDEX_TEMPLATE,
        history=history,
        selected_map_id=selected_map_id,
        geojson=json.dumps(geojson) if geojson else None,
        summary=summary,
    )


@app.route("/map/<map_id>")
def view_map(map_id: str):
    """مشاهده نقشه خاص"""
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
    
    if geojson and geojson.get("features"):
        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            feature_id = get_feature_identifier(feature)
            
            # پیدا کردن نام محله
            name = None
            keywords = ['name', 'mahalle', 'district', 'region']
            for key in props:
                key_lower = key.lower()
                if any(kw in key_lower for kw in keywords):
                    value = props[key]
                    if value and str(value).strip():
                        name = str(value).strip()
                        break
            
            if not name:
                name = "نامشخص"
            
            # اطلاعات اضافی
            info_parts = []
            for key in props:
                key_lower = key.lower()
                if any(kw in key_lower for kw in keywords) and str(props[key]).strip():
                    info_parts.append(f"{key}: {props[key]}")
            info = " | ".join(info_parts[:3]) if info_parts else "بدون اطلاعات"
            
            # لینک ذخیره شده
            link = saved_links.get(feature_id, "") if feature_id else ""
            
            neighborhoods.append({
                "id": feature_id or f"feature_{len(neighborhoods)}",
                "name": name,
                "info": info,
                "link": link
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
            "neighborhood": "نام محله",
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
                    
                    # جستجوی نام محله
                    for field in NEIGHBORHOOD_FIELDS:
                        if field in props and props[field]:
                            neighborhood = str(props[field])
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
                        # استفاده از slug از properties
                        slug = _resolve_group_slug(props)
                        if slug:
                            tootapp_url = f"{TOOTAPP_BASE_URL.rstrip('/')}/{slug.lstrip('/')}"
                    
                    return jsonify({
                        "success": True,
                        "neighborhood": neighborhood,
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
