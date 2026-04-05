import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_SCRIPT = REPO_ROOT / "plugins/video-processing/skills/audio-to-obsidian/scripts/pipeline.py"


class PipelineCliTests(unittest.TestCase):
    def test_dry_run_and_max_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            obsidian = Path(tmp) / "vault"
            obsidian.mkdir(parents=True, exist_ok=True)
            urls_file = Path(tmp) / "urls.txt"
            urls_file.write_text(
                "https://example.com/a\nhttps://example.com/b\n",
                encoding="utf-8",
            )

            cmd = [
                "python3",
                str(PIPELINE_SCRIPT),
                str(urls_file),
                "--obsidian-repo",
                str(obsidian),
                "--dry-run",
                "--max-items",
                "1",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertTrue(payload["success"])
            self.assertEqual(payload["summary"]["total"], 1)
            self.assertEqual(len(payload["items"]), 1)
            self.assertEqual(payload["items"][0]["status"], "planned")


if __name__ == "__main__":
    unittest.main()
