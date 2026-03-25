# Agent.Chappie Local-First OpenClaw Stack

This workspace implements the deliverables from your build spec:

- deterministic Python agent loop
- structured JSON output enforcement
- one minimal tool (`fetch_url`)
- one usable workflow (`fetch -> summarise -> structured insights`)
- local-first config examples for OpenClaw + Ollama

## What is already present on this machine

The host already has:

- `node v25.8.1`
- `npm 11.11.0`
- `python3 3.14.3`
- `openclaw 2026.3.13`
- `ollama` client `0.18.2`

OpenClaw is installed and running locally. Its current config already contains an `ollama` provider entry in `~/.openclaw/openclaw.json`.

## Workspace layout

- `src/agent_chappie/` core implementation
- `apps/consultant-followup-web/` thin public test app layer
- `tests/` unit tests
- `config/` config examples
- `scripts/` helper scripts

## Quick start

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run the deterministic dry-run workflow:

```bash
python scripts/run_workflow.py \
  --task "Fetch https://example.com and summarise it" \
  --url "https://example.com" \
  --dry-run
```

Run the thin public test app:

```bash
cd apps/consultant-followup-web
cp .env.example .env.local
npm install
npm run dev
```

Run the private worker bridge locally:

```bash
cp .env.example .env.local
source .venv/bin/activate
python scripts/worker_bridge.py
```

Run against a live Ollama instance:

```bash
python scripts/run_workflow.py \
  --task "Fetch https://example.com and summarise it" \
  --url "https://example.com"
```

## Phase mapping

### Phase 0

Host prep commands are documented in [`docs/setup.md`](/Users/chappie/Projects/Agent.Chappie/docs/setup.md).

### Phase 1

Ollama install and model pull commands are documented in [`docs/setup.md`](/Users/chappie/Projects/Agent.Chappie/docs/setup.md).

### Phase 2 and 3

OpenClaw verification plus local Ollama provider examples are in:

- [`config/openclaw.local.example.json`](/Users/chappie/Projects/Agent.Chappie/config/openclaw.local.example.json)
- [`docs/setup.md`](/Users/chappie/Projects/Agent.Chappie/docs/setup.md)

### Phase 8 — 3steps (in progress)

Production-credible learning and first-app delivery: [`docs/phase8_milestones_and_gates.md`](docs/phase8_milestones_and_gates.md), task feedback [`docs/09_contracts/feedback_v2.md`](docs/09_contracts/feedback_v2.md).

### Phase 4 to 7 (core scaffold and app)

Implemented in:

- [`src/agent_chappie/agent_loop.py`](/Users/chappie/Projects/Agent.Chappie/src/agent_chappie/agent_loop.py)
- [`src/agent_chappie/models.py`](/Users/chappie/Projects/Agent.Chappie/src/agent_chappie/models.py)
- [`src/agent_chappie/tools.py`](/Users/chappie/Projects/Agent.Chappie/src/agent_chappie/tools.py)
- [`src/agent_chappie/workflows.py`](/Users/chappie/Projects/Agent.Chappie/src/agent_chappie/workflows.py)

## Notes on local verification

This coding environment cannot open loopback network connections to `127.0.0.1`, so live Ollama/OpenClaw calls are blocked inside the sandbox even though the host has those services installed. The code includes a dry-run model stub and mocked tests so the project is still verifiable here.

The public test app intentionally defers auth in Phase 4 and uses demo-safe anonymous identifiers until a later auth phase is introduced.

Phase 5 adds a private worker bridge plus a continuous observation layer. The app remains thin, while the Mac mini worker ingests market signals, stores hidden system observations, and returns only ranked user-facing actions.

## Agent Work Rule
When you are done with a bucket of tasks, always provide a full plain text summary that can be easily copied and pasted for the Architect to review.

## Documentation-first policy

This repository is documentation-driven:

- implementation must follow repository docs (`architecture`, `contracts`, `runbooks`, `roadmap`, `handoffs`)
- do not assume undocumented behavior
- clarify ambiguity before acting on critical behavior changes
- keep code and docs synchronized in the same pass
