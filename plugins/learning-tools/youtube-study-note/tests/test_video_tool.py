import importlib.util
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "video_tool.py"
FIXTURE = ROOT / "tests" / "fixtures" / "transcript.json"
DEFAULT_NOTE_ROOT = Path.home() / "Documents" / "video-note"


spec = importlib.util.spec_from_file_location("video_tool", SCRIPT)
video_tool = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(video_tool)


class VideoToolTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )

    def test_default_output_dir_uses_youtube_video_id(self) -> None:
        out = video_tool.default_output_dir("https://www.youtube.com/watch?v=tCfmxMX5WaU&list=abc")
        self.assertEqual(out, DEFAULT_NOTE_ROOT / "tCfmxMX5WaU")

    def test_transcript_with_input_preserves_source_url(self) -> None:
        source_url = "https://www.youtube.com/watch?v=tCfmxMX5WaU&list=abc"
        out = video_tool.default_output_dir(source_url, str(FIXTURE))
        self.assertEqual(out, DEFAULT_NOTE_ROOT / "tCfmxMX5WaU")

        with tempfile.TemporaryDirectory() as tmp:
            run_out = Path(tmp) / "note"
            self.run_cli("run", "--input", source_url, "--transcript", str(FIXTURE), "--title", "Target video", "--out", str(run_out))
            metadata = json.loads((run_out / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["id"], "tCfmxMX5WaU")
            self.assertEqual(metadata["title"], "Target video")
            self.assertEqual(metadata["webpage_url"], source_url)
            frame_plan = json.loads((run_out / "frame_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(any(source_url in item["timestamp_link"] for item in frame_plan))

    def test_merge_tree_with_existing_target_subdirs(self) -> None:
        # 回归：目标目录已有同名子目录时，递归 merge 后不能对 child 重复 rmdir
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            (src / "chapters").mkdir(parents=True)
            (src / "chapters" / "a.md").write_text("new", encoding="utf-8")
            (src / "logs").mkdir()
            (dst / "chapters").mkdir(parents=True)
            (dst / "chapters" / "b.md").write_text("old", encoding="utf-8")
            video_tool.merge_tree(src, dst)
            self.assertFalse(src.exists())
            self.assertEqual((dst / "chapters" / "a.md").read_text(encoding="utf-8"), "new")
            self.assertEqual((dst / "chapters" / "b.md").read_text(encoding="utf-8"), "old")
            self.assertTrue((dst / "logs").is_dir())

    def test_prepare_without_out_rehomes_package_to_title_folder(self) -> None:
        old_root = video_tool.DEFAULT_NOTES_ROOT
        source_url = "https://www.youtube.com/watch?v=tCfmxMX5WaU&list=abc"
        with tempfile.TemporaryDirectory() as tmp:
            video_tool.DEFAULT_NOTES_ROOT = Path(tmp)
            try:
                out = video_tool.cmd_prepare(argparse.Namespace(
                    input=source_url,
                    transcript=str(FIXTURE),
                    title="Target video",
                    out=None,
                ))
            finally:
                video_tool.DEFAULT_NOTES_ROOT = old_root
            self.assertEqual(out, (Path(tmp) / "Target-video").resolve())
            self.assertTrue((out / "metadata.json").exists())
            self.assertFalse((Path(tmp) / "tCfmxMX5WaU").exists())

    def test_run_with_transcript_creates_complete_safe_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "note"
            self.run_cli("run", "--transcript", str(FIXTURE), "--out", str(out))

            expected = [
                "metadata.json",
                "transcript.json",
                "transcript.md",
                "summary.json",
                "debate.json",
                "frame_plan.json",
                "lesson_units.json",
                "visual_storyboard.json",
                "assessment.json",
                "asset_health.json",
                "replacement_review.json",
                "image_prompts.json",
                "generated_images.json",
                "run_review.json",
                "notes_for_next_run.md",
                "report.md",
                "report.html",
                "index.html",
                "chapters/index.md",
                "source_transcripts/transcript.json",
            ]
            for name in expected:
                self.assertTrue((out / name).exists(), name)
            self.assertFalse((out / "frames" / "index.json").exists())

            frame_plan = json.loads((out / "frame_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item["need_frame"] for item in frame_plan))
            self.assertTrue(all("timestamp_link" in item for item in frame_plan))
            debate = json.loads((out / "debate.json").read_text(encoding="utf-8"))
            self.assertTrue(debate["chapter_reviews"])
            self.assertIn("skeptic_view", debate["chapter_reviews"][0])
            self.assertIn("judge_view", debate["chapter_reviews"][0])
            lesson_units = json.loads((out / "lesson_units.json").read_text(encoding="utf-8"))
            self.assertTrue(lesson_units)
            self.assertIn("verification_conditions", lesson_units[0])
            assessment = json.loads((out / "assessment.json").read_text(encoding="utf-8"))
            self.assertTrue(assessment["quiz"])
            self.assertIn("answer_index", assessment["quiz"][0])
            self.assertIn("explanation", assessment["quiz"][0])
            replacement_review = json.loads((out / "replacement_review.json").read_text(encoding="utf-8"))
            self.assertIn("replacement_score", replacement_review)
            self.assertIn("threshold", replacement_review)

            report = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("## 5. 关键证据和时间戳", report)
            self.assertIn("当前报告还没有选定关键帧", report)
            self.assertIn("## 11. 手绘学习图", report)
            self.assertIn("本次没有生成手绘学习图", report)
            self.assertIn("[AUTHOR_VIEW]", report)
            self.assertIn("[COUNTERPOINT]", report)
            self.assertIn("[JUDGMENT]", report)
            self.assertNotIn("This section appears", report)
            self.assertNotIn("The main study takeaway", report)
            self.assertNotIn("Transcript mentions visual material", report)
            self.assertNotIn("图片生成提示词", report)
            self.assertNotIn("...", report)

            image_prompts = json.loads((out / "image_prompts.json").read_text(encoding="utf-8"))
            self.assertEqual(image_prompts[0]["size"], "1600x900")
            self.assertIn("Xiaohei", image_prompts[0]["prompt"])
            generated_images = json.loads((out / "generated_images.json").read_text(encoding="utf-8"))
            self.assertEqual(generated_images, [])
            self.assertFalse((out / "generated" / "sketch_map_01.svg").exists())
            self.assertFalse((out / "generated" / "review_card_01.svg").exists())

            report_html = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn("data-notes", report_html)
            self.assertIn("localStorage", report_html)
            self.assertIn("id=\"practice\"", report_html)
            self.assertIn("先懂核心", report_html)
            self.assertIn("学习路线", report_html)
            self.assertIn("5 分钟速学", report_html)
            self.assertIn("概念翻译", report_html)
            self.assertIn("核心章节", report_html)
            self.assertIn("chapter-judgment", report_html)
            self.assertIn("judgment-grid", report_html)
            self.assertIn("全片争议", report_html)
            self.assertIn("comparison-list", report_html)
            self.assertIn("来源证据", report_html)
            self.assertIn("观点总结图", report_html)
            self.assertIn("data-quiz-score", report_html)
            self.assertIn("查看答案和解析", report_html)
            self.assertNotIn("图片生成提示词", report_html)
            self.assertNotIn("Transcript mentions visual material", report_html)
            self.assertNotIn("章节预览", report_html)
            self.assertNotIn("回看清单", report_html)
            self.assertNotIn("这一段保留完整概要", report_html)
            self.assertNotIn("内置 imagegen", report_html)
            self.assertNotIn("生成信息", report_html)
            self.assertNotIn("Debug", report_html)
            self.assertNotIn("当前 transcript 覆盖", report_html)
            self.assertNotIn("报告按", report_html)
            self.assertNotIn("报告把", report_html)
            self.assertNotIn("字幕文本", report_html)
            self.assertNotIn("Markdown", report_html)
            self.assertNotIn("查看 transcript", report_html)
            self.assertNotIn("推断：", report_html)
            self.assertNotIn("data-tabs", report_html)
            self.assertNotIn("—", report_html)
            self.assertNotIn("–", report_html)
            chapter_dirs = [path for path in (out / "chapters").iterdir() if path.is_dir()]
            self.assertTrue(chapter_dirs)
            self.assertTrue(any((path / "chapter.md").exists() for path in chapter_dirs))

            source_image = Path(tmp) / "imagegen-output.png"
            source_image.write_bytes(b"fake-png")
            self.run_cli(
                "image",
                "--out",
                str(out),
                "--image-prompts",
                str(out / "image_prompts.json"),
                "--asset",
                f"sketch_map_01={source_image}",
                "--render",
            )
            registered_images = json.loads((out / "generated_images.json").read_text(encoding="utf-8"))
            self.assertEqual(registered_images[0]["type"], "built_in_imagegen_png")
            self.assertEqual(registered_images[0]["model"], "image_gen")
            self.assertTrue((out / "generated" / "sketch_map_01.png").exists())
            self.run_cli("render", "--out", str(out))
            with_generated_html = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn("generated/sketch_map_01.png", with_generated_html)
            self.assertIn("小黑价格筛选机", with_generated_html)

            (out / "frames" / "sample.jpg").write_bytes(b"fake")
            (out / "frames" / "selected_frames.json").write_text(
                json.dumps([
                    {
                        "timestamp": 5,
                        "topic": "测试截图",
                        "selected_frame": "frames/sample.jpg",
                        "caption": "这张截图用于验证 HTML 截图画廊。",
                        "source": "unit_test",
                    }
                ], ensure_ascii=False),
                encoding="utf-8",
            )
            self.run_cli("render", "--out", str(out))
            rerendered_html = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn("chapter-frame", rerendered_html)
            self.assertIn("frames/sample.jpg", rerendered_html)
            self.assertIn("测试截图", rerendered_html)

    def test_concept_image_metadata_renders_in_glossary_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "note"
            transcript = Path(tmp) / "trading.json"
            transcript.write_text(
                json.dumps([
                    {
                        "start": 0,
                        "end": 20,
                        "text": "这里讲解 PD Array，先选 Dealing Range，再用 Premium / Discount 判断高价区和低价区。",
                    },
                    {
                        "start": 20,
                        "end": 45,
                        "text": "接着观察 Order Block、FVG 和小周期确认，但不能把任何一个概念当成单独入场信号。",
                    },
                ], ensure_ascii=False),
                encoding="utf-8",
            )
            self.run_cli("run", "--transcript", str(transcript), "--out", str(out))

            prompts = json.loads((out / "image_prompts.json").read_text(encoding="utf-8"))
            pd_prompt = next(item for item in prompts if item.get("role") == "concept" and item.get("concept_term") == "PD Array")
            self.assertEqual(pd_prompt["id"], "concept_pd_array")
            self.assertIn("价格输送清单", pd_prompt["title"])

            source_image = Path(tmp) / "pd-array.png"
            source_image.write_bytes(b"fake-png")
            self.run_cli(
                "image",
                "--out",
                str(out),
                "--image-prompts",
                str(out / "image_prompts.json"),
                "--asset",
                f"{pd_prompt['id']}={source_image}",
                "--render",
            )

            generated_images = json.loads((out / "generated_images.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item.get("role") == "concept" and item.get("concept_term") == "PD Array" for item in generated_images))
            report_html = (out / "report.html").read_text(encoding="utf-8")
            self.assertIn("generated/concept_pd_array.png", report_html)
            self.assertIn('alt="PD Array 概念图"', report_html)
            self.assertIn('<span class="term-cn">价格输送清单</span>', report_html)
            self.assertIn('<span class="term-en">PD Array</span>', report_html)
            self.assertIn("展开课程卡", report_html)
            self.assertIn("concept-answer", report_html)
            self.assertIn("查看参考答案", report_html)
            self.assertNotIn("<dt>参考答案</dt>", report_html)
            self.assertLess(report_html.index('id="concepts"'), report_html.index('id="overview"'))
            self.assertLess(report_html.index('id="overview"'), report_html.index('id="route"'))

    def test_analyze_speech_only_transcript_defaults_to_no_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "note"
            transcript = Path(tmp) / "plain.json"
            transcript.write_text(
                json.dumps([
                    {"start": 0, "end": 5, "text": "This section is only spoken context."},
                    {"start": 5, "end": 12, "text": "The author explains the idea without visual evidence."},
                ]),
                encoding="utf-8",
            )
            self.run_cli("run", "--transcript", str(transcript), "--out", str(out))
            frame_plan = json.loads((out / "frame_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(frame_plan)
            self.assertTrue(all(not item["need_frame"] for item in frame_plan))

    def test_visual_storyboard_matches_nearby_selected_frame(self) -> None:
        storyboard = video_tool.build_visual_storyboard(
            {
                "chapters": [
                    {"start": 0, "end": 100, "title": "A"},
                    {"start": 100, "end": 240, "title": "B"},
                ],
            },
            [
                {
                    "timestamp": 180,
                    "need_frame": True,
                    "topic": "这里解释 PD Array 和 Order Block 的图表示例。",
                },
            ],
            [
                {
                    "timestamp": 170,
                    "selected_frame": "frames/keyframe_001.jpg",
                    "topic": "高清替换截图",
                },
            ],
        )
        self.assertEqual(storyboard[0]["frame"], "frames/keyframe_001.jpg")
        self.assertFalse(storyboard[0]["needs_annotation"])

    def test_long_transcript_gets_more_chapters_and_chinese_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "note"
            transcript = Path(tmp) / "long.json"
            rows = []
            for i in range(24):
                start = i * 90
                rows.append({
                    "start": start,
                    "end": start + 80,
                    "text": f"第{i + 1}段：这里讲解 PD Array、订单块、图表验证和风险控制。",
                })
            transcript.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            self.run_cli("run", "--transcript", str(transcript), "--title", "长视频测试", "--out", str(out))

            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(summary["chapters"]), 10)
            report = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("主线起点", report)
            self.assertNotIn("报告按完整视频长度拆成", report)
            self.assertIn("## 运行复核", report)
            self.assertNotIn("Which claim", report)
            self.assertNotIn("Create an original", report)


if __name__ == "__main__":
    unittest.main()
