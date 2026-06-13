# CSF 2.0 ↔ ISO 27018 Crosswalk

High-level mapping between NIST CSF 2.0 categories and ISO/IEC 27018:2019 PII processor control objectives.

Tag formats: `CSF:GV.OC-03` · `ISO27018:A.16.1.1`

---

## Govern (GV)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| GV.OC Organizational Context | A.18.1, A.9.2.1 | Legal/regulatory PII context; customer agreements |
| GV.PO Policy | A.9.2.1, A.18.1 | PII processing policy aligned with customer instructions |
| GV.SC Supply Chain | A.9.3, A.15.1 | Sub-processor authorization; supplier PII terms |

## Identify (ID)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| ID.AM Asset Management | A.8.2.3, A.9.4 | PII asset handling; temporary file protection |

## Protect (PR)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| PR.AA Identity & Access | A.7.1.2 | Personnel confidentiality for PII access |
| PR.DS Data Security | A.12.3, A.13.1, A.8.2.3 | Backup, network protection, secure disposal |
| PR.PS Platform Security | A.14.1 | Secure development for PII-processing systems |

## Detect (DE)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| DE.CM Continuous Monitoring | A.10.1 | Audit trails for PII processing |
| DE.AE Adverse Event Analysis | A.10.1, A.16.1.1 | Event logging; PII breach detection |

## Respond (RS)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| RS.CO Reporting & Communication | A.16.1.1, A.9.5 | Breach notification; disclosure requests |
| RS.MA Incident Management | A.16.1.1 | PII incident handling |

## Recover (RC)

| CSF 2.0 Category | Primary ISO 27018 controls | Notes |
| --- | --- | --- |
| RC.RP Recovery Execution | A.17.1 | Continuity of PII processing services |

---

## Thematic alignment

| Topic | CSF 2.0 | ISO 27018 |
| --- | --- | --- |
| Cloud PII contracts | GV.PO, GV.SC | A.9.2.1, A.9.3 |
| Breach notification | RS.CO | A.16.1.1 |
| Data return / deletion | PR.DS, ID.AM | A.18.1.4, A.8.2.3 |
| Sub-processors | GV.SC | A.9.3, A.15.1 |
| Audit support | DE.CM | A.12.4.1, A.10.1 |

---

## See also

- [soc2-iso27018-crosswalk.md](soc2-iso27018-crosswalk.md)
- [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md)
- [iso27018-overview.md](iso27018-overview.md)
