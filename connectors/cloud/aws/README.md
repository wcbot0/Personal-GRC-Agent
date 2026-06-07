# AWS Cloud Evidence Connector (read-only)

Collects audit evidence from AWS via the [official AWS MCP Server](https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html). PGA never calls `boto3` directly in this layer — all AWS access goes through MCP `call_aws` with read-only checks only.

## Governance

**This connector is read-only.** `AwsCloudProvider` exposes only `collect()` and `list_capabilities()` — there are no write, create, or mutate code paths.

**IAM is the primary security boundary.** Attach a read-only IAM policy to the credential or role PGA uses (for example `ReadOnlyAccess`, or a scoped `SecurityAudit` policy). PGA's read-only check map and MCP `READ_OPERATIONS_ONLY=true` are belt-and-suspenders controls on top of IAM — they do **not** replace a least-privilege IAM policy.

Never grant mutating IAM permissions to the PGA AWS principal. `prod_iam_change` remains **A5 (blocked)** in `agent/autonomy-policy.yaml`.

## Enable path (post-MVP)

1. Rename `mcp/aws.json.disabled` → `mcp/aws.json` and set `"enabled": true`.
2. Set environment auth: `AWS_PROFILE=<read-only-profile>` **or** `AWS_ROLE_ARN=<read-only-role-arn>`.
3. Set `CLOUD_PROVIDER=aws`.
4. Set `connectors.cloud.live_write_enabled: true` in `agent/autonomy-policy.yaml` (registry gate — required even though collection is read-only).

Keep `READ_OPERATIONS_ONLY=true` in the MCP config env block.

## Redaction

Collected findings are passed through `spa.memory.redaction.redact_obj` before return and before audit log emission (account IDs, ARNs, IPs, key material in metadata).

## Supported checks

| Check | Read-only AWS CLI |
|-------|-------------------|
| `iam_account_summary` | `iam get-account-summary` |
| `iam_password_policy` | `iam get-account-password-policy` |
| `cloudtrail_trails` | `cloudtrail describe-trails` |
| `config_recorders` | `configservice describe-configuration-recorders` |
| `guardduty_detectors` | `guardduty list-detectors` |

## Default

`CLOUD_PROVIDER=none` (safe default, no network). AWS stays disabled until explicitly configured.
