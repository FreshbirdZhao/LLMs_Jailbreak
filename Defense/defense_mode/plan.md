# Jailbreak Defense Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a modular 3-layer defense system (input/interaction/output) that can be optionally enabled in `jailbreak_tools` attack workflows and stays compatible with future attack scripts.

**Architecture:** Add a standalone `defense_mode` package with a unified context/result protocol and composable pipeline runner. Integrate through lightweight hooks in `jailbreak_tools/single_jail.py` first, then expose reusable adapter APIs so later scripts can adopt defense with minimal changes.

**Tech Stack:** Python 3 (`dataclasses`, `enum`, `typing`, `json`, `sqlite3`, `re`), existing async workflow in `jailbreak_tools`.

---

## Design Options

### Option A (Recommended): Hook-based defense pipeline
- Add `DefenseEngine` and stage hooks (`before_input`, `before_model_call`, `after_model_response`).
- `single_jail.py` only calls hooks; defense logic remains in `defense_mode`.
- Best compatibility for future attack scripts.

### Option B: Embed defense logic directly into `single_jail.py`
- Faster initial coding, but creates coupling and future maintenance cost.

### Option C: External proxy process for defense
- Strong isolation, but extra process/protocol complexity and harder debugging.

**Recommendation:** Option A.

---

## Target Directory Structure

- Create: `defense_mode/__init__.py`
- Create: `defense_mode/interfaces.py`
- Create: `defense_mode/types.py`
- Create: `defense_mode/engine.py`
- Create: `defense_mode/config.py`
- Create: `defense_mode/logging_store.py`
- Create: `defense_mode/input_layer.py`
- Create: `defense_mode/interaction_layer.py`
- Create: `defense_mode/output_layer.py`
- Create: `defense_mode/rules.py`
- Create: `defense_mode/classifiers.py`
- Create: `tests/test_defense_engine.py`
- Create: `tests/test_defense_input_layer.py`
- Create: `tests/test_defense_interaction_layer.py`
- Create: `tests/test_defense_output_layer.py`
- Modify: `jailbreak_tools/single_jail.py`

---

## Unified Data Contract

### `DefenseContext`
- Request metadata: `model_name`, `test_id`, `attack_type`, `category`, `round_idx`.
- Text fields: `original_prompt`, `sanitized_prompt`, `raw_response`, `sanitized_response`.
- Runtime state: `risk_score`, `risk_flags`, `state`, `decision_history`.

### `DefenseDecision`
- `action`: `allow | rewrite | block | truncate | replace | redact`.
- `risk_level`: `0-3`.
- `reasons`: list of triggered rules/signals.
- `rewritten_text`: optional.
- `audit_payload`: structured JSON for archiving.

### `DefenseModule` interface
- `name()`
- `enabled(config)`
- `process(context) -> DefenseDecision`

---

## Task Plan (TDD-first)

### Task 1: Add failing tests for core protocol and engine orchestration

**Files:**
- Create: `tests/test_defense_engine.py`
- Create: `defense_mode/types.py`
- Create: `defense_mode/interfaces.py`
- Create: `defense_mode/engine.py`

1. Write tests for deterministic stage order: input -> interaction -> output.
2. Write tests for independent enable/disable of each module.
3. Write tests for decision precedence (`block` short-circuits model call).
4. Run: `python3 -m unittest tests.test_defense_engine -v` (expect FAIL first).
5. Implement minimal types/interfaces/engine until tests pass.
6. Re-run same test command and verify PASS.

### Task 2: Input layer defense (rules + lightweight classifier stub + rewrite)

**Files:**
- Create: `defense_mode/input_layer.py`
- Create: `defense_mode/rules.py`
- Create: `defense_mode/classifiers.py`
- Create: `tests/test_defense_input_layer.py`

1. Write failing tests for rule hits (system prompt hijack, privilege escalation, leakage bait).
2. Write failing tests for combined scoring (rule score + classifier score).
3. Write failing tests for actions by threshold: allow/rewrite/block.
4. Run: `python3 -m unittest tests.test_defense_input_layer -v` (expect FAIL first).
5. Implement minimal rule matcher + classifier adapter + templated rewrite.
6. Re-run targeted tests and verify PASS.

