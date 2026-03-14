# Multi-Turn Global Concurrency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the new multi-turn runtime actually execute tasks concurrently across all datasets and models using the existing `--concurrency` flag.

**Architecture:** Keep `MultiTurnCaseRunner` unchanged as a single-case executor. Extend the runtime coordination layer with an async work queue, worker pool, serialized writer access, and serialized progress updates.

**Tech Stack:** Python 3, asyncio, unittest

---

### Task 1: Add failing runtime tests for concurrent queue execution

**Files:**
- Modify: `tests/test_multi_turn_runtime.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/runtime.py`

**Step 1: Write the failing tests**

Cover:

- building and consuming a shared task queue
- honoring a requested concurrency value greater than 1
- skipping completed pairs before queueing

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: FAIL because runtime has no worker-pool helper yet.

**Step 3: Write minimal implementation**

Add:

- async worker helper
- queue processing helper
- progress-safe state updates

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: PASS

### Task 2: Wire global concurrency into the entry points

**Files:**
- Modify: `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- Modify: `Jailbreak/jailbreak_tools/multi_jail/result_writer.py`

**Step 1: Write the failing regression test if needed**

Add or extend runtime tests to assert writer access remains correct when multiple tasks share a writer.

**Step 2: Run tests to verify they fail**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: FAIL if locks are not present.

**Step 3: Write minimal implementation**

Add:

- writer-side async lock helpers
- global task queue wiring in both entry points

**Step 4: Run tests to verify they pass**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py`
Expected: PASS

### Task 3: Run focused regression verification

**Files:**
- Read: `Jailbreak/jailbreak_tools/multi_jail/*.py`
- Read: `Jailbreak/jailbreak_tools/single_jail/*.py`
- Read: `tests/*.py`

**Step 1: Run focused tests**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_result_writer.py /home/jellyz/Experiment/tests/test_multi_turn_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py /home/jellyz/Experiment/tests/test_multi_turn_runner.py`
Expected: PASS

**Step 2: Run help checks**

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/single_jail.py --help`
Expected: still lists concurrency flag

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py --help`
Expected: still lists concurrency flag

**Step 3: Inspect diff**

Run: `git -C /home/jellyz/Experiment diff --stat`
Expected: runtime and entry points updated for real concurrency
