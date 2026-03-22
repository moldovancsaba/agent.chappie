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

### SQLite

Layer:

- structured runtime persistence

Status:

- planned, not implemented

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
