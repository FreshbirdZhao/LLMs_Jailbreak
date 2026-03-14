# Jailbreak Launcher Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `Jelly_Z/bin/jailbreak` launch the new multi-turn jailbreak entry scripts without changing the visible menu wording.

**Architecture:** Modify the shell launcher in place. Keep its model and dataset selection flow, but switch script targets and only pass CLI flags supported by the new Python entry points. Treat defense settings as ignored for now rather than rebuilding defense integration.

**Tech Stack:** Bash, Python CLI entry points, unittest-based verification

---

### Task 1: Add a failing test for launcher path and argument mapping

**Files:**
- Create: `tests/test_jailbreak_launcher.py`
- Modify: `Jelly_Z/bin/jailbreak`

**Step 1: Write the failing test**

Create a test that reads `Jelly_Z/bin/jailbreak` and asserts:

- it references `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- it references `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- it uses `--datasets` for multi mode
- it does not reference deleted flat script paths

**Step 2: Run test to verify it fails**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: FAIL because the launcher still points to deleted flat scripts.

**Step 3: Write minimal implementation**

Update the launcher script path assignments and the single/multi Python invocation blocks.

**Step 4: Run test to verify it passes**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: PASS

### Task 2: Verify launcher and new CLIs still execute

**Files:**
- Modify: `Jelly_Z/bin/jailbreak`

**Step 1: Run regression tests**

Run: `python -m unittest /home/jellyz/Experiment/tests/test_single_jail_runtime.py /home/jellyz/Experiment/tests/test_multi_turn_cli.py /home/jellyz/Experiment/tests/test_multi_turn_single_cli.py /home/jellyz/Experiment/tests/test_jailbreak_launcher.py`
Expected: PASS

**Step 2: Run Python CLI help checks**

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/single_jail/single_jail.py --help`
Expected: exit 0

Run: `python /home/jellyz/Experiment/Jailbreak/jailbreak_tools/multi_jail/multi_jail.py --help`
Expected: exit 0

**Step 3: Inspect diff**

Run: `git -C /home/jellyz/Experiment diff -- Jelly_Z/bin/jailbreak tests/test_jailbreak_launcher.py`
Expected: only launcher sync changes and its test
