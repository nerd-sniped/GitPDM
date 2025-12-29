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

    python tools/architecture_guard.py
}
finally {
    Pop-Location
}
