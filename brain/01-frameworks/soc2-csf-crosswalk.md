# SOC 2 ↔ NIST CSF 2.0 Crosswalk

High-level mapping between AICPA Trust Services Criteria and NIST CSF 2.0 categories. SOC 2 Security = Common Criteria (CC); Confidentiality and Privacy add supplemental criteria.

Tag formats: `SOC2:CC6.1` · `CSF:PR.AA-05`

---

## Common Criteria (Security) → CSF 2.0

| SOC 2 | CSF 2.0 | Notes |
| --- | --- | --- |
| CC1.1–CC1.5 Control Environment | GV.RR, GV.PO, GV.OC | Governance, roles, policy, organizational context |
| CC2.1–CC2.3 Communication & Information | GV.RM-05, PR.AT, ID.IM | Internal/external communication, awareness |
| CC3.1–CC3.4 Risk Assessment | ID.RA, GV.RM, ID.AM | Risk identification, asset criticality, change assessment |
| CC4.1–CC4.2 Monitoring | GV.OV, DE.CM, ID.IM | Control monitoring, deficiency remediation |
| CC5.1–CC5.3 Control Activities | GV.PO, PR.PS | Policy deployment, technology general controls |
| CC6.1–CC6.3 Logical Access | PR.AA | Identity, authentication, authorization, least privilege |
| CC6.4 Physical Access | PR.AA-06, A.7.* (ISO) | Physical access restrictions |
| CC6.5 Asset Disposal | PR.PS-02/03, C1.2 | Secure disposal before decommission |
| CC6.6 Boundary Protection | PR.IR-01, DE.CM-01 | Firewalls, external access controls |
| CC6.7 Data Transmission | PR.DS-02, PR.DS-01 | Encryption, DLP, removable media |
| CC6.8 Malware/Unauthorized Software | PR.PS-05, PR.PS-02 | Anti-malware, software restrictions |
| CC7.1 Vulnerability/Config Mgmt | ID.RA-01, PR.PS-01 | Vuln scanning, config standards, FIM |
| CC7.2 Anomaly Detection | DE.CM, DE.AE | Monitoring, log analysis, SIEM |
| CC7.3 Incident Evaluation | DE.AE-08, RS.MA | Security event analysis, incident declaration |
| CC7.4 Incident Response | RS.MA, RS.MI, RS.CO | IR program execution, containment |
| CC7.5 Incident Recovery | RC.RP, RC.CO | Recovery activities, lessons learned |
| CC8.1 Change Management | PR.PS-01, PR.PS-06, ID.RA-07 | SDLC, change control, testing |
| CC9.1 Business Disruption | PR.IR-03, RC.RP | BCP/DR, resilience |
| CC9.2 Vendor Risk | GV.SC | Supply chain / third-party risk management |

---

## Confidentiality (C) → CSF 2.0

| SOC 2 | CSF 2.0 | Notes |
| --- | --- | --- |
| C1.1 Identify & maintain confidential info | PR.DS-01/02/10, ID.AM-05 | Classification, access restriction, data protection |
| C1.2 Dispose of confidential info | PR.DS-11, PR.PS-02/03, ID.AM-08 | Secure deletion, media sanitization, lifecycle |

---

## Privacy (P) → CSF 2.0

| SOC 2 | CSF 2.0 | Notes |
| --- | --- | --- |
| P1.1 Notice | GV.OC-03, GV.PO-01 | Privacy notice, legal/regulatory requirements |
| P2.1 Choice & Consent | GV.PO-01 | Consent management policies |
| P3.1–P3.2 Collection | GV.OC-03, ID.AM-07 | Purpose-limited collection, data inventory |
| P4.1–P4.3 Use, Retention, Disposal | PR.DS-01/10/11, ID.AM-08 | Retention, secure disposal |
| P5.1–P5.2 Access (data subject) | PR.AA, GV.PO | Subject access, correction processes |
| P6.1–P6.7 Disclosure & Notification | RS.CO, GV.SC, RC.CO | Third-party disclosure, breach notification, vendor privacy |
| P7.1 Quality | ID.AM-07, PR.DS | Data accuracy, completeness |
| P8.1 Monitoring & Enforcement | GV.OV, ID.IM | Privacy complaint handling, compliance monitoring |

---

## Frequently used SPA mappings

Mappings referenced in SPA skills and brain evidence:

| SOC 2 | CSF 2.0 | Context |
| --- | --- | --- |
| CC3.2 | ID.RA, ID.AM | Risk assessment, asset identification |
| CC4.1 | GV.OV, DE.CM | Monitoring program effectiveness |
| CC6.1 | PR.AA | Logical access, access reviews |
| CC7.2 | DE.AE | Event analysis, anomaly detection |
| CC8.1 | PR.PS, GV.PO | Change management, SDLC |

Legacy CSF 1.1 tags still appear in some artifacts: `CSF:PR.AC` → `PR.AA`; `CSF:PR.IP` → `GV.PO` / `PR.PS`.

---

## SOC 2 ↔ ISO 27001 (selected)

| SOC 2 | ISO 27001:2022 |
| --- | --- |
| CC6.1–CC6.3 | A.5.15–A.5.18, A.8.2–A.8.5 |
| CC7.1 | A.8.8, A.8.9 |
| CC7.2–CC7.4 | A.5.24–A.5.26, A.8.15, A.8.16 |
| CC8.1 | A.8.25–A.8.32 |
| CC9.2 | A.5.19–A.5.22 |
| C1.1–C1.2 | A.5.12–A.5.14, A.8.10 |
| P1.1–P8.1 | A.5.34, A.6.3, A.5.31, A.5.28 |

See also [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md).
