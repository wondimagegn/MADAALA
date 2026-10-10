# EthioContextEval — local Ollama pilot workflow (Windows PowerShell)
# Will NOT run model inference unless you explicitly confirm.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== EthioContextEval local pilot (Ollama) ===" -ForegroundColor Cyan

try {
    if (-not $env:VIRTUAL_ENV) {
        if (Test-Path ".\.venv\Scripts\Activate.ps1") {
            . .\.venv\Scripts\Activate.ps1
        }
    }
} catch {
    Write-Host "Activation blocked by execution policy. Trying process-scoped Bypass..." -ForegroundColor Yellow
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    . .\.venv\Scripts\Activate.ps1
}

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "ERROR: .venv not found. Create with: python -m venv .venv" -ForegroundColor Red
    exit 1
}

$config = "config\models.local.json"
if (-not (Test-Path $config)) {
    Write-Host "ERROR: missing $config" -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/8] Validate dataset"
& $py -m ethiocontexteval.dataset validate data\scenarios.jsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/8] Ollama health"
& $py -m ethiocontexteval.models health --provider ollama
$healthCode = $LASTEXITCODE

Write-Host "`n[3/8] List installed models"
& $py -m ethiocontexteval.models list --provider ollama --config $config

Write-Host "`n[4/8] Verify configured models"
& $py -m ethiocontexteval.models check --provider ollama --config $config
$checkCode = $LASTEXITCODE

Write-Host "`n[5/8] Dry run (no inference)"
& $py -m ethiocontexteval.runner --provider ollama --config $config --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Dry run complete. Local model inference is NOT started yet." -ForegroundColor Yellow
Write-Host "Confirm only after models are installed and expected generation count looks correct." -ForegroundColor Yellow
$confirm = Read-Host "Type EXECUTE to run local generations (anything else aborts)"

if ($confirm -ne "EXECUTE") {
    Write-Host "Aborted. No model generations were run." -ForegroundColor Green
    exit 0
}

if ($healthCode -ne 0 -or $checkCode -ne 0) {
    Write-Host "Ollama health or model check failed. Aborting execute for safety." -ForegroundColor Red
    Write-Host "Install Ollama and pull candidate models manually (this repo does not auto-download)."
    exit 2
}

Write-Host "`n[6/8] Execute local generations"
& $py -m ethiocontexteval.runner --provider ollama --config $config --execute
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[7/8] Anonymize latest generations"
$latest = Get-ChildItem .\results\raw\generations_*.jsonl -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) {
    Write-Host "No generations file found." -ForegroundColor Red
    exit 1
}
& $py -m ethiocontexteval.anonymize $latest.FullName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[8/8] Rating template from latest blinded CSV"
$blinded = Get-ChildItem .\results\blinded\blinded_responses_*.csv -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($blinded) {
    & $py -m ethiocontexteval.human_evaluation template $blinded.FullName
}

Write-Host "`nLocal generation+blind workflow finished." -ForegroundColor Green
Write-Host "Complete human ratings before interpreting results. Mock/Ollama outputs are not self-validated science."
