# Frameworks — Local Reference

Canonical reference material for security frameworks used by SPA skills and the control catalog.

## Contents

| File | Framework | Use |
| --- | --- | --- |
| [csf-2.0-overview.md](csf-2.0-overview.md) | NIST CSF 2.0 | Functions, tiers, profiles, tagging |
| [csf-2.0-core.md](csf-2.0-core.md) | NIST CSF 2.0 | Full Core: 6 functions, 22 categories, 106 subcategories |
| [iso27001-overview.md](iso27001-overview.md) | ISO/IEC 27001:2022 | ISMS clauses 4–10, certification structure |
| [iso27001-annex-a.md](iso27001-annex-a.md) | ISO/IEC 27001:2022 | All 93 Annex A controls by theme |
| [iso27018-overview.md](iso27018-overview.md) | ISO/IEC 27018:2019 | Cloud PII processor code of practice |
| [iso27018-controls.md](iso27018-controls.md) | ISO/IEC 27018:2019 | PII control objectives |
| [iso42001-overview.md](iso42001-overview.md) | ISO/IEC 42001:2023 | AI management system (AIMS) overview |
| [iso42001-annex-a.md](iso42001-annex-a.md) | ISO/IEC 42001:2023 | Annex A AI controls |
| [soc2-overview.md](soc2-overview.md) | AICPA SOC 2 TSC | Trust Services Categories, report types, CC structure |
| [soc2-common-criteria.md](soc2-common-criteria.md) | SOC 2 Security (CC) | CC1.1–CC9.2 — mandatory Common Criteria |
| [soc2-confidentiality-privacy.md](soc2-confidentiality-privacy.md) | SOC 2 C + P | C1.1–C1.2, P1.1–P8.1 supplemental criteria |
| [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md) | CSF 2.0 ↔ ISO 27001 | High-level category/control mapping |
| [soc2-csf-crosswalk.md](soc2-csf-crosswalk.md) | SOC 2 ↔ CSF 2.0 | CC/C/P to CSF category mapping |
| [soc2-iso27001-crosswalk.md](soc2-iso27001-crosswalk.md) | SOC 2 ↔ ISO 27001 | CC/C/P to Annex A control mapping |
| [soc2-iso27018-crosswalk.md](soc2-iso27018-crosswalk.md) | SOC 2 ↔ ISO 27018 | Privacy/CC to cloud PII controls |
| [csf-iso27018-crosswalk.md](csf-iso27018-crosswalk.md) | CSF 2.0 ↔ ISO 27018 | Category to cloud PII controls |
| [soc2-iso42001-crosswalk.md](soc2-iso42001-crosswalk.md) | SOC 2 ↔ ISO 42001 | CC/P to AI Annex A controls |
| [csf-iso42001-crosswalk.md](csf-iso42001-crosswalk.md) | CSF 2.0 ↔ ISO 42001 | Category to AI Annex A controls |

## Tagging convention

SPA skills tag outputs with framework identifiers:

- **CSF 2.0:** `CSF:<Category>` or `CSF:<Subcategory>` — e.g. `CSF:PR.AA`, `CSF:PR.AA-05`
- **ISO 27001:** `ISO27001:A.<control>` — e.g. `ISO27001:A.5.15`, `ISO27001:A.8.5`
- **ISO 27018:** `ISO27018:A.<section>.<number>` — e.g. `ISO27018:A.9.2.1`, `ISO27018:A.16.1.1`
- **ISO 42001:** `ISO42001:A.<control>` — e.g. `ISO42001:A.5.2`, `ISO42001:A.6.2.6`
- **SOC 2:** `SOC2:<criterion>` — e.g. `SOC2:CC6.1`, `SOC2:C1.1`, `SOC2:P4.3`

## Sources

- NIST CSF 2.0 — [NIST CSWP 29](https://doi.org/10.6028/NIST.CSWP.29) (February 26, 2024)
- ISO/IEC 27001:2022 — Information security, cybersecurity and privacy protection — Information security management systems — Requirements
- ISO/IEC 27018:2019 — Code of practice for protection of PII in public clouds acting as PII processors
- ISO/IEC 42001:2023 — AI management system for organizations using, developing, or providing AI systems
- AICPA TSP Section 100 — [2017 Trust Services Criteria (revised points of focus 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)
