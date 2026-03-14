# Multi-Turn Defense Integration Design

**Date:** 2026-03-14

**Goal:** Integrate the existing `Defense` engine into the new multi-turn jailbreak execution paths under `Jailbreak/jailbreak_tools/single_jail/` and `Jailbreak/jailbreak_tools/multi_jail/`.

## Scope

- Add real defense execution to the new multi-turn runners.
- Restore defense-related CLI options on the new entry points.
- Reconnect `Jelly_Z/bin/jailbreak` so defense selection is functional again.
- Reuse the existing `Defense.defense_mode` engine and modules rather than re-implementing policy logic.

## Recommended Approach

Use runner-driven defense integration.

`MultiTurnCaseRunner` becomes the orchestration point for:

- pre-call defense
- model invocation
- post-call defense
- per-round result assembly
- early stop on defense block/truncate

`MultiTurnModelTester` stays focused on model transport and config loading.

## Per-Round Execution Semantics

For each round:

1. Build a defense context from the current case, model, and round index.
2. Override `context.original_prompt` with the actual prompt being sent in that round.
3. Run `apply_pre_call_defense`.
4. If pre-call defense returns `BLOCK` or `TRUNCATE`, do not call the model.
5. Record the blocked/truncated round in `conversation`.
6. End the case with final status `blocked`.
7. If the model call is allowed, send `sanitized_prompt` when present, otherwise send the original prompt.
8. Run `apply_post_call_defense`.
9. Use `sanitized_response` when present as the visible response for judging and follow-up generation.
10. If the judged response is a success, stop.
11. Otherwise, generate the next prompt and continue.

This preserves the old single-call defense semantics while adapting them to a multi-turn loop.

## Output Model

### Case-Level Fields

Add:

- `defense_enabled`
- `defense_blocked`
- `defense_final_action`
- `defense_final_risk_level`
- `defense_final_reasons`
- `defense_trace`

### Round-Level Fields

Each `conversation` item should include:

- `defense_enabled`
- `defense_action`
- `defense_risk_level`
- `defense_reasons`
- `defense_trace`
- `defense_prompt`
- `raw_assistant_response`
- `assistant_response`

The visible `assistant_response` should prefer `sanitized_response`.

## CLI Changes

Re-add these options to the new Python entry points:

- `--enable-defense`
- `--defense-config`
- `--defense-archive-format`

Affected files:

- `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`

## Launcher Changes

`Jelly_Z/bin/jailbreak` should once again pass defense arguments to the new entry points when the user enables defense.

The menu wording remains unchanged.

## Risks

### Interaction layer may stop runs earlier than before

This is expected. The interaction module already uses `round_idx` and `max_round`.

### Follow-up generation after output sanitization

The recommended behavior is to base the next turn on the defense-visible response, not the raw response.

### JSONL growth

Per-round defense traces increase result size, but multi-turn runs are already bounded by `max_rounds`.

## Testing

- unit test blocked pre-call behavior
- unit test sanitized post-call response propagation
- unit test CLI parser accepts defense flags
- unit test launcher script passes defense flags again
- regression test existing multi-turn runner behavior without defense enabled
