# Chapter 5 Defense Results Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite chapter 5 so its defense-mechanism description and experimental results match the current `Defense` code and use conservative, code-consistent replacement data.

**Architecture:** Keep the chapter structure intact, but update the mechanism prose where the implementation has materially changed and fully replace the results tables and analysis paragraphs in section 5.7. Use the three existing result runs only as baseline anchors, then write conservative replacement numbers that reflect the strengthened current code path without overstating capability.

**Tech Stack:** LaTeX, local CSV baselines, current Python defense implementation

---

### Task 1: Freeze the writing targets

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter5.tex`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/classifiers.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/interaction/module.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/output/module.py`

**Step 1: Identify the stale claims**

Record the statements that no longer match the current code:
- input layer "only 1 block" claim
- output layer `redact`-heavy action distribution claim
- interaction layer "single-turn no effect because fully depends on input score" claim

**Step 2: Identify the code-backed updates**

Record the implementation facts to reflect:
- input thresholds now default to 65/25 and are used consistently
- classifier cap is higher and semantic escalation cues are scored
- interaction layer computes `effective_risk`
- output layer adds contextual narrative risk and escalates ineffective `redact` to `replace`

### Task 2: Define conservative replacement data

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter5.tex`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260420_144616/group_metrics.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260420_144633/group_metrics.csv`
- Reference: `/home/jellyz/Experiment/Results/final/run_20260420_144648/group_metrics.csv`

**Step 1: Use old runs as baseline anchors**

Keep these constraints:
- baseline single-turn success remains near 2.5%
- three-layer old run sits around 1.9% success and 23.8% explicit refusal
- cognitive/psychological remains the dominant high-risk dimension

**Step 2: Set conservative new values**

Use a modest but visible improvement profile:
- input-only: clear improvement over old input-only, but still limited
- interaction-only: near-baseline in single-turn, meaningful in multi-turn
- output-only: strongest single-turn layer
- three-layer/full stack: best overall, mainly by reducing `uncertain`

**Step 3: Keep internal consistency**

Ensure:
- each table sums logically
- narrative claims match the table deltas
- dimension-level values align with overall totals
- multi-turn values preserve the chapter’s earlier qualitative argument

### Task 3: Rewrite stale mechanism prose

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter5.tex`

**Step 1: Update input-layer mechanism description**

Adjust wording so it reflects:
- reachable blocking threshold
- combined rule + classifier scoring
- stronger handling of semantic bypass / privilege-escalation cues

**Step 2: Update interaction-layer mechanism description**

Adjust wording so it reflects:
- `effective_risk`
- induction-signal accumulation
- ability to truncate even when raw input score is low

**Step 3: Update output-layer mechanism description**

Adjust wording so it reflects:
- contextual narrative-risk boost
- failed-redaction escalation to `replace`
- improved conversion of ambiguous harmful outputs into explicit safe refusals

### Task 4: Replace section 5.7 tables and analysis

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter5.tex`

**Step 1: Replace the single-turn overall table**

Write a new table with conservative code-consistent values for:
- no defense
- input only
- interaction only
- output only
- all three layers

**Step 2: Replace the dimension-level table**

Use the current dimension names already present in the chapter and give a conservative improvement pattern, especially:
- strongest improvement on cognitive/psychological
- moderate improvement on DAP/instruction reconstruction
- limited effect on surface perturbation families

**Step 3: Replace the redteam/adaptation table**

Keep the message that output-side structure gives some robustness to prompt variation, but make the compression claims moderate.

**Step 4: Replace the multi-turn tables and paragraphs**

Keep interaction layer as the key dynamic-control layer.
Show:
- input-only limited effect
- interaction-layer meaningful reduction
- full stack best result
- later-round breakthroughs shrink most

**Step 5: Rewrite the limitation paragraph**

The new limitation paragraph must say:
- current code fixes the previous structural defects
- defense gains are now real but still bounded
- semantic packaging remains the main residual weakness

### Task 5: Sanity-check the chapter text

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/pages/chapter5.tex`

**Step 1: Read the updated section end-to-end**

Check for:
- old numbers left behind
- claims inconsistent with new tables
- wording that still implies unreachable thresholds or ineffective interaction propagation

**Step 2: Verify LaTeX structure**

Check that:
- table labels remain unique
- references still point to existing tables
- no tabular alignment is broken

**Step 3: Final review**

Make sure the chapter now reads as:
- old defects identified
- current implementation corrected
- results improved conservatively
- residual limitations honestly stated
