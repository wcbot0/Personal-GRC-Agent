"""risk-analyst: principal-grade product risk assessment with threat model + FAIR/NIST scoring."""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from spa.paths import resolve_output_dir
from spa.skills.io import write_text_file

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

_DEFAULT_CONTROL_TAGS = [
    "CSF:ID.RA-05",
    "CSF:GV.RM-03",
    "SOC2:CC3.2",
    "SOC2:CC9.2",
    "800-53:RA-3",
    "800-53:RA-5",
]

_RISK_MATRIX: list[list[int]] = [
    [1, 2, 3, 4, 5],
    [2, 2, 3, 4, 5],
    [3, 3, 3, 4, 5],
    [4, 4, 4, 4, 5],
    [5, 5, 5, 5, 5],
]

_PRODUCT_CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "saas_crm",
        "keywords": ["crm", "sales", "pipeline", "customer", "contact", "deal"],
        "category": "SaaS CRM / revenue platform",
        "deployment": "Multi-tenant SaaS (vendor-hosted)",
        "default_integrations": ["SSO/IdP (Okta, Entra ID)", "Email/calendar sync", "REST API + webhooks", "ETL/export connectors"],
        "default_data_stores": ["Customer records (PII)", "Sales pipeline metadata", "Activity/audit logs"],
    },
    {
        "id": "identity_broker",
        "keywords": ["identity", "sso", "idp", "okta", "auth0", "entra"],
        "category": "Identity / SSO broker",
        "deployment": "Cloud identity platform (vendor-hosted)",
        "default_integrations": ["SAML/OIDC applications", "Directory sync (LDAP/SCIM)", "MFA providers", "HRIS provisioning"],
        "default_data_stores": ["User directory", "Authentication logs", "Session tokens"],
    },
    {
        "id": "data_platform",
        "keywords": ["warehouse", "database", "analytics", "etl", "snowflake", "databricks"],
        "category": "Data platform / analytics",
        "deployment": "Cloud-managed data platform",
        "default_integrations": ["BI tools", "ETL pipelines", "Object storage", "SQL/ODBC clients"],
        "default_data_stores": ["Structured datasets", "Query audit logs", "Service credentials"],
    },
    {
        "id": "integration_platform",
        "keywords": ["api", "webhook", "integration", "middleware", "zapier", "workato"],
        "category": "Integration / automation platform",
        "deployment": "Cloud integration platform (vendor-hosted)",
        "default_integrations": ["OAuth-connected SaaS apps", "Custom HTTP endpoints", "Event triggers", "Credential vault"],
        "default_data_stores": ["Integration credentials", "Payload metadata", "Execution logs"],
    },
]

_DEFAULT_CATEGORY = {
    "id": "saas_generic",
    "category": "Commercial SaaS application",
    "deployment": "Multi-tenant SaaS (vendor-hosted)",
    "default_integrations": ["SSO/IdP", "REST API", "Admin console", "Third-party OAuth apps"],
    "default_data_stores": ["Application data", "User credentials/tokens", "Audit logs"],
}

_SCENARIO_TEMPLATES: list[dict[str, Any]] = [
    {
        "keywords": ["sso", "mfa", "auth", "password", "credential", "login", "privileged", "admin"],
        "title": "Unauthorized privileged access",
        "threat_actor": "External attacker / malicious insider",
        "threat_event": "Credential compromise of privileged account",
        "vulnerability": "Weak or missing authentication controls on privileged access",
        "effect": "Confidentiality and integrity breach; unauthorized data access",
        "stride": "Spoofing",
        "tef": 3, "vuln": 4, "cs": 2, "plm": 4, "slm": 3,
        "mitigate": "Enforce SSO and MFA for all privileged roles",
        "transfer": "Confirm cyber insurance covers SaaS credential compromise",
        "owner": "identity-team",
    },
    {
        "keywords": ["soc 2", "soc2", "attestation", "audit", "report", "stale", "certification"],
        "title": "Insufficient vendor assurance",
        "threat_actor": "Vendor / supply chain",
        "threat_event": "Undetected control failure at vendor",
        "vulnerability": "Outdated or incomplete third-party attestation",
        "effect": "Compliance gap; undetected vendor control weaknesses",
        "stride": "Information Disclosure",
        "tef": 2, "vuln": 3, "cs": 2, "plm": 3, "slm": 4,
        "mitigate": "Obtain current SOC 2 Type II report and review exceptions",
        "transfer": "Include vendor SLA and audit rights in contract",
        "owner": "vendor-risk",
    },
    {
        "keywords": ["dlp", "export", "exfil", "download", "bulk", "data leak"],
        "title": "Unauthorized data exfiltration",
        "threat_actor": "Malicious insider / compromised account",
        "threat_event": "Bulk export of sensitive data without DLP controls",
        "vulnerability": "Missing data loss prevention on export endpoints",
        "effect": "Confidentiality breach; regulatory notification required",
        "stride": "Information Disclosure",
        "tef": 2, "vuln": 4, "cs": 2, "plm": 5, "slm": 4,
        "mitigate": "Enable DLP policies on bulk export and API endpoints",
        "transfer": "Confirm data breach coverage under cyber insurance",
        "owner": "data-protection",
    },
    {
        "keywords": ["api key", "secret", "token", "vault", "rotation", "key"],
        "title": "Compromised API credentials",
        "threat_actor": "External attacker",
        "threat_event": "Theft or leakage of long-lived API credentials",
        "vulnerability": "Shared or non-rotated API keys in credential stores",
        "effect": "Unauthorized API access; data manipulation or exfiltration",
        "stride": "Spoofing",
        "tef": 3, "vuln": 4, "cs": 2, "plm": 4, "slm": 3,
        "mitigate": "Implement short-lived tokens and automated key rotation",
        "transfer": "Restrict API scope and monitor anomalous usage",
        "owner": "security-engineering",
    },
    {
        "keywords": ["encrypt", "tls", "transit", "rest", "storage"],
        "title": "Inadequate data protection",
        "threat_actor": "External attacker",
        "threat_event": "Interception or exposure of unencrypted sensitive data",
        "vulnerability": "Missing or weak encryption controls",
        "effect": "Confidentiality breach of data at rest or in transit",
        "stride": "Information Disclosure",
        "tef": 2, "vuln": 3, "cs": 3, "plm": 4, "slm": 3,
        "mitigate": "Verify encryption at rest and TLS 1.2+ in transit",
        "transfer": "Contractually require vendor encryption standards",
        "owner": "cloud-security",
    },
]

