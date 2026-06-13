# Contributing to Personal GRC Agent

Thank you for your interest in contributing to PGA. This project is a local-first, draft-by-default GRC copilot — contributions should preserve that safety model.

## Getting started

```bash
git clone https://github.com/wcbot0/Personal-GRC-Agent.git
cd Personal-GRC-Agent
./bootstrap.sh
source .venv/bin/activate
```

For development with tests:

```bash
pip install -e ".[dev]"
```

## Development workflow

1. Create a feature branch from `main`.
2. Make changes; keep diffs focused.
3. Run quality gates before opening a PR:

```bash
make selftest          # health checks
make lint              # policy-lint + secret-scan
make eval              # golden skill evals
make eval-crosswalk    # csf-crosswalk scenarios (optional)
pytest tests/ -v       # unit/integration tests
```

4. Open a PR using the template checklist.

## Governance rules for PRs

- **Draft-by-default:** Do not add auto-publish, auto-assign, or live vendor write paths without explicit A3/A4 gates and tests.
- **Use `spa` for governed artifacts:** Skill outputs that pass verifiers should flow through `spa run-skill`, not hand-crafted JSON in proposal paths.
- **Control tags:** Tag security-relevant outputs with `CSF:`, `SOC2:`, `ISO27001:`, etc.
- **Brain edits:** After substantive changes under `brain/`, run `make seed`.
- **Never commit:** `.env`, signing keys, audit logs, or local workspace data.

## Project layout

| Path | Purpose |
|------|---------|
| `spa/` | CLI, skill runner, governance, audit |
| `skills/` | Skill contracts and schemas |
| `brain/` | Security Brain (frameworks, policies, evidence) |
| `evals/` | Golden fixtures and eval harness |
| `tests/` | Unit and integration tests |
| `agent/` | Charter and autonomy policy |

Agent navigation for AI assistants: [AGENTS.md](AGENTS.md).

## Adding a skill

1. Scaffold under `skills/<name>/` with `SKILL.md` and `output.schema.json`.
2. Implement in `spa/skills/<name>.py` and register in the runner.
3. Add a golden fixture under `evals/fixtures/` and expected output under `evals/golden-outputs/`.
4. Wire into `evals/run_evals.py`.

## Documentation

- User-facing: `README.md`, `docs/getting-started.md`, `docs/runtimes/`
- Architecture reference: `docs/SPA_MVP.md`
- Agent operators: `AGENTS.md`, `agent/charter.md`

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and safe deployment guidance.
