# EthioContextEval — environment check (Windows PowerShell)
# Does not print secrets.

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

# venv
$inVenv = $env:VIRTUAL_ENV -or (Test-Path ".\.venv\Scripts\python.exe")
Show-Status "Virtual env (.venv)" (Test-Path ".\.venv\Scripts\python.exe") $(if (Test-Path ".\.venv\Scripts\python.exe") { "present" } else { "run: python -m venv .venv" })
if ($env:VIRTUAL_ENV) {
    Write-Host "  Active VIRTUAL_ENV=$env:VIRTUAL_ENV"
} else {
    Write-Host "  Tip: .\.venv\Scripts\Activate.ps1  (or Set-ExecutionPolicy -Scope Process Bypass if needed)"
}

# Packages
if ($py) {
    $pkgs = @("boto3", "pandas", "numpy", "scipy", "statsmodels", "dotenv", "matplotlib", "pytest", "ruff")
    foreach ($p in $pkgs) {
        $mod = if ($p -eq "dotenv") { "dotenv" } else { $p }
        & $py -c "import $mod" 2>$null
        Show-Status "Package $p" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "import ok" } else { "not importable" })
    }
}

# Dataset
$ds = ".\data\scenarios.jsonl"
Show-Status "Dataset scenarios.jsonl" (Test-Path $ds) $(if (Test-Path $ds) { $ds } else { "missing" })
$dsEn = ".\data\pilot_scenarios_en.jsonl"
Show-Status "Dataset pilot_scenarios_en.jsonl" (Test-Path $dsEn) $(if (Test-Path $dsEn) { $dsEn } else { "missing" })

if ($py -and (Test-Path $ds)) {
    & $py -m ethiocontexteval.dataset validate $ds
    Show-Status "Dataset validate" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "valid" } else { "invalid" })
}

# AWS CLI
$aws = Get-Command aws -ErrorAction SilentlyContinue
if ($aws) {
    $awsVer = & aws --version 2>&1
    Show-Status "AWS CLI" $true "$awsVer"
} else {
    Show-Status "AWS CLI" $false "Not on PATH (needed for easy credential setup)"
}

# Region
$region = $env:AWS_REGION
if (-not $region) { $region = $env:AWS_DEFAULT_REGION }
if (-not $region) { $region = "us-east-1 (default fallback in app)" }
Show-Status "AWS region env" $true "$region"

# Identity (no secrets)
if ($aws) {
    Write-Host "Checking aws sts get-caller-identity (Account/Arn/UserId only)..."
    & aws sts get-caller-identity 2>&1 | ForEach-Object { Write-Host "  $_" }
    Show-Status "AWS identity" ($LASTEXITCODE -eq 0) $(if ($LASTEXITCODE -eq 0) { "credentials resolved" } else { "not configured or denied" })
} else {
    Show-Status "AWS identity" $false "skipped (no AWS CLI)"
}

Write-Host "=== check complete ===" -ForegroundColor Cyan
Write-Host "This script never prints access keys. Configure credentials with 'aws configure' or env vars outside git."
