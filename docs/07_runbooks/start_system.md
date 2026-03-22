# Runbook: Start Agent.Chappie

## Dry-run

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/run_workflow.py --task "Fetch https://example.com and summarise it" --url "https://example.com" --dry-run --trace-dir /Users/chappie/Projects/Agent.Chappie/traces
```

Expected result:

- run completes
- triad artifacts are returned
- trace files are written to `traces/<run_id>/`

## Live-run

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/run_workflow.py --task "Fetch https://example.com and summarise it" --url "https://example.com" --trace-dir /Users/chappie/Projects/Agent.Chappie/traces
```

Current expected result in this sandbox:

- request trace is written
- placeholder triad artifacts may be written
- outcome is `error` because Ollama transport is blocked

## Host live-run with validated model

```bash
AGENT_MODEL=llama3:latest python3 /Users/chappie/Projects/Agent.Chappie/scripts/run_workflow.py --task "Fetch https://example.com and summarise it" --url "https://example.com" --trace-dir /Users/chappie/Projects/Agent.Chappie/traces
```

Expected result on host:

- triad artifacts are produced
- outcome status is `complete`
- trace files are written for all five artifacts
