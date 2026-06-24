#!/usr/bin/env bash
# Pre-flight check for the BRK241 demo deployment.
#
# This does NOT deploy anything — it verifies prerequisites and prints the exact
# next commands (including the AZURE_TENANT_ID export that `azd deploy` needs).
#
# Usage (source it so AZURE_TENANT_ID persists in your shell):
#     source ./scripts/preflight.sh

ok=0; warn=0; fail=0
green='\033[0;32m'; yellow='\033[0;33m'; red='\033[0;31m'; cyan='\033[0;36m'; nc='\033[0m'
pass() { printf "  ${green}[PASS]${nc} %s\n" "$1"; ok=$((ok+1)); }
warned() { printf "  ${yellow}[WARN]${nc} %s\n" "$1"; warn=$((warn+1)); }
failed() { printf "  ${red}[FAIL]${nc} %s\n" "$1"; fail=$((fail+1)); }
has() { command -v "$1" >/dev/null 2>&1; }

printf "${cyan}BRK241 deployment pre-flight${nc}\n"
echo "----------------------------"

# 1. Required CLIs
if has azd; then pass "azd found ($(azd version 2>/dev/null | head -n1))"; else failed "azd not found — https://aka.ms/azd-install"; fi
if has az;  then pass "az found";  else failed "Azure CLI (az) not found — https://aka.ms/azcli"; fi

# 2. Python
if has python3 || has python; then
    py=$(command -v python3 || command -v python)
    pyv=$("$py" --version 2>&1)
    if echo "$pyv" | grep -Eq "3\.(1[2-9]|[2-9][0-9])"; then pass "$pyv"; else warned "$pyv (3.12+ recommended)"; fi
else
    failed "python not found — https://www.python.org/downloads/"
fi

# 3. Foundry agents azd extension
if has azd; then
    if azd extension list 2>/dev/null | grep -q "azure.ai.agents"; then
        pass "azd extension azure.ai.agents installed"
    else
        warned "azd extension azure.ai.agents NOT installed — run: azd extension install azure.ai.agents"
    fi
fi

# 4. Azure login + tenant
tenant=""
if has az; then
    tenant=$(az account show --query tenantId -o tsv 2>/dev/null)
    if [ -n "$tenant" ]; then
        pass "az logged in (tenant $tenant)"
        export AZURE_TENANT_ID="$tenant"
        pass "AZURE_TENANT_ID exported for this session"
    else
        warned "Not logged in to az — run: az login"
    fi
fi

echo ""
printf "${cyan}Summary: %s passed, %s warning(s), %s failure(s)${nc}\n" "$ok" "$warn" "$fail"

if [ "$fail" -gt 0 ]; then
    printf "${red}Resolve the [FAIL] items above before deploying.${nc}\n"
else
    echo ""
    printf "${green}Ready. Next steps:${nc}\n"
    echo "  azd auth login"
    echo "  azd provision"
    if [ -n "$tenant" ]; then
        echo "  export AZURE_TENANT_ID=$tenant   # already exported if you sourced this script"
    else
        echo "  export AZURE_TENANT_ID=\$(az account show --query tenantId -o tsv)"
    fi
    echo "  azd deploy"
fi
