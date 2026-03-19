$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$icon = Get-ChildItem -Path $projectRoot -Filter *.ico | Select-Object -First 1
if (-not $icon) {
    throw "No se encontró un archivo .ico en la carpeta del proyecto."
}

$entryPoint = Join-Path $projectRoot "clawbotmanayer.py"
$specPath = Join-Path $projectRoot "build"
$workPath = Join-Path $env:TEMP ("clawbotGUI-pyinstaller-" + (Get-Date -Format "yyyyMMddHHmmss"))

New-Item -ItemType Directory -Force -Path $specPath | Out-Null

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "clawbotGUI" `
  --icon $icon.FullName `
  --distpath $projectRoot `
  --workpath $workPath `
  --specpath $specPath `
  $entryPoint

if (Test-Path $workPath) {
    Remove-Item -LiteralPath $workPath -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Compilación finalizada. EXE generado en: $projectRoot\\clawbotGUI.exe"
