# SOC 2 — Confidentiality & Privacy Criteria

**Source:** AICPA TSP Section 100 — C series and P series

These **supplemental criteria** apply in addition to the Common Criteria (CC1–CC9) when Confidentiality and/or Privacy are in scope for a SOC 2 examination.

Tag format: `SOC2:C<n>.<n>`, `SOC2:P<n>.<n>`

---

## Confidentiality (C series)

**Category objective:** Information designated as confidential is protected to meet the entity's objectives.

Confidentiality applies to sensitive information the entity is obligated to protect — proprietary data, trade secrets, customer data under contractual confidentiality commitments, etc. It is **broader than Privacy** (which applies only to personal information).

| ID | Criterion |
| --- | --- |
| **C1.1** | The entity identifies and maintains confidential information to meet the entity's objectives related to confidentiality. |
| **C1.2** | The entity disposes of confidential information to meet the entity's objectives related to confidentiality. |

### C1.1 — key control themes

- Identify information requiring confidentiality protection (classification, labeling)
- Define and communicate confidentiality commitments to internal and external parties
- Restrict access to confidential information per classification and authorization
- Protect confidential information during storage, processing, and transmission

### C1.2 — key control themes

- Retain confidential information only as long as required
- Securely delete or destroy confidential information when no longer needed
- Apply sanitization to media and assets before disposal or reuse

### When to include Confidentiality TSC

Include when the service organization makes **explicit commitments** to protect customer or third-party confidential information — e.g., NDAs, data classification requirements, contractual confidentiality clauses. Common for B2B SaaS handling customer business data.

---

## Privacy (P series)

**Category objective:** Personal information is collected, used, retained, disclosed, and disposed of to meet the entity's objectives.

Privacy applies **only to personal information** (PII). The P criteria are organized into eight domains aligned with generally accepted privacy principles (GAPP):

| Category | ID | Criterion |
| --- | --- | --- |
| **P1 — Notice** | P1.1 | The entity provides notice to data subjects about its privacy practices to meet the entity's objectives related to privacy. The notice is updated and communicated to data subjects in a timely manner for changes to the entity's privacy practices, including changes in the use of personal information, to meet the entity's objectives related to privacy. |
| **P2 — Choice & Consent** | P2.1 | The entity communicates choices available regarding the collection, use, retention, disclosure, and disposal of personal information to the data subjects and the consequences, if any, of each choice. Explicit consent for the collection, use, retention, disclosure, and disposal of personal information is obtained from data subjects or other authorized persons, if required. Such consent is obtained only for the intended purpose of the information to meet the entity's objectives related to privacy. The entity's basis for determining implicit consent for the collection, use, retention, disclosure, and disposal of personal information is documented. |
| **P3 — Collection** | P3.1 | Personal information is collected consistent with the entity's objectives related to privacy. |
| | P3.2 | For information requiring explicit consent, the entity communicates the need for such consent as well as the consequences of a failure to provide consent for the request for personal information and obtains the consent prior to the collection of the information to meet the entity's objectives related to privacy. |
| **P4 — Use, Retention & Disposal** | P4.1 | The entity limits the use of personal information to the purposes identified in the entity's objectives related to privacy. |
| | P4.2 | The entity retains personal information consistent with the entity's objectives related to privacy. |
| | P4.3 | The entity securely disposes of personal information to meet the entity's objectives related to privacy. |
| **P5 — Access** | P5.1 | The entity grants identified and authenticated data subjects the ability to access their stored personal information for review and, upon request, provides physical or electronic copies of that information to data subjects to meet the entity's objectives related to privacy. If access is denied, data subjects are informed of the denial and reason for such denial, as required, to meet the entity's objectives related to privacy. |
| | P5.2 | The entity corrects, amends, or appends personal information based on information provided by data subjects and communicates such information to third parties, as committed or required, to meet the entity's objectives related to privacy. If a request for correction is denied, data subjects are informed of the denial and reason for such denial to meet the entity's objectives related to privacy. |
| **P6 — Disclosure & Notification** | P6.1 | The entity discloses personal information to third parties with the explicit consent of data subjects and such consent is obtained prior to disclosure to meet the entity's objectives related to privacy. |
| | P6.2 | The entity creates and retains a complete, accurate, and timely record of authorized disclosures of personal information to meet the entity's objectives related to privacy. |
| | P6.3 | The entity creates and retains a complete, accurate, and timely record of detected or reported unauthorized disclosures (including breaches) of personal information to meet the entity's objectives related to privacy. |
| | P6.4 | The entity obtains privacy commitments from vendors and other third parties who have access to personal information to meet the entity's objectives related to privacy. The entity assesses those parties' compliance on a periodic and as-needed basis and takes corrective action, if necessary. |
| | P6.5 | The entity obtains commitments from vendors and other third parties with access to personal information to notify the entity in the event of actual or suspected unauthorized disclosures of personal information. Such notifications are reported to appropriate personnel and acted on in accordance with established incident-response procedures to meet the entity's objectives related to privacy. |
| | P6.6 | The entity provides notification of breaches and incidents to affected data subjects, regulators, and others to meet the entity's objectives related to privacy. |
| | P6.7 | The entity provides data subjects with an accounting of the personal information held and disclosure of the data subjects' personal information, upon the data subjects' request, to meet the entity's objectives related to privacy. |
| **P7 — Quality** | P7.1 | The entity collects and maintains accurate, up-to-date, complete, and relevant personal information to meet the entity's objectives related to privacy. |
| **P8 — Monitoring & Enforcement** | P8.1 | The entity implements a process for receiving, addressing, resolving, and communicating the resolution of inquiries, complaints, and disputes from data subjects and others and periodically monitors compliance to meet the entity's objectives related to privacy. Corrections and other necessary actions related to identified deficiencies are made or taken in a timely manner. |

