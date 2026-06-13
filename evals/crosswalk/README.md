# csf-crosswalk scenario evals

Multi-scenario golden evals for framework crosswalk coverage (ISO 27001, 27018, 42001, CSF, SOC 2, 800-53).

## Scenarios

| ID | Fixture | Validates |
| --- | --- | --- |
| `cloud-saas-vendor` | Cloud SaaS + PII | ISO27018 tags and mapping fields; no ISO42001 |
| `ai-governance-vendor` | LLM / AI platform | ISO42001 tags and mapping fields; no ISO27018 |
| `combined-ai-cloud` | AI + cloud PII | Both ISO27018 and ISO42001 |

## Run

```bash
make eval-crosswalk          # all crosswalk scenarios only
make eval                    # includes crosswalk scenarios in full skill suite
pytest tests/test_crosswalk_eval.py -v
```

Heuristic mode (`SPA_NO_LLM=1`) is used by default in CI so scenarios assert deterministic stub behavior. Set `LLM_API_KEY` and unset `SPA_NO_LLM` to exercise LLM output against the same golden rules.

## Add a scenario

1. Add fixture under `fixtures/<id>.md`
2. Add golden expectations under `golden/<id>.json`
3. Register in `scenarios.yaml`
4. Run `make eval-crosswalk`

## Golden schema

| Key | Type | Meaning |
| --- | --- | --- |
| `required_fields` | list | Top-level output keys that must exist |
| `min_mappings` | int | Minimum `control_mappings` length |
| `min_gaps` | int | Minimum `gaps` length |
| `control_tags_include_prefixes` | list | At least one tag must start with each prefix |
| `require_nonempty_fields` | list | At least one mapping must have a non-empty value per field |
| `absent_or_empty_fields` | list | Every mapping must omit or leave empty these fields |
