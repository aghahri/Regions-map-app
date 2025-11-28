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
except ImportError as exc:  # pragma: no cover - fails fast on missing deps
    raise RuntimeError("لطفاً بسته GeoPandas را نصب کنید (pip install geopandas).") from exc
from flask import Flask, render_template_string, request, session, redirect, url_for
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

ALLOWED_EXTENSIONS = {"zip", "geojson"}
TOOTAPP_BASE_URL = "https://tootapp.ir/"

# پسورد ادمین (در تولید باید از متغیر محیطی استفاده شود)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
# استفاده از pbkdf2:sha256 که در همه نسخه‌های Python موجود است
USE_SIMPLE_HASH = False
try:
    ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256")
except Exception:
    # Fallback: استفاده از hash ساده (فقط برای توسعه)
    USE_SIMPLE_HASH = True
    ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()


def verify_admin_password(password: str) -> bool:
    """بررسی صحت رمز عبور ادمین"""
    if USE_SIMPLE_HASH:
        # Fallback: مقایسه ساده (فقط برای توسعه)
        return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH
    else:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)

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


def delete_map(map_id: str) -> bool:
    """حذف نقشه از تاریخچه و فایل ذخیره شده"""
    try:
        # حذف فایل JSON
        map_file = STORAGE_DIR / f"{map_id}.json"
        if map_file.exists():
            map_file.unlink()

        # حذف فایل لینک‌ها
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


