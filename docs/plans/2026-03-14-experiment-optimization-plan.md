# Experiment Project Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the Experiment project with a bounded optimization pass focused on safety nets, runtime reliability, and a shared LLM access layer without entering large structural refactors.

**Architecture:** This plan is intentionally capped at boundary 2: `Phase 0 + Phase 1 + Phase 2`. The work starts by establishing regression coverage around the highest-risk workflows, then normalizes timeout/retry/recovery behavior across `Redteam`, `Jailbreak`, and `Analyze`, and finally extracts a shared LLM access layer so model/provider behavior is no longer duplicated. External CLI behavior should remain stable during this plan.

**Tech Stack:** Python 3.12, `unittest`, existing Bash runners, `httpx`, `urllib`, YAML-based model registry, Ollama, OpenAI-compatible APIs.

---

### Task 1: Create The Plan Skeleton And Test Inventory

**Files:**
- Create: `docs/plans/2026-03-14-experiment-optimization-plan.md`
- Create: `tests/__init__.py`
- Create: `tests/test_loader.py`
- Create: `tests/test_analyze_pipeline.py`
- Create: `tests/test_defense_engine.py`
- Modify: `tests/test_analyze_runner.py`

**Step 1: Write the failing test for Loader normalization**

```python
import unittest

from Jailbreak.jailbreak_tools.loader import Loader


class LoaderTest(unittest.TestCase):
    def test_normalize_case_prefers_existing_ids_and_prompt_aliases(self):
        loader = Loader()
        case = loader._normalize_case(
            {"test_id": "42", "query": "hello", "type": "cat", "method": "attack"},
            fallback_id="9",
        )
        self.assertEqual(case["id"], "jb_42")
        self.assertEqual(case["prompt"], "hello")
        self.assertEqual(case["category"], "cat")
        self.assertEqual(case["attack_type"], "attack")
```

**Step 2: Run test to verify it passes or fails for the expected reason**

Run: `python3 -m unittest tests.test_loader.LoaderTest.test_normalize_case_prefers_existing_ids_and_prompt_aliases`

Expected: If `tests/` is missing, import/setup should fail first. Fix test layout before moving on.

**Step 3: Write the failing test for Analyze checkpoint resume**

```python
import tempfile
import unittest
from pathlib import Path

from Analyze.pipeline import evaluate_records


class _FakeJudge:
    def __init__(self):
        self.calls = 0

    def judge(self, response):
        self.calls += 1
        from Analyze.schema import JudgeDecision
        return JudgeDecision(
            is_jailbreak="no",
            risk_level=0,
            evidence_spans=[],
            reasoning_tags=[],
            judge_source="fake",
            raw_judge_output={},
        )


class AnalyzeResumeTest(unittest.TestCase):
    def test_resume_skips_previously_written_rows(self):
        with tempfile.TemporaryDirectory() as td:
            input_dir = Path(td) / "input"
            input_dir.mkdir()
            (input_dir / "a.jsonl").write_text('{"response":"x"}\n{"response":"y"}\n', encoding="utf-8")
            out_dir = Path(td) / "out"
            judge = _FakeJudge()
            evaluate_records(input_dir, judge, judge, checkpoint_dir=out_dir, resume=True)
            judge.calls = 0
            evaluate_records(input_dir, judge, judge, checkpoint_dir=out_dir, resume=True)
            self.assertEqual(judge.calls, 0)
```

**Step 4: Run test to verify it fails or exposes missing setup**

Run: `python3 -m unittest tests.test_analyze_pipeline.AnalyzeResumeTest.test_resume_skips_previously_written_rows`

Expected: RED if test or packaging is incomplete.

**Step 5: Write the failing test for DefenseEngine hook ordering**

```python
import unittest

from Defense.defense_mode.engine import DefenseEngine
from Defense.defense_mode.types import DefenseAction, DefenseDecision


class _Module:
    def __init__(self, name, action=DefenseAction.ALLOW):
        self.name = name
        self.action = action
        self.calls = []

    def process(self, context):
        self.calls.append(self.name)
        return DefenseDecision(action=self.action, risk_level=0)


class DefenseEngineTest(unittest.TestCase):
    def test_pre_and_post_hooks_run_in_expected_order(self):
        input_module = _Module("input")
        interaction_module = _Module("interaction")
        output_module = _Module("output")
        engine = DefenseEngine(input_module, interaction_module, output_module)
        ctx = engine.build_context_from_case({"id": "1", "prompt": "p"}, model_name="m")
        engine.apply_pre_call_defense(ctx)
        engine.apply_post_call_defense(ctx, "resp")
        self.assertEqual(ctx.decision_history[0]["layer"], "input")
        self.assertEqual(ctx.decision_history[1]["layer"], "interaction_pre")
        self.assertEqual(ctx.decision_history[2]["layer"], "output")
        self.assertEqual(ctx.decision_history[3]["layer"], "interaction_post")
```

