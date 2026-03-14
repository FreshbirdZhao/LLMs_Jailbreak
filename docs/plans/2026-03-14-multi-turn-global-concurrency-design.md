# Multi-Turn Global Concurrency Design

**Date:** 2026-03-14

**Goal:** Restore real global concurrency to the new multi-turn jailbreak execution path so `--concurrency` once again controls the number of `(model, case)` tasks running at the same time across all datasets.

## Scope

- Make `--concurrency` functional rather than parser-only.
- Apply one global concurrency pool across all datasets.
- Preserve current resume, autosave, defense, per-dataset output, and aggregate progress semantics.

## Recommended Approach

Use a shared async work queue in the entry-point coordination layer.

Each queued item is:

- target dataset
- output writer for that dataset
- model
- case

Workers call the existing `MultiTurnCaseRunner` for one item at a time.

This keeps:

- runner focused on single-case execution
- concurrency policy in the runtime orchestration layer
- resume and progress semantics easy to reason about

## Execution Semantics

1. Load all datasets.
2. Enumerate all `(dataset, model, case)` tasks.
3. For resume-enabled runs:
   - check the destination writer's existing completed pairs
   - mark matching tasks as skipped before queueing
4. Push remaining tasks into a single async queue.
5. Launch `--concurrency` workers.
6. Each worker:
   - runs the case
   - writes result to the correct writer
   - updates shared counters
   - refreshes the aggregate progress bar

## Synchronization

### Writer locking

Each output writer should have an async lock to serialize writes and fsync.

### Progress locking

Progress rendering should use one shared async lock so terminal output remains coherent.

### Shared counters

Counters and progress state should be updated under the same progress lock or a small dedicated state lock.

## Risks

### Cross-dataset output races

Safe if each writer is locked independently.

### Progress bar flicker

Safe if rendering is serialized.

### Autosave racing with normal writes

Safe if autosave also uses the writer lock.

## Testing

- unit test runtime queue processing with concurrency > 1
- unit test skipped tasks are not queued
- unit test writes remain complete under parallel execution
- regression test parser and runner behavior stay unchanged
