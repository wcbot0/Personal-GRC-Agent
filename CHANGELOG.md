# Changelog

All notable changes to Personal GRC Agent (PGA) are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.1] - 2026-06-13

Public-release hygiene: scrubbed published git history and clarified fork/privacy expectations.

### Security

- Rewrote published git history to remove accidental local paths, committed runtime artifacts, and personal identifiers from reachable refs
- Untracked `.cursor/` (generate local glue with `spa init --runtime cursor`)

### Changed

- README privacy and forking guidance for public consumers
- `CODEOWNERS` maintainer handles and fork instructions

## [0.1.0] - 2026-06-13

Initial public release of Personal GRC Agent — a local-first, draft-by-default GRC copilot.

### Features

- **`spa` CLI** — ingest, skill runner, proposals, audit verify, brain packs, cloud scan
- **Governed MCP server** (`spa mcp serve`) — ToolGuard-wrapped tools with hash-chained audit
- **Skills** — meeting-synth, ticket-draft, policy-redline, csf-crosswalk, evidence-pack, daily-brief, risk-analyst, repo-security-review, questionnaire
- **Draft-by-default governance** — A0–A5 action-risk gates via `agent/autonomy-policy.yaml` and CPO approval queue
- **Local-first memory** — SQLite episodic + Qdrant semantic + redaction-at-write
- **Five runtime adapters** — Cursor, Claude Code, Hermes, ChatGPT, OpenClaw (`spa init --runtime`)
- **Security Brain** — git-backed frameworks, policies, controls, evidence templates
- **CI quality gates** — skill evals, policy-lint, secret-scan, redteam corpus

### Connectors

- File-only ticket/GRC providers by default (`TICKET_PROVIDER=none`)
- Optional Linear live writes behind CPO (disabled by default)
- Disabled vendor MCP templates (AWS, GCP, Slack, Jira, Vanta, Drata)

### Added (pre-release development)

- Multi-framework csf-crosswalk eval scenarios (ISO 27018, ISO 42001)
- Brain framework crosswalks for SOC 2, CSF, ISO 27001/27018/42001
- Community docs: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Dependabot configuration for pip and GitHub Actions

### Changed (pre-release development)

- Removed internal agent handoff docs from public tree
- Reframed `docs/SPA_MVP.md` as contributor architecture reference
- Moved `pytest` to optional `[dev]` dependencies in `pyproject.toml`

[Unreleased]: https://github.com/wcbot0/Personal-GRC-Agent/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/wcbot0/Personal-GRC-Agent/releases/tag/v0.1.1
[0.1.0]: https://github.com/wcbot0/Personal-GRC-Agent/releases/tag/v0.1.0
