# SOC 2 — Common Criteria (Security)

**Source:** AICPA TSP Section 100 — Trust Services Criteria, CC series

The Common Criteria (CC1–CC9) form the **Security** Trust Services Category and are **mandatory in every SOC 2 examination**. Tag format: `SOC2:CC<n>.<n>`.

Criteria sourced from COSO principles appear without italics in the official document; supplemental criteria (CC6–CC9) are technology-specific.

---

## CC1 — Control Environment

### CC1.1 — COSO Principle 1
The entity demonstrates a commitment to integrity and ethical values.

### CC1.2 — COSO Principle 2
The board of directors demonstrates independence from management and exercises oversight of the development and performance of internal control.

### CC1.3 — COSO Principle 3
Management establishes, with board oversight, structures, reporting lines, and appropriate authorities and responsibilities in the pursuit of objectives.

### CC1.4 — COSO Principle 4
The entity demonstrates a commitment to attract, develop, and retain competent individuals in alignment with objectives.

### CC1.5 — COSO Principle 5
The entity holds individuals accountable for their internal control responsibilities in the pursuit of objectives.

---

## CC2 — Communication and Information

### CC2.1 — COSO Principle 13
The entity obtains or generates and uses relevant, quality information to support the functioning of internal control.

### CC2.2 — COSO Principle 14
The entity internally communicates information, including objectives and responsibilities for internal control, necessary to support the functioning of internal control.

### CC2.3 — COSO Principle 15
The entity communicates with external parties regarding matters affecting the functioning of internal control.

---

## CC3 — Risk Assessment

### CC3.1 — COSO Principle 6
The entity specifies objectives with sufficient clarity to enable the identification and assessment of risks relating to objectives.

### CC3.2 — COSO Principle 7
The entity identifies risks to the achievement of its objectives across the entity and analyzes risks as a basis for determining how the risks should be managed.

### CC3.3 — COSO Principle 8
The entity considers the potential for fraud in assessing risks to the achievement of objectives.

### CC3.4 — COSO Principle 9
The entity identifies and assesses changes that could significantly impact the system of internal control.

---

## CC4 — Monitoring Activities

### CC4.1 — COSO Principle 16
The entity selects, develops, and performs ongoing and/or separate evaluations to ascertain whether the components of internal control are present and functioning.

### CC4.2 — COSO Principle 17
The entity evaluates and communicates internal control deficiencies in a timely manner to those parties responsible for taking corrective action, including senior management and the board of directors, as appropriate.

---

## CC5 — Control Activities

### CC5.1 — COSO Principle 10
The entity selects and develops control activities that contribute to the mitigation of risks to the achievement of objectives to acceptable levels.

### CC5.2 — COSO Principle 11
The entity also selects and develops general control activities over technology to support the achievement of objectives.

### CC5.3 — COSO Principle 12
The entity deploys control activities through policies that establish what is expected and in procedures that put policies into action.

---

## CC6 — Logical and Physical Access Controls

### CC6.1
The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity's objectives.

### CC6.2
Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity. For those users whose access is administered by the entity, user system credentials are removed when user access is no longer authorized.

### CC6.3
The entity authorizes, modifies, or removes access to data, software, functions, and other protected information assets based on roles, responsibilities, or the system design and changes, giving consideration to the concepts of least privilege and segregation of duties, to meet the entity's objectives.

### CC6.4
The entity restricts physical access to facilities and protected information assets (for example, data center facilities, backup media storage, and other sensitive locations) to authorized personnel to meet the entity's objectives.

### CC6.5
The entity discontinues logical and physical protections over physical assets only after the ability to read or recover data and software from those assets has been diminished and is no longer required to meet the entity's objectives.

### CC6.6
The entity implements logical access security measures to protect against threats from sources outside its system boundaries.

### CC6.7
The entity restricts the transmission, movement, and removal of information to authorized internal and external users and processes, and protects it during transmission, movement, or removal to meet the entity's objectives.

### CC6.8
The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software to meet the entity's objectives.

---

## CC7 — System Operations

### CC7.1
To meet its objectives, the entity uses detection and monitoring procedures to identify (1) changes to configurations that result in the introduction of new vulnerabilities, and (2) susceptibilities to newly discovered vulnerabilities.

### CC7.2
The entity monitors system components and the operation of those components for anomalies that are indicative of malicious acts, natural disasters, and errors affecting the entity's ability to meet its objectives; anomalies are analyzed to determine whether they represent security events.

### CC7.3
The entity evaluates security events to determine whether they could or have resulted in a failure of the entity to meet its objectives (security incidents) and, if so, takes actions to prevent or address such failures.

### CC7.4
The entity responds to identified security incidents by executing a defined incident-response program to understand, contain, remediate, and communicate security incidents, as appropriate.

### CC7.5
The entity identifies, develops, and implements activities to recover from identified security incidents.

---

## CC8 — Change Management

### CC8.1
The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes to infrastructure, data, software, and procedures to meet its objectives.

---

## CC9 — Risk Mitigation

### CC9.1
The entity identifies, selects, and develops risk mitigation activities for risks arising from potential business disruptions.

### CC9.2
The entity assesses and manages risks associated with vendors and business partners.

---

## Quick reference — criteria by theme

| Theme | Criteria | Common SPA/evidence use |
| --- | --- | --- |
| Governance & ethics | CC1.1–CC1.5 | Tone at the top, HR screening, accountability |
| Risk management | CC3.1–CC3.4 | Risk assessments, asset inventory, vendor risk |
| Monitoring | CC4.1–CC4.2, CC7.2 | Internal audit, control deficiency tracking, SIEM |
| Access control | CC6.1–CC6.3 | IAM, MFA, access reviews, least privilege |
| Physical security | CC6.4 | Data center access, badge systems |
| Data protection | CC6.7 | Encryption in transit, DLP, removable media |
| Vulnerability mgmt | CC7.1 | Patch management, vuln scanning |
| Incident response | CC7.3–CC7.5 | IR plan, containment, recovery testing |
| Change management | CC8.1 | SDLC, change approval, emergency changes |
| Business continuity | CC9.1 | BCP/DR plans, insurance |
| Vendor management | CC9.2 | Third-party risk assessments, vendor contracts |
