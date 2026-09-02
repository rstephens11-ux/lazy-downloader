#!/usr/bin/env bash
# Build the standalone Lazy Downloader .app with PyInstaller.
# Requires: brew install pyinstaller python-tk@3.14 yt-dlp ffmpeg
set -euo pipefail

cd "$(dirname "$0")"

ICON="${ICON:-}"

if [ -n "$ICON" ]; then
  pyinstaller --windowed --name "Lazy Downloader" --icon "$ICON" --clean lazy_downloader.py
else
  pyinstaller --windowed --name "Lazy Downloader" --clean lazy_downloader.py
fi

echo ""
echo "Built: dist/Lazy Downloader.app"
echo "Install: cp -R \"dist/Lazy Downloader.app\" /Applications/"
