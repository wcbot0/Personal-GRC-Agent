# T8 — CI green in GitHub Actions

## Context
Four workflows exist: `policy-lint.yml`, `skill-tests.yml`, `secret-scan.yml`,
`redteam.yml`. They must run on PR and pass using the env-isolated paths from T2.

## Goal
All four workflows green on a test PR, on a clean runner.

## Files touched
- `.github/workflows/policy-lint.yml` — validate frontmatter + control-mapping +
  schemas.
- `.github/workflows/skill-tests.yml` — run `evals/run_evals.py` + pytest with
  `SPA_DATA_DIR`/`SPA_AUDIT_DIR` pointed at a temp dir.
- `.github/workflows/secret-scan.yml` — fail on any committed secret.
- `.github/workflows/redteam.yml` — run the prompt-injection corpus.
- `requirements.txt` / `pyproject.toml` — ensure CI installs match local.

## Acceptance criteria
- Open a draft PR; all four checks report success.
- skill-tests writes no state into the repo tree (uses temp dirs).
- Introducing a fake secret makes secret-scan fail.

## Do NOT
- Do not mark workflows `continue-on-error` to force green.
