# Run the full JourneyX pytest suite using the repository virtualenv.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
Set-Location $CapstoneRoot

Write-Host "=== pytest use-case suite ==="
& $CapstonePython -m pip install -q -e ".[dev]" | Out-Null
& $CapstonePython -m pytest tests/ -v --tb=short
exit $LASTEXITCODE