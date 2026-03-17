# Analyze Multi-Turn Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep `Analyze` focused on single-turn jailbreak analysis and add a separate `Analyze/multi_turn/` package for multi-turn result analysis.

**Architecture:** Revert the main `Analyze.pipeline` behavior to only consume top-level `response` fields. Add a dedicated `Analyze/multi_turn` package with its own record normalization and CLI, while reusing the existing judges, stats, and plotting modules where possible.

**Tech Stack:** Python, unittest, pandas

---

### Task 1: Restore single-turn behavior in the main Analyze pipeline

**Files:**
- Modify: `Analyze/pipeline.py`
- Modify: `tests/test_analyze_pipeline.py`

**Step 1: Write the failing test**

Adjust tests so the main pipeline is expected to only preserve top-level `response` data and not infer multi-turn responses from `conversation`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_analyze_pipeline -v`
Expected: FAIL because the current main pipeline still extracts multi-turn responses

**Step 3: Write minimal implementation**

Remove the multi-turn extraction helper from `Analyze/pipeline.py` and restore direct top-level `response` reads.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_analyze_pipeline -v`
Expected: PASS

### Task 2: Add a dedicated multi-turn analysis pipeline

**Files:**
- Create: `Analyze/multi_turn/__init__.py`
- Create: `Analyze/multi_turn/pipeline.py`
- Create: `Analyze/multi_turn/cli.py`
- Create: `tests/test_analyze_multi_turn_pipeline.py`

**Step 1: Write the failing test**

Add tests that assert the multi-turn pipeline:
- uses `success_round` when present
- falls back to the last round otherwise
- preserves core metadata fields

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_analyze_multi_turn_pipeline -v`
Expected: FAIL because the package does not exist yet

**Step 3: Write minimal implementation**

Create a multi-turn pipeline that normalizes each record to a final assistant response and feeds that response through the existing judge and stats flow.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_analyze_multi_turn_pipeline -v`
Expected: PASS

### Task 3: Verify focused regression coverage

**Files:**
- Modify: `Analyze/pipeline.py`
- Modify: `Analyze/multi_turn/pipeline.py`
- Test: `tests/test_analyze_pipeline.py`
- Test: `tests/test_analyze_multi_turn_pipeline.py`

**Step 1: Run focused tests**

Run: `python3 -m unittest tests.test_analyze_pipeline tests.test_analyze_multi_turn_pipeline -v`
Expected: PASS

**Step 2: Commit**

```bash
git add docs/plans/2026-03-17-analyze-multi-turn-split.md Analyze/pipeline.py Analyze/multi_turn tests/test_analyze_pipeline.py tests/test_analyze_multi_turn_pipeline.py
git commit -m "refactor: split multi-turn analyze flow"
```