**Step 6: Run test to verify it passes or fails for the expected reason**

Run: `python3 -m unittest tests.test_defense_engine.DefenseEngineTest.test_pre_and_post_hooks_run_in_expected_order`

Expected: If current behavior diverges, keep the test and fix code in later tasks.

**Step 7: Commit**

```bash
git add docs/plans/2026-03-14-experiment-optimization-plan.md tests/__init__.py tests/test_loader.py tests/test_analyze_pipeline.py tests/test_defense_engine.py tests/test_analyze_runner.py
git commit -m "test: add optimization baseline coverage"
```


### Task 2: Stabilize Test Packaging And Shared Test Utilities

**Files:**
- Create: `tests/common.py`
- Modify: `tests/test_loader.py`
- Modify: `tests/test_analyze_pipeline.py`
- Modify: `tests/test_defense_engine.py`
- Modify: `tests/test_analyze_runner.py`

**Step 1: Write the failing test for shared temporary project setup**

```python
import unittest

from tests.common import make_temp_project_root


class TestCommonTest(unittest.TestCase):
    def test_make_temp_project_root_returns_existing_directory(self):
        temp_ctx, root = make_temp_project_root()
        try:
            self.assertTrue(root.exists())
            self.assertTrue(root.is_dir())
        finally:
            temp_ctx.cleanup()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.common`

Expected: RED because helper does not exist yet.

**Step 3: Write minimal helper implementation**

```python
import tempfile
from pathlib import Path


def make_temp_project_root():
    temp_ctx = tempfile.TemporaryDirectory()
    return temp_ctx, Path(temp_ctx.name)
```

**Step 4: Run all current tests**

Run: `python3 -m unittest tests.test_loader tests.test_analyze_pipeline tests.test_defense_engine tests.test_analyze_runner`

Expected: PASS, or reveal remaining packaging gaps that must be fixed before runtime work.

**Step 5: Commit**

```bash
git add tests/common.py tests/test_loader.py tests/test_analyze_pipeline.py tests/test_defense_engine.py tests/test_analyze_runner.py
git commit -m "test: stabilize experiment test package"
```


### Task 3: Add A Shared Runtime Retry Policy Contract

**Files:**
- Create: `common/__init__.py`
- Create: `common/runtime.py`
- Test: `tests/test_runtime_config.py`

**Step 1: Write the failing test for runtime retry policy defaults**

```python
import unittest

from common.runtime import RetryPolicy


class RetryPolicyTest(unittest.TestCase):
    def test_retry_policy_clamps_invalid_values(self):
        policy = RetryPolicy(timeout=0, max_retries=-2, retry_backoff=-1)
        self.assertEqual(policy.timeout, 1)
        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.retry_backoff, 0.0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_runtime_config.RetryPolicyTest.test_retry_policy_clamps_invalid_values`

Expected: RED because module does not exist yet.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    timeout: int = 30
    max_retries: int = 0
    retry_backoff: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "timeout", max(1, int(self.timeout)))
        object.__setattr__(self, "max_retries", max(0, int(self.max_retries)))
        object.__setattr__(self, "retry_backoff", max(0.0, float(self.retry_backoff)))
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_runtime_config`

Expected: PASS

**Step 5: Commit**

```bash
git add common/__init__.py common/runtime.py tests/test_runtime_config.py
git commit -m "feat: add shared runtime retry policy"
```


### Task 4: Harden Analyze External Provider Retry Behavior

**Files:**
- Modify: `Analyze/llm_clients.py`
- Test: `tests/test_analyze_llm_clients.py`

**Step 1: Write the failing test for external transient retry**

```python
import unittest
from unittest.mock import patch
from urllib import error

from Analyze.llm_clients import ExternalAPIClient


class ExternalClientTest(unittest.TestCase):
    def test_external_client_retries_transient_errors(self):
        client = ExternalAPIClient(model="x", timeout=1, max_retries=1, retry_backoff=0.0)
        responses = [error.URLError("timeout"), object()]

        def _fake_urlopen(req, timeout):
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            class _Resp:
                def __enter__(self): return self
                def __exit__(self, exc_type, exc, tb): return False
                def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'
            return _Resp()

        with patch("Analyze.llm_clients.request.urlopen", side_effect=_fake_urlopen):
            self.assertEqual(client.complete("p"), "ok")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_analyze_llm_clients.ExternalClientTest.test_external_client_retries_transient_errors`

Expected: RED because `ExternalAPIClient` does not yet retry.

**Step 3: Write minimal implementation**

Implement in `Analyze/llm_clients.py`:
- add `max_retries` and `retry_backoff` fields to `ExternalAPIClient`
- add transient error detection reuse or shared helper
- loop retries in `complete()`

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_analyze_llm_clients`

