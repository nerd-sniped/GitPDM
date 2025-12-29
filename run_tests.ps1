$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot
try {
    # Prefer pytest if available; otherwise run a stdlib-only test runner.
    $hasPytest = $false
    try {
        & python -c "import pytest" 2>$null
        $hasPytest = ($LASTEXITCODE -eq 0)
    } catch {
        $hasPytest = $false
    }

    if ($hasPytest) {
        python -m pytest
    }
    else {
        python tools/stdlib_test_runner.py
    }

    # Optional lint: run ruff if installed.
    $hasRuff = $false
    try {
        & python -c "import ruff" 2>$null
        $hasRuff = ($LASTEXITCODE -eq 0)
    } catch {
        $hasRuff = $false
    }

    if ($hasRuff) {
        python -m ruff check .
    }

    python tools/architecture_guard.py
}
finally {
    Pop-Location
}