def is_admin() -> bool:
    """بررسی اینکه کاربر ادمین است یا نه"""
    return session.get("is_admin", False)


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
    <h1>ورود ادمین</h1>
    <form method="post">
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
    <h1>پنل ادمین - آپلود نقشه</h1>
  </header>
  <main>
    <div class="card">
      <div style="text-align: left; margin-bottom: 1rem;">
        <a href="/" style="color: #2a9d8f; text-decoration: none;">← بازگشت به صفحه اصلی</a>
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
      <p style="color: #6c757d; margin-bottom: 1rem;">لینک‌ها باید با <code>tootapp.ir/</code> شروع شوند. فقط قسمت بعد از اسلش را وارد کنید.</p>
      {% for neighborhood in neighborhoods %}
      <div class="neighborhood-item">
        <div class="neighborhood-name">{{ neighborhood.name }}</div>
        <div class="neighborhood-info">{{ neighborhood.info }}</div>
        <form method="post" action="/admin/links/{{ map_id }}/save" class="neighborhood-form">
          <input type="hidden" name="feature_id" value="{{ neighborhood.id }}" />
          <div class="link-input-group">
            <span class="link-prefix">tootapp.ir/</span>
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
    .history-list { list-style: none; padding: 0; }
    .history-item { padding: 1rem; margin-bottom: 0.5rem; background: #f8f9fa; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
    .history-item:hover { background: #e9ecef; }
    .history-item.active { background: #2a9d8f; color: #fff; }
    .admin-link { text-align: center; margin-top: 1rem; }
    .admin-link a { color: #2a9d8f; text-decoration: none; }
    .summary { margin-top: 1rem; line-height: 1.8; }
    .summary-toggle-btn { width: 100%; padding: 0.75rem; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; background: #2a9d8f; color: #fff; margin-bottom: 1rem; }
    .summary-toggle-btn:hover { background: #238a7d; }
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
      <ul class="history-list">
        {% for item in history %}
        <li class="history-item {% if item.map_id == selected_map_id %}active{% endif %}" onclick="loadMap('{{ item.map_id }}')">
          <strong>{{ item.map_name or item.original_filename }}</strong><br/>
          <small>تاریخ: {{ item.upload_date }} | تعداد عوارض: {{ item.feature_count }}</small>
        </li>
        {% endfor %}
      </ul>
    </section>
    {% endif %}
    <section class="card">
      {% if summary %}
      <button onclick="toggleSummary()" class="summary-toggle-btn">نمایش ویژگی‌های لایه</button>
      <div class="summary" id="summary-details" style="display: none;">
        <strong>ویژگی‌های لایه:</strong>
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
            
            const link = props.tootapp_url || 'https://tootapp.ir';
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
        btn.textContent = 'مخفی کردن ویژگی‌های لایه';
      } else {
        summaryDiv.style.display = 'none';
        btn.textContent = 'نمایش ویژگی‌های لایه';
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
    """ورود ادمین"""
    if is_admin():
        return redirect(url_for("admin_panel"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if verify_admin_password(password):
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "رمز عبور اشتباه است."

    return render_template_string(LOGIN_TEMPLATE, error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    """خروج ادمین"""
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    """پنل ادمین - آپلود نقشه"""
    if not is_admin():
        return redirect(url_for("admin_login"))

    error = None
    success = None

    # بررسی پیام‌های query string
    if request.args.get("deleted") == "1":
        success = "نقشه با موفقیت حذف شد."
    elif request.args.get("error"):
        error = request.args.get("error")

    if request.method == "POST":
        file_obj = request.files.get("shapefile")
        map_name = request.form.get("map_name", "").strip()

        if not file_obj or not file_obj.filename:
            error = "لطفاً یک فایل انتخاب کنید."
        else:
            try:
                geojson, summary = load_geojson(file_obj)
                map_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                save_map_data(map_id, geojson, summary, file_obj.filename)

                history = load_history()
                history.insert(0, {
                    "map_id": map_id,
                    "map_name": map_name or file_obj.filename,
                    "original_filename": file_obj.filename,
                    "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "feature_count": summary.get("feature_count", 0),
                })
                save_history(history)

                success = f"نقشه با موفقیت آپلود شد! شناسه: {map_id}"
            except ValueError as exc:
                error = str(exc)

    history = load_history()
    return render_template_string(ADMIN_TEMPLATE, error=error, success=success, history=history)


@app.route("/admin/delete/<map_id>", methods=["POST"])
def admin_delete_map(map_id: str):
    """حذف نقشه از تاریخچه (فقط برای ادمین)"""
    if not is_admin():
        return redirect(url_for("admin_login"))

    if delete_map(map_id):
        return redirect(url_for("admin_panel") + "?deleted=1")
    else:
        return redirect(url_for("admin_panel") + "?error=حذف نقشه با خطا مواجه شد")


@app.route("/admin/links/<map_id>", methods=["GET"])
def admin_manage_links(map_id: str):
    """مدیریت لینک‌های توت‌اپ برای یک نقشه (فقط برای ادمین)"""
    if not is_admin():
        return redirect(url_for("admin_login"))

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
    """ذخیره لینک یک محله خاص (فقط برای ادمین)"""
    if not is_admin():
        return json.dumps({"success": False, "error": "دسترسی غیرمجاز"}), 403, {"Content-Type": "application/json"}

    feature_id = request.form.get("feature_id", "").strip()
    link_value = request.form.get("link", "").strip()

    if not feature_id:
        return json.dumps({"success": False, "error": "شناسه محله نامعتبر است"}), 400, {"Content-Type": "application/json"}

    try:
        # بارگذاری لینک‌های موجود
        links = load_links(map_id)

        if link_value:
            # حذف tootapp.ir/ اگر کاربر آن را وارد کرده
            if link_value.startswith("tootapp.ir/"):
                link_value = link_value.replace("tootapp.ir/", "")
            if link_value.startswith("https://tootapp.ir/"):
                link_value = link_value.replace("https://tootapp.ir/", "")
            if link_value.startswith("http://tootapp.ir/"):
                link_value = link_value.replace("http://tootapp.ir/", "")
            links[feature_id] = link_value
        elif feature_id in links:
            # اگر لینک خالی شد، حذف می‌کنیم
            del links[feature_id]

        save_links(map_id, links)
        return json.dumps({"success": True, "message": "لینک با موفقیت ذخیره شد"}), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}), 500, {"Content-Type": "application/json"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
