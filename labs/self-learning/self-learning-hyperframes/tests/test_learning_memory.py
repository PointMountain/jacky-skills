from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE_SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_RELATIVE = Path("references/workflows/1.1.0.json")
FINAL_RENDER_HASH = "5" * 64


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


class LearningMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.skill_root = self.root / "skill"
        shutil.copytree(SOURCE_SKILL_ROOT / "scripts", self.skill_root / "scripts")
        shutil.copytree(SOURCE_SKILL_ROOT / "references", self.skill_root / "references")
        self.record = self.skill_root / "scripts" / "record_learning.py"
        self.local_root = self.skill_root / "local"

        self.repo = self.root / "repo"
        self.run_id = "memory-run"
        self.run_dir = self.repo / ".learning" / "runs" / self.run_id
        (self.run_dir / "drafts").mkdir(parents=True)
        (self.run_dir / "evidence").mkdir()
        self._write_json(self.run_dir / "evidence/review.json", {"reviewed": True})
        self._write_json(self.run_dir / "evidence/conflict.json", {"conflict": True})
        workflow = self.skill_root / WORKFLOW_RELATIVE
        self.run = {
            "schema_version": "1.0.0",
            "workflow_version": "1.1.0",
            "workflow_sha256": digest(workflow),
            "run_id": self.run_id,
            "status": "running",
            "current_stage": "ingest",
            "next_stage": "transcript",
            "completed_stages": ["preflight"],
            "invalidated_stages": [],
            "source": {"kind": "local_file", "source_id": "memory-source"},
            "artifacts": {},
            "bindings": [],
            "extensions": {
                "learning_loop": {
                    "required": True,
                    "state": "collecting",
                    "contract_version": "1.0.0",
                    "selection": None,
                    "sidecars": {},
                }
            },
        }
        self._write_json(self.run_dir / "run.json", self.run)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(value))

    def _write_draft(self, name: str, value: dict) -> str:
        relative = f"drafts/{name}.json"
        self._write_json(self.run_dir / relative, value)
        return relative

    def _cli(self, command: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.record),
                command,
                "--repo",
                str(self.repo),
                "--run-id",
                self.run_id,
                *arguments,
                "--json",
            ],
            text=True,
            capture_output=True,
        )

    def _query(self, *, conflict: bool = False) -> str:
        return self._write_draft(
            "memory-query-conflict" if conflict else "memory-query",
            {
                "task_intents": ["learn_tutorial"],
                "mechanisms": ["poster_wall"],
                "capability_ids": ["motion_observation"],
                "conflicting_evidence_refs": (
                    ["evidence/conflict.json"] if conflict else []
                ),
                "created_at": "2026-07-11T08:00:00Z",
            },
        )

    def _seed_memory(
        self,
        memory_id: str,
        *,
        status: str = "active",
        mechanism: str = "poster_wall",
        verified_at: str = "2026-07-10T08:00:00Z",
    ) -> None:
        memory = {
            "schema_version": "1.0.0",
            "memory_id": memory_id,
            "revision": 1,
            "status": status,
            "destination": "error_memory",
            "finding_type": "failure_root_cause",
            "symptom": f"symptom-{memory_id}",
            "root_cause": f"root-{memory_id}",
            "root_cause_key": hashlib.sha256(f"root-{memory_id}".encode()).hexdigest(),
            "next_rule": f"rule-{memory_id}",
            "applies_to": ["tutorial video"],
            "not_applies_to": [],
            "scope": {
                "task_intents": ["learn_tutorial"],
                "mechanisms": [mechanism],
                "capability_ids": ["motion_observation"],
            },
            "problem_model": "visual-evidence",
            "evidence_refs": [],
            "verified_at": verified_at,
            "source_candidate": {"run_id": "seed", "candidate_id": memory_id},
        }
        path = self.local_root / "memories" / f"{memory_id}.json"
        self._write_json(path, memory)
        index_path = self.local_root / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text())
        else:
            index = {"schema_version": "1.0.0", "memories": {}, "maps": {}}
        index["memories"][memory_id] = {
            "path": f"memories/{memory_id}.json",
            "sha256": digest(path),
            "revision": 1,
            "status": status,
            "destination": "error_memory",
            "scope": memory["scope"],
            "problem_model": memory["problem_model"],
            "entered_at": verified_at,
            "reason": "verified root cause",
        }
        self._write_json(index_path, index)

    def _freeze_run(self) -> tuple[bytes, bytes]:
        r2 = self.run_dir / "score-r2.json"
        final = self.run_dir / "final.json"
        retrospective = self.run_dir / "retrospective.json"
        self._write_json(
            r2,
            {
                "artifact_type": "score",
                "round": "r2",
                "reviewed_render_sha256": FINAL_RENDER_HASH,
            },
        )
        self._write_json(
            final,
            {"artifact_type": "final", "render_sha256": FINAL_RENDER_HASH},
        )
        self._write_json(retrospective, {"frozen": True})
        run = json.loads((self.run_dir / "run.json").read_text())
        run.update(
            {
                "status": "completed",
                "current_stage": "finalize",
                "next_stage": None,
            }
        )
        run["artifacts"].update(
            {
                "verify": {
                    "path": "evidence/review.json",
                    "sha256": digest(self.run_dir / "evidence/review.json"),
                },
                "review_r2": {"path": r2.name, "sha256": digest(r2)},
                "finalize": {"path": final.name, "sha256": digest(final)},
            }
        )
        extension = run["extensions"]["learning_loop"]
        extension["state"] = "frozen"
        extension["sidecars"]["retrospective.json"] = {
            "path": "retrospective.json",
            "sha256": digest(retrospective),
        }
        self._write_json(self.run_dir / "run.json", run)
        return final.read_bytes(), retrospective.read_bytes()

    def _feedback(
        self,
        candidate_id: str,
        *,
        destination: str,
        evidence: bool = True,
        root_cause: str | None = "Frame sampling skipped the transition midpoint",
        finding_type: str = "failure_root_cause",
        problem_model: str = "visual-evidence",
        verified_at: str | None = "2026-07-11T08:10:00Z",
    ) -> str:
        payload = {
            "candidate_id": candidate_id,
            "final_hash": FINAL_RENDER_HASH,
            "r2_hash": FINAL_RENDER_HASH,
            "evidence_refs": ["evidence/review.json"] if evidence else [],
            "applies_to": ["tutorials with short transitions"],
            "destination": destination,
            "received_at": "2026-07-11T08:11:00Z",
            "source": "reviewer_feedback" if evidence else "asserted_user_instruction",
            "claim": "Dense sampling is required around the transition midpoint",
            "next_validation": "Check the next tutorial transition with a dense strip",
            "finding_type": finding_type,
            "symptom": "The key transition was not observable",
            "root_cause": root_cause,
            "future_recurrence": "Tutorials with transitions shorter than coarse sampling",
            "verified_at": verified_at,
            "not_applies_to": ["static tutorials"],
            "problem_model": problem_model,
            "scope": {
                "task_intents": ["learn_tutorial"],
                "mechanisms": ["poster_wall"],
                "capability_ids": ["motion_observation"],
            },
        }
        return self._write_draft(candidate_id, payload)

    def _record_feedback(self, relative: str) -> subprocess.CompletedProcess[str]:
        return self._cli("record-feedback", "--input", relative)

    def _promote(self, candidate_id: str) -> subprocess.CompletedProcess[str]:
        return self._cli(
            "promote-memory",
            "--input",
            f"feedback-candidates/{candidate_id}.json",
        )

    def test_empty_selection_is_written_without_creating_local(self) -> None:
        self.assertFalse(self.local_root.exists())
        result = self._cli("select-memory", "--input", self._query())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.local_root.exists())
        selection = json.loads((self.run_dir / "memory-selection.json").read_text())
        self.assertEqual(selection["selected"], [])
        self.assertEqual(selection["rejected"], [])
        self.assertEqual(
            selection["selection_snapshot_sha256"],
            hashlib.sha256(canonical_bytes(selection["selection_snapshot"])).hexdigest(),
        )
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(
            run["extensions"]["learning_loop"]["selection"]["path"],
            "memory-selection.json",
        )

    def test_selection_reads_only_active_scope_matches_limits_three_and_freezes_snapshot(self) -> None:
        for memory_id in ("m1", "m2", "m3", "m4"):
            self._seed_memory(memory_id)
        self._seed_memory("archived", status="archived")
        self._seed_memory("other", mechanism="unrelated")
        result = self._cli("select-memory", "--input", self._query())
        self.assertEqual(result.returncode, 0, result.stderr)
        selection_path = self.run_dir / "memory-selection.json"
        selection = json.loads(selection_path.read_text())
        self.assertEqual(len(selection["selected"]), 3)
        self.assertNotIn("archived", {item["memory_id"] for item in selection["selected"]})
        self.assertNotIn("other", {item["memory_id"] for item in selection["selected"]})
        self.assertTrue(all("snapshot" in item for item in selection["selected"]))
        frozen = selection_path.read_bytes()
        memory_path = self.local_root / "memories/m1.json"
        memory = json.loads(memory_path.read_text())
        memory["revision"] = 2
        self._write_json(memory_path, memory)
        self.assertEqual(selection_path.read_bytes(), frozen)

    def test_conflicting_current_evidence_rejects_matching_memory(self) -> None:
        self._seed_memory("conflicted")
        result = self._cli("select-memory", "--input", self._query(conflict=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        selection = json.loads((self.run_dir / "memory-selection.json").read_text())
        self.assertEqual(selection["selected"], [])
        self.assertEqual(selection["rejected"][0]["reason"], "conflicting_evidence")
        self.assertEqual(
            selection["query"]["conflicting_evidence_refs"][0]["sha256"],
            digest(self.run_dir / "evidence/conflict.json"),
        )

    def test_selection_rejects_index_memory_status_mismatch(self) -> None:
        self._seed_memory("status-mismatch", status="archived")
        index_path = self.local_root / "index.json"
        index = json.loads(index_path.read_text())
        index["memories"]["status-mismatch"]["status"] = "active"
        self._write_json(index_path, index)

        result = self._cli("select-memory", "--input", self._query())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status", result.stderr.lower())
        self.assertFalse((self.run_dir / "memory-selection.json").exists())

    def test_reviewer_and_promotion_reject_model_authored_draft_evidence(self) -> None:
        self._freeze_run()
        self._write_json(self.run_dir / "drafts/self-claim.json", {"claim": "I passed"})
        relative = self._feedback("self-claim-reviewer", destination="backlog")
        payload = json.loads((self.run_dir / relative).read_text())
        payload["evidence_refs"] = ["drafts/self-claim.json"]
        self._write_json(self.run_dir / relative, payload)
        rejected = self._record_feedback(relative)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("trusted", rejected.stderr.lower())

        payload["candidate_id"] = "self-claim-user"
        payload["source"] = "asserted_user_instruction"
        payload["destination"] = "error_memory"
        relative = self._write_draft("self-claim-user", payload)
        accepted_candidate = self._record_feedback(relative)
        self.assertEqual(accepted_candidate.returncode, 0, accepted_candidate.stderr)
        rejected_promotion = self._promote("self-claim-user")
        self.assertNotEqual(rejected_promotion.returncode, 0)
        self.assertIn("trusted", rejected_promotion.stderr.lower())
        self.assertFalse(self.local_root.exists())

    def test_feedback_is_append_only_and_evidence_less_user_feedback_stays_backlog(self) -> None:
        final_before, retrospective_before = self._freeze_run()
        reviewer_without_evidence = self._feedback(
            "reviewer-no-evidence",
            destination="backlog",
            evidence=False,
            root_cause=None,
            verified_at=None,
        )
        reviewer_payload = json.loads((self.run_dir / reviewer_without_evidence).read_text())
        reviewer_payload["source"] = "reviewer_feedback"
        self._write_json(self.run_dir / reviewer_without_evidence, reviewer_payload)
        rejected = self._record_feedback(reviewer_without_evidence)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("reviewer", rejected.stderr.lower())

        relative = self._feedback(
            "feedback-no-evidence",
            destination="backlog",
            evidence=False,
            root_cause=None,
            verified_at=None,
        )
        result = self._record_feedback(relative)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.run_dir / "final.json").read_bytes(), final_before)
        self.assertEqual(
            (self.run_dir / "retrospective.json").read_bytes(), retrospective_before
        )
        self.assertFalse(self.local_root.exists())
        candidate = json.loads(
            (self.run_dir / "feedback-candidates/feedback-no-evidence.json").read_text()
        )
        self.assertEqual(candidate["destination"], "backlog")
        self.assertEqual(candidate["final_hash"], FINAL_RENDER_HASH)
        self.assertEqual(candidate["r2_hash"], FINAL_RENDER_HASH)
        self.assertNotEqual(self._promote("feedback-no-evidence").returncode, 0)

    def test_promotion_revalidates_error_memory_gate_and_rejects_shared_destinations(self) -> None:
        self._freeze_run()
        missing_root = self._feedback(
            "missing-root", destination="error_memory", root_cause=None
        )
        self.assertEqual(self._record_feedback(missing_root).returncode, 0)
        failed = self._promote("missing-root")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("root", failed.stderr.lower())
        self.assertFalse(self.local_root.exists())

        shared = self._feedback("shared-rule", destination="reference")
        self.assertEqual(self._record_feedback(shared).returncode, 0)
        failed = self._promote("shared-rule")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("candidate", failed.stderr.lower())
        self.assertFalse(self.local_root.exists())

    def test_environment_memory_requires_verified_at_and_valid_promotion_is_idempotent(self) -> None:
        self._freeze_run()
        missing_time = self._feedback(
            "missing-time",
            destination="local_memory",
            finding_type="environment_fact",
            verified_at=None,
        )
        self.assertEqual(self._record_feedback(missing_time).returncode, 0)
        self.assertNotEqual(self._promote("missing-time").returncode, 0)
        self.assertFalse(self.local_root.exists())

        valid = self._feedback(
            "environment-valid",
            destination="local_memory",
            finding_type="environment_fact",
        )
        self.assertEqual(self._record_feedback(valid).returncode, 0)
        first = self._promote("environment-valid")
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self._promote("environment-valid")
        self.assertEqual(second.returncode, 0, second.stderr)
        memories = list((self.local_root / "memories").glob("*.json"))
        receipts = list((self.run_dir / "promotion-receipts").glob("*.json"))
        self.assertEqual(len(memories), 1)
        self.assertEqual(len(receipts), 1)
        self.assertNotIn(str(self.root), memories[0].read_text())

    def test_same_root_cause_updates_one_memory_and_three_shared_models_create_one_map(self) -> None:
        self._freeze_run()
        for index, root_cause in enumerate(("same-root", "same-root"), start=1):
            relative = self._feedback(
                f"same-root-{index}",
                destination="error_memory",
                root_cause=root_cause,
            )
            self.assertEqual(self._record_feedback(relative).returncode, 0)
            promoted = self._promote(f"same-root-{index}")
            self.assertEqual(promoted.returncode, 0, promoted.stderr)
        memories = list((self.local_root / "memories").glob("*.json"))
        self.assertEqual(len(memories), 1)
        self.assertEqual(json.loads(memories[0].read_text())["revision"], 2)

        for index in range(2):
            relative = self._feedback(
                f"map-root-{index}",
                destination="error_memory",
                root_cause=f"map-root-{index}",
                problem_model="visual-evidence",
            )
            self.assertEqual(self._record_feedback(relative).returncode, 0)
            promoted = self._promote(f"map-root-{index}")
            self.assertEqual(promoted.returncode, 0, promoted.stderr)
        maps = list((self.local_root / "maps").glob("*.json"))
        self.assertEqual(len(maps), 1)
        self.assertEqual(len(json.loads(maps[0].read_text())["memory_ids"]), 3)

    def test_same_root_update_reconciles_old_and_new_problem_model_maps(self) -> None:
        self._freeze_run()
        roots = ("moving-root", "old-root-2", "old-root-3")
        for index, root_cause in enumerate(roots):
            relative = self._feedback(
                f"old-model-{index}",
                destination="error_memory",
                root_cause=root_cause,
                problem_model="old-model",
            )
            self.assertEqual(self._record_feedback(relative).returncode, 0)
            promoted = self._promote(f"old-model-{index}")
            self.assertEqual(promoted.returncode, 0, promoted.stderr)
        self.assertEqual(len(list((self.local_root / "maps").glob("*.json"))), 1)

        moved = self._feedback(
            "moved-model",
            destination="error_memory",
            root_cause="moving-root",
            problem_model="new-model",
        )
        self.assertEqual(self._record_feedback(moved).returncode, 0)
        promoted = self._promote("moved-model")
        self.assertEqual(promoted.returncode, 0, promoted.stderr)

        index = json.loads((self.local_root / "index.json").read_text())
        self.assertEqual(index["maps"], {})
        self.assertEqual(list((self.local_root / "maps").glob("*.json")), [])
        linted = self._cli("lint")
        self.assertEqual(linted.returncode, 0, linted.stderr)

    def test_lint_detects_orphan_memory_and_private_feedback_is_rejected(self) -> None:
        self._freeze_run()
        valid = self._feedback("lint-valid", destination="error_memory")
        self.assertEqual(self._record_feedback(valid).returncode, 0)
        self.assertEqual(self._promote("lint-valid").returncode, 0)
        clean = self._cli("lint")
        self.assertEqual(clean.returncode, 0, clean.stderr)

        self._write_json(self.local_root / "memories/orphan.json", {"orphan": True})
        broken = self._cli("lint")
        self.assertNotEqual(broken.returncode, 0)
        self.assertIn("orphan", broken.stderr.lower())

        private = json.loads(
            (self.run_dir / "feedback-candidates/lint-valid.json").read_text()
        )
        private["candidate_id"] = "private-feedback"
        private["claim"] = "/" + "Users/alice/private.mov"
        relative = self._write_draft("private-feedback", private)
        rejected = self._record_feedback(relative)
        self.assertNotEqual(rejected.returncode, 0)


if __name__ == "__main__":
    unittest.main()
