# Resolve repository-local Python (.venv or .venv-review). Dot-source from scripts/*.ps1.
$script:CapstoneRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Get-CapstonePythonPath {
    foreach ($dir in @(".venv", ".venv-review")) {
        $py = Join-Path $CapstoneRoot "$dir\Scripts\python.exe"
        if (Test-Path -LiteralPath $py) {
            return $py
        }
    }
    throw @"
Capstone virtualenv not found.

  cd $CapstoneRoot
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt -e .
"@
}

function Use-CapstonePythonEnv {
    $env:PYTHONPATH = Join-Path $CapstoneRoot "packages"
}

$script:CapstonePython = Get-CapstonePythonPath
Use-CapstonePythonEnv