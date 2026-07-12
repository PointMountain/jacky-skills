from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
EXTRACTION_PROTOCOL = SKILL_ROOT / "references" / "extraction-protocol.md"
LEARNING_LOOP = SKILL_ROOT / "references" / "learning-loop.md"

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

EXTRACTION_CARDS = [
    "来源摄取",
    "音轨识别",
    "时间码字幕",
    "cue 复核",
    "粗抽帧",
    "关键段密集抽帧",
    "小主体放大",
    "屏幕代码取证",
    "事实分层",
    "method/motion 交接",
    "异常回退与候选",
]

SIDECAR_RELATIONS = {
    "memory-selection.json": ("preflight", "after_preflight", "required"),
    "runtime-capabilities.json": ("preflight", "after_probe", "required"),
    "decision-trace.json": ("all", "on_decision", "required"),
    "usage-events/*.json": ("all", "after_usage_or_coverage", "required"),
    "skill-usage-manifest.json": ("finalize", "on_finalize", "required"),
    "usage-ledger.json": ("finalize", "on_finalize", "required"),
    "retrospective.json": ("finalize", "on_finalize", "required"),
    "feedback-candidates/*.json": ("post_run", "on_feedback", "optional"),
    "promotion-receipts/*.json": ("post_run", "on_promotion", "optional"),
}

def markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^## |\Z)", text)
    if not match:
        raise AssertionError(f"missing Markdown section: {heading}")
    return match.group(1)


def first_markdown_table(section: str) -> tuple[list[str], list[list[str]]]:
    table_lines = [line for line in section.splitlines() if line.startswith("|")]
    if len(table_lines) < 3:
        raise AssertionError("missing Markdown table")
    parsed = [[cell.strip() for cell in line.strip("|").split("|")] for line in table_lines]
    headers, separator, *rows = parsed
    if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        raise AssertionError("invalid Markdown table separator")
    if any(len(row) != len(headers) for row in rows):
        raise AssertionError("Markdown table row width differs from header")
    return headers, rows


def code_value(cell: str) -> str:
    return cell.strip().strip("`")


def csv_tokens(cell: str) -> set[str]:
    return {code_value(token.strip()) for token in cell.split(",") if token.strip()}


def csv_list(cell: str) -> list[str]:
    return [code_value(token.strip()) for token in cell.split(",") if token.strip()]


def path_matches(pattern: str, path: str) -> bool:
    regex = "^" + re.escape(pattern).replace(r"\*", "[^/]+") + "$"
    return re.fullmatch(regex, path) is not None


def json_blocks(section: str) -> list[dict[str, object]]:
    return [
        json.loads(raw)
        for raw in re.findall(r"(?ms)```json\n(.*?)\n```", section)
    ]


def parse_shallow_yaml(text: str) -> dict[str, dict[str, str]]:
    """解析本文件需要的两层、带引号字符串 YAML，不引入 PyYAML。"""

    result: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            if not raw_line.endswith(":"):
                raise AssertionError(f"line {line_number}: expected top-level mapping")
            current = {}
            result[raw_line[:-1]] = current
            continue
        if current is None or not raw_line.startswith("  ") or raw_line.startswith("    "):
            raise AssertionError(f"line {line_number}: expected two-space scalar")
        key, separator, raw_value = raw_line.strip().partition(":")
        if not separator or not raw_value.strip():
            raise AssertionError(f"line {line_number}: expected key/value scalar")
        try:
            value = ast.literal_eval(raw_value.strip())
        except (SyntaxError, ValueError) as error:
            raise AssertionError(f"line {line_number}: expected quoted scalar") from error
        if not isinstance(value, str):
            raise AssertionError(f"line {line_number}: expected string scalar")
        current[key] = value
    return result


class LearningDocsTests(unittest.TestCase):
    def test_runtime_capabilities_and_execution_receipts_have_one_machine_shape(self) -> None:
        text = LEARNING_LOOP.read_text(encoding="utf-8")
        self.assertIn("capabilities{}", text)
        self.assertNotIn("capabilities[]", text)
        self.assertIn("probes[]", text)
        self.assertIn("receipt_type=execution", text)
        self.assertIn("RFC3339", text)

    def test_skill_is_a_thin_map_and_all_markdown_targets_exist(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 200)
        local_targets = {
            target.split("#", 1)[0]
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
            if not re.match(r"^[a-z]+://", target)
        }
        self.assertTrue(
            {
                "references/extraction-protocol.md",
                "references/learning-loop.md",
            }.issubset(local_targets)
        )
        for target in sorted(local_targets):
            with self.subTest(target=target):
                self.assertFalse(Path(target).is_absolute())
                self.assertTrue((SKILL_ROOT / target).is_file())

    def test_skill_declares_the_exact_twelve_stage_order(self) -> None:
        section = markdown_section(SKILL_MD.read_text(encoding="utf-8"), "## 12 阶段")
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["阶段", "核心动作", "主要交付"])
        self.assertEqual([code_value(row[0]) for row in rows], STAGE_IDS)

    def test_extraction_protocol_has_ordered_executable_cards(self) -> None:
        text = EXTRACTION_PROTOCOL.read_text(encoding="utf-8")
        cards = re.findall(
            r"(?ms)^## 卡片 (\d+)：([^\n]+)\n(.*?)(?=^## 卡片 \d+：|\Z)",
            text,
        )
        self.assertEqual([int(number) for number, _, _ in cards], list(range(1, 12)))
        self.assertEqual([title for _, title, _ in cards], EXTRACTION_CARDS)
        expected_fields = {
            "触发",
            "输入",
            "观察",
            "证据",
            "判断",
            "行动",
            "产物",
            "Must-pass",
            "Fallback",
        }
        for number, title, body in cards:
            fields = {
                name: value
                for name, value in re.findall(r"(?m)^- \*\*([^*]+)\*\*：(.+)$", body)
            }
            with self.subTest(card=number, title=title):
                self.assertEqual(set(fields), expected_fields)
                self.assertTrue(all(value.strip() for value in fields.values()))

    def test_sidecar_table_normalizes_to_path_stage_trigger_and_requirement(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Workflow 1.1.0 sidecars"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["相对路径", "阶段", "触发", "必需性", "机器事实"])
        actual = {
            code_value(row[0]): tuple(code_value(value) for value in row[1:4])
            for row in rows
        }
        self.assertEqual(actual, SIDECAR_RELATIONS)
        self.assertTrue(all(row[4].strip() for row in rows))

    def test_memory_selection_is_required_even_when_no_memory_matches(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Phase 0 memory selection"
        )
        examples = json_blocks(section)
        self.assertEqual(len(examples), 1)
        selection = examples[0]
        required = {
            "schema_version",
            "workflow_version",
            "run_id",
            "selected",
            "rejected",
            "selection_snapshot",
            "selection_snapshot_sha256",
        }
        self.assertTrue(required.issubset(selection))
        self.assertEqual(selection["workflow_version"], "1.1.0")
        self.assertEqual(selection["selected"], [])
        self.assertEqual(selection["rejected"], [])
        self.assertIn("empty_selection_required", csv_tokens(first_markdown_table(section)[1][0][1]))
        self.assertIn("no_empty_local", csv_tokens(first_markdown_table(section)[1][0][1]))

    def test_extension_examples_use_the_single_collecting_and_frozen_shape(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## run.json extension 与校验"
        )
        initial, frozen = json_blocks(section)
        self.assertEqual(initial["workflow_version"], "1.1.0")
        self.assertEqual(
            initial["extensions"]["learning_loop"],
            {
                "required": True,
                "state": "collecting",
                "contract_version": "1.0.0",
                "selection": None,
                "sidecars": {},
            },
        )

        extension = frozen["extensions"]["learning_loop"]
        self.assertEqual(set(extension), set(initial["extensions"]["learning_loop"]))
        self.assertEqual(extension["state"], "frozen")
        self.assertEqual(set(extension["selection"]), {"path", "sha256"})
        self.assertEqual(extension["selection"]["path"], "memory-selection.json")
        self.assertIsInstance(extension["sidecars"], dict)
        self.assertTrue(extension["sidecars"])
        for name, descriptor in extension["sidecars"].items():
            self.assertEqual(name, descriptor["path"])
            self.assertEqual(set(descriptor), {"path", "sha256"})

    def test_completed_example_covers_every_required_sidecar_descriptor(self) -> None:
        text = LEARNING_LOOP.read_text(encoding="utf-8")
        relation_rows = first_markdown_table(
            markdown_section(text, "## Workflow 1.1.0 sidecars")
        )[1]
        required_patterns = [
            code_value(row[0]) for row in relation_rows if code_value(row[3]) == "required"
        ]
        frozen = json_blocks(markdown_section(text, "## run.json extension 与校验"))[1]
        extension = frozen["extensions"]["learning_loop"]
        sidecar_paths = set(extension["sidecars"])

        self.assertEqual(extension["selection"]["path"], "memory-selection.json")
        self.assertNotIn("memory-selection.json", sidecar_paths)
        for pattern in required_patterns:
            if pattern == "memory-selection.json":
                continue
            with self.subTest(pattern=pattern):
                self.assertTrue(any(path_matches(pattern, path) for path in sidecar_paths))

    def test_usage_kind_branches_have_distinct_evidence_contracts(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Usage event kind 分支"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["kind", "特有字段", "receipt 策略"])
        actual = {
            code_value(row[0]): (csv_tokens(row[1]), code_value(row[2])) for row in rows
        }
        self.assertEqual(set(actual), {"content", "skill", "tool"})
        self.assertTrue({"content_ref", "content_sha256"}.issubset(actual["content"][0]))
        self.assertEqual(actual["content"][1], "forbidden")
        for kind in ("skill", "tool"):
            self.assertTrue(
                {"version", "execution_receipt.path", "execution_receipt.sha256"}.issubset(
                    actual[kind][0]
                )
            )
            self.assertEqual(actual[kind][1], "required_when_captured")

    def test_usage_coverage_prevents_silent_stage_capability_gaps(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Usage coverage"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["规则", "结构约束"])
        rules = {code_value(row[0]): csv_tokens(row[1]) for row in rows}
        self.assertEqual(
            rules["capture_state_enum"],
            {"captured", "missing", "degraded", "not_recorded"},
        )
        self.assertEqual(
            rules["stage_capability"],
            {"completed_stage", "workflow_capability", "event_or_coverage"},
        )
        self.assertEqual(rules["silent_absence"], {"finalize_fails"})
        self.assertEqual(
            rules["evidence_hash"],
            {"record-usage", "read_evidence_refs", "recompute_sha256", "reject_self_reported_hash"},
        )

    def test_each_stage_declares_usage_event_or_coverage(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## 各阶段写入纪律"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["阶段", "usage 规则", "额外 sidecar"])
        self.assertEqual([code_value(row[0]) for row in rows], STAGE_IDS)
        self.assertTrue(all(code_value(row[1]) == "event_or_coverage" for row in rows))
        extras = {code_value(row[0]): csv_tokens(row[2]) for row in rows}
        self.assertTrue(
            {"runtime-capabilities", "memory-selection"}.issubset(extras["preflight"])
        )
        self.assertIn("decision-trace", extras["plan_demo"])
        self.assertIn("decision-trace", extras["revise"])
        finalize_row = next(row for row in rows if code_value(row[0]) == "finalize")
        self.assertEqual(
            csv_list(finalize_row[2]),
            ["skill-usage-manifest", "usage-ledger", "retrospective", "state=frozen"],
        )

    def test_finalize_freezes_core_learning_and_feedback_is_append_only(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Freeze 与 post-run feedback"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["时期", "允许写入", "禁止改写"])
        boundaries = {
            code_value(row[0]): (csv_tokens(row[1]), csv_tokens(row[2])) for row in rows
        }
        finalize_row = next(row for row in rows if code_value(row[0]) == "finalize")
        self.assertEqual(
            csv_list(finalize_row[1]),
            ["skill-usage-manifest", "usage-ledger", "retrospective", "state=frozen"],
        )
        self.assertEqual(
            boundaries["post_run"][0], {"feedback-candidate", "promotion-receipt"}
        )
        self.assertTrue(
            {"retrospective", "final", "skill-usage-manifest", "usage-ledger"}.issubset(
                boundaries["post_run"][1]
            )
        )

    def test_finalize_order_is_consistent_and_supports_retrospective_reference(self) -> None:
        text = LEARNING_LOOP.read_text(encoding="utf-8")
        expected = [
            "skill-usage-manifest",
            "usage-ledger",
            "retrospective",
            "state=frozen",
        ]
        preamble = text.split("##", 1)[0]
        flow_tokens = [token for token in re.findall(r"`([^`]+)`", preamble) if token in expected]
        self.assertEqual(flow_tokens, expected)

        freeze = markdown_section(text, "## Freeze 与 post-run feedback")
        self.assertRegex(freeze, r"三个.*draft.*同批校验")
        self.assertIn("skills_manifest_ref", freeze)

        settlement = markdown_section(
            SKILL_MD.read_text(encoding="utf-8"), "## 学习沉淀与收尾"
        )
        settlement_positions = [settlement.index(token) for token in expected]
        self.assertEqual(settlement_positions, sorted(settlement_positions))

    def test_feedback_and_promotion_bind_frozen_evidence(self) -> None:
        section = markdown_section(
            LEARNING_LOOP.read_text(encoding="utf-8"), "## Candidate 与 promotion"
        )
        headers, rows = first_markdown_table(section)
        self.assertEqual(headers, ["规则", "结构约束"])
        rules = {code_value(row[0]): csv_tokens(row[1]) for row in rows}
        self.assertTrue(
            {
                "run_id",
                "final_hash",
                "r2_hash",
                "evidence_refs",
                "applies_to",
                "destination",
                "received_at",
                "source",
                "claim",
                "next_validation",
            }.issubset(rules["feedback_binding"])
        )
        self.assertEqual(
            rules["promotion_revalidation"],
            {"reread_evidence", "recompute_hash", "write_receipt"},
        )

    def test_legacy_is_valid_and_backfill_is_explicit_bounded_and_idempotent(self) -> None:
        text = LEARNING_LOOP.read_text(encoding="utf-8")
        version_section = markdown_section(text, "## 版本边界")
        headers, rows = first_markdown_table(version_section)
        self.assertEqual(headers, ["workflow_version", "默认验证", "显式模式", "extension state"])
        versions = {
            code_value(row[0]): tuple(code_value(value) for value in row[1:]) for row in rows
        }
        self.assertEqual(versions["1.1.0"], ("full", "native", "collecting_or_frozen"))
        self.assertEqual(versions["1.0.0"], ("valid_without_v2", "backfill", "backfilled"))
        self.assertEqual(versions["unknown"], ("fail_closed", "none", "none"))

        backfill_section = markdown_section(text, "## Backfill 约束")
        backfill_headers, backfill_rows = first_markdown_table(backfill_section)
        self.assertEqual(backfill_headers, ["规则", "结构约束"])
        rules = {code_value(row[0]): csv_tokens(row[1]) for row in backfill_rows}
        self.assertEqual(rules["eligible"], {"completed", "workflow=1.0.0"})
        self.assertEqual(rules["unknown_usage"], {"not_recorded", "no_current_environment"})
        self.assertEqual(
            rules["immutability"],
            {"sidecars", "run.json.extensions", "old_files_unchanged", "final_hash_unchanged"},
        )
        self.assertEqual(rules["idempotence"], {"byte_identical"})
        self.assertNotIn("不得回填", text)

    def test_learning_loop_is_bounded_and_not_chain_of_thought(self) -> None:
        text = LEARNING_LOOP.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?i)不是.{0,20}(CoT|思维链)")
        self.assertRegex(text, r"下一轮.{0,30}(1[–-]3|1 至 3).{0,10}条")

    def test_skill_states_selection_freeze_feedback_and_backfill_boundaries(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        settlement = markdown_section(text, "## 学习沉淀与收尾")
        for token in (
            "workflow 1.1.0",
            "memory-selection.json",
            "state=frozen",
            "feedback candidate",
            "workflow 1.0.0",
            "backfill",
            "not_recorded",
        ):
            with self.subTest(token=token):
                self.assertIn(token, settlement)
        self.assertNotIn("不得回填", text)

    def test_local_memory_is_ignored_at_the_skill_root(self) -> None:
        lines = (SKILL_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/local/", lines)

    def test_openai_metadata_is_the_expected_mapping(self) -> None:
        actual = parse_shallow_yaml(
            (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            actual,
            {
                "interface": {
                    "display_name": "HyperFrames Apprentice",
                    "short_description": "从教程自主学习、复盘并产出可验证 HyperFrames Demo",
                    "default_prompt": (
                        "Use $ai-video-flow to learn this tutorial, "
                        "build a verified HyperFrames demo, and record its evidence-backed "
                        "learning ledger."
                    ),
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
