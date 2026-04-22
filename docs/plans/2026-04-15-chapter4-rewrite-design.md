# Chapter 4 Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `A_paper/4.tex` into a complete experimental analysis chapter centered on common safety-alignment vulnerabilities across three evaluated models, while explicitly leaving placeholders for missing automated red-team and multi-turn results.

**Architecture:** The rewrite will use the static-analysis outputs under `Results/final/run_*` as the primary evidence base. The chapter will be organized around attack-dimension findings and mechanism interpretation rather than model-by-model reporting, with cross-model differences embedded only as supporting evidence. Sections without available data will remain in place but be turned into clearly labeled data requirements and future-fill placeholders.

**Tech Stack:** LaTeX, CSV analysis outputs, representative case summaries, local experiment figures

---

### Task 1: Consolidate static experimental evidence

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/4.tex`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202601/group_metrics.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202620/group_metrics.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202631/group_metrics.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202601/representative_cases.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202620/representative_cases.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260415_202631/representative_cases.csv`

**Step 1: Read and summarize group-level statistics**

Collect for each model:
- success rate by attack group
- uncertain rate by attack group
- high-risk ratio by attack group

Identify stable cross-model patterns rather than one-off outliers.

**Step 2: Read representative cases**

Extract a small set of cases that support:
- semantic-packaging vulnerability
- structure / context-induced boundary weakening
- residual robustness in low-resource and encoding settings

**Step 3: Define the evidence hierarchy**

Use this order in the chapter:
- cross-model common patterns
- attack-dimension contrasts
- representative cases
- residual limitations and data gaps

### Task 2: Rewrite Chapter 4 around vulnerability analysis

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/4.tex`

**Step 1: Rewrite the chapter opening**

State that:
- the chapter analyzes static attack results from three models
- the aim is to identify common alignment weaknesses
- numerical success rates are low overall, but this does not imply absence of risk

**Step 2: Replace the static-results section structure**

Prefer headings that emphasize:
- overall experimental characteristics
- cross-dimension vulnerability comparison
- risk distribution and uncertainty
- representative case analysis

Allow modest title changes while keeping the chapter coherent with Chapter 3.

**Step 3: Write balanced interpretation**

Frame the results so that:
- low direct-success rates indicate partial effectiveness of current alignment
- persistent cross-model success in certain dimensions reveals systematic weaknesses
- large uncertain regions indicate unstable boundaries rather than robust safety

**Step 4: Keep missing-result sections explicit**

For automated red-team and multi-turn sections:
- state that complete results are not yet available
- list the exact data needed to complete analysis
- avoid pretending that these results already exist

### Task 3: Final consistency check

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/4.tex`
- Reference: `/home/jellyz/Experiment/A_paper/3.tex`
- Reference: `/home/jellyz/Experiment/A_paper/5.tex`

**Step 1: Check chapter-to-chapter flow**

Ensure:
- Chapter 3 defines data, process, and metrics
- Chapter 4 performs evidence-based comparison and interpretation
- Chapter 5 can naturally inherit the identified weak attack surfaces

**Step 2: Check tone and claims**

Avoid:
- overclaiming defense failure
- turning the chapter into a model ranking
- unsupported statements about red-team or multi-turn results

**Step 3: Final polish**

Tighten wording, remove redundant meta-commentary, and keep the chapter academically consistent with the rest of the thesis.
