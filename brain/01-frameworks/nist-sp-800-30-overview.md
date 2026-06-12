# NIST SP 800-30 — Risk Assessment Overview

Reference for PGA risk-analyst skill scoring. Rev. 1 guide for conducting risk assessments.

## Process (800-30)

| Phase | Activities |
|-------|------------|
| **Prepare** | Identify purpose, scope, assumptions, constraints, information sources |
| **Conduct** | Identify threats, vulnerabilities, likelihood, impact; determine risk |
| **Communicate** | Share results with decision makers |
| **Maintain** | Monitor risk factors; update assessment on change |

## Risk factors

- **Threat sources and events** — adversaries, errors, structural failures
- **Vulnerabilities and predisposing conditions** — weaknesses that enable threat realization
- **Likelihood** — probability a threat event results in adverse impact
- **Impact** — magnitude of harm (confidentiality, integrity, availability, mission)

## Semi-quantitative scale (1–5)

Used by `risk-analyst` for likelihood and impact:

| Score | Likelihood | Impact |
|-------|------------|--------|
| 1 | Very unlikely (< once per 5 years) | Negligible |
| 2 | Unlikely (once per 2–5 years) | Minor |
| 3 | Possible (once per year) | Moderate |
| 4 | Likely (multiple times per year) | Major |
| 5 | Very likely (monthly or more) | Severe / catastrophic |

## Inherent vs residual risk

- **Inherent risk** — risk before controls (likelihood × impact matrix)
- **Residual risk** — risk after controls applied
- **Risk level labels:** low (1–2), moderate (3), high (4–5)

## Risk response (800-30)

| Response | Description |
|----------|-------------|
| **Mitigate** | Implement controls to reduce likelihood or impact |
| **Transfer** | Shift risk (insurance, contractual terms) |
| **Avoid** | Eliminate the risk source (discontinue use) |
| **Accept** | Acknowledge residual risk — requires authorized decision maker |

> PGA MVP: formal risk acceptance is **A5 blocked**; skill may propose accept as draft only.

## Control tags

- `800-53:RA-3` — Risk assessment
- `800-53:RA-5` — Vulnerability monitoring and scanning
- `CSF:ID.RA-05` — Threats, vulnerabilities, likelihoods, and impacts used to determine risk
- `SOC2:CC3.2` — Fraud and change risks considered
