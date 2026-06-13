# SOC 2 ↔ ISO 27001:2022 Crosswalk

High-level mapping between AICPA Trust Services Criteria and ISO/IEC 27001:2022 Annex A controls. Use with [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md) for CSF-aligned triangulation.

Tag formats: `SOC2:CC6.1` · `ISO27001:A.5.15`

---

## Common Criteria (Security) → ISO 27001

| SOC 2 | ISO 27001:2022 | Notes |
| --- | --- | --- |
| CC1.1–CC1.5 Control Environment | A.5.1–A.5.4, Cl. 5.1–5.3 | Policy, roles, segregation of duties, leadership |
| CC2.1–CC2.3 Communication & Information | A.5.1, A.6.3, Cl. 7.4 | Internal/external communication, awareness |
| CC3.1–CC3.4 Risk Assessment | Cl. 6.1.2–6.1.3, A.5.7, A.8.8 | Risk assessment, threat intel, vulnerability mgmt |
| CC4.1–CC4.2 Monitoring | Cl. 9.1, A.5.35, A.8.15–A.8.16 | Performance evaluation, independent review, logging |
| CC5.1–CC5.3 Control Activities | A.5.1, A.5.37, A.8.9 | Policy deployment, configuration management |
| CC6.1–CC6.3 Logical Access | A.5.15–A.5.18, A.8.2–A.8.5 | Access control, identity, authentication, authorization |
| CC6.4 Physical Access | A.7.1–A.7.4 | Physical security perimeters, entry, monitoring |
| CC6.5 Asset Disposal | A.7.10, A.7.14, A.8.10 | Secure disposal, equipment return, information deletion |
| CC6.6 Boundary Protection | A.8.20–A.8.22 | Network security, segregation, web filtering |
| CC6.7 Data Transmission | A.8.24, A.5.14, A.8.11 | Cryptography, information transfer, data masking |
| CC6.8 Malware/Unauthorized Software | A.8.7, A.8.19 | Protection against malware, software installation rules |
| CC7.1 Vulnerability/Config Mgmt | A.8.8, A.8.9 | Vulnerability management, configuration management |
| CC7.2 Anomaly Detection | A.8.15, A.8.16, A.5.25 | Logging, monitoring, event assessment |
| CC7.3 Incident Evaluation | A.5.25, A.5.24 | Event assessment, incident management planning |
| CC7.4 Incident Response | A.5.26, A.5.28, A.6.8 | Incident response, evidence collection, reporting |
| CC7.5 Incident Recovery | A.5.29, A.5.30, A.8.13–A.8.14 | ICT readiness, continuity, backup, redundancy |
| CC8.1 Change Management | A.8.25–A.8.32 | Secure development, change control, test environments |
| CC9.1 Business Disruption | A.5.29, A.5.30, A.8.13–A.8.14 | ICT continuity, backup, redundancy |
| CC9.2 Vendor Risk | A.5.19–A.5.23 | Supplier relationships, cloud services, supply chain |

---

## Confidentiality (C) → ISO 27001

| SOC 2 | ISO 27001:2022 | Notes |
| --- | --- | --- |
| C1.1 Identify & maintain confidential info | A.5.12–A.5.14, A.8.2–A.8.4 | Classification, labelling, access restriction |
| C1.2 Dispose of confidential info | A.8.10, A.7.10, A.7.14 | Secure deletion, equipment sanitization |

---

## Privacy (P) → ISO 27001

| SOC 2 | ISO 27001:2022 | Notes |
| --- | --- | --- |
| P1.1 Notice | A.5.34, A.5.31 | Privacy and protection of PII, legal requirements |
| P2.1 Choice & Consent | A.5.34, A.5.31 | Privacy notice, regulatory compliance |
| P3.1–P3.2 Collection | A.5.34, A.8.11 | PII protection, data masking |
| P4.1–P4.3 Use, Retention, Disposal | A.5.34, A.8.10–A.8.12 | Retention, secure deletion, DLP |
| P5.1–P5.2 Access (data subject) | A.5.34, A.5.15–A.5.18 | Subject rights, access control |
| P6.1–P6.7 Disclosure & Notification | A.5.26, A.5.28, A.5.19–A.5.22 | Incident communication, supplier disclosure |
| P7.1 Quality | A.5.34, A.8.11 | Data accuracy, masking |
| P8.1 Monitoring & Enforcement | A.5.35, A.5.36, Cl. 9.1 | Compliance review, independent assessment |

---

## Frequently used SPA mappings

| SOC 2 | ISO 27001 | CSF 2.0 | Context |
| --- | --- | --- | --- |
| CC6.1 | A.5.15, A.8.2 | PR.AA | Logical access, access reviews |
| CC7.2 | A.8.15, A.8.16 | DE.AE | Monitoring, log analysis |
| CC8.1 | A.8.25, A.8.32 | PR.PS | Change management, SDLC |
| CC9.2 | A.5.19, A.5.22 | GV.SC | Vendor / supply chain risk |

---

## Usage notes

- **Many-to-many:** One SOC 2 criterion may align with several ISO Annex A controls; derive primary controls from the organization's Statement of Applicability (SoA).
- **Clauses vs Annex A:** SOC 2 CC1–CC5 program criteria often map to ISO Clauses 4–10 (especially 5, 6, 9, 10) in addition to Annex A.
- **See also:** [soc2-csf-crosswalk.md](soc2-csf-crosswalk.md), [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md), [iso27001-annex-a.md](iso27001-annex-a.md).
