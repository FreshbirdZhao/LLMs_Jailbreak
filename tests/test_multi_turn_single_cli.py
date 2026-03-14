import unittest

from Jailbreak.jailbreak_tools.single_jail.single_jail import build_parser


class MultiTurnSingleCliTest(unittest.TestCase):
    def test_parser_defaults_to_six_rounds(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--models",
                "demo",
                "--dataset",
                "data.json",
                "--output-dir",
                "out",
            ]
        )

        self.assertEqual(args.max_rounds, 6)

    def test_parser_accepts_defense_flags(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--models",
                "demo",
                "--dataset",
                "data.json",
                "--output-dir",
                "out",
                "--enable-defense",
                "--defense-config",
                "defense.yaml",
                "--defense-archive-format",
                "jsonl",
            ]
        )

        self.assertTrue(args.enable_defense)
        self.assertEqual(args.defense_config, "defense.yaml")
        self.assertEqual(args.defense_archive_format, "jsonl")

    def test_parser_accepts_runtime_reliability_flags(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--models",
                "demo",
                "--dataset",
                "data.json",
                "--output-dir",
                "out",
                "--resume",
                "--autosave-interval",
                "10",
                "--concurrency",
                "3",
            ]
        )

        self.assertTrue(args.resume)
        self.assertEqual(args.autosave_interval, 10)
        self.assertEqual(args.concurrency, 3)


if __name__ == "__main__":
    unittest.main()
