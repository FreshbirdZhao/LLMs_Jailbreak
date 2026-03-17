# Multi-Turn Output Schema Optimization Design

**Problem**

The current multi-turn JSONL output mixes together two different concerns:

- user-facing run results
- internal debugging and analysis artifacts

This causes the final JSONL to become excessively large and repetitive because it includes full attack plans, plan version history, replan events, complete judge feedback objects, and duplicated per-round text that ordinary users do not need to inspect.

**Goal**

Keep the existing result file path and naming convention exactly as-is, but change the content so the user-visible JSONL contains only concise, readable run summaries. Preserve the full raw execution artifacts in a separate internal debug store under `Jailbreak/jailbreak_tools/multi_jail/`.

**Scope**

- Keep the final result file path and filename unchanged.
- Keep generating the full internal result record.
- Add a projection layer that writes a summarized version to the existing JSONL.
- Add an internal debug store directory under `Jailbreak/jailbreak_tools/multi_jail/debug_store/`.
- Write one full debug JSON per case into that directory.

**Non-Goals**

- Changing the execution logic in the runner beyond what is needed to support output projection.
- Changing CLI output paths or adding mandatory new CLI options.
- Removing the ability to inspect full planner, judge, and defense traces internally.

**User-Facing Output Design**

The final `*_multi_turn.jsonl` file remains in the current output directory and keeps the current filename pattern.

Each top-level record should retain only:

- `model_name`
- `test_id`
- `test_name`
- `category`
- `attack_type`
- `prompt`
- `final_status`
- `success_round`
- `rounds_used`
- `elapsed_time`
- `judge_model_name`
- `judge_final_reason`
- `judge_final_confidence`
- `planner_model_name`
- `timestamp`

The per-round data should be reduced to:

- `round`
- `input_prompt`
- `output_response`
- `judge_status`
- `judge_reason`
- `judge_confidence`
- `defense_action`
- `followup_prompt`

This preserves exactly what the user asked to see:

- original prompt
- each round's final input
- each round's target-model final output
- necessary judge state

**Fields Removed From User JSONL**

Remove these top-level fields from the user-facing file:

- `initial_attack_plan`
- `active_plan_versions`
- `replan_events`
- `response`
- `http_status`
- `max_rounds`
- `judge_mode`
- `defense_enabled`
- `defense_blocked`
- `defense_final_action`
- `defense_final_risk_level`
- `defense_final_reasons`

Remove these per-round fields from the user-facing file:

- `plan_round_idx`
- `plan_version`
- `plan_goal`
- `plan_strategy`
- `raw_assistant_response`
- `elapsed_time`
- `judge_stage`
- `judge_feedback`
- `judge_model_name`
- `defense_risk_level`
- `defense_reasons`
- `defense_prompt`
- `followup_strategy`
- `followup_generator_model`
- `followup_generation_error`

**Field Renames For User Readability**

For user-facing output:

- `user_prompt` becomes `input_prompt`
- `assistant_response` becomes `output_response`

No other semantic changes are needed for the summary projection.

**Internal Debug Store Design**

Create:

- `Jailbreak/jailbreak_tools/multi_jail/debug_store/`

Inside it, create one run-specific directory derived from the visible output target, for example using the output filename stem plus a timestamp or stable run identifier.

Each case writes one full JSON file named by:

- `test_id`
- `model_name`

Suggested shape:

- `debug_store/<run_id>/<test_id>__<model_name>.json`

The internal debug file should preserve the full record produced by the runner, including:

- `initial_attack_plan`
- `active_plan_versions`
- `replan_events`
- full `conversation`
- full `judge_feedback`
- `raw_assistant_response`
- full defense metadata

**Architecture**

Keep `runner.py` responsible for execution and full result generation.

Move output concerns into `result_writer.py`:

- build a full debug artifact writer
- build a user-facing summary projection function
- write the projected summary into the existing JSONL
- write the full record into the internal debug store

This cleanly separates:

- execution data model
- user presentation schema
- internal diagnostics

**Error Handling**

- If debug store write fails, the user-facing JSONL should still be written.
- If summary projection fails, surface the error instead of silently dropping the result.
- Sanitize model names when creating debug filenames to avoid invalid paths.

**Testing Strategy**

- Unit test summary projection preserves only the approved fields.
- Unit test the final JSONL path and naming remain unchanged.
- Unit test debug store path creation and full-record persistence.
- Integration test one multi-turn run writes:
  - a concise JSONL row
  - a full debug JSON sidecar

**Files Expected To Change**

- `Jailbreak/jailbreak_tools/multi_jail/result_writer.py`
- `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- `tests/test_multi_turn_cli.py`
- `tests/test_multi_turn_runner.py`
- new tests for writer/schema projection if needed
