# EthioContextEval — safe pilot workflow (Windows PowerShell)
# Will NOT call Bedrock unless you explicitly confirm.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== EthioContextEval pilot runner ===" -ForegroundColor Cyan

# Session-level execution policy workaround if needed (does not change machine policy)
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

Write-Host "`n[1/7] Validate dataset"
& $py -m ethiocontexteval.dataset validate data\scenarios.jsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/7] List/check Bedrock models (requires AWS creds)"
& $py -m ethiocontexteval.models list
$modelsListCode = $LASTEXITCODE
& $py -m ethiocontexteval.models check
$modelsCheckCode = $LASTEXITCODE

Write-Host "`n[3/7] Dry run (no Bedrock calls)"
& $py -m ethiocontexteval.runner --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Dry run complete. Paid Bedrock inference is NOT started yet." -ForegroundColor Yellow
Write-Host "Next step would invoke Amazon Bedrock and may incur cost." -ForegroundColor Yellow
$confirm = Read-Host "Type EXECUTE to run real generations (anything else aborts)"

if ($confirm -ne "EXECUTE") {
    Write-Host "Aborted. No Bedrock generation calls were made." -ForegroundColor Green
    Write-Host "You can still generate a template report:"
    Write-Host "  $py -m ethiocontexteval.analysis --report-only-template"
    exit 0
}

if ($modelsListCode -ne 0 -or $modelsCheckCode -ne 0) {
    Write-Host "Model discovery/check reported problems. Aborting execute for safety." -ForegroundColor Red
    exit 2
}

Write-Host "`n[4/7] Execute generations"
& $py -m ethiocontexteval.runner --execute
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[5/7] Anonymize latest generations"
$latest = Get-ChildItem .\results\raw\generations_*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) {
    Write-Host "No generations file found." -ForegroundColor Red
    exit 1
}
& $py -m ethiocontexteval.anonymize $latest.FullName
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[6/7] Create rating template from latest blinded CSV"
$blinded = Get-ChildItem .\results\blinded\blinded_responses_*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($blinded) {
    & $py -m ethiocontexteval.human_evaluation template $blinded.FullName
}

Write-Host "`n[7/7] Template analysis report"
& $py -m ethiocontexteval.analysis --report-only-template

Write-Host "`nPilot generation+blind workflow finished." -ForegroundColor Green
Write-Host "Complete human ratings before interpreting results."
