# Pre-deploy: sync local Postgres -> Neon, then you can git push / Railway deploy.
#
# Usage (from zenkimpact_BE):
#   .\sync-db-to-neon.ps1
#   .\sync-db-to-neon.ps1 -Check          # compare only
#   .\sync-db-to-neon.ps1 -Yes            # skip confirmation
#
# Requires: .env with DATABASE_URL (local) and NEON_DATABASE_URL (Neon).

param(
    [switch]$Check,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "venv not found. Create it first, then re-run."
    exit 1
}

$argsList = @("scripts\sync_local_to_neon.py")
if ($Check) { $argsList += "--check" }
if ($Yes) { $argsList += "--yes" }

$env:PYTHONIOENCODING = "utf-8"
& $py @argsList
exit $LASTEXITCODE
