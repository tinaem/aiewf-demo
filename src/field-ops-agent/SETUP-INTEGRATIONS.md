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
| **Foundry IQ** | Indexed documents (AI Search) — e.g. the supplier agreement; **Toolbox tool must be named `supplier_docs`** | (inside Toolbox) | `analyze_document` mock + `sample_docs/` |
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

Foundry IQ is a **knowledge base** (powered by Azure AI Search *agentic
retrieval*) that the agent reaches through a Toolbox MCP tool. It's a 4-object
chain — get the names right and the wiring is trivial:

```
documents in a data store        ← what you upload (PDF/DOCX/JSON…)
        │  (indexer chunks + embeds)
        ▼
Azure AI Search index            ← e.g.  supplier-docs-index
        │  (referenced by)
        ▼
knowledge source                 ← e.g.  supplier-docs-ks
        │  (added to)
        ▼
knowledge base                   ← e.g.  supplier-docs-kb   → exposes an MCP endpoint
        │  (surfaced through Toolbox as a tool)
        ▼
Toolbox tool the agent calls     ← MUST be named  supplier_docs
```

### ⚠️ The one name that must match: `supplier_docs`

This agent's instructions
([`.agent_configs/baseline/instructions.md`](.agent_configs/baseline/instructions.md))
tell the model, verbatim:

> *"…call `supplier_docs` (from the Foundry Toolbox) … Cite filenames in your answer."*

So the tool the Toolbox exposes for this knowledge base **must be named
`supplier_docs`**. The index / knowledge-source / knowledge-base names above are
your choice — only the **tool name** is load-bearing.

#### Tool names vs. resource names — two different rule sets

These are *separate namespaces*; don't confuse them:

| | Rule | Examples used here |
| --- | --- | --- |
| **Resource names** (toolbox, connection, index, knowledge source, knowledge base) | Alphanumeric, hyphens allowed in the middle, must start/end alphanumeric — **no underscores** | `supplier-docs` (toolbox), `supplier-docs-search`, `supplier-docs-ks`, `supplier-docs-kb`, `supplier-docs-ks-index` |
| **Tool name** (the string the model invokes) | Set via the tool definition's optional `name` field — **underscores are allowed** | `supplier_docs` |

Underscores in tool names are normal (the Foundry IQ quickstart's own default is
`knowledge_base_retrieve`). So `supplier_docs` is a **valid** tool name — it does
*not* need to become `supplier-docs`.

> ⚠️ **Don't name the Toolbox `supplier_docs`.** The portal's **Create toolbox →
> Name** field is a resource name and will reject the underscore with *"Toolbox
> name must start and end with alphanumeric characters and can contain hyphens in
> the middle."* Name the **toolbox** `supplier-docs` (hyphen); name the **tool
> inside it** `supplier_docs` (underscore).

#### How to set the tool name to `supplier_docs`

When you add the knowledge base / search index to the Toolbox, set the tool
definition's `name` field explicitly:

```jsonc
{
  "type": "azure_ai_search",        // (or the knowledge-base tool type)
  "name": "supplier_docs",           // ← the load-bearing tool name
  "description": "Hybrid semantic + keyword retrieval over supplier docs.",
  "azure_ai_search": {
    "indexes": [
      { "index_name": "supplier-docs-ks-index", "project_connection_id": "supplier-docs-search" }
    ]
  }
}
```

For first-party tool types (`azure_ai_search`, `web_search`, knowledge base) the
exposed name **is** the `name` field value — no prefix. (Only *remote MCP server*
tools get a `server_label.` prefix, e.g. `myserver.some_tool`.) If you instead
accept the quickstart default (`knowledge_base_retrieve`), either set `name:
supplier_docs` as above **or** change every `supplier_docs` reference in
`instructions.md` to match. Mismatch = the model calls a tool that doesn't exist
and silently falls back to its offline mock.

### Ready-to-upload documents

This repo ships the document corpus for you — **12 Markdown files** (6 topics ×
2 suppliers) under [`sample_docs/index_corpus/`](sample_docs/index_corpus/).
They carry YAML front matter (supplier, vendor_id, agreement_id, document_type,
dates) and human-readable filenames that double as citations. Regenerate them
from the supplier JSON anytime:

