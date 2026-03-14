# Multi-Turn Runtime Reliability Design

**Date:** 2026-03-14

**Goal:** Restore legacy runtime reliability features to the new multi-turn jailbreak flow: resume by `(model_name, test_id)`, real-time JSONL writes with periodic fsync, and a single dynamic progress bar across all datasets.

## Scope

- Add `resume` support to the new `single_jail/` and `multi_jail/` entry points.
- Add periodic autosave (`flush + fsync`) on top of immediate line flushing.
- Add a single aggregate dynamic progress bar in multi-dataset mode.
- Keep the per-case multi-turn runner focused on case execution only.

## Resume Semantics

Resume uses the legacy rule:

- load the existing output JSONL
- extract `(model_name, test_id)` from each completed line
- skip any task whose pair is already present

It does not distinguish between:

- success
- blocked
- refused
- error

If the line exists in the output file, the task counts as completed for resume purposes.

## Progress Semantics

Use one aggregate progress bar across all datasets.

- total = all `(model, case)` tasks after dataset loading
- completed = skipped + newly finished tasks
- update once per skipped or finished case
- no model or case details in the bar

Display format:

```text
[12/80] ██████░░░░░░░░░░░░ 15.0% | success
```

Possible trailing statuses:

- `skipped`
- `success`
- `blocked`
- `refused`
- `error`

## Architecture

### `result_writer.py`

Extend the writer to support:

- loading completed `(model_name, test_id)` pairs from an existing JSONL
- immediate line flushing
- explicit `fsync`

### New runtime coordinator

Add a small runtime coordinator module under `multi_jail/` to own:

- task enumeration across datasets
- resume filtering
- progress bar rendering
- counters and final summary
- autosave background task

### Entry points

`single_jail.py`

- use the same coordinator logic for one dataset

`multi_jail.py`

- use the same coordinator logic for multiple datasets
- report one merged progress bar

## CLI Changes

Add back:

- `--resume`
- `--autosave-interval`
- `--concurrency`

The first version may still execute serially if concurrency wiring becomes unnecessary complexity, but the parser should expose the option for compatibility. Preferred implementation is to keep execution serial for now and only restore compatibility flags plus progress/reliability behavior.

## Risks

### Resume key collision across datasets

Because resume only keys on `(model_name, test_id)`, two datasets with the same `test_id` could collide if they share one output file. To avoid this, output remains dataset-scoped per file.

### Progress bar in non-interactive environments

If stdout is not a TTY, the implementation should fall back to stable line logging rather than carriage-return updates.

## Testing

- unit test writer loads completed pairs from JSONL
- unit test parser accepts `resume` and `autosave` flags
- unit test progress renderer emits expected compact format
- integration-style test that resume skips already written tasks
