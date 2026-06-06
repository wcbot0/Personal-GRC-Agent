# Skill Template

Copy this directory to create a new skill: `./scripts/new-skill.sh my-skill`

## Required files
- `skill.md` — purpose, inputs, outputs, risk class (A1 draft)
- `input.schema.json` / `output.schema.json`
- `verifiers/rubric.md`
- `fixtures/input.md`
- `tests/` (optional)

## Verifier pipeline
1. Schema validation
2. Control-mapping-present
3. Secrets scan
4. Self-critique rubric (retry once, then escalate to CPO)
