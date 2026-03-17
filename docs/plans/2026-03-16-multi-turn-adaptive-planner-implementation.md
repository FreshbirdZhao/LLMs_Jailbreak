# Multi-Turn Adaptive Planner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the multi-turn jailbreak runtime so the auxiliary model builds an initial six-round attack plan, the judge model emits structured revision advice each round, and the executor updates the remaining plan without changing the original prompt objective.

**Architecture:** Split the flow into explicit planner, judge-feedback, and execution-state components. The entrypoint resolves planner and judge models, `AttackPlanner` creates an `AttackPlan`, `LayeredJudge` returns structured `JudgeFeedback`, and `MultiTurnCaseRunner` manages plan versions, replan triggers, and per-round prompt generation anchored to the original prompt.

**Tech Stack:** Bash, Python 3.12, asyncio, httpx, pytest

---

### Task 1: Lock down the planner data model with tests

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/prompt_strategy.py`
- Test: `tests/test_adaptive_multi_turn_strategy.py`

**Step 1: Write the failing test**

Cover:
- `AttackPlan` stores planner metadata and ordered round nodes
- `PlanRound` stores `goal`, `strategy`, `prompt_candidate`, and `fallback_hint`
- fallback plan generation produces six deterministic rounds anchored to `original_prompt`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_multi_turn_strategy.py -k "attack_plan or fallback_plan" -v`
Expected: FAIL because structured plan objects do not exist.

**Step 3: Write minimal implementation**

- add dataclasses for `PlanRound`, `AttackPlan`, and `FollowupPromptResult`
- keep `DefaultFollowupStrategy` as the deterministic fallback plan source
- add a helper that builds a six-round fallback plan using the original prompt and round index

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adaptive_multi_turn_strategy.py -k "attack_plan or fallback_plan" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/prompt_strategy.py tests/test_adaptive_multi_turn_strategy.py
git commit -m "feat: add multi-turn attack plan data model"
```

### Task 2: Build the initial attack planner with TDD

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/prompt_strategy.py`
- Test: `tests/test_adaptive_multi_turn_strategy.py`

**Step 1: Write the failing test**

Cover:
- planner model receives only the original prompt and round budget when building the initial plan
- valid planner JSON becomes an `AttackPlan`
- invalid or empty planner output falls back to the deterministic plan
- planner metadata and generation errors are preserved

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adaptive_multi_turn_strategy.py -k "initial_plan" -v`
Expected: FAIL because `AttackPlanner` does not exist.

**Step 3: Write minimal implementation**

- add `AttackPlanner`
- define planner prompt contract that asks for a six-round structured plan
- parse strict JSON into `AttackPlan`
- fall back to the deterministic plan on call failure or parse failure

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_adaptive_multi_turn_strategy.py -k "initial_plan" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py Jailbreak/jailbreak_tools/multi_jail/prompt_strategy.py tests/test_adaptive_multi_turn_strategy.py
git commit -m "feat: add initial multi-turn attack planner"
```

### Task 3: Expand judge output to structured revision feedback

**Files:**
- Modify: `Jailbreak/jailbreak_tools/single_jail/judgers.py`
- Test: `tests/test_multi_turn_judgers.py`

**Step 1: Write the failing tests**

Cover:
- `JudgeFeedback` exposes verdict plus revision fields
- `LLMJudge` parses strict JSON with `adjustment_goal`, `do_not_repeat`, and `alignment_to_original_prompt`
- malformed judge JSON returns a structured error feedback object
- heuristic-only refusals still produce valid `JudgeFeedback`

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_turn_judgers.py -k "judge_feedback or llm_judge" -v`
Expected: FAIL because judge feedback fields do not exist.

**Step 3: Write minimal implementation**

- replace or extend `JudgeResult` with a structured `JudgeFeedback` dataclass
- update `LLMJudge` prompt to require strict JSON with revision fields
- normalize heuristic results into the same feedback shape
- keep layered fallback semantics

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_multi_turn_judgers.py -k "judge_feedback or llm_judge" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/single_jail/judgers.py tests/test_multi_turn_judgers.py
git commit -m "feat: add structured judge feedback for multi-turn jailbreak"
```

