# Setting up the IQ integrations yourself

The field-ops-agent runs **out of the box with built-in sample data** — every
integration below has a local mock or seed fallback, so you can demo with zero
cloud setup. This guide is for when you want to wire the agent to the **real**
Foundry / Fabric services.

> **Key idea:** Work IQ, Foundry IQ, and Fabric IQ are **configured in the
> Foundry portal and Fabric — they are not data files in this repo.** The agent
> reaches them at runtime through environment variables (and, for Toolbox-served
> tools, a single MCP endpoint). The only "fill it with data in a certain shape"
> files in this repo are the **local fallbacks** (`procedural_memory_seed.json`
> and the mock dicts in [`worker_agent.py`](worker_agent.py)).

| Integration | What it is | Wired via | Local fallback |
| --- | --- | --- | --- |
| **Toolbox** | One MCP endpoint that serves portal-configured tools (Work IQ, Foundry IQ / AI Search, Web Search, Code Interpreter) | `TOOLBOX_ENDPOINT` | Local `@tool` functions only |
| **Work IQ** | Work-order / task system, surfaced as a Toolbox tool | (inside Toolbox) | `search_work_iq` mock in `worker_agent.py` |
| **Foundry IQ** | Indexed documents (AI Search) — e.g. the supplier agreement | (inside Toolbox) | `analyze_document` mock + `sample_docs/` |
| **Fabric IQ** | Natural-language query over OneLake telemetry (Fabric data agent) | `FABRIC_*` vars | `query_site_reliability` mock |
| **Procedural memory** | Foundry Memory Store of learned procedures | `PROCEDURAL_MEMORY_*` | `procedural_memory_seed.json` |

Everything is opt-in: leave a variable unset and that integration degrades
gracefully to its fallback.

---

## 1. Toolbox (the MCP umbrella)

Toolbox is a single Foundry-managed MCP endpoint. Tools you add in the portal
(Work IQ, an AI Search index, Web Search, Code Interpreter) all appear to the
agent as one entry in its `tools=[...]` list — see
[`toolbox.py`](toolbox.py)'s `build_toolbox_tool()`.

**Set up:**
1. In the Foundry portal, open your project → **Toolbox** → add the tools you
   want (e.g. Work IQ, your AI Search index).
2. Copy the Toolbox MCP URL and set it:
   ```
   TOOLBOX_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>/toolboxes/<toolbox>/mcp?api-version=v1
   ```
3. (Optional) override the feature header:
   `FOUNDRY_AGENT_TOOLBOX_FEATURES=Toolboxes=V1Preview` (this is the default).

Auth is handled for you — `toolbox.py` injects an AAD bearer token
(`https://ai.azure.com/.default`) on every request via `DefaultAzureCredential`.
No keys in the repo.

> **Naming/shape note:** you don't define Work IQ's data shape here. Whatever the
> Toolbox tool returns is what the model sees. To keep parity with the demo,
> mirror the field names used by the local mock `MOCK_WORK_ORDERS`
> (`id`, `title`, `priority`, `status`, `assignee`, `site`, `parts_needed`).

---

## 2. Foundry IQ — indexed documents (the supplier agreement)

Foundry IQ is an **AI Search index** of your documents, exposed through Toolbox.
The demo's document is the supplier agreement under
[`sample_docs/`](sample_docs/).

**Set up:**
1. Generate the demo PDF (or use your own documents):
   ```bash
   python sample_docs/generate_supplier_agreement_pdf.py
   ```
2. Upload the document(s) to the blob/data source behind your AI Search index.
3. In the portal, create/refresh the index and add it to your Toolbox.

**Data shape / naming:** AI Search defines the schema, not this repo. For the
demo punchline to land, the indexed content must contain the dispatch facts the
agent quotes — connector `LC/UPC Duplex`, after-hours rate `$235/hr`, etc. The
canonical source for those values is
[`sample_docs/supplier_agreement.json`](sample_docs/supplier_agreement.json);
keep your real document consistent with it (or edit both).

The local fallback is `analyze_document` in `worker_agent.py`, which routes any
URL containing `supplier`/`agreement`/`msa`/`cascade` to the bundled supplier
data and everything else to a generic spec sheet.

---

## 3. Fabric IQ — live telemetry (Fabric data agent)

`query_site_reliability` in [`fabric_tool.py`](fabric_tool.py) forwards a
natural-language question to a **published Fabric data agent** over OneLake.

**Set up (pick one):**

*Via a Foundry connection (recommended — works hosted + local):*
```
FABRIC_DATA_AGENT_CONNECTION_NAME=fabric-site-reliability   # a MicrosoftFabric connection in your project
```

*Or direct IDs (handy for local dev):*
```
FABRIC_WORKSPACE_ID=<your-fabric-workspace-id>
FABRIC_ARTIFACT_ID=<your-fabric-data-agent-id>
FABRIC_DATA_AGENT_TIMEOUT_SEC=90   # optional, default 90
```

**Data shape / naming:** Fabric owns the data. The agent only sends a question
and reads back the answer string, so there is **no required schema on this
side** — just make sure your Fabric data agent can answer site-reliability
questions (metrics, incidents, SLOs). Auth uses
`https://api.fabric.microsoft.com/.default`.

---

## 4. Procedural memory (Foundry Memory Store)

This is the one integration with a **strict local data shape**, because the
seed file is loaded directly. See
[`procedural_memory.py`](procedural_memory.py) and
[`procedural_memory_seed.json`](procedural_memory_seed.json).

**Modes** (`PROCEDURAL_MEMORY_MODE`):
- `hybrid` *(default)* — try the live Memory Store, fall back to the seed file on
  any error. Demos work with no setup.
- `live` — require the live Memory Store.
- `seed` — always use the bundled JSON.

**To use a live store:**
```
PROCEDURAL_MEMORY_MODE=live
PROCEDURAL_MEMORY_STORE_NAME=<your-memory-store-name>
```

**Seed-file shape (must match exactly):**
```jsonc
{
  "items": [
    {
      "id": "proc-...",            // unique id
      "kind": "procedural",
      "scope": "user-procedural",
      "content": {
        "applicable_to": "When <situation> …",   // when this pattern fires
        "instruction": "Do <X> …"                 // what the agent should do
      }
    }
  ]
}
```
`tests/test_assets.py` validates that this file stays valid JSON.

---

## Quick reference — environment variables

| Variable | For | Required? |
| --- | --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | core | auto-injected when hosted |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | core | yes |
| `TOOLBOX_ENDPOINT` | Toolbox / Work IQ / Foundry IQ | no |
| `FOUNDRY_AGENT_TOOLBOX_FEATURES` | Toolbox | no (defaults) |
| `FABRIC_DATA_AGENT_CONNECTION_NAME` | Fabric IQ | no |
| `FABRIC_WORKSPACE_ID` / `FABRIC_ARTIFACT_ID` | Fabric IQ (direct) | no |
| `FABRIC_DATA_AGENT_TIMEOUT_SEC` | Fabric IQ | no (90s) |
| `PROCEDURAL_MEMORY_MODE` | memory | no (`hybrid`) |
| `PROCEDURAL_MEMORY_STORE_NAME` | memory (live) | only if `MODE=live` |

Copy [`.env.example`](.env.example) to `.env` for local runs. `.env` is
git-ignored and `.agentignore`'d — never commit real endpoints or keys.
