#!/usr/bin/env pwsh
# Pre-flight check for the BRK241 demo deployment.
#
# This does NOT deploy anything — it verifies prerequisites and prints the exact
# next commands (including the AZURE_TENANT_ID export that `azd deploy` needs).
#
# Usage (dot-source so AZURE_TENANT_ID persists in your shell):
#     . ./scripts/preflight.ps1

$ok = 0; $warn = 0; $fail = 0
function Pass($m) { Write-Host "  [PASS] $m" -ForegroundColor Green; $script:ok++ }
function Warn($m) { Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:warn++ }
function Fail($m) { Write-Host "  [FAIL] $m" -ForegroundColor Red; $script:fail++ }
function Has($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host "BRK241 deployment pre-flight" -ForegroundColor Cyan
Write-Host "----------------------------"

# 1. Required CLIs
if (Has "azd") { Pass "azd found ($((azd version) 2>$null | Select-Object -First 1))" } else { Fail "azd not found — https://aka.ms/azd-install" }
if (Has "az")  { Pass "az found"  } else { Fail "Azure CLI (az) not found — https://aka.ms/azcli" }

# 2. Python
if (Has "python") {
    $pyv = (python --version) 2>&1
    if ($pyv -match "3\.(1[2-9]|[2-9]\d)") { Pass "$pyv" } else { Warn "$pyv (3.12+ recommended)" }
} else { Fail "python not found — https://www.python.org/downloads/" }

# 3. Foundry agents azd extension
if (Has "azd") {
    $ext = (azd extension list 2>$null | Out-String)
    if ($ext -match "azure\.ai\.agents") { Pass "azd extension azure.ai.agents installed" }
    else { Warn "azd extension azure.ai.agents NOT installed — run: azd extension install azure.ai.agents" }
}

# 4. Azure login + tenant
$tenant = $null
if (Has "az") {
    $tenant = (az account show --query tenantId -o tsv 2>$null)
    if ($tenant) {
        Pass "az logged in (tenant $tenant)"
        $env:AZURE_TENANT_ID = $tenant
        Pass "AZURE_TENANT_ID set for this session"
    } else {
        Warn "Not logged in to az — run: az login"
    }
}

Write-Host ""
Write-Host "Summary: $ok passed, $warn warning(s), $fail failure(s)" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host "Resolve the [FAIL] items above before deploying." -ForegroundColor Red
} else {
    Write-Host ""
    Write-Host "Ready. Next steps:" -ForegroundColor Green
    Write-Host "  azd auth login"
    Write-Host "  azd provision"
    if ($tenant) { Write-Host "  `$env:AZURE_TENANT_ID = '$tenant'   # already set if you dot-sourced this script" }
    else         { Write-Host "  `$env:AZURE_TENANT_ID = (az account show --query tenantId -o tsv)" }
    Write-Host "  azd deploy"
}
