#!/bin/bash
echo "Đang tạo icon cho ứng dụng..."

IMG="/Users/hoainam/.gemini/antigravity/brain/9e5bc79a-9a0d-4b48-a6ae-4abc2dea90f8/focus_pet_icon_1778695633391.png"

# Copy the generated image to assets
cp "$IMG" assets/icon.png

# Create macOS icon (.icns)
mkdir MyIcon.iconset
sips -z 16 16     assets/icon.png --out MyIcon.iconset/icon_16x16.png > /dev/null
sips -z 32 32     assets/icon.png --out MyIcon.iconset/icon_16x16@2x.png > /dev/null
sips -z 32 32     assets/icon.png --out MyIcon.iconset/icon_32x32.png > /dev/null
sips -z 64 64     assets/icon.png --out MyIcon.iconset/icon_32x32@2x.png > /dev/null
sips -z 128 128   assets/icon.png --out MyIcon.iconset/icon_128x128.png > /dev/null
sips -z 256 256   assets/icon.png --out MyIcon.iconset/icon_128x128@2x.png > /dev/null
sips -z 256 256   assets/icon.png --out MyIcon.iconset/icon_256x256.png > /dev/null
sips -z 512 512   assets/icon.png --out MyIcon.iconset/icon_256x256@2x.png > /dev/null
sips -z 512 512   assets/icon.png --out MyIcon.iconset/icon_512x512.png > /dev/null
sips -z 1024 1024 assets/icon.png --out MyIcon.iconset/icon_512x512@2x.png > /dev/null

iconutil -c icns MyIcon.iconset -o assets/icon.icns
rm -R MyIcon.iconset

# Create Windows icon (.ico) using python
python3 -c "from PIL import Image; img = Image.open('assets/icon.png'); img.save('assets/icon.ico')"

echo "Đã tạo thành công icon.icns (cho Mac) và icon.ico (cho Windows) trong thư mục assets!"
