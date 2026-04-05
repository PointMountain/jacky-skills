import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_PATH = REPO_ROOT / "plugins/video-processing/skills/extract-url-media/scripts/extract.py"


def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_url_media_script", EXTRACT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load extract module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ExtractUtilsTests(unittest.TestCase):
    def test_build_suggestion_403(self) -> None:
        module = load_extract_module()
        suggestion = module.build_suggestion("HTTP Error 403: Forbidden")
        self.assertIn("cookies-from-browser", suggestion)

    def test_load_existing_result(self) -> None:
        module = load_extract_module()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            audio = work / "audio.wav"
            audio.write_bytes(b"abc")
            meta = {
                "id": "vid1",
                "platform": "youtube",
                "url": "https://example.com",
                "title": "hello",
                "author": "author",
                "duration": "1:00",
                "stages": {
                    "media": {"status": "done", "audioFile": "audio.wav"},
                    "subtitle": {"status": "pending", "file": None},
                    "obsidian": {"status": "pending"},
                },
            }
            (work / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

            data = module.load_existing_result(work)
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["id"], "vid1")
            self.assertEqual(Path(data["audioPath"]).name, "audio.wav")

    def test_guess_platform_and_id(self) -> None:
        module = load_extract_module()
        ytb = module.guess_platform_and_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(ytb, ("youtube", "dQw4w9WgXcQ"))
        bilibili = module.guess_platform_and_id("https://www.bilibili.com/video/BV1xx411c7mD")
        self.assertEqual(bilibili, ("bilibili", "BV1xx411c7mD"))


if __name__ == "__main__":
    unittest.main()
