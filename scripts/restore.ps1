<#
.SYNOPSIS
    Restore ProducerOS's database from a backup file.

.DESCRIPTION
    Destructive: replaces the live database (a pre-restore safety copy is
    still taken automatically, see docs\BACKUP_RESTORE.md). Always runs a
    dry-run preview (integrity check + table row counts) first and asks
    for typed confirmation before touching anything.

.PARAMETER BackupPath
    Path to the .db backup file to restore, e.g.
    %LOCALAPPDATA%\ProducerOS\backups\produceros_20260101T000000Z.db

.EXAMPLE
    .\scripts\restore.ps1 -BackupPath "$env:LOCALAPPDATA\ProducerOS\backups\produceros_20260101T000000Z.db"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuiltExe = Join-Path $RepoRoot "dist\ProducerOS\ProducerOS.exe"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path $BuiltExe) {
    $Runner = { param($cliArgs) & $BuiltExe @cliArgs }
} elseif (Test-Path $VenvPython) {
    $Runner = { param($cliArgs) & $VenvPython -m produceros.cli @cliArgs }
} else {
    throw "Neither a built exe ($BuiltExe) nor a dev .venv ($VenvPython) was found. Run scripts\setup_windows.ps1 or scripts\build_windows.ps1 first."
}

if (-not (Test-Path $BackupPath)) {
    throw "Backup file not found: $BackupPath"
}

Write-Host "==> Dry-run preview of $BackupPath"
& $Runner @("restore-dry-run", $BackupPath)

Write-Host ""
Write-Host "This will REPLACE your live ProducerOS database with the backup above."
$confirmation = Read-Host 'Type RESTORE (all caps) to proceed, anything else to cancel'
if ($confirmation -cne "RESTORE") {
    Write-Host "Cancelled. No changes made."
    exit 1
}

& $Runner @("restore", $BackupPath, "--yes")
