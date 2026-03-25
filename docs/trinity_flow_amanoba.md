# Trinity Flow

> **Agent.Chappie canonical docs:** For file paths, environment variables, IMP/T-U IDs, SQLite tables, and test commands, treat **[`docs/trinity_architecture.md`](trinity_architecture.md)** and the portable narrative **[`docs/trinity_flow.md`](trinity_flow.md)** as the source of truth. This document is an alternate plain-language narrative; align numbered backlog items with those files when they differ.

## Abstract

Trinity is a three-role local AI workflow designed to turn rough source material into polished, reviewable output with clear quality gates. The three roles are:

- **Drafter**: breaks source into smaller parts and creates the first usable draft structure.
- **Writer**: rewrites, expands, and improves the draft into readable content.
- **Judge**: checks whether the result meets the required quality, structure, and language rules.

The core idea is simple: do not ask one model to do everything. Instead, divide the work into three specialized steps so each step can focus on one job. This improves traceability, makes failures easier to diagnose, and allows partial progress to be saved even when the final result still needs work.

This document describes the workflow in plain English while keeping the technical details visible enough to support scientific evaluation.

## 1. Problem Statement

Single-pass generation often fails in predictable ways:

- The output is too short.
- The output is structurally weak.
- The output mixes languages.
- The output is technically valid but not actually useful.
- The model can produce fluent text that still misses the real task.

Trinity addresses this by separating generation into three distinct responsibilities:

1. **Decompose**
2. **Enrich**
3. **Judge**

That separation makes the system more robust than a one-shot prompt because each step can be specialized and independently checked.

## 2. Core Roles

### 2.1 Drafter

The Drafter is the first stage.

Purpose:

- split the source into atomic ideas
- identify the shape of the content
- create the initial structure
- preserve the original intent without over-editing too early

Technical role:

- usually the smallest or fastest available model
- optimized for decomposition, extraction, and rough outlining
- should not be responsible for final quality

The Drafter should answer:

- What is this source trying to say?
- What are the main units of meaning?
- What should the Writer preserve?

### 2.2 Writer

The Writer is the enrichment stage.

Purpose:

- expand the draft into readable, polished output
- improve clarity, flow, and usefulness
- keep the target language pure
- preserve the intended structure

Technical role:

- the main production model for content generation
- should be strong enough to write natural text
- should follow formatting rules and domain-specific constraints

The Writer should answer:

- How do we turn the draft into something useful?
- How do we preserve correctness while improving quality?
- How do we keep the output in the correct language and format?

### 2.3 Judge

The Judge is the final quality gate.

Purpose:

- check structure, language, and consistency
- decide whether the draft is acceptable
- decide whether the draft should be revised again

Technical role:

- can be a model, a validator, or a hybrid rule engine
- in strict systems, the Judge should be able to reject weak output
- the Judge should not silently accept low-quality content

The Judge should answer:

- Is the output structurally valid?
- Is the output in the correct language?
- Is the output useful enough to keep?
- Should we accept, repair, or fail?

## 3. Recommended Local Model Stack

The current Trinity concept can run locally on Apple Silicon using MLX-based models. A practical stack for a memory-constrained machine is:

- **Drafter**: Gemma 3 270M
- **Writer**: Granite 4.0 350M (H-variant)
- **Judge**: Qwen 2.5 0.5B

This stack is intentionally small enough to run locally while still separating responsibilities.

Why this matters:

- The Drafter can stay lightweight.
- The Writer can focus on content quality.
- The Judge can focus on reasoning and validation.

The system can also use fallback runtimes when needed, but the role mapping should stay explicit so the user can see which model is supposed to do what.

## 4. Runtime Technology

### 4.1 MLX-LM

MLX-LM is the primary local execution technology for Apple Silicon.

Why it is useful:

- optimized for unified memory
- works well on Mac hardware
- supports local model execution without cloud dependency

### 4.2 Fallback Runtimes

Fallback runtime support is useful for resilience, but it should not hide the actual role model state.

Principle:

- if the requested model is installed, the role should show as available
- if the requested model is missing, the role should show as missing
- fallback runtime availability should be shown separately

This prevents the UI from claiming that a role is ready when it is only using a backup provider.

### 4.3 Health Checks

Each role should have health checks that answer different questions:

- Is the model installed?
- Is the runtime process alive?
- Is the model responsive?
- Is the worker making progress?

Health checks should be honest. They should distinguish:

- installed
- available
- degraded
- missing
- stalled

## 5. Workflow

### 5.1 Input

The workflow starts with source material:

- a topic
- a course language
- a lesson
- a quiz goal
- optional human feedback

