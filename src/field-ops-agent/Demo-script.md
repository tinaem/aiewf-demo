# Demo Script — Field Operations Agent (BRK241)

> **Session:** BRK241 — *From Prototype to Production: Build and Run Agents at Scale*
> **Speakers:** Jeff Hollan, Tina Schuchman
> **This script drives the `field-ops-agent` portion of the demo** (the voice-enabled
> field technician assistant). It is the source of the step numbers referenced from the
> `DEMO POINT` banners in the code:
>
> | Code file | Banner reference | Step(s) here |
> | --- | --- | --- |
> | [`toolbox.py`](toolbox.py) | "from Demo-script.md, step 2" | **Step 2** |
> | [`worker_agent.py`](worker_agent.py) | "from Demo-script.md, steps 6-7" | **Steps 6–7** |
> | [`router_agent.py`](router_agent.py) | "the gap Demo-script.md step 10 explicitly calls out" | **Step 10** |
>
> Keep the step numbering stable — the banners cite it directly.

---

## The scenario (one breath)

> "Microsoft runs the world's largest cloud infrastructure. When a fiber cable gets cut
> near one of our data centers, we need an agentic system that can respond, dispatch, and
> resolve fast. We're going to build one such agent — an autonomous fiber-outage response
> agent — and walk it through three developer phases: **build**, **deploy**, **operate** —
> all in a continuous learning loop."

The `field-ops-agent` is the **build phase** hero: a voice-enabled assistant that helps a
technician on-site repair a fiber line. The `fibey-coordinator` sibling project carries the
**deploy / operate** phases (Routines, hosted-agent sessions, Teams autopilot).

---

## The arc at a glance

```
BUILD  ──►  scaffold with Copilot + Foundry Toolkit
            wire tools through Toolbox (Step 2)
            Agent Framework worker: @tool + as_agent() (Steps 6–7)
            Fabric IQ + procedural memory
            F5 debug locally (Step 9)
            voice routing kills the dead-space (Step 10)
            voice-enable in one click (Step 11)

DEPLOY ──►  deploy to Foundry as a hosted agent
            per-session sandbox isolation, durable state
            publish to Teams / M365 Copilot

OPERATE ─►  Trace Replay observability
            azd ai agent eval init  → benchmark
            custom rubric (weighted dimensions)
            azd ai agent optimize   → ranked candidates
            deploy the winning candidate (developer in control)
```

---

## BUILD

### Step 1 — Blank canvas → scaffold with Copilot

**Talk track:**
> "You can use any tool with Foundry — Claude Code, Copilot CLI, Cursor, Visual Studio.
> My combo is VS Code + GitHub Copilot. The **Foundry Toolkit** extension (now GA) gives me
> everything for the whole flow — not just creating agents, but tracing, evaluations, models —
> right here in the editor."

**What to show:**
- Foundry Toolkit extension surface in VS Code.
- "Generate with Copilot" → describe the Field Operations agent.
- Call out that the extension **auto-integrates Foundry best-practice skills** into the coding
  agent, so the scaffold comes out production-shaped, not toy-shaped.

**Land the point:** *"Building is no longer the hard part."*

---

### Step 2 — Toolbox: one place to organize, govern, and serve tools

> 📌 **Referenced by [`toolbox.py`](toolbox.py).**

**Talk track:**
> "If there's one tool feature to remember, it's **Foundry Toolbox**. Rather than building
> one-off integrations, I use Toolbox — a single place to organize, govern, and serve all my
> agent's tools. I add Work IQ here, and it's instantly available to any agent I build."

**What to show:**
- Toolbox managing **Foundry IQ** (indexed supplier contracts / agreements), **Work IQ**
  (Outlook + Teams history), **Fabric IQ** (site reliability data), **Web search**.
- **One MCP-compatible endpoint** manages auth (bearer token) for all of them.
- **Guardrails** — e.g., PII redaction configured once, applied to every tool.
- **Tool Search** — when enabled, Toolbox returns *only the tools relevant to the task*,
  keeping the agent's context window focused.

