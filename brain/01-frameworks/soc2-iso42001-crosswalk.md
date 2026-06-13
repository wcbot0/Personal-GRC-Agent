# SOC 2 ↔ ISO 42001 Crosswalk

High-level mapping between AICPA Trust Services Criteria and ISO/IEC 42001:2023 Annex A AI controls.

Tag formats: `SOC2:CC3.2` · `ISO42001:A.5.2`

---

## Common Criteria (Security) → ISO 42001

| SOC 2 | ISO 42001 | Notes |
| --- | --- | --- |
| CC1.1–CC1.5 Control Environment | A.2.2, A.3.2 | AI policy, roles, leadership accountability |
| CC3.1–CC3.4 Risk Assessment | A.5.2, A.5.4, A.5.5 | AI impact assessment, individual/societal impact |
| CC4.1–CC4.2 Monitoring | A.6.2.6, A.6.2.8 | AI system monitoring, event logs |
| CC5.1–CC5.3 Control Activities | A.2.2, A.9.2 | AI policy deployment, responsible use processes |
| CC6.1–CC6.3 Logical Access | A.4.6, A.9.4 | Human resources; responsible use controls |
| CC7.1 Vulnerability/Config Mgmt | A.6.2.4, A.6.2.6 | Validation/testing; operational monitoring |
| CC7.2 Anomaly Detection | A.6.2.6, A.6.2.8 | Performance monitoring, event logging |
| CC8.1 Change Management | A.6.2.5, A.6.2.3 | Deployment, design/development documentation |
| CC9.2 Vendor Risk | A.10.3, A.10.2 | Third-party models/APIs; responsibility allocation |

---

## Privacy (P) → ISO 42001

| SOC 2 | ISO 42001 | Notes |
| --- | --- | --- |
| P1.1–P3.2 Notice, Consent, Collection | A.8.2, A.5.4 | User documentation; impact on individuals |
| P4.1–P4.3 Use, Retention, Disposal | A.7.2, A.7.4 | Training data lifecycle; data quality |
| P6.1–P6.7 Disclosure & Notification | A.8.4, A.8.3 | Incident communication; external reporting |

---

## Frequently used SPA mappings

| SOC 2 | ISO 42001 | Context |
| --- | --- | --- |
| CC3.2 | A.5.2 | AI risk / impact assessment |
| CC8.1 | A.6.2.5 | Model deployment change control |
| CC9.2 | A.10.3 | Third-party AI vendor due diligence |
| CC7.2 | A.6.2.6 | Production AI monitoring |

---

## Usage notes

- **AIMS vs ISMS:** ISO 42001 addresses AI-specific lifecycle and impact controls; pair with ISO 27001 for security baseline.
- **NIST AI RMF:** Outcome-oriented complement — see `brain/packs/nist-ai-rmf/`.
- **See also:** [csf-iso42001-crosswalk.md](csf-iso42001-crosswalk.md), [iso42001-annex-a.md](iso42001-annex-a.md).
