from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class TestSingleJailEntrypoint(unittest.TestCase):
    def test_script_runs_help_without_import_error(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "Jailbreak" / "jailbreak_tools" / "single_jail.py"

        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            proc.returncode,
            0,
            msg=f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}",
        )
        self.assertNotIn("No module named 'Defense.jailbreak_defense'", proc.stderr)


if __name__ == "__main__":
    unittest.main()