**Show in code:** [`toolbox.py`](toolbox.py) is tiny on purpose —
`build_toolbox_tool()` returns an `MCPStreamableHTTPTool` that drops straight into the agent's
`tools=[...]` list, the same shape as a local function tool. Auth is bearer-token managed for us;
the agent just declares the endpoint (`TOOLBOX_ENDPOINT`).

**Land the point:** *"Foundry-managed tools look identical to local tools from the agent's
perspective."*

---

### Step 3 — Content Understanding for un-agent-ready documents

**Talk track:**
> "One cool Toolbox tool is **Content Understanding**. I have a contract PDF with tabular data —
> not very agent-readable. Content Understanding uses a specialized model to turn that PDF into an
> agent-ready format: tables, markdown, figures, or raw JSON."

**What to show:** the supplier-agreement PDF → markdown/JSON conversion. Use the bundled sample
[`sample_docs/supplier-agreement.pdf`](sample_docs/supplier-agreement.pdf) — a Cascade Fiber MSA
with tabular rate-card and SLA data that is intentionally *not* trivially agent-readable. Tie it
back to the `analyze_document` placeholder `@tool` in [`worker_agent.py`](worker_agent.py).

> 🛠️ **Regenerate the PDF:** it's built from
> [`sample_docs/supplier_agreement.json`](sample_docs/supplier_agreement.json) via
> `python sample_docs/generate_supplier_agreement_pdf.py` (`pip install reportlab`). Edit the JSON
> and re-run to change the document.

---

### Step 4 — `agent.yaml`: the hosted-agent contract

**Talk track:**
> "One YAML file. Foundry hosts this."

**What to show:** [`agent.yaml`](agent.yaml) — the single deploy contract Foundry reads.

---

### Step 5 — The harness: agents that do more than call predefined tools

**Talk track:**
> "I'm using **Microsoft's Agent Framework** in Python. New here is the **harness** — a secure
> environment where the agent can execute shell commands, and read / write / execute code, all
> managed. I can even plug in the GitHub Copilot SDK as an additional harness. Agents today aren't
> limited to the tools you configured — they can dynamically investigate and write code."

**What to show:** the wheels in [`wheels/`](wheels/) (Agent Framework 1.0 + agent-server packages)
and where the harness slots in.

---

### Steps 6–7 — Agent Framework: tools, the agent loop, and Foundry

> 📌 **Referenced by [`worker_agent.py`](worker_agent.py).**

**Step 6 — `@tool` is the entire tool definition.**
> "Look at the `@tool` decorator on these Python functions — *that's* a tool definition. No JSON
> schema to maintain. Agent Framework reads the type hints and docstring and builds the schema the
> model needs."

Walk top-to-bottom through [`worker_agent.py`](worker_agent.py):
- `search_site_specs`, `search_work_iq`, `get_repair_procedure`, `analyze_document` — local
  `@tool` functions with rich, deterministic sample data (feature teams swap in real backends).
- `query_site_reliability` — **real** Fabric data agent (Step 8).
- `recall_learned_procedures` — **real** procedural memory (Step 8).

**Step 7 — `as_agent()` is the entire agent loop.**
> "Three lines wire it together:
> `FoundryChatClient(...).as_agent(name, instructions, tools=[...])`.
> That single `as_agent` call *is* the agent loop — model call → tool dispatch → model call → …
> → final message. No manual orchestration."

Call out in `create_worker_agent()`:
- Toolbox MCP tools merge into the **same** `tools=` list — Foundry-managed tools look identical
  to local tools.
- Instructions / tool descriptions / skills load from `.agent_configs/baseline/` via
  `load_config()`, so `azd ai agent optimize` can tune them **without code changes** (pays off in
  Step 16).

**Land the point:** *"This is production-ready scaffolding — the harness, the tool connections,
the memory scope — not a toy."*

---

### Step 8 — Connected intelligence: Fabric IQ + Procedural Memory

**Talk track:**
> "Beyond Work IQ, we wire in **Fabric IQ** — a natural-language interface over our live site
> reliability telemetry sitting in OneLake. And **procedural memory** lets the agent learn the
> playbook across all sessions, so it doesn't relearn from scratch every conversation."

