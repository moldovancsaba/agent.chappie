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
| Flashcards (optional **Trinity**) | `agent_chappie.flashcard_trinity` — MLX **Trinity**: Gemma drafter → Granite writer → Qwen judge via **MLX-LM**; see [`docs/trinity_architecture.md`](trinity_architecture.md) | **Yes** — when **`FLASHCARD_MLX_TRINITY=1`** (legacy: `FLASHCARD_MLX_TRIAD`) and `mlx_lm` is installed |

### MLX Trinity (optional flashcard pipeline)

Layer:

- Apple Silicon inference for consultant-worker flashcards (`process_job_payload` in `worker_bridge.py`)

**Note:** **Trinity** names the **MLX flashcard** product (three MLX models). It is separate from the **governed triad** control-plane language used elsewhere in older docs.

Status:

- implemented behind **`FLASHCARD_MLX_TRINITY=1`** ( **`FLASHCARD_MLX_TRIAD=1`** still accepted)
- install **`requirements-mlx-flashcards.txt`** in addition to `requirements.txt` on the Mac worker
- logger name: **`agent_chappie.flashcard_trinity`**; set **`FLASHCARD_MLX_TRINITY_DEBUG=1`** or legacy **`FLASHCARD_MLX_DEBUG=1`** for DEBUG lines (drafter/writer/judge drop counts, retry accept/reject, threshold filtering)
- long-running workers call **`configure_worker_logging()`** from `agent_chappie.worker_logging` at startup (`serve()` in `worker_bridge.py`, `main()` in `scripts/worker_queue_consumer.py`)
- full low-level design, production commands, API flows, and **committed implementation plan (IMP-01, IMP-02, IMP-03, IMP-04, IMP-07):** **[`docs/trinity_architecture.md`](trinity_architecture.md)**
- portable Trinity narrative + Appendix A (same IMP IDs): **[`docs/trinity_flow.md`](trinity_flow.md)**
- deferred Trinity items (TR-R05, TR-R06, TR-R08, TR-R09): **[`docs/03_roadmap.md`](03_roadmap.md)** (*Trinity extended roadmap*)

**Checklist (nothing else is vendored in git):**

- Python: **`requirements.txt`** + **`requirements-mlx-flashcards.txt`** (`mlx`, `mlx-lm`, transitive `huggingface_hub`, etc.).
- Model weights: **not** in the repo; first `mlx_lm.load(...)` downloads to the Hugging Face cache, or prefetch with **`scripts/prefetch_mlx_flashcard_models.py`**.
- **Apple Silicon** + MLX-supported macOS for real inference (other platforms typically skip MLX at import or runtime).
- Optional **`HF_TOKEN`** for higher Hub rate limits when downloading.
- **Disk** for three small MLX repos (on the order of hundreds of MB combined for the default quantized IDs).

| Variable | Purpose | Default |
| --- | --- | --- |
| **`AGENT_WORKER_LOG_LEVEL`** | Root / `agent_chappie` log level for queue consumer and HTTP worker (`DEBUG`, `INFO`, …) | `INFO` |
| **`FLASHCARD_MLX_TRINITY`** | Enable Trinity MLX path for `intelligence_cards` / `card_scores` | off |
| **`FLASHCARD_MLX_TRIAD`** | Legacy alias for **`FLASHCARD_MLX_TRINITY`** | off |
| **`FLASHCARD_MLX_TRINITY_DEBUG`** | Verbose Trinity logs + tracebacks; sets **`agent_chappie.flashcard_trinity`** to **DEBUG** | off |
| **`FLASHCARD_MLX_DEBUG`** | Legacy alias for **`FLASHCARD_MLX_TRINITY_DEBUG`** | off |
| **`MLX_DRAFTER_MODEL`** | Hugging Face repo id for MLX drafter | `mlx-community/gemma-3-270m-it-4bit` |
| **`MLX_WRITER_MODEL`** | MLX writer (Granite 4 H 350M) | `mlx-community/granite-4.0-h-350m-8bit` |
| **`MLX_JUDGE_MODEL`** | MLX judge | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` |
| **`FLASHCARD_MLX_CONFIDENCE_THRESHOLD`** | Min product `d_conf * w_conf * j_conf` to keep a card | `0.5` |
| **`FLASHCARD_MLX_MAX_ATOMS`** | Cap on drafter JSON array length | `24` |
| **`FLASHCARD_MLX_INPUT_CHARS`** | Max characters fed into the drafter from summary + raw text + facts | `12000` |
| **`FLASHCARD_MLX_JUDGE_RETRY_THRESHOLD`** | While `j_conf` is below this, run extra writer→judge passes (bounded) | `0.35` |
| **`FLASHCARD_MLX_WRITER_RETRY_EXTRA`** | Max extra writer+judge rounds per atom after the batch judge | `2` |
| **`FLASHCARD_MLX_SEQUENTIAL_UNLOAD`** | Unload each MLX model after use to reduce unified-memory pressure | `1` |
| **`TRINITY_MAX_WALL_SECONDS`** | Max wall-clock seconds for Trinity (`run_trinity`); `0` = no limit (**IMP-07**) | `0` |
| **`TRINITY_SUBPROCESS`** | `1` + **`TRINITY_MAX_WALL_SECONDS` > 0** → run Trinity in a subprocess and **kill** on timeout | unset |
| **`AGENT_ALLOW_HEURISTIC_FLASHCARDS`** | When **`FLASHCARD_MLX_TRINITY=1`**, allow heuristic fallback if Trinity yields no promoted cards; **unset = strict** (job **blocked**, `trinity_strict_blocked`) | unset |

If Trinity is enabled but MLX is missing: with **strict** mode (default when Trinity on), the job **blocks** unless **`AGENT_ALLOW_HEURISTIC_FLASHCARDS=1`**. With that env set, the worker logs a **warning** and falls back to heuristics. Use **`FLASHCARD_MLX_TRINITY_DEBUG=1`** for stage-level DEBUG lines.

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
