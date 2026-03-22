# Agent.Chappie Vision

## Purpose

Agent.Chappie is a local-first governed agent system for macOS that turns a task request into explicit, inspectable control-plane artifacts and a bounded execution outcome.

## What "sovereign" means here

- primary execution stays local by default
- decision logic is explicit and inspectable
- outputs are structured and machine-validated
- trace artifacts are persisted for audit and replay
- human review remains available when confidence or policy requires it

## Current success target on this machine

On the M4 Mac mini 16GB / 256GB, success means:

- the control plane produces a `StructuredTaskObject`
- the control plane produces an `ExecutionPlan`
- the control plane produces a `DecisionRecord`
- the confidence router chooses `proceed`, `revise`, or `stop`
- each run writes immutable trace files to disk
- dry-run mode is reliable and repeatable
- live-run mode is validated separately when local transport is available

## What Agent.Chappie is not

- not a general autonomous swarm system
- not a live online fine-tuning system
- not a broad plugin platform
- not a UI-first product at this phase
- not yet a continuously running daemon or launchd-managed service

## Current status

- dry-run validated
- live-run not validated in this sandbox
- governed triad scaffold implemented
