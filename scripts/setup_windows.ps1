<#
.SYNOPSIS
    One-time developer setup: creates a Python virtual environment and
    installs ProducerOS in editable mode with its dev dependencies.

.DESCRIPTION
    Run this once after cloning the repository, before using
    run_desktop.ps1 / run_lan.ps1 / run_tests.ps1 / build_windows.ps1.
    Requires Python 3.11+ already installed and on PATH (this script does
    not install Python itself). End users who just want to run ProducerOS
    do NOT need this script -- they use the built ProducerOS.exe instead.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-PythonCommand {
    foreach ($candidate in @("py -3.12", "py -3", "python3", "python")) {
        $exe, $arg = $candidate.Split(" ", 2)
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }
    throw "No Python 3.11+ interpreter found on PATH. Install Python from https://python.org and re-run this script."
}

$pythonCmd = Get-PythonCommand
Write-Host "Using Python launcher: $pythonCmd"

Push-Location $RepoRoot
try {
    if (-not (Test-Path ".venv")) {
        Write-Host "Creating virtual environment at .venv ..."
        Invoke-Expression "$pythonCmd -m venv .venv"
    } else {
        Write-Host ".venv already exists, reusing it."
    }

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    Write-Host "Installing ProducerOS (editable) with dev dependencies ..."
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e ".[dev]"

    Write-Host ""
    Write-Host "Setup complete. Next steps:"
    Write-Host "  .\scripts\run_tests.ps1     - run the test suite"
    Write-Host "  .\scripts\run_desktop.ps1   - run ProducerOS locally (desktop mode)"
    Write-Host "  .\scripts\build_windows.ps1 - build the standalone .exe"
} finally {
    Pop-Location
}
