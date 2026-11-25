[CmdletBinding()]
param(
    [string]$Name = "researchscout_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
)

$ErrorActionPreference = 'Stop'
$backupDir = Join-Path $PSScriptRoot '..\backups'
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backupPath = Join-Path $backupDir $Name
if ($Name -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]*\.dump$') {
    throw 'Name must be a simple filename containing letters, numbers, dots, dashes, or underscores and ending in .dump.'
}

$containerCommand = 'pg_dump --format=custom --no-owner --no-acl --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file "/backups/' + $Name + '"'
docker compose exec -T postgres sh -c $containerCommand
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup failed.' }
Write-Host "Backup saved to $backupPath"
