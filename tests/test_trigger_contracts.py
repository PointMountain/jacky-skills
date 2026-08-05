import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_FLOW_ROOT = REPO_ROOT / "labs" / "web-flow"


def load_description(skill_name: str, root: Path | None = None) -> str:
    path = (root or REPO_ROOT / "skills") / skill_name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    return str(yaml.safe_load(frontmatter)["description"])


class TriggerContractTests(unittest.TestCase):
    def test_happy_visual_workflow_has_short_trigger_and_delivery_gates(self) -> None:
        description = load_description("happy-visual-workflow")
        skill_root = REPO_ROOT / "skills" / "happy-visual-workflow"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        contract = (skill_root / "references" / "delivery-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("视觉稿", description)
        self.assertIn("Happy/Paws", description)
        self.assertIn("独立验收", skill)
        self.assertIn("按需一对一 E2E", skill)
        self.assertIn("交互评审", skill)
        self.assertIn("PR 前后对比", skill)
        self.assertIn("Visible UI cases", skill)
        self.assertIn("不自动包含等待 CI、OTA、合并和清理", skill)
        self.assertIn("新增平台或测试框架时，只需提供同一返回契约", contract)

    def test_web_flow_children_are_internal_only(self) -> None:
        children = [
            "web-flow-research",
            "web-flow-prototype",
            "web-flow-design",
            "web-flow-build",
            "web-flow-benchmark",
            "web-flow-deploy",
        ]
        for skill_name in children:
            with self.subTest(skill=skill_name):
                description = load_description(skill_name, WEB_FLOW_ROOT)
                self.assertIn("仅在 web-flow 主 Skill 明确调用时使用", description)
                self.assertIn("不要因普通用户请求单独触发", description)

    def test_web_flow_uses_benchmark_and_stage_owned_memory(self) -> None:
        skill_path = WEB_FLOW_ROOT / "web-flow" / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")
        self.assertIn("references/workflow.md", skill)
        self.assertIn("web-flow-benchmark", skill)
        self.assertIn("当前阶段 Skill", skill)
        self.assertNotIn("workflow.yaml", skill)
        self.assertNotIn("external-skills.yaml", skill)
        self.assertFalse((WEB_FLOW_ROOT / "web-flow-memory").exists())

    def test_crafted_web_and_web_flow_are_mutually_exclusive(self) -> None:
        crafted = load_description("crafted-web")
        flow = load_description("web-flow", WEB_FLOW_ROOT)
        self.assertIn("不用于需要部署的完整站点项目", crafted)
        self.assertIn("单文件 HTML 成品应使用 crafted-web", flow)


if __name__ == "__main__":
    unittest.main()
