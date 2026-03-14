# Multi-Turn Defense Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reconnect the existing `Defense` engine to the new multi-turn jailbreak runners and expose it through the new CLIs and launcher.

**Architecture:** Keep defense orchestration in `MultiTurnCaseRunner`, using the existing `Defense.defense_mode` engine for per-round pre-call and post-call decisions. Keep the model tester transport-only, and restore CLI flags and launcher argument passing around the runner.

**Tech Stack:** Python 3, Bash, unittest, existing `Defense.defense_mode`

---

### Task 1: Add failing runner tests for defense block and sanitized response

**Files:**
- Modify: `tests/test_multi_turn_runner.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runner.py`

**Step 1: Write the failing tests**

Add tests covering:

- pre-call defense block stops before model invocation
- post-call sanitized response is used as visible response

**Step 2: Run test to verify it fails**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runner.py`
Expected: FAIL because runner does not yet support defense injection.

**Step 3: Write minimal implementation**

Add:

- optional `defense_engine`
- optional `defense_enabled`
- per-round defense handling
- defense metadata in round and final result payloads

**Step 4: Run test to verify it passes**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runner.py`
Expected: PASS

### Task 2: Add failing CLI tests for defense flags

**Files:**
- Modify: `tests/test_multi_turn_cli.py`
- Modify: `tests/test_multi_turn_single_cli.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/model_tester.py`

**Step 1: Write the failing tests**

Assert the parsers accept:

- `--enable-defense`
- `--defense-config`
- `--defense-archive-format`

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py`
Expected: FAIL because these flags are missing.

**Step 3: Write minimal implementation**

Add:

- parser flags
- helper to build a `DefenseEngine` from CLI options
- runner wiring

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py`
Expected: PASS

### Task 3: Add a failing launcher test and reconnect defense flags

**Files:**
- Modify: `tests/test_jailbreak_launcher.py`
- Modify: `Jelly_Z/bin/jailbreak`

**Step 1: Write the failing test**

Assert the launcher again passes defense flags to the Python entry points when defense is enabled.

**Step 2: Run test to verify it fails**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: FAIL because defense is currently ignored.

**Step 3: Write minimal implementation**

Update the launcher to:

- rebuild `DEFENSE_ARGS`
- pass them to both single and multi Python commands

**Step 4: Run test to verify it passes**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: PASS

### Task 4: Run regression verification

**Files:**
- Read: `Jailbreak/jailbreak_tools/single_jail/*.py`
- Read: `Jailbreak/jailbreak_tools/multi_jail/*.py`
- Read: `Jelly_Z/bin/jailbreak`
- Read: `tests/*.py`

**Step 1: Run focused regression tests**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_runner.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: PASS

**Step 2: Run Python CLI help checks**

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/single_jail.py --help`
Expected: exit 0 with defense flags listed

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py --help`
Expected: exit 0 with defense flags listed

**Step 3: Inspect diff**

Run: `git -C /home/jellyz/Experiment diff --stat`
Expected: runner, CLI, launcher, tests, and plan docs updated
