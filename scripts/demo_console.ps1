# Interactive console demo (LangGraph agent; no HTTP server).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
Set-Location $CapstoneRoot

$env:PYTHONPATH = Join-Path $CapstoneRoot "packages"
if (-not $env:JOURNEYX_AGENT_DRY_RUN) { $env:JOURNEYX_AGENT_DRY_RUN = "true" }
if (-not $env:JOURNEYX_EMBEDDING_FALLBACK) { $env:JOURNEYX_EMBEDDING_FALLBACK = "true" }
if (-not $env:JOURNEYX_DISABLE_RERANK) { $env:JOURNEYX_DISABLE_RERANK = "true" }

$demoScript = Join-Path $PSScriptRoot "demo_console.py"
if ($Args.Count -eq 0) {
    & $CapstonePython $demoScript
} else {
    & $CapstonePython $demoScript @Args
}
exit $LASTEXITCODE