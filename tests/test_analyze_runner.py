import os
import shutil
import stat
import subprocess
import textwrap
import unittest
from pathlib import Path

from tests.common import make_temp_project_root


REPO_ROOT = Path("/home/jellyz/Experiment")
ANALYZE_SCRIPT = REPO_ROOT / "Jelly_Z/bin/analyze"
OLLAMA_UTILS = REPO_ROOT / "Jelly_Z/bin/ollama_utils.sh"
MODEL_REGISTRY = REPO_ROOT / "model_registry.py"


class AnalyzeRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir, self.root = make_temp_project_root()
        self.project_root = self.root / "project"
        (self.project_root / "Jelly_Z/bin").mkdir(parents=True)
        (self.project_root / "Jailbreak/jailbreak_results").mkdir(parents=True)
        (self.project_root / "Defense/defense_results/all_layers").mkdir(parents=True)
        (self.project_root / "Results").mkdir(parents=True)

        shutil.copy2(ANALYZE_SCRIPT, self.project_root / "Jelly_Z/bin/analyze")
        shutil.copy2(OLLAMA_UTILS, self.project_root / "Jelly_Z/bin/ollama_utils.sh")
        shutil.copy2(MODEL_REGISTRY, self.project_root / "model_registry.py")

        (self.project_root / "models.yaml").write_text(
            textwrap.dedent(
                """
                commercial:
                  - name: deepseek-chat
                    type: openai_compatible
                    provider: external
                    base_url: https://api.deepseek.com
                    model: deepseek-chat
                    api_key_env: DEEPSEEK_API_KEY
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (self.project_root / "Jailbreak/jailbreak_results/sample.jsonl").write_text(
            '{"response":"x"}\n', encoding="utf-8"
        )

        self.stub_state = self.root / "analyze_attempts.txt"
        self.stub_state.write_text("0\n", encoding="utf-8")
        self._write_fake_python()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_fake_python(self) -> None:
        fake_python = self.project_root / "Jelly_Z/bin/python"
        real_python = shutil.which("python3") or "/usr/bin/python3"
        script = textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "${{1:-}}" == "-m" && "${{2:-}}" == "Analyze.cli" ]]; then
              state_file="{self.stub_state}"
              attempt="$(cat "$state_file")"
              attempt="$((attempt + 1))"
              printf '%s\\n' "$attempt" > "$state_file"
              if [[ "$attempt" == "1" ]]; then
                printf 'Traceback (most recent call last):\\nRuntimeError: boom\\n' >&2
                exit 1
              fi
              exit 0
            fi

            exec "{real_python}" "$@"
            """
        )
        fake_python.write_text(script, encoding="utf-8")
        fake_python.chmod(fake_python.stat().st_mode | stat.S_IEXEC)

    def test_llm_retry_hides_traceback_from_terminal(self) -> None:
        env = os.environ.copy()
        env["DEEPSEEK_API_KEY"] = "test-key"

        proc = subprocess.run(
            [str(self.project_root / "Jelly_Z/bin/analyze")],
            input="1\n2\n1\n",
            text=True,
            capture_output=True,
            cwd=self.project_root,
            env=env,
            timeout=15,
        )
        terminal_output = proc.stdout + proc.stderr

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertNotIn("Traceback", terminal_output)
        self.assertIn(
            "⚠ 分析进程异常退出（可能由 Ollama 超时/退出导致），正在重新唤醒服务并断点续跑...",
            terminal_output,
        )
        self.assertEqual(self.stub_state.read_text(encoding="utf-8").strip(), "2")


if __name__ == "__main__":
    unittest.main()
