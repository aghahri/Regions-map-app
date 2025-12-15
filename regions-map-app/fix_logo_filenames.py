#!/usr/bin/env python3
"""
اسکریپت برای اصلاح نام فایل‌های لوگو که پسوند ندارند
این اسکریپت فایل‌های قدیمی را پیدا کرده و پسوند مناسب به آنها اضافه می‌کند
"""

import json
import shutil
from pathlib import Path

# مسیر فولدر logos
LOGO_DIR = Path(__file__).parent / "uploads" / "regions" / "logos"

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}

def detect_file_type(file_path: Path) -> str:
    """تشخیص نوع فایل بر اساس محتوای آن"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(12)
            
        # JPEG
        if header.startswith(b'\xff\xd8\xff'):
            return 'jpg'
        # PNG
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        # GIF
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'gif'
        # WebP
        elif header.startswith(b'RIFF') and b'WEBP' in header:
            return 'webp'
        # SVG (text file)
        elif header.startswith(b'<?xml') or header.startswith(b'<svg'):
            return 'svg'
    except Exception:
        pass
    
    return None

def fix_logo_filenames():
    """اصلاح نام فایل‌های لوگو"""
    if not LOGO_DIR.exists():
        print(f"❌ فولدر {LOGO_DIR} وجود ندارد")
        return
    
    print(f"🔍 جستجوی فایل‌های لوگو در {LOGO_DIR}")
    
    fixed_count = 0
    error_count = 0
    not_found_count = 0
    
    # لیست تمام فایل‌های عکس موجود
    existing_image_files = {}
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        for img_file in LOGO_DIR.glob(f"*.{ext}"):
            existing_image_files[img_file.name] = img_file
    
    # بررسی تمام فایل‌های JSON
    for json_file in LOGO_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logo_filename = data.get("logo_filename", "")
            if not logo_filename:
                continue
            
            logo_path = LOGO_DIR / logo_filename
            
            # بررسی وجود فایل
            file_exists = logo_path.exists() and logo_path.is_file()
            
            # اگر فایل وجود ندارد، جستجو برای فایل‌های مشابه
            if not file_exists:
                # جستجو برای فایل‌هایی که با این نام شروع می‌شوند
                found_file = None
                for img_name, img_path in existing_image_files.items():
                    # اگر نام فایل بدون پسوند با نام موجود شروع می‌شود
                    base_name = logo_filename.rsplit('.', 1)[0] if '.' in logo_filename else logo_filename
                    if img_name.startswith(base_name) or base_name in img_name:
                        found_file = img_name
                        break
                
                if found_file:
                    print(f"✅ فایل مشابه پیدا شد: {logo_filename} → {found_file}")
                    # به‌روزرسانی JSON
                    data["logo_filename"] = found_file
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    fixed_count += 1
                    continue
                else:
                    print(f"⚠️  فایل لوگو پیدا نشد: {logo_filename}")
                    not_found_count += 1
                    continue
            
            # اگر فایل وجود دارد و پسوند ندارد یا پسوند اشتباه دارد
            if file_exists:
                # بررسی پسوند
                if '.' not in logo_filename or not any(logo_filename.lower().endswith(f'.{ext}') for ext in ALLOWED_IMAGE_EXTENSIONS):
                    print(f"⚠️  فایل بدون پسوند یا با پسوند اشتباه پیدا شد: {logo_filename}")
                    
                    # تشخیص نوع فایل
                    file_type = detect_file_type(logo_path)
                    if file_type:
                        # ساخت نام جدید
                        if '.' in logo_filename:
                            # اگر پسوند دارد اما اشتباه است
                            base_name = logo_filename.rsplit('.', 1)[0]
                        else:
                            base_name = logo_filename
                        
                        new_filename = f"{base_name}.{file_type}"
                        new_path = LOGO_DIR / new_filename
                        
                        # اگر فایل جدید وجود ندارد، rename کن
                        if not new_path.exists():
                            logo_path.rename(new_path)
                            print(f"✅ فایل rename شد: {logo_filename} → {new_filename}")
                            
                            # به‌روزرسانی JSON
                            data["logo_filename"] = new_filename
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            fixed_count += 1
                        else:
                            print(f"⚠️  فایل جدید از قبل وجود دارد: {new_filename}")
                    else:
                        print(f"❌ نتوانست نوع فایل را تشخیص دهد: {logo_filename}")
                        error_count += 1
                else:
                    # بررسی اینکه فایل واقعاً از نوع گفته شده است
                    file_type = detect_file_type(logo_path)
                    if file_type:
                        current_ext = logo_filename.rsplit('.', 1)[1].lower() if '.' in logo_filename else ''
                        if file_type != current_ext:
                            print(f"⚠️  پسوند فایل با نوع واقعی آن مطابقت ندارد: {logo_filename} (نوع واقعی: {file_type})")
                            
                            # اصلاح پسوند
                            base_name = logo_filename.rsplit('.', 1)[0]
                            new_filename = f"{base_name}.{file_type}"
                            new_path = LOGO_DIR / new_filename
                            
                            if not new_path.exists():
                                logo_path.rename(new_path)
                                print(f"✅ پسوند فایل اصلاح شد: {logo_filename} → {new_filename}")
                                
                                # به‌روزرسانی JSON
                                data["logo_filename"] = new_filename
                                with open(json_file, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                                
                                fixed_count += 1
            else:
                print(f"⚠️  فایل لوگو پیدا نشد: {logo_filename}")
                
        except Exception as e:
            print(f"❌ خطا در پردازش {json_file}: {e}")
            error_count += 1
    
    print(f"\n✅ تمام!")
    print(f"   - {fixed_count} فایل اصلاح شد")
    print(f"   - {not_found_count} فایل پیدا نشد")
    print(f"   - {error_count} خطا")

if __name__ == "__main__":
    fix_logo_filenames()

