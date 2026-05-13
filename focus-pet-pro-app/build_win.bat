@echo off
echo Installing requirements...
pip install pyqt6 pyqt6-webengine pyinstaller

echo Building Focus Pet Pro for Windows...
pyinstaller --noconfirm --onedir --windowed --icon "assets/icon.ico" --add-data "assets;assets/" --add-data "lock_screen.html;." --name "FocusPetPro" "main.py"

echo Build complete! You can find your .exe inside the "dist/FocusPetPro" folder.
pause
