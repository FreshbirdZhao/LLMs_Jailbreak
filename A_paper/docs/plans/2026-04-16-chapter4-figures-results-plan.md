# Chapter 4 Figures And Results Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace chapter 4 placeholder figure tables and formula tables with final result figures and equations, and convert remaining placeholder tables into publication-ready three-line tables with real values where available.

**Architecture:** Read real metrics from `Results/final/run_20260415_*`, encode the stable values directly into figure source files under `figures/`, and update `pages/chapter4.tex` to include those figures in the same pattern used by chapters 2 and 3. For sections without completed experiments, replace placeholders with method/readiness diagrams instead of fabricated result charts.

**Tech Stack:** LaTeX, TikZ/PGFPlots, existing thesis class, chapter 2 table style (`booktabs`)

---

### Task 1: Build chapter 4 figure sources

**Files:**
- Create: `figures/fig4-1-experiment-overview.tex`
- Create: `figures/fig4-2-overall-results-bars.tex`
- Create: `figures/fig4-3-success-heatmap.tex`
- Create: `figures/fig4-4-uncertainty-heatmap.tex`
- Create: `figures/fig4-5-semantic-attack-comparison.tex`
- Create: `figures/fig4-6-dap-fsh-comparison.tex`
- Create: `figures/fig4-7-surface-attack-comparison.tex`
- Create: `figures/fig4-8-success-uncertainty-scatter.tex`
- Create: `figures/fig4-9-risk-distribution.tex`
- Create: `figures/fig4-10-chain-induction-flow.tex`
- Create: `figures/fig4-11-vulnerability-layering.tex`
- Create: `figures/fig4-12-redteam-readiness.tex`
- Create: `figures/fig4-13-multiturn-readiness.tex`
- Create: `figures/fig4-14-findings-mechanism-map.tex`

**Steps:**
1. Use real values from `group_metrics.csv` for all result figures.
2. Keep visual style aligned with chapters 2 and 3.
3. Avoid raw harmful content in any case-oriented figure labels.

### Task 2: Update chapter 4 body

**Files:**
- Modify: `pages/chapter4.tex`

**Steps:**
1. Replace placeholder figure tables with final `figure` environments and captions.
2. Replace the formula placeholder table with a formal equation and short explanatory text.
3. Replace the summary table with real metrics.
4. Replace the case comparison table with abstracted, de-risked descriptions.

### Task 3: Verify build

**Files:**
- Modify if needed after compile feedback: `pages/chapter4.tex`, `figures/fig4-*.tex`

**Steps:**
1. Run `make pdf`.
2. Fix compile errors and serious layout issues.
3. Re-run until the PDF builds successfully.
