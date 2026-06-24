# Tests & pre-flight checks

Lightweight checks so the demo doesn't break on stage. Nothing here touches
Azure or requires a deployment.

## Offline tests

```bash
pip install -r requirements-dev.txt
pytest
```

- **`tests/test_assets.py`** — validates every shipped data/config file
  (`supplier_agreement.json`, `procedural_memory_seed.json`, `tools.json`,
  `rubric_dimensions.json`, the golden eval `.jsonl`) and regenerates the
  supplier-agreement PDF. Requires only `pytest` + `reportlab`.
- **`tests/test_tools.py`** — checks the `field-ops-agent` worker tools
  (`analyze_document` routing, the Quincy North connector punchline). These
  import the Microsoft Agent Framework, so they **auto-skip** unless the agent
  wheels are installed:

  ```bash
  pip install src/field-ops-agent/wheels/*.whl
  pytest tests/test_tools.py
  ```

## Deployment pre-flight

Verifies prerequisites and sets `AZURE_TENANT_ID` (the easy-to-miss step before
`azd deploy`). It does **not** deploy — it prints the next commands.

```bash
# macOS / Linux (source it so AZURE_TENANT_ID persists)
source ./scripts/preflight.sh
```

```powershell
# Windows (dot-source it so AZURE_TENANT_ID persists)
. ./scripts/preflight.ps1
```

Then follow the printed `azd provision` / `azd deploy` steps.
