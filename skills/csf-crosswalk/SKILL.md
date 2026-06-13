---
name: csf-crosswalk
description: Map vendor artifacts or policy excerpts to CSF, SOC2, ISO 27001, ISO 27018, ISO 42001, and 800-53 controls with gap analysis. Use when processing vendor questionnaires, cloud privacy, or AI governance crosswalk requests.
---

**Risk class:** A1 (local draft)

Artifact or policy excerpt → CSF 2.0 + SOC2 CC + ISO 27001 Annex A + ISO 27018 (cloud PII) + ISO 42001 (AI) + 800-53 mapping table and gap list.

## Output contract

Each entry in `control_mappings` must include the core security fields. Include optional ISO 27018 / ISO 42001 fields when the artifact indicates **cloud PII processing** or **AI system** scope respectively; omit or set to empty string when not applicable.

| Field | Example | Required | Notes |
| --- | --- | --- | --- |
| `artifact_excerpt` | `"SSO via Okta"` | no | Short quote or paraphrase from input |
| `csf_2` | `PR.AA-05` | yes | CSF 2.0 subcategory |
| `soc2_cc` | `CC6.1` | yes | SOC 2 Common Criteria (or C/P when applicable) |
| `iso27001` | `A.5.15` | yes | ISO/IEC 27001:2022 Annex A (no `A.` prefix in field value) |
| `iso27018` | `A.9.2.1` | when cloud PII | ISO/IEC 27018 PII processor control |
| `iso42001` | `A.6.2.6` | when AI scope | ISO/IEC 42001 Annex A AI control |
| `nist_800_53` | `AC-2` | yes | NIST SP 800-53 control |
| `coverage` | `partial` | no | `full`, `partial`, or `none` |
| `notes` | free text | no | Mapping rationale or evidence gap |

Emit `control_tags` with prefixed identifiers: `CSF:…`, `SOC2:…`, `ISO27001:A.…`, `ISO27018:A.…`, `ISO42001:A.…`, `800-53:…`.

Brain crosswalk references: `brain/01-frameworks/soc2-csf-crosswalk.md`, `brain/01-frameworks/csf-iso27001-crosswalk.md`, `brain/01-frameworks/soc2-iso27001-crosswalk.md`, `brain/01-frameworks/soc2-iso27018-crosswalk.md`, `brain/01-frameworks/csf-iso27018-crosswalk.md`, `brain/01-frameworks/soc2-iso42001-crosswalk.md`, `brain/01-frameworks/csf-iso42001-crosswalk.md`.
