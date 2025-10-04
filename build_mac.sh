#!/usr/bin/env bash
set -euo pipefail

# Paths
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/Scripts"
ENTRY="$SCRIPTS_DIR/txedge_gui.py"
ICON_PATH="$PROJECT_ROOT/Scripts/app.icns"   # <- put your .icns here if you want a custom icon

# Create virtual environment in .venv if not exists
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip & install pyinstaller
pip install --upgrade pip
pip install pyinstaller

# PyInstaller args
ARGS=(
  --noconfirm
  --onefile
  --windowed        # <- prevents terminal from staying open
  --clean
  --name txedge_gui
  --add-data "$SCRIPTS_DIR:Scripts"
)

# If icon file exists, add it
if [ -f "$ICON_PATH" ]; then
  echo "Using icon: $ICON_PATH"
  ARGS+=( --icon "$ICON_PATH" )
else
  echo "No icon found at $ICON_PATH, building without one."
fi

# Build
pyinstaller "${ARGS[@]}" "$ENTRY"

echo "✅ Build complete."
echo "   Executable: dist/txedge_gui"
echo "   App Bundle: dist/txedge_gui.app"
