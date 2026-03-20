$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$entryPoint = Join-Path $projectRoot "clawbotmanayer.py"
$specPath = Join-Path $projectRoot "build"
$workPath = Join-Path $env:TEMP ("clawbotGUI-pyinstaller-" + (Get-Date -Format "yyyyMMddHHmmss"))
$icon = Get-ChildItem -LiteralPath $projectRoot -Filter *.ico | Sort-Object Name | Select-Object -First 1

if (-not $icon) {
    throw "No se encontró un archivo .ico en la carpeta del proyecto."
}

$versionFields = python -c "from app_version import APP_AUTHOR, APP_NAME, APP_VERSION, APP_VERSION_TAG; print('|'.join((APP_AUTHOR, APP_NAME, APP_VERSION, APP_VERSION_TAG)))"
if ($LASTEXITCODE -ne 0 -or -not $versionFields) {
    throw "No se pudo leer la versión de app_version.py"
}

$appAuthor, $appName, $appVersion, $appVersionTag = $versionFields.Trim() -split '\|', 4
$versionTuple = (($appVersion -split '\.') + '0') -join ', '

New-Item -ItemType Directory -Force -Path $specPath | Out-Null
New-Item -ItemType Directory -Force -Path $workPath | Out-Null

$versionFile = Join-Path $workPath "file_version_info.txt"
$versionFileContent = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($versionTuple),
    prodvers=($versionTuple),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '$appAuthor'),
            StringStruct('FileDescription', '$appName'),
            StringStruct('FileVersion', '$appVersionTag'),
            StringStruct('InternalName', 'clawbotGUI'),
            StringStruct('OriginalFilename', 'clawbotGUI.exe'),
            StringStruct('ProductName', '$appName'),
            StringStruct('ProductVersion', '$appVersionTag')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
Set-Content -LiteralPath $versionFile -Value $versionFileContent -Encoding utf8

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "clawbotGUI" `
  --icon $icon.FullName `
  --version-file $versionFile `
  --distpath $projectRoot `
  --workpath $workPath `
  --specpath $specPath `
  $entryPoint

if (Test-Path $workPath) {
    Remove-Item -LiteralPath $workPath -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Compilación finalizada para $appVersionTag. EXE generado en: $projectRoot\\clawbotGUI.exe"
