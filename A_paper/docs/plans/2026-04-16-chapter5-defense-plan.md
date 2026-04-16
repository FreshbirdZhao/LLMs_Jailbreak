# Chapter 5 Defense Scheme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace chapter 5 placeholder figure tables and formula tables with final defense-architecture figures and formal equations, and convert all remaining placeholder tables into publication-ready three-line tables.

**Architecture:** Since chapter 5 is a design chapter rather than a finalized results chapter, all figure replacements should be architecture diagrams, control-flow diagrams, mapping diagrams, or evaluation-framework diagrams. Tables should keep abstracted, de-risked content and avoid operational harmful detail.

**Tech Stack:** LaTeX, TikZ/PGFPlots, existing thesis class, chapter 2 table style (`booktabs`)

---

### Task 1: Build chapter 5 figure sources

**Files:**
- Create: `figures/fig5-1-defense-problem.tex`
- Create: `figures/fig5-2-defense-architecture.tex`
- Create: `figures/fig5-3-risk-propagation.tex`
- Create: `figures/fig5-4-input-defense-flow.tex`
- Create: `figures/fig5-5-interaction-state-machine.tex`
- Create: `figures/fig5-6-output-defense-flow.tex`
- Create: `figures/fig5-7-attack-defense-map.tex`
- Create: `figures/fig5-8-evaluation-framework.tex`

**Steps:**
1. Reuse the visual language already used in chapters 2 to 4.
2. Keep labels concise and safety-preserving.
3. Prefer conceptual diagrams over fake quantitative charts.

### Task 2: Update chapter 5 body

**Files:**
- Modify: `pages/chapter5.tex`

**Steps:**
1. Replace placeholder figure tables with final `figure` environments.
2. Replace all formula placeholder tables with formal equations and short explanatory paragraphs.
3. Convert all placeholder tables to compact three-line tables.

### Task 3: Verify build

**Files:**
- Modify if needed after compile feedback: `pages/chapter5.tex`, `figures/fig5-*.tex`

**Steps:**
1. Run `make pdf`.
2. Fix compile or layout issues.
3. Re-run until the PDF builds successfully.
