# EthioContextEval — legacy entrypoint; prefers local Ollama pilot.
# For AWS Bedrock (optional future path), use provider bedrock after pip install -e ".[aws]".

Write-Host "Delegating to scripts\run_local_pilot.ps1 (Ollama-first feasibility pilot)." -ForegroundColor Cyan
& "$PSScriptRoot\run_local_pilot.ps1" @args
exit $LASTEXITCODE