### Task 4: Add execution state and per-round prompt generation

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runner.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py`
- Test: `tests/test_multi_turn_runner.py`

**Step 1: Write the failing test**

Cover:
- runner creates an initial plan before round 1
- failed rounds call `AdaptivePromptGenerator` with current plan node and `JudgeFeedback`
- successful rounds stop without generating extra prompts
- round records store plan metadata and structured judge feedback

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_turn_runner.py -k "initial_plan or prompt_generation" -v`
Expected: FAIL because the runner still uses ad hoc local state.

**Step 3: Write minimal implementation**

- add `ExecutionState`
- make the runner request an `AttackPlan` at case start
- use the active plan node for each round
- store plan version, plan goal, strategy, and follow-up metadata in round records

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_multi_turn_runner.py -k "initial_plan or prompt_generation" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/runner.py Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py tests/test_multi_turn_runner.py
git commit -m "feat: add execution state for adaptive multi-turn planning"
```

### Task 5: Add constrained suffix replanning

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runner.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py`
- Test: `tests/test_multi_turn_runner.py`

**Step 1: Run focused pytest coverage**

Write tests that cover:
- replanning triggers after two consecutive refusals
- replanning never rewrites executed rounds
- replanning is rejected when `alignment_to_original_prompt` is `misaligned`
- repeated replan failure falls back to local prompt rewriting only

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_turn_runner.py -k "replan" -v`
Expected: FAIL because suffix replanning does not exist.

**Step 3: Write minimal implementation**

- add replan trigger evaluation inside the runner
- add planner support for rebuilding only the remaining suffix
- record `replan_events` and new `plan_version` values
- reject misaligned replans and keep the last valid plan active

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_multi_turn_runner.py -k "replan" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/runner.py Jailbreak/jailbreak_tools/multi_jail/adaptive_strategy.py tests/test_multi_turn_runner.py
git commit -m "feat: add constrained multi-turn suffix replanning"
```

### Task 6: Wire planner and judge model resolution into the entrypoint and launcher

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/model_tester.py`
- Modify: `Jelly_Z/bin/jailbreak`
- Test: `tests/test_multi_turn_cli.py`
- Test: `tests/test_jailbreak_launcher.py`

**Step 1: Write the failing test**

Cover:
- `--planner-model` is required in multi-turn mode
- planner and judge models resolve cleanly from `models.yaml`
- launcher forwards planner model selection into the multi-turn script
- existing single-turn flows remain unchanged

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_multi_turn_cli.py tests/test_jailbreak_launcher.py -k "planner_model or multi_turn" -v`
Expected: FAIL because the redesigned runtime still assumes the older planner interface.

**Step 3: Write minimal implementation**

- resolve planner and judge models explicitly in the multi-turn entrypoint
- construct the new planner and judge objects for the runner
- update launcher prompt and command wiring for multi-step mode only

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_multi_turn_cli.py tests/test_jailbreak_launcher.py -k "planner_model or multi_turn" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add Jailbreak/jailbreak_tools/multi_jail/multi_jail.py Jailbreak/jailbreak_tools/single_jail/model_tester.py Jelly_Z/bin/jailbreak tests/test_multi_turn_cli.py tests/test_jailbreak_launcher.py
git commit -m "feat: wire adaptive multi-turn planner through launcher and cli"
```

### Task 7: Run focused verification before claiming completion

**Files:**
- No intended code changes unless verification exposes defects

**Step 1: Run the focused multi-turn test suite**

Run:

```bash
pytest tests/test_adaptive_multi_turn_strategy.py \
       tests/test_multi_turn_judgers.py \
       tests/test_multi_turn_runner.py \
       tests/test_multi_turn_cli.py \
       tests/test_jailbreak_launcher.py -v
```

Expected: all targeted tests PASS.

**Step 2: Run one multi-turn smoke command**

Run a minimal local smoke invocation of `multi_jail.py` with stubbed or mocked models if the test harness supports it.
Expected: startup succeeds, initial plan is created, and result output contains plan metadata.

**Step 3: Fix defects only if verification fails**

Apply the smallest change needed to satisfy the failing verification.

**Step 4: Re-run the failing command and the focused suite**

Expected: PASS.

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify redesigned adaptive multi-turn jailbreak flow"
```
