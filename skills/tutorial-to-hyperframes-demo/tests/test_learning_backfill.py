from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


TESTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_ROOT))

import test_run_contract as run_contract  # noqa: E402


SKILL_ROOT = Path(__file__).resolve().parents[1]
RECORD = SKILL_ROOT / "scripts" / "record_learning.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_run.py"
WORKFLOW_V1 = SKILL_ROOT / "references" / "workflows" / "1.0.0.json"
STAGES = run_contract.STAGES


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LegacyBackfillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = run_contract.ValidateRunTests(methodName="runTest")
        self.fixture.setUp()
        self.fixture.make_valid_run()
        self.repo = self.fixture.repo
        self.run_id = "valid-run"
        self.run_dir = self.fixture.run_dir
        self.run_path = self.run_dir / "run.json"
        run = self.read_run()
        workflow_hash = digest(WORKFLOW_V1)
        run["workflow_version"] = "1.0.0"
        run["workflow_sha256"] = workflow_hash
        run.pop("extensions", None)
        for descriptor in run["artifacts"].values():
            descriptor["workflow_version"] = "1.0.0"
            descriptor["workflow_sha256"] = workflow_hash
        self.write_run(run)

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def read_run(self) -> dict:
        return json.loads(self.run_path.read_text(encoding="utf-8"))

    def write_run(self, value: dict) -> None:
        self.run_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def cli(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RECORD),
                "backfill",
                "--repo",
                str(self.repo),
                "--run-id",
                self.run_id,
                "--json",
            ],
            text=True,
            capture_output=True,
            env=self.fixture.cli_env,
        )

    def validate(self, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATE),
                "--repo",
                str(self.repo),
                "--run-id",
                self.run_id,
                "--ffprobe",
                "off",
                "--json",
                *extra,
            ],
            text=True,
            capture_output=True,
            env=self.fixture.cli_env,
        )
        return result, json.loads(result.stdout)

    def file_snapshot(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.run_dir).as_posix(): path.read_bytes()
            for path in self.run_dir.rglob("*")
            if path.is_file()
        }

    def test_rejects_incomplete_or_non_legacy_run_without_writes(self) -> None:
        run = self.read_run()
        run.update(
            {
                "status": "running",
                "completed_stages": STAGES[:-1],
                "current_stage": "finalize",
                "next_stage": None,
            }
        )
        self.write_run(run)
        before = self.file_snapshot()
        incomplete = self.cli()
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertIn("completed", incomplete.stderr.lower())
        self.assertEqual(self.file_snapshot(), before)

        self.setUp_legacy_completed_again()
        run = self.read_run()
        run["workflow_version"] = "1.1.0"
        self.write_run(run)
        non_legacy = self.cli()
        self.assertNotEqual(non_legacy.returncode, 0)
        self.assertIn("1.0", non_legacy.stderr)

    def setUp_legacy_completed_again(self) -> None:
        run = self.read_run()
        run.update(
            {
                "status": "completed",
                "completed_stages": list(STAGES),
                "current_stage": "finalize",
                "next_stage": None,
            }
        )
        self.write_run(run)

    def test_backfill_is_historical_idempotent_and_preserves_old_bytes(self) -> None:
        core_before, core_payload = self.validate("--core-only")
        self.assertEqual(core_before.returncode, 0, core_payload)
        before = self.file_snapshot()
        final_path = self.run_dir / self.read_run()["artifacts"]["finalize"]["path"]
        final_hash = digest(final_path)

        first = self.cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        first_payload = json.loads(first.stdout)
        self.assertFalse(first_payload["reused"])
        run = self.read_run()
        extension = run["extensions"]["learning_loop"]
        self.assertEqual(extension["state"], "backfilled")
        self.assertEqual(extension["selection"]["path"], "memory-selection.json")
        self.assertFalse((self.repo / ".learning" / "local").exists())
        self.assertEqual(digest(final_path), final_hash)

        old_paths = set(before) - {"run.json"}
        after_first = self.file_snapshot()
        self.assertEqual(
            {path: after_first[path] for path in old_paths},
            {path: before[path] for path in old_paths},
        )
        events = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((self.run_dir / "usage-events").glob("*.json"))
        ]
        self.assertTrue(events)
        for event in events:
            if event["kind"] in {"skill", "tool"}:
                self.assertEqual(event["result"], "not_recorded")
                self.assertEqual(event["capture_state"], "not_recorded")
                self.assertIsNone(event["version"])
                self.assertIsNone(event["execution_receipt"])

        frozen_snapshot = self.file_snapshot()
        second = self.cli()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(json.loads(second.stdout)["reused"])
        self.assertEqual(self.file_snapshot(), frozen_snapshot)

        required, payload = self.validate("--require-learning-memory")
        self.assertEqual(required.returncode, 0, payload)

    def test_extension_error_never_invalidates_valid_core(self) -> None:
        first = self.cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        run = self.read_run()
        run["extensions"]["learning_loop"]["sidecars"][
            "retrospective.json"
        ]["sha256"] = "f" * 64
        self.write_run(run)
        before = self.read_run()

        result, payload = self.validate("--apply-invalidation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(payload["invalidated_from"])
        self.assertEqual(payload["invalidated_stages"], [])
        self.assertEqual(self.read_run(), before)


if __name__ == "__main__":
    unittest.main()
