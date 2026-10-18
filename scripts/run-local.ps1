# Startet SolarPilot lokal ohne Docker (Windows): Backend liefert das gebaute Frontend aus.
#   1) cd frontend; npm ci; npm run build
#   2) .\scripts\run-local.ps1          -> http://localhost:8000
param([int]$Port = 8000, [switch]$Demo)

$root = Split-Path -Parent $PSScriptRoot
$env:SOLARPILOT_STATIC_DIR = Join-Path $root "frontend\out"
$env:SOLARPILOT_CONFIG_DIR = Join-Path $root "config"
if ($Demo) { $env:SOLARPILOT_DEMO = "true" }
Set-Location (Join-Path $root "backend")
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
