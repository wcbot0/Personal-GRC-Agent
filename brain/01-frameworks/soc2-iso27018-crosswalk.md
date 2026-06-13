# SOC 2 ↔ ISO 27018 Crosswalk

High-level mapping between AICPA Trust Services Criteria (especially Privacy) and ISO/IEC 27018:2019 PII processor control objectives for public cloud services.

Tag formats: `SOC2:P4.3` · `ISO27018:A.9.2.1`

---

## Privacy (P) → ISO 27018

| SOC 2 | ISO 27018 | Notes |
| --- | --- | --- |
| P1.1 Notice | A.9.2.1, A.18.1 | Customer agreement, lawful processing terms |
| P2.1 Choice & Consent | A.9.2.1 | Process PII only per customer instructions |
| P3.1–P3.2 Collection | A.9.2.1, A.10.1 | Purpose-limited processing; audit trails |
| P4.1–P4.3 Use, Retention, Disposal | A.18.1.4, A.8.2.3, A.12.3 | Return/deletion at contract end; secure disposal; backup retention |
| P5.1–P5.2 Access (data subject) | A.9.2.1, A.12.4.1 | Support customer subject-access obligations; audit support |
| P6.1–P6.7 Disclosure & Notification | A.9.3, A.9.5, A.16.1.1, A.15.1 | Sub-processors, law-enforcement disclosure, breach notification, supplier PII terms |
| P7.1 Quality | A.10.1 | Data quality via processing records |
| P8.1 Monitoring & Enforcement | A.12.4.1, A.18.1 | Customer audit rights; compliance documentation |

---

## Common Criteria (Security) → ISO 27018

| SOC 2 | ISO 27018 | Notes |
| --- | --- | --- |
| CC6.1–CC6.3 Logical Access | A.7.1.2, A.13.1 | Personnel confidentiality; network protection for PII |
| CC6.7 Data Transmission | A.13.1 | Encrypted channels for PII in transit |
| CC7.2 Anomaly Detection | A.10.1 | Audit trails for PII processing operations |
| CC7.4 Incident Response | A.16.1.1 | PII breach notification to customer |
| CC9.2 Vendor Risk | A.9.3, A.15.1 | Sub-processor authorization and flow-down |

---

## Frequently used SPA mappings

| SOC 2 | ISO 27018 | Context |
| --- | --- | --- |
| P4.3 | A.18.1.4 | Secure disposal / return of PII at contract termination |
| P6.7 | A.16.1.1 | Breach notification to customer |
| P6.1 | A.9.3 | Sub-processor disclosure and authorization |
| CC9.2 | A.15.1 | Supplier PII contractual obligations |

---

## Usage notes

- **Controller vs processor:** SOC 2 Privacy criteria describe the **service organization's** obligations (often as processor to its customers). ISO 27018 articulates **processor** commitments in public cloud contexts.
- **27001 pairing:** 27018 extends 27002; organizations often seek ISO 27001 certification with 27018 as an extension for cloud PII.
- **See also:** [soc2-iso27001-crosswalk.md](soc2-iso27001-crosswalk.md), [csf-iso27018-crosswalk.md](csf-iso27018-crosswalk.md), [iso27018-controls.md](iso27018-controls.md).
