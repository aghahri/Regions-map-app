#!/usr/bin/env python3
"""
اسکریپت برای استخراج و پردازش فایل کسب و کارهای محلی
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    print("❌ لطفاً pandas را نصب کنید: pip install pandas")
    sys.exit(1)

try:
    from rarfile import RarFile
except ImportError:
    print("⚠️  rarfile نصب نیست. در حال نصب...")
    os.system("pip install rarfile")
    try:
        from rarfile import RarFile
    except ImportError:
        print("❌ نتوانستم rarfile را نصب کنم. لطفاً دستی نصب کنید: pip install rarfile")
        sys.exit(1)

try:
    from shapely.geometry import Point
except ImportError:
    print("❌ لطفاً shapely را نصب کنید: pip install shapely")
    sys.exit(1)


def extract_rar(rar_path: str, extract_to: str) -> List[str]:
    """استخراج فایل RAR"""
    extracted_files = []
    try:
        with RarFile(rar_path) as rar:
            rar.extractall(extract_to)
            extracted_files = rar.namelist()
            print(f"✅ {len(extracted_files)} فایل استخراج شد")
            return extracted_files
    except Exception as e:
        print(f"❌ خطا در استخراج RAR: {e}")
        return []


def read_excel_file(excel_path: str) -> Optional[pd.DataFrame]:
    """خواندن فایل اکسل"""
    try:
        # تلاش برای خواندن با pandas
        df = pd.read_excel(excel_path, engine='openpyxl')
        print(f"✅ فایل اکسل خوانده شد: {len(df)} ردیف")
        return df
    except Exception as e:
        print(f"⚠️  خطا در خواندن با openpyxl: {e}")
        try:
            # تلاش با xlrd
            df = pd.read_excel(excel_path, engine='xlrd')
            print(f"✅ فایل اکسل خوانده شد (xlrd): {len(df)} ردیف")
            return df
        except Exception as e2:
            print(f"❌ خطا در خواندن فایل اکسل: {e2}")
            return None


def find_coordinate_columns(df: pd.DataFrame) -> tuple:
    """پیدا کردن ستون‌های مختصات (lat, lon)"""
    # نام‌های احتمالی برای عرض جغرافیایی
    lat_names = ['lat', 'latitude', 'عرض', 'عرض جغرافیایی', 'y', 'Y', 'Lat', 'LAT']
    # نام‌های احتمالی برای طول جغرافیایی
    lon_names = ['lon', 'lng', 'longitude', 'long', 'طول', 'طول جغرافیایی', 'x', 'X', 'Lon', 'LON', 'Lng', 'LNG']
    
    lat_col = None
    lon_col = None
    
    # جستجو در نام ستون‌ها
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if not lat_col:
            for lat_name in lat_names:
                if lat_name.lower() in col_lower:
                    lat_col = col
                    break
        if not lon_col:
            for lon_name in lon_names:
                if lon_name.lower() in col_lower:
                    lon_col = col
                    break
    
    return lat_col, lon_col


def find_name_column(df: pd.DataFrame) -> Optional[str]:
    """پیدا کردن ستون نام کسب و کار"""
    name_names = ['name', 'نام', 'title', 'عنوان', 'business_name', 'نام کسب و کار', 
                  'shop_name', 'نام مغازه', 'store_name', 'نام فروشگاه']
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        for name_name in name_names:
            if name_name.lower() in col_lower:
                return col
    return None


def convert_to_geojson(df: pd.DataFrame, lat_col: str, lon_col: str, 
                       name_col: Optional[str] = None) -> Dict:
    """تبدیل DataFrame به GeoJSON"""
    features = []
    
    for idx, row in df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            
            # بررسی معتبر بودن مختصات
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print(f"⚠️  ردیف {idx}: مختصات نامعتبر ({lat}, {lon})")
                continue
            
            # ساخت Point geometry
            point = Point(lon, lat)  # GeoJSON از (lon, lat) استفاده می‌کند
            
            # ساخت properties
            properties = {}
            
            # اضافه کردن نام
            if name_col and name_col in row:
                properties['name'] = str(row[name_col])
            else:
                properties['name'] = f"کسب و کار {idx + 1}"
            
            # اضافه کردن تمام ستون‌های دیگر به properties
            for col in df.columns:
                if col not in [lat_col, lon_col, name_col]:
                    value = row[col]
                    # تبدیل به string اگر قابل JSON serialization نیست
                    if pd.isna(value):
                        continue
                    try:
                        json.dumps(value)  # تست serialization
                        properties[str(col)] = value
                    except (TypeError, ValueError):
                        properties[str(col)] = str(value)
            
            # ساخت feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": properties
            }
            
            features.append(feature)
            
        except (ValueError, KeyError) as e:
            print(f"⚠️  خطا در ردیف {idx}: {e}")
            continue
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson


def main():
    """تابع اصلی"""
    if len(sys.argv) < 2:
        print("استفاده: python process_businesses.py <مسیر_فایل_RAR>")
        print("مثال: python process_businesses.py '/Users/akiokaviano/Documents/Toot/Regions/Tabriz/تبریز (1).rar'")
        sys.exit(1)
    
    rar_path = sys.argv[1]
    
    if not os.path.exists(rar_path):
        print(f"❌ فایل پیدا نشد: {rar_path}")
        sys.exit(1)
    
    # مسیر استخراج
    base_dir = Path(__file__).parent
    extract_dir = base_dir / "temp_extract"
    extract_dir.mkdir(exist_ok=True)
    
    print(f"📦 استخراج فایل RAR: {rar_path}")
    extracted_files = extract_rar(rar_path, str(extract_dir))
    
    if not extracted_files:
        print("❌ هیچ فایلی استخراج نشد")
        sys.exit(1)
    
    # پیدا کردن فایل اکسل
    excel_file = None
    for file in extracted_files:
        file_path = extract_dir / file
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            excel_file = file_path
            break
    
    if not excel_file:
        print("❌ فایل اکسل پیدا نشد")
        sys.exit(1)
    
    print(f"📊 خواندن فایل اکسل: {excel_file}")
    df = read_excel_file(str(excel_file))
    
    if df is None or df.empty:
        print("❌ فایل اکسل خالی است یا خطا در خواندن")
        sys.exit(1)
    
    print(f"\n📋 ستون‌های موجود:")
    for col in df.columns:
        print(f"   - {col}")
    
    # پیدا کردن ستون‌های مختصات
    lat_col, lon_col = find_coordinate_columns(df)
    
    if not lat_col or not lon_col:
        print("\n❌ ستون‌های مختصات پیدا نشد!")
        print("لطفاً مطمئن شوید که فایل اکسل دارای ستون‌های lat/latitude و lon/longitude است")
        sys.exit(1)
    
    print(f"\n✅ ستون عرض جغرافیایی: {lat_col}")
    print(f"✅ ستون طول جغرافیایی: {lon_col}")
    
    # پیدا کردن ستون نام
    name_col = find_name_column(df)
    if name_col:
        print(f"✅ ستون نام: {name_col}")
    else:
        print("⚠️  ستون نام پیدا نشد - از نام پیش‌فرض استفاده می‌شود")
    
    # تبدیل به GeoJSON
    print("\n🔄 تبدیل به GeoJSON...")
    geojson = convert_to_geojson(df, lat_col, lon_col, name_col)
    
    # ذخیره GeoJSON
    output_file = base_dir / "uploads" / "uploads" / "regions" / "businesses" / "tabriz_businesses.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ GeoJSON ذخیره شد: {output_file}")
    print(f"📊 تعداد کسب و کارها: {len(geojson['features'])}")
    
    # پاکسازی فایل‌های موقت
    shutil.rmtree(extract_dir)
    print("🧹 فایل‌های موقت پاک شدند")
    
    print("\n✅ تمام!")


if __name__ == "__main__":
    main()

