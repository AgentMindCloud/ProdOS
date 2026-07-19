<#
.SYNOPSIS
    Run ProducerOS in desktop mode (binds to 127.0.0.1 only, opens your
    browser automatically).

.DESCRIPTION
    Uses the built dist\ProducerOS\ProducerOS.exe if one exists (the
    normal end-user path); otherwise falls back to running from source
    via the .venv created by setup_windows.ps1 (the developer path).
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuiltExe = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path $BuiltExe) {
    Write-Host "Running built executable: $BuiltExe"
    & $BuiltExe run --mode desktop
} elseif (Test-Path $VenvPython) {
    Write-Host "Running from source via .venv"
    & $VenvPython -m produceros.cli run --mode desktop
} else {
    throw "Neither a built exe ($BuiltExe) nor a dev .venv ($VenvPython) was found. Run scripts\setup_windows.ps1 or scripts\build_windows.ps1 first."
}
