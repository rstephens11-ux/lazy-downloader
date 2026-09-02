#!/usr/bin/env bash
# Convert assets/monkey-icon.png into an .icns for PyInstaller's --icon flag.
# Usage: ./icon.sh   →  outputs assets/monkey-icon.icns
set -euo pipefail

cd "$(dirname "$0")"

SRC="assets/monkey-icon.png"
OUT="assets/monkey-icon.icns"

if [ ! -f "$SRC" ]; then
  echo "Missing $SRC" >&2
  exit 1
fi

ICONSET="$(mktemp -d)/monkey.iconset"
mkdir -p "$ICONSET"

sips -z 16 16   "$SRC" --out "$ICONSET/icon_16x16.png"       >/dev/null
sips -z 32 32   "$SRC" --out "$ICONSET/icon_16x16@2x.png"    >/dev/null
sips -z 32 32   "$SRC" --out "$ICONSET/icon_32x32.png"       >/dev/null
sips -z 64 64   "$SRC" --out "$ICONSET/icon_32x32@2x.png"    >/dev/null
sips -z 128 128 "$SRC" --out "$ICONSET/icon_128x128.png"     >/dev/null
sips -z 256 256 "$SRC" --out "$ICONSET/icon_128x128@2x.png"  >/dev/null
sips -z 256 256 "$SRC" --out "$ICONSET/icon_256x256.png"     >/dev/null
sips -z 512 512 "$SRC" --out "$ICONSET/icon_256x256@2x.png"  >/dev/null
sips -z 512 512 "$SRC" --out "$ICONSET/icon_512x512.png"     >/dev/null
cp "$SRC" "$ICONSET/icon_512x512@2x.png"

iconutil -c icns "$ICONSET" -o "$OUT"
rm -rf "$(dirname "$ICONSET")"

echo "Wrote $OUT"
