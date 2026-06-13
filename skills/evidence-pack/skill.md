---
name: evidence-pack
description: Build evidence indexes for a control and audit period. Use when preparing audit evidence or running cloud checks for a SOC2/CC control.
---

**Risk class:** A1 (local draft)

Control id + period → evidence index file under `brain/evidence/`, with optional automated cloud evidence collection via the CloudConnector when `CLOUD_PROVIDER` is configured.