# CSF 2.0 ↔ ISO 27001:2022 Crosswalk

High-level mapping between NIST CSF 2.0 categories and ISO/IEC 27001:2022 Annex A controls. For authoritative subcategory-level mappings, use NIST CSF 2.0 **Informative References** ([nist.gov/cyberframework](https://www.nist.gov/cyberframework)).

Tag formats: `CSF:<Category>` · `ISO27001:A.<control>`

---

## Govern (GV)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| GV.OC Organizational Context | A.5.31, A.5.34, A.5.1 | Legal/regulatory context, privacy, policy foundation |
| GV.RM Risk Management Strategy | Cl. 6.1.2, 6.1.3, A.5.1 | Risk assessment/treatment is Clause 6; policy in A.5.1 |
| GV.RR Roles & Authorities | A.5.2, A.5.4, Cl. 5.3 | Roles, management responsibilities, leadership |
| GV.PO Policy | A.5.1, A.5.37, A.5.36 | Policies, documented procedures, compliance |
| GV.OV Oversight | A.5.35, Cl. 9.3 | Independent review, management review |
| GV.SC Supply Chain | A.5.19–A.5.22, A.5.23, A.5.21 | Supplier, cloud, ICT supply chain controls |

## Identify (ID)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| ID.AM Asset Management | A.5.9, A.5.10, A.5.11, A.5.12, A.5.13 | Inventory, classification, labelling, acceptable use |
| ID.RA Risk Assessment | Cl. 6.1.2, A.5.7, A.8.8 | Risk assessment process; threat intel; vulnerability mgmt |
| ID.IM Improvement | Cl. 10.2, A.5.27, A.5.35 | Continual improvement, lessons learned, review |

## Protect (PR)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| PR.AA Identity & Access | A.5.15–A.5.18, A.8.2–A.8.5, A.7.1–A.7.2 | Access control, identity, authentication; physical entry |
| PR.AT Awareness & Training | A.6.3, A.6.2 | Awareness, education; employment terms |
| PR.DS Data Security | A.8.24, A.8.10–A.8.13, A.5.14 | Cryptography, deletion, masking, DLP, backup |
| PR.PS Platform Security | A.8.9, A.8.19, A.8.7, A.8.25–A.8.28, A.8.32 | Config mgmt, software install, malware, SDLC, change |
| PR.IR Infrastructure Resilience | A.8.20–A.8.22, A.8.14, A.8.6, A.5.30 | Network security, redundancy, capacity, ICT continuity |

## Detect (DE)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| DE.CM Continuous Monitoring | A.8.15, A.8.16, A.7.4, A.6.8 | Logging, monitoring, physical monitoring, event reporting |
| DE.AE Adverse Event Analysis | A.5.25, A.8.15, A.8.16, A.5.7 | Event assessment, log analysis, threat intelligence |

## Respond (RS)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| RS.MA Incident Management | A.5.24, A.5.26, A.5.28 | IR planning, response, evidence collection |
| RS.AN Incident Analysis | A.5.25, A.5.28, A.8.15 | Event assessment, evidence, logging |
| RS.CO Reporting & Communication | A.5.5, A.5.26, A.6.8 | Authorities contact, response, event reporting |
| RS.MI Incident Mitigation | A.5.26, A.8.7, A.8.22 | Response actions; malware; network segregation |

## Recover (RC)

| CSF 2.0 Category | Primary ISO 27001 controls | Notes |
| --- | --- | --- |
| RC.RP Recovery Execution | A.5.29, A.5.30, A.8.13, A.8.14 | Disruption security, ICT continuity, backup, redundancy |
| RC.CO Recovery Communication | A.5.26, A.5.5 | Incident response communication, authorities |

---

## Thematic alignment

| Topic | CSF 2.0 | ISO 27001 |
| --- | --- | --- |
| Governance & policy | GV.* | Cl. 5, A.5.1–A.5.4 |
| Risk management | GV.RM, ID.RA | Cl. 6.1 |
| Asset inventory | ID.AM | A.5.9–A.5.13 |
| Access control | PR.AA | A.5.15–A.5.18, A.8.2–A.8.5 |
| Supplier / supply chain | GV.SC | A.5.19–A.5.23 |
| Cloud security | GV.SC, PR.IR | A.5.23 |
| Secure development | PR.PS | A.8.25–A.8.31 |
| Monitoring & logging | DE.CM, DE.AE | A.8.15, A.8.16 |
| Incident response | RS.*, RC.* | A.5.24–A.5.28, A.6.8 |
| Business continuity | RC.RP, PR.IR | A.5.29, A.5.30, A.8.13–A.8.14 |
| Physical security | PR.AA-06 | A.7.* |
| HR security | GV.RR-04, PR.AT | A.6.* |
| Privacy / PII | GV.OC-03 | A.5.34, A.8.11 |

---

## Usage notes

- **Many-to-many:** One CSF subcategory may map to several ISO controls; one ISO control may support multiple CSF outcomes.
- **Clauses vs Annex A:** ISO Clauses 4–10 (especially 6, 9, 10) implement CSF Govern and Identify outcomes at the program level; Annex A controls implement Protect/Detect/Respond/Recover outcomes.
- **SoA exclusions:** ISO allows excluding Annex A controls with documented justification; CSF has no exclusions — organizations prioritize which outcomes to target in Profiles.
- **Authoritative mapping:** NIST OLIR Informative References provide machine-readable CSF ↔ ISO 27001 mappings at subcategory granularity. Submit mapping suggestions to olir@nist.gov.
