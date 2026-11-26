# JourneyX AI — Local Run Script (No Docker Required)
# Run from the JourneyX folder: powershell -ExecutionPolicy Bypass -File run_local.ps1

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JourneyX AI — Local Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Kill any existing Streamlit on port 8501 ─────────────────────────────────
$existing = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($existing) {
    $pid8501 = ($existing | Select-Object -First 1).OwningProcess
    if ($pid8501) {
        Write-Host "[INFO] Stopping existing process on port 8501 (PID $pid8501)..." -ForegroundColor Yellow
        Stop-Process -Id $pid8501 -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

# ── Environment ──────────────────────────────────────────────────────────────
$env:PYTHONPATH = "$ROOT\packages;$ROOT\apps"
$env:JOURNEYX_AGENT_DRY_RUN = "true"   # Use heuristic planner (reliable slot filling + find_accommodations)
$env:JOURNEYX_EMBEDDING_FALLBACK = "true"
$env:JOURNEYX_DISABLE_RERANK = "true"
$env:JOURNEYX_UI_USE_API = "auto"

# ── Check venv ────────────────────────────────────────────────────────────────
$python = "$ROOT\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "[ERROR] .venv not found. Run: powershell -File scripts\bootstrap_venv.ps1" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Virtual environment found" -ForegroundColor Green

# ── Check credentials ─────────────────────────────────────────────────────────
$creds = "$ROOT\config\credentials.local.yaml"
if (-not (Test-Path $creds)) {
    Write-Host "[WARN] credentials.local.yaml not found — running in DRY_RUN mode" -ForegroundColor Yellow
    $env:JOURNEYX_AGENT_DRY_RUN = "true"
    $env:JOURNEYX_EMBEDDING_FALLBACK = "true"
} else {
    Write-Host "[OK] Credentials found" -ForegroundColor Green
}

# ── Check RAG indexes ─────────────────────────────────────────────────────────
$indexDir = "$ROOT\data\indexes\v1"
if (-not (Test-Path "$indexDir\bm25.pkl")) {
    Write-Host "[INFO] RAG indexes not found — building now..." -ForegroundColor Yellow
    & $python scripts\ingest_corpus.py
    Write-Host "[OK] RAG indexes built" -ForegroundColor Green
} else {
    Write-Host "[OK] RAG indexes ready" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# ── Start FastAPI backend in background ───────────────────────────────────────
Write-Host "[1/2] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    param($root, $python, $pythonpath)
    $env:PYTHONPATH = $pythonpath
    $env:JOURNEYX_AGENT_DRY_RUN = $using:env:JOURNEYX_AGENT_DRY_RUN
    $env:JOURNEYX_EMBEDDING_FALLBACK = $using:env:JOURNEYX_EMBEDDING_FALLBACK
    Set-Location $root
    & $python -m uvicorn api.main:app --app-dir apps --host 127.0.0.1 --port 8000 --reload
} -ArgumentList $ROOT, $python, $env:PYTHONPATH

# Wait for API to start
Start-Sleep -Seconds 4

# ── Start Streamlit UI ────────────────────────────────────────────────────────
Write-Host "[2/2] Starting Streamlit UI on http://localhost:8501 ..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  JourneyX AI is running!" -ForegroundColor Green
Write-Host "  Open: http://localhost:8501" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$env:JOURNEYX_API_URL = "http://127.0.0.1:8000"
$env:JOURNEYX_UI_USE_API = "false"   # Always use local code (bypasses API server)
& $python -m streamlit run apps\ui\streamlit_app.py --server.port 8501 --server.headless false

# Cleanup
Stop-Job $apiJob -ErrorAction SilentlyContinue
Remove-Job $apiJob -ErrorAction SilentlyContinue