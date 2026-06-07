# Risk Register (`brain/06-risks/`)

Git-backed risk register for assessed scenarios and treatment status.

## Layout (planned)

```
brain/06-risks/
  README.md              # this file
  <risk-slug>.md         # promoted risk scenario entries
  register-index.md      # optional rollup of open risks
```

## Promotion workflow

1. Run `spa run-skill risk-analyst --input <assessment.md>`
2. Review drafts in `workspace/proposals/risks/`:
   - `risk-proposal-RISK-ASSESS-001.json` — structured assessment
   - `risk-assessment-<product-slug>.md` — human-readable report
3. After human review, promote accepted scenarios to `brain/06-risks/<risk-slug>.md`
4. Run `make seed` to re-index semantic memory

## Entry format (suggested)

Each promoted risk should include:

- Risk ID, title, product/vendor
- FAIR factors (1–5) and NIST likelihood/impact
- Inherent and residual risk scores
- Treatment decision and owner
- Control tags (`CSF:ID.RA`, `SOC2:CC3.2`, `800-53:RA-3`)
- Review date

## Governance

- Draft proposals: **A2** (AI-proposed, unassigned)
- Formal risk acceptance: **A5 blocked** — requires human authorization outside MVP automation
