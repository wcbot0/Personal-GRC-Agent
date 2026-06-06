# ISO/IEC 27001:2022 — Overview

**Source:** ISO/IEC 27001:2022 — Information security, cybersecurity and privacy protection — Information security management systems — Requirements

ISO 27001 specifies requirements for establishing, implementing, maintaining, and continually improving an **Information Security Management System (ISMS)**. Certification audits assess **Clauses 4–10** (mandatory) and **Annex A** controls selected via risk assessment.

SPA tag format: `ISO27001:A.<control>` — e.g. `ISO27001:A.5.15`, `ISO27001:A.8.5`. See [iso27001-annex-a.md](iso27001-annex-a.md) for all 93 controls.

## Standard structure

| Section | Content | Auditable? |
| --- | --- | --- |
| Clauses 0–3 | Introduction, scope, normative references, terms | No |
| **Clauses 4–10** | **Mandatory ISMS requirements** | **Yes — all required** |
| **Annex A** | **93 reference controls** (from ISO/IEC 27002:2022) | **Yes — must consider all; apply per risk** |

Annex A controls are **not all mandatory**. Organizations must **consider** all 93 controls, apply those relevant to identified risks, and document inclusions/exclusions with justification in the **Statement of Applicability (SoA)**.

## PDCA alignment

| Phase | Clauses | Focus |
| --- | --- | --- |
| **Plan** | 4, 5, 6 | Context, leadership, risk assessment, risk treatment, objectives |
| **Do** | 7, 8 | Resources, competence, documentation, operational execution |
| **Check** | 9 | Monitoring, internal audit, management review |
| **Act** | 10 | Nonconformities, corrective action, continual improvement |

## Clauses 4–10 (mandatory requirements)

### Clause 4 — Context of the Organization

| Sub-clause | Requirement |
| --- | --- |
| 4.1 | Understand the organization and its context (internal/external issues affecting the ISMS) |
| 4.2 | Understand needs and expectations of interested parties relevant to information security |
| 4.3 | Determine the scope of the ISMS (boundaries, applicability) |
| 4.4 | Establish, implement, maintain, and continually improve the ISMS |

**Key deliverable:** documented ISMS scope.

### Clause 5 — Leadership

| Sub-clause | Requirement |
| --- | --- |
| 5.1 | Top management demonstrates leadership and commitment (9 specific responsibilities) |
| 5.2 | Establish an information security policy appropriate to the organization's purpose |
| 5.3 | Assign and communicate organizational roles, responsibilities, and authorities for information security |

**Key deliverable:** information security policy signed by top management.

### Clause 6 — Planning

| Sub-clause | Requirement |
| --- | --- |
| 6.1.1 | Address risks and opportunities relevant to the ISMS |
| 6.1.2 | Perform and document information security risk assessment (criteria, consistent methodology, results, risk owners) |
| 6.1.3 | Define information security risk treatment; produce risk treatment plan and **Statement of Applicability (SoA)**; obtain risk owner approval |
| 6.2 | Set measurable information security objectives and plans to achieve them |
| 6.3 | Plan changes to the ISMS in a controlled manner |

**Key deliverables:** risk assessment, risk treatment plan, Statement of Applicability.

### Clause 7 — Support

| Sub-clause | Requirement |
| --- | --- |
| 7.1 | Determine and provide resources needed for the ISMS |
| 7.2 | Ensure personnel are competent (education, training, experience) |
| 7.3 | Ensure personnel are aware of the policy, their contribution, and implications of nonconformance |
| 7.4 | Determine internal and external communications relevant to the ISMS |
| 7.5 | Control documented information required by the standard and the ISMS |

### Clause 8 — Operation

| Sub-clause | Requirement |
| --- | --- |
| 8.1 | Plan, implement, and control processes needed to meet ISMS requirements and implement actions from Clause 6 |
| 8.2 | Perform information security risk assessments at planned intervals or when significant changes occur |
| 8.3 | Implement the information security risk treatment plan |

### Clause 9 — Performance Evaluation

| Sub-clause | Requirement |
| --- | --- |
| 9.1 | Monitor, measure, analyze, and evaluate ISMS performance |
| 9.2 | Conduct internal audits at planned intervals |
| 9.3 | Top management reviews the ISMS at planned intervals |

**Key deliverables:** internal audit program and records, management review records.

### Clause 10 — Improvement

| Sub-clause | Requirement |
| --- | --- |
| 10.1 | React to nonconformities; take corrective action; evaluate effectiveness |
| 10.2 | Continually improve the suitability, adequacy, and effectiveness of the ISMS |

## Annex A (2022 revision)

| Theme | Controls | Annex A section |
| --- | --- | --- |
| Organisational | 37 | A.5.1 – A.5.37 |
| People | 8 | A.6.1 – A.6.8 |
| Physical | 14 | A.7.1 – A.7.14 |
| Technological | 34 | A.8.1 – A.8.34 |
| **Total** | **93** | (reduced from 114 in 2013 edition) |

11 new controls added in 2022: A.5.7, A.5.23, A.5.30, A.7.4, A.8.9, A.8.10, A.8.11, A.8.12, A.8.16, A.8.23, A.8.28.

Full control list: [iso27001-annex-a.md](iso27001-annex-a.md).

## Key certification deliverables

| Deliverable | Clause |
| --- | --- |
| ISMS scope document | 4.3 |
| Information security policy | 5.2 |
| Risk assessment methodology and results | 6.1.2 |
| Risk treatment plan | 6.1.3 |
| Statement of Applicability (SoA) | 6.1.3 |
| Information security objectives | 6.2 |
| Competence records | 7.2 |
| Operational procedures | 7.5, 8.1 |
| Internal audit reports | 9.2 |
| Management review records | 9.3 |
| Corrective action records | 10.1 |

## Relationship to ISO/IEC 27002:2022

Annex A control **titles** are in ISO 27001; detailed **implementation guidance** for each control is in ISO/IEC 27002:2022. Organizations typically use 27002 when designing control implementations referenced in the SoA.

## Relationship to NIST CSF 2.0

CSF provides outcome-level taxonomy; ISO 27001 provides certifiable ISMS requirements plus a control catalog. NIST publishes Informative References mapping CSF subcategories to ISO 27001 controls. See [csf-iso27001-crosswalk.md](csf-iso27001-crosswalk.md).
