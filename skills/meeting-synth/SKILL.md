---
name: meeting-synth
description: Synthesize meeting notes into decisions, risks, action items, and proposed tickets. Use when raw meeting notes or transcripts land in the inbox.
---

**Risk class:** A1 (local draft)

Transcript or meeting notes → decisions, risks, action items, and AI-Proposed ticket files (unassigned).

## Inputs
Markdown or plain-text meeting notes/transcript.

## Outputs
- `decisions`, `risks`, `action_items` arrays
- `proposed_tickets` with `control_tags`
- `ticket-proposal-*.json` files in workspace drafts