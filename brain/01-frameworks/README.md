# Frameworks — Local Reference

Canonical reference material for security frameworks used by SPA skills and the control catalog.

## Contents

| File | Framework | Use |
| --- | --- | --- |
| [csf-2.0-overview.md](csf-2.0-overview.md) | NIST CSF 2.0 | Functions, tiers, profiles, tagging |
| [csf-2.0-core.md](csf-2.0-core.md) | NIST CSF 2.0 | Full Core: 6 functions, 22 categories, 106 subcategories |
| [iso27001-overview.md](iso27001-overview.md) | ISO/IEC 27001:2022 | ISMS clauses 4–10, certification structure |
| [iso27001-annex-a.md](iso27001-annex-a.md) | ISO/IEC 27001:2022 | All 93 Annex A controls by theme |
| [soc2-overview.md](soc2-overview.md) | AICPA SOC 2 TSC | Trust Services Categories, report types, CC structure |
| [soc2-common-criteria.md](soc2-common-criteria.md) | SOC 2 Security (CC) | CC1.1–CC9.2 — mandatory Common Criteria |
| [soc2-confidentiality-privacy.md](soc2-confidentiality-privacy.md) | SOC 2 C + P | C1.1–C1.2, P1.1–P8.1 supplemental criteria |
| [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md) | CSF 2.0 ↔ ISO 27001 | High-level category/control mapping |
| [soc2-csf-crosswalk.md](soc2-csf-crosswalk.md) | SOC 2 ↔ CSF 2.0 | CC/C/P to CSF category mapping |

## Tagging convention

SPA skills tag outputs with framework identifiers:

- **CSF 2.0:** `CSF:<Category>` or `CSF:<Subcategory>` — e.g. `CSF:PR.AA`, `CSF:PR.AA-05`
- **ISO 27001:** `ISO27001:A.<control>` — e.g. `ISO27001:A.5.15`, `ISO27001:A.8.5`
- **SOC 2:** `SOC2:<criterion>` — e.g. `SOC2:CC6.1`, `SOC2:C1.1`, `SOC2:P4.3`

## Sources

- NIST CSF 2.0 — [NIST CSWP 29](https://doi.org/10.6028/NIST.CSWP.29) (February 26, 2024)
- ISO/IEC 27001:2022 — Information security, cybersecurity and privacy protection — Information security management systems — Requirements
- AICPA TSP Section 100 — [2017 Trust Services Criteria (revised points of focus 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)
