<#
.SYNOPSIS
    Shared helper: find the Python interpreter that has ProducerOS installed.

.DESCRIPTION
    Dot-source this from other scripts:  . "$PSScriptRoot\_python.ps1"

    Prefers the repo's own .venv (the normal developer setup created by
    scripts\setup_windows.ps1), but falls back to whatever `python` is on
    PATH. That fallback is not a nicety -- CI installs ProducerOS into the
    runner's system Python rather than a virtual environment, so scripts
    that hard-required .venv failed instantly on every GitHub Actions run.
#>

function Get-ProducerOSPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    foreach ($candidate in @("python", "python3", "py")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            # Only accept an interpreter that can actually import ProducerOS,
            # so we fail with a useful message rather than deep inside a build.
            & $command.Source -c "import produceros" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $command.Source
            }
        }
    }

    throw @"
Could not find a Python interpreter with ProducerOS installed.

Either create the project virtual environment:
    .\scripts\setup_windows.ps1

or install ProducerOS into the Python already on your PATH:
    pip install -e ".[dev]"
"@
}
