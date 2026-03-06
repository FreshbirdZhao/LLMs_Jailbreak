# Jailbreak Visualization Seaborn Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade jailbreak visualization to publication-ready aesthetics using seaborn while preserving current metrics pipeline and add Chinese documentation for all four figures' parameters, meaning, and formulas.

**Architecture:** Keep `stats.py` and record/group aggregation unchanged, and refactor plotting/CLI only. Introduce unified plotting style setup with seaborn + matplotlib fallback, add two new plot functions, and wire CLI to output four images consistently. Add tests for normal and empty inputs to prevent regressions.

**Tech Stack:** Python 3, pandas, matplotlib, seaborn (optional fallback), unittest

---

### Task 1: Add plotting tests for four output figures

**Files:**
- Create: `tests/test_jailbreak_plotting.py`

**Step 1: Write the failing test**
- Add test fixture dataframe with all required columns.
- Assert plotting entrypoint generates 4 files:
  - `success_rate.png`
  - `risk_distribution.png`
  - `uncertainty_overview.png`
  - `risk_heatmap.png`
- Assert all files exist and non-empty.
- Add empty-dataframe test asserting same 4 files are still generated.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_plotting.py -v`
- Expected: FAIL (missing APIs/files)

**Step 3: Write minimal implementation**
- Add plotting APIs and compatibility wrapper in `plotting.py`.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_plotting.py -v`
- Expected: PASS

### Task 2: Refactor plotting style and add two new charts

**Files:**
- Modify: `results_analyze/jailbreak_metrics/plotting.py`

**Step 1: Implement unified publication style**
- Add seaborn theme setup:
  - serif-focused academic font stack
  - colorblind-safe palette
  - consistent font sizes/line widths/grid style
  - deterministic figure export dpi
- Keep current placeholder PNG fallback behavior.

**Step 2: Upgrade existing two charts**
- Improve layout, sorting, annotation, and legibility for `success_rate` and `risk_distribution`.

**Step 3: Add two new charts**
- Add:
  - `plot_uncertainty_overview`
  - `plot_risk_heatmap`
- Ensure robust empty dataframe rendering.

**Step 4: Run tests**
- Run: `python -m unittest tests/test_jailbreak_plotting.py -v`
- Expected: PASS

### Task 3: Wire CLI to export all four figures

**Files:**
- Modify: `results_analyze/jailbreak_metrics/cli.py`

**Step 1: Write the failing CLI smoke test**
- Create: `tests/test_jailbreak_cli_smoke.py`
- Use temp directories and small JSONL fixture.
- Assert CLI exits 0 and output `figures/` contains all four png files.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_cli_smoke.py -v`
- Expected: FAIL (CLI currently writes only 2 figures)

**Step 3: Minimal CLI changes**
- Import and invoke new plotting functions.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_cli_smoke.py -v`
- Expected: PASS

### Task 4: Add Chinese parameter/formula documentation for four figures

**Files:**
- Create: `results_analyze/jailbreak_metrics/FIGURE_PARAMETERS_ZH.md`

**Step 1: Draft docs with exact field/formula mapping**
- For each figure, document:
  - required columns/parameters
  - parameter semantics
  - calculations tied to `stats.py`
- Include formula section for:
  - `success_rate`
  - `uncertain_rate`
  - `risk_i_ratio` (`i=0..4`)
  - `success_variance`
  - Wilson 95% CI (`ci95_low`, `ci95_high`)

**Step 2: Verify docs consistency against code**
- Cross-check every metric name and formula with `stats.py` and plotting usage.

### Task 5: End-to-end verification

**Files:**
- No code file required

**Step 1: Run targeted tests**
- `python -m unittest tests/test_jailbreak_plotting.py tests/test_jailbreak_cli_smoke.py -v`

**Step 2: Run CLI on sample dataset**
- `python -m results_analyze.jailbreak_metrics.cli --input-dir jailbreak_results --judge-mode keyword --output-dir /tmp/jb_vis_check --no-show-progress`

**Step 3: Confirm artifacts**
- Verify expected csv + 4 png files exist and are non-empty.
