<#
.SYNOPSIS
    Create a ProducerOS backup from the command line.

.DESCRIPTION
    Equivalent to clicking "Create backup" on the Backup page in the app,
    for scripting or scheduled-task use. Uses the built exe if present,
    otherwise the dev .venv.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuiltExe = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path $BuiltExe) {
    & $BuiltExe backup-create
} elseif (Test-Path $VenvPython) {
    & $VenvPython -m produceros.cli backup-create
} else {
    throw "Neither a built exe ($BuiltExe) nor a dev .venv ($VenvPython) was found. Run scripts\setup_windows.ps1 or scripts\build_windows.ps1 first."
}
