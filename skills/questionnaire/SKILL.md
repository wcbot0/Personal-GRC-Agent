---
name: questionnaire
description: Draft security questionnaire answers (CAIQ/SIG) grounded in brain/ policies and controls. Use for vendor security questionnaires requiring cited responses.
---

**Risk class:** A1 (local draft)

Ingest a CAIQ/SIG-style question list (markdown, CSV-like, or numbered). For each question, draft an answer with brain citations, confidence score, and `needs_human` when unsupported. Never fabricate citations — unsupported answers must set `needs_human=true`.
