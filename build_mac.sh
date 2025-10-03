#!/usr/bin/env bash
set -euo pipefail

# Create virtual environment in .venv if not exists
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip & install pyinstaller
pip install --upgrade pip
pip install pyinstaller

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
