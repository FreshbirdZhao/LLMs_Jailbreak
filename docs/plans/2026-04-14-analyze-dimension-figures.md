# Analyze Dimension Figures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `Analyze` to keep existing overview figures and additionally generate thesis-oriented attack-dimension figures for chapter 4.

**Architecture:** Reuse the existing `group_metrics.csv` aggregation keyed by `analysis_group == attack_dimension`, then add four dedicated plotting functions in `Analyze.plotting` and call them from the paper-mode CLI. Keep output under the existing `figures/` directory so the current analyze workflow and shell wrapper remain unchanged.

**Tech Stack:** Python, pandas, matplotlib, existing `Analyze` plotting/statistics modules, unittest.

---

### Task 1: Add failing tests for new dimension figure outputs

**Files:**
- Modify: `/home/jellyz/Experiment/tests/test_analyze_paper_mode.py`
- Test: `/home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

**Step 1: Write the failing test**

Add a test that builds a minimal grouped dataframe and asserts these files are created:
- `dimension_success_ranking.png`
- `dimension_risk_heatmap.png`
- `dimension_profile_panel.png`
- `dimension_priority_quadrants.png`

**Step 2: Run test to verify it fails**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

Expected: import or attribute failure because the new plotting functions do not exist yet.

**Step 3: Write minimal implementation**

Add the missing plotting functions and export them from the CLI only as needed to satisfy the test.

**Step 4: Run test to verify it passes**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

Expected: test passes.

### Task 2: Implement the four thesis-oriented dimension plots

**Files:**
- Modify: `/home/jellyz/Experiment/Analyze/plotting.py`

**Step 1: Add dimension sorting and label helpers**

Reuse existing plotting infrastructure and add only light helpers for:
- stable dimension ordering
- consistent title/axis wording for attack dimensions

**Step 2: Implement `dimension_success_ranking`**

Use horizontal bars with:
- `success_rate`
- Wilson CI
- `yes_count/total` annotation

**Step 3: Implement `dimension_risk_heatmap`**

Use a 9x5 heatmap over `risk_0_ratio` to `risk_4_ratio`.

**Step 4: Implement `dimension_profile_panel`**

Use grouped bars for:
- `success_rate`
- `high_risk_ratio`
- `uncertain_rate`

**Step 5: Implement `dimension_priority_quadrants`**

Use a scatter plot with:
- x: `success_rate`
- y: `high_risk_ratio`
- size: `total`

**Step 6: Run targeted tests**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

Expected: green.

### Task 3: Wire the new dimension figures into paper-mode analysis output

**Files:**
- Modify: `/home/jellyz/Experiment/Analyze/cli.py`

**Step 1: Import the new plotting functions**

Keep existing imports and add the four dimension plotters.

**Step 2: Generate the new figures**

After the current overview figures are written, also generate:
- `dimension_success_ranking.png`
- `dimension_risk_heatmap.png`
- `dimension_profile_panel.png`
- `dimension_priority_quadrants.png`

**Step 3: Run CLI-targeted verification**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`

Expected: green.

### Task 4: Run end-to-end verification on enriched real results

**Files:**
- Modify: none

**Step 1: Run the paper analyze CLI on the enriched JSONL**

Run:
`python -m Analyze.cli --input-dir /home/jellyz/Experiment/Jailbreak/jailbreak_results/qwen2.5_3b_jailbreaking_dataset_v1_single_turn_enriched.jsonl --output-dir /home/jellyz/Experiment/Results --output-run-subdir run_20260414_dimension_refresh --judge-mode paper --no-show-progress --no-resume`

Expected:
- `group_metrics.csv` exists
- all old figures still exist
- four new dimension figures exist

**Step 2: Run full tests**

Run: `python -m unittest discover -s /home/jellyz/Experiment/tests -p 'test_*.py'`

Expected: all pass.
