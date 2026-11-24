# Production embedding ingest and live baseline (requires hosted chat and embedding APIs).
param(
    [int]$SmokeMaxAttempts = 6,
    [int]$SmokeRetrySeconds = 15
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
$Root = $CapstoneRoot
$Py = $CapstonePython
Set-Location $Root

$env:JOURNEYX_EMBEDDING_FALLBACK = "false"
$env:JOURNEYX_BASELINE_DRY_RUN = "false"
$env:JOURNEYX_DISABLE_RERANK = "false"

Write-Host "=== API smoke test (retries) ==="
$smokeOk = $false
foreach ($i in 1..$SmokeMaxAttempts) {
    & $Py scripts/test_capstone_api.py 2>&1
    if ($LASTEXITCODE -eq 0) {
        $smokeOk = $true
        break
    }
    if ($i -lt $SmokeMaxAttempts) {
        Write-Host "Smoke attempt $i/$SmokeMaxAttempts failed; retry in ${SmokeRetrySeconds}s (campus/VPN to 103.42.50.41)..."
        Start-Sleep -Seconds $SmokeRetrySeconds
    }
}
if (-not $smokeOk) {
    Write-Host "API smoke failed after $SmokeMaxAttempts attempts — no ingest/baseline ran."
    Write-Host "When online: powershell -File scripts/complete_live_baseline.ps1"
    exit 1
}

Write-Host "=== Production ingest + chunking experiment ==="
& $Py scripts/ingest_corpus.py --experiment
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Retrieval eval ==="
& $Py scripts/run_retrieval_eval.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Live baseline (65 queries x 3 strategies) ==="
& $Py scripts/run_baseline.py --limit 65
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Gates ==="
& $Py scripts/validate_data_gate.py
& $Py scripts/validate_retrieval_gate.py
Write-Host "Done. See docs/baseline_results_summary.md, data/manifest.yaml, reports/retrieval_eval_v1.json"