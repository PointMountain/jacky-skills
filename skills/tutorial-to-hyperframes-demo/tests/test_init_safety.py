from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_RUN = SKILL_ROOT / "scripts" / "init_run.py"


class InitSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        (self.repo / "demos").mkdir(parents=True)
        self.source = Path(self.tempdir.name) / "private tutorial.mp4"
        self.source.write_bytes(b"private-media")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cli(
        self,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INIT_RUN), *map(str, args)],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=env,
        )

    def start(self, run_id: str = "safe-run") -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "start",
            "--repo",
            str(self.repo),
            "--run-id",
            run_id,
            "--source",
            str(self.source),
            "--json",
        )

    def init_git(self, gitignore: str) -> None:
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )
        (self.repo / ".gitignore").write_text(gitignore, encoding="utf-8")

    def test_git_repo_blocks_before_private_write_when_either_path_is_not_ignored(
        self,
    ) -> None:
        cases = (
            ("/.learning/runs/\n", ".learning.lock", "/.learning.lock"),
            ("/.learning.lock\n", ".learning/runs/safe-run", "/.learning/runs/"),
        )
        for gitignore, missing_path, repair_rule in cases:
            with self.subTest(missing_path=missing_path):
                with tempfile.TemporaryDirectory() as root:
                    repo = Path(root) / "repo"
                    (repo / "demos").mkdir(parents=True)
                    subprocess.run(
                        ["git", "init", "-q"],
                        cwd=repo,
                        check=True,
                        text=True,
                        capture_output=True,
                    )
                    (repo / ".gitignore").write_text(gitignore, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(INIT_RUN),
                            "start",
                            "--repo",
                            str(repo),
                            "--run-id",
                            "safe-run",
                            "--source",
                            str(self.source),
                        ],
                        cwd=repo,
                        text=True,
                        capture_output=True,
                    )

                    self.assertEqual(result.returncode, 2)
                    self.assertIn(missing_path, result.stderr)
                    self.assertIn(repair_rule, result.stderr)
                    self.assertFalse((repo / ".learning").exists())
                    self.assertFalse((repo / ".learning.lock").exists())

    def test_git_repo_starts_only_after_both_private_paths_are_ignored(self) -> None:
        self.init_git("/.learning/runs/\n/.learning.lock\n")

        result = self.start()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.repo / ".learning" / "runs" / "safe-run" / "run.json").is_file()
        )

    def test_non_git_temp_repo_bootstraps_future_ignore_rules(self) -> None:
        self.assertFalse((self.repo / ".git").exists())

        result = self.start()

        self.assertEqual(result.returncode, 0, result.stderr)
        gitignore = (self.repo / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.learning/runs/", gitignore.splitlines())
        self.assertIn("/.learning.lock", gitignore.splitlines())
        self.assertTrue(
            (self.repo / ".learning" / "runs" / "safe-run" / "run.json").is_file()
        )

    def test_non_git_bootstrap_moves_authoritative_rules_after_negations(self) -> None:
        gitignore_path = self.repo / ".gitignore"
        gitignore_path.write_text(
            "\n".join(
                [
                    "/.learning/runs/",
                    "/.learning.lock",
                    "!/.learning/runs/",
                    "!/.learning/runs/**",
                    "!/.learning.lock",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        first = self.start("negated-run")

        self.assertEqual(first.returncode, 0, first.stderr)
        rewritten = gitignore_path.read_text(encoding="utf-8")
        self.assertTrue(
            rewritten.endswith(
                "# >>> tutorial-to-hyperframes-demo private state >>>\n"
                "/.learning/runs/\n"
                "/.learning.lock\n"
                "# <<< tutorial-to-hyperframes-demo private state <<<\n"
            )
        )

        second = self.start("second-run")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(gitignore_path.read_text(encoding="utf-8"), rewritten)

        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )
        for candidate in (
            ".learning/runs/negated-run/run.json",
            ".learning/runs/second-run/run.json",
            ".learning.lock",
        ):
            with self.subTest(candidate=candidate):
                ignored = subprocess.run(
                    ["git", "check-ignore", "-q", "--", candidate],
                    cwd=self.repo,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(ignored.returncode, 0, candidate)

        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        self.assertNotIn(".learning/runs/", status)

    def test_non_git_bootstrap_closes_nested_learning_negation(self) -> None:
        learning = self.repo / ".learning"
        learning.mkdir()
        nested_ignore = learning / ".gitignore"
        original_nested = "# 用户规则\n!runs/\n!runs/**\n"
        nested_ignore.write_text(original_nested, encoding="utf-8")

        first = self.start("nested-negation")

        self.assertEqual(first.returncode, 0, first.stderr)
        rewritten = nested_ignore.read_text(encoding="utf-8")
        self.assertIn(original_nested.rstrip(), rewritten)
        self.assertTrue(
            rewritten.endswith(
                "# >>> tutorial-to-hyperframes-demo private runs >>>\n"
                "/runs/\n"
                "# <<< tutorial-to-hyperframes-demo private runs <<<\n"
            )
        )

        second = self.start("nested-second")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(nested_ignore.read_text(encoding="utf-8"), rewritten)

        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )
        for candidate in (
            ".learning/runs/nested-negation/run.json",
            ".learning/runs/nested-second/run.json",
            ".learning.lock",
        ):
            with self.subTest(candidate=candidate):
                ignored = subprocess.run(
                    ["git", "check-ignore", "-q", "--", candidate],
                    cwd=self.repo,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(ignored.returncode, 0, candidate)

        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        self.assertNotIn(".learning/runs/", status)

    def test_bind_retry_adopts_same_number_after_sigkill_following_mkdir(self) -> None:
        started = self.start("crash-run")
        self.assertEqual(started.returncode, 0, started.stderr)
        run_path = self.repo / ".learning" / "runs" / "crash-run" / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["completed_stages"] = [
            "preflight",
            "ingest",
            "transcript",
            "learn_method",
            "observe_motion",
            "plan_demo",
        ]
        run_path.write_text(json.dumps(run), encoding="utf-8")

        command = (
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "crash-run",
            "--slug",
            "recoverable-demo",
            "--json",
        )
        fault_env = os.environ.copy()
        fault_env["TUTORIAL_TO_HYPERFRAMES_FAULT"] = "kill_after_demo_mkdir"

        crashed = self.run_cli(*command, env=fault_env)

        self.assertEqual(crashed.returncode, -9)
        target = self.repo / "demos" / "01-recoverable-demo"
        self.assertTrue(target.is_dir())
        self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(
            json.loads(run_path.read_text(encoding="utf-8"))["bindings"], []
        )
        run_dir = run_path.parent
        self.assertTrue((run_dir / "binding-intent.json").is_file())

        retried = self.run_cli(*command)

        self.assertEqual(retried.returncode, 0, retried.stderr)
        output = json.loads(retried.stdout)
        self.assertEqual(output["number"], 1)
        self.assertEqual(output["demo_dir"], "demos/01-recoverable-demo")
        self.assertEqual(
            json.loads(run_path.read_text(encoding="utf-8"))["bindings"][0]["number"],
            1,
        )
        intent = json.loads(
            (run_dir / "binding-intent.json").read_text(encoding="utf-8")
        )
        owner = json.loads(
            (run_dir / "binding-owner.json").read_text(encoding="utf-8")
        )
        self.assertEqual(intent["status"], "committed")
        self.assertEqual(owner["status"], "committed")
        self.assertEqual(intent["token"], owner["token"])


if __name__ == "__main__":
    unittest.main()
