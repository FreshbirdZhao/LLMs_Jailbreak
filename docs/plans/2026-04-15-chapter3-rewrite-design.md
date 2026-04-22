# Chapter 3 Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `A_paper/3.tex` so Chapter 3 reflects the real jailbreak experiment design, data pipeline, and evaluation protocol while keeping all existing section and subsection headings.

**Architecture:** The rewrite keeps the current chapter structure but replaces abstract or mismatched taxonomy text with implementation-aligned descriptions drawn from the local dataset, loader, single-turn executor, judging logic, and analysis outputs. The chapter remains design-oriented: it defines threat model, dataset construction, execution flow, and evaluation metrics, while leaving empirical findings to Chapter 4.

**Tech Stack:** LaTeX, local CSV/JSONL experiment artifacts, Python execution pipeline, analysis documentation

---

### Task 1: Align source materials

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/3.tex`
- Reference: `/home/jellyz/Experiment/Attack_Dataset/jailbreaking_dataset_v1.csv`
- Reference: `/home/jellyz/Experiment/Jailbreak/jailbreak_tools/loader.py`
- Reference: `/home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- Reference: `/home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/judgers.py`
- Reference: `/home/jellyz/Experiment/Results/ANALYZE_RESULTS_GUIDE_ZH.md`

**Step 1: Confirm the real experiment inputs**

Read the dataset fields, execution script, judge logic, and analysis guide. Record the exact concepts that must appear in Chapter 3:
- normalized dataset fields
- black-box single-turn testing
- heuristic non-refusal judge during execution
- offline `yes/no/uncertain` and `risk_level` analysis
- distinction between static experiment design and later result interpretation

**Step 2: Identify mismatches in current chapter text**

Mark any paragraph that:
- uses a taxonomy not reflected in the real data pipeline
- states results instead of design
- over-describes automatic red teaming or multi-turn modules without matching evidence

**Step 3: Define the rewrite boundary**

Keep all current headings. Rewrite body text so that:
- static attacks are the chapter core
- automated red teaming and multi-turn sections are retained only as framework extensions
- no Chapter 4-style ranking or conclusion is introduced

### Task 2: Rewrite the chapter body

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/3.tex`

**Step 1: Rewrite the threat model section**

Describe:
- black-box attacker assumptions
- harmful prompt reformulation ability
- single-turn focus of the main experiment
- attack surface categories used to motivate the dataset

**Step 2: Rewrite the framework section**

Describe the three-part framework with correct emphasis:
- static dataset as the main evaluated module
- automated red teaming as later expansion
- multi-turn jailbreak as interaction extension

Avoid implying that all three parts have equal empirical coverage in Chapter 3.

**Step 3: Rewrite the static nine-dimension section**

For each retained subsection:
- explain the testing purpose of the dimension
- connect it to prompt construction patterns and dataset organization
- avoid claiming exact effectiveness

Use wording that can coexist with the real `attack_dimension` and `attack_type` fields without inventing unsupported mappings.

**Step 4: Rewrite the unified workflow and metrics section**

Describe:
- dataset loading and normalization
- model invocation flow
- single-turn response recording
- online heuristic judging
- offline analysis outputs and aggregate metrics

Make the metric definitions consistent with `group_metrics.csv` and `records.csv`.

### Task 3: Verify chapter consistency

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/3.tex`
- Reference: `/home/jellyz/Experiment/A_paper/4.tex`

**Step 1: Read the rewritten chapter top-to-bottom**

Check that the chapter:
- reads as methodology, not results
- matches the terminology in Chapters 1, 2, and 4
- avoids overcommitting on unsupported red-team or multi-turn results

**Step 2: Check transitions**

Ensure the end of Chapter 3 naturally hands off to Chapter 4:
- Chapter 3 defines data, process, and metrics
- Chapter 4 performs comparative analysis and mechanism interpretation

**Step 3: Final polish**

Tighten repeated phrases, remove implementation noise that is too code-like for a thesis, and keep the final prose academically consistent with the earlier chapters.
