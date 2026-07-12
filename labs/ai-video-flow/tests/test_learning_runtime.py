from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor


SKILL_ROOT = Path(__file__).resolve().parents[1]
RECORD = SKILL_ROOT / "scripts" / "record_learning.py"
VALIDATE = SKILL_ROOT / "scripts" / "validate_run.py"
WORKFLOW = SKILL_ROOT / "references" / "workflows" / "1.1.0.json"
CAPABILITY_REGISTRY = (
    SKILL_ROOT / "references" / "capability-registries" / "1.0.0.json"
)
CAPABILITY_REGISTRY_VALUE = json.loads(CAPABILITY_REGISTRY.read_text())
CAPABILITY_CANDIDATES = {
    entry["id"]: [candidate["id"] for candidate in entry["candidates"]]
    for entry in CAPABILITY_REGISTRY_VALUE["capabilities"]
}
STAGES = [stage["id"] for stage in json.loads(WORKFLOW.read_text())["stages"]]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LearningRuntimeTests(unittest.TestCase):
    def test_concurrent_usage_keeps_event_directory_and_descriptors_exact(self) -> None:
        drafts: list[str] = []
        for index in range(40):
            drafts.append(
                self.write_draft(
                    f"concurrent-{index:02d}",
                    {
                        "event_id": f"concurrent-{index:02d}",
                        "kind": "tool",
                        "stage": "preflight",
                        "capability_id": "environment_probe",
                        "actual_id": "node_runtime",
                        "purpose": "并发记录真实 coverage",
                        "result": "not_recorded",
                        "capture_state": "not_recorded",
                        "evidence_refs": [],
                        "version": None,
                        "execution_receipt": None,
                        "recorded_at": f"2026-07-11T00:02:{index:02d}Z",
                    },
                )
            )

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(
                executor.map(
                    lambda relative: self.cli(
                        "record-usage", "--input", relative
                    ),
                    drafts,
                )
            )
        failures = [result.stderr for result in results if result.returncode != 0]
        self.assertEqual(failures, [])

        event_paths = {
            path.relative_to(self.run_dir).as_posix()
            for path in (self.run_dir / "usage-events").glob("*.json")
        }
        run = json.loads((self.run_dir / "run.json").read_text())
        descriptor_paths = {
            path
            for path in run["extensions"]["learning_loop"]["sidecars"]
            if path.startswith("usage-events/")
        }
        self.assertEqual(len(event_paths), 40)
        self.assertEqual(descriptor_paths, event_paths)

    def test_runs_ancestor_symlink_is_rejected_by_record_and_validator(self) -> None:
        runs = self.repo / ".learning" / "runs"
        outside = Path(self.tempdir.name) / "outside-runs"
        runs.rename(outside)
        runs.symlink_to(outside, target_is_directory=True)
        marker = outside / self.run_id / "run.json"
        before = marker.read_bytes()

        record = self.cli(
            "record-usage", "--input", "drafts/does-not-matter.json"
        )
        self.assertNotEqual(record.returncode, 0)
        self.assertIn("symlink", record.stderr.lower())
        validation = subprocess.run(
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
            ],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("symlink", validation.stdout.lower())
        self.assertEqual(marker.read_bytes(), before)

    def test_current_registry_drift_does_not_reinterpret_but_frozen_drift_fails(self) -> None:
        copied = Path(self.tempdir.name) / "copied-skill"
        shutil.copytree(SKILL_ROOT, copied)
        current = copied / "references" / "capabilities.json"
        current.write_text(current.read_text(encoding="utf-8") + " ", encoding="utf-8")
        draft = {
            "event_id": "copied-current-registry",
            "kind": "content",
            "stage": "preflight",
            "capability_id": "environment_probe",
            "actual_id": "preflight-input",
            "purpose": "验证只按冻结 registry 解释",
            "result": "passed",
            "capture_state": "captured",
            "evidence_refs": ["evidence/probe.json"],
            "content_ref": "preflight.json",
            "recorded_at": "2026-07-11T00:07:00Z",
        }
        relative = self.write_draft("copied-current-registry", draft)

        def copied_cli(input_path: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable,
                    str(copied / "scripts" / "record_learning.py"),
                    "record-usage",
                    "--repo",
                    str(self.repo),
                    "--run-id",
                    self.run_id,
                    "--input",
                    input_path,
                    "--json",
                ],
                text=True,
                capture_output=True,
            )

        accepted = copied_cli(relative)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        frozen = copied / "references" / "capability-registries" / "1.0.0.json"
        frozen.write_text(frozen.read_text(encoding="utf-8") + " ", encoding="utf-8")
        draft["event_id"] = "copied-frozen-registry"
        relative = self.write_draft("copied-frozen-registry", draft)
        rejected = copied_cli(relative)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("registry", rejected.stderr.lower())

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.run_id = "runtime-run"
        self.run_dir = self.repo / ".learning" / "runs" / self.run_id
        (self.run_dir / "drafts").mkdir(parents=True)
        (self.run_dir / "evidence").mkdir()
        self.evidence = self.run_dir / "evidence" / "probe.json"
        self.evidence.write_text('{"ok":true}\n', encoding="utf-8")
        self.content = self.run_dir / "preflight.json"
        self.content.write_text('{"artifact_type":"preflight"}\n', encoding="utf-8")
        self.source = Path(self.tempdir.name) / "source.mp4"
        self.source.write_bytes(b"runtime-source")
        core_artifacts: dict[str, dict[str, str]] = {}
        for stage in (
            "transcript",
            "learn_method",
            "observe_motion",
            "plan_demo",
            "build",
            "review_r1",
            "review_r2",
            "finalize",
        ):
            path = self.run_dir / f"core-{stage}.json"
            path.write_text(json.dumps({"stage": stage}) + "\n", encoding="utf-8")
            core_artifacts[stage] = {"path": path.name, "sha256": digest(path)}
        self._write_fixed_learning_inputs()
        run = {
            "schema_version": "1.0.0",
            "workflow_version": "1.1.0",
            "workflow_sha256": digest(WORKFLOW),
            "run_id": self.run_id,
            "status": "completed",
            "current_stage": "finalize",
            "next_stage": None,
            "completed_stages": STAGES,
            "invalidated_stages": [],
            "source": {
                "kind": "local_file",
                "source_id": "source-runtime",
                "private_locator": str(self.source),
                "media_sha256": digest(self.source),
            },
            "artifacts": core_artifacts,
            "bindings": [],
            "extensions": {
                "learning_loop": {
                    "required": True,
                    "state": "collecting",
                    "contract_version": "1.0.0",
                    "selection": {
                        "path": "memory-selection.json",
                        "sha256": digest(self.run_dir / "memory-selection.json"),
                    },
                    "sidecars": {
                        "runtime-capabilities.json": {
                            "path": "runtime-capabilities.json",
                            "sha256": digest(self.run_dir / "runtime-capabilities.json"),
                        },
                        "decision-trace.json": {
                            "path": "decision-trace.json",
                            "sha256": digest(self.run_dir / "decision-trace.json"),
                        },
                    },
                }
            },
        }
        self._write_json(self.run_dir / "run.json", run)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def _write_fixed_learning_inputs(self) -> None:
        identity = {
            "schema_version": "1.0.0",
            "workflow_version": "1.1.0",
            "run_id": self.run_id,
        }
        self._write_json(
            self.run_dir / "memory-selection.json",
            {
                **identity,
                "query": {},
                "selected": [],
                "rejected": [],
                "selection_snapshot": [],
                "selection_snapshot_sha256": hashlib.sha256(b"[]").hexdigest(),
                "created_at": "2026-07-11T00:00:00Z",
            },
        )
        self._write_json(
            self.run_dir / "runtime-capabilities.json",
            {
                **identity,
                "registry_version": "1.0.0",
                "registry_sha256": digest(CAPABILITY_REGISTRY),
                "probed_at": "2026-07-11T00:00:00Z",
                "capabilities": {},
            },
        )
        self._write_json(
            self.run_dir / "decision-trace.json", {**identity, "decisions": []}
        )

    def cli(
        self, command: str, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RECORD),
                command,
                "--repo",
                str(self.repo),
                "--run-id",
                self.run_id,
                *args,
                "--json",
            ],
            text=True,
            capture_output=True,
            env=env,
        )

    def write_draft(self, name: str, value: dict) -> str:
        relative = f"drafts/{name}.json"
        self._write_json(self.run_dir / relative, value)
        return relative

    def record_usage(self, draft: dict) -> subprocess.CompletedProcess[str]:
        relative = self.write_draft(draft["event_id"], draft)
        return self.cli("record-usage", "--input", relative)

    def coverage_pairs(self) -> list[tuple[str, str]]:
        workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
        return [
            (stage["id"], capability)
            for stage in workflow["stages"]
            for capability in stage["capability_ids"]
        ]

    def record_full_coverage(self) -> None:
        receipt = self.run_dir / "evidence" / "node-execution.json"
        self._write_json(
            receipt,
            {
                "receipt_type": "execution",
                "command": ["node", "--version"],
                "exit_code": 0,
                "executed_at": "2026-07-11T00:00:01Z",
            },
        )
        for index, (stage, capability) in enumerate(self.coverage_pairs()):
            captured = stage == "preflight" and capability == "environment_probe"
            result = self.record_usage(
                {
                    "event_id": f"coverage-{index:02d}",
                    "kind": "tool",
                    "stage": stage,
                    "capability_id": capability,
                    "actual_id": CAPABILITY_CANDIDATES[capability][0],
                    "purpose": "明确记录无可验证历史执行凭据",
                    "result": "passed" if captured else "not_recorded",
                    "capture_state": "captured" if captured else "not_recorded",
                    "evidence_refs": ["evidence/probe.json"] if captured else [],
                    "version": "1.0.0" if captured else None,
                    "execution_receipt": (
                        "evidence/node-execution.json" if captured else None
                    ),
                    "recorded_at": "2026-07-11T00:00:02Z",
                }
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def record_required_decisions(self) -> None:
        evidence_by_stage = {
            "transcript": "core-transcript.json",
            "plan_demo": "core-plan_demo.json",
            "revise": "core-review_r1.json",
        }
        for index, stage in enumerate(("transcript", "plan_demo", "revise")):
            relative = self.write_draft(
                f"required-decision-{index}",
                {
                    "decision_id": f"required-decision-{index}",
                    "stage": stage,
                    "observation": f"{stage} 已产生可定位事实",
                    "evidence_refs": [evidence_by_stage[stage]],
                    "decision": f"按 {stage} 事实继续",
                    "action": "执行下一步",
                    "validation": "由后续产物验证",
                    "error": None,
                    "root_cause": None,
                    "next_rule": "保留同一事实边界",
                    "recorded_at": f"2026-07-11T00:01:0{index}Z",
                },
            )
            result = self.cli("record-decision", "--input", relative)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_record_capability_accumulates_probe_facts_and_rejects_registry_drift(self) -> None:
        for index, (capability_id, status, selected, fallback, probe_results) in enumerate(
            (
                (
                    "environment_probe",
                    "available",
                    ["node_runtime", "local_hyperframes_binary"],
                    None,
                    [("node_runtime", "passed"), ("local_hyperframes_binary", "passed")],
                ),
                (
                    "local_transcription",
                    "degraded",
                    "audio_to_subtitle",
                    "continue_to_next_candidate",
                    [("audio_to_subtitle", "degraded")],
                ),
                (
                    "motion_observation",
                    "missing",
                    None,
                    "use_capability_fallback",
                    [("animate_prompt", "missing"), ("ffmpeg_frame_sampling", "missing")],
                ),
            )
        ):
            relative = self.write_draft(
                f"capability-{index}",
                {
                    "capability_id": capability_id,
                    "status": status,
                    "selected": selected,
                    "fallback": fallback,
                    "probes": [
                        {
                            "candidate_id": candidate_id,
                            "result": probe_result,
                            "evidence_refs": ["evidence/probe.json"],
                        }
                        for candidate_id, probe_result in probe_results
                    ],
                    "checked_at": f"2026-07-11T00:00:0{index}Z",
                },
            )
            result = self.cli("record-capability", "--input", relative)
            self.assertEqual(result.returncode, 0, result.stderr)

        runtime = json.loads(
            (self.run_dir / "runtime-capabilities.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(runtime["capabilities"]),
            {"environment_probe", "local_transcription", "motion_observation"},
        )
        self.assertEqual(
            runtime["capabilities"]["environment_probe"]["probes"][0][
                "evidence_refs"
            ][0],
            {"path": "evidence/probe.json", "sha256": digest(self.evidence)},
        )
        bad = self.write_draft(
            "capability-rogue",
            {
                "capability_id": "environment_probe",
                "status": "available",
                "selected": ["invented_tool"],
                "fallback": None,
                "probes": [
                    {
                        "candidate_id": "invented_tool",
                        "result": "passed",
                        "evidence_refs": ["evidence/probe.json"],
                    }
                ],
                "checked_at": "2026-07-11T00:00:09Z",
            },
        )
        result = self.cli("record-capability", "--input", bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("registry", result.stderr)

    def test_record_decision_requires_evidence_for_root_cause_and_is_idempotent(self) -> None:
        base = {
            "decision_id": "decision-001",
            "stage": "plan_demo",
            "observation": "素材边界已可定位",
            "evidence_refs": ["core-plan_demo.json"],
            "decision": "使用单 Demo 范围",
            "action": "冻结实现范围",
            "validation": "R1 将验证范围是否完整",
            "error": None,
            "root_cause": None,
            "next_rule": "相同机制保持单 Demo",
            "recorded_at": "2026-07-11T00:00:03Z",
        }
        relative = self.write_draft("decision", base)
        first = self.cli("record-decision", "--input", relative)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.cli("record-decision", "--input", relative)
        self.assertEqual(second.returncode, 0, second.stderr)
        decisions = json.loads(
            (self.run_dir / "decision-trace.json").read_text(encoding="utf-8")
        )["decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            decisions[0]["evidence_refs"][0]["sha256"],
            digest(self.run_dir / "core-plan_demo.json"),
        )

        unsupported = dict(base)
        unsupported.update(
            {
                "decision_id": "decision-002",
                "evidence_refs": [],
                "root_cause": "没有证据却声称已定位根因",
            }
        )
        relative = self.write_draft("decision-no-evidence", unsupported)
        failed = self.cli("record-decision", "--input", relative)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("root_cause", failed.stderr)

    def test_input_and_semantic_payload_reject_escape_symlink_and_private_data(self) -> None:
        outside = Path(self.tempdir.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        (self.run_dir / "drafts" / "linked.json").symlink_to(outside)
        for unsafe in (str(outside), "../outside.json", "drafts/linked.json"):
            with self.subTest(unsafe=unsafe):
                result = self.cli("record-usage", "--input", unsafe)
                self.assertNotEqual(result.returncode, 0)

        private = self.write_draft(
            "private",
            {
                "event_id": "private-event",
                "kind": "tool",
                "stage": "preflight",
                "capability_id": "environment_probe",
                "actual_id": "node_runtime",
                "purpose": "泄漏路径 " + "/" + "Users/alice/private.mov",
                "result": "not_recorded",
                "capture_state": "not_recorded",
                "evidence_refs": [],
                "version": None,
                "execution_receipt": None,
                "recorded_at": "2026-07-11T00:00:04Z",
            },
        )
        result = self.cli("record-usage", "--input", private)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("绝对路径", result.stderr)

    def test_captured_tool_requires_real_receipt_and_passed_requires_evidence(self) -> None:
        receipt = self.run_dir / "evidence" / "execution-receipt.json"
        self._write_json(
            receipt,
            {
                "receipt_type": "execution",
                "command": ["hyperframes", "check"],
                "exit_code": 0,
                "executed_at": "2026-07-11T00:00:04Z",
            },
        )
        base = {
            "event_id": "tool-check",
            "kind": "tool",
            "stage": "verify",
            "capability_id": "hyperframes_validation",
            "actual_id": "local_hyperframes_check_suite",
            "purpose": "执行项目检查",
            "result": "passed",
            "capture_state": "captured",
            "evidence_refs": ["evidence/probe.json"],
            "version": "1.0.0",
            "execution_receipt": "evidence/execution-receipt.json",
            "recorded_at": "2026-07-11T00:00:05Z",
        }
        result = self.record_usage(base)
        self.assertEqual(result.returncode, 0, result.stderr)
        event = json.loads(
            (self.run_dir / "usage-events" / "tool-check.json").read_text()
        )
        self.assertEqual(event["execution_receipt"]["sha256"], digest(receipt))

        missing = dict(base)
        missing["event_id"] = "tool-missing-receipt"
        missing["execution_receipt"] = None
        result = self.record_usage(missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt", result.stderr)

        unproven = dict(base)
        unproven["event_id"] = "tool-unproven"
        unproven["evidence_refs"] = []
        result = self.record_usage(unproven)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence", result.stderr)

    def test_execution_receipt_is_semantically_verified_and_result_bound(self) -> None:
        invalid_receipt = self.run_dir / "evidence" / "invalid-receipt.json"
        invalid_receipt.write_text('{"exit_code":0}\n', encoding="utf-8")
        draft = {
            "event_id": "invalid-receipt-event",
            "kind": "tool",
            "stage": "verify",
            "capability_id": "hyperframes_validation",
            "actual_id": "local_hyperframes_check_suite",
            "purpose": "验证 receipt 结构",
            "result": "passed",
            "capture_state": "captured",
            "evidence_refs": ["evidence/probe.json"],
            "version": "1.0.0",
            "execution_receipt": "evidence/invalid-receipt.json",
            "recorded_at": "2026-07-11T00:03:00Z",
        }
        result = self.record_usage(draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt", result.stderr.lower())

        valid_receipt = self.run_dir / "evidence" / "valid-receipt.json"
        valid_receipt.write_text(
            json.dumps(
                {
                    "receipt_type": "execution",
                    "command": ["hyperframes", "check"],
                    "exit_code": 1,
                    "executed_at": "2026-07-11T00:02:59Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        draft.update(
            {
                "event_id": "passed-nonzero",
                "execution_receipt": "evidence/valid-receipt.json",
            }
        )
        result = self.record_usage(draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit_code", result.stderr)

        draft.update(
            {
                "event_id": "failed-zero",
                "result": "failed",
            }
        )
        receipt_value = json.loads(valid_receipt.read_text())
        receipt_value["exit_code"] = 0
        self._write_json(valid_receipt, receipt_value)
        result = self.record_usage(draft)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit_code", result.stderr)

    def test_usage_requires_registry_actual_id_version_and_rfc3339_time(self) -> None:
        receipt = self.run_dir / "evidence" / "semantic-receipt.json"
        self._write_json(
            receipt,
            {
                "receipt_type": "execution",
                "command": ["hyperframes", "check"],
                "exit_code": 0,
                "executed_at": "2026-07-11T00:04:00Z",
            },
        )
        base = {
            "event_id": "semantic-usage",
            "kind": "tool",
            "stage": "verify",
            "capability_id": "hyperframes_validation",
            "actual_id": "invented-tool",
            "purpose": "验证实际候选",
            "result": "passed",
            "capture_state": "captured",
            "evidence_refs": ["evidence/probe.json"],
            "version": "1.0.0",
            "execution_receipt": "evidence/semantic-receipt.json",
            "recorded_at": "2026-07-11T00:04:01Z",
        }
        result = self.record_usage(base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("actual_id", result.stderr)

        base.update(
            {
                "event_id": "missing-version",
                "actual_id": "local_hyperframes_check_suite",
                "version": None,
            }
        )
        result = self.record_usage(base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version", result.stderr)

        base.update(
            {
                "event_id": "invalid-recorded-at",
                "version": "1.0.0",
                "recorded_at": "2026-07-11 00:04:01",
            }
        )
        result = self.record_usage(base)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recorded_at", result.stderr)

    def test_decision_and_capability_reject_empty_semantics_and_invalid_time(self) -> None:
        decision = {
            "decision_id": "invalid-semantics",
            "stage": "plan_demo",
            "observation": "",
            "evidence_refs": ["evidence/probe.json"],
            "decision": "继续",
            "action": "执行",
            "validation": "验证",
            "error": None,
            "root_cause": None,
            "next_rule": "规则",
            "recorded_at": "2026-07-11T00:05:00Z",
        }
        relative = self.write_draft("invalid-decision-semantics", decision)
        result = self.cli("record-decision", "--input", relative)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("observation", result.stderr)

        capability = {
            "capability_id": "local_transcription",
            "status": "available",
            "selected": "audio_to_subtitle",
            "fallback": None,
            "probes": [
                {
                    "candidate_id": "audio_to_subtitle",
                    "result": "passed",
                    "evidence_refs": ["evidence/probe.json"],
                }
            ],
            "evidence_refs": ["evidence/probe.json"],
            "checked_at": "yesterday",
        }
        relative = self.write_draft("invalid-capability-time", capability)
        result = self.cli("record-capability", "--input", relative)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checked_at", result.stderr)

    def test_orphan_usage_file_blocks_finalize_and_validator(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        orphan = self.run_dir / "usage-events" / "orphan.json"
        self._write_json(
            orphan,
            {
                "schema_version": "1.0.0",
                "workflow_version": "1.1.0",
                "run_id": self.run_id,
                "event_id": "orphan",
                "kind": "tool",
                "stage": "preflight",
                "capability_id": "environment_probe",
                "actual_id": "node_runtime",
                "purpose": "没有 descriptor 的孤儿事件",
                "result": "not_recorded",
                "capture_state": "not_recorded",
                "evidence_refs": [],
                "version": None,
                "execution_receipt": None,
                "recorded_at": "2026-07-11T00:06:00Z",
            },
        )
        result = self.finalize()
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"orphan|exact|descriptor")

    def test_usage_rejects_inapplicable_conditional_and_inconsistent_capture(self) -> None:
        conditional = {
            "event_id": "local-link-ingest",
            "kind": "tool",
            "stage": "ingest",
            "capability_id": "link_ingest",
            "actual_id": "not-recorded",
            "purpose": "本地源不适用 URL capability",
            "result": "not_recorded",
            "capture_state": "not_recorded",
            "evidence_refs": [],
            "version": None,
            "execution_receipt": None,
            "recorded_at": "2026-07-11T00:00:06Z",
        }
        result = self.record_usage(conditional)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不适用", result.stderr)

        receipt = self.run_dir / "evidence" / "capture-receipt.json"
        self._write_json(
            receipt,
            {
                "receipt_type": "execution",
                "command": ["hyperframes", "check"],
                "exit_code": 0,
                "executed_at": "2026-07-11T00:00:05Z",
            },
        )
        inconsistent = {
            **conditional,
            "event_id": "captured-not-recorded",
            "stage": "verify",
            "capability_id": "hyperframes_validation",
            "actual_id": "local_hyperframes_check_suite",
            "purpose": "captured 与 not_recorded 不能同时成立",
            "capture_state": "captured",
            "version": "1.0.0",
            "execution_receipt": "evidence/capture-receipt.json",
        }
        result = self.record_usage(inconsistent)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("captured", result.stderr)

    def test_record_usage_hashes_real_content_and_is_immutable(self) -> None:
        draft = {
            "event_id": "content-preflight",
            "kind": "content",
            "stage": "preflight",
            "capability_id": "environment_probe",
            "actual_id": "preflight-input",
            "purpose": "记录实际读取内容",
            "result": "passed",
            "capture_state": "captured",
            "evidence_refs": ["evidence/probe.json"],
            "content_ref": "preflight.json",
            "content_sha256": "f" * 64,
            "recorded_at": "2026-07-11T00:00:01Z",
        }
        first = self.record_usage(draft)
        self.assertEqual(first.returncode, 0, first.stderr)
        event_path = self.run_dir / "usage-events" / "content-preflight.json"
        event = json.loads(event_path.read_text(encoding="utf-8"))
        self.assertEqual(event["content_sha256"], digest(self.content))
        self.assertEqual(event["evidence_refs"][0]["sha256"], digest(self.evidence))

        second = self.record_usage(draft)
        self.assertEqual(second.returncode, 0, second.stderr)
        draft["purpose"] = "冲突写入"
        conflict = self.record_usage(draft)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertEqual(json.loads(event_path.read_text()), event)

    def test_record_usage_allows_the_active_stage_before_completion(self) -> None:
        run_path = self.run_dir / "run.json"
        run = json.loads(run_path.read_text())
        run.update(
            {
                "status": "running",
                "completed_stages": [],
                "current_stage": "preflight",
                "next_stage": "ingest",
            }
        )
        self._write_json(run_path, run)
        result = self.record_usage(
            {
                "event_id": "active-preflight",
                "kind": "content",
                "stage": "preflight",
                "capability_id": "environment_probe",
                "actual_id": "preflight-input",
                "purpose": "阶段执行中即时记录读取事实",
                "result": "passed",
                "capture_state": "captured",
                "evidence_refs": ["evidence/probe.json"],
                "content_ref": "preflight.json",
                "recorded_at": "2026-07-11T00:00:01Z",
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def _finalize_drafts(self) -> tuple[str, str, str]:
        manifest = {
            "entries": [
                {
                    "capability": "environment_probe",
                    "phase": "preflight",
                    "candidates_checked": ["node_runtime"],
                    "selected": "node_runtime",
                    "source": "local-binary",
                    "revision": "1.0.0",
                    "mode": "fallback",
                    "inputs": ["preflight.json"],
                    "outputs": ["evidence/probe.json"],
                    "result": "passed",
                    "evidence_refs": ["evidence/probe.json"],
                    "friction": None,
                    "adjustment_candidate": None,
                }
            ]
        }
        ledger = {"objective": "从不可变事件聚合实际使用事实"}
        retrospective = {
            "objective": "生成可审计学习闭环",
            "result": "success",
            "skills_manifest_ref": "skill-usage-manifest.json",
            "evidence": ["evidence/probe.json"],
            "findings": [],
        }
        return (
            self.write_draft("manifest", manifest),
            self.write_draft("ledger", ledger),
            self.write_draft("retrospective", retrospective),
        )

    def finalize(self) -> subprocess.CompletedProcess[str]:
        manifest, ledger, retrospective = self._finalize_drafts()
        return self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )

    def test_finalize_rejects_missing_coverage_without_partial_freeze(self) -> None:
        result = self.finalize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coverage", result.stderr.lower())
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(run["extensions"]["learning_loop"]["state"], "collecting")
        for name in ("skill-usage-manifest.json", "usage-ledger.json", "retrospective.json"):
            self.assertFalse((self.run_dir / name).exists())

    def test_finalize_requires_exact_unique_passed_manifest_projection(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        manifest, ledger, retrospective = self._finalize_drafts()
        manifest_path = self.run_dir / manifest
        manifest_value = json.loads(manifest_path.read_text())
        manifest_value["entries"] = []
        self._write_json(manifest_path, manifest_value)
        missing = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("projection", missing.stderr.lower())

        manifest, ledger, retrospective = self._finalize_drafts()
        manifest_path = self.run_dir / manifest
        manifest_value = json.loads(manifest_path.read_text())
        manifest_value["entries"].append(dict(manifest_value["entries"][0]))
        self._write_json(manifest_path, manifest_value)
        duplicate = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("duplicate", duplicate.stderr.lower())

    def test_ordered_fallback_missing_requires_every_candidate_probed(self) -> None:
        relative = self.write_draft(
            "partial-missing-capability",
            {
                "capability_id": "local_transcription",
                "status": "missing",
                "selected": None,
                "fallback": "continue_to_next_candidate",
                "probes": [
                    {
                        "candidate_id": "audio_to_subtitle",
                        "result": "missing",
                        "evidence_refs": ["evidence/probe.json"],
                    }
                ],
                "checked_at": "2026-07-11T00:09:00Z",
            },
        )
        record = self.cli("record-capability", "--input", relative)
        self.assertNotEqual(record.returncode, 0)
        self.assertIn("all candidates", record.stderr.lower())

        full_relative = self.write_draft(
            "full-missing-capability",
            {
                "capability_id": "local_transcription",
                "status": "missing",
                "selected": None,
                "fallback": "use_capability_fallback",
                "probes": [
                    {
                        "candidate_id": candidate,
                        "result": "missing",
                        "evidence_refs": ["evidence/probe.json"],
                    }
                    for candidate in CAPABILITY_CANDIDATES["local_transcription"]
                ],
                "checked_at": "2026-07-11T00:09:01Z",
            },
        )
        recorded = self.cli("record-capability", "--input", full_relative)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        self.record_full_coverage()
        self.record_required_decisions()
        frozen = self.finalize()
        self.assertEqual(frozen.returncode, 0, frozen.stderr)

        runtime_path = self.run_dir / "runtime-capabilities.json"
        runtime = json.loads(runtime_path.read_text())
        runtime["capabilities"]["local_transcription"]["probes"] = runtime[
            "capabilities"
        ]["local_transcription"]["probes"][:1]
        runtime["capabilities"]["local_transcription"][
            "fallback"
        ] = "continue_to_next_candidate"
        self._write_json(runtime_path, runtime)
        run_path = self.run_dir / "run.json"
        run = json.loads(run_path.read_text())
        run["extensions"]["learning_loop"]["sidecars"][
            "runtime-capabilities.json"
        ]["sha256"] = digest(runtime_path)
        self._write_json(run_path, run)
        validation = subprocess.run(
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
            ],
            text=True,
            capture_output=True,
        )
        errors = "\n".join(json.loads(validation.stdout)["errors"])
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("all candidates", errors.lower())

    def test_finalize_with_full_coverage_freezes_and_reuses_identical_bytes(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()

        first = self.finalize()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = (self.run_dir / "run.json").read_bytes()
        run = json.loads(before)
        self.assertEqual(run["extensions"]["learning_loop"]["state"], "frozen")
        for name in ("skill-usage-manifest.json", "usage-ledger.json", "retrospective.json"):
            self.assertIn(name, run["extensions"]["learning_loop"]["sidecars"])

        second = self.finalize()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((self.run_dir / "run.json").read_bytes(), before)

    def test_finalize_requires_three_auditable_decision_points(self) -> None:
        self.record_full_coverage()
        result = self.finalize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decision", result.stderr.lower())
        self.assertEqual(
            json.loads((self.run_dir / "run.json").read_text())["extensions"]
            ["learning_loop"]["state"],
            "collecting",
        )

    def test_finalize_rejects_unproven_manifest_and_non_backlog_finding(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        manifest, ledger, retrospective = self._finalize_drafts()
        manifest_path = self.run_dir / manifest
        manifest_value = json.loads(manifest_path.read_text())
        manifest_value["entries"][0]["outputs"] = ["evidence/missing.json"]
        self._write_json(manifest_path, manifest_value)
        result = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, r"output|不存在")

        manifest, ledger, retrospective = self._finalize_drafts()
        retrospective_path = self.run_dir / retrospective
        retrospective_value = json.loads(retrospective_path.read_text())
        retrospective_value["findings"] = [
            {
                "type": "effective_pattern",
                "claim": "一次观察还不能形成规则",
                "evidence_refs": [],
                "applies_to": ["tutorial-demo"],
                "destination_candidate": "reference",
                "status": "candidate",
                "basis": "guess",
            }
        ]
        self._write_json(retrospective_path, retrospective_value)
        result = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backlog", result.stderr)

    def test_finalize_fault_rolls_back_outputs_and_conflicting_retry_cannot_overwrite(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        manifest, ledger, retrospective = self._finalize_drafts()
        env = dict(os.environ)
        env["AI_VIDEO_FLOW_LEARNING_FAULT"] = "after-output-1"
        failed = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
            env=env,
        )
        self.assertNotEqual(failed.returncode, 0)
        for name in ("skill-usage-manifest.json", "usage-ledger.json", "retrospective.json"):
            self.assertFalse((self.run_dir / name).exists())
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(run["extensions"]["learning_loop"]["state"], "collecting")

        succeeded = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertEqual(succeeded.returncode, 0, succeeded.stderr)
        frozen = (self.run_dir / "retrospective.json").read_bytes()
        changed = json.loads((self.run_dir / retrospective).read_text())
        changed["objective"] = "冲突重试不得覆盖"
        self._write_json(self.run_dir / retrospective, changed)
        conflict = self.cli(
            "finalize",
            "--manifest-input",
            manifest,
            "--ledger-input",
            ledger,
            "--retrospective-input",
            retrospective,
        )
        self.assertNotEqual(conflict.returncode, 0)
        self.assertEqual((self.run_dir / "retrospective.json").read_bytes(), frozen)

    def test_concurrent_normal_and_fault_finalize_never_deletes_frozen_winner(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        manifest, ledger, retrospective = self._finalize_drafts()

        def invoke(fault: bool) -> subprocess.CompletedProcess[str]:
            env = dict(os.environ)
            if fault:
                env["AI_VIDEO_FLOW_LEARNING_FAULT"] = "after-output-1"
            return self.cli(
                "finalize",
                "--manifest-input",
                manifest,
                "--ledger-input",
                ledger,
                "--retrospective-input",
                retrospective,
                env=env,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(invoke, (False, True)))
        self.assertTrue(any(result.returncode == 0 for result in results))
        run = json.loads((self.run_dir / "run.json").read_text())
        self.assertEqual(run["extensions"]["learning_loop"]["state"], "frozen")
        for name in (
            "skill-usage-manifest.json",
            "usage-ledger.json",
            "retrospective.json",
        ):
            self.assertTrue((self.run_dir / name).is_file())

    def test_finalize_rejects_drifted_core_binding_before_writing_sidecars(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        run_path = self.run_dir / "run.json"
        run = json.loads(run_path.read_text())
        run["artifacts"]["finalize"]["sha256"] = "f" * 64
        self._write_json(run_path, run)
        result = self.finalize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("binding", result.stderr.lower())
        self.assertFalse((self.run_dir / "skill-usage-manifest.json").exists())

    def test_finalize_rejects_url_source_hash_not_backed_by_ingested_bytes(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        ingested = self.run_dir / "ingested.mp4"
        ingested.write_bytes(b"actual-downloaded-media")
        ingest = self.run_dir / "core-ingest.json"
        self._write_json(
            ingest,
            {
                "artifact_type": "ingest",
                "local_media_path": "ingested.mp4",
                "media_sha256": digest(ingested),
            },
        )
        run_path = self.run_dir / "run.json"
        run = json.loads(run_path.read_text())
        run["source"] = {
            "kind": "url",
            "source_id": "source-runtime",
            "media_sha256": "f" * 64,
            "fingerprint_state": "verified",
        }
        run["artifacts"]["ingest"] = {
            "path": "core-ingest.json",
            "sha256": digest(ingest),
        }
        self._write_json(run_path, run)
        link_coverage = self.record_usage(
            {
                "event_id": "url-link-ingest",
                "kind": "tool",
                "stage": "ingest",
                "capability_id": "link_ingest",
                "actual_id": "video_to_text",
                "purpose": "URL capability coverage",
                "result": "not_recorded",
                "capture_state": "not_recorded",
                "evidence_refs": [],
                "version": None,
                "execution_receipt": None,
                "recorded_at": "2026-07-11T00:08:00Z",
            }
        )
        self.assertEqual(link_coverage.returncode, 0, link_coverage.stderr)
        result = self.finalize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("url core binding", result.stderr.lower())
        self.assertFalse((self.run_dir / "skill-usage-manifest.json").exists())

    def test_validator_rehashes_nested_learning_evidence_and_coverage(self) -> None:
        self.record_full_coverage()
        self.record_required_decisions()
        result = self.finalize()
        self.assertEqual(result.returncode, 0, result.stderr)

        manifest_path = self.run_dir / "skill-usage-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["entries"][0]["evidence_refs"][0]["sha256"] = "f" * 64
        self._write_json(manifest_path, manifest)
        run_path = self.run_dir / "run.json"
        run = json.loads(run_path.read_text())
        run["extensions"]["learning_loop"]["sidecars"][
            "skill-usage-manifest.json"
        ]["sha256"] = digest(manifest_path)
        self._write_json(run_path, run)

        validation = subprocess.run(
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
            ],
            text=True,
            capture_output=True,
        )
        payload = json.loads(validation.stdout)
        self.assertNotEqual(validation.returncode, 0)
        errors = "\n".join(payload["errors"])
        self.assertIn("manifest", errors.lower())
        self.assertIn("evidence", errors.lower())


if __name__ == "__main__":
    unittest.main()
