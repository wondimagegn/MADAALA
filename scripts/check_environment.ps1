# EthioContextEval — environment check (Windows PowerShell)
# Local-first: does not require AWS. Does not print secrets.

$ErrorActionPreference = "Continue"
Write-Host "=== EthioContextEval environment check ===" -ForegroundColor Cyan

function Show-Status([string]$name, [bool]$ok, [string]$detail) {
    $mark = if ($ok) { "OK" } else { "MISSING" }
    $color = if ($ok) { "Green" } else { "Yellow" }
    Write-Host ("[{0}] {1}: {2}" -f $mark, $name, $detail) -ForegroundColor $color
}

# Python
$py = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
    $py = (Resolve-Path ".\.venv\Scripts\python.exe").Path
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $py = (Get-Command python).Source
}

if ($py) {
    $ver = & $py --version 2>&1
    Show-Status "Python" $true "$ver ($py)"
} else {
    Show-Status "Python" $false "Not found"
}

Show-Status "Virtual env (.venv)" (Test-Path ".\.venv\Scripts\python.exe") $(if (Test-Path ".\.venv\Scripts\python.exe") { "present" } else { "run: python -m venv .venv" })
if ($env:VIRTUAL_ENV) {
    Write-Host "  Active VIRTUAL_ENV=$env:VIRTUAL_ENV"
} else {
    Write-Host "  Tip: .\.venv\Scripts\Activate.ps1  (or Set-ExecutionPolicy -Scope Process Bypass if needed)"
}

# Core packages (boto3 optional)
if ($py) {
    $pkgs = @("pandas", "numpy", "scipy", "statsmodels", "dotenv", "matplotlib", "pytest", "ruff")
    foreach ($p in $pkgs) {
        $mod = $p
        & $py -c "import $mod" 2>$null
        Show-Status "Package $p" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "import ok" } else { "not importable" })
    }
    & $py -c "import boto3" 2>$null
    Show-Status "Package boto3 (optional AWS)" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "present" } else { "not installed — OK for local pilot" })
}

# Dataset
$ds = ".\data\scenarios.jsonl"
Show-Status "Dataset scenarios.jsonl" (Test-Path $ds) $(if (Test-Path $ds) { $ds } else { "missing" })
if ($py -and (Test-Path $ds)) {
    & $py -m ethiocontexteval.dataset validate $ds
    Show-Status "Dataset validate" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "valid" } else { "invalid" })
}

# Output dirs
foreach ($d in @("results\raw","results\blinded","results\ratings","results\analysis")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
    Show-Status "Dir $d" (Test-Path $d) "ready"
}

# Ollama executable
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    $ov = & ollama --version 2>&1
    Show-Status "Ollama CLI" $true "$ov"
} else {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $candidate) {
        $ov = & $candidate --version 2>&1
        Show-Status "Ollama CLI" $true "$ov ($candidate)"
    } else {
        Show-Status "Ollama CLI" $false "Not found — install from https://ollama.com for local pilot"
    }
}

# Ollama API + models
if ($py) {
    & $py -m ethiocontexteval.models health --provider ollama 2>&1 | ForEach-Object { Write-Host "  $_" }
    Show-Status "Ollama API health" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "reachable" } else { "not reachable" })
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installed / visible models:"
        & $py -m ethiocontexteval.models list --provider ollama 2>&1 | ForEach-Object { Write-Host "  $_" }
    }
}

# Git
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    $gs = & git status -sb 2>&1
    Show-Status "Git" $true "$gs"
} else {
    Show-Status "Git" $false "not on PATH"
}

# AWS optional note
$aws = Get-Command aws -ErrorAction SilentlyContinue
if ($aws) {
    Show-Status "AWS CLI (optional)" $true "present — not required for local Ollama pilot"
} else {
    Show-Status "AWS CLI (optional)" $true "not installed — OK for local pilot"
}

Write-Host "=== check complete ===" -ForegroundColor Cyan
Write-Host "Local pilot provider: ollama | Tests/CI provider: mock | Future funded path: bedrock (optional)"
Write-Host "This script never prints access keys."
