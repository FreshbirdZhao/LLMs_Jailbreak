# Single Jail Metadata Design

**Goal:** Make `Jailbreak/jailbreak_tools/single_jail` emit single-turn JSONL records with the same static attack metadata shape as `Jailbreak/jailbreak_results/qwen2.5_3b_jailbreaking_dataset_v1_single_turn.jsonl` when the source dataset is `Attack_Dataset/jailbreaking_dataset_v1.csv`.

**Problem**

The current single-turn pipeline already writes several metadata fields from the normalized `case` object, but the loader does not explicitly map the `jailbreaking_dataset_v1.csv` schema into the normalized fields needed by the writer. As a result, generated records can miss:

- `attack_dimension`
- `attack_method`
- `source_prompt`
- `origin`

This forces post-processing with `Analyze/enrich_results.py`, which is avoidable and has already proven risky when used in-place.

**Approaches Considered**

1. Patch only `single_jail.py`
   This would add dataset-specific mapping logic inside the result writer path. It is the fastest short-term patch, but it couples the runtime result emitter to one CSV schema and makes future dataset support harder to reason about.

2. Patch only `Loader`
   This keeps dataset-specific field mapping in the normalization layer, which is where it belongs. It works for most required fields, but `single_jail.py` still needs to persist `origin`, so loader-only is incomplete.

3. Patch `Loader` plus one small write-path change in `single_jail.py`
   This keeps schema translation in `Loader` and makes the output writer persist the full normalized metadata set. It is the smallest complete fix and preserves separation of concerns.

**Recommendation**

Use approach 3.

**Design**

1. Extend `Jailbreak/jailbreak_tools/loader.py` so CSV rows from `jailbreaking_dataset_v1.csv` normalize as:
   - `attack_dimension <- technique_type`
   - `attack_method <- technique`
   - `source_prompt <- input_prompt`
   - `origin <- origin`
   - `source_file <- dataset_name`
   - `attack_type <- attack_dimension` when no explicit `attack_type` exists

2. Extend `Jailbreak/jailbreak_tools/single_jail/single_jail.py` so the record written by `_run_single_case()` includes:
   - `origin`

3. Verify with focused tests:
   - loader normalization for `jailbreaking_dataset_v1.csv`
   - single-turn result generation includes the reference metadata fields

**Error Handling**

- Missing optional CSV columns should still degrade safely to empty strings.
- If prompt content is missing, existing loader validation should continue to fail fast.

**Testing**

- Add a targeted unit test for `Loader.load_from_csv()`.
- Add a focused unit test for `_run_single_case()` or equivalent result construction behavior.
- Run the targeted test module with the project Python environment.
