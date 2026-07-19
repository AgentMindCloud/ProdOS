<#
.SYNOPSIS
    Run ProducerOS in LAN mode (binds to your machine's private LAN
    address so a paired Android phone on the same network can reach it).

.DESCRIPTION
    Uses the built dist\ProducerOS\ProducerOS.exe if one exists;
    otherwise falls back to running from source via .venv. Never forward
    this port through your router -- LAN mode is for your home network
    only. See docs\ANDROID_PWA.md for the phone-pairing walkthrough.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuiltExe = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path $BuiltExe) {
    Write-Host "Running built executable: $BuiltExe"
    & $BuiltExe run --mode lan
} elseif (Test-Path $VenvPython) {
    Write-Host "Running from source via .venv"
    & $VenvPython -m produceros.cli run --mode lan
} else {
    throw "Neither a built exe ($BuiltExe) nor a dev .venv ($VenvPython) was found. Run scripts\setup_windows.ps1 or scripts\build_windows.ps1 first."
}
