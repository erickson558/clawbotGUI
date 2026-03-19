$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$icon = Get-ChildItem -Path $projectRoot -Filter *.ico | Select-Object -First 1
if (-not $icon) {
    throw "No se encontró un archivo .ico en la carpeta del proyecto."
}

$entryPoint = Join-Path $projectRoot "clawbotmanayer.py"
$buildPath = Join-Path $projectRoot "build"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "clawbotGUI" `
  --icon $icon.FullName `
  --distpath $projectRoot `
  --workpath $buildPath `
  --specpath $buildPath `
  $entryPoint

Write-Host "Compilación finalizada. EXE generado en: $projectRoot\\clawbotGUI.exe"
