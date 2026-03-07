# Jailbreak LLM Resilience Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add retry + Ollama auto-restart recovery for llm/hybrid analysis and add checkpoint resume so interrupted runs continue without losing completed results.

**Architecture:** Persist per-record progress in pipeline-side checkpoint artifacts and reuse them on restart. Add transient-error retry in Ollama client with local auto-start recovery. Keep shell runner lifecycle semantics so auto-started Ollama is cleaned up after analyze ends.

**Tech Stack:** Python (`unittest`, `urllib`), Bash runner (`analyze`, `ollama_utils.sh`), pandas pipeline.

---

### Task 1: Add failing tests for resume and retry

**Files:**
- Create/Modify: `tests/test_jailbreak_resilience.py`
- Test: `tests/test_jailbreak_resilience.py`

1. Write failing tests for pipeline resume after mid-run crash.
2. Run `python3 -m unittest tests.test_jailbreak_resilience` and verify failure.

### Task 2: Implement pipeline checkpoint resume

**Files:**
- Modify: `results_analyze/jailbreak_metrics/pipeline.py`
- Modify: `results_analyze/jailbreak_metrics/cli.py`
- Test: `tests/test_jailbreak_resilience.py`

1. Add checkpoint state and partial rows persistence.
2. Add CLI wiring (`--resume`) and pass output dir into pipeline.
3. Run targeted tests and ensure pass.

### Task 3: Implement Ollama retry and auto-restart recovery

**Files:**
- Modify: `results_analyze/jailbreak_metrics/llm_clients.py`
- Modify: `results_analyze/jailbreak_metrics/cli.py`
- Modify: `my_ai/bin/analyze`
- Test: `tests/test_jailbreak_resilience.py`

1. Add transient-error retry loop in Ollama client.
2. Auto-start local Ollama when unavailable and clean up processes started by Python client.
3. Add CLI knobs for retry counts.
4. Update `analyze` to retry CLI execution when Ollama-based run fails and continue from checkpoint.
5. Run targeted tests.

### Task 4: Final verification

**Files:**
- Verify modified files only.

1. Run focused tests for resilience behavior.
2. Run existing smoke tests for jailbreak CLI path.
3. Report exact verification commands and outcomes.
