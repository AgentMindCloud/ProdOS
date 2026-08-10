<#
.SYNOPSIS
    Build the standalone ProducerOS.exe with PyInstaller.

.DESCRIPTION
    Produces dist\ProducerOS\ (a onedir build: ProducerOS.exe plus an
    _internal\ folder with the bundled Python runtime, templates, static
    assets, and Alembic migrations). Zip the whole dist\ProducerOS\
    folder to distribute it -- see packaging\README.md.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"
$VenvPython = Get-ProducerOSPython -RepoRoot $RepoRoot
Write-Host "Using Python: $VenvPython"

Push-Location $RepoRoot
try {
    Write-Host "==> Building with PyInstaller"
    & $VenvPython -m PyInstaller packaging\pyinstaller\produceros.spec --noconfirm

    $exePath = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
    if (-not (Test-Path $exePath)) {
        throw "Build finished but $exePath was not produced -- check the PyInstaller output above."
    }

    Write-Host ""
    Write-Host "Build complete: $exePath"
    Write-Host "Run it with .\scripts\run_desktop.ps1, or zip dist\ProducerOS\ to distribute it."
} finally {
    Pop-Location
}
