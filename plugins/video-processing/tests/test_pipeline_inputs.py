import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_PATH = REPO_ROOT / "plugins/video-processing/skills/audio-to-obsidian/scripts/pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("audio_to_obsidian_pipeline", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load pipeline module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PipelineInputTests(unittest.TestCase):
    def test_infer_url_input(self) -> None:
        module = load_pipeline_module()
        tasks = module.infer_inputs("https://example.com/video")
        self.assertEqual(tasks, [{"type": "url", "value": "https://example.com/video"}])

    def test_infer_local_media_input(self) -> None:
        module = load_pipeline_module()
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "demo.mp3"
            media.write_bytes(b"abc")
            tasks = module.infer_inputs(str(media))
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["type"], "local")

    def test_infer_url_list_file(self) -> None:
        module = load_pipeline_module()
        with tempfile.TemporaryDirectory() as tmp:
            urls = Path(tmp) / "urls.txt"
            urls.write_text(
                "# comment\n\nhttps://a.example.com\nhttps://b.example.com\n",
                encoding="utf-8",
            )
            tasks = module.infer_inputs(str(urls))
            self.assertEqual(
                tasks,
                [
                    {"type": "url", "value": "https://a.example.com"},
                    {"type": "url", "value": "https://b.example.com"},
                ],
            )

    def test_infer_empty_url_list_file_should_fail(self) -> None:
        module = load_pipeline_module()
        with tempfile.TemporaryDirectory() as tmp:
            urls = Path(tmp) / "urls.txt"
            urls.write_text("# only comments\n\n", encoding="utf-8")
            with self.assertRaises(module.PipelineError):
                module.infer_inputs(str(urls))

    def test_parse_json_output_with_noise(self) -> None:
        module = load_pipeline_module()
        noisy = "INFO something\n{\"success\": true, \"k\": 1}\n"
        parsed = module.parse_json_output(noisy)
        self.assertTrue(parsed["success"])
        self.assertEqual(parsed["k"], 1)


if __name__ == "__main__":
    unittest.main()
