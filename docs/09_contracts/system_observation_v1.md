# Contract: System Observation v1

## Purpose

Defines the internal signal format used by the private worker to accumulate competitive memory without leaking raw observation data into the app UI.

## Ownership

- produced by the private worker
- persisted in the **authoritative local worker database** (Mac mini SQLite), table `system_observations` — **not** in Neon; Neon may hold app-visible shared state only and must not be authoritative for internal observations
- consumed internally by task-generation logic
- not shown directly to end users

## Schema

```json
{
  "signal_id": "string",
  "signal_type": "pricing_change | opening | closure | staffing | offer | asset_sale | messaging_shift | proof_signal | vendor_adoption",
  "competitor": "string",
  "region": "string",
  "summary": "string",
  "source_ref": "string",
  "observed_at": "ISO timestamp",
  "confidence": "float 0-1",
  "business_impact": "low | medium | high"
}
```

## Storage requirements

- store in the authoritative local worker database table `system_observations`
- index by:
  - `competitor`
  - `region`
  - `signal_type`
  - `observed_at`

## Deduplication rule

- same competitor
- same signal type
- similar summary
- recent time window

If all of the above are true, merge or ignore the newer duplicate instead of storing repeated noise.

## Update rule

- newer signals override older conflicting signals in downstream interpretation
- the worker should prefer the latest high-confidence signal when generating visible actions

## Boundary rule

`SystemObservation v1` is internal memory for the competitive action engine. It must not be rendered directly in the public app.
