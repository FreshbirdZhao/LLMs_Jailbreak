# Chapter 3 Figure Formula Table Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace placeholder figure tables and formula tables in chapter 3 with final TikZ figures and formal equations, and restyle the remaining statistics table to match chapter 2.

**Architecture:** Add six standalone TikZ source files under `figures/` so chapter 3 can include them with the same pattern already used in chapter 2. Update `pages/chapter3.tex` to replace placeholder tables with `figure` and `equation` environments while preserving the surrounding chapter narrative and original table content.

**Tech Stack:** LaTeX, TikZ/PGF, existing `whu-bachelor-style` class, chapter 2 table style (`booktabs`)

---

### Task 1: Add chapter 3 TikZ figure sources

**Files:**
- Create: `figures/fig3-1-threat-model.tex`
- Create: `figures/fig3-2-framework-overview.tex`
- Create: `figures/fig3-3-attack-dimensions-map.tex`
- Create: `figures/fig3-4-automated-redteam.tex`
- Create: `figures/fig3-5-multiturn-jailbreak.tex`
- Create: `figures/fig3-6-evaluation-pipeline.tex`

**Steps:**
1. Follow the visual language already used in `figures/fig2-2-safety-alignment-overview.tex`.
2. Keep each figure self-contained and sized for `\resizebox{0.98\textwidth}{!}{\input{...}}`.
3. Use concise Chinese labels that match the chapter wording.

### Task 2: Replace placeholder blocks in chapter 3

**Files:**
- Modify: `pages/chapter3.tex`

**Steps:**
1. Replace each placeholder figure table with a formal `figure` environment plus caption and label.
2. Replace the formula placeholder tables with formal numbered equations and explanatory text.
3. Keep the statistics table content unchanged while converting its formatting to the same compact three-line style used in chapter 2.

### Task 3: Verify LaTeX compilation

**Files:**
- Modify if needed after compile feedback: `pages/chapter3.tex`, `figures/fig3-*.tex`

**Steps:**
1. Run a project LaTeX build.
2. Fix any TikZ or float errors.
3. Re-run the build until it completes successfully.
