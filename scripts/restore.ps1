[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [string]$Backup
)

$ErrorActionPreference = 'Stop'
$backupDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\backups'))
$backupPath = [IO.Path]::GetFullPath($Backup)
if ([IO.Path]::GetFileName($backupPath) -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]*\.dump$' -or
    -not $backupPath.StartsWith($backupDir + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    -not (Test-Path -LiteralPath $backupPath -PathType Leaf) -or
    [IO.Path]::GetExtension($backupPath) -ne '.dump') {
    throw "Choose an existing .dump file inside $backupDir"
}
$fileName = [IO.Path]::GetFileName($backupPath)
if ($PSCmdlet.ShouldProcess('ResearchScout PostgreSQL database', "Replace database contents from $fileName")) {
    docker compose stop backend worker crawler scheduler
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop application services.' }
    $containerCommand = 'pg_restore --clean --if-exists --no-owner --no-acl --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "/backups/' + $fileName + '"'
    docker compose exec -T postgres sh -c $containerCommand
    if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }
    Write-Host 'Restore finished. Start services with: docker compose up -d'
}
