# Analyze Results Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write a user-facing Chinese guide under `Results/` that explains single-turn and multi-turn analysis outputs, judge-mode logic, CSV fields, and figure parameters well enough for users to interpret analysis results correctly.

**Architecture:** The guide will be a standalone Markdown document in `Results/` so users can find it next to generated outputs. It will synthesize behavior from `Analyze.cli`, `Analyze.multi_turn.cli`, judge implementations, and plotting/statistics code into practical reading guidance rather than code-oriented API notes.

**Tech Stack:** Markdown

---

### Task 1: Draft the guide content

**Files:**
- Create: `Results/ANALYZE_RESULTS_GUIDE_ZH.md`

**Step 1: Gather the exact behaviors to document**

Capture:
- `keyword / llm / hybrid` judge logic
- single-turn vs multi-turn output directory layout
- `records.csv`, `group_metrics.csv`, `multi_turn_round_metrics.csv`
- six figures and how to read them

**Step 2: Write the document**

The document should cover:

```md
1. Analyze 在做什么
2. 三种判定模式的逻辑
3. 单轮结果怎么看
4. 多轮结果怎么看
5. 每个 CSV 的关键字段
6. 每张图的参数与读法
7. 常见误区
```

**Step 3: Review for clarity**

Check that a user without code context can answer:
- 判定模式有什么区别
- `yes/no/uncertain` 怎么来的
- 风险等级怎么理解
- 多轮成功轮次怎么读

**Step 4: Commit**

```bash
git add /home/jellyz/Experiment/Results/ANALYZE_RESULTS_GUIDE_ZH.md /home/jellyz/Experiment/docs/plans/2026-03-22-analyze-results-guide.md
git commit -m "docs: add analyze results guide"
```
