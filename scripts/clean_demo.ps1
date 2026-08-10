<#
.SYNOPSIS
    Remove all synthetic demo data loaded via the "Load demo data" step.

.DESCRIPTION
    Deletes exactly the rows created by `produceros demo-load` (tracked by
    a precise manifest at creation time), leaving any of your own real
    catalog data untouched.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuiltExe = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
. "$PSScriptRoot\_python.ps1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    # No project venv: fall back to a PATH Python that has ProducerOS
    # installed, so running from source works without setup_windows.ps1.
    $VenvPython = try { Get-ProducerOSPython -RepoRoot $RepoRoot } catch { $null }
}

if (Test-Path $BuiltExe) {
    & $BuiltExe demo-clean
} elseif ($VenvPython -and (Test-Path $VenvPython)) {
    & $VenvPython -m produceros.cli demo-clean
} else {
    throw "Neither a built exe ($BuiltExe) nor a dev .venv ($VenvPython) was found. Run scripts\setup_windows.ps1 or scripts\build_windows.ps1 first."
}