_DEFAULT_TEMPLATE = {
    "title": "Control gap in third-party product",
    "threat_actor": "Varies (threat landscape dependent)",
    "threat_event": "Exploitation of identified control gap",
    "vulnerability": "Insufficient compensating controls for identified gap",
    "effect": "Potential confidentiality, integrity, or availability impact",
    "stride": "Elevation of Privilege",
    "tef": 2, "vuln": 3, "cs": 2, "plm": 3, "slm": 2,
    "mitigate": "Implement compensating controls for identified gap",
    "transfer": "Document risk and confirm insurance or contractual coverage",
    "owner": "security-team",
}

_STRIDE_BASELINE: list[dict[str, str]] = [
    {
        "category": "Spoofing",
        "component": "Authentication boundary",
        "threat": "Attacker impersonates legitimate user or service account",
        "mitigation": "Enforce SSO, MFA, and service-to-service authentication with short-lived credentials",
        "priority": "critical",
    },
    {
        "category": "Tampering",
        "component": "API / integration layer",
        "threat": "Unauthorized modification of records or configuration via API",
        "mitigation": "Implement least-privilege API scopes, request signing, and integrity monitoring",
        "priority": "high",
    },
    {
        "category": "Repudiation",
        "component": "Audit logging",
        "threat": "Actor denies performing sensitive action; insufficient forensic trail",
        "mitigation": "Enable immutable audit logs with centralized SIEM forwarding",
        "priority": "medium",
    },
    {
        "category": "Information Disclosure",
        "component": "Data export / storage",
        "threat": "Sensitive data exposed via export, misconfigured sharing, or inadequate encryption",
        "mitigation": "Apply DLP, encryption at rest/in transit, and data classification enforcement",
        "priority": "critical",
    },
    {
        "category": "Denial of Service",
        "component": "Application availability",
        "threat": "Service disruption via API abuse or resource exhaustion",
        "mitigation": "Rate limiting, WAF, and vendor SLA monitoring with failover procedures",
        "priority": "medium",
    },
    {
        "category": "Elevation of Privilege",
        "component": "Admin console / RBAC",
        "threat": "Standard user or compromised account gains administrative privileges",
        "mitigation": "Enforce RBAC, JIT admin access, and periodic access reviews",
        "priority": "critical",
    },
]


def _parse_field(content: str, field: str) -> str | None:
    match = re.search(rf"(?im)^{re.escape(field)}\s*:\s*(.+)$", content)
    return match.group(1).strip() if match else None


