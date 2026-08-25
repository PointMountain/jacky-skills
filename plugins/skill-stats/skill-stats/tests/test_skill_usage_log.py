import json
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOK = Path(__file__).resolve().parents[1] / "hooks" / "skill-usage-log.py"


class SkillUsageLogTests(unittest.TestCase):
    def run_hook(self, payload: dict) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "usage.jsonl"
            result = subprocess.run(
                ["python3", str(HOOK), str(log_path)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            if not log_path.exists():
                return []
            return [json.loads(line) for line in log_path.read_text().splitlines()]

    def test_absolute_user_path_is_not_recorded_as_skill(self) -> None:
        self.assertEqual(self.run_hook({
            "hook_event_name": "UserPromptSubmit",
            "session_id": "test-session",
            "cwd": "/tmp/project",
            "prompt": "/Users/example/project/SKILL.md",
        }), [])

    def test_real_slash_skill_is_recorded(self) -> None:
        records = self.run_hook({
            "hook_event_name": "UserPromptSubmit",
            "session_id": "test-session",
            "cwd": "/tmp/project",
            "prompt": "/skill-name 处理这个任务",
        })

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["skill"], "skill-name")
        self.assertEqual(records[0]["source"], "user")

    def test_codex_post_tool_use_is_recorded(self) -> None:
        records = self.run_hook({
            "hook_event_name": "PostToolUse",
            "tool_name": "Skill",
            "tool_input": {"skill": "playwright-cli"},
            "session_id": "codex-session",
            "cwd": "/tmp/project",
        })
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["skill"], "playwright-cli")
        self.assertEqual(records[0]["source"], "ai")


if __name__ == "__main__":
    unittest.main()
