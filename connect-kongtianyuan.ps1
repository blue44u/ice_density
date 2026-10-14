$ErrorActionPreference = 'Stop'
$repoUrl = 'https://github.com/blue44u/ice_density.git'
$source = $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows, then reopen the terminal.' }
Set-Location -LiteralPath $source
if (Test-Path -LiteralPath (Join-Path $source '.git')) {
    Write-Host 'Existing repository found. No configuration changes made.'
    git remote -v
    git branch -vv
    git status --short
    exit $LASTEXITCODE
}
$parent = Split-Path -Parent $source
$name = Split-Path -Leaf $source
$staging = Join-Path $parent ($name + '-git-setup')
$backup = Join-Path $parent ($name + '-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $staging) { throw 'Staging folder exists. Inspect it before retrying.' }
if (Test-Path -LiteralPath $backup) { throw 'Backup folder already exists.' }
git clone --branch main $repoUrl $staging
if ($LASTEXITCODE -ne 0) { throw 'Clone failed. Original folder has not been changed.' }
Get-ChildItem -LiteralPath $source -Force | Where-Object { $_.Name -ne 'connect-kongtianyuan.ps1' } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $staging -Recurse -Force
}
Set-Location -LiteralPath $parent
Move-Item -LiteralPath $source -Destination $backup
try {
    Move-Item -LiteralPath $staging -Destination $source
} catch {
    Move-Item -LiteralPath $backup -Destination $source
    throw
}
Set-Location -LiteralPath $source
git remote -v
git branch -vv
git status --short
Write-Host "Original folder backup: $backup"
Write-Host 'Setup complete. No files have been committed or uploaded.'
