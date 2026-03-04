# Jailbreak Judge Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a refactored jailbreak evaluation pipeline with keyword judge, LLM classifier-style judge (Ollama + external API abstraction), structured policy judge, and quantitative stats/plots.

**Architecture:** Introduce a modular judge pipeline with a shared schema and provider-agnostic LLM client. Process JSONL records into a dataframe, evaluate per-record decisions, then aggregate by model and attack method for success rate, stability, and risk distribution. Expose a CLI for one-shot analysis and chart export.

**Tech Stack:** Python 3, dataclasses, pandas, numpy, matplotlib, unittest

---

### Task 1: Define schema and decision contracts

**Files:**
- Create: `results_analyze/jailbreak_metrics/schema.py`
- Create: `tests/test_jailbreak_schema.py`

**Step 1: Write the failing test**
- Add tests for:
  - valid `JudgeDecision` creation
  - invalid `is_jailbreak` or `risk_level` rejected
  - `from_dict`/`to_dict` roundtrip

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_schema.py -v`
- Expected: FAIL (missing module/classes)

**Step 3: Write minimal implementation**
- Implement shared schema dataclasses and validators.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_schema.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add tests/test_jailbreak_schema.py results_analyze/jailbreak_metrics/schema.py`
- `git commit -m "feat: add jailbreak decision schema"`

### Task 2: Implement keyword and structured policy judges

**Files:**
- Create: `results_analyze/jailbreak_metrics/judges/__init__.py`
- Create: `results_analyze/jailbreak_metrics/judges/keyword_judge.py`
- Create: `results_analyze/jailbreak_metrics/judges/structured_policy_judge.py`
- Create: `tests/test_jailbreak_judges_rules.py`

**Step 1: Write the failing test**
- Test refusal response -> `no`, harmful steps -> `yes`, mixed response -> `uncertain`.
- Test structured judge downgrades missing evidence to `uncertain`.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_judges_rules.py -v`
- Expected: FAIL

**Step 3: Write minimal implementation**
- Add keyword lists and deterministic rule mapping.
- Add structured validation for three-part schema constraints.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_judges_rules.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add tests/test_jailbreak_judges_rules.py results_analyze/jailbreak_metrics/judges/*`
- `git commit -m "feat: add keyword and structured policy judges"`

### Task 3: Implement LLM judge with provider abstraction

**Files:**
- Create: `results_analyze/jailbreak_metrics/llm_clients.py`
- Create: `results_analyze/jailbreak_metrics/judges/llm_judge.py`
- Create: `tests/test_jailbreak_llm_judge.py`

**Step 1: Write the failing test**
- Test provider selection (`ollama`, `external`).
- Test JSON parsing success and parse-failure fallback decision.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_llm_judge.py -v`
- Expected: FAIL

**Step 3: Write minimal implementation**
- Define `BaseLLMClient`, `OllamaClient`, `ExternalAPIClient`.
- Implement `LLMJudge` prompt+JSON parsing+fallback behavior.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_llm_judge.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add tests/test_jailbreak_llm_judge.py results_analyze/jailbreak_metrics/llm_clients.py results_analyze/jailbreak_metrics/judges/llm_judge.py`
- `git commit -m "feat: add pluggable llm judge with ollama and external adapters"`

### Task 4: Build end-to-end pipeline and statistics

**Files:**
- Create: `results_analyze/jailbreak_metrics/pipeline.py`
- Create: `results_analyze/jailbreak_metrics/stats.py`
- Create: `tests/test_jailbreak_pipeline_stats.py`

**Step 1: Write the failing test**
- Use temporary JSONL fixture and mock judge outputs.
- Validate per-record dataframe columns and aggregated metrics.
- Validate CI columns and risk distribution columns exist.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_pipeline_stats.py -v`
- Expected: FAIL

**Step 3: Write minimal implementation**
- Implement JSONL loader, evaluator loop, dataframe builder.
- Implement grouped metrics using pandas/numpy.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_pipeline_stats.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add tests/test_jailbreak_pipeline_stats.py results_analyze/jailbreak_metrics/pipeline.py results_analyze/jailbreak_metrics/stats.py`
- `git commit -m "feat: add jailbreak analysis pipeline and grouped statistics"`

### Task 5: Add matplotlib visualization and CLI

**Files:**
- Create: `results_analyze/jailbreak_metrics/plotting.py`
- Create: `results_analyze/jailbreak_metrics/cli.py`
- Modify: `results_analyze/jailbreak_metrics/__init__.py`
- Create: `tests/test_jailbreak_cli_smoke.py`

**Step 1: Write the failing test**
- Smoke test CLI argument parsing and output artifact creation in temp dir.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_cli_smoke.py -v`
- Expected: FAIL

**Step 3: Write minimal implementation**
- Add plot functions and save figures.
- Add CLI orchestrating evaluation->stats->csv->plots.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_cli_smoke.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add tests/test_jailbreak_cli_smoke.py results_analyze/jailbreak_metrics/plotting.py results_analyze/jailbreak_metrics/cli.py results_analyze/jailbreak_metrics/__init__.py`
- `git commit -m "feat: add jailbreak metrics cli and visualizations"`

### Task 6: Verify with real dataset and document usage

**Files:**
- Modify: `results_analyze/jailbreak_metrics/minimal_demo.py` (optional wrapper/deprecation)
- Create: `results_analyze/jailbreak_metrics/README.md`

**Step 1: Write the failing test**
- Add a small regression test for backward-compatible demo import/entry behavior if needed.

**Step 2: Run test to verify it fails**
- Run: `python -m unittest tests/test_jailbreak_results_demo.py -v`
- Expected: FAIL (if behavior changed)

**Step 3: Write minimal implementation**
- Keep demo compatibility or redirect to new CLI.
- Add README with sample commands and provider config.

**Step 4: Run test to verify it passes**
- Run: `python -m unittest tests/test_jailbreak_results_demo.py -v`
- Expected: PASS

**Step 5: Commit**
- `git add results_analyze/jailbreak_metrics/minimal_demo.py results_analyze/jailbreak_metrics/README.md tests/test_jailbreak_results_demo.py`
- `git commit -m "docs: add jailbreak metrics usage and preserve demo compatibility"`
