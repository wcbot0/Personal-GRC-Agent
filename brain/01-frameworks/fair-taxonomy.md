# FAIR Taxonomy — Semi-Quantitative Reference

Reference for PGA risk-analyst skill. Based on [FAIR Institute](https://www.fairinstitute.org/) factor analysis; MVP uses 1–5 scales without dollar-denominated ALE.

## FAIR model overview

FAIR decomposes risk into measurable factors:

```
Risk = Loss Event Frequency × Loss Magnitude
LEF  = Threat Event Frequency × Vulnerability
Loss Magnitude = Primary Loss + Secondary Loss
```

## Factor definitions

| Factor | Abbrev | Description |
|--------|--------|-------------|
| Threat Event Frequency | TEF | How often a threat actor attempts the threat event |
| Vulnerability | Vuln | Probability the threat event results in loss (inverse of resistance strength) |
| Control Strength | CS | Effectiveness of controls reducing TEF or Vuln (higher = stronger) |
| Loss Event Frequency | LEF | Estimated frequency of actual loss events |
| Primary Loss Magnitude | PLM | Direct losses (response, replacement, fines) |
| Secondary Loss Magnitude | SLM | Indirect losses (reputation, regulatory, customer churn) |

## Semi-quantitative scale (1–5)

| Score | TEF / LEF | Vulnerability | Control Strength | Loss Magnitude |
|-------|-----------|---------------|------------------|----------------|
| 1 | Rare | Highly resistant | Very strong | Negligible |
| 2 | Unlikely | Resistant | Strong | Minor |
| 3 | Possible | Moderate | Moderate | Moderate |
| 4 | Likely | Weak | Weak | Major |
| 5 | Frequent | Very weak | Very weak | Severe |

## MVP scoring notes

- `loss_event_frequency` ≈ weighted function of TEF, Vuln, and inverse CS
- No **Annualized Loss Expectancy (ALE)** in MVP — qualitative/semi-quant only
- Future LLM-backed version may refine factor estimates from vendor artifacts

## Control tags

- `CSF:ID.RA-05` — Risk analysis using likelihood and impact
- `CSF:GV.RM-03` — Risk management activities in policy
- `SOC2:CC3.2` — COSO risk assessment principles
