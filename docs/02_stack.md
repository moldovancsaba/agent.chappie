# Agent.Chappie Stack

## Current stack

### Python 3.14.3

Layer:

- application runtime

Why it exists:

- runs orchestration, validation, routing, and trace persistence

### Agent.Chappie codebase

Layer:

- application and control plane

Why it exists:

- implements the governed local scaffold

### Ollama

Layer:

- local model runtime

Why it exists:

- provides local model inference for live-run mode

Status:

- configured in code
- host live-run validated with `llama3:latest`
- sandbox live-run still restricted

### launchd runtime foundation

Layer:

- service supervision

Why it exists:

- provides a path to continuous local execution on the Mac mini

Status:

- runtime plist implemented with `KeepAlive=true`
- watchdog plist implemented with `StartInterval=30`
- both services evidenced under launchd in this repository handoff

### watchdog runtime foundation

Layer:

- crash and freeze recovery

Why it exists:

- detects stale heartbeat state and enforces bounded restart behavior

Status:

- watchdog script implemented
- persistent watchdog launchd job implemented
- healthy/stale checks validated on host
- restart behavior exercised successfully against the launchd service in this handoff

### OpenClaw

Layer:

- adjacent orchestrator environment

Why it exists:

- present on host and relevant to the broader local stack

Status:

- installed on the host
- not currently wired into the Agent.Chappie control plane

## Planned stack

### SQLite (worker brain)

Layer:

- structured persistence for internal intelligence on the Mac mini worker (`AGENT_LOCAL_DB_PATH`, default under `runtime_status/`)

Status:

- in use for the private worker / 3steps app path (observations, sources, task feedback, generation memory, etc.)

### LLM usage: “drafter / writer / judge” vs consultant worker

These names mean **different things** in different entrypoints. This section is factual from the code.

**A) Governed orchestrator flow** (`src/agent_chappie/orchestrator.py` → `OllamaModelAdapter` in `src/agent_chappie/models.py`)

| Role | What calls it | Tool / runtime | Model selection |
| --- | --- | --- | --- |
| **Drafter** | `model_adapter.draft()` | **Ollama** HTTP `POST` to `OLLAMA_URL` (default `http://127.0.0.1:11434/api/generate`) | Env **`DRAFTER_MODEL`**, else **`AGENT_MODEL`** on `OllamaClient` (default `llama3:latest`) |
| **Writer** | `model_adapter.write()` | Same **Ollama** endpoint | Env **`WRITER_MODEL`**, else same fallback as client default |
| **Judge** | `model_adapter.judge()` | Same **Ollama** endpoint | Env **`JUDGE_MODEL`**, else same fallback as client default |

The client sends JSON `{ "model", "prompt", "stream": false }` and reads the `response` string (expected JSON for the next validation step).

**B) Consultant follow-up / queue worker** (`process_job_payload` in `src/agent_chappie/worker_bridge.py`)

This path does **not** call `OllamaModelAdapter.draft/write/judge`.

| Concept | Implementation | LLM? |
| --- | --- | --- |
| “Draft” knowledge segments | `build_draft_segments` — merges cards, chips, units, clauses | **No** — Python only |
| Observations from source text | `extract_observations` in `observation_engine.py` — keyword / rule tables | **No** |
| “Writer” tasks for checklist | `segment_to_task`, `write_tasks_from_segments`, `generate_learning_checklist` — templates and rules | **No** |
| “Judge” / ranking | `judge_tasks` — filters, `task_priority_score`, diversity selection | **No** — not `ModelAdapter.judge` |
| Flashcard scores | `score_flashcards` — numeric heuristics | **No** |

### MLX

Layer:

- future Apple Silicon runtime option

Status:

- planned, not implemented

### llama.cpp

Layer:

- future model runtime option

Status:

- planned, not implemented

### Open WebUI

Layer:

- optional interface layer

Status:

- planned, not implemented

## Product stack direction

### Vercel

Layer:

- public product surface

Status:

- planned, not implemented

### durable database / job layer

Layer:

- app state and job exchange

Status:

- planned, not implemented
