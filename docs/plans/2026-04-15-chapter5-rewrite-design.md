# Chapter 5 Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `A_paper/5.tex` into a complete thesis chapter that presents the three-layer defense scheme implemented under `Defense/` as a paper-ready design, while explicitly leaving experimental validation sections as placeholders pending defense results.

**Architecture:** The rewrite will treat the defense system as a layered risk-control framework spanning pre-call input inspection, interaction-stage risk accumulation control, and post-generation output sanitization. The prose will emphasize functional roles, decision flow, and attack-surface mapping rather than code internals, but it will remain faithful to the actual modules, risk signals, and actions implemented in `Defense/defense_mode`.

**Tech Stack:** LaTeX, local Python defense modules, rule-based detection, lightweight risk scoring, audit logging

---

### Task 1: Extract the real defense design from code

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/5.tex`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/engine.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/input/module.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/interaction/module.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/output/module.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/rules.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/classifiers.py`
- Reference: `/home/jellyz/Experiment/Defense/defense_mode/types.py`

**Step 1: Summarize the engine-level control flow**

Capture the actual design elements that must appear in the chapter:
- unified `DefenseContext`
- shared `risk_score` and `risk_flags`
- layer-by-layer decision aggregation
- strongest-action priority across layers

**Step 2: Summarize each defense layer**

Record for each module:
- what it detects
- what action space it has
- what kind of risk it is meant to stop

**Step 3: Define the paper abstraction**

Translate code concepts into thesis language:
- rules + classifier become hybrid risk recognition
- rewrite / block become graded input intervention
- truncate / warning become interaction-stage containment
- redact / replace / archive become output-side sanitization and audit

### Task 2: Rewrite Chapter 5 as a paper-ready defense chapter

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/5.tex`

**Step 1: Rewrite the problem definition and framework sections**

State clearly that:
- the defense target is a full attack chain, not isolated keywords
- the scheme is intentionally layered
- the design follows the weak points identified in Chapter 4

**Step 2: Rewrite the three defense-layer sections**

For each layer:
- describe functional positioning
- explain main risk signals and decision logic
- relate the layer to the attack dimensions from earlier chapters

Keep this paper-oriented rather than implementation-manual style.

**Step 3: Rewrite the evaluation section as explicit placeholders**

Since defense results are not yet available:
- specify the exact data needed
- specify which tables/figures should be filled later
- avoid making any unsupported performance claims

### Task 3: Final consistency check

**Files:**
- Modify: `/home/jellyz/Experiment/A_paper/5.tex`
- Reference: `/home/jellyz/Experiment/A_paper/4.tex`
- Reference: `/home/jellyz/Experiment/A_paper/6.tex`

**Step 1: Check chapter linkage**

Ensure:
- Chapter 4 identifies the vulnerable attack surfaces
- Chapter 5 responds to them with a structurally matched defense design
- Chapter 6 can summarize this as part of the full attack-evaluation-defense loop

**Step 2: Check claim discipline**

Avoid:
- claiming defense effectiveness without data
- overloading the chapter with code-specific implementation trivia
- disconnecting the defense scheme from the attack evidence

**Step 3: Final polish**

Tighten language, make the three-layer structure prominent, and keep the tone consistent with the rest of the thesis.