Expected: PASS

**Step 5: Commit**

```bash
git add Analyze/llm_clients.py tests/test_analyze_llm_clients.py
git commit -m "fix: add retry handling for external analyze client"
```


### Task 5: Centralize Retry Policy Use In Analyze

**Files:**
- Modify: `Analyze/llm_clients.py`
- Modify: `Analyze/cli.py`
- Test: `tests/test_analyze_llm_clients.py`

**Step 1: Write the failing test for build_llm_client policy propagation**

```python
import unittest

from Analyze.llm_clients import build_llm_client, ExternalAPIClient


class BuildClientTest(unittest.TestCase):
    def test_build_llm_client_passes_retry_settings_to_external_client(self):
        client = build_llm_client(
            {
                "provider": "external",
                "model": "m",
                "timeout": 12,
                "max_retries": 3,
                "retry_backoff": 2.5,
            }
        )
        self.assertIsInstance(client, ExternalAPIClient)
        self.assertEqual(client.timeout, 12)
        self.assertEqual(client.max_retries, 3)
        self.assertEqual(client.retry_backoff, 2.5)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_analyze_llm_clients.BuildClientTest.test_build_llm_client_passes_retry_settings_to_external_client`

Expected: RED until builder and dataclass are aligned.

**Step 3: Write minimal implementation**

Ensure `build_llm_client()` passes the shared retry policy inputs to both provider types.

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_analyze_llm_clients`

Expected: PASS

**Step 5: Commit**

```bash
git add Analyze/llm_clients.py Analyze/cli.py tests/test_analyze_llm_clients.py
git commit -m "refactor: centralize analyze retry policy wiring"
```


### Task 6: Introduce Shared LLM Config Resolution Layer

**Files:**
- Create: `common/llm/__init__.py`
- Create: `common/llm/config.py`
- Test: `tests/test_shared_llm_config.py`

**Step 1: Write the failing test for normalized provider config**

```python
import unittest

from common.llm.config import normalize_provider_config


class SharedLLMConfigTest(unittest.TestCase):
    def test_normalize_provider_config_fills_provider_defaults(self):
        cfg = normalize_provider_config(
            {
                "provider": "external",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "timeout": 20,
            }
        )
        self.assertEqual(cfg["provider"], "external")
        self.assertEqual(cfg["timeout"], 20)
        self.assertIn("max_retries", cfg)
        self.assertIn("retry_backoff", cfg)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_shared_llm_config.SharedLLMConfigTest.test_normalize_provider_config_fills_provider_defaults`

Expected: RED because shared module does not exist yet.

**Step 3: Write minimal implementation**

```python
def normalize_provider_config(raw):
    return {
        "provider": str(raw.get("provider", "ollama")).lower(),
        "model": str(raw.get("model", "")).strip(),
        "base_url": str(raw.get("base_url", "")).strip(),
        "api_key": str(raw.get("api_key", "")).strip(),
        "timeout": max(1, int(raw.get("timeout", 30))),
        "max_retries": max(0, int(raw.get("max_retries", 0))),
        "retry_backoff": max(0.0, float(raw.get("retry_backoff", 0.0))),
    }
```

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_shared_llm_config`

Expected: PASS

**Step 5: Commit**

```bash
git add common/llm/__init__.py common/llm/config.py tests/test_shared_llm_config.py
git commit -m "feat: add shared llm config normalization"
```


### Task 7: Rewire Analyze To Use Shared LLM Config Normalization

**Files:**
- Modify: `Analyze/llm_clients.py`
- Modify: `Analyze/cli.py`
- Test: `tests/test_shared_llm_config.py`
- Test: `tests/test_analyze_llm_clients.py`

**Step 1: Write the failing test for Analyze builder using shared normalization**

```python
import unittest

from Analyze.llm_clients import build_llm_client


class AnalyzeBuilderIntegrationTest(unittest.TestCase):
    def test_build_llm_client_accepts_sparse_input_and_normalizes_it(self):
        client = build_llm_client({"provider": "ollama", "model": "qwen2:latest"})
        self.assertEqual(client.provider_name, "ollama")
        self.assertEqual(client.base_url, "http://127.0.0.1:11434")
```

**Step 2: Run test to verify behavior**

Run: `python3 -m unittest tests.test_analyze_llm_clients.AnalyzeBuilderIntegrationTest.test_build_llm_client_accepts_sparse_input_and_normalizes_it`

Expected: If already green, keep the test as regression and still migrate internals to shared normalization.

**Step 3: Write minimal implementation**

