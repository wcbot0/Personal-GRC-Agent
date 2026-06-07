# repo-security-review

**Risk class:** A1 (local draft)

Lightweight security review of an open-source or local repository for common OWASP Top 10 issues, ASVS-aligned control gaps, and dependency risks. Accepts a local path or `https://` Git URL.

## Input

```markdown
Repo: /path/to/repo
Branch: main
Focus: all
```

| Field | Required | Values |
|-------|----------|--------|
| `Repo:` | yes | Local path or `https://` Git URL |
| `Branch:` | no | Default `main` (Git clones only) |
| `Focus:` | no | `all`, `dependencies`, `secrets`, `injection`, `auth`, `config` |

## Output

- Brief Markdown report: `workspace/proposals/repo-security-review-<YYYYMMDD>.md`
- Skill JSON artifact with `findings[]` ranked by exploitability

## Risk rubric (exploitability)

| Risk | Criteria |
|------|----------|
| **critical** | Live secrets/credentials; critical CVEs from audit tools; RCE patterns (`eval`, unsafe deserialization) |
| **high** | Injection patterns; SSRF with user input; auth bypass strings |
| **medium** | Security misconfigurations; unpinned deps; medium CVEs |
| **low** | Weak crypto (MD5/SHA1 for passwords); hardening gaps |
| **info** | Observations, scan skipped, no issues in scope |

## Checks

- **secrets** — hardcoded credentials (A02)
- **dependencies** — unpinned manifests + optional `pip-audit` / `npm audit` (A06)
- **injection** — SQL concat, eval, XSS patterns (A03)
- **auth** — session/auth misconfig (A01/A07)
- **config** — debug mode, CORS wildcard, committed `.env` (A05)
- **ssrf/deserial** — pickle, unsafe yaml, user-controlled fetch (A08/A10)

Each finding includes OWASP category, ASVS reference, MITRE ATT&CK technique (when mapped), and control tags.
