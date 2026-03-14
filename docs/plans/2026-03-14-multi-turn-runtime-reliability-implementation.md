# Multi-Turn Runtime Reliability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore resume, autosave, and aggregate dynamic progress behavior to the new multi-turn jailbreak entry points.

**Architecture:** Extend the JSONL writer with completion-index and fsync support, then add a lightweight runtime coordinator used by both new entry points. Keep `MultiTurnCaseRunner` unchanged apart from consuming the resulting runtime flow.

**Tech Stack:** Python 3, asyncio, JSONL, unittest

---

### Task 1: Add failing tests for completed-pair loading and progress formatting

**Files:**
- Modify: `tests/test_multi_turn_result_writer.py`
- Create: `tests/test_multi_turn_runtime.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/result_writer.py`
- Create: `Jailbreak/jailbreak_tools/multi_jail/runtime.py`

**Step 1: Write the failing tests**

Cover:

- loading completed `(model_name, test_id)` pairs from existing JSONL
- rendering the compact progress bar format

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: FAIL because the writer and runtime helper do not yet support this behavior.

**Step 3: Write minimal implementation**

Add:

- completed-pair loader
- explicit fsync helper
- progress rendering helper

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: PASS

### Task 2: Add failing CLI tests for resume and autosave flags

**Files:**
- Modify: `tests/test_multi_turn_cli.py`
- Modify: `tests/test_multi_turn_single_cli.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/single_jail.py`

**Step 1: Write the failing tests**

Assert both parsers accept:

- `--resume`
- `--autosave-interval`
- `--concurrency`

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py`
Expected: FAIL because these flags are missing.

**Step 3: Write minimal implementation**

Add parser flags and runtime wiring.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py`
Expected: PASS

### Task 3: Add failing resume-flow tests and wire coordinator into entry points

**Files:**
- Modify: `tests/test_single_jail_runtime.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runtime.py`

**Step 1: Write the failing tests**

Cover:

- resume skips a completed `(model_name, test_id)` pair
- aggregate counters update correctly

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: FAIL because entry points do not yet coordinate resume/progress behavior.

**Step 3: Write minimal implementation**

Wire both entry points through the shared runtime coordinator.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: PASS

### Task 4: Run focused regression verification

**Files:**
- Read: `Jailbreak/jailbreak_tools/multi_jail/*.py`
- Read: `Jailbreak/jailbreak_tools/single_jail/*.py`
- Read: `tests/*.py`

**Step 1: Run focused tests**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py /home/jellyz/Experiment/tests/test_multi_turn_runner.py`
Expected: PASS

**Step 2: Run help checks**

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/single_jail.py --help`
Expected: lists resume/autosave/concurrency flags

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py --help`
Expected: lists resume/autosave/concurrency flags

**Step 3: Inspect diff**

Run: `git -C /home/jellyz/Experiment diff --stat`
Expected: runtime, writer, tests, and entry points updated