def _parse_section(content: str, heading: str) -> list[str]:
    pattern = rf"(?im)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, content)
    if not match:
        return []
    rest = content[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", rest)
    block = rest[: next_heading.start()] if next_heading else rest
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif stripped.startswith("* "):
            items.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            items.append(stripped)
    return items


def _parse_section_text(content: str, heading: str) -> str | None:
    items = _parse_section(content, heading)
    return "\n".join(items) if items else None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "unspecified"


def _risk_level(score: int) -> str:
    if score <= 2:
        return "low"
    if score == 3:
        return "moderate"
    return "high"


def _inherent_risk(likelihood: int, impact: int) -> int:
    li = max(1, min(5, likelihood)) - 1
    ii = max(1, min(5, impact)) - 1
    return _RISK_MATRIX[li][ii]


def _loss_event_frequency(tef: int, vuln: int, cs: int) -> int:
    raw = tef * 0.4 + vuln * 0.4 + (6 - cs) * 0.2
    return max(1, min(5, round(raw)))


def _residual_risk(inherent: int, control_strength: int) -> int:
    reduction = max(0, control_strength - 2)
    return max(1, inherent - reduction)


def _detect_product_category(product: str, use_case: str | None, content: str) -> dict[str, Any]:
    corpus = f"{product} {use_case or ''} {content}".lower()
    for cat in _PRODUCT_CATEGORIES:
        if any(kw in corpus for kw in cat["keywords"]):
            return cat
    return _DEFAULT_CATEGORY


def _infer_compliance_posture(findings: list[str]) -> str:
    lower = " ".join(findings).lower()
    if "soc 2" in lower or "soc2" in lower:
        if any(k in lower for k in ("stale", "in progress", "expired", "missing")):
            return "SOC 2 attestation present but outdated or incomplete"
        return "SOC 2 attestation referenced"
    return "Compliance posture not fully established from available evidence"


def _build_product_profile(parsed: dict[str, Any], content: str) -> dict[str, Any]:
    product = parsed["product"]
    vendor = parsed["vendor"]
    use_case = parsed.get("use_case")
    findings = parsed.get("findings", [])
    category = _detect_product_category(product, use_case, content)

    architecture = _parse_section_text(content, "Architecture")
    integrations_input = _parse_section(content, "Integrations")
    research_notes = _parse_section(content, "Research notes")

    integration_surface = integrations_input or list(category["default_integrations"])
    if use_case and "sso" in use_case.lower() and "SSO/IdP" not in " ".join(integration_surface):
        integration_surface = ["SSO/IdP federation"] + integration_surface

    architecture_summary = architecture or (
        f"{vendor} {product} operates as {category['deployment'].lower()}. "
        f"Primary use case: {use_case or 'business application workload'}. "
        f"Users authenticate via corporate identity; data flows through vendor-managed "
        f"application tier, API layer, and persistent storage."
    )

    research_sources = ["Analyst input (findings/gaps assessment)"]
    if research_notes:
        research_sources.extend(research_notes)
    if architecture:
        research_sources.append("Architecture notes provided in assessment input")
    if integrations_input:
        research_sources.append("Integration inventory provided in assessment input")
    research_sources.append(f"Product category inference: {category['category']}")

    return {
        "product_category": category["category"],
        "deployment_model": category["deployment"],
        "architecture_summary": architecture_summary,
        "integration_surface": integration_surface,
        "data_stores": list(category["default_data_stores"]),
        "compliance_posture": _infer_compliance_posture(findings),
        "research_sources": research_sources,
    }


def _build_threat_model(
    *,
    product: str,
    vendor: str,
    profile: dict[str, Any],
    parsed: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    data_class = parsed.get("data_classification") or "Internal"
    use_case = parsed.get("use_case") or "business application"

    assets = [
        {"id": "A1", "name": f"{data_class} application data", "type": "data", "owner": "data-owner", "criticality": "high"},
        {"id": "A2", "name": "User and service credentials", "type": "credential", "owner": "identity-team", "criticality": "critical"},
        {"id": "A3", "name": f"{product} admin configuration", "type": "configuration", "owner": "app-owner", "criticality": "high"},
        {"id": "A4", "name": "API keys and OAuth tokens", "type": "credential", "owner": "security-engineering", "criticality": "critical"},
        {"id": "A5", "name": "Audit and activity logs", "type": "log", "owner": "security-operations", "criticality": "medium"},
    ]

    trust_boundaries = [
        {
            "id": "TB1",
            "name": "Internet → Corporate user",
            "from_zone": "Untrusted (Internet)",
            "to_zone": "Corporate identity / endpoint",
            "controls": ["Endpoint protection", "Phishing-resistant MFA", "Conditional access"],
        },
        {
            "id": "TB2",
            "name": "Corporate identity → SaaS application",
            "from_zone": "Corporate IdP",
            "to_zone": f"{vendor} {product}",
            "controls": ["SAML/OIDC federation", "SSO enforcement", "Session timeout"],
        },
        {
            "id": "TB3",
            "name": "SaaS application → Integrations",
            "from_zone": f"{vendor} application tier",
            "to_zone": "Third-party integrations / API consumers",
            "controls": ["OAuth scopes", "API key rotation", "IP allowlisting", "Webhook signing"],
        },
        {
            "id": "TB4",
            "name": "Vendor platform → Customer data store",
            "from_zone": f"{vendor} managed infrastructure",
            "to_zone": "Persistent data storage",
            "controls": ["Encryption at rest", "Tenant isolation", "Backup encryption"],
        },
    ]

    data_flows = [
        {
            "id": "DF1",
            "source": "Corporate user (browser)",
            "destination": f"{product} web UI",
            "protocol": "HTTPS/TLS 1.2+",
            "data_class": data_class,
            "notes": "Primary human access path",
        },
        {
            "id": "DF2",
            "source": "Corporate IdP",
            "destination": f"{product} auth endpoint",
            "protocol": "SAML 2.0 / OIDC",
            "data_class": "Authentication assertions",
            "notes": "Federated SSO path",
        },
        {
            "id": "DF3",
            "source": f"{product} API",
            "destination": "Downstream integrations",
            "protocol": "REST / webhooks",
            "data_class": data_class,
            "notes": "Machine-to-machine and automation flows",
        },
        {
            "id": "DF4",
            "source": f"{product} export endpoints",
            "destination": "User download / ETL pipeline",
            "protocol": "HTTPS / bulk export",
            "data_class": data_class,
            "notes": "High-risk exfiltration path if uncontrolled",
        },
    ]

    entry_points = [
        {"id": "EP1", "surface": "Web application UI", "exposure": "external", "auth_required": True},
        {"id": "EP2", "surface": "REST/GraphQL API", "exposure": "external", "auth_required": True},
        {"id": "EP3", "surface": "Admin / tenant configuration console", "exposure": "external", "auth_required": True},
        {"id": "EP4", "surface": "OAuth consent and third-party app connections", "exposure": "external", "auth_required": True},
        {"id": "EP5", "surface": "Webhook receivers", "exposure": "external", "auth_required": "varies"},
    ]

    threat_actors = [
        {"id": "TA1", "profile": "External opportunistic attacker", "motivation": "Credential theft, data resale", "capability": "moderate"},
        {"id": "TA2", "profile": "Malicious insider (tenant user)", "motivation": "Data exfiltration, sabotage", "capability": "moderate"},
        {"id": "TA3", "profile": "Supply chain / vendor compromise", "motivation": "Broad tenant access", "capability": "high"},
        {"id": "TA4", "profile": "Nation-state / APT (targeted)", "motivation": "Persistent access to high-value data", "capability": "high"},
    ]

    stride_threats: list[dict[str, Any]] = []
    for base in _STRIDE_BASELINE:
        stride_threats.append(
            {
                "id": f"ST-{len(stride_threats) + 1:02d}",
                "stride_category": base["category"],
                "component": base["component"],
                "threat": base["threat"],
                "mitigation": base["mitigation"],
                "priority": base["priority"],
                "status": "open",
            }
        )

    for scenario in scenarios:
        template = _match_template(scenario["source_finding"])
        stride_cat = template.get("stride", "Elevation of Privilege")
        stride_threats.append(
            {
                "id": f"ST-{len(stride_threats) + 1:02d}",
                "stride_category": stride_cat,
                "component": product,
                "threat": scenario["threat_event"],
                "mitigation": next(
                    (t["action"] for t in scenario["treatment_options"] if t["response"] == "mitigate"),
                    "Implement compensating control",
                ),
                "priority": "critical" if scenario["nist_800_30"]["residual_risk"] >= 4 else "high",
                "status": "open",
                "linked_risk_id": scenario["id"],
                "source_finding": scenario["source_finding"],
            }
        )

    high_risk = sorted(scenarios, key=lambda s: s["nist_800_30"]["residual_risk"], reverse=True)
    attack_paths = []
    for i, scenario in enumerate(high_risk[:3], start=1):
        attack_paths.append(
            {
                "id": f"AP{i:02d}",
                "name": f"Path to {scenario['title'].lower()}",
                "steps": [
                    f"Reconnaissance: identify {product} tenant and entry points",
                    f"Initial access: exploit — {scenario['vulnerability']}",
                    f"Execution: {scenario['threat_event']}",
                    f"Impact: {scenario['effect']}",
                ],
                "linked_risk_id": scenario["id"],
                "likelihood": scenario["nist_800_30"]["likelihood"],
                "impact": scenario["nist_800_30"]["impact"],
            }
        )

    return {
        "scope": (
            f"Threat model for {vendor} {product} in context of: {use_case}. "
            f"Covers tenant-facing application, API/integration layer, and vendor-managed "
            f"infrastructure boundaries relevant to {data_class} data."
        ),
        "assets": assets,
        "trust_boundaries": trust_boundaries,
        "data_flows": data_flows,
        "entry_points": entry_points,
        "threat_actors": threat_actors,
        "stride_threats": stride_threats,
        "attack_paths": attack_paths,
        "assumptions": [
            f"{vendor} maintains baseline platform security (patching, hypervisor isolation)",
            "Corporate IdP is configured with phishing-resistant MFA for privileged users",
            "Network egress from corporate endpoints is monitored",
            f"Assessment based on provided findings; no live penetration test performed",
        ],
        "out_of_scope": [
            "Vendor internal infrastructure and proprietary source code",
            "Physical security of vendor data centers (covered by vendor attestations)",
            "Social engineering campaigns targeting non-technical staff (separate program)",
            "Zero-day vulnerabilities in underlying cloud provider hypervisor",
        ],
    }


def _build_implementation_plan(scenarios: list[dict[str, Any]], threat_model: dict[str, Any]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    phase1: list[dict[str, Any]] = []

    for scenario in sorted(scenarios, key=lambda s: s["nist_800_30"]["residual_risk"], reverse=True):
        if scenario["nist_800_30"]["residual_risk"] < 3:
            continue
        mitigate = next((t for t in scenario["treatment_options"] if t["response"] == "mitigate"), None)
        if not mitigate:
            continue
        template = _match_template(scenario["source_finding"])
        phase1.append(
            {
                "phase": "Phase 1 — Immediate (0–30 days)",
                "priority": "critical" if scenario["nist_800_30"]["residual_risk"] >= 4 else "high",
                "control": mitigate["action"],
                "rationale": f"Addresses {scenario['id']} ({scenario['title']}) with residual risk {scenario['nist_800_30']['residual_risk']}/5",
                "suggested_owner": mitigate.get("suggested_owner", "security-team"),
                "risk_ids": [scenario["id"]],
                "stride_categories": [template.get("stride", "Elevation of Privilege")],
            }
        )

    plan.extend(phase1[:4])

    plan.append(
        {
            "phase": "Phase 2 — Hardening (30–90 days)",
            "priority": "high",
            "control": "Deploy continuous control monitoring: SSO/MFA coverage, API key inventory, export anomaly detection",
            "rationale": "Operationalize detective controls across trust boundaries TB2 and TB3",
            "suggested_owner": "security-engineering",
            "risk_ids": [s["id"] for s in scenarios],
            "stride_categories": ["Spoofing", "Information Disclosure"],
        }
    )

    critical_stride = [st for st in threat_model["stride_threats"] if st["priority"] == "critical" and st["status"] == "open"]
    for st in critical_stride[:2]:
        if any(p["control"] == st["mitigation"] for p in plan):
            continue
        plan.append(
            {
                "phase": "Phase 2 — Hardening (30–90 days)",
                "priority": "high",
                "control": st["mitigation"],
                "rationale": f"Closes STRIDE gap ({st['stride_category']}) on {st['component']}",
                "suggested_owner": "security-engineering",
                "risk_ids": [st["linked_risk_id"]] if st.get("linked_risk_id") else [],
                "stride_categories": [st["stride_category"]],
            }
        )

    plan.append(
        {
            "phase": "Phase 3 — Assurance (90+ days)",
            "priority": "medium",
            "control": "Establish annual vendor risk review cycle with attestation refresh and tabletop exercise",
            "rationale": "Maintain NIST 800-30 'Maintain' phase; validate residual risk acceptance decisions",
            "suggested_owner": "vendor-risk",
            "risk_ids": [s["id"] for s in scenarios if s["nist_800_30"]["residual_risk"] >= 3],
            "stride_categories": ["Repudiation"],
        }
    )

    return plan


def _build_executive_summary(
    *,
    product: str,
    vendor: str,
    profile: dict[str, Any],
    summary: dict[str, int],
    scenarios: list[dict[str, Any]],
) -> str:
    top = sorted(scenarios, key=lambda s: s["nist_800_30"]["residual_risk"], reverse=True)[:3]
    top_titles = ", ".join(s["title"] for s in top)
    posture = profile["compliance_posture"]

    if summary["high_residual"] >= 2:
        recommendation = "Conditional approval — implement Phase 1 controls before production expansion"
    elif summary["high_residual"] == 1:
        recommendation = "Approved with remediation plan — track Phase 1 items to closure"
    else:
        recommendation = "Approved with standard monitoring — no critical residual risks identified"

    return (
        f"This assessment evaluates {vendor} {product} ({profile['product_category']}) as a "
        f"{profile['deployment_model']} supporting {profile.get('architecture_summary', 'business operations')[:80]}. "
        f"Analysis identified {summary['total_scenarios']} risk scenarios: "
        f"{summary['high_inherent']} high inherent and {summary['high_residual']} high residual. "
        f"Top concerns: {top_titles}. Compliance posture: {posture}. "
        f"Recommendation: {recommendation}."
    )


def _match_template(finding: str) -> dict[str, Any]:
    lower = finding.lower()
    for template in _SCENARIO_TEMPLATES:
        if any(kw in lower for kw in template["keywords"]):
            return template
    return _DEFAULT_TEMPLATE


def _derive_scenario(
    finding: str,
    *,
    idx: int,
    product: str,
    data_classification: str,
) -> dict[str, Any]:
    template = _match_template(finding)
    asset = f"{data_classification} data in {product}" if data_classification else f"Data and services in {product}"

    tef, vuln, cs = template["tef"], template["vuln"], template["cs"]
    plm, slm = template["plm"], template["slm"]
    lef = _loss_event_frequency(tef, vuln, cs)
    likelihood, impact = lef, max(plm, slm)
    inherent = _inherent_risk(likelihood, impact)
    residual = _residual_risk(inherent, cs)

    treatments: list[dict[str, str]] = [
        {"response": "mitigate", "action": template["mitigate"], "suggested_owner": template["owner"]},
        {"response": "transfer", "action": template["transfer"]},
    ]
    if residual <= 2:
        treatments.append(
            {
                "response": "accept",
                "action": f"Accept residual risk for: {finding[:80]}",
                "note": "Formal acceptance requires human approval (A5 blocked in MVP)",
            }
        )

    return {
        "id": f"RISK-{idx:03d}",
        "title": template["title"],
        "asset": asset,
        "threat_actor": template["threat_actor"],
        "threat_event": template["threat_event"],
        "vulnerability": finding,
        "effect": template["effect"],
        "source_finding": finding,
        "fair": {
            "threat_event_frequency": tef,
            "vulnerability": vuln,
            "control_strength": cs,
            "loss_event_frequency": lef,
            "primary_loss_magnitude": plm,
            "secondary_loss_magnitude": slm,
        },
        "nist_800_30": {
            "likelihood": likelihood,
            "impact": impact,
            "inherent_risk": inherent,
            "residual_risk": residual,
            "risk_level": _risk_level(residual),
        },
        "treatment_options": treatments,
    }


def _build_summary(scenarios: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_scenarios": len(scenarios),
        "high_inherent": sum(1 for s in scenarios if s["nist_800_30"]["inherent_risk"] >= 4),
        "high_residual": sum(1 for s in scenarios if s["nist_800_30"]["residual_risk"] >= 4),
        "moderate_inherent": sum(1 for s in scenarios if s["nist_800_30"]["inherent_risk"] == 3),
        "moderate_residual": sum(1 for s in scenarios if s["nist_800_30"]["residual_risk"] == 3),
    }


def _proposed_tickets(scenarios: list[dict[str, Any]], product: str) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for i, scenario in enumerate(scenarios, start=1):
        if scenario["nist_800_30"]["residual_risk"] < 3:
            continue
        mitigate = next((t for t in scenario["treatment_options"] if t["response"] == "mitigate"), None)
        if not mitigate:
            continue
        tickets.append(
            {
                "id": f"AI-PROPOSED-RISK-{i:03d}",
                "title": f"[{product}] {scenario['title']}",
                "description": (
                    f"Risk scenario {scenario['id']}: {scenario['source_finding']}\n\n"
                    f"Recommended action: {mitigate['action']}\n\n"
                    f"Residual risk score: {scenario['nist_800_30']['residual_risk']}/5"
                ),
                "status": "ai_proposed",
                "assignee": "unassigned",
                "suggested_owner": mitigate.get("suggested_owner", "security-team"),
                "priority": "high" if scenario["nist_800_30"]["residual_risk"] >= 4 else "medium",
                "control_tags": _DEFAULT_CONTROL_TAGS,
            }
        )
    return tickets


def _render_threat_model_doc(
    *,
    product: str,
    vendor: str,
    threat_model: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    lines = [
        f"# Threat Model: {product}",
        "",
        f"**Vendor:** {vendor}  ",
        f"**Category:** {profile['product_category']}  ",
        f"**Deployment:** {profile['deployment_model']}",
        "",
        "## Scope",
        "",
        threat_model["scope"],
        "",
        "## System context",
        "",
        profile["architecture_summary"],
        "",
        "### Integration surface",
        "",
    ]
    for item in profile["integration_surface"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Assets", ""])
    for asset in threat_model["assets"]:
        lines.append(f"- **{asset['id']}** — {asset['name']} ({asset['type']}, criticality: {asset['criticality']})")
    lines.extend(["", "## Trust boundaries", ""])
    for tb in threat_model["trust_boundaries"]:
        lines.append(f"### {tb['id']}: {tb['name']}")
        lines.append(f"- **From:** {tb['from_zone']}")
        lines.append(f"- **To:** {tb['to_zone']}")
        lines.append(f"- **Controls:** {', '.join(tb['controls'])}")
        lines.append("")
    lines.extend(["## Data flows", ""])
    lines.append("| ID | Source | Destination | Protocol | Data class |")
    lines.append("|----|--------|-------------|----------|------------|")
    for df in threat_model["data_flows"]:
        lines.append(
            f"| {df['id']} | {df['source']} | {df['destination']} | {df['protocol']} | {df['data_class']} |"
        )
    lines.extend(["", "## Entry points", ""])
    for ep in threat_model["entry_points"]:
        lines.append(f"- **{ep['id']}** {ep['surface']} ({ep['exposure']}, auth: {ep['auth_required']})")
    lines.extend(["", "## Threat actors", ""])
    for ta in threat_model["threat_actors"]:
        lines.append(f"- **{ta['id']}** {ta['profile']} — {ta['motivation']} (capability: {ta['capability']})")
    lines.extend(["", "## STRIDE analysis", ""])
    lines.append("| ID | Category | Component | Threat | Mitigation | Priority |")
    lines.append("|----|----------|-----------|--------|------------|----------|")
    for st in threat_model["stride_threats"]:
        lines.append(
            f"| {st['id']} | {st['stride_category']} | {st['component']} | {st['threat']} | {st['mitigation']} | {st['priority']} |"
        )
    lines.extend(["", "## Attack paths", ""])
    for ap in threat_model["attack_paths"]:
        lines.append(f"### {ap['id']}: {ap['name']}")
        for step in ap["steps"]:
            lines.append(f"1. {step}")
        lines.append(f"- Linked risk: {ap.get('linked_risk_id', 'N/A')} (L={ap['likelihood']}, I={ap['impact']})")
        lines.append("")
    lines.extend(["## Assumptions", ""])
    for a in threat_model["assumptions"]:
        lines.append(f"- {a}")
    lines.extend(["", "## Out of scope", ""])
    for o in threat_model["out_of_scope"]:
        lines.append(f"- {o}")
    lines.extend(["", "---", "*Implementation-ready draft — validate with engineering before build-out.*"])
    return "\n".join(lines)


def _render_report(
    *,
    product: str,
    vendor: str,
    use_case: str | None,
    data_classification: str | None,
    executive_summary: str,
    profile: dict[str, Any],
    threat_model: dict[str, Any],
    implementation_plan: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    summary: dict[str, int],
) -> str:
    lines = [
        f"# Third-Party Risk Assessment: {product}",
        "",
        "*Principal Security Analyst — comprehensive assessment draft*",
        "",
        "## Executive summary",
        "",
        executive_summary,
        "",
        "## Product profile",
        "",
        f"| Attribute | Value |",
        f"|-----------|-------|",
        f"| Vendor | {vendor} |",
        f"| Category | {profile['product_category']} |",
        f"| Deployment | {profile['deployment_model']} |",
        f"| Data classification | {data_classification or 'Not specified'} |",
        f"| Compliance posture | {profile['compliance_posture']} |",
        "",
        "### Architecture summary",
        "",
        profile["architecture_summary"],
        "",
        "### Research sources",
        "",
    ]
    for src in profile["research_sources"]:
        lines.append(f"- {src}")
    lines.extend(["", "## Threat model overview", "", f"**Scope:** {threat_model['scope']}", ""])
    lines.append(f"- Assets identified: {len(threat_model['assets'])}")
    lines.append(f"- Trust boundaries: {len(threat_model['trust_boundaries'])}")
    lines.append(f"- STRIDE threats: {len(threat_model['stride_threats'])} (see `threat-model-*.md` for full model)")
    lines.append(f"- Attack paths documented: {len(threat_model['attack_paths'])}")
    lines.extend(["", "## Implementation plan", ""])
    for item in implementation_plan:
        lines.append(f"### {item['phase']} — {item['control']}")
        lines.append(f"- **Priority:** {item['priority']}")
        lines.append(f"- **Rationale:** {item['rationale']}")
        if item.get("suggested_owner"):
            lines.append(f"- **Owner:** {item['suggested_owner']}")
        if item.get("risk_ids"):
            lines.append(f"- **Linked risks:** {', '.join(item['risk_ids'])}")
        lines.append("")
    lines.extend(
        [
            "## Risk register summary",
            "",
            f"- Total scenarios: {summary['total_scenarios']}",
            f"- High inherent risk (≥4): {summary['high_inherent']}",
            f"- High residual risk (≥4): {summary['high_residual']}",
            "",
            "## Risk scenarios",
            "",
        ]
    )
    for s in scenarios:
        nist, fair = s["nist_800_30"], s["fair"]
        lines.extend(
            [
                f"### {s['id']}: {s['title']}",
                "",
                f"**Source finding:** {s['source_finding']}",
                "",
                f"| Factor | Score (1–5) |",
                f"|--------|-------------|",
                f"| Threat event frequency | {fair['threat_event_frequency']} |",
                f"| Vulnerability | {fair['vulnerability']} |",
                f"| Control strength | {fair['control_strength']} |",
                f"| Loss event frequency | {fair['loss_event_frequency']} |",
                f"| Primary loss magnitude | {fair['primary_loss_magnitude']} |",
                f"| Secondary loss magnitude | {fair['secondary_loss_magnitude']} |",
                f"| NIST likelihood | {nist['likelihood']} |",
                f"| NIST impact | {nist['impact']} |",
                f"| Inherent risk | {nist['inherent_risk']} |",
                f"| Residual risk | {nist['residual_risk']} ({nist['risk_level']}) |",
                "",
                "**Treatment options:**",
                "",
            ]
        )
        for t in s["treatment_options"]:
            owner = f" (suggested: {t['suggested_owner']})" if t.get("suggested_owner") else ""
            note = f" — {t['note']}" if t.get("note") else ""
            lines.append(f"- **{t['response'].title()}:** {t['action']}{owner}{note}")
        lines.append("")
    lines.extend(["---", "*Draft assessment — promote to brain/06-risks/ after human review.*"])
    return "\n".join(lines)


def _parse_input(content: str) -> dict[str, Any]:
    title_match = re.search(r"(?im)^#\s+(.+)$", content)
    title = title_match.group(1).strip() if title_match else "Unspecified product risk assessment"

    product = _parse_field(content, "Product") or title.replace("Risk assessment:", "").strip() or "Unspecified product"
    vendor = _parse_field(content, "Vendor") or "Unspecified vendor"
    use_case = _parse_field(content, "Use case")
    data_classification = _parse_field(content, "Data classification")

    findings = _parse_section(content, "Findings")
    gaps = _parse_section(content, "Gaps")
    items = findings + gaps
    if not items:
        items = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.startswith("#") and not re.match(r"^[A-Za-z][\w\s]*:", ln)
        ]
        items = [ln for ln in items if len(ln) > 10][:5]
    if not items:
        items = ["General third-party security control gap requiring assessment"]

    return {
        "title": title,
        "product": product,
        "vendor": vendor,
        "use_case": use_case,
        "data_classification": data_classification or "Internal",
        "findings": findings,
        "gaps": gaps,
        "items": items,
    }


def create_proposal(assessment: dict[str, Any], guard: "ToolGuard | None" = None) -> dict[str, Any]:
    """Persist a risk assessment proposal (for future ingest handoff)."""
    out_dir = resolve_output_dir(None)
    risks_dir = out_dir / "risks"
    risks_dir.mkdir(parents=True, exist_ok=True)
    assessment_id = assessment.get("id", "RISK-ASSESS-001").replace("/", "-")
    path = risks_dir / f"risk-proposal-{assessment_id}.json"
    record = dict(assessment)
    record.setdefault("status", "ai_proposed")
    record.setdefault("control_tags", _DEFAULT_CONTROL_TAGS)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {"path": str(path), "record": record}


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    out_dir = resolve_output_dir(context)
    risks_dir = out_dir / "risks"
    risks_dir.mkdir(parents=True, exist_ok=True)

    parsed = _parse_input(content)
    product, vendor = parsed["product"], parsed["vendor"]
    data_classification = parsed["data_classification"]

    product_profile = _build_product_profile(parsed, content)
    scenarios = [
        _derive_scenario(item, idx=i, product=product, data_classification=data_classification)
        for i, item in enumerate(parsed["items"], start=1)
    ]
    summary = _build_summary(scenarios)
    threat_model = _build_threat_model(
        product=product, vendor=vendor, profile=product_profile, parsed=parsed, scenarios=scenarios
    )
    implementation_plan = _build_implementation_plan(scenarios, threat_model)
    executive_summary = _build_executive_summary(
        product=product, vendor=vendor, profile=product_profile, summary=summary, scenarios=scenarios
    )
    proposed_tickets = _proposed_tickets(scenarios, product)

    assessment_id, slug = "RISK-ASSESS-001", _slugify(product)
    methodology = ["NIST-SP-800-30", "FAIR-aligned", "STRIDE threat modeling"]

    core = {
        "id": assessment_id,
        "status": "ai_proposed",
        "product": product,
        "vendor": vendor,
        "use_case": parsed.get("use_case"),
        "data_classification": data_classification,
        "methodology": methodology,
        "executive_summary": executive_summary,
        "product_profile": product_profile,
        "threat_model": threat_model,
        "implementation_plan": implementation_plan,
        "risk_scenarios": scenarios,
        "summary": summary,
        "proposed_tickets": proposed_tickets,
        "control_tags": _DEFAULT_CONTROL_TAGS,
    }

    proposal_path = risks_dir / f"risk-proposal-{assessment_id}.json"
    write_text_file(context, "create_risk_proposal", proposal_path, json.dumps(core, indent=2))

    report_path = risks_dir / f"risk-assessment-{slug}.md"
    write_text_file(
        context,
        "create_risk_report",
        report_path,
        _render_report(
            product=product,
            vendor=vendor,
            use_case=parsed.get("use_case"),
            data_classification=data_classification,
            executive_summary=executive_summary,
            profile=product_profile,
            threat_model=threat_model,
            implementation_plan=implementation_plan,
            scenarios=scenarios,
            summary=summary,
        ),
    )

    threat_model_path = risks_dir / f"threat-model-{slug}.md"
    write_text_file(
        context,
        "create_risk_report",
        threat_model_path,
        _render_threat_model_doc(product=product, vendor=vendor, threat_model=threat_model, profile=product_profile),
    )

    return {
        "skill": "risk-analyst",
        "product": product,
        "vendor": vendor,
        "use_case": parsed.get("use_case"),
        "data_classification": data_classification,
        "methodology": methodology,
        "executive_summary": executive_summary,
        "product_profile": product_profile,
        "threat_model": threat_model,
        "implementation_plan": implementation_plan,
        "risk_scenarios": scenarios,
        "summary": summary,
        "proposed_tickets": proposed_tickets,
        "control_tags": _DEFAULT_CONTROL_TAGS,
        "artifact_file": proposal_path.name,
        "report_file": report_path.name,
        "threat_model_file": threat_model_path.name,
    }
