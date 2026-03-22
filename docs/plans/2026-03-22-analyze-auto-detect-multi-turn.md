# Analyze Auto-Detect Multi-Turn Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `Jelly_Z/bin/analyze` automatically detect whether selected result files are multi-turn based on the `multi_turn.jsonl` suffix, route pure multi-turn selections to `Analyze.multi_turn.cli`, keep single-turn behavior unchanged, and reject mixed selections.

**Architecture:** The shell entrypoint remains the routing layer. After file selection, it classifies each selected file by filename suffix, validates whether the selection is homogeneous, and chooses the Python module plus output directory accordingly. Existing single-turn analysis flow and judge-mode prompts are preserved; only the backend module and final output path become conditional.

**Tech Stack:** Bash, Python module invocation, `unittest`

---

### Task 1: Add failing runner tests for routing behavior

**Files:**
- Modify: `tests/test_analyze_runner.py`
- Test: `tests/test_analyze_runner.py`

**Step 1: Write the failing tests**

Add tests that verify:

```python
def test_multi_turn_selection_calls_multi_turn_cli(self):
    ...

def test_mixed_single_and_multi_turn_selection_is_rejected(self):
    ...
```

The first should create a `*_multi_turn.jsonl` file, select it, and assert the fake Python shim records `Analyze.multi_turn.cli`. The second should create one single-turn file and one multi-turn file, select both, and assert the script exits non-zero with the mixed-selection error.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /home/jellyz/Experiment/tests/test_analyze_runner.py`
Expected: FAIL because `Jelly_Z/bin/analyze` still always calls `Analyze.cli` and does not reject mixed selections.

**Step 3: Write minimal implementation**

Update `Jelly_Z/bin/analyze` to:

```bash
if [[ "$filename" == *multi_turn.jsonl ]]; then
  selected_kind="multi_turn"
else
  selected_kind="single_turn"
fi
```

Then:
- reject mixed kinds
- choose `Analyze.cli` for single-turn
- choose `Analyze.multi_turn.cli` for multi-turn
- adjust `OUT_DIR` and final printed paths accordingly

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest /home/jellyz/Experiment/tests/test_analyze_runner.py`
Expected: PASS

**Step 5: Commit**

```bash
git add /home/jellyz/Experiment/tests/test_analyze_runner.py /home/jellyz/Experiment/Jelly_Z/bin/analyze /home/jellyz/Experiment/docs/plans/2026-03-22-analyze-auto-detect-multi-turn.md
git commit -m "feat: auto-detect multi-turn analyze inputs"
```

### Task 2: Verify no regression in analysis tests

**Files:**
- Test: `tests/test_analyze_pipeline.py`
- Test: `tests/test_analyze_multi_turn_pipeline.py`
- Test: `tests/test_analyze_multi_turn_cli.py`

**Step 1: Run focused regression tests**

Run:

```bash
python3 -m unittest \
  /home/jellyz/Experiment/tests/test_analyze_runner.py \
  /home/jellyz/Experiment/tests/test_analyze_pipeline.py \
  /home/jellyz/Experiment/tests/test_analyze_multi_turn_pipeline.py \
  /home/jellyz/Experiment/tests/test_analyze_multi_turn_cli.py \
  /home/jellyz/Experiment/tests/test_analyze_multi_turn_stats.py
```

Expected: PASS

**Step 2: Run syntax verification**

Run:

```bash
python3 -m py_compile \
  /home/jellyz/Experiment/Jelly_Z/bin/analyze \
  /home/jellyz/Experiment/tests/test_analyze_runner.py
```

Expected: `py_compile` should be skipped for the shell script and run only on Python files if needed; the intent is syntax sanity for touched Python tests.

**Step 3: Commit**

```bash
git add /home/jellyz/Experiment/Jelly_Z/bin/analyze /home/jellyz/Experiment/tests/test_analyze_runner.py
git commit -m "test: cover analyze routing for multi-turn inputs"
```
