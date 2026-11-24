# Create Capstone/.venv and install dependencies (run once per machine).
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\CapstoneVenv.ps1")
Set-Location $CapstoneRoot

$venvPy = Join-Path $CapstoneRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host "Creating .venv ..."
    $bootstrap = $null
    foreach ($dir in @(".venv-review", ".venv")) {
        $candidate = Join-Path $CapstoneRoot "$dir\Scripts\python.exe"
        if (Test-Path -LiteralPath $candidate) {
            $bootstrap = $candidate
            break
        }
    }
    if (-not $bootstrap) {
        $bootstrap = (Get-Command python -ErrorAction SilentlyContinue).Source
    }
    if (-not $bootstrap) {
        throw "No Python found to create .venv"
    }
    & $bootstrap -m venv (Join-Path $CapstoneRoot ".venv")
}

& $venvPy -m pip install -r requirements.txt
& $venvPy -m pip install -e .
Write-Host "Ready: $venvPy"