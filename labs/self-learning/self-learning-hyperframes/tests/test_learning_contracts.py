from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
CURRENT = REFERENCES / "workflow.json"
V1 = REFERENCES / "workflows" / "1.0.0.json"
V11 = REFERENCES / "workflows" / "1.1.0.json"
LEARNING_CONTRACT = REFERENCES / "learning-contract.json"
FROZEN_LEARNING_CONTRACT = REFERENCES / "learning-contracts" / "1.0.0.json"
CAPABILITIES = REFERENCES / "capabilities.json"
FROZEN_CAPABILITIES = REFERENCES / "capability-registries" / "1.0.0.json"
RUBRIC = REFERENCES / "rubric.json"
INIT_RUN = SKILL_ROOT / "scripts" / "init_run.py"

STAGE_IDS = [
    "preflight",
    "ingest",
    "transcript",
    "learn_method",
    "observe_motion",
    "plan_demo",
    "build",
    "verify",
    "review_r1",
    "revise",
    "review_r2",
    "finalize",
]

REQUIRED_ARTIFACTS = {
    "memory-selection.json",
    "runtime-capabilities.json",
    "decision-trace.json",
    "skill-usage-manifest.json",
    "usage-ledger.json",
    "retrospective.json",
}


class LearningContractTests(unittest.TestCase):
    def load_json(self, path: Path) -> dict[str, Any]:
        self.assertTrue(path.is_file(), f"缺少契约文件：{path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        return payload

    def test_all_contract_json_files_are_parseable_objects(self) -> None:
        for path in (
            CURRENT,
            V1,
            V11,
            LEARNING_CONTRACT,
            FROZEN_LEARNING_CONTRACT,
            CAPABILITIES,
            FROZEN_CAPABILITIES,
            RUBRIC,
        ):
            with self.subTest(path=path.name):
                self.load_json(path)

    def test_frozen_v1_workflow_preserves_original_hash(self) -> None:
        self.assertTrue(V1.is_file(), f"缺少冻结 workflow：{V1}")
        self.assertEqual(
            hashlib.sha256(V1.read_bytes()).hexdigest(),
            "ba38112d9af58bb268b8052cde776928a1a1d24ed7b5afa783f6dc32fb973ab8",
        )

    def test_current_and_v11_workflows_are_byte_identical(self) -> None:
        self.assertTrue(V11.is_file(), f"缺少 workflow 1.1：{V11}")
        self.assertEqual(CURRENT.read_bytes(), V11.read_bytes())

    def test_learning_contract_is_frozen_and_hash_pinned_by_v11(self) -> None:
        self.assertTrue(
            FROZEN_LEARNING_CONTRACT.is_file(),
            f"缺少冻结 learning contract：{FROZEN_LEARNING_CONTRACT}",
        )
        self.assertEqual(
            LEARNING_CONTRACT.read_bytes(), FROZEN_LEARNING_CONTRACT.read_bytes()
        )
        frozen_hash = hashlib.sha256(FROZEN_LEARNING_CONTRACT.read_bytes()).hexdigest()
        extension = self.load_json(V11)["learning_extension"]
        self.assertEqual(extension["contract_allowlist"], ["1.0.0"])
        self.assertEqual(extension["contract_version"], "1.0.0")
        self.assertEqual(extension["contract_sha256"], frozen_hash)

    def test_v11_preserves_the_original_twelve_stage_machine(self) -> None:
        v1 = self.load_json(V1)
        v11 = self.load_json(V11)
        self.assertEqual([stage["id"] for stage in v1["stages"]], STAGE_IDS)
        self.assertEqual([stage["id"] for stage in v11["stages"]], STAGE_IDS)
        self.assertEqual(v11["stages"], v1["stages"])
        self.assertEqual(v1["workflow_version"], "1.0.0")
        self.assertEqual(v11["workflow_version"], "1.1.0")

    def test_v11_declares_terminal_and_post_run_sidecar_boundaries(self) -> None:
        extension = self.load_json(V11)["learning_extension"]
        self.assertEqual(extension["contract_version"], "1.0.0")
        self.assertIn("contract_allowlist", extension)
        self.assertIn("contract_sha256", extension)
        self.assertEqual(extension["contract_allowlist"], ["1.0.0"])
        self.assertRegex(extension["contract_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(extension["extension_key"], "learning_loop")
        self.assertTrue(extension["required"])
        self.assertEqual(extension["selection"]["path"], "memory-selection.json")
        self.assertEqual(extension["selection"]["required_after_stage"], "preflight")
        self.assertEqual(
            {entry["path"] for entry in extension["required_sidecars"]},
            REQUIRED_ARTIFACTS - {"memory-selection.json"},
        )
        self.assertTrue(
            all(
                entry["required_after_stage"] == "finalize"
                and "required_at" not in entry
                for entry in extension["required_sidecars"]
            )
        )
        self.assertEqual(
            extension["variable_sidecars"],
            [
                {
                    "path_pattern": "usage-events/*.json",
                    "coverage": "completed_stage_workflow_capability",
                    "required_after_stage": "finalize",
                }
            ],
        )
        self.assertEqual(
            extension["post_run_optional_sidecars"],
            [
                {
                    "path_pattern": "feedback-candidates/*.json",
                    "trigger": "on_feedback",
                    "descriptor_policy": "append_new_key_only",
                },
                {
                    "path_pattern": "promotion-receipts/*.json",
                    "trigger": "on_promotion",
                    "descriptor_policy": "append_new_key_only",
                },
            ],
        )

    def test_extension_contract_has_one_shape_and_bounded_states(self) -> None:
        extension = self.load_json(LEARNING_CONTRACT)["extension"]
        self.assertEqual(extension["key"], "learning_loop")
        self.assertEqual(
            extension["required_fields"],
            ["required", "state", "contract_version", "selection", "sidecars"],
        )
        self.assertEqual(
            set(extension["state_enum"]), {"collecting", "frozen", "backfilled"}
        )
        self.assertEqual(
            extension["selection_descriptor"],
            {
                "path": "memory-selection.json",
                "fields": ["path", "sha256"],
                "nullable_before": "preflight_completed",
            },
        )
        self.assertEqual(
            extension["sidecars"],
            {
                "type": "object",
                "key_equals_descriptor_path": True,
                "descriptor_fields": ["path", "sha256"],
            },
        )

    def test_learning_artifact_contract_matches_workflow_boundaries(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        artifacts = contract["artifacts"]
        self.assertEqual(set(artifacts["required"]), REQUIRED_ARTIFACTS)
        self.assertEqual(
            artifacts["variable_required"],
            {
                "path_pattern": "usage-events/*.json",
                "coverage": "completed_stage_workflow_capability",
            },
        )
        self.assertEqual(
            set(artifacts["post_run_optional"]),
            {"feedback-candidates/*.json", "promotion-receipts/*.json"},
        )

    def test_usage_event_contract_has_real_kind_branches_and_finite_results(self) -> None:
        usage = self.load_json(LEARNING_CONTRACT)["usage_event"]
        self.assertEqual(set(usage["kind_enum"]), {"content", "skill", "tool"})
        self.assertEqual(
            set(usage["capture_state_enum"]),
            {"captured", "missing", "degraded", "not_recorded"},
        )
        self.assertEqual(
            set(usage["result_enum"]),
            {"passed", "degraded", "failed", "not_recorded"},
        )
        branches = usage["branches"]
        self.assertEqual(set(branches), set(usage["kind_enum"]))
        self.assertEqual(
            branches["content"],
            {
                "required_fields": ["content_ref", "content_sha256"],
                "execution_receipt": "forbidden",
            },
        )
        for kind in ("skill", "tool"):
            self.assertEqual(branches[kind]["required_fields"], ["version", "execution_receipt"])
            self.assertEqual(branches[kind]["execution_receipt"], "required_when_captured")

    def test_runtime_capability_and_execution_receipt_schemas_are_machine_bounded(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        runtime = contract["runtime_capabilities"]
        self.assertEqual(runtime["capabilities_type"], "object_by_capability_id")
        self.assertEqual(
            set(runtime["status_enum"]), {"available", "degraded", "missing"}
        )
        self.assertEqual(
            set(runtime["probe_result_enum"]), {"passed", "degraded", "failed", "missing"}
        )
        self.assertEqual(runtime["probe_field"], "probes")
        self.assertEqual(runtime["ordered_fallback_selected_type"], "string_or_null")
        self.assertEqual(runtime["all_selected_type"], "array")
        self.assertTrue(runtime["all_requires_every_candidate"])

        receipt = contract["execution_receipt"]
        self.assertEqual(
            receipt["required_fields"],
            ["receipt_type", "command", "exit_code", "executed_at"],
        )
        self.assertEqual(receipt["receipt_type"], "execution")
        self.assertEqual(receipt["command"], "nonempty_string_array")
        self.assertEqual(receipt["exit_code"], "integer_not_boolean")
        self.assertEqual(receipt["executed_at"], "rfc3339_timezone_aware")
        self.assertEqual(
            set(receipt["optional_reference_fields"]), {"stdout", "stderr", "target"}
        )
        self.assertEqual(receipt["result_binding"]["passed"], "exit_code_zero")
        self.assertEqual(receipt["result_binding"]["failed"], "exit_code_nonzero")

    def test_retrospective_contract_is_complete_without_inventing_review_rules(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        self.assertIn("retrospective", contract)
        retrospective = contract["retrospective"]
        self.assertEqual(
            retrospective["required_fields"],
            [
                "schema_version",
                "workflow_version",
                "run_id",
                "objective",
                "result",
                "skills_manifest_ref",
                "evidence",
                "findings",
            ],
        )
        self.assertEqual(
            retrospective["result_enum"], ["success", "success_with_residuals"]
        )
        self.assertEqual(
            retrospective["finding_required_fields"],
            [
                "type",
                "claim",
                "evidence_refs",
                "applies_to",
                "destination_candidate",
                "status",
            ],
        )
        self.assertEqual(
            set(retrospective["finding_type_enum"]),
            {
                "effective_pattern",
                "failure_root_cause",
                "environment_fact",
                "skill_friction",
            },
        )
        self.assertEqual(
            set(retrospective["destination_enum"]),
            {"reference", "local_memory", "error_memory", "skill_adjustment", "backlog"},
        )
        self.assertEqual(retrospective["status_enum"], ["candidate"])
        self.assertEqual(
            retrospective["without_evidence"],
            {"destination": "backlog", "promotable": False},
        )

    def test_coverage_selection_and_finalize_are_machine_bounded(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        self.assertEqual(
            contract["coverage"],
            {
                "scope": "completed_stage_workflow_capability",
                "satisfied_by": ["captured_event", "explicit_coverage_event"],
                "explicit_capture_states": ["missing", "degraded", "not_recorded"],
                "silent_absence": "finalize_fails",
            },
        )
        self.assertEqual(
            contract["selection_limits"],
            {
                "root_indexes": 1,
                "topic_maps": 1,
                "cross_domain_topic_maps": 2,
                "memory_items_min": 0,
                "memory_items_max": 3,
            },
        )
        self.assertEqual(
            contract["finalize"]["write_order"],
            [
                "skill-usage-manifest.json",
                "usage-ledger.json",
                "retrospective.json",
                "state=frozen",
            ],
        )
        self.assertEqual(
            contract["finalize"]["state_transition"],
            {"from": "collecting", "to": "frozen", "atomic": True},
        )

    def test_manifest_results_and_candidate_destinations_require_evidence(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        manifest = contract["skill_usage_manifest"]
        self.assertTrue(
            {
                "capability",
                "phase",
                "candidates_checked",
                "selected",
                "source",
                "revision",
                "mode",
                "inputs",
                "outputs",
                "result",
                "evidence_refs",
                "friction",
                "adjustment_candidate",
            }.issubset(manifest["entry_required_fields"])
        )
        self.assertEqual(manifest["passed_requires"], ["actual_output_or_receipt"])

        candidates = contract["candidates"]
        self.assertEqual(
            set(candidates["destination_enum"]),
            {"reference", "local_memory", "error_memory", "skill_adjustment", "backlog"},
        )
        self.assertEqual(candidates["no_evidence_destination"], "backlog")
        self.assertEqual(candidates["default_state"], "candidate")
        self.assertEqual(
            candidates["post_run_paths"],
            {
                "feedback": "feedback-candidates/*.json",
                "promotion_receipt": "promotion-receipts/*.json",
            },
        )

    def test_post_run_descriptors_are_append_only_while_frozen_facts_stay_immutable(self) -> None:
        contract = self.load_json(LEARNING_CONTRACT)
        self.assertIn("post_run_append_only", contract)
        policy = contract["post_run_append_only"]
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            (repo / "demos").mkdir(parents=True)
            source = Path(root) / "tutorial.mp4"
            source.write_bytes(b"private-media")
            result = subprocess.run(
                [
                    sys.executable,
                    str(INIT_RUN),
                    "start",
                    "--repo",
                    str(repo),
                    "--run-id",
                    "contract-run",
                    "--source",
                    str(source),
                    "--json",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            generated_run = json.loads(
                (repo / ".learning" / "runs" / "contract-run" / "run.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(policy["allowed_states"], ["frozen", "backfilled"])
        self.assertEqual(
            policy["allowed_path_patterns"],
            ["feedback-candidates/*.json", "promotion-receipts/*.json"],
        )
        self.assertEqual(
            policy["descriptor_target"], "extensions.learning_loop.sidecars"
        )
        self.assertEqual(policy["operation"], "add_new_key_only")
        self.assertIn("run_mutation_allowlist", policy)
        self.assertIn("immutable_run_fields", policy)
        self.assertIn("immutable_artifact_paths", policy)
        self.assertEqual(
            policy["run_mutation_allowlist"],
            ["extensions.learning_loop.sidecars.<new-key>"],
        )

        immutable_run_fields = set(policy["immutable_run_fields"])
        self.assertTrue(set(generated_run).issubset(immutable_run_fields))
        self.assertTrue(
            {
                "extensions.learning_loop.required",
                "extensions.learning_loop.state",
                "extensions.learning_loop.contract_version",
                "extensions.learning_loop.selection",
                "extensions.learning_loop.sidecars.<existing-key>",
            }.issubset(immutable_run_fields)
        )
        self.assertNotIn("core_artifacts", immutable_run_fields)
        self.assertFalse(any(path.endswith(".json") for path in immutable_run_fields))

        immutable_artifact_paths = set(policy["immutable_artifact_paths"])
        self.assertTrue(
            {
                "final.json",
                "score-r2.json",
                "retrospective.json",
                "skill-usage-manifest.json",
                "usage-ledger.json",
            }.issubset(immutable_artifact_paths)
        )
        self.assertTrue(
            {
                "memory-selection.json",
                "runtime-capabilities.json",
                "decision-trace.json",
                "usage-events/*.json",
            }.issubset(immutable_artifact_paths)
        )

    def test_capability_registry_is_stable_and_candidates_define_probe_order(self) -> None:
        registry = self.load_json(CAPABILITIES)
        self.assertIn("registry_kind", registry)
        self.assertIn("runtime_state_destination", registry)
        self.assertEqual(registry["registry_kind"], "stable_capability_slots")
        self.assertEqual(
            registry["runtime_state_destination"], "runtime-capabilities.json"
        )
        self.assertIn("default_candidate_mode", registry["policy"])
        self.assertEqual(registry["policy"]["default_candidate_mode"], "ordered_fallback")
        forbidden_runtime_keys = {
            "available",
            "checked_at",
            "probed_at",
            "selected",
            "status",
        }
        environment = next(
            capability
            for capability in registry["capabilities"]
            if capability["id"] == "environment_probe"
        )
        self.assertEqual(environment["candidate_mode"], "all")
        self.assertEqual(
            environment["aggregate_result"],
            "record_each_probe_without_short_circuit",
        )
        self.assertEqual(len(environment["candidates"]), 2)
        self.assertTrue(
            all(
                candidate["fallback"] == "record_missing_and_continue"
                for candidate in environment["candidates"]
            )
        )

        for capability in registry["capabilities"]:
            priorities: list[int] = []
            for candidate in capability["candidates"]:
                self.assertEqual(
                    {"id", "priority", "probe", "fallback"} - set(candidate), set()
                )
                self.assertIsInstance(candidate["priority"], int)
                self.assertGreater(candidate["priority"], 0)
                self.assertIsInstance(candidate["probe"], dict)
                self.assertTrue(candidate["probe"]["side_effect_free"])
                self.assertIsInstance(candidate["fallback"], str)
                self.assertTrue(candidate["fallback"])
                priorities.append(candidate["priority"])
            self.assertEqual(priorities, sorted(priorities))
            self.assertEqual(len(priorities), len(set(priorities)))
            if capability["id"] != "environment_probe":
                self.assertEqual(
                    capability.get(
                        "candidate_mode", registry["policy"]["default_candidate_mode"]
                    ),
                    "ordered_fallback",
                )
                for candidate in capability["candidates"][:-1]:
                    self.assertEqual(candidate["fallback"], "continue_to_next_candidate")
                self.assertEqual(
                    capability["candidates"][-1]["fallback"],
                    "use_capability_fallback",
                )

        def walk_keys(value: Any) -> set[str]:
            if isinstance(value, dict):
                return set(value) | {key for child in value.values() for key in walk_keys(child)}
            if isinstance(value, list):
                return {key for child in value for key in walk_keys(child)}
            return set()

        self.assertFalse(forbidden_runtime_keys & walk_keys(registry))

    def test_capability_registry_is_frozen_and_hash_pinned_by_v11(self) -> None:
        self.assertEqual(CAPABILITIES.read_bytes(), FROZEN_CAPABILITIES.read_bytes())
        registry = self.load_json(FROZEN_CAPABILITIES)
        self.assertEqual(registry["registry_version"], "1.0.0")
        extension = self.load_json(V11)["learning_extension"]
        self.assertEqual(extension["capability_registry_version"], "1.0.0")
        self.assertEqual(
            extension["capability_registry_sha256"],
            hashlib.sha256(FROZEN_CAPABILITIES.read_bytes()).hexdigest(),
        )

    def test_low_scores_and_r2_residuals_are_candidate_only(self) -> None:
        rubric = self.load_json(RUBRIC)
        self.assertIn("learning_candidate_policy", rubric)
        policy = rubric["learning_candidate_policy"]
        self.assertEqual(
            set(policy["candidate_only_inputs"]),
            {"low_score", "r2_residual", "aesthetic_opinion", "single_failure"},
        )
        self.assertEqual(policy["default_destination"], "backlog")
        self.assertTrue(policy["never_activate_memory_directly"])
        self.assertEqual(
            set(policy["promotion_requires"]), {"evidence_refs", "revalidation"}
        )


if __name__ == "__main__":
    unittest.main()
