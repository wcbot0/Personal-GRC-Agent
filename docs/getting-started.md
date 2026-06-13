# Getting started with Personal GRC Agent

This guide walks you from a fresh clone to your first governed artifacts. For a feature overview and use-case examples, see the [README](../README.md).

**PGA** is the product · **`spa`** is the CLI you run in the terminal.

---

## What you need

| Requirement | Notes |
|-------------|-------|
| **Python 3.11+** | Required |
| **Docker Desktop** | Runs Qdrant for semantic memory (`localhost:6333`) |
| **Git** | Clone, bootstrap, and policy branches |
| **macOS or Linux** | Primary platforms |

Optional:

- **LLM API key** — OpenAI, Anthropic, or [Ollama](https://ollama.com) for full skill output (heuristic fallbacks exist for some paths)
- **MCP-compatible assistant** — Cursor, Claude Code, or Hermes for conversational access

---

## Install

```bash
git clone https://github.com/wcbot0/Personal-GRC-Agent.git
cd Personal-GRC-Agent
./bootstrap.sh
source .venv/bin/activate
make selftest
```

Bootstrap is **idempotent**. It creates a virtualenv, installs `spa`, copies `.env` from `.env.example`, starts Docker services, seeds the Security Brain into Qdrant, and runs health checks.

**CLI-only** (skip optional chat-runtime prompts):

```bash
HERMES_BOOTSTRAP=0 ./bootstrap.sh
```

If Docker was not running during bootstrap:

```bash
docker compose up -d && make seed
```

### macOS: permission errors

If bootstrap fails with `Operation not permitted`:

1. Grant **Full Disk Access** to your terminal and IDE
2. Clear quarantine on fresh clones: `xattr -dr com.apple.quarantine .`
3. Verify write access: `echo test > governance/audit-logs/_t.tmp && rm governance/audit-logs/_t.tmp`

---

## Configure

Bootstrap copies `.env.example` → `.env`. Edit `.env` for your environment. **Never commit `.env`.**

| Variable | Default | When to change |
|----------|---------|----------------|
| `LLM_PROVIDER` | `openai` | Set to `anthropic` or `ollama` if preferred |
| `LLM_API_KEY` | _(empty)_ | Required for OpenAI/Anthropic cloud models |
| `LLM_MODEL` | `gpt-4o-mini` | Use a model your provider supports |
| `TICKET_PROVIDER` | `none` | Set to `linear` or `jira` when wiring ticket connectors |
| `GRC_PROVIDER` | `none` | Set when wiring Vanta, Drata, or Secureframe |

Embeddings run **locally** via `sentence-transformers` — no external embedding API is required.

Governance and persona files (usually left as-is until you fork for your org):

- [`agent/charter.md`](../agent/charter.md) — draft-by-default principles
- [`agent/autonomy-policy.yaml`](../agent/autonomy-policy.yaml) — action-risk gates A0–A5
- [`governance/redaction-rules.yaml`](../governance/redaction-rules.yaml) — secret/PII patterns stripped at write time

---

## Your first workflow

The fastest way to see PGA in action is ingest with a meeting-shaped note.

### 1. Drop a file in `inbox/`

Copy the included sample or write your own notes with meeting signals (`decisions`, `action items`, `risks`, `attendees`, etc.):

```bash
cp evals/fixtures/meeting_sample.md inbox/my-first-meeting.md
```

### 2. Ingest

```bash
spa ingest inbox/my-first-meeting.md
```

Ingest always:

1. Redacts secrets and PII
2. Indexes content into episodic (SQLite) and semantic (Qdrant) memory

When meeting signals are detected, ingest also:

1. Runs **meeting-synth** → decisions, risks, action items
2. Creates **AI-Proposed ticket JSON** in `workspace/proposals/tickets/` (`assignee: unassigned`)
3. Runs **policy-redline** when notes mention policy, MFA, or redline updates

### 3. Review outputs

```bash
# Skill JSON artifacts (default location)
ls workspace/.data/drafts/meeting-synth/

# AI-Proposed tickets
ls workspace/proposals/tickets/

# Optional policy redline
ls workspace/proposals/03-policies/proposals/
```

Nothing is assigned to a person or published externally. Review drafts, edit as needed, and promote when ready.

### 4. Verify the audit trail

```bash
spa audit verify
```

Every governed action appends to a hash-chained JSONL log in `governance/audit-logs/`.

---

## Run a skill directly

When you know which skill you need, skip auto-detection:

```bash
spa run-skill <skill-name> --input <path> [--output-dir <dir>]
```

| Skill | Example input | Primary output |
|-------|---------------|----------------|
| `meeting-synth` | Meeting notes or transcript | Decisions, risks, tickets |
| `ticket-draft` | Gap or finding description | `workspace/proposals/tickets/` |
| `policy-redline` | Change request with optional `Policy: <slug>` | Redline Markdown + draft PR body |
| `csf-crosswalk` | Vendor artifact or policy excerpt | Multi-framework mapping + gaps |
| `evidence-pack` | `Control: CC6.1` + `Period: 2026-Q2` | Evidence index under `brain/evidence/` |
| `daily-brief` | Optional context note | `workspace/proposals/daily-brief-*.md` |
| `risk-analyst` | Product/vendor assessment | Risk register + threat model |
| `repo-security-review` | `Repo: <path or URL>` | OWASP/ASVS findings |
| `questionnaire` | CAIQ/SIG question list | Cited answers with `needs_human` flags |

Example — evidence pack written into git-backed brain:

```bash
spa run-skill evidence-pack --input evals/fixtures/evidence_pack_input.md --output-dir .
make seed   # re-index after brain edits
```

Skill contracts: [`skills/`](../skills/) · Per-skill details: [`skills/<name>/SKILL.md`](../skills/)

---

## Understand draft surfaces

PGA writes to specific locations. Knowing where to look saves time.

| Surface | What lands here |
|---------|-----------------|
| `workspace/.data/drafts/<skill>/` | Default skill JSON output from `spa run-skill` |
| `workspace/proposals/tickets/` | AI-Proposed ticket files |
| `workspace/proposals/03-policies/proposals/` | Policy redlines |
| `workspace/proposals/risks/` | Risk assessments and threat models |
| `brain/03-policies/proposals/` | Git-backed policy proposals (promote after review) |
| `brain/evidence/<control-slug>/` | Evidence indexes (use `--output-dir .` on evidence-pack) |
| `governance/approval-queue/` | Change Proposal Objects (CPOs) for A3+ actions |
| `governance/audit-logs/` | Append-only audit events (never edit by hand) |

Canonical path rules live in [`spa/paths.py`](../spa/paths.py).

---

## Security Brain

Your knowledge base lives under `brain/` — frameworks, policies, controls, and evidence. PGA searches it semantically after `make seed`.

```
brain/
├── 00-meta/           Conventions
├── 01-frameworks/     CSF 2.0, SOC 2, ISO crosswalks
├── 02-controls/       Control catalog
├── 03-policies/       Authoritative policies
├── 04-standards/      Installed framework packs
├── evidence/          Evidence indexes
└── packs/             Optional packs to install
```

**After editing brain content:**

```bash
make seed
```

**Install optional framework packs:**

```bash
spa brain list
spa brain add iso-42001
spa brain add nist-ai-rmf
```

Replace template policies under `brain/03-policies/` with your organization's authoritative documents when forking for production use.

---

## Approvals and governance

PGA classifies every action A0–A5. Reads and local drafts run freely. Actions that affect other people or create authoritative records require a **Change Proposal Object (CPO)**.

| Class | Examples | Approval |
|:-----:|----------|----------|
| A0 | Read brain, ingest, search memory | None |
| A1 | Local drafts, git branches | None |
| A2 | AI-Proposed tickets, draft PR bodies | Notify |
| A3 | Assign ticket to a human | **CPO required** |
| A4 | Publish policy, merge PR, GRC write | **CPO required** |
| A5 | Delete audit logs, unknown tools | **Blocked** |

Review pending approvals:

```bash
spa proposals list
spa proposals show cpo-<uuid>
spa proposals approve cpo-<uuid>
spa proposals reject cpo-<uuid> --reason "..."
```

Full policy: [`agent/autonomy-policy.yaml`](../agent/autonomy-policy.yaml)

---

## Connect your AI assistant (MCP)

The same governed pipeline runs from any MCP client — not just the terminal.

```bash
spa mcp serve    # stdio transport
```

| MCP tool | Purpose |
|----------|---------|
| `pga_ingest` | Ingest + auto-pipeline |
| `pga_run_skill` | Run a drafting skill |
| `pga_proposals_list` / `pga_proposals_show` | View CPOs |
| `pga_proposals_approve` / `pga_proposals_reject` | Approve/reject (requires `confirm: true`) |
| `pga_audit_verify` | Hash chain check |
| `pga_memory_search` | Search episodic + semantic memory |

**One-time setup per runtime:**

```bash
spa init --runtime cursor    # or claude, hermes, chatgpt, openclaw
```

Hermes users: `./scripts/setup-hermes.sh`

Per-runtime details: [`docs/runtimes/`](runtimes/)

For AI coding assistants operating in this repo, see [`AGENTS.md`](../AGENTS.md) — that file is the agent navigation guide, not a human tutorial.

---

## Common next steps

**Cloud compliance scan**

```bash
spa cloud scan --provider aws --period 2026-Q2
```

**Export audit bundle for review**

```bash
spa evidence export --output /tmp/pga-evidence.tar.gz
```

**Fork for your organization**

1. Use GitHub "Use this template" or fork to a private org repo
2. Replace `brain/` template content with your policies and controls
3. Configure `.env` and connectors when ready (live writes remain CPO-gated)
4. Run `spa init --runtime <name>` for your preferred AI assistant
5. Never commit `.env`, audit logs, or private workspace state

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pip: command not found` after activate | `./bootstrap.sh` or `rm -rf .venv && ./bootstrap.sh` |
| Docker not running | Start Docker Desktop → `docker compose up -d && make seed` |
| Qdrant seed warnings | Wait for healthy containers → `make seed` |
| Empty skill output | Set `LLM_API_KEY` in `.env` or use `LLM_PROVIDER=ollama` |
| MCP tools not visible | Confirm `spa mcp serve` works; check runtime config from `spa init` |
| Assistant ignores PGA rules | Open the project from repo root so `AGENTS.md` loads |

---

## Where to go next

| Doc | Audience |
|-----|----------|
| [README](../README.md) | Product overview, use cases, feature summary |
| [AGENTS.md](../AGENTS.md) | AI assistant navigation, path rules, skill routing |
| [docs/runtimes/](runtimes/) | Cursor, Claude Code, Hermes, ChatGPT, OpenClaw setup |
| [agent/charter.md](../agent/charter.md) | Persona and draft-by-default principles |
| [skills/](../skills/) | Skill contracts and output schemas |
