# ISO/IEC 42001:2023 — Overview

**Source:** ISO/IEC 42001:2023 — Information technology — Artificial intelligence — Management system for organizations using, developing, or providing AI systems

ISO 42001 specifies requirements for establishing, implementing, maintaining, and continually improving an **AI Management System (AIMS)**. Certification audits assess **Clauses 4–10** (mandatory) and **Annex A** AI-specific controls selected via risk assessment.

SPA tag format: `ISO42001:A.<control>` — e.g. `ISO42001:A.6.2`, `ISO42001:A.7.3`. See [iso42001-annex-a.md](iso42001-annex-a.md) for Annex A controls.

Extended pack (installable): `brain/packs/iso-42001/` via `spa brain add iso-42001`.

## Standard structure

| Section | Content | Auditable? |
| --- | --- | --- |
| Clauses 4–10 | Mandatory AIMS requirements (context, leadership, planning, support, operation, evaluation, improvement) | Yes |
| **Annex A** | **38 AI reference controls** | Yes — apply per risk / SoA |

## Core themes

| Theme | Clauses / Annex A | Focus |
| --- | --- | --- |
| **Governance** | Cl. 5, A.2–A.3 | AI policy, roles, accountability |
| **Risk & impact** | Cl. 6, A.5 | AI risk assessment, impact analysis, acceptance criteria |
| **Lifecycle** | A.6 | Design, development, validation, deployment, monitoring, retirement |
| **Data** | A.7 | Training/validation data quality, provenance, bias considerations |
| **Transparency** | A.8 | Intended purpose, limitations, documentation for interested parties |
| **Use & oversight** | A.9 | Human oversight, monitoring of AI system performance |
| **Third parties** | A.10 | Supplier due diligence for models, APIs, embedded AI |

## Relationship to other frameworks

| Framework | Relationship |
| --- | --- |
| **ISO 27001** | Information security baseline; AIMS often integrated with ISMS |
| **NIST AI RMF** | Outcome-oriented functions (GOVERN/MAP/MEASURE/MANAGE); see `brain/packs/nist-ai-rmf/` |
| **SOC 2** | CC3 (risk), CC8 (change), CC9.2 (vendor) for AI-enabled services |
| **CSF 2.0** | GV.* governance, ID.RA risk, PR.PS platform security |

Crosswalks: [csf-iso42001-crosswalk.md](csf-iso42001-crosswalk.md), [soc2-iso42001-crosswalk.md](soc2-iso42001-crosswalk.md).
