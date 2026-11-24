# Run any Python command with Capstone's local venv (never system Python).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
Set-Location $CapstoneRoot

if ($Args.Count -eq 0) {
    & $CapstonePython
} else {
    & $CapstonePython @Args
}
exit $LASTEXITCODE