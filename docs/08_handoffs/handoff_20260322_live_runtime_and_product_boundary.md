# Agent.Chappie handoff

## Phase

- Phase 2 host live-run validated
- Phase 2.5 runtime foundation implemented
- product boundary merged into docs only

## Verified host live-run

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/run_workflow.py --task "Fetch https://example.com and summarise it" --url "https://example.com" --trace-dir /Users/chappie/Projects/Agent.Chappie/traces
```

Result:

- `status=complete`
- full trace set written
- trace set: `/Users/chappie/Projects/Agent.Chappie/traces/20260322T060439Z_2213bb3c/`

## Runtime foundation

- launchd plist added
- heartbeat runtime loop added
- watchdog added with restart storm protection
- launchd service verified as running
- watchdog restart path exercised successfully

## Product direction

- Vercel public layer
- durable app/database/job layer
- Mac mini private worker
- one-domain, one-user-type, one-loop MVP
