import os
import sys
import subprocess
import shutil

print("1. Cài đặt các thư viện cần thiết...")
subprocess.run([sys.executable, "-m", "pip", "install", "pyqt6", "pyqt6-webengine", "pyinstaller", "pillow"], check=True)

print("2. Đang sao chép và xử lý ảnh Icon...")
img_path = "/Users/hoainam/.gemini/antigravity/brain/9e5bc79a-9a0d-4b48-a6ae-4abc2dea90f8/focus_pet_icon_1778695633391.png"
assets_dir = "assets"
os.makedirs(assets_dir, exist_ok=True)
dest_img = os.path.join(assets_dir, "icon.png")

if os.path.exists(img_path):
    shutil.copy(img_path, dest_img)
else:
    print(f"❌ LỖI: Không tìm thấy ảnh gốc tại: {img_path}")
    sys.exit(1)

print("3. Đang tạo icon cho macOS (.icns) và Windows (.ico)...")
from PIL import Image
try:
    img = Image.open(dest_img)
    # Resize to standard icon size to avoid issues
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
    
    icns_path = os.path.join(assets_dir, "icon.icns")
    ico_path = os.path.join(assets_dir, "icon.ico")
    
    img.save(icns_path, format="ICNS")
    img.save(ico_path, format="ICO", sizes=[(256, 256)])
    print("✓ Đã tạo thành công icon.icns và icon.ico bằng Pillow!")
except Exception as e:
    print(f"❌ Lỗi khi tạo icon bằng Pillow: {e}")
    sys.exit(1)

print("4. Tiến hành đóng gói ứng dụng macOS...")
build_cmd = [
    "pyinstaller", "--noconfirm", "--onedir", "--windowed",
    "--icon", "assets/icon.icns",
    "--add-data", "assets:assets",
    "--add-data", "lock_screen.html:.",
    "--name", "FocusPetPro",
    "main.py"
]
subprocess.run(build_cmd)

print("🎉 HOÀN TẤT! File FocusPetPro.app của bạn đã được xuất ra trong thư mục 'dist'")
