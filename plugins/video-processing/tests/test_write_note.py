import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "plugins/video-processing/skills/audio-to-subtitle/scripts/transcribe.py"
)


def load_transcribe_module():
    spec = importlib.util.spec_from_file_location("audio_to_subtitle_transcribe", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载转录脚本: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


transcribe = load_transcribe_module()


class AudioToSubtitleContractTests(unittest.TestCase):
    def test_formats_transcription_as_supported_subtitle_types(self) -> None:
        result = transcribe.TranscriptionResult(
            segments=[transcribe.Segment(start=1.25, end=3.5, text="第一段")],
            language="zh",
            duration=3.5,
            text="第一段",
        )

        self.assertIn("00:00:01,250 --> 00:00:03,500", transcribe.to_srt(result))
        self.assertIn("00:00:01.250 --> 00:00:03.500", transcribe.to_vtt(result))
        self.assertEqual(transcribe.to_txt(result), "第一段")
        self.assertIn("- **0:01** 第一段", transcribe.to_md(result))

    def test_discovers_only_supported_audio_and_video_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in ("b.MP4", "a.mp3", "notes.txt"):
                (directory / name).touch()

            files = transcribe.find_audio_files(str(directory))

        self.assertEqual(
            [Path(path).name for path in files],
            ["a.mp3", "b.MP4"],
        )


if __name__ == "__main__":
    unittest.main()
