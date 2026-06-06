# Reliability Metrics

Track from first skill live:

| Metric | Target | Notes |
|--------|--------|-------|
| M1 First-pass acceptance rate | > 70% within 4 weeks/skill | Drafts merged without substantive edits |
| M2 Mean time to detect agent error | < 24h | Via audit log review + daily-brief |
| M3 Verifier pass rate (first attempt) | 100% on golden fixtures | Per skill, from `evals/run_evals.py` |

## M3 collection (automated)

Every CI run and local `make eval`:

1. Runs each skill against golden fixtures
2. Records first-attempt verifier pass/fail per skill
3. Writes `governance/eval-history/m3-{timestamp}.json`
4. Fails CI if first-pass rate falls below `SPA_M3_MIN_FIRST_PASS_RATE` (default `1.0`)

Example report fields:

```json
{
  "metric": "M3",
  "first_pass_count": 6,
  "total_skills": 6,
  "first_pass_rate": 1.0,
  "skills": [{"skill": "meeting-synth", "first_pass": true, "verifiers": []}]
}
```

Record M1/M2 observations in this file or an external dashboard post-MVP.
