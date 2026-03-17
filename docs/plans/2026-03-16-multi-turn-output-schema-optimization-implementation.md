# Multi-Turn Output Schema Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the existing multi-turn result file path and filename unchanged while changing its contents to a concise user-facing schema and moving full execution artifacts into an internal debug store.

**Architecture:** Leave `runner.py` producing the full internal record. Move presentation concerns into `result_writer.py` by adding a summary projection layer for the user JSONL and a debug sidecar writer under `Jailbreak/jailbreak_tools/multi_jail/debug_store/`. Wire the writer setup through `multi_jail.py` without changing the public output path.

**Tech Stack:** Python 3.12, `unittest`, JSONL file I/O, existing multi-turn jailbreak runtime

---

### Task 1: Lock the summary schema with failing tests

**Files:**
- Modify: `tests/test_multi_turn_runner.py`
- Modify: `tests/test_multi_turn_cli.py`
- Reference: `Jailbreak/jailbreak_tools/multi_jail/runner.py`

**Step 1: Write the failing test**

Add coverage that asserts the user-visible record keeps only:

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
- `conversation`

And per round only:

- `round`
- `input_prompt`
- `output_response`
- `judge_status`
- `judge_reason`
- `judge_confidence`
- `defense_action`
- `followup_prompt`

**Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py
```

Expected: FAIL because the result schema still exposes full planner and debug artifacts.

**Step 3: Write minimal implementation**

Do not change runner execution logic yet. Only prepare the tests that define the target summary contract.

**Step 4: Re-run the targeted tests**

Run the same command again after verifying the tests are correct.
Expected: still FAIL for the same schema reasons.

**Step 5: Commit**

```bash
git add /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py
git commit -m "test: lock concise multi-turn result schema"
```

### Task 2: Add summary projection and debug sidecar writing

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/result_writer.py`
- Test: `tests/test_multi_turn_result_writer.py`

**Step 1: Write the failing test**

Create tests that cover:

- `summarize_result(record)` strips `initial_attack_plan`, `active_plan_versions`, `replan_events`, and per-round raw/debug fields
- `user_prompt` is renamed to `input_prompt`
- `assistant_response` is renamed to `output_response`
- a full debug JSON file is written under `Jailbreak/jailbreak_tools/multi_jail/debug_store/`
- the visible JSONL path passed into the writer remains unchanged

**Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py
```

Expected: FAIL because there is no summary projector or debug sidecar writer.

**Step 3: Write minimal implementation**

In `result_writer.py`:

- add a summary projection helper
- add a debug-store path builder
- write the summary to the existing JSONL
- write the full record to `Jailbreak/jailbreak_tools/multi_jail/debug_store/<run_id>/<test_id>__<model_name>.json`

**Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py
git commit -m "feat: write concise multi-turn results with debug sidecars"
```

### Task 3: Wire the writer through the multi-turn entrypoint

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `tests/test_multi_turn_cli.py`

**Step 1: Write the failing test**

Add or extend a test that asserts:

- the output JSONL file path and name remain unchanged
- the writer receives enough context to derive a stable debug run directory
- no new required CLI arguments are introduced

**Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py
```

Expected: FAIL because the writer is not yet configured for dual output.

**Step 3: Write minimal implementation**

In `multi_jail.py`:

- keep `_build_output_path()` unchanged
- construct the writer so it knows both:
  - the visible JSONL path
  - the internal debug store root

**Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py
git commit -m "feat: wire multi-turn debug sidecar output"
```

### Task 4: Verify end-to-end summary output and internal debug persistence

**Files:**
- Modify: `tests/test_multi_turn_runner.py`
- Modify: `tests/test_multi_turn_result_writer.py`

**Step 1: Write the failing integration test**

Cover:

- one run produces a concise JSONL entry
- the same run produces a full debug JSON sidecar
- the summary record does not expose planner/debug-only fields
- the debug record still contains `initial_attack_plan`, `active_plan_versions`, `replan_events`, and full `conversation`

**Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py
```

Expected: FAIL until the full path from runner output to writer persistence is covered.

**Step 3: Write minimal implementation**

Only patch code if the integration test reveals missing glue. Prefer the smallest fix in `result_writer.py` or `multi_jail.py`.

**Step 4: Run test to verify it passes**

Run the same command again.
Expected: PASS.

**Step 5: Commit**

```bash
git add /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/result_writer.py /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py
git commit -m "test: verify concise multi-turn output and debug archive"
```

### Task 5: Run focused verification before claiming completion

**Files:**
- No intended code changes unless verification exposes defects

**Step 1: Run the focused suite**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py
```

Expected: PASS.

**Step 2: Run the broader multi-turn regression set**

Run:

```bash
python -m unittest /home/jellyz/Experiment/tests/test_adaptive_multi_turn_strategy.py /home/jellyz/Experiment/tests/test_multi_turn_judgers.py /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_jailbreak_launcher.py
```

Expected: PASS.

**Step 3: Inspect one generated summary/debug pair manually**

Confirm:

- the visible JSONL is concise
- the debug sidecar preserves the full record
- the visible JSONL path and filename are unchanged

**Step 4: Fix only defects revealed by verification**

Apply the smallest necessary patch and re-run the failing command.

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify concise multi-turn result output flow"
```
