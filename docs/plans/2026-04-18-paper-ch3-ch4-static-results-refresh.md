# Paper Chapter 3 And 4 Static Results Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refresh `A_paper` chapter 3 and chapter 4 so the static experiment design, figures, and narrative align with the latest `Results/final` data while keeping the redteam and multi-turn modules unchanged.

**Architecture:** Use the three latest static analysis runs under `Results/final` as the only quantitative basis, rewrite chapter 3 to describe the nine concrete attack dimensions and updated offline analysis口径, rewrite chapter 4 so attack-dimension effects become the main narrative, and replace old static-result figures with newly drawn TikZ/PGFPlots figures. Remove obsolete static-result figure files that are no longer referenced to avoid later misuse.

**Tech Stack:** LaTeX, TikZ/PGFPlots, thesis chapter sources under `A_paper/pages`, figure sources under `A_paper/figures`, CSV metrics from `Results/final`

---

### Task 1: Update chapter 3 design narrative and attack-dimension table

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter3.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig3-3-attack-dimensions-map.tex`

**Steps:**
1. Align the static dataset description with the nine concrete `analysis_group` dimensions used in the latest analysis results.
2. Replace placeholder sample counts and shares with real counts derived from the current static dataset.
3. Update the evaluation-pipeline description so it matches the current offline analysis口径 used in `Results/final`.

### Task 2: Rebuild chapter 4 static-result figures around attack-dimension effects

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-1-experiment-overview.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-2-overall-results-bars.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-3-success-heatmap.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-4-uncertainty-heatmap.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-8-success-uncertainty-scatter.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-9-risk-distribution.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-11-vulnerability-layering.tex`
- Modify: `/home/jellyz/Experiment/A_paper/figures/fig4-14-findings-mechanism-map.tex`
- Delete: `/home/jellyz/Experiment/A_paper/figures/fig4-5-semantic-attack-comparison.tex`
- Delete: `/home/jellyz/Experiment/A_paper/figures/fig4-6-dap-fsh-comparison.tex`
- Delete: `/home/jellyz/Experiment/A_paper/figures/fig4-7-surface-attack-comparison.tex`

**Steps:**
1. Encode the latest static results directly into refreshed figure sources.
2. Make figures emphasize attack-dimension layering and cross-model repeatability instead of model ranking.
3. Remove obsolete static comparison figures that no longer belong to the new chapter 4 structure.

### Task 3: Rewrite chapter 4 static analysis narrative

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter4.tex`

**Steps:**
1. Keep the redteam and multi-turn sections as deferred/unchanged modules.
2. Rewrite the static-result sections so the main claims are about attack dimensions, ambiguity structure, and defensive implications.
3. Use the three models only as repeatability evidence, not as the narrative subject.

### Task 4: Verify references and figure usage

**Files:**
- Modify as needed after review: `/home/jellyz/Experiment/A_paper/pages/chapter3.tex`
- Modify as needed after review: `/home/jellyz/Experiment/A_paper/pages/chapter4.tex`

**Steps:**
1. Remove references to deleted static-result figures.
2. Ensure every remaining figure file is still intentionally used.
3. Run a quick grep-based sanity check on chapter 3 and 4 figure references.
