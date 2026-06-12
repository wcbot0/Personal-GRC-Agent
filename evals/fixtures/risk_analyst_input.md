# Risk assessment: Acme CRM Enterprise

Product: Acme CRM Enterprise
Vendor: Acme Corp
Use case: Customer PII in sales pipeline
Data classification: Confidential

## Architecture
Multi-tenant SaaS hosted in US-East (AWS). Users authenticate via Okta SAML federation.
Application tier exposes REST API and bulk CSV export. Background workers sync email/calendar.

## Integrations
- Okta SAML SSO (production)
- Salesforce bi-directional sync via REST API
- Slack notifications via OAuth app
- Snowflake nightly ETL export

## Research notes
- Vendor trust center lists SOC 2 Type II (Dec 2025) — customer copy is 6 months stale
- Admin API documented at docs.acme.example; supports service account tokens
- Subprocessor list includes AWS, SendGrid, Snowflake

## Findings
- SOC 2 Type II report is 6 months stale
- Admin accounts lack SSO enforcement
- API keys stored in shared vault without rotation policy

## Gaps
- Privileged access MFA not enforced (maps to CC6.1)
- No DLP on bulk export endpoints
