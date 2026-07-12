from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_RUN = SKILL_ROOT / "scripts" / "init_run.py"
VALIDATE_RUN = SKILL_ROOT / "scripts" / "validate_run.py"
WORKFLOWS = SKILL_ROOT / "references" / "workflows"
WORKFLOW_V11 = WORKFLOWS / "1.1.0.json"
WORKFLOW_V10 = WORKFLOWS / "1.0.0.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selection_payload(run_id: str, workflow_version: str = "1.1.0") -> dict:
    return {
        "schema_version": "1.0.0",
        "workflow_version": workflow_version,
        "run_id": run_id,
        "query": {},
        "selected": [],
        "rejected": [],
        "selection_snapshot": [],
        "selection_snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
        "created_at": "2026-07-11T00:00:00Z",
    }


class LearningCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.source = Path(self.tempdir.name) / "source.mp4"
        self.source.write_bytes(b"tutorial-source")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def cli(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )

    def start(self, run_id: str = "new-run") -> dict:
        result = self.cli(
            INIT_RUN,
            "start",
            "--repo",
            str(self.repo),
            "--run-id",
            run_id,
            "--source",
            str(self.source),
            "--source-id",
            f"source-{run_id}",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.read_run(run_id)

    def run_path(self, run_id: str) -> Path:
        return self.repo / ".learning" / "runs" / run_id / "run.json"

    def read_run(self, run_id: str) -> dict:
        return json.loads(self.run_path(run_id).read_text(encoding="utf-8"))

    def write_run(self, run_id: str, run: dict) -> None:
        self.run_path(run_id).write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def validate(self, run_id: str, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = self.cli(
            VALIDATE_RUN,
            "--repo",
            str(self.repo),
            "--run-id",
            run_id,
            "--ffprobe",
            "off",
            "--json",
            *extra,
        )
        return result, json.loads(result.stdout)

    def create_legacy_run(self, run_id: str = "legacy-run") -> dict:
        run_dir = self.repo / ".learning" / "runs" / run_id
        run_dir.mkdir(parents=True)
        media_hash = sha256(self.source)
        run = {
            "schema_version": "1.0.0",
            "workflow_version": "1.0.0",
            "workflow_sha256": sha256(WORKFLOW_V10),
            "run_id": run_id,
            "status": "running",
            "current_stage": "preflight",
            "next_stage": "ingest",
            "completed_stages": [],
            "invalidated_stages": [],
            "source": {
                "kind": "local_file",
                "source_id": f"source-{run_id}",
                "private_locator": str(self.source.resolve()),
                "locator_sha256": hashlib.sha256(
                    str(self.source.resolve()).encode()
                ).hexdigest(),
                "media_sha256": media_hash,
                "fingerprint_state": "verified",
            },
            "artifacts": {},
            "bindings": [],
        }
        self.write_run(run_id, run)
        return run

    def complete_preflight(self, run_id: str = "new-run") -> dict:
        run = self.read_run(run_id)
        artifact = self.run_path(run_id).parent / "preflight.json"
        artifact.write_text(
            json.dumps(
                {
                    "artifact_type": "preflight",
                    "source_readable": True,
                    "source_id": f"source-{run_id}",
                }
            ),
            encoding="utf-8",
        )
        run.update(
            {
                "completed_stages": ["preflight"],
                "current_stage": "ingest",
                "next_stage": "transcript",
                "artifacts": {
                    "preflight": {
                        "path": "preflight.json",
                        "sha256": sha256(artifact),
                        "schema_version": "1.0.0",
                        "workflow_version": "1.1.0",
                        "workflow_sha256": sha256(WORKFLOW_V11),
                        "source_media_sha256": sha256(self.source),
                        "upstream": {},
                    }
                },
            }
        )
        self.write_run(run_id, run)
        return run

    def test_start_defaults_to_v11_and_initializes_collecting_extension(self) -> None:
        run = self.start()
        self.assertEqual(run["workflow_version"], "1.1.0")
        self.assertEqual(run["workflow_sha256"], sha256(WORKFLOW_V11))
        self.assertEqual(
            run["extensions"]["learning_loop"],
            {
                "required": True,
                "state": "collecting",
                "contract_version": "1.0.0",
                "selection": None,
                "sidecars": {},
            },
        )

    def test_legacy_default_passes_but_require_learning_memory_fails(self) -> None:
        self.create_legacy_run()
        default, payload = self.validate("legacy-run")
        self.assertEqual(default.returncode, 0, payload)

        required, payload = self.validate("legacy-run", "--require-learning-memory")
        self.assertNotEqual(required.returncode, 0)
        self.assertIn("learning_loop", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_preflight_completion_requires_real_selection_file_and_hash(self) -> None:
        self.start()
        run = self.complete_preflight()

        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selection", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

        selection = self.run_path("new-run").parent / "memory-selection.json"
        selection.write_text(
            json.dumps(selection_payload("new-run"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        run["extensions"]["learning_loop"]["selection"] = {
            "path": "memory-selection.json",
            "sha256": sha256(selection),
        }
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertEqual(result.returncode, 0, payload)

        run["extensions"]["learning_loop"]["selection"]["sha256"] = "f" * 64
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", "\n".join(payload["errors"]))

        run["extensions"]["learning_loop"]["selection"] = {
            "path": "../memory-selection.json",
            "sha256": sha256(selection),
        }
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("..", "\n".join(payload["errors"]))

    def test_core_only_skips_learning_extension_but_not_core(self) -> None:
        run = self.start()
        run["extensions"]["learning_loop"]["state"] = "broken"
        self.write_run("new-run", run)

        result, payload = self.validate("new-run", "--core-only")
        self.assertEqual(result.returncode, 0, payload)

        run["status"] = "invented"
        self.write_run("new-run", run)
        result, payload = self.validate("new-run", "--core-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status", "\n".join(payload["errors"]))

    def test_unknown_workflow_version_and_hash_fail_closed(self) -> None:
        run = self.start()
        run["workflow_version"] = "9.9.9"
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("workflow", "\n".join(payload["errors"]))

        run = self.start("bad-hash")
        run["workflow_sha256"] = "f" * 64
        self.write_run("bad-hash", run)
        result, payload = self.validate("bad-hash")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash", "\n".join(payload["errors"]))

    def test_unknown_learning_contract_version_fails_closed(self) -> None:
        run = self.start()
        run["extensions"]["learning_loop"]["contract_version"] = "9.9.9"
        self.write_run("new-run", run)

        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_version", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_learning_contract_bytes_must_match_workflow_hash_pin(self) -> None:
        self.start()
        copied_skill = Path(self.tempdir.name) / "copied-skill"
        shutil.copytree(SKILL_ROOT, copied_skill)
        frozen_contract = (
            copied_skill / "references" / "learning-contracts" / "1.0.0.json"
        )
        frozen_contract.write_text(
            frozen_contract.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )

        result = self.cli(
            copied_skill / "scripts" / "validate_run.py",
            "--repo",
            str(self.repo),
            "--run-id",
            "new-run",
            "--ffprobe",
            "off",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract 实际 hash", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_legacy_contract_bytes_are_also_pinned_fail_closed(self) -> None:
        run = self.create_legacy_run()
        run["extensions"] = {
            "learning_loop": {
                "required": True,
                "state": "backfilled",
                "contract_version": "1.0.0",
                "selection": None,
                "sidecars": {},
            }
        }
        self.write_run("legacy-run", run)
        copied_skill = Path(self.tempdir.name) / "copied-legacy-skill"
        shutil.copytree(SKILL_ROOT, copied_skill)
        frozen_contract = (
            copied_skill / "references" / "learning-contracts" / "1.0.0.json"
        )
        frozen_contract.write_text(
            frozen_contract.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )

        result = self.cli(
            copied_skill / "scripts" / "validate_run.py",
            "--repo",
            str(self.repo),
            "--run-id",
            "legacy-run",
            "--ffprobe",
            "off",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract 实际 hash", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_incomplete_legacy_run_cannot_claim_backfilled_learning(self) -> None:
        run = self.create_legacy_run()
        run["extensions"] = {
            "learning_loop": {
                "required": True,
                "state": "backfilled",
                "contract_version": "1.0.0",
                "selection": None,
                "sidecars": {},
            }
        }
        self.write_run("legacy-run", run)

        result, payload = self.validate("legacy-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("legacy", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_sidecar_membership_rejects_rogue_deep_non_json_and_duplicates(self) -> None:
        invalid_paths = [
            "rogue.json",
            "memory-selection.json",
            "usage-events/deep/event.json",
            "usage-events/./event.json",
            "usage-events//event.json",
            "usage-events/.json",
            "usage-events/event.txt",
            "feedback-candidates/deep/item.json",
            "promotion-receipts/item.txt",
        ]
        for index, invalid_path in enumerate(invalid_paths):
            with self.subTest(path=invalid_path):
                run_id = f"membership-{index}"
                run = self.start(run_id)
                sidecar = self.run_path(run_id).parent / invalid_path
                sidecar.parent.mkdir(parents=True, exist_ok=True)
                sidecar.write_text("{}\n", encoding="utf-8")
                run["extensions"]["learning_loop"]["sidecars"] = {
                    invalid_path: {"path": invalid_path, "sha256": sha256(sidecar)}
                }
                self.write_run(run_id, run)

                result, payload = self.validate(run_id)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("sidecar", "\n".join(payload["errors"]))
                self.assertIsNone(payload["invalidated_from"])

    def test_post_run_sidecars_require_terminal_learning_state(self) -> None:
        run = self.start()
        candidate_path = "feedback-candidates/feedback-001.json"
        candidate = self.run_path("new-run").parent / candidate_path
        candidate.parent.mkdir()
        candidate.write_text("{}\n", encoding="utf-8")
        run["extensions"]["learning_loop"]["sidecars"] = {
            candidate_path: {"path": candidate_path, "sha256": sha256(candidate)}
        }
        self.write_run("new-run", run)

        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frozen", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_selection_and_sidecars_reject_symlink_components(self) -> None:
        self.start()
        run = self.complete_preflight()
        run_dir = self.run_path("new-run").parent
        target = run_dir / "selection-target.json"
        target.write_text(
            json.dumps(selection_payload("new-run"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        selection = run_dir / "memory-selection.json"
        selection.symlink_to(target.name)
        run["extensions"]["learning_loop"]["selection"] = {
            "path": "memory-selection.json",
            "sha256": sha256(target),
        }
        self.write_run("new-run", run)

        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

        run = self.start("sidecar-symlink")
        run_dir = self.run_path("sidecar-symlink").parent
        target = run_dir / "capabilities-target.json"
        target.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "workflow_version": "1.1.0",
                    "run_id": "sidecar-symlink",
                    "probed_at": "2026-07-11T00:00:00Z",
                    "capabilities": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        sidecar = run_dir / "runtime-capabilities.json"
        sidecar.symlink_to(target.name)
        run["extensions"]["learning_loop"]["sidecars"] = {
            "runtime-capabilities.json": {
                "path": "runtime-capabilities.json",
                "sha256": sha256(target),
            }
        }
        self.write_run("sidecar-symlink", run)

        result, payload = self.validate("sidecar-symlink")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

        run = self.start("directory-symlink")
        run_dir = self.run_path("directory-symlink").parent
        real_events = run_dir / "real-events"
        real_events.mkdir()
        event = real_events / "event-001.json"
        event.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "workflow_version": "1.1.0",
                    "run_id": "directory-symlink",
                    "event_id": "event-001",
                    "kind": "content",
                    "stage": "preflight",
                    "capability_id": "environment_probe",
                    "actual_id": "source-media",
                    "purpose": "测试目录 symlink",
                    "result": "passed",
                    "capture_state": "captured",
                    "evidence_refs": [],
                    "recorded_at": "2026-07-11T00:00:00Z",
                    "content_ref": "source-media",
                    "content_sha256": "f" * 64,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "usage-events").symlink_to(real_events.name, target_is_directory=True)
        run["extensions"]["learning_loop"]["sidecars"] = {
            "usage-events/event-001.json": {
                "path": "usage-events/event-001.json",
                "sha256": sha256(event),
            }
        }
        self.write_run("directory-symlink", run)

        result, payload = self.validate("directory-symlink")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

    def test_learning_json_requires_contract_fields_and_identity(self) -> None:
        self.start()
        run = self.complete_preflight()
        selection = self.run_path("new-run").parent / "memory-selection.json"
        selection.write_text('{"selected":[]}\n', encoding="utf-8")
        run["extensions"]["learning_loop"]["selection"] = {
            "path": "memory-selection.json",
            "sha256": sha256(selection),
        }
        self.write_run("new-run", run)

        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

        selection.write_text("not-json\n", encoding="utf-8")
        run["extensions"]["learning_loop"]["selection"]["sha256"] = sha256(
            selection
        )
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JSON 对象", "\n".join(payload["errors"]))
        self.assertIsNone(payload["invalidated_from"])

        wrong_identity = selection_payload("different-run")
        wrong_identity["workflow_version"] = "1.0.0"
        selection.write_text(
            json.dumps(wrong_identity, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        run["extensions"]["learning_loop"]["selection"]["sha256"] = sha256(
            selection
        )
        self.write_run("new-run", run)
        result, payload = self.validate("new-run")
        self.assertNotEqual(result.returncode, 0)
        errors = "\n".join(payload["errors"])
        self.assertIn("workflow_version", errors)
        self.assertIn("run_id", errors)
        self.assertIsNone(payload["invalidated_from"])

    def test_extension_failure_never_invalidates_or_mutates_core_stages(self) -> None:
        run = self.start()
        run["extensions"]["learning_loop"]["state"] = "broken"
        before = json.loads(json.dumps(run))
        self.write_run("new-run", run)

        result, payload = self.validate("new-run", "--apply-invalidation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(payload["invalidated_from"])
        self.assertFalse(payload["invalidation_applied"])
        self.assertEqual(self.read_run("new-run"), before)

    def test_learning_modes_are_mutually_exclusive(self) -> None:
        self.start()
        result = self.cli(
            VALIDATE_RUN,
            "--repo",
            str(self.repo),
            "--run-id",
            "new-run",
            "--core-only",
            "--require-learning-memory",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed", result.stderr)


if __name__ == "__main__":
    unittest.main()
