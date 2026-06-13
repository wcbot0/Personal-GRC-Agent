# Security Policy

## Reporting a vulnerability

If you discover a security issue in Personal GRC Agent (PGA), please report it responsibly:

1. **Preferred:** Open a [GitHub private security advisory](https://github.com/wcbot0/Personal-GRC-Agent/security/advisories/new) on this repository.
2. **Alternative:** Open a GitHub issue with minimal reproduction details and mark it sensitive if your account supports that workflow.

Please do **not** open public issues for exploitable vulnerabilities before a fix is available.

We aim to acknowledge reports within 5 business days.

## Scope

This policy covers the PGA codebase (`spa` CLI, MCP server, skills, governance layer, and bundled connectors). It does **not** cover third-party runtimes you install separately (Hermes Agent, OpenClaw, etc.).

## Safe defaults

PGA is designed **draft-by-default**:

- Ticket and GRC connectors default to file-only mode (`TICKET_PROVIDER=none`).
- Live vendor writes require explicit configuration **and** an approved Change Proposal Object (CPO).
- Audit logs are append-only; agents must not delete or truncate them.
- Secrets and PII are redacted at write time per `governance/redaction-rules.yaml`.

## Local secrets

Never commit:

- `.env` or `.env.*` (use `.env.example` as a template)
- `governance/.cpo-signing-key` or any `*.cpo-signing-key`
- Contents of `secrets/`, `workspace/.data/`, `governance/audit-logs/`, or `governance/approval-queue/`

Run `make secret-scan` before publishing forks that include local workspace content.

## Third-party installers

Bootstrap optionally installs [Hermes Agent](https://hermes-agent.nousresearch.com/) via:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

This is an upstream supply-chain choice. Review the installer and pin versions if your threat model requires it. Set `HERMES_BOOTSTRAP=0` to skip Hermes during bootstrap.

## Intentional test fixtures

The following paths contain **synthetic** secrets and vulnerabilities for automated testing. They are not real credentials:

| Path | Purpose |
|------|---------|
| `evals/fixtures/secret_leak_sample.md` | Redaction-at-write test |
| `evals/fixtures/sample-vuln-repo/` | Repo security review eval (OWASP-style vulns) |
| `governance/prompt-injection-tests/corpus.jsonl` | Red-team prompt-injection corpus |
| `tests/` | Unit tests with fake tokens (e.g. AWS-key-shaped placeholders, GitHub PAT patterns) |

Secret scanning intentionally skips some fixture paths during CI; run a full-repo scan before release if you fork this project.

## Forking for production use

When deploying PGA for an organization:

1. Fork into a **private** repository for brain content, policies, and audit logs.
2. Rotate any API keys used during development.
3. Review `agent/autonomy-policy.yaml` and tighten gates for your environment.
4. Strip sample brain content and replace with your authoritative policies and evidence.

See [README.md](README.md) for privacy guidance before sharing artifacts.
