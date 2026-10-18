param([string]$Profile = "", [string]$Region = "eu-north-1")
$ErrorActionPreference = "Stop"
$awsOptions = @("--region", $Region, "--no-cli-pager")
if ($Profile) { $awsOptions += @("--profile", $Profile) }
aws --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
aws sts get-caller-identity @awsOptions
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
aws bedrock list-foundation-models @awsOptions --query "modelSummaries[:10].[modelId,modelName]" --output table
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Discovery only. Runtime access and quota remain unverified. No inference was sent."
