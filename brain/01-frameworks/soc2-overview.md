# SOC 2 — Trust Services Criteria Overview

**Source:** AICPA TSP Section 100 — [2017 Trust Services Criteria (With Revised Points of Focus — 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)

SOC 2 examinations report on controls at a service organization relevant to one or more **Trust Services Categories (TSC)**. Criteria are aligned to the COSO Internal Control — Integrated Framework (2013), with supplemental criteria for technology-specific areas.

SPA tag format: `SOC2:<criterion>` — e.g. `SOC2:CC6.1`, `SOC2:C1.1`, `SOC2:P4.3`.

## Five Trust Services Categories

| Category | Criteria | Required? | Summary |
| --- | --- | --- | --- |
| **Security** | CC1–CC9 (Common Criteria) | **Yes — every SOC 2 report** | Information and systems protected against unauthorized access, disclosure, and damage |
| **Availability** | CC + A series | Optional | Information and systems available for operation and use |
| **Processing Integrity** | CC + PI series | Optional | System processing complete, valid, accurate, timely, authorized |
| **Confidentiality** | CC + C series | Optional | Information designated confidential is protected through its lifecycle |
| **Privacy** | CC + P series | Optional | Personal information collected, used, retained, disclosed, and disposed per objectives |

**Security = Common Criteria (CC).** No additional category-specific criteria are needed for Security alone. Confidentiality and Privacy each add supplemental criteria on top of CC.

## Report types

| Type | Scope | Opinion on operating effectiveness? |
| --- | --- | --- |
| Type I | Design of controls at a point in time | No |
| Type II | Design and operating effectiveness over a period (typically 6–12 months) | Yes |

## Common Criteria structure (CC1–CC9)

| Series | COSO alignment | Focus |
| --- | --- | --- |
| CC1 | Principles 1–5 | Control environment |
| CC2 | Principles 13–15 | Communication and information |
| CC3 | Principles 6–9 | Risk assessment |
| CC4 | Principles 16–17 | Monitoring activities |
| CC5 | Principles 10–12 | Control activities (design/implementation) |
| CC6 | Supplemental | Logical and physical access controls |
| CC7 | Supplemental | System operations |
| CC8 | Supplemental | Change management |
| CC9 | Supplemental | Risk mitigation |

33 Common Criteria total (CC1.1–CC1.5, CC2.1–CC2.3, CC3.1–CC3.4, CC4.1–CC4.2, CC5.1–CC5.3, CC6.1–CC6.8, CC7.1–CC7.5, CC8.1, CC9.1–CC9.2).

Full criterion text: [soc2-common-criteria.md](soc2-common-criteria.md).

## Confidentiality vs Privacy

| | Confidentiality (C) | Privacy (P) |
| --- | --- | --- |
| **Scope** | Any information designated confidential (proprietary, trade secrets, customer data under NDA) | **Personal information only** |
| **Criteria** | C1.1, C1.2 (2 criteria) | P1.1–P8.1 (8 categories, 18 criteria) |
| **When to include** | Contractual or policy commitments to protect classified/sensitive data | Organization **directly collects** personal information from data subjects |
| **Key distinction** | Protects designated confidential info from unauthorized access/disclosure | Governs collection, consent, use, retention, access rights, breach notification for PII |

Include Privacy only when the service organization acts as a data collector/controller relative to data subjects — not when it merely processes customer-owned data on their behalf (Confidentiality may suffice).

Full C and P criteria: [soc2-confidentiality-privacy.md](soc2-confidentiality-privacy.md).

## Key concepts

**Entity's objectives** — In a SOC 2 engagement, criteria are evaluated against the service organization's **commitments to customers** (contracts, SLAs, privacy notices) and **system requirements** (laws, regulations, industry standards).

**Points of focus** — Illustrative characteristics for each criterion; not a checklist. Management may customize or substitute characteristics. The 2022 revision added points of focus (e.g., CC1.3/CC1.5 privacy reporting lines; CC9.2 vendor vulnerability risks) without changing the criteria themselves.

**System description** — Management provides a description of the system in scope; the auditor tests controls mapped to selected TSC categories.

## Related files

| File | Content |
| --- | --- |
| [soc2-common-criteria.md](soc2-common-criteria.md) | CC1.1–CC9.2 (Security / Common Criteria) |
| [soc2-confidentiality-privacy.md](soc2-confidentiality-privacy.md) | C1.1–C1.2, P1.1–P8.1 |
| [soc2-csf-crosswalk.md](soc2-csf-crosswalk.md) | SOC 2 ↔ NIST CSF 2.0 mapping |

## Sources

- AICPA TSP Section 100 (2017 TSC, revised points of focus 2022)
- AICPA Guide: SOC 2 Reporting on Controls at a Service Organization (2018)
