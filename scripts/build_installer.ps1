<#
.SYNOPSIS
    Build the full ProducerOS-Setup-<version>.exe installer: PyInstaller
    bundle + Inno Setup compiler.

.DESCRIPTION
    This is what a non-technical user actually downloads and
    double-clicks -- a single .exe that installs ProducerOS with a Start
    Menu entry and (optionally) a desktop icon, no admin rights required.
    See packaging/inno/producer-os.iss and docs/adr/0006-inno-setup-installer.md.

    Requires Inno Setup (ISCC.exe) in addition to the usual Python dev
    setup. Install it from https://jrsoftware.org/isdl.php if you don't
    have it -- GitHub's windows-latest Actions runner already includes
    it, so CI (.github/workflows/windows-build.yml) needs no extra setup.

.PARAMETER Version
    Version string to embed in the installer (e.g. "1.2.3"). Defaults to
    the version in pyproject.toml.
#>

param(
    [string]$Version
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "No .venv found at $VenvPython. Run scripts\setup_windows.ps1 first."
}

if (-not $Version) {
    $pyprojectText = Get-Content (Join-Path $RepoRoot "pyproject.toml") -Raw
    if ($pyprojectText -match 'version\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    } else {
        throw "Could not determine a version from pyproject.toml; pass -Version explicitly."
    }
}
Write-Host "Building ProducerOS installer version $Version"

function Find-InnoSetupCompiler {
    $onPath = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    return $null
}

$iscc = Find-InnoSetupCompiler
if (-not $iscc) {
    throw "Inno Setup's ISCC.exe was not found. Install Inno Setup from https://jrsoftware.org/isdl.php (default install location is fine) and re-run this script."
}
Write-Host "Using Inno Setup compiler: $iscc"

Push-Location $RepoRoot
try {
    Write-Host "==> Building the PyInstaller bundle"
    & $VenvPython -m PyInstaller packaging\pyinstaller\produceros.spec --noconfirm

    $exePath = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
    if (-not (Test-Path $exePath)) {
        throw "PyInstaller build finished but $exePath was not produced."
    }

    Write-Host "==> Compiling the installer with Inno Setup"
    & $iscc "/DMyAppVersion=$Version" "packaging\inno\producer-os.iss"

    $installerPath = Join-Path $RepoRoot "installer-output\ProducerOS-Setup-$Version.exe"
    if (-not (Test-Path $installerPath)) {
        throw "Inno Setup finished but $installerPath was not produced -- check the ISCC output above."
    }

    Write-Host ""
    Write-Host "Installer built: $installerPath"
    Write-Host "This is the single file to share -- double-clicking it installs ProducerOS with Start Menu + desktop shortcuts, no admin rights needed."
} finally {
    Pop-Location
}
