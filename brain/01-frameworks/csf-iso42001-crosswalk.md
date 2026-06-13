# CSF 2.0 ↔ ISO 42001 Crosswalk

High-level mapping between NIST CSF 2.0 categories and ISO/IEC 42001:2023 Annex A AI controls.

Tag formats: `CSF:GV.PO` · `ISO42001:A.2.2`

---

## Govern (GV)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| GV.OC Organizational Context | A.5.5, A.8.3 | Societal impact; external reporting |
| GV.RM Risk Management Strategy | A.5.2, A.5.3 | AI impact assessment process and documentation |
| GV.RR Roles & Authorities | A.3.2, A.3.3 | AI roles; concern reporting |
| GV.PO Policy | A.2.2, A.2.4 | AI policy; periodic review |
| GV.SC Supply Chain | A.10.3, A.10.2 | Third-party AI; responsibility allocation |

## Identify (ID)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| ID.AM Asset Management | A.4.2, A.4.3 | AI resource inventory; data resources |
| ID.RA Risk Assessment | A.5.2, A.5.4 | AI system impact assessment |
| ID.IM Improvement | A.2.4, Cl. 10 | Policy review; continual improvement |

## Protect (PR)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| PR.AA Identity & Access | A.9.4, A.4.6 | Responsible use; competent personnel |
| PR.AT Awareness & Training | A.4.6 | AI competence and training |
| PR.DS Data Security | A.7.2, A.7.5 | AI training data; provenance |
| PR.PS Platform Security | A.6.2.3, A.6.2.4, A.6.2.5 | Design, V&V, deployment |
| PR.IR Infrastructure Resilience | A.4.5 | Computing resources for AI systems |

## Detect (DE)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| DE.CM Continuous Monitoring | A.6.2.6, A.6.2.8 | Operation monitoring; event logs |
| DE.AE Adverse Event Analysis | A.6.2.8, A.8.4 | Event analysis; incident communication |

## Respond (RS)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| RS.MA Incident Management | A.8.4 | AI incident communication |
| RS.CO Reporting & Communication | A.8.3, A.8.5 | External reporting; interested-party information |

## Recover (RC)

| CSF 2.0 Category | Primary ISO 42001 controls | Notes |
| --- | --- | --- |
| RC.RP Recovery Execution | A.6.2.6 | Restore/monitor AI system after incidents |

---

## Thematic alignment

| Topic | CSF 2.0 | ISO 42001 |
| --- | --- | --- |
| AI governance | GV.PO, GV.RR | A.2.2, A.3.2 |
| Impact assessment | ID.RA, GV.RM | A.5.2, A.5.4 |
| Model lifecycle | PR.PS | A.6.2.* |
| Training data | PR.DS, ID.AM | A.7.2–A.7.6 |
| Third-party AI | GV.SC | A.10.3 |
| Human oversight | PR.AA | A.9.3, A.9.4 |

---

## See also

- [soc2-iso42001-crosswalk.md](soc2-iso42001-crosswalk.md)
- [iso42001-overview.md](iso42001-overview.md)
- `brain/packs/nist-ai-rmf/` — NIST AI RMF pack
