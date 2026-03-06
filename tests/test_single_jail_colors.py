from __future__ import annotations

import sys
import types
import unittest

if "loader" not in sys.modules:
    loader_stub = types.ModuleType("loader")

    class _Loader:  # pragma: no cover - import stub for single_jail module
        pass

    loader_stub.Loader = _Loader
    sys.modules["loader"] = loader_stub

from jailbreak_tools.single_jail import Colors


class TestSingleJailColors(unittest.TestCase):
    def test_bold_wraps_text_with_ansi_sequence(self) -> None:
        self.assertEqual(Colors.bold("x"), f"{Colors.BOLD}x{Colors.RESET}")


if __name__ == "__main__":
    unittest.main()
