# Update forward records (run about once a month, or more often).
#   powershell -ExecutionPolicy Bypass -File scripts\update_and_record.ps1
# Steps: 1. fetch new J-Quants data (already-fetched days are skipped by the checkpoint)  2. build processed tables
#        3. record forward predictions  4. score and summarize.
# This file is ASCII only on purpose (Windows PowerShell 5.1 misreads UTF-8 without BOM).
# The API key is asked each time (hidden, never written to a file). Never paste it in chat.
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $env:JQUANTS_API_KEY) {
    $sec = Read-Host "J-Quants API key" -AsSecureString
    $env:JQUANTS_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}
function Run($cmd) {
    Write-Host ">>> $cmd"
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { throw "failed: $cmd (exit $LASTEXITCODE)" }
}
Run "git pull"
Run "python scripts/jquants/backfill.py --execute"
Run "python scripts/jquants/build_processed.py"
Run "python scripts/w5/forward.py record"
Run "python scripts/w5/forward_s2.py record"
Run "python scripts/w5/forward_events.py record"
Run "python scripts/w5/forward.py score"
Run "python scripts/w5/forward_s2.py score"
Run "python scripts/w5/forward_events.py score"
Run "python scripts/w5/forward.py summary"
Run "python scripts/w5/forward_s2.py summary"
Run "python scripts/w5/forward_events.py summary"
Remove-Item Env:JQUANTS_API_KEY -ErrorAction SilentlyContinue
Write-Host "Done. Paste the summary output above (aggregates only)."