### Privacy criteria summary by domain

| Domain | Criteria count | Focus |
| --- | --- | --- |
| P1 Notice | 1 | Privacy notice, updates, communication |
| P2 Choice & Consent | 1 | Opt-in/opt-out, explicit/implicit consent documentation |
| P3 Collection | 2 | Purpose limitation, pre-collection consent |
| P4 Use, Retention & Disposal | 3 | Purpose-bound use, retention schedules, secure disposal |
| P5 Access | 2 | Subject access requests, correction/amendment |
| P6 Disclosure & Notification | 7 | Third-party disclosure, breach records, vendor privacy commitments, breach notification |
| P7 Quality | 1 | Data accuracy and relevance |
| P8 Monitoring & Enforcement | 1 | Complaint handling, compliance monitoring |

**18 privacy criteria** across 8 categories (P1.1, P2.1, P3.1–P3.2, P4.1–P4.3, P5.1–P5.2, P6.1–P6.7, P7.1, P8.1).

### When to include Privacy TSC

Include when the service organization **directly collects personal information from data subjects** (e.g., end-user registration, marketing forms, employee HR data). Often **not applicable** when the organization only processes customer-owned personal data as a processor without direct data-subject relationships — Confidentiality may be sufficient.

Criteria may be marked **Not Applicable (N/A)** with documented rationale when the service model does not trigger them (e.g., P3.1 when the entity does not directly collect personal information).

---

## CC criteria with category-specific points of focus

When Confidentiality or Privacy are in scope, additional **points of focus** apply to certain Common Criteria (criteria text unchanged):

| CC | Additional focus (Confidentiality) | Additional focus (Privacy) |
| --- | --- | --- |
| CC2.3 | Communicate confidentiality objectives to external parties | Communicate privacy objectives to external parties |
| CC7.3 | — | Assess impact on personal information; identify affected PI |
| CC7.4 | — | Communicate unauthorized use/disclosure; apply sanctions |
| CC8.1 | Protect confidential information during SDLC/change | Protect personal information during SDLC/change |
| CC9.2 | Obtain/assess vendor confidentiality commitments | Obtain/assess vendor privacy commitments |

---

## Regulatory alignment (informative)

Privacy criteria align with concepts in GDPR, CCPA/CPRA, and other privacy frameworks — but SOC 2 Privacy is **not** a legal compliance attestation. It evaluates whether controls meet the entity's **stated privacy objectives and commitments**.

Confidentiality criteria support contractual and regulatory obligations to protect non-public information but do not replace sector-specific requirements (HIPAA, PCI DSS, etc.).
