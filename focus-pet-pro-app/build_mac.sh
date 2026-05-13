#!/bin/bash
echo "Installing requirements..."
pip install pyqt6 pyqt6-webengine pyinstaller

echo "Building Focus Pet Pro for macOS..."
pyinstaller --noconfirm --onedir --windowed --icon "assets/icon.icns" --add-data "assets:assets" --add-data "lock_screen.html:." --name "FocusPetPro" "main.py"

echo "Build complete! You can find your FocusPetPro.app inside the dist folder."