Replace ad hoc config extraction in `Analyze/llm_clients.py` with the shared normalization helper.

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_shared_llm_config tests.test_analyze_llm_clients`

Expected: PASS

**Step 5: Commit**

```bash
git add Analyze/llm_clients.py Analyze/cli.py common/llm/config.py tests/test_shared_llm_config.py tests/test_analyze_llm_clients.py
git commit -m "refactor: route analyze client config through shared llm layer"
```


### Task 8: Rewire Redteam To Use Shared LLM Config Normalization

**Files:**
- Modify: `Redteam/redteam_llm/clients.py`
- Modify: `Redteam/redteam_llm/surrogate_model.py`
- Test: `tests/test_redteam_clients.py`

**Step 1: Write the failing test for redteam client config normalization**

```python
import unittest

from Redteam.redteam_llm.clients import ClientConfig


class RedteamClientConfigTest(unittest.TestCase):
    def test_client_config_uses_safe_default_timeout(self):
        cfg = ClientConfig(timeout_s=0)
        self.assertGreaterEqual(cfg.timeout_s, 1.0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_redteam_clients.RedteamClientConfigTest.test_client_config_uses_safe_default_timeout`

Expected: RED unless validation already exists.

**Step 3: Write minimal implementation**

Add config normalization or dataclass clamping so `Redteam` uses the shared policy expectations and safe defaults.

**Step 4: Run targeted tests**

Run: `python3 -m unittest tests.test_redteam_clients`

Expected: PASS

**Step 5: Commit**

```bash
git add Redteam/redteam_llm/clients.py Redteam/redteam_llm/surrogate_model.py tests/test_redteam_clients.py
git commit -m "refactor: align redteam client config with shared llm policy"
```


### Task 9: Rewire Jailbreak Model Calls Through Shared Config Helpers

**Files:**
- Modify: `Jailbreak/jailbreak_tools/single_jail.py`
- Test: `tests/test_single_jail_runtime.py`

**Step 1: Write the failing test for normalized model config usage**

```python
import unittest

from Jailbreak.jailbreak_tools.single_jail import ModelTester


class JailbreakRuntimeTest(unittest.TestCase):
    def test_extract_round_idx_defaults_to_one(self):
        self.assertEqual(ModelTester._extract_round_idx({}), 1)
```

**Step 2: Add a second failing test for consistent timeout/retry wiring**

```python
import unittest


class JailbreakRetryPolicyTest(unittest.TestCase):
    def test_model_tester_keeps_retry_limit_non_negative(self):
        tester = ModelTester(
            "models.yaml",
            timeout=30,
            concurrency=1,
            retry_limit=-2,
            autosave_interval=0,
            resume=False,
            retry_backoff_base=1.0,
            retry_backoff_cap=5.0,
        )
        self.assertGreaterEqual(tester.retry_limit, 0)
```

**Step 3: Run targeted tests**

Run: `python3 -m unittest tests.test_single_jail_runtime`

Expected: RED if runtime guardrails are missing.

**Step 4: Write minimal implementation**

Normalize `timeout`, `retry_limit`, `retry_backoff_base`, and `retry_backoff_cap` at construction time and route model resolution through the shared config helpers where useful.

**Step 5: Run targeted tests**

Run: `python3 -m unittest tests.test_single_jail_runtime`

Expected: PASS

**Step 6: Commit**

```bash
git add Jailbreak/jailbreak_tools/single_jail.py tests/test_single_jail_runtime.py
git commit -m "refactor: add runtime guardrails for jailbreak execution"
```


### Task 10: Full Boundary-2 Verification

**Files:**
- Verify modified files and tests only

**Step 1: Run focused test suite**

Run:

```bash
python3 -m unittest \
  tests.test_loader \
  tests.test_analyze_pipeline \
  tests.test_defense_engine \
  tests.test_analyze_runner \
  tests.test_runtime_config \
  tests.test_analyze_llm_clients \
  tests.test_shared_llm_config \
  tests.test_redteam_clients \
  tests.test_single_jail_runtime
```

Expected: PASS

**Step 2: Run syntax verification**

Run:

```bash
python3 -m py_compile \
  Analyze/*.py \
  Analyze/judges/*.py \
  Redteam/redteam_llm/*.py \
  Jailbreak/jailbreak_tools/*.py \
  Defense/defense_mode/*.py \
  common/*.py \
  common/llm/*.py
```

Expected: PASS

**Step 3: Record exact outputs in implementation notes**

Save a concise summary of:
- which tests were added
- which modules were rewired
- any behavior intentionally left unchanged

**Step 4: Commit**

```bash
git add Analyze Redteam Jailbreak Defense common tests
git commit -m "refactor: complete boundary-2 experiment optimization pass"
```

