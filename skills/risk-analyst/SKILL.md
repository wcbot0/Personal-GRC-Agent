---
name: risk-analyst
description: Produce FAIR-aligned product/tool risk assessments with STRIDE threat models. Use when reviewing vendor or product risk with findings and gaps.
---

**Risk class:** A2 (external draft — file-only when `TICKET_PROVIDER=none`)

Principal-analyst-grade commercial product/tool risk assessment. Researches product context from input, produces an implementation-ready threat model, FAIR-aligned semi-quantitative scoring (1–5), and NIST SP 800-30 risk scenarios from findings and gaps. Formal risk acceptance requires human approval (A5 blocked).

## Inputs

Markdown with:

- `#` title (required)
- `Product:`, `Vendor:`, `Use case:`, `Data classification:` (optional structured fields)
- `## Findings` and/or `## Gaps` bullet lists (at least one required)
- `## Architecture`, `## Integrations`, `## Research notes` (optional — enrich product profile and threat model)

## Outputs

| Field | Description |
|-------|-------------|
| `executive_summary` | Principal analyst narrative: scope, posture, top risks, recommendation |
| `product_profile` | Researched product context: deployment model, assets, integrations, posture |
| `threat_model` | Implementation-ready model: trust boundaries, data flows, STRIDE threats, attack paths |
| `implementation_plan` | Prioritized security controls mapped to risk scenarios |
| `risk_scenarios[]` | FAIR + NIST scored scenarios per finding/gap |
| `summary` | Counts by inherent/residual risk tier |
| `proposed_tickets[]` | Remediation handoff (`status: ai_proposed`, `assignee: unassigned`) |
| `artifact_file` | Risk proposal JSON filename |
| `report_file` | Comprehensive assessment Markdown |
| `threat_model_file` | Standalone threat model Markdown for engineering handoff |

## Threat model structure

The `threat_model` object includes:

- **scope** — assessment boundary and assumptions
- **assets** — data, credentials, services at risk
- **trust_boundaries** — zones and crossing controls
- **data_flows** — source → destination with protocol and data class
- **entry_points** — external and internal attack surfaces
- **threat_actors** — relevant adversary profiles
- **stride_threats** — STRIDE-categorized threats with mitigations and priority
- **attack_paths** — multi-step paths from entry to impact
- **assumptions** / **out_of_scope** — explicit model boundaries

## Scoring scales (1–5)

| Score | Label |
|-------|-------|
| 1 | Very low |
| 2 | Low |
| 3 | Moderate |
| 4 | High |
| 5 | Very high |

Reference: `brain/01-frameworks/fair-taxonomy.md`, `brain/01-frameworks/nist-sp-800-30-overview.md`.

## Artifact paths

- Primary JSON: `workspace/.data/drafts/risk-analyst/risk-analyst-{timestamp}.json`
- Proposal: `workspace/proposals/risks/risk-proposal-{id}.json`
- Report: `workspace/proposals/risks/risk-assessment-{slug}.md`
- Threat model: `workspace/proposals/risks/threat-model-{slug}.md`

Promote reviewed assessments to `brain/06-risks/` after human review.