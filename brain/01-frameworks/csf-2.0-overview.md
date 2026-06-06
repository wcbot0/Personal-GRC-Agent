# NIST CSF 2.0 — Overview

**Source:** [NIST Cybersecurity Framework (CSF) 2.0](https://doi.org/10.6028/NIST.CSWP.29) — NIST CSWP 29, February 26, 2024

The NIST Cybersecurity Framework provides a taxonomy of high-level cybersecurity **outcomes** — not prescriptive controls. Organizations map these outcomes to their own practices, standards, and regulations.

SPA skills tag outputs with CSF identifiers — e.g. `CSF:PR.AA`, `CSF:DE.AE-03`. See [csf-2.0-core.md](csf-2.0-core.md) for the full subcategory list.

## Core structure

| Layer | Count | Description |
| --- | --- | --- |
| Functions | 6 | Highest-level groupings (verbs) |
| Categories | 22 | Related outcomes within a Function |
| Subcategories | 106 | Specific technical and management outcomes |

Subcategory numbering retains gaps from CSF 1.1 where outcomes were relocated or merged in 2.0.

## Six Functions

| ID | Function | Summary |
| --- | --- | --- |
| **GV** | **Govern** | Cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored. *(New in 2.0 — central to the framework wheel.)* |
| **ID** | **Identify** | Current cybersecurity risks are understood (assets, threats, vulnerabilities, improvement opportunities). |
| **PR** | **Protect** | Safeguards manage cybersecurity risks (identity, training, data, platform, infrastructure resilience). |
| **DE** | **Detect** | Possible attacks and compromises are found and analyzed. |
| **RS** | **Respond** | Actions regarding detected incidents are taken. |
| **RC** | **Recover** | Assets and operations affected by incidents are restored. |

Functions should be addressed **concurrently**. GOVERN, IDENTIFY, PROTECT, and DETECT run continuously; RESPOND and RECOVER must be ready at all times.

## Categories by Function

| Function | Categories |
| --- | --- |
| Govern (GV) | GV.OC Organizational Context · GV.RM Risk Management Strategy · GV.RR Roles, Responsibilities, and Authorities · GV.PO Policy · GV.OV Oversight · GV.SC Cybersecurity Supply Chain Risk Management |
| Identify (ID) | ID.AM Asset Management · ID.RA Risk Assessment · ID.IM Improvement |
| Protect (PR) | PR.AA Identity Management, Authentication, and Access Control · PR.AT Awareness and Training · PR.DS Data Security · PR.PS Platform Security · PR.IR Technology Infrastructure Resilience |
| Detect (DE) | DE.CM Continuous Monitoring · DE.AE Adverse Event Analysis |
| Respond (RS) | RS.MA Incident Management · RS.AN Incident Analysis · RS.CO Incident Response Reporting and Communication · RS.MI Incident Mitigation |
| Recover (RC) | RC.RP Incident Recovery Plan Execution · RC.CO Incident Recovery Communication |

## Key changes from CSF 1.1

- **Govern (GV)** added as a sixth Function; governance and supply-chain outcomes moved here from other Functions.
- Subcategories reduced from 108 to 106; supply chain subcategories expanded (GV.SC now has 10).
- Category renames: e.g. `PR.AC` → `PR.AA`, `PR.IP` → absorbed into `GV.PO` / `PR.PS`; `ID.BE` removed; `RS.RP` merged into `RS.MA` / `RC.RP`.
- Online **Informative References** and **Implementation Examples** updated continuously on [nist.gov/cyberframework](https://www.nist.gov/cyberframework).

## CSF Tiers

Tiers characterize the rigor of cybersecurity risk **governance** (GOVERN) and **management** (ID, PR, DE, RS, RC). They complement — not replace — an organization's risk methodology.

| Tier | Name | Governance | Management |
| --- | --- | --- | --- |
| 1 | Partial | Ad hoc strategy; prioritization not formally risk-based | Limited awareness; irregular, case-by-case implementation |
| 2 | Risk Informed | Management-approved practices; prioritization informed by objectives/threats | Awareness exists; no organization-wide approach |
| 3 | Repeatable | Formally approved, risk-informed policies reviewed regularly | Organization-wide approach; routine information sharing |
| 4 | Adaptive | Risk strategy integrated into culture; budget aligned to risk environment | Continuous improvement; real-time/near-real-time adaptation |

Higher tiers are not automatically better — select based on risk profile, resources, and business needs.

## Organizational Profiles

Profiles describe current and/or target posture in terms of Core outcomes:

1. **Current Profile** — outcomes currently achieved (or attempted)
2. **Target Profile** — desired, prioritized outcomes
3. **Community Profile** — sector/use-case baseline published by NIST or industry groups

Typical workflow: scope → gather information → create profiles → gap analysis → action plan → implement → repeat.

## Related NIST resources

- CSF 2.0 Reference Tool — explore/export Core, Informative References, Implementation Examples
- Quick Start Guides — ERM integration, small business, supply chain, etc.
- Mappings to SP 800-53, ISO 27001, and other standards via Informative References
