# Runbook: Debug live-run

## Symptom

Live-run fails before `StructuredTaskObject` generation.

## Current failing command

```bash
python3 /Users/chappie/Projects/Agent.Chappie/scripts/run_workflow.py --task "Fetch https://example.com and summarise it" --url "https://example.com" --trace-dir /Users/chappie/Projects/Agent.Chappie/traces
```

## Current failure

`Failed to reach Ollama at http://127.0.0.1:11434/api/generate: <urlopen error [Errno 1] Operation not permitted>`

## Checks

1. confirm Ollama is running on the host
2. run the live command outside the sandboxed environment
3. inspect `traces/<run_id>/` for placeholder artifacts and the error outcome

## Current scope boundary

- do not change architecture to work around sandbox transport limits
- validate live-run on the host environment instead
