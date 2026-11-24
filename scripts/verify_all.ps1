# Full verification in repo-local venv (.venv or .venv-review)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
$Root = $CapstoneRoot
$Py = $CapstonePython
$env:JOURNEYX_EMBEDDING_FALLBACK = "true"
$env:JOURNEYX_DISABLE_RERANK = "true"

Set-Location $Root
Write-Host "=== compileall ===" 
& $Py -m compileall packages scripts -q

Write-Host "=== validate_data_gate ==="
& $Py scripts/validate_data_gate.py

Write-Host "=== ingest_corpus ==="
& $Py scripts/ingest_corpus.py

Write-Host "=== run_retrieval_eval ==="
& $Py scripts/run_retrieval_eval.py

Write-Host "=== validate_retrieval_gate ==="
& $Py scripts/validate_retrieval_gate.py

Write-Host "=== pytest (deps from pyproject) ==="
& $Py -m pip install -q -e ".[dev]" | Out-Null
& $Py -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== validate_agent_gate ==="
& $Py scripts/validate_agent_gate.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== tool smoke ==="
& $Py -c @"
from journeyx.tools.search_kb import search_travel_kb
from journeyx.tools.transport import compare_transport, get_route_info
r = search_travel_kb('Jaipur Amber Fort', dest_id='dest_jaipur', top_k=3)
assert r['chunks'], 'no kb chunks'
t = compare_transport('city_delhi', 'city_jaipur', 2)
assert any(m['mode']=='road_diesel' for m in t['modes'])
g = get_route_info('city_delhi', 'city_jaipur')
assert g['distance_km'] > 0
print('tool_smoke: OK', len(r['chunks']), 'chunks')
"@

Write-Host "=== validate_release_gate ==="
& $Py scripts/validate_release_gate.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== ALL PASSED ==="