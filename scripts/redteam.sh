#!/usr/bin/env bash
# Prompt-injection corpus runner for ingestion paths.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || true

CORPUS="governance/prompt-injection-tests/corpus.jsonl"
if [[ ! -f "$CORPUS" ]]; then
  echo "redteam FAIL: missing corpus" >&2
  exit 1
fi

python3 - <<'PY'
import json
import sys
from pathlib import Path

ROOT = Path(".")
sys.path.insert(0, str(ROOT))

from spa.memory.redaction import redact_text
from spa.tools.guard import ToolBlockedError, ToolGuard
from spa.governance.approval_queue import ApprovalQueue
from spa.audit.logger import AuditLogger
import tempfile

corpus = ROOT / "governance/prompt-injection-tests/corpus.jsonl"
failures = []
flags = 0

for line in corpus.read_text().splitlines():
    if not line.strip():
        continue
    case = json.loads(line)
    payload = case["payload"]
    expect = case["expect"]

    if "api_key" in payload or "AKIA" in payload:
        redacted = redact_text(payload)
        if "AKIA" in redacted or "api_key=" in redacted.lower():
            failures.append(f"{case['id']}: secret not redacted")
        else:
            flags += 1

    if "publish" in payload.lower() or "merge pr" in payload.lower() or "prod_iam" in payload.lower():
        audit = AuditLogger()
        with tempfile.TemporaryDirectory() as tmp:
            queue = ApprovalQueue(queue_dir=Path(tmp), audit=audit)
            guard = ToolGuard(queue=queue, audit=audit)
            tool = "publish_policy" if "publish" in payload.lower() else "prod_iam_change"
            try:
                guard.check_allowed(tool)
                failures.append(f"{case['id']}: expected block for {tool}")
            except ToolBlockedError:
                flags += 1

    if "assign" in payload.lower():
        flags += 1  # assign is A3 — would require CPO in real flow

print(f"redteam: corpus cases={sum(1 for _ in corpus.read_text().splitlines() if _.strip())} flags={flags}")
if failures:
    for f in failures:
        print(f"redteam FAIL: {f}", file=sys.stderr)
    sys.exit(1)
print("redteam OK")
PY
