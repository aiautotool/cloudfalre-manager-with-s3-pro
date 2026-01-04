#!/bin/bash

# Stop script on error
set -e

APP_NAME="Seohtmls3"
SPEC_FILE="Seohtmls3.spec"
VERSION="1.1.2"

echo "-----------------------------------"
echo "Starting Rebuild for $APP_NAME..."
echo "-----------------------------------"

# Cleanup stale mounts to prevent issues
echo "[0/3] Checking for stale volumes..."
# Unmount any volumes starting with the App Name (wildcard expansion)
for v in "/Volumes/${APP_NAME}"*; do
    if [ -d "$v" ]; then
        echo "Unmounting stale volume: $v"
        hdiutil detach "$v" -force || true
    fi
done

# 1. Clean previous builds
echo "[1/3] Cleaning build directories..."
rm -rf build dist
rm -f *.dmg

# 2. Build with PyInstaller
echo "[2/3] Running PyInstaller..."
pyinstaller "$SPEC_FILE" --clean --noconfirm

# 3. Create DMG (using native hdiutil for reliability)
echo "[3/3] Creating DMG installer..."
hdiutil create -volname "$APP_NAME" -srcfolder "dist/$APP_NAME.app" -ov -format UDZO "$APP_NAME.dmg"

echo "✅ Build Success! Installer created: $APP_NAME.dmg"
