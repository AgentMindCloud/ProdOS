<#
.SYNOPSIS
    Run the full ProducerOS validation suite: lint, type-check, and tests.

.DESCRIPTION
    Mirrors what CI runs (see .github/workflows/ci.yml). Playwright's
    Chromium must already be installed (`python -m playwright install
    chromium`) for the e2e suite to run; pass -SkipE2E to skip it on a
    machine without a browser available.
#>

param(
    [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "No .venv found at $VenvPython. Run scripts\setup_windows.ps1 first."
}

Push-Location $RepoRoot
try {
    Write-Host "==> ruff format --check"
    & $VenvPython -m ruff format --check src tests

    Write-Host "==> ruff check"
    & $VenvPython -m ruff check src tests

    Write-Host "==> mypy"
    & $VenvPython -m mypy src

    Write-Host "==> pytest (unit, integration, security)"
    & $VenvPython -m pytest tests/unit tests/integration tests/security -q

    if (-not $SkipE2E) {
        Write-Host "==> pytest (e2e)"
        & $VenvPython -m pytest tests/e2e -q
    } else {
        Write-Host "==> skipping e2e (per -SkipE2E)"
    }

    Write-Host ""
    Write-Host "All checks passed."
} finally {
    Pop-Location
}
