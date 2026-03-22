# Agent.Chappie Constraints

## Governing constraints

- local-first by default
- deterministic structured outputs
- explicit schema validation
- auditable trace persistence
- minimal, reversible changes
- no premature broadening of scope

## Disallowed expansion at this phase

- no swarms
- no memory subsystem beyond repository docs and trace artifacts
- no online fine-tuning
- no broad plugin expansion
- no UI work unless required for an already working path
- no app implementation during the platform-boundary pass
- no scheduler implementation during the scheduler-foundation pass
- no app implementation during the MVP-contract pass
- no app, scheduler, or task-engine implementation during the contract-formalization pass
- no domain logic inside the core layer
- no app-specific orchestration inside the core layer
- no second domain during the MVP-contract pass
- no second user type during the MVP-contract pass
- no auth implementation is required during the first public test app pass

## Layering constraints

- the core must remain app-agnostic
- scheduler policy belongs to the scheduler layer, not app clients
- app clients communicate through contracts, not direct model control
- the first MVP must consume the core as a client, not reshape the core around app needs
- scheduler foundation work remains docs, contracts, and examples only until explicitly promoted to implementation
- MVP-contract work remains scope, examples, and contracts only until explicitly promoted to app implementation
- contract-formalization work remains schema, validation, and documentation only until explicitly promoted to implementation
- the public test app may use anonymous demo identifiers, but it must not pretend to be a secure multi-user product

## Execution discipline

- do not claim completion without command-level evidence
- distinguish clearly between dry-run validated and live-run validated
- keep documentation aligned with code
- prefer smallest production-relevant step

## Environment constraint

- this sandbox cannot reach local loopback model transport reliably
- live Ollama validation must be treated separately from dry-run validation