**What to show:**
- [`fabric_tool.py`](fabric_tool.py) — `query_site_reliability` forwards a natural-language
  question to the published Fabric data agent.
- [`procedural_memory.py`](procedural_memory.py) — learned procedures are **prepended to the
  system prompt** as native skills (not tool output), loaded from the Foundry Memory Store
  (live) or [`procedural_memory_seed.json`](procedural_memory_seed.json) (fallback).

**Land the point:** *"The agent gets smarter over time without code changes — always developer in
control."*

---

### Step 9 — F5 debug the agent locally

**Talk track:**
> "Satya's keynote showed UI and code working together. In Foundry I can **F5 debug** my agent —
> it spins up locally, connects to Toolbox over that single MCP endpoint, and I can set a breakpoint
> to inspect the exact request and response. Everything streaming in and out of the agent — right
> here in VS Code."

**What to show:**
- F5 → agent on localhost.
- Ask: *"I'm on site trying to figure out the downtime — what connection type should I use?"*
- Hit a pre-set breakpoint; inspect inputs/outputs; watch the event stream.

---

### Step 10 — Voice latency: how to fill the dead space (router pattern)

> 📌 **Referenced by [`router_agent.py`](router_agent.py) and
> [`route_worker_agent.md`](route_worker_agent.md).**

**Talk track:**
> "This will likely take a few seconds to pull up, **so we need to capture the dead space**.
> A naïve voice agent runs the model + tools, *then* speaks — the user hears 8–15 seconds of
> silence. That kills the voice experience."

**The pattern (front desk / back office):**
- **Router** ([`router_agent.py`](router_agent.py)) — a single LLM call per turn with
  `tool_choice="required"` over **five meta-tools** (`respond_directly`, `start_task`,
  `check_task_status`, `cancel_task`, `get_task_result`). No free-text path → no
  "I'll look into it…" hallucinations.
- `start_task` spawns the **worker** in the background and immediately speaks a short ack —
  *"Looking that up."* — so the user hears speech in ~1 s.
- **Worker** ([`worker_agent.py`](worker_agent.py)) — the MAF agent does the real research,
  takes as long as it takes. Tasks survive client disconnect.
- Shared lifecycle state in [`task_store.py`](task_store.py):
  `QUEUED → RUNNING → COMPLETED → DELIVERED`.

**What to show:** the architecture diagram in [`route_worker_agent.md`](route_worker_agent.md);
the `ack_message` field on `start_task`.

**Land the point:** *"Same total time, way better feel. Router = front desk, always responsive.
Worker = back office, does the work."*

---

### Step 11 — Voice-enable in one click

**Talk track:**
> "This agent is useful as chat — but the technician is wearing leather work gloves. Chat with
> gloves is a bad experience. So **voice mode, done.** Foundry automatically wraps industry-leading
> voice models; I can pick the voice model if I want."

**What to show — the live voice query:**
> "Hey, can you pull up the fiber termination spec for the Quincy North site and tell me which
> connector I should use on the B-side panel?"

Expected behavior:
- Fast ack → *"Just a sec. / Pulling that up now."* (the Step 10 pattern in action).
- WebSocket streams partial updates while Toolbox tools run.
- Final answer: *"Connector family: **LC/UPC Duplex** required on the B-side panel."*
  (matches `MOCK_SITE_SPECS["quincy_north_b"]` in [`worker_agent.py`](worker_agent.py)).

> ⚠️ **Demo note:** unmute speakers before this step. Expect a 1–3 s pause before the first
> spoken token — that's exactly the dead space Step 10 fills.

---

## DEPLOY

> The deploy phase is carried mainly by the `fibey-coordinator` sibling project. Keep these talking
> points handy when transitioning.

### Step 12 — Deploy to Foundry as a hosted agent

**Talk track:**
> "I deploy this agent into Foundry — it takes the code I ran locally and hosts it. Hosted agents
> give me **per-session sandbox isolation, sub-second cold start, zero idle cost, framework
> agnostic**, and durable file-system state."

