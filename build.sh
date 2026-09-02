#!/usr/bin/env bash
# Build the standalone Lazy Downloader .app with PyInstaller.
# Requires: brew install pyinstaller python-tk@3.14 yt-dlp ffmpeg
set -euo pipefail

cd "$(dirname "$0")"

# Build the .icns from the monkey PNG if it isn't there yet.
ICON="assets/monkey-icon.icns"
if [ ! -f "$ICON" ]; then
  ./icon.sh
fi

pyinstaller --windowed --name "Lazy Downloader" --icon "$ICON" --clean lazy_downloader.py

echo ""
echo "Built: dist/Lazy Downloader.app"
echo "Install: cp -R \"dist/Lazy Downloader.app\" /Applications/"
