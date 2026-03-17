# Layered LLM Judge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an expanded heuristic judge plus an LLM-backed runtime judge so multi-turn jailbreak success is only confirmed when a dedicated judge model determines the response materially answers the harmful request.

**Architecture:** The shell launcher selects a third model for judging in multi-step mode, the multi-turn entrypoint resolves and wires that model into a layered judge, and the runner awaits that judge after each round. Heuristics reject obvious failures locally while the LLM judge only reviews ambiguous candidate successes.

**Tech Stack:** Bash, Python 3.12, asyncio, httpx, unittest

---

### Task 1: Add judge-model selection to the multi-step launcher

**Files:**
- Modify: `Jelly_Z/bin/jailbreak`
- Test: `tests/test_jailbreak_launcher.py`

**Step 1: Write the failing test**

Extend the launcher test to require:

- a judge-model selection prompt in multi-step mode
- Ollama lifecycle handling for judge model
- `--judge-model "$JUDGE_MODEL_NAME"` in the multi-turn command

**Step 2: Run test to verify it fails**

Run: `Jelly_Z/bin/python -m unittest tests/test_jailbreak_launcher.py`
Expected: FAIL because launcher does not yet mention judge-model selection.

**Step 3: Implement launcher changes**

- add judge-model selection after planner-model selection
- store `JUDGE_MODEL_NAME`, `JUDGE_MODEL_BASE_URL`, `JUDGE_MODEL_TYPE`
- call `ensure_ollama_for_base_url "$JUDGE_MODEL_BASE_URL" "jailbreak-judge"` when needed
- print judge-model summary in final config
- pass `--judge-model "$JUDGE_MODEL_NAME"` to `multi_jail.py`

**Step 4: Run test to verify it passes**

Run: `Jelly_Z/bin/python -m unittest tests/test_jailbreak_launcher.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jelly_Z/bin/jailbreak tests/test_jailbreak_launcher.py
git commit -m "feat: require judge model for multi-step jailbreak"
```

### Task 2: Add CLI and model resolution support for judge model

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/model_tester.py`
- Test: `tests/test_multi_turn_cli.py`
- Test: `tests/test_multi_turn_model_tester.py`

**Step 1: Write the failing tests**

Cover:

- `--judge-model` is required for multi-turn CLI
- the entrypoint resolves the judge model
- startup fails cleanly when judge model is unavailable

**Step 2: Run tests to verify they fail**

Run:

```bash
Jelly_Z/bin/python -m unittest \
  tests/test_multi_turn_cli.py \
  tests/test_multi_turn_model_tester.py
```

Expected: FAIL because judge-model support is missing.

**Step 3: Implement minimal support**

- add `--judge-model` argument
- resolve judge model with `MultiTurnModelTester.get_model`
- fail fast if not found
- wire resolved judge model into layered judge construction

**Step 4: Run tests to verify they pass**

Run the same unittest command.
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/multi_jail.py Jailbreak/jailbreak_tools/single_jail/model_tester.py tests/test_multi_turn_cli.py tests/test_multi_turn_model_tester.py
git commit -m "feat: wire judge model into multi-turn runtime"
```

### Task 3: Implement expanded heuristics and LLM judge classes

**Files:**
- Modify: `Jailbreak/jailbreak_tools/single_jail/judgers.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/__init__.py`
- Test: `tests/test_multi_turn_judgers.py`
- Create: `tests/test_layered_llm_judge.py`

**Step 1: Write the failing tests**

Cover:

- heuristic judge marks direct refusal as `refused`
- heuristic judge marks policy preaching / generic non-answer as `refused`
- heuristic judge marks ambiguous content as `needs_llm_review`
- LLM judge parses valid JSON result
- LLM judge returns `error` on malformed output
- layered judge skips LLM call when heuristics already refuse
- layered judge calls LLM judge only for `needs_llm_review`

**Step 2: Run tests to verify they fail**

Run:

```bash
Jelly_Z/bin/python -m unittest \
  tests/test_multi_turn_judgers.py \
  tests/test_layered_llm_judge.py
```

Expected: FAIL because the new classes and statuses do not exist.

**Step 3: Implement minimal judge stack**

- add `HeuristicJudge`
- add `LLMJudge`
- add `LayeredJudge`
- preserve or alias `NonRefusalJudge` only if needed for backward compatibility
- define structured judge metadata including stage/model/confidence

**Step 4: Run tests to verify they pass**

Run the same unittest command.
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/single_jail/judgers.py Jailbreak/jailbreak_tools/single_jail/__init__.py tests/test_multi_turn_judgers.py tests/test_layered_llm_judge.py
git commit -m "feat: add layered heuristic and llm judge stack"
```

### Task 4: Integrate layered judge into the runner and result schema

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runner.py`
- Test: `tests/test_multi_turn_runner.py`

**Step 1: Write the failing test**

Cover:

- runner awaits the layered judge
- round metadata includes `judge_stage`, `judge_model_name`, and `judge_confidence`
- final result records judge model name and final reason/confidence
- non-success judge result triggers another planner-generated round

**Step 2: Run test to verify it fails**

Run: `Jelly_Z/bin/python -m unittest tests/test_multi_turn_runner.py`
Expected: FAIL because runner does not record layered judge metadata or await async judging.

**Step 3: Implement minimal runner changes**

- allow async judge interface
- replace fixed `NonRefusalJudge` default with layered judge when supplied
- persist per-round and final judge metadata
- use the final judge result, not heuristic absence-of-refusal, to stop the loop

**Step 4: Run test to verify it passes**

Run: `Jelly_Z/bin/python -m unittest tests/test_multi_turn_runner.py`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/runner.py tests/test_multi_turn_runner.py
git commit -m "feat: use layered llm judge in multi-turn runner"
```

### Task 5: Focused verification and smoke checks

**Files:**
- No additional files unless defects are found

**Step 1: Run focused unit tests**

Run:

```bash
Jelly_Z/bin/python -m unittest \
  tests/test_jailbreak_launcher.py \
  tests/test_multi_turn_cli.py \
  tests/test_multi_turn_model_tester.py \
  tests/test_multi_turn_judgers.py \
  tests/test_layered_llm_judge.py \
  tests/test_multi_turn_runner.py
```

Expected: PASS.

**Step 2: Run shell syntax smoke check**

Run: `bash -n Jelly_Z/bin/jailbreak`
Expected: PASS with no output.

**Step 3: Run one targeted runtime smoke test**

Run a patched or mocked `multi_jail.main()` test path to ensure planner model and judge model are both wired without network calls.

**Step 4: Re-run focused unit tests if any fixes were needed**

Expected: PASS.

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify layered llm judge runtime flow"
```
