# ISO/IEC 27018:2019 — Overview

**Source:** ISO/IEC 27018:2019 — Information technology — Security techniques — Code of practice for protection of personally identifiable information (PII) in public clouds acting as PII processors

ISO 27018 provides **implementation guidance for PII processors** using public cloud services. It extends ISO/IEC 27002 controls with cloud-specific PII obligations and is commonly cited alongside ISO 27001 for cloud privacy assurance (often as an ISO 27001 certification extension).

SPA tag format: `ISO27018:A.<section>.<number>` — e.g. `ISO27018:A.9.2.1`, `ISO27018:A.16.1.1`. See [iso27018-controls.md](iso27018-controls.md) for control objectives.

## Scope and role

| Role | Standard focus |
| --- | --- |
| **PII controller** | Customer organization defining purpose/lawful basis |
| **PII processor (cloud provider)** | ISO 27018 primary audience — contractual and operational safeguards |
| **Joint assessment** | Vendor questionnaires often map controller obligations (SOC 2 Privacy) to processor commitments (27018) |

## Core PII processor obligations (themes)

| Theme | Summary | Representative controls |
| --- | --- | --- |
| **Customer agreement** | Process PII only per documented customer instructions | A.9.2.1 |
| **Sub-processors** | Disclose sub-processors; obtain customer authorization | A.9.3 |
| **Location & disclosure** | Inform on storage location; limit law-enforcement disclosure | A.9.5, A.18.1 |
| **Breach notification** | Notify customer of PII breaches without undue delay | A.16.1.1 |
| **Return & deletion** | Return or delete PII at contract end | A.8.2.3, A.18.1.4 |
| **Temporary files** | Protect and erase temporary PII copies | A.9.4 |
| **Audit & assurance** | Support customer audits within agreed limits | A.12.4.1 |
| **Personnel** | Confidentiality obligations for staff with PII access | A.7.1.2 |

## Relationship to other frameworks

| Framework | Relationship |
| --- | --- |
| **ISO 27001** | 27018 controls extend 27002; often certified as 27001 + 27018 extension |
| **SOC 2 Privacy (P)** | P-criteria express controller obligations; 27018 maps to processor-side evidence |
| **CSF 2.0** | GV.OC-03 (privacy), PR.DS (data security), RS.CO (breach communication) |
| **GDPR / CPRA** | Regulatory basis; 27018 operationalizes processor contractual terms |

Crosswalks: [soc2-iso27018-crosswalk.md](soc2-iso27018-crosswalk.md), [csf-iso27018-crosswalk.md](csf-iso27018-crosswalk.md).
