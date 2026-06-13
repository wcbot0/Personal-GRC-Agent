# Eval harness

Golden-fixture evals for PGA skills. Run all skills:

```bash
make eval
```

Run csf-crosswalk scenarios only:

```bash
make eval-crosswalk
```

## Layout

| Path | Contents |
|------|----------|
| `fixtures/` | Sample inputs per skill |
| `golden-outputs/` | Expected output shapes for heuristic/LLM-off mode |
| `crosswalk/` | Multi-scenario csf-crosswalk evals (fixtures, golden, `scenarios.yaml`) |
| `rubrics/` | Verifier rubrics referenced by skills |

## Synthetic test data

Several fixtures contain **intentionally fake** secrets or vulnerabilities for automated testing:

- `fixtures/secret_leak_sample.md` — redaction test token
- `fixtures/sample-vuln-repo/` — deliberately vulnerable Python for repo-security-review
- `fixtures/meeting_autonomous_loop.md` — canary secret for ingest pipeline tests

These are not real credentials. Secret scanning skips some fixture paths in CI by design; see [SECURITY.md](../SECURITY.md).

## CI mode

Evals run with `SPA_NO_LLM=1` in GitHub Actions for deterministic heuristic output. To test LLM-backed skills locally, set `LLM_API_KEY` and unset `SPA_NO_LLM`.
