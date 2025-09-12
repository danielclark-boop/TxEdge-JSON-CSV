#!/usr/bin/env bash
set -euo pipefail

# Build macOS executable for txedge GUI using PyInstaller
# Requires: python3 -m pip install pyinstaller

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/Scripts"
ENTRY="$SCRIPTS_DIR/txedge_gui.py"

pyinstaller \
  --noconfirm \
  --onefile \
  --clean \
  --name txedge_gui \
  --add-data "$SCRIPTS_DIR:Scripts" \
  "$ENTRY"

echo "Build complete. Output located in dist/txedge_gui"
