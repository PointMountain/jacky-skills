"""Skill 文档中可执行路径的回归测试。"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BROWSER_CONTROL = (ROOT / "plugins/dev-tools/browser-control/SKILL.md").read_text(
    encoding="utf-8"
)
BROWSER_ROUTER = (
    ROOT / "plugins/dev-tools/browser-control/scripts/route-provider.mjs"
).read_text(encoding="utf-8")
AUDIO_TO_SUBTITLE = (
    ROOT / "plugins/video-processing/skills/audio-to-subtitle/SKILL.md"
).read_text(encoding="utf-8")


class SkillExecutionPathTests(unittest.TestCase):
    def test_browser_control_has_one_ego_lite_execution_path(self) -> None:
        self.assertIn("Browser Control → Ego Ops → Ego Lite", BROWSER_CONTROL)
        self.assertIn('const PROVIDER = "ego-ops"', BROWSER_ROUTER)
        self.assertIn("不属于统一 Ego Lite 路由", BROWSER_ROUTER)

    def test_audio_setup_does_not_infer_the_skill_path_from_shell_zero(self) -> None:
        self.assertNotIn('$(dirname "$0")/scripts/setup.sh', AUDIO_TO_SUBTITLE)
        self.assertIn("AUDIO_TO_SUBTITLE_SKILL_DIR", AUDIO_TO_SUBTITLE)
        self.assertIn(
            '$HOME/.j-skills/linked/audio-to-subtitle', AUDIO_TO_SUBTITLE
        )
        self.assertIn(
            'bash "$AUDIO_TO_SUBTITLE_SKILL_DIR/scripts/setup.sh"',
            AUDIO_TO_SUBTITLE,
        )


if __name__ == "__main__":
    unittest.main()