```pwsh
python sample_docs/generate_index_corpus.py
```

Upload everything in that folder to the data store behind `supplier-docs-index`.
See [`sample_docs/index_corpus/README.md`](sample_docs/index_corpus/README.md)
for portal and `az storage blob upload-batch` instructions.

### Set up (portal — fastest)

1. Sign in to [Microsoft Foundry](https://ai.azure.com/) with **New Foundry**
   on, open your project, choose **Build → Knowledge**.
2. Create or connect a **search service that supports agentic retrieval**.
3. Upload your documents (see shape below) to the backing data store and let the
   indexer build the index (e.g. `supplier-docs-index`).
4. **Create a knowledge source** over that index (e.g. `supplier-docs-ks`). In
   its `sourceDataFields`, include the **file-name field** — that's what powers
   the "cite filenames" instruction.
5. **Create a knowledge base** (e.g. `supplier-docs-kb`) that references the
   knowledge source.
6. **Create a Toolbox.** On the **Create toolbox** screen, the **Name** field is
   a *resource* name — give it a **hyphenated** name like `supplier-docs`.

   > ⚠️ **Common mistake:** Do **not** type `supplier_docs` here. The portal
   > rejects it with *"Toolbox name must start and end with alphanumeric
   > characters and can contain hyphens in the middle."* That underscore name is
   > the **tool** name, set in the next step — not the toolbox name.

7. Add the knowledge base to that Toolbox and set the **exposed tool's name** to
   **exactly `supplier_docs`** (underscore — this is the string `instructions.md`
   calls). Set `TOOLBOX_ENDPOINT` (see section 1).
8. Grant the agent's managed identity read access on the search service
   (agentic-identity auth — no stored key).

Programmatic path (REST/SDK) and the end-to-end automation are documented here:
- [What is Foundry IQ? (workflow)](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq#workflow)
- [Quickstart: Foundry IQ knowledge base + toolbox for a hosted agent](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-foundry-iq-hosted-agent)
- [Create a search-index knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-search-index)

### What documents to put in it (and how to name them)

The agent is built to answer per-subcontractor questions — *contract, insurance,
rates, certifications, safety attestations, dispatch quick-reference*. Load **one
set of documents per supplier**. The repo ships **two** suppliers as canonical
examples:

- **Cascade Fiber** —
  [`sample_docs/supplier_agreement.json`](sample_docs/supplier_agreement.json)
  (structured source of truth) →
  [`sample_docs/supplier-agreement.pdf`](sample_docs/supplier-agreement.pdf).
- **Pacific OptoLink** —
  [`sample_docs/pacific_optolink_agreement.json`](sample_docs/pacific_optolink_agreement.json)
  → `sample_docs/pacific-optolink-agreement.pdf`.

Regenerate both PDFs with `python sample_docs/generate_supplier_agreement_pdf.py`
(it renders every entry in the module's `SUPPLIERS` list). Add more suppliers by
copying a JSON file, editing the values, and appending a `(json, pdf)` row to
`SUPPLIERS`.

**File-naming tip:** because the agent cites filenames, give each document a
human-readable, supplier-prefixed name so citations read well, e.g.
`cascade-fiber-msa-2026-CF-0417.pdf`, `cascade-fiber-coi-2026.pdf`,
`pacific-optolink-msa-2026-PO-0291.pdf`, `pacific-optolink-rate-card.pdf`.

**Content the demo punchlines depend on:** the indexed content must contain the
dispatch facts the agent quotes — for Cascade Fiber: connector `LC/UPC Duplex`,
after-hours rate `$235/hr`, P1 rate `$310/hr`; for Pacific OptoLink: connector
`LC/APC Duplex` (APC, not UPC), after-hours rate `$265/hr`, P1 rate `$345/hr`.
Keep your real documents consistent with the JSON sources (or edit both
together).

### Local fallback

No Toolbox configured? `analyze_document` in
[`worker_agent.py`](worker_agent.py) routes any URL containing
`pacific`/`optolink` to the Pacific OptoLink data,
`supplier`/`agreement`/`msa`/`cascade` to the Cascade Fiber data, and everything
else to a generic spec sheet — so the demo runs offline for both suppliers.


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