**Land the point:** subcontractor A and subcontractor B each get an **isolated workspace** — no
cross-session file or context leakage — but state is **durably persisted** and **resumed** when a
session wakes.

### Step 13 — Routines make the agent proactive

> "**Routines** turn the agent from reactive to proactive. A heartbeat wakes it every hour to check
> the investigation log, look for anomalies, and follow its skills to alert the right person or
> dispatch a subcontractor — with human approval where needed."

### Step 14 — Publish to Teams / M365 Copilot

> "I publish the agent to **Teams and M365 Copilot** — identity, policy, and permissions flow
> through automatically. As an **autopilot agent**, it can take a functional ID, an email address,
> and Teams presence — it can initiate conversations and follow up on action items, all governed in
> Agent 365."

---

## OPERATE

### Step 15 — Observability: Trace Replay

**Talk track:**
> "First piece is visibility — what happened and why. **Trace Replay** shows the full trajectory of
> a request: reasoning on the model (~20 s), tool call, reasoning, tool call. I can click into any
> step for exact inputs/outputs, switch to a **token view** to see where tokens are consumed, and
> even **replay** the conversation at 8× to see what the user experienced."

### Step 16 — Optimize: eval → rubric → ranked candidates

**The real feedback we acted on:**
> "The voice answer came back as a **bullet-point list** — robotic when read aloud. I want a more
> voice-natural response. But which variable do I tune — model, tools, code, instructions?"

**Walk the CLI:**
1. `azd ai agent eval init` → pick `field-ops-agent`. If you have no eval dataset, Foundry
   **generates one** from historic traces using an LLM.
2. **Custom rubric** — auto-generated weighted dimensions (e.g., highest weight on *correct tool
   use* — "uptime questions must use Fabric IQ"; a *safety warning* dimension). Bump
   **voice-optimized conciseness** from weight **3 → 10** based on the feedback.
   *(This is exactly why instructions/tool descriptions live in `.agent_configs/baseline/` —
   see Steps 6–7.)*
3. `azd ai agent optimize` → pick the eval-initialized agent. The optimizer varies **system
   prompts, tool descriptions, skills, and even the target model** (GPT-5.5 vs Opus 4.8) and uses
   leading data-science techniques to find better candidates against the rubric.

**The payoff:**
> "It found a candidate that boosts the evaluator **11%** — four ranked candidates, each with
> pros/cons, shown side-by-side across **quality, cost, and latency**. I review the diff (old prompt
> vs new prompt), then **deploy the winning candidate** as the new default — with rollback,
> traceback, and lineage right there."

**Land the point:** *"No manual rewrite of prompts or skills. The agent becomes smarter, safer, and
cheaper the more it runs — always developer in control on every change."*

---

## Closing (Tina)

> "We started with a real scenario — a fiber got cut near a data center. We **built** locally with
> Microsoft Agent Framework, connected Foundry Toolbox, Foundry IQ, memory, voice, and Content
> Understanding. We **deployed** as a hosted agent in an isolated secure runtime and published to
> Teams. We **operated** it — traced end-to-end, and it's meaningfully getting better every run.
> Built simply, deployed powerfully, operated with trust."

---

## Demo-day checklist

- [ ] `TOOLBOX_ENDPOINT` set (else Toolbox tools are skipped — Step 2/9 degrade gracefully).
- [ ] `FOUNDRY_PROJECT_ENDPOINT` + `AZURE_AI_MODEL_DEPLOYMENT_NAME` set.
- [ ] Fabric connection configured (`FABRIC_DATA_AGENT_CONNECTION_NAME`) for Step 8.
- [ ] Procedural memory mode confirmed (`PROCEDURAL_MEMORY_MODE=hybrid` default) for Step 8.
- [ ] Breakpoint pre-set in the request handler for Step 9.
- [ ] Speakers unmuted before Step 11; mic tested.
- [ ] Pre-baked optimization run URL on hand for Step 16 (the live run takes ~dozens of minutes).
- [ ] Quincy North B-side query returns **LC/UPC Duplex** (deterministic sample data).
