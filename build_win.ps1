# Build Windows executable for txedge GUI using PyInstaller
# Requires: pip install pyinstaller

$ErrorActionPreference = "Stop"

# Ensure venv/python available (assumes python in PATH)
python -m pip install --upgrade pip
python -m pip install pyinstaller

# Paths
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptsDir = Join-Path $projectRoot "Scripts"
$entry = Join-Path $scriptsDir "txedge_gui.py"
$outDir = $projectRoot

# Include Scripts package so imports work
pyinstaller `
  --noconfirm `
  --onefile `
  --clean `
  --name txedge_gui `
  --add-data "$scriptsDir;Scripts" `
  "$entry"

Write-Host "Build complete. Output located in 'dist/txedge_gui.exe'."
