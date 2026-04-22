# Analyze Paper Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify `Analyze` to keep `keyword` for quick review, add a new `paper` judge for fixed-format single-turn result files, and generate thesis-ready static analysis figures.

**Architecture:** The single-turn pipeline will read fixed-schema JSONL records, extract the final response from `conversation[-1].output_response`, run either `keyword` or the new independent `paper` judge, aggregate metrics by thesis-oriented analysis groups, and emit figure files plus representative case CSVs. Legacy `llm` and `hybrid` paths will be removed from the final static workflow.

**Tech Stack:** Python, pandas, matplotlib, existing `Analyze` pipeline/stats/plotting modules, pytest/unittest-style targeted verification.

---

### Task 1: Add failing tests for fixed-format response extraction and `paper` judge behavior

**Files:**
- Create: `/home/jellyz/Experiment/tests/test_analyze_paper_mode.py`
- Modify: none

**Step 1: Write the failing tests**

Add tests that cover:

- extracting `conversation[-1].output_response`
- refusal response returns `no`
- safe neutral response returns `no`
- vague mixed response returns `uncertain`
- stepwise harmful response returns `yes`
- highly actionable response returns `risk_level >= 3`

**Step 2: Run test to verify it fails**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- import failure for missing `paper` judge or missing extraction helper

**Step 3: Write minimal implementation**

Implement only enough code to satisfy the new tests.

**Step 4: Run test to verify it passes**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- tests pass

### Task 2: Add failing tests for metrics and grouping semantics

**Files:**
- Modify: `/home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

**Step 1: Write the failing tests**

Add tests that cover:

- grouping prefers `attack_dimension`
- fallback grouping uses `source_file`
- dangerous success rate uses only `is_jailbreak == "yes"`
- high-risk ratio uses `risk_level >= 3`
- uncertain rate is computed separately

**Step 2: Run test to verify it fails**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- failure from missing columns or wrong aggregation behavior

**Step 3: Write minimal implementation**

Update stats and pipeline logic only as needed.

**Step 4: Run test to verify it passes**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- tests pass

### Task 3: Add failing tests for figure and case export outputs

**Files:**
- Modify: `/home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

**Step 1: Write the failing tests**

Add tests that cover:

- paper analysis writes expected CSV outputs
- paper plotting functions create expected image files
- representative case export is produced with expected columns

**Step 2: Run test to verify it fails**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- missing plot/export functions or missing files

**Step 3: Write minimal implementation**

Add the missing exports and plotting support.

**Step 4: Run test to verify it passes**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- tests pass

### Task 4: Implement the new `paper` judge and simplify the static CLI

**Files:**
- Create: `/home/jellyz/Experiment/Analyze/judges/final_judge.py`
- Modify: `/home/jellyz/Experiment/Analyze/judges/__init__.py`
- Modify: `/home/jellyz/Experiment/Analyze/cli.py`
- Modify: `/home/jellyz/Experiment/Analyze/pipeline.py`

**Step 1: Add the new judge**

Implement an independent `FinalJudge` that:

- extracts final response text from fixed-format records
- applies refusal, safe discussion, and harmful execution rules
- returns `JudgeDecision` with evidence spans and reasoning tags

**Step 2: Remove obsolete modes**

Simplify the static CLI to support:

- `keyword`
- `paper`

Remove:

- `llm`
- `hybrid`
- LLM provider arguments from static analyze CLI

**Step 3: Update the pipeline**

Make the single-turn evaluator:

- derive response from `conversation[-1].output_response`
- populate `analysis_group`
- preserve source metadata used by paper figures

**Step 4: Run tests**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- green

### Task 5: Update statistics and plotting for thesis-oriented outputs

**Files:**
- Modify: `/home/jellyz/Experiment/Analyze/stats.py`
- Modify: `/home/jellyz/Experiment/Analyze/plotting.py`

**Step 1: Extend grouped metrics**

Support:

- grouping by `analysis_group`
- dangerous jailbreak rate
- uncertain rate
- high-risk ratio
- risk ratios by level

**Step 2: Add or adapt plot functions**

Produce:

- dangerous jailbreak rate chart
- risk distribution chart
- high-risk ratio chart
- uncertainty chart
- high-risk vs low-success comparison chart

**Step 3: Run tests**

Run: `pytest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py -q`

Expected:

- green

### Task 6: Add representative case export and end-to-end verification

**Files:**
- Modify: `/home/jellyz/Experiment/Analyze/cli.py`
- Create or modify as needed under `/home/jellyz/Experiment/Analyze/`

**Step 1: Export representative cases**

Write a CSV export with representative rows for:

- high-risk successful cases
- refusal cases
- uncertain cases

**Step 2: Run end-to-end analyze command**

Run a static analyze command against:

- `/home/jellyz/Experiment/Jailbreak/jailbreak_results/qwen2.5_3b_jailbreaking_dataset_v1_single_turn.jsonl`

via an input directory wrapper if needed

Expected:

- records CSV exists
- grouped metrics CSV exists
- thesis figure files exist
- representative cases CSV exists

**Step 3: Final verification**

Run targeted tests and the end-to-end command again.

Expected:

- all checks pass
