import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "plugins/video-processing/skills/write-obsidian-note/scripts/write_note.py"


class WriteNoteCliTests(unittest.TestCase):
    def run_cli(self, args: list[str]) -> tuple[int, dict]:
        cmd = ["python3", str(SCRIPT)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        payload = json.loads(result.stdout.strip())
        return result.returncode, payload

    def test_write_and_skip_when_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            obsidian_repo = Path(tmp) / "vault"
            obsidian_repo.mkdir(parents=True, exist_ok=True)

            input_json = Path(tmp) / "payload.json"
            input_json.write_text(
                json.dumps(
                    {
                        "metadata": {
                            "title": "测试标题",
                            "author": "作者A",
                            "url": "https://example.com/video",
                            "duration": "10:00",
                        },
                        "transcript": "第一行\n第二行\n第三行",
                        "category": "Audio",
                        "extraContent": {"extraTags": ["demo tag", "#already_ok"]},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            code, payload = self.run_cli(
                ["--input-json", str(input_json), "--obsidian-repo", str(obsidian_repo)]
            )
            self.assertEqual(code, 0)
            self.assertTrue(payload["success"])
            original = Path(payload["files"]["originalPath"])
            summary = Path(payload["files"]["summaryPath"])
            self.assertTrue(original.exists())
            self.assertTrue(summary.exists())

            text = original.read_text(encoding="utf-8")
            self.assertIn("https://example.com/video", text)
            self.assertIn("版权声明", text)
            self.assertIn("#demo_tag", text)
            self.assertIn("#already_ok", text)

            code2, payload2 = self.run_cli(
                ["--input-json", str(input_json), "--obsidian-repo", str(obsidian_repo)]
            )
            self.assertEqual(code2, 0)
            self.assertTrue(payload2["success"])
            self.assertTrue(payload2.get("skipped"))

    def test_sanitize_filename_for_invalid_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            obsidian_repo = Path(tmp) / "vault"
            obsidian_repo.mkdir(parents=True, exist_ok=True)

            code, payload = self.run_cli(
                [
                    "--obsidian-repo",
                    str(obsidian_repo),
                    "--title",
                    "A/B:C*D?E",
                    "--author",
                    "AA|BB",
                    "--url",
                    "https://example.com",
                    "--transcript",
                    "hello",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(payload["success"])
            original = Path(payload["files"]["originalPath"])
            self.assertIn("A_B_C_D_E-原文.md", original.name)
            self.assertIn("AA_BB", str(original.parent))


if __name__ == "__main__":
    unittest.main()
