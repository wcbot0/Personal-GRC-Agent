# GCP Cloud Evidence Connector (read-only)

Collects audit evidence from Google Cloud via an MCP `run_gcloud` transport. PGA never calls the Google Cloud client libraries directly in this layer — all GCP access goes through MCP with read-only checks only.

## Governance

**This connector is read-only.** `GcpCloudProvider` exposes only `collect()` and `list_capabilities()` — there are no write, create, or mutate code paths.

**IAM is the primary security boundary.** Bind a read-only / auditor-scoped IAM role to the service account or principal PGA uses (for example `roles/viewer`, `roles/securitycenter.adminViewer`, or a custom role limited to `*.get`, `*.list`, and `*.describe` on in-scope resources). PGA's read-only check map and MCP `READ_OPERATIONS_ONLY=true` are belt-and-suspenders controls on top of IAM — they do **not** replace a least-privilege IAM policy.

Never grant mutating IAM permissions (`*.create`, `*.update`, `*.delete`, `*.setIamPolicy`, etc.) to the PGA GCP principal. Production infrastructure changes remain **A5 (blocked)** in `agent/autonomy-policy.yaml`.

## Enable path (post-MVP)

1. Rename `mcp/gcp.json.disabled` → `mcp/gcp.json` and set `"enabled": true`.
2. Set environment auth:
   - `GCP_PROJECT=<project-id>` (or `GOOGLE_CLOUD_PROJECT`)
   - `GOOGLE_APPLICATION_CREDENTIALS=<path-to-readonly-sa-key.json>` **or** `GCP_SERVICE_ACCOUNT_EMAIL=<auditor-sa@project.iam.gserviceaccount.com>`
   - Optional: `GCP_ORGANIZATION_ID=<org-id>` for org-scoped SCC / org-policy checks
3. Set `CLOUD_PROVIDER=gcp`.
4. Set `connectors.cloud.live_write_enabled: true` in `agent/autonomy-policy.yaml` (registry gate — required even though collection is read-only).

Keep `READ_OPERATIONS_ONLY=true` in the MCP config env block.

## Redaction

Collected findings are passed through `spa.memory.redaction.redact_obj` before return and before audit log emission (project numbers, service account emails, IPs, key material in metadata).

## Supported checks

| Check | Read-only gcloud |
|-------|------------------|
| `iam_mfa_enforced` | `resource-manager org-policies list` |
| `service_account_key_inventory` | `iam service-accounts list` |
| `super_admin_inventory` | `projects get-iam-policy` |
| `cloud_storage_public_access` | `storage buckets list --format=json` |
| `firewall_open_ingress` | `compute firewall-rules list --format=json` |
| `cloud_storage_encryption_default` | `storage buckets list --format=json` |
| `compute_disk_encryption_default` | `compute disks list --format=json` |
| `security_command_center_enabled` | `services list --enabled --filter=name:securitycenter.googleapis.com` |
| `asset_inventory_enabled` | `services list --enabled --filter=name:cloudasset.googleapis.com` |
| `cloud_audit_logging_enabled` | `logging logs list` |
| `log_sink_configured` | `logging sinks list` |
| `security_command_center_detectors` | `scc sources list` |

Control mappings live in `brain/02-controls/cloud-checks.yaml` under the `gcp:` key.

## Default

`CLOUD_PROVIDER=none` (safe default, no network). GCP stays disabled until explicitly configured.

## Transport note

The client abstraction uses MCP tool `run_gcloud` with injectable `invoke` for tests. When a stable official GCP MCP server is wired into `mcp/gcp.json`, no provider code changes are required — only the MCP server config.
