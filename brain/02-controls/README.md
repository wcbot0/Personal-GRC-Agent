# Control catalog

Maps SOC 2 Common Criteria (and future frameworks) to cloud-provider evidence checks consumed by the evidence-pack skill and related SPA workflows.

## Files

| File | Purpose |
| --- | --- |
| `cloud-checks.yaml` | Provider-keyed mapping of control IDs → read-only cloud checks |

Framework definitions and crosswalks live under `brain/01-frameworks/` (e.g. `soc2-common-criteria.md`, `soc2-csf-crosswalk.md`). Control IDs in this catalog use the same `CC<n>.<n>` notation as those files and the `SOC2:CC<n>.<n>` tags emitted by the csf-crosswalk skill.

## `cloud-checks.yaml` format

Top-level keys are cloud providers (`aws`, `gcp`, …). Each provider block maps **control IDs** to a short description and a list of **check** identifiers:

```yaml
aws:
  CC6.1:
    description: Logical access — IAM password policy, MFA, root usage
    checks:
      - iam_password_policy
      - mfa_enforced
gcp: {}   # reserved; add mappings in H9 without restructuring
```

### Semantics

- **Human-reviewed audit logic** — this file is brain content, not executable code. Changes should be reviewed like policy updates.
- **Read-only checks only** — every check name must correspond to a read-only `collect(check, params)` operation on the provider connector (no create/update/delete).
- **All checks must pass** — a control is considered *covered* by automated cloud evidence only when **every** listed check returns satisfactory findings for the in-scope account and region. Partial pass = not covered.
- **Stable identifiers** — check names are snake_case strings shared between this file and the provider's `READ_ONLY_CHECKS` map (see `connectors/cloud/aws/provider.py`).

### Provider implementation status (AWS)

The H6 connector ships an initial read-only check set. The mapping below lists which brain check IDs are implemented today:

| Check | Implemented (H6) | AWS CLI (read-only) |
| --- | --- | --- |
| `iam_password_policy` | yes | `iam get-account-password-policy` |
| `iam_account_summary` | yes | `iam get-account-summary` |
| `cloudtrail_trails` | yes | `cloudtrail describe-trails` |
| `config_recorders` | yes | `configservice describe-configuration-recorders` |
| `guardduty_detectors` | yes | `guardduty list-detectors` |
| `mfa_enforced`, `root_account_mfa`, `root_access_keys` | planned | IAM credential report / summary fields |
| `s3_public_access_block`, `security_groups_open_ingress` | planned | S3 account public access block, EC2 security groups |
| `s3_encryption_at_rest`, `ebs_encryption_default` | planned | S3 bucket encryption, EBS default encryption |
| `cloudtrail_enabled`, `cloudtrail_multi_region` | planned | CloudTrail trail status / multi-region |
| `config_recorder_on` | planned | Config recorder recording status |

Until planned checks land in the provider, evidence-pack (H8) should treat unimplemented checks as gaps rather than failures.

## Adding a control mapping

1. Confirm the control ID exists in `brain/01-frameworks/soc2-common-criteria.md` and appears in `soc2-csf-crosswalk.md` if CSF alignment matters.
2. Choose checks that together demonstrate the control's intent for that cloud (logical access, encryption, monitoring, etc.).
3. Add an entry under the provider key in `cloud-checks.yaml` with a one-line `description` and ordered `checks` list.
4. If the check is new, add the corresponding read-only CLI fragment to the provider's `READ_ONLY_CHECKS` in a connector task (brain-first naming; implement in code separately).
5. Re-run `make selftest` and note the mapping in an evidence index under `brain/evidence/` when collecting for a period.

## Adding a check

1. Pick a **stable snake_case name** (e.g. `s3_encryption_at_rest`) — this becomes the `collect()` argument everywhere.
2. Document the read-only AWS/GCP API or CLI operation it wraps in `connectors/cloud/<provider>/README.md`.
3. Reference the check from one or more control entries in `cloud-checks.yaml`.
4. Implement `collect()` support in the provider connector (outside brain-only tasks).

## Related paths

- Evidence indexes: `brain/evidence/<control-id>/`
- AWS connector: `connectors/cloud/aws/`
- evidence-pack skill: `skills/evidence-pack/`
