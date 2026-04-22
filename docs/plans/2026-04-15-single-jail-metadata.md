# Single Jail Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the single-turn jailbreak pipeline write `attack_type`, `attack_dimension`, `attack_method`, `source_prompt`, `source_file`, and `origin` directly into result JSONL records for `jailbreaking_dataset_v1.csv`.

**Architecture:** Keep CSV-schema translation in `Jailbreak/jailbreak_tools/loader.py`, where dataset rows become normalized cases, and keep result emission in `Jailbreak/jailbreak_tools/single_jail/single_jail.py` limited to serializing normalized fields. Add narrow tests around both layers so future schema drift is caught before runtime.

**Tech Stack:** Python 3.12, `unittest`, project-local runtime in `Jelly_Z`

---

### Task 1: Cover Loader Normalization

**Files:**
- Modify: `tests/test_static_dimension_dataset_compat.py`
- Modify: `Jailbreak/jailbreak_tools/loader.py`

**Step 1: Write the failing test**

Add a test that writes a temporary `jailbreaking_dataset_v1.csv`-shaped CSV containing `id`, `prompt`, `origin`, `input_prompt`, `technique`, and `technique_type`, then loads it through `Loader.load_from_csv()` and asserts:

```python
self.assertEqual(case["id"], "jb_abc123")
self.assertEqual(case["attack_dimension"], "adversarial_suffixes")
self.assertEqual(case["attack_method"], "emoji_suffix")
self.assertEqual(case["source_prompt"], "seed prompt")
self.assertEqual(case["source_file"], "jailbreaking_dataset_v1.csv")
self.assertEqual(case["origin"], "handcrafted")
self.assertEqual(case["attack_type"], "adversarial_suffixes")
```

**Step 2: Run test to verify it fails**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest tests.test_static_dimension_dataset_compat`
Expected: FAIL because loader does not yet normalize `technique_type`, `technique`, `input_prompt`, or `origin`.

**Step 3: Write minimal implementation**

Update `Jailbreak/jailbreak_tools/loader.py` so `_normalize_case()` maps the `jailbreaking_dataset_v1.csv` columns into normalized metadata fields and includes `origin` in the returned case.

**Step 4: Run test to verify it passes**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest tests.test_static_dimension_dataset_compat`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_static_dimension_dataset_compat.py Jailbreak/jailbreak_tools/loader.py
git commit -m "feat: normalize jailbreak dataset metadata"
```

### Task 2: Cover Single-Turn Result Emission

**Files:**
- Modify: `Jailbreak/tests/test_single_jail_ordering.py`
- Modify: `Jailbreak/jailbreak_tools/single_jail/single_jail.py`

**Step 1: Write the failing test**

Add a focused async/unit test that calls `_run_single_case()` with a normalized `case` containing:

```python
{
    "id": "jb_abc123",
    "name": "sample",
    "prompt": "mutated prompt",
    "category": "Unsafe",
    "attack_type": "adversarial_suffixes",
    "attack_dimension": "adversarial_suffixes",
    "attack_method": "emoji_suffix",
    "source_prompt": "seed prompt",
    "source_file": "jailbreaking_dataset_v1.csv",
    "origin": "handcrafted",
}
```

Assert the returned record contains the same metadata fields, including `origin`.

**Step 2: Run test to verify it fails**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest Jailbreak.tests.test_single_jail_ordering`
Expected: FAIL because the emitted record does not yet include `origin`.

**Step 3: Write minimal implementation**

Update `_run_single_case()` in `Jailbreak/jailbreak_tools/single_jail/single_jail.py` to serialize `origin` from the normalized case.

**Step 4: Run test to verify it passes**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest Jailbreak.tests.test_single_jail_ordering`
Expected: PASS

**Step 5: Commit**

```bash
git add Jailbreak/tests/test_single_jail_ordering.py Jailbreak/jailbreak_tools/single_jail/single_jail.py
git commit -m "feat: emit single-jail origin metadata"
```

### Task 3: Verify End-to-End Metadata Shape

**Files:**
- Modify: `tests/test_analyze_paper_mode.py`

**Step 1: Write the failing test**

Add or extend a test that constructs an enriched single-turn-like record and verifies the final shape matches the reference static fields:

```python
self.assertEqual(record["attack_type"], "adversarial_suffixes")
self.assertEqual(record["attack_dimension"], "adversarial_suffixes")
self.assertEqual(record["attack_method"], "emoji_suffix")
self.assertEqual(record["source_prompt"], "seed prompt")
self.assertEqual(record["source_file"], "jailbreaking_dataset_v1.csv")
self.assertEqual(record["origin"], "handcrafted")
```

**Step 2: Run test to verify it fails**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`
Expected: FAIL if any required field is still missing from the pipeline shape.

**Step 3: Write minimal implementation**

Make only the smallest necessary changes to keep the emitted single-turn record shape consistent with the reference file.

**Step 4: Run test to verify it passes**

Run: `/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest /home/jellyz/Experiment/tests/test_analyze_paper_mode.py`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_analyze_paper_mode.py
git commit -m "test: cover single-jail metadata shape"
```

### Task 4: Final Verification

**Files:**
- No code changes required

**Step 1: Run targeted verification**

Run:

```bash
/home/jellyz/Experiment/Jelly_Z/bin/python -m unittest \
  tests.test_static_dimension_dataset_compat \
  Jailbreak.tests.test_single_jail_ordering \
  /home/jellyz/Experiment/tests/test_analyze_paper_mode.py
```

Expected: All targeted tests pass.

**Step 2: Inspect changed files**

Run:

```bash
git diff -- Jailbreak/jailbreak_tools/loader.py \
  Jailbreak/jailbreak_tools/single_jail/single_jail.py \
  tests/test_static_dimension_dataset_compat.py \
  Jailbreak/tests/test_single_jail_ordering.py \
  tests/test_analyze_paper_mode.py
```

Expected: Diff is limited to metadata normalization, result serialization, and tests.

**Step 3: Commit**

```bash
git add docs/plans/2026-04-15-single-jail-metadata-design.md docs/plans/2026-04-15-single-jail-metadata.md
git commit -m "docs: plan single-jail metadata output"
```
