import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HappyVisualWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (ROOT / "skills/happy-visual-workflow/SKILL.md").read_text()
        cls.contract = (
            ROOT / "skills/happy-visual-workflow/references/delivery-contract.md"
        ).read_text()
        cls.web_e2e = (ROOT / "skills/web-e2e/SKILL.md").read_text()
        cls.pc_reviewer = (
            ROOT / "skills/pc-web-interaction-reviewer/SKILL.md"
        ).read_text()
        cls.mobile_reviewer = (
            ROOT / "skills/mobile-app-interaction-reviewer/SKILL.md"
        ).read_text()

    def test_keeps_the_user_requested_gate_order(self):
        expected = "开发 → 独立验收 → 按需一对一 E2E → 交互评审 → 可视证据交付 → PR 前后对比"
        self.assertIn(expected, self.workflow)

    def test_e2e_is_conditional_and_visible_e2e_media_is_sent(self):
        self.assertIn("可以记为 `not-required`", self.workflow)
        self.assertIn("用户可见的移动端变化必须录制最终通过版本", self.workflow)
        self.assertIn("只要 Gate 3 要求 E2E", self.workflow)
        self.assertIn("`mcp__happy__send_image`", self.workflow)
        self.assertIn("`mcp__happy__send_file`", self.workflow)
        self.assertIn("本机路径不等于跨设备交付", self.contract)

    def test_pr_creation_does_not_wait_for_ci_or_merge(self):
        self.assertIn("然后立即返回 PR URL", self.workflow)
        self.assertIn("不自动包含等待 CI、OTA、合并和清理", self.workflow)
        self.assertIn("PR 已创建、正文和图片已实际渲染、URL 已返回", self.contract)

    def test_capability_skills_do_not_own_global_delivery(self):
        self.assertIn("本 Skill 不自行创建 PR、等待 CI", self.web_e2e)
        self.assertIn("没有越权创建 PR、等待 CI 或合并", self.pc_reviewer)
        self.assertIn("新增平台或测试框架时，只需提供同一返回契约", self.contract)

    def test_routes_pc_and_mobile_to_distinct_reviewers(self):
        self.assertIn("PC Web 使用 `pc-web-interaction-reviewer`", self.workflow)
        self.assertIn("使用 `mobile-app-interaction-reviewer`", self.workflow)
        self.assertIn("Hover/Tooltip", self.pc_reviewer)
        self.assertIn("移动端没有可靠 hover", self.mobile_reviewer)


if __name__ == "__main__":
    unittest.main()