### Task 3: Interaction layer defense (state machine + multi-turn truncation)

**Files:**
- Create: `defense_mode/interaction_layer.py`
- Create: `tests/test_defense_interaction_layer.py`

1. Write failing tests for risk accumulation across rounds.
2. Write failing tests for state transitions (`normal -> warning -> restricted -> blocked`).
3. Write failing tests for truncation strategy when induced attack pattern persists.
4. Run: `python3 -m unittest tests.test_defense_interaction_layer -v` (expect FAIL first).
5. Implement minimal state machine and policy gates.
6. Re-run targeted tests and verify PASS.

### Task 4: Output layer defense (detect/filter/replace/archive)

**Files:**
- Create: `defense_mode/output_layer.py`
- Create: `defense_mode/logging_store.py`
- Create: `tests/test_defense_output_layer.py`

1. Write failing tests for output risk detection and keyword/structure policy hits.
2. Write failing tests for action strategy:
   - low risk: redact partial spans
   - medium risk: safe rewrite
   - high risk: refuse template replacement
3. Write failing tests for archival record shape (JSONL and SQLite adapters).
4. Run: `python3 -m unittest tests.test_defense_output_layer -v` (expect FAIL first).
5. Implement minimal output processing + archive writer.
6. Re-run targeted tests and verify PASS.

### Task 5: Integrate optional defense hooks into `single_jail.py`

**Files:**
- Modify: `jailbreak_tools/single_jail.py`
- Create: `defense_mode/config.py`
- Modify/Create: `defense_mode/__init__.py`
- Extend tests: `tests/test_jailbreak_cli_smoke.py` or create `tests/test_single_jail_defense_integration.py`

1. Add CLI options:
   - `--enable-defense`
   - `--defense-config <path>`
   - `--defense-archive-format jsonl|sqlite`
2. Before model call: run input + interaction pre-check.
3. After model response: run output check and final content substitution.
4. Ensure blocked cases are still logged with defense decision metadata.
5. Add failing integration tests for:
   - defense disabled (baseline behavior unchanged)
   - defense enabled and block/rewrite paths
6. Run integration tests and verify PASS.

### Task 6: Compatibility adapter for future attack scripts

**Files:**
- Modify: `defense_mode/engine.py`
- Create: `defense_mode/interfaces.py` (adapter protocol section)
- Create: `docs/plans/2026-03-07-defense-integration-guide.md`

1. Define script-agnostic adapter API:
   - `build_context_from_case(case, model_name, round_idx)`
   - `apply_pre_call_defense(context)`
   - `apply_post_call_defense(context, response)`
2. Add unit tests for adapter behavior using synthetic attack-script payloads.
3. Write integration guide for adding defense to new scripts in <30 LOC.

### Task 7: End-to-end verification

**Files:**
- Verify modified files and tests.

1. Run targeted defense tests:
   - `python3 -m unittest tests.test_defense_engine tests.test_defense_input_layer tests.test_defense_interaction_layer tests.test_defense_output_layer -v`
2. Run attack flow smoke tests:
   - `python3 -m unittest tests.test_jailbreak_cli_smoke -v`
3. Run selected existing resilience tests:
   - `python3 -m unittest tests.test_jailbreak_resilience -v`
4. Record exact command outputs before claiming completion.

---

## Configuration Sketch

`defense_config.yaml` fields:
- `enabled_layers`: `input|interaction|output`
- `input`: rule list, score thresholds, rewrite template set, classifier backend
- `interaction`: state thresholds, max risk rounds, truncation policy
- `output`: detection thresholds, redact policy, refuse templates
- `archive`: format (`jsonl` or `sqlite`), path, include_full_context

---

## Milestones

1. `M1`: Core engine + contracts + input layer.
2. `M2`: Interaction + output layer + archive.
3. `M3`: `single_jail.py` integration + compatibility adapter + docs.