### 5.2 Drafter Stage

The Drafter creates the first structured interpretation of the source.

Outputs may include:

- outline
- atomic facts
- draft section structure
- rough intent map

If the Drafter fails, the system should still preserve partial work when possible.

### 5.3 Writer Stage

The Writer turns the draft into better content.

Expected improvements:

- longer and clearer text
- stronger structure
- fewer language mistakes
- better alignment with the canonical format

The Writer should not invent a different task. It should improve the existing one.

### 5.4 Judge Stage

The Judge evaluates the result.

The Judge should reject content that:

- is too short
- mixes languages
- breaks the canonical structure
- contains obvious placeholder text
- looks polished but does not actually solve the task

The Judge can still allow partial progress to be saved if the output is better than before but not yet good enough for completion.

### 5.5 Acceptance

Acceptance does not mean final success.

A draft can be:

- improved and saved
- then still rejected
- then reworked again later

This is important because the system should preserve progress while still holding the quality line.

## 6. Failure Handling

Trinity should assume that local AI systems can fail in several ways:

- model not installed
- runtime unavailable
- process frozen
- health probe timeout
- output invalid
- output too short
- output in the wrong language
- output structurally incomplete

The recovery model should be:

1. detect the failure
2. save any usable partial improvement
3. retry if appropriate
4. fall back only when the primary role is unavailable
5. keep the system observable

## 7. Watchdog and Supervision

A Trinity system should not rely on manual babysitting.

It needs supervision:

- restart on crash
- stall detection
- heartbeat monitoring
- backlog monitoring
- child process cleanup

The watcher should not pretend everything is healthy if the worker is actually frozen.

Good supervision means:

- if the worker is idle but backlog exists, detect that
- if the writer model is frozen, kill and restart it
- if a role is missing, mark it missing
- if the system falls back, expose that fact clearly

## 8. Canonical Quality Principles

Trinity is only useful if the content rules are clear.

Core quality principles:

- preserve the target language
- follow canonical structure
- keep the output specific
- avoid filler
- avoid template leakage
- save partial progress
- never hide fallback state

## 9. Scientific Hypothesis

The Trinity model proposes that content quality improves when generation is split into three distinct cognitive roles:

- **Drafter** reduces ambiguity.
- **Writer** increases quality and readability.
- **Judge** increases correctness and consistency.

Hypothesis:

> A three-stage local AI workflow produces more reliable content than a single-stage generation workflow because it separates decomposition, enrichment, and validation into independent steps.

This hypothesis is testable.

Possible evaluation dimensions:

- structural validity
- language purity
- factual consistency
- revision quality
- time to recovery after failure
- percentage of partial progress preserved

## 10. Engineering Implications

Trinity implies a few practical design rules:

- Roles must be visible in the UI.
- Installed-vs-fallback state must be explicit.
- Progress must be persisted incrementally.
- Supervisors must detect stalls, not just crashes.
- Quality gates must reject weak output, even if the text looks fluent.

## 11. What Trinity Can Do

The current Trinity workflow can:

- decompose a topic into smaller content units
- draft and rewrite content locally
- judge quality against structural and language rules
- save partial progress
- restart after failures
- run continuously in the background
- use local models instead of cloud APIs

## 12. Ideabank

Future Trinity capabilities that could be added:

- **Stage-specific scoring**
  - separate confidence, impact, and trust scores for each role

- **Role-specialized prompts**
  - different prompt contracts for lessons, quizzes, summaries, and research

- **Auto-repair loops**
  - if Judge rejects, send only the weak sections back to Writer

- **Role competition**
  - multiple candidate drafts per stage, with the Judge selecting the best one

- **Traceable provenance**
  - store exactly which role changed which field and why

- **Language purity enforcement**
  - stronger rules for mixed-language detection and repair

- **Canonical format compiler**
  - convert role outputs into a strict lesson/quiz schema before write-back

- **Model benchmarking**
  - compare Gemma/Granite/Qwen against other local or remote models

- **Fallback transparency**
  - always show when the system is using a backup provider

- **Self-healing infrastructure**
  - detect and recover from frozen processes, stalled queues, and broken launch agents automatically

## 13. Conclusion

Trinity is a practical local AI architecture for quality-first content generation. Its main idea is not speed. Its main idea is controlled responsibility:

- one role decomposes
- one role writes
- one role judges

That structure makes the system easier to observe, easier to repair, and easier to improve scientifically.

The strongest claim Trinity can make is not that it is perfect. The stronger claim is that it is measurable, modular, and able to preserve quality work even when final acceptance still fails.

