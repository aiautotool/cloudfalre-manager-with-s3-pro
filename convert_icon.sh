#!/bin/bash
set -e

SOURCE="new_icon_source.png"
ICONSET="Seohtmls3.iconset"
ICNS="Seohtmls3.icns"

echo "Creating iconset directory..."
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

echo "Resizing images..."
# sips needs explicit format setting to avoid warnings/errors and ensure PNG
sips -z 16 16     "$SOURCE" --setProperty format png --out "$ICONSET/icon_16x16.png"
sips -z 32 32     "$SOURCE" --setProperty format png --out "$ICONSET/icon_16x16@2x.png"
sips -z 32 32     "$SOURCE" --setProperty format png --out "$ICONSET/icon_32x32.png"
sips -z 64 64     "$SOURCE" --setProperty format png --out "$ICONSET/icon_32x32@2x.png"
sips -z 128 128   "$SOURCE" --setProperty format png --out "$ICONSET/icon_128x128.png"
sips -z 256 256   "$SOURCE" --setProperty format png --out "$ICONSET/icon_128x128@2x.png"
sips -z 256 256   "$SOURCE" --setProperty format png --out "$ICONSET/icon_256x256.png"
sips -z 512 512   "$SOURCE" --setProperty format png --out "$ICONSET/icon_256x256@2x.png"
sips -z 512 512   "$SOURCE" --setProperty format png --out "$ICONSET/icon_512x512.png"
sips -z 1024 1024 "$SOURCE" --setProperty format png --out "$ICONSET/icon_512x512@2x.png"

echo "Converting to .icns..."
iconutil -c icns "$ICONSET"

echo "Replacing existing icns..."
rm -rf "$ICONSET"
echo "✅ New Icon created: $ICNS"
