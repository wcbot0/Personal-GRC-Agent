# T9 — Connector contract test (adapters stay disabled)

## Context
Vendor adapters exist as disabled stubs: tickets (Linear, Jira) and GRC (Vanta,
Drata, Secureframe). The MVP must run fully on the `none` providers, and swapping
a provider must be config-only — no code edits.

## Goal
Prove provider-agnosticism via a contract test while keeping all vendor stubs
inert.

## Files touched
- `connectors/interfaces/ticket.py`, `connectors/interfaces/grc.py`,
  `connectors/interfaces/notes.py`, `connectors/interfaces/comms.py` — confirm
  the capability + gated_capability contracts.
- `connectors/registry.py` — resolve provider from `TICKET_PROVIDER` /
  `GRC_PROVIDER` env (default `none`).
- `tests/test_connectors.py` — contract test across providers.

## Acceptance criteria
- With `TICKET_PROVIDER=none` and `GRC_PROVIDER=none`, the full draft workflow
  runs file-only (no network).
- `test_none_ticket_provider_file_draft` passes (after T1/T2 unblock writes).
- A contract test asserts every vendor stub raises/declares "disabled" and is NOT
  invoked unless explicitly selected.
- Switching `TICKET_PROVIDER=linear` is rejected/no-op in MVP (stub disabled),
  with a clear "select + enable post-MVP" message.

## Do NOT
- Do not implement any live vendor API write in MVP.
