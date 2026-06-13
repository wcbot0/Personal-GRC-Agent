#!/usr/bin/env bash
# Scaffold a new skill from _template.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <skill-name>"
  exit 1
fi

NAME="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/skills/$NAME"

if [[ -e "$DEST" ]]; then
  echo "Skill already exists: $DEST"
  exit 1
fi

cp -R "$ROOT/skills/_template" "$DEST"
cat > "$DEST/SKILL.md" <<EOF
---
name: $NAME
description: Describe what this skill does. Use when <trigger condition>.
---

**Risk class:** A1 (local draft)

Describe purpose, inputs, and outputs.
EOF

mkdir -p "$DEST/verifiers" "$DEST/fixtures"
echo "- require: control_tags" > "$DEST/verifiers/rubric.md"
echo '{"type":"object","required":["skill","control_tags"]}' > "$DEST/output.schema.json"
echo "# fixture" > "$DEST/fixtures/input.md"

echo "Created skill scaffold at skills/$NAME"
