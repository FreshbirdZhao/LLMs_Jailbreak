from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Defense.jailbreak_defense import (
    InputDefenseModule,
    InteractionDefenseModule,
    OutputDefenseModule,
)
from Defense.jailbreak_defense.input import InputDefenseModule as InputFromNewPkg
from Defense.jailbreak_defense.interaction import InteractionDefenseModule as InteractionFromNewPkg
from Defense.jailbreak_defense.output import OutputDefenseModule as OutputFromNewPkg


class TestDefenseStructureImports(unittest.TestCase):
    def test_new_mode_packages_export_same_classes(self) -> None:
        self.assertIs(InputDefenseModule, InputFromNewPkg)
        self.assertIs(InteractionDefenseModule, InteractionFromNewPkg)
        self.assertIs(OutputDefenseModule, OutputFromNewPkg)

    def test_new_output_package_module_is_instantiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = OutputFromNewPkg(archive_path=Path(tmp) / "audit.jsonl", archive_format="jsonl")
            self.assertIsNotNone(module)


if __name__ == "__main__":
    unittest.main()
