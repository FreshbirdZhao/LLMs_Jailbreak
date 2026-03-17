import unittest
from unittest.mock import AsyncMock, patch

from Jailbreak.jailbreak_tools.multi_jail.multi_jail import build_parser, main


class MultiTurnCliTest(unittest.TestCase):
    def test_parser_defaults_to_six_rounds(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--models",
                "demo",
                "--planner-model",
                "planner",
                "--judge-model",
                "judge",
                "--datasets",
                "data.json",
                "--output-dir",
                "out",
            ]
        )

        self.assertEqual(args.max_rounds, 6)
        self.assertEqual(args.judge_mode, "layered_llm")

    def test_parser_accepts_defense_flags(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--models",
                "demo",
                "--planner-model",
                "planner",
                "--judge-model",
                "judge",
                "--datasets",
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
                "--planner-model",
                "planner",
                "--judge-model",
                "judge",
                "--datasets",
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

    def test_parser_requires_planner_and_judge_models(self):
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--models",
                    "demo",
                    "--datasets",
                    "data.json",
                    "--output-dir",
                    "out",
                ]
            )

        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--models",
                    "demo",
                    "--planner-model",
                    "planner",
                    "--datasets",
                    "data.json",
                    "--output-dir",
                    "out",
                ]
            )

    def test_main_builds_runner_with_planner_and_judge_models(self):
        fake_tester = type(
            "FakeTester",
            (),
            {
                "get_models": lambda self, names: [{"name": "target", "model": "target-id", "type": "ollama", "base_url": "http://localhost"}],
                "get_model": lambda self, name: {
                    "name": name,
                    "model": f"{name}-id",
                    "type": "ollama",
                    "base_url": "http://localhost",
                },
                "call_model": AsyncMock(return_value=("ok", 0.1, 200)),
                "aclose": AsyncMock(return_value=None),
                "build_defense_engine": lambda self, config, archive: None,
            },
        )()

        fake_writer = type(
            "FakeWriter",
            (),
            {
                "__init__": lambda self, *args, **kwargs: setattr(self, "init_kwargs", kwargs),
                "write_async": AsyncMock(return_value=None),
                "fsync_async": AsyncMock(return_value=None),
                "close": lambda self: None,
            },
        )

        async def fake_queue(tasks, concurrency, tracker, worker_fn):
            self.assertEqual(concurrency, 1)
            self.assertEqual(len(tasks), 1)

        with (
            patch("sys.argv", ["multi_jail.py", "--models", "target", "--planner-model", "planner", "--judge-model", "judge", "--datasets", "data.csv", "--output-dir", "out"]),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnModelTester", return_value=fake_tester),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.Loader") as loader_cls,
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnResultWriter", fake_writer),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.run_task_queue", new=fake_queue),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.AttackPlanner") as attack_planner_cls,
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.AdaptivePlannerStrategy") as strategy_cls,
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.LayeredJudge") as layered_judge_cls,
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnCaseRunner") as runner_cls,
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=True),
        ):
            loader_cls.return_value.load.return_value = [
                {"id": "jb_1", "name": "case", "prompt": "attack", "category": "c", "attack_type": "a"}
            ]
            runner_cls.return_value = object()

            exit_code = __import__("asyncio").run(main())

        self.assertEqual(exit_code, 0)
        attack_planner_cls.assert_called_once()
        _, attack_planner_kwargs = attack_planner_cls.call_args
        self.assertEqual(attack_planner_kwargs["planner_model"]["name"], "planner")
        strategy_cls.assert_called_once()
        _, strategy_kwargs = strategy_cls.call_args
        self.assertEqual(strategy_kwargs["planner_model"]["name"], "planner")
        layered_judge_cls.assert_called_once()
        _, judge_kwargs = layered_judge_cls.call_args
        self.assertEqual(judge_kwargs["judge_model"]["name"], "judge")
        runner_cls.assert_called_once()
        _, runner_kwargs = runner_cls.call_args
        self.assertIs(runner_kwargs["attack_planner"], attack_planner_cls.return_value)
        self.assertIs(runner_kwargs["followup_strategy"], strategy_cls.return_value)
        self.assertIs(runner_kwargs["judge"], layered_judge_cls.return_value)

    def test_main_keeps_output_path_and_adds_internal_debug_root(self):
        created_writers = []

        class FakeWriter:
            def __init__(self, path, debug_root=None):
                self.path = path
                self.debug_root = debug_root
                created_writers.append(self)

            async def write_async(self, record):
                return None

            async def fsync_async(self):
                return None

            def close(self):
                return None

        fake_tester = type(
            "FakeTester",
            (),
            {
                "get_models": lambda self, names: [{"name": "target", "model": "target-id", "type": "ollama", "base_url": "http://localhost"}],
                "get_model": lambda self, name: {
                    "name": name,
                    "model": f"{name}-id",
                    "type": "ollama",
                    "base_url": "http://localhost",
                },
                "call_model": AsyncMock(return_value=("ok", 0.1, 200)),
                "aclose": AsyncMock(return_value=None),
                "build_defense_engine": lambda self, config, archive: None,
            },
        )()

        async def fake_queue(tasks, concurrency, tracker, worker_fn):
            return None

        with (
            patch("sys.argv", ["multi_jail.py", "--models", "target", "--planner-model", "planner", "--judge-model", "judge", "--datasets", "data.csv", "--output-dir", "out"]),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnModelTester", return_value=fake_tester),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.Loader") as loader_cls,
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnResultWriter", FakeWriter),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.run_task_queue", new=fake_queue),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.AttackPlanner"),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.AdaptivePlannerStrategy"),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.LayeredJudge"),
            patch("Jailbreak.jailbreak_tools.multi_jail.multi_jail.MultiTurnCaseRunner"),
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=True),
        ):
            loader_cls.return_value.load.return_value = [
                {"id": "jb_1", "name": "case", "prompt": "attack", "category": "c", "attack_type": "a"}
            ]
            exit_code = __import__("asyncio").run(main())

        self.assertEqual(exit_code, 0)
        self.assertEqual(str(created_writers[0].path), "out/target_data_multi_turn.jsonl")
        self.assertEqual(str(created_writers[0].debug_root), "Jailbreak/jailbreak_tools/multi_jail/debug_store")


if __name__ == "__main__":
    unittest.main()
