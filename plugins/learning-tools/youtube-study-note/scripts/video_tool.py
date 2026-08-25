#!/usr/bin/env python3
"""Utility CLI for the youtube-study-note skill.

This script intentionally keeps LLM reasoning outside the media pipeline. It prepares
an evidence packet for the agent, extracts frames from an agent-produced frame plan,
renders reports from agent-produced JSON, and optionally calls OpenAI image generation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

LOCAL_DEPS = Path(__file__).resolve().parents[1] / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

TIME_RE = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?:[\.,](?P<ms>\d{1,3}))?")
DEFAULT_NOTES_ROOT = Path(os.environ.get("VIDEO_NOTE_ROOT", "~/Documents/video-note")).expanduser()
VISUAL_KEYWORDS = {
    "chart", "diagram", "slide", "screen", "code", "formula", "whiteboard", "flow",
    "图", "表", "图表", "流程", "屏幕", "代码", "公式", "白板", "演示", "界面", "截图",
}
LABEL_FACT = "[FACT]"
LABEL_AUTHOR = "[AUTHOR_VIEW]"
LABEL_INFERENCE = "[MODEL_INFERENCE]"
LABEL_COUNTER = "[COUNTERPOINT]"
LABEL_JUDGMENT = "[JUDGMENT]"
LABEL_TODO = "[TODO_VERIFY]"

TRADING_GLOSSARY = [
    {
        "term": "PD Array",
        "zh_name": "价格输送清单",
        "aliases": ["pd array", "price delivery array"],
        "plain": "一套看价格位置和结构的清单，用来判断现在更适合等待、找多头机会，还是找空头机会。",
        "why": "视频的主线。它不是买卖按钮，而是入场前的复盘框架。",
    },
    {
        "term": "Premium / Discount",
        "zh_name": "高低价区",
        "aliases": ["premium", "discount", "高价区", "低价区"],
        "plain": "把一个波段用 50% 分成高价区和低价区。高价区更偏等待做空条件，低价区更偏等待做多条件。",
        "why": "解决“现在价格贵不贵、便不便宜”的问题。",
    },
    {
        "term": "Dealing Range",
        "zh_name": "交易区间",
        "aliases": ["dealing range", "交易区间", "区间"],
        "plain": "先选一个明确的价格波段，再在这个波段里画 50% 分界。",
        "why": "没有区间，Premium / Discount 就没有参照物。",
    },
    {
        "term": "Order Block",
        "zh_name": "订单块",
        "aliases": ["order block", "订单块"],
        "plain": "作者用来观察机构可能留下订单的位置。视频里强调要看后续吞没、小周期确认和结构变化。",
        "why": "它是观察区域，不应该被当成单独入场信号。",
    },
    {
        "term": "FVG",
        "zh_name": "价格失衡缺口",
        "aliases": ["fvg", "fair value gap", "失衡"],
        "plain": "价格快速移动后留下的失衡空档，常用来观察价格是否会回补或发生反应。",
        "why": "常和 Order Block、小周期确认一起用。",
    },
    {
        "term": "小周期确认",
        "zh_name": "小周期触发确认",
        "aliases": ["小周期", "小时间框架", "小时框架"],
        "plain": "在更小时间框架里确认结构变化、失衡或触发条件。",
        "why": "避免看到一个大区间就直接进场。",
    },
    {
        "term": "失效条件",
        "zh_name": "判断失效条件",
        "aliases": ["失效条件", "止损", "风险"],
        "plain": "如果价格怎么走就说明判断错了，要提前定义。",
        "why": "没有失效条件，任何图形都容易变成事后解释。",
    },
]

CORE_CONTENT_KEYWORDS = [
    "pd array", "premium", "discount", "dealing range", "order block", "fvg",
    "fair value gap", "高价区", "低价区", "50%", "订单块", "小周期", "小时间框架",
    "结构转换", "失衡", "价格输送", "交易区间", "复盘", "图表", "入场", "止损",
]

EDGE_CONTENT_KEYWORDS = [
    "作者介绍", "经验", "订阅", "观众", "系列后续", "后续还会", "这全新的系列",
    "学到一半", "ict 本人", "第一集主要", "完整版第二集",
]


def run(cmd: list[str], cwd: Path | None = None, log_file: Path | None = None, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as f:
            f.write("\n$ " + " ".join(cmd) + "\n")
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="ignore")
        if log_file:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(partial)
                f.write(f"\nTimed out after {timeout} seconds.\n")
        raise RuntimeError(f"Command timed out after {timeout} seconds: {' '.join(cmd)}\n{partial}") from exc
    if log_file:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(proc.stdout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc


def tool_command(bin_name: str) -> list[str]:
    if bin_name == "yt-dlp":
        env_bin = os.getenv("YT_DLP_BIN")
        if env_bin:
            return [env_bin]
        path = shutil.which("yt-dlp")
        if path:
            return [path]
        local_main = LOCAL_DEPS / "yt_dlp" / "__main__.py"
        if local_main.exists():
            return [sys.executable, str(local_main)]
        local_bin = LOCAL_DEPS / "bin" / "yt-dlp"
        if local_bin.exists():
            return [str(local_bin)]
        if importlib.util.find_spec("yt_dlp"):
            return [sys.executable, "-m", "yt_dlp"]
        raise SystemExit("Missing required tool: yt-dlp. Install it, set YT_DLP_BIN, or install the yt-dlp Python package.")
    path = shutil.which(bin_name)
    if not path:
        raise SystemExit(f"Missing required binary: {bin_name}")
    return [path]


def require(bin_name: str) -> None:
    tool_command(bin_name)


def yt_dlp_extra_args(cookies_from_browser: str | None = None, js_runtime: str | None = None, cookies_file: str | None = None) -> list[str]:
    args: list[str] = []
    if js_runtime:
        args += ["--js-runtimes", js_runtime]
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        args += ["--cookies", str(Path(cookies_file).expanduser())]
    return args


def is_url(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https"}


def slugify(value: str, fallback: str = "video") -> str:
    value = re.sub(r"[^\w\-.\u4e00-\u9fff]+", "-", value, flags=re.UNICODE).strip("-._")
    return value[:80] or fallback


def youtube_video_id(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.netloc.endswith("youtu.be"):
        return slugify(parsed.path.strip("/"), "youtube")
    query_id = parse_qs(parsed.query).get("v", [None])[0]
    if query_id:
        return slugify(query_id, "youtube")
    return None


def is_transcript_path(value: str | None) -> bool:
    if not value:
        return False
    suffix = Path(value).expanduser().suffix.lower()
    return suffix in {".json", ".md", ".txt", ".srt", ".vtt"}


def default_output_dir(input_value: str | None = None, transcript_path: str | None = None) -> Path:
    if input_value and is_url(input_value):
        return DEFAULT_NOTES_ROOT / (youtube_video_id(input_value) or "youtube-video")
    if input_value:
        return DEFAULT_NOTES_ROOT / slugify(Path(input_value).expanduser().stem, "video")
    if transcript_path:
        return DEFAULT_NOTES_ROOT / slugify(Path(transcript_path).expanduser().stem, "transcript")
    return DEFAULT_NOTES_ROOT / f"video-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"


def resolve_output_dir(out_arg: str | None, input_value: str | None = None, transcript_path: str | None = None) -> Path:
    if out_arg:
        return Path(out_arg).expanduser().resolve()
    return default_output_dir(input_value, transcript_path).expanduser().resolve()


def title_output_dir(metadata: dict[str, Any], fallback: str = "video") -> Path:
    title = clean_caption_text(str(metadata.get("title") or "")).strip()
    if not title:
        title = str(metadata.get("id") or fallback)
    target = DEFAULT_NOTES_ROOT / slugify(title, fallback)
    existing_metadata = load_optional_json(target / "metadata.json", {}) if target.exists() else {}
    current_id = str(metadata.get("id") or metadata.get("webpage_url") or metadata.get("local_path") or "")
    existing_id = str(existing_metadata.get("id") or existing_metadata.get("webpage_url") or existing_metadata.get("local_path") or "")
    if target.exists() and existing_metadata and current_id and existing_id and current_id != existing_id:
        return DEFAULT_NOTES_ROOT / slugify(f"{title}-{current_id}", fallback)
    return target


def merge_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir() and target.exists() and target.is_dir():
            # merge_tree 递归结束时已自行 rmdir(src)，此处不能再删一次
            merge_tree(child, target)
        elif target.exists():
            if child.is_file():
                shutil.copy2(child, target)
                child.unlink()
            else:
                shutil.rmtree(target)
                shutil.move(str(child), str(target))
        else:
            shutil.move(str(child), str(target))
    src.rmdir()


def rehome_output_dir_for_title(out: Path, out_arg: str | None, metadata: dict[str, Any]) -> Path:
    if out_arg:
        return out
    target = title_output_dir(metadata)
    if out.resolve() == target.resolve():
        return out
    if out.exists():
        if target.exists():
            merge_tree(out, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(out), str(target))
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def ensure_note_package_dirs(out: Path) -> None:
    for dirname in ("logs", "frames", "source_transcripts", "chapters"):
        (out / dirname).mkdir(parents=True, exist_ok=True)


def archive_source_transcript(transcript_path: Path, out: Path) -> str | None:
    transcript_path = transcript_path.expanduser().resolve()
    archive_dir = out / "source_transcripts"
    archive_dir.mkdir(parents=True, exist_ok=True)
    try:
        transcript_path.relative_to(out)
        return str(transcript_path.relative_to(out))
    except ValueError:
        pass
    target = archive_dir / transcript_path.name
    if target.exists() and target.resolve() != transcript_path:
        target = archive_dir / f"{transcript_path.stem}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}{transcript_path.suffix}"
    shutil.copy2(transcript_path, target)
    return str(target.relative_to(out))


def seconds_to_hhmmss(seconds: float) -> str:
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def timestamp_link(source_url: str, seconds: float) -> str:
    if not source_url or not is_url(source_url):
        return seconds_to_hhmmss(seconds)
    sep = "&" if "?" in source_url else "?"
    return f"{source_url}{sep}t={int(max(0, seconds))}s"


def parse_time_to_seconds(text: str) -> float:
    m = TIME_RE.search(text)
    if not m:
        raise ValueError(f"No timestamp in: {text}")
    h = int(m.group("h"))
    minute = int(m.group("m"))
    s = int(m.group("s"))
    ms = int((m.group("ms") or "0").ljust(3, "0")[:3])
    return h * 3600 + minute * 60 + s + ms / 1000


def clean_caption_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_segments(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("segments") or raw.get("transcript") or raw.get("items") or []
    if not isinstance(raw, list):
        raise ValueError("Transcript JSON must be a list or contain a segments list.")
    segments: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            text = clean_caption_text(item)
            start = float(index * 10)
            end = start + 10.0
        elif isinstance(item, dict):
            text = clean_caption_text(str(item.get("text") or item.get("caption") or ""))
            start = float(item.get("start") or item.get("start_seconds") or 0)
            end = float(item.get("end") or item.get("end_seconds") or start)
            if end <= start:
                end = start + max(1.0, min(10.0, len(text) / 8))
        else:
            continue
        if text:
            segments.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return merge_near_duplicates(segments)


def parse_transcript_markdown(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        matches = list(TIME_RE.finditer(line))
        if matches:
            start = parse_time_to_seconds(matches[0].group(0))
            end = parse_time_to_seconds(matches[1].group(0)) if len(matches) > 1 else start + 10
            content = clean_caption_text(TIME_RE.sub(" ", line, count=2).strip("[] -"))
            if content:
                segments.append({"start": round(start, 3), "end": round(max(end, start + 1), 3), "text": content})
        elif segments:
            segments[-1]["text"] = clean_caption_text(f"{segments[-1]['text']} {line}")
        else:
            content = clean_caption_text(line)
            if content and not content.startswith("#"):
                segments.append({"start": 0.0, "end": 10.0, "text": content})
    if segments:
        return merge_near_duplicates(segments)
    text = clean_caption_text(text)
    return [{"start": 0.0, "end": max(10.0, len(text) / 8), "text": text}] if text else []


def load_transcript_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".srt", ".vtt"}:
        return parse_vtt_or_srt(path)
    if suffix == ".json":
        return normalize_segments(read_json(path))
    return parse_transcript_markdown(path.read_text(encoding="utf-8", errors="ignore"))


def parse_vtt_or_srt(path: Path) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" not in line:
            i += 1
            continue
        left, right = line.split("-->", 1)
        try:
            start = parse_time_to_seconds(left.strip())
            end = parse_time_to_seconds(right.strip())
        except ValueError:
            i += 1
            continue
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            # Skip duplicate per-word timestamp tags often present in auto VTT.
            text_lines.append(lines[i].strip())
            i += 1
        text = clean_caption_text(" ".join(text_lines))
        if text:
            if segments and abs(segments[-1]["start"] - start) < 0.05 and segments[-1]["text"] == text:
                pass
            else:
                segments.append({"start": round(start, 3), "end": round(end, 3), "text": text})
        i += 1
    return merge_near_duplicates(segments)


def merge_near_duplicates(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen = set()
    for seg in segments:
        text = seg["text"].strip()
        key = (round(float(seg["start"]), 1), text)
        if key in seen:
            continue
        seen.add(key)
        if merged and text == merged[-1]["text"] and abs(float(seg["start"]) - float(merged[-1]["end"])) < 1.5:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)
    return merged


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metadata_for_input(input_value: str, out: Path, log: Path, cookies_from_browser: str | None = None, js_runtime: str | None = None, tool_timeout: float | None = None, cookies_file: str | None = None) -> dict[str, Any]:
    if is_url(input_value):
        proc = run([*tool_command("yt-dlp"), *yt_dlp_extra_args(cookies_from_browser, js_runtime, cookies_file), "-J", "--no-playlist", input_value], log_file=log, timeout=tool_timeout)
        metadata = json.loads(proc.stdout)
    else:
        p = Path(input_value).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        require("ffprobe")
        proc = run([
            "ffprobe", "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(p)
        ], log_file=log)
        ffmeta = json.loads(proc.stdout)
        duration = float(ffmeta.get("format", {}).get("duration") or 0)
        metadata = {
            "id": slugify(p.stem),
            "title": p.stem,
            "webpage_url": str(p),
            "duration": duration,
            "extractor_key": "local_file",
            "local_path": str(p),
        }
    write_json(out / "metadata.json", metadata)
    return metadata


def metadata_for_transcript(path: Path, source_input: str | None = None, title: str | None = None) -> dict[str, Any]:
    source_ref = str(path)
    source_id = slugify(path.stem, "transcript")
    if source_input:
        if is_url(source_input):
            source_ref = source_input
            source_id = youtube_video_id(source_input) or source_id
        else:
            source_path = Path(source_input).expanduser().resolve()
            source_ref = str(source_path)
            source_id = slugify(source_path.stem, "video")
    return {
        "id": source_id,
        "title": title or path.stem,
        "webpage_url": source_ref,
        "extractor_key": "transcript_file",
        "transcript_path": str(path),
    }


def download_subtitles(input_value: str, out: Path, languages: str, log: Path, cookies_from_browser: str | None = None, js_runtime: str | None = None, tool_timeout: float | None = None, cookies_file: str | None = None) -> list[dict[str, Any]]:
    if not is_url(input_value):
        return []
    yt_dlp = tool_command("yt-dlp")
    subs_dir = out / "subs"
    subs_dir.mkdir(parents=True, exist_ok=True)
    # Write both manual and automatic subtitles without media download.
    run([
        *yt_dlp, *yt_dlp_extra_args(cookies_from_browser, js_runtime, cookies_file), "--skip-download", "--no-playlist",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", languages,
        "--sub-format", "vtt/srt/best",
        "-o", str(subs_dir / "%(id)s.%(ext)s"),
        input_value,
    ], log_file=log, check=False, timeout=tool_timeout)

    candidates = sorted([p for p in subs_dir.glob("*") if p.suffix.lower() in {".vtt", ".srt"}], key=lambda p: p.stat().st_size, reverse=True)
    for path in candidates:
        segments = parse_vtt_or_srt(path)
        if len(segments) >= 3:
            write_json(out / "transcript_source.json", {"source": "subtitle", "path": str(path)})
            return segments
    return []


def extract_audio(input_value: str, out: Path, metadata: dict[str, Any], log: Path, cookies_from_browser: str | None = None, js_runtime: str | None = None, tool_timeout: float | None = None, cookies_file: str | None = None) -> Path:
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    if is_url(input_value):
        yt_dlp = tool_command("yt-dlp")
        before = set(audio_dir.glob("*"))
        run([
            *yt_dlp, *yt_dlp_extra_args(cookies_from_browser, js_runtime, cookies_file), "--no-playlist",
            "-f", "bestaudio/best",
            "-x", "--audio-format", "m4a", "--audio-quality", "5",
            "-o", str(audio_dir / "%(id)s.%(ext)s"),
            input_value,
        ], log_file=log, timeout=tool_timeout)
        after = set(audio_dir.glob("*"))
        new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
        if not new_files:
            new_files = sorted(audio_dir.glob("*.m4a"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not new_files:
            raise RuntimeError("Audio extraction completed but no audio file was found.")
        return new_files[0]
    else:
        require("ffmpeg")
        p = Path(input_value).expanduser().resolve()
        audio_path = audio_dir / f"{slugify(p.stem)}.m4a"
        run(["ffmpeg", "-y", "-i", str(p), "-vn", "-acodec", "aac", "-b:a", "96k", str(audio_path)], log_file=log)
        return audio_path


def transcribe_audio(audio_path: Path, out: Path, whisper_model: str, log: Path) -> list[dict[str, Any]]:
    try:
        import mlx_whisper  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("mlx-whisper is not installed. Run: python3 -m pip install mlx-whisper") from exc

    with log.open("a", encoding="utf-8") as f:
        f.write(f"\nTranscribing with mlx-whisper model={whisper_model}\n")
    result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=whisper_model)
    raw_segments = result.get("segments") or []
    segments: list[dict[str, Any]] = []
    for seg in raw_segments:
        text = clean_caption_text(str(seg.get("text", "")))
        if text:
            segments.append({
                "start": round(float(seg.get("start", 0)), 3),
                "end": round(float(seg.get("end", 0)), 3),
                "text": text,
            })
    if not segments and result.get("text"):
        segments = [{"start": 0.0, "end": 0.0, "text": clean_caption_text(result["text"])}]
    write_json(out / "transcript_source.json", {"source": "mlx_whisper", "audio_path": str(audio_path), "model": whisper_model})
    return segments


def transcript_to_markdown(segments: list[dict[str, Any]]) -> str:
    lines = ["# Transcript", ""]
    for seg in segments:
        lines.append(f"[{seconds_to_hhmmss(seg['start'])} - {seconds_to_hhmmss(seg['end'])}] {seg['text']}")
    return "\n".join(lines) + "\n"


def build_agent_packet(metadata: dict[str, Any], segments: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    packet = {
        "metadata_path": str(out / "metadata.json"),
        "transcript_path": str(out / "transcript.json"),
        "transcript_markdown_path": str(out / "transcript.md"),
        "source_title": metadata.get("title"),
        "source_url": metadata.get("webpage_url") or metadata.get("original_url"),
        "duration": metadata.get("duration"),
        "task_for_agent": {
            "produce_files": ["summary.json", "debate.json", "frame_plan.json", "image_prompts.json"],
            "rules": [
                "Use timestamp evidence for claims.",
                "Separate FACT, AUTHOR_VIEW, MODEL_INFERENCE, COUNTERPOINT, JUDGMENT, TODO_VERIFY.",
                "Select frames only when visual evidence adds meaning.",
                "Generated image prompts must request original hand-drawn learning diagrams, not screenshot recreation."
            ]
        },
        "first_segments_preview": segments[:12],
    }
    write_json(out / "agent_packet.json", packet)
    return packet


def cmd_prepare(args: argparse.Namespace) -> Path:
    transcript_arg = getattr(args, "transcript", None)
    if not args.input and not transcript_arg:
        raise SystemExit("prepare requires --input or --transcript")
    out = resolve_output_dir(args.out, args.input, transcript_arg)
    out.mkdir(parents=True, exist_ok=True)
    ensure_note_package_dirs(out)
    log = out / "logs" / "prepare.log"
    if transcript_arg:
        transcript_path = Path(transcript_arg).expanduser().resolve()
        if not transcript_path.exists():
            raise FileNotFoundError(transcript_path)
        metadata = metadata_for_transcript(transcript_path, args.input, getattr(args, "title", None))
        out = rehome_output_dir_for_title(out, args.out, metadata)
        ensure_note_package_dirs(out)
        log = out / "logs" / "prepare.log"
        write_json(out / "metadata.json", metadata)
        segments = load_transcript_file(transcript_path)
        archived_path = archive_source_transcript(transcript_path, out)
        write_json(out / "transcript_source.json", {"source": "transcript_file", "path": str(transcript_path), "archived_path": archived_path})
    else:
        metadata = metadata_for_input(args.input, out, log, args.cookies_from_browser, args.js_runtime, args.tool_timeout, args.cookies)
        out = rehome_output_dir_for_title(out, args.out, metadata)
        ensure_note_package_dirs(out)
        log = out / "logs" / "prepare.log"
        write_json(out / "metadata.json", metadata)
        segments = download_subtitles(args.input, out, args.languages, log, args.cookies_from_browser, args.js_runtime, args.tool_timeout, args.cookies)
        if not segments:
            audio = extract_audio(args.input, out, metadata, log, args.cookies_from_browser, args.js_runtime, args.tool_timeout, args.cookies)
            segments = transcribe_audio(audio, out, args.whisper_model, log)
    if not segments:
        raise RuntimeError("No transcript segments produced.")
    write_json(out / "transcript.json", segments)
    (out / "transcript.md").write_text(transcript_to_markdown(segments), encoding="utf-8")
    build_agent_packet(metadata, segments, out)
    print(f"Prepared evidence packet at: {out}")
    print(f"Next: have the agent read agent_packet.json + transcript.md and write summary.json, debate.json, frame_plan.json, image_prompts.json")
    return out


def segment_midpoint(seg: dict[str, Any]) -> float:
    return (float(seg.get("start", 0)) + float(seg.get("end", 0))) / 2


def compact_text(text: str, limit: int = 160) -> str:
    text = clean_caption_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def full_segment_text(segs: list[dict[str, Any]]) -> str:
    return clean_caption_text(" ".join(str(seg.get("text", "")) for seg in segs))


def first_complete_sentence(text: Any, fallback_limit: int = 120) -> str:
    text = clean_caption_text(str(text or ""))
    if not text:
        return ""
    for mark in ["。", "？", "！", ";", "；", ". "]:
        pos = text.find(mark)
        if 0 < pos <= max(fallback_limit, 40):
            return text[: pos + len(mark)].strip()
    return text if len(text) <= fallback_limit else text[:fallback_limit].rstrip()


def chunk_segments(segments: list[dict[str, Any]], max_chapters: int | None = None) -> list[list[dict[str, Any]]]:
    if not segments:
        return []
    if max_chapters is None:
        duration = max(float(segments[-1].get("end", 0)), float(len(segments) * 10))
        if duration >= 1800:
            max_chapters = 12
        elif duration >= 900:
            max_chapters = 10
        else:
            max_chapters = 6
    if len(segments) <= max_chapters:
        return [[seg] for seg in segments]
    total_duration = max(float(segments[-1].get("end", 0)), float(len(segments) * 10))
    target = max(90.0, total_duration / max_chapters)
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    chunk_start = float(segments[0].get("start", 0))
    for seg in segments:
        current.append(seg)
        if float(seg.get("end", 0)) - chunk_start >= target and len(chunks) < max_chapters - 1:
            chunks.append(current)
            current = []
            chunk_start = float(seg.get("end", 0))
    if current:
        chunks.append(current)
    return chunks


def representative_text(segs: list[dict[str, Any]], limit: int = 240) -> str:
    return first_complete_sentence(full_segment_text(segs), limit)


def detailed_text(segs: list[dict[str, Any]], limit: int | None = None) -> str:
    text = full_segment_text(segs)
    if limit is None or len(text) <= limit:
        return text
    return text[:limit].rstrip()


def segment_bullets(segs: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    for seg in segs:
        text = clean_caption_text(str(seg.get("text", "")))
        if limit is not None and len(text) > limit:
            text = text[:limit].rstrip()
        bullets.append({
            "label": LABEL_FACT,
            "text": text,
            "evidence_timestamps": [round(float(seg.get("start", 0)), 3)],
        })
    return bullets


def visual_score(text: str) -> int:
    lower = text.lower()
    return sum(1 for keyword in VISUAL_KEYWORDS if keyword in lower)


def build_summary(metadata: dict[str, Any], segments: list[dict[str, Any]]) -> dict[str, Any]:
    source_url = metadata.get("webpage_url") or metadata.get("original_url") or metadata.get("local_path") or ""
    chunks = chunk_segments(segments)
    chapters: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        start = float(chunk[0].get("start", 0))
        end = float(chunk[-1].get("end", start))
        excerpt = representative_text(chunk, 120)
        details = detailed_text(chunk)
        midpoint = segment_midpoint(chunk[min(len(chunk) // 2, len(chunk) - 1)])
        key_points = segment_bullets(chunk[:4])
        key_points.append({
            "label": LABEL_INFERENCE,
            "text": f"回看 {seconds_to_hhmmss(midpoint)} 附近的示例，补齐图表条件、失效条件和自己的判断依据。",
            "evidence_timestamps": [round(midpoint, 3)],
        })
        chapters.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "title": f"第 {index} 节：{excerpt}" if excerpt else f"第 {index} 节",
            "summary": f"{LABEL_INFERENCE} 本节内容：{details}",
            "key_points": key_points,
        })
    first = clean_caption_text(str(segments[0].get("text", ""))) if segments else ""
    last = clean_caption_text(str(segments[-1].get("text", ""))) if segments else ""
    return {
        "title": metadata.get("title") or "Video Study Note",
        "source_url": source_url,
        "tldr": [
            f"{LABEL_INFERENCE} 主线起点：{first}" if first else f"{LABEL_INFERENCE} 主线起点暂缺。",
            f"{LABEL_INFERENCE} 收束观点：{last}" if last else f"{LABEL_INFERENCE} 收束观点暂缺。",
            f"{LABEL_TODO} 关键交易概念和图表示例需要回看原视频时间戳后再用于真实交易判断。",
        ],
        "chapters": chapters,
        "action_items": [
            "逐个回看关键时间戳，把 PD Array、Order Block、FVG 等概念在自己的图表中标出来。",
            "把每个入场判断拆成：所在区间、触发结构、风险位置、失效条件。",
            "对任何交易结论先做历史图表复盘，不要只根据摘要直接下单。",
        ],
        "review_questions": [
            "PD Array 在这支视频里解决的核心问题是什么？",
            "Premium / Discount 的 50% 分界如何改变做多和做空的等待位置？",
            "Order Block 的有效条件有哪些？哪些条件需要小时间框架确认？",
            "如果一个位置看起来符合 ICT 术语，但没有流动性或结构转换，还能不能交易？",
            "哪些内容只是作者观点，哪些内容可以从图表证据验证？",
        ],
        "closing_excerpt": last,
    }


def build_debate(summary: dict[str, Any], segments: list[dict[str, Any]]) -> dict[str, Any]:
    first_ts = round(float(segments[0].get("start", 0)), 3) if segments else 0.0
    author_claims = []
    chapter_reviews: list[dict[str, Any]] = []
    for index, chapter in enumerate(summary.get("chapters", []), start=1):
        text = chapter.get("summary", "").replace(LABEL_INFERENCE, "").strip()
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        title = chapter.get("title") or f"第 {index} 节"
        short_topic = first_complete_sentence(str(title).split("：", 1)[-1], 80)
        author_claim = text
        if index <= 8:
            author_claims.append({
                "chapter_index": index,
                "chapter_title": title,
                "start": round(start, 3),
                "end": round(end, 3),
                "claim": text,
                "evidence_timestamps": [round(start, 3)],
            })
        chapter_reviews.append({
            "chapter_index": index,
            "chapter_title": title,
            "start": round(start, 3),
            "end": round(end, 3),
            "author_view": author_claim,
            "skeptic_view": (
                f"本章围绕“{short_topic}”。需要警惕把作者的术语解释直接当成交易信号；"
                "还要回看画面、记录图表条件，并用历史样本验证。"
            ),
            "counter_view": f"也可以把“{short_topic}”当作复盘观察清单，而不是直接可执行的入场信号。",
            "judge_view": (
                f"这一节适合先转成验证问题：在图表上如何确认“{short_topic}”？"
                "可用价值在于帮助定位概念和时间戳；真实有效性取决于后续复盘。"
            ),
            "what_to_verify_next": [
                f"回看 {seconds_to_hhmmss(start)} 至 {seconds_to_hhmmss(end)}，确认本章是否漏掉图表细节。",
                "把本节提到的概念写成自己的验证条件，而不是只记术语名称。",
            ],
            "confidence": 0.62 if segments else 0.0,
            "evidence_timestamps": [round(start, 3)],
        })
    if not author_claims:
        author_claims.append({"claim": "没有足够 transcript，无法可靠还原作者观点。", "evidence_timestamps": [first_ts]})
    return {
        "chapter_reviews": chapter_reviews,
        "author_view": author_claims,
        "skeptic_view": [
            {
                "issue": "当前分析基于 transcript 和关键帧，不能证明交易方法本身长期有效。",
                "why_it_matters": "交易策略需要回测、样本外验证和风险控制；视频讲解只能作为学习材料。",
                "evidence_timestamps": [first_ts],
            },
            {
                "issue": "章节边界由时间戳和 transcript 自动推断，不等同于作者原始大纲。",
                "why_it_matters": "复习时应以原视频画面和实际图表示例为准，必要时手动调整章节。",
                "evidence_timestamps": [first_ts],
            },
        ],
        "counter_view": [
            {
                "claim": "也可以把这支视频视为 ICT 术语入门，而不是完整可执行交易系统。",
                "supporting_reason": "视频覆盖概念很多，但真正执行还需要流动性、结构、时段、止损和样本验证共同成立。",
            }
        ],
        "judge": {
            "useful_parts": [
                "PD Array 把“价格是否值得入场”转成 Premium / Discount 与具体价格结构的问题。",
                "Order Block、FVG、Breaker Block 等工具可以作为复盘图表时的观察清单。",
                "作者强调看懂位置和结构后，再结合图表细节判断是否值得等待。",
            ],
            "questionable_parts": [
                "任何“聪明钱会在这里进场”的说法都需要图表样本验证，不能只看术语定义。",
                "个别概念边界容易被学成术语记忆，必须回到图表条件和失效条件。",
            ],
            "what_to_verify_next": [
                "回看 20:06 附近的 Premium / Discount 解释，并在自己的图表上画 50% 分界。",
                "回看 23:33-26:44 附近的 Order Block 示例，确认吞没条件和小时间框架确认。",
                "把视频提到的 PD Array 工具列成复盘清单，逐一找历史案例。",
            ],
            "overall_confidence": 0.62 if segments else 0.0,
        },
    }


def build_frame_plan(metadata: dict[str, Any], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_url = metadata.get("webpage_url") or metadata.get("original_url") or metadata.get("local_path") or ""
    candidates = sorted(segments, key=lambda seg: visual_score(str(seg.get("text", ""))), reverse=True)
    plan: list[dict[str, Any]] = []
    for seg in candidates:
        score = visual_score(str(seg.get("text", "")))
        if score <= 0:
            continue
        ts = round(segment_midpoint(seg), 3)
        plan.append({
            "timestamp": ts,
            "timestamp_link": timestamp_link(source_url, ts),
            "topic": clean_caption_text(str(seg.get("text", ""))),
            "reason": "字幕文本提到图表、画面或可视化内容，关键帧有助于复核讲解。",
            "evidence_quote": clean_caption_text(str(seg.get("text", ""))),
            "need_frame": True,
            "window_seconds": 8,
        })
        if len(plan) >= 8:
            break
    if not plan:
        for seg in segments[: min(3, len(segments))]:
            ts = round(segment_midpoint(seg), 3)
            plan.append({
                "timestamp": ts,
                "timestamp_link": timestamp_link(source_url, ts),
                "topic": clean_caption_text(str(seg.get("text", ""))),
                "reason": "安全模式没有发现强视觉证据触发点；默认使用时间戳链接，除非人工复核认为需要截图。",
                "evidence_quote": clean_caption_text(str(seg.get("text", ""))),
                "need_frame": False,
                "window_seconds": 8,
            })
    return plan


def build_image_prompts(summary: dict[str, Any], debate: dict[str, Any]) -> list[dict[str, Any]]:
    title = summary.get("title") or "Video Study Note"
    chapter_titles = " / ".join(ch.get("title", "") for ch in summary.get("chapters", [])[:4])
    useful = "；".join(debate.get("judge", {}).get("useful_parts", [])[:2])
    style_prompt = (
        "Ian 'Xiaohei' (小黑) hand-drawn explainer style. Pure white background, no paper texture, "
        "beige, shadows, or gradients. Thin hand-drawn black ink linework with slight hand-wobble, "
        "lots of whitespace, subject fills only 40-60% of the 16:9 landscape frame. Express one "
        "single clear visual metaphor; use an absurd contraption only when it clarifies the actual "
        "argument. 小黑 is a solid matte-black blob figure with two small "
        "white dot eyes, thin stick legs, blank expression, actively operating the contraption. "
        "Add sparse handwritten Chinese annotation labels in red, orange, and blue with thin arrows. "
        "Weird, witty, clean, never cute or childish."
    )
    prompts = [
        {
            "id": "sketch_map_01",
            "type": "xiaohei_contraption",
            "title": "小黑价格筛选机",
            "prompt": (
                f"{style_prompt} "
                "画一台荒诞的价格筛选机，把视频主题转成一个可操作的学习隐喻。"
                f"主题：{title}。主要分支：{chapter_titles}。"
                "不要复刻视频截图、人物形象或原视频视觉风格。"
            ),
            "size": "1600x900",
        },
        {
            "id": "review_card_01",
            "type": "xiaohei_judgment_machine",
            "title": "小黑观点蒸馏机",
            "prompt": (
                f"{style_prompt} "
                "画一台荒诞的观点蒸馏机，把作者观点、质疑点和综合判断压缩成一个机器隐喻。"
                f"可用要点：{useful}。文字要短、清晰可读。不要复制任何视频画面。"
            ),
            "size": "1600x900",
        },
    ]
    for entry in build_glossary_entries(summary.get("chapters") or [])[:8]:
        term = entry["term"]
        zh_name = entry.get("zh_name") or term
        concept_slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", term.lower(), flags=re.UNICODE).strip("_")
        concept_id = f"concept_{concept_slug or 'item'}"
        prompts.append({
            "id": concept_id,
            "type": "xiaohei_concept_card",
            "title": f"{zh_name} ({term}) 概念图" if zh_name != term else f"{term} 概念图",
            "role": "concept",
            "concept_term": term,
            "prompt": (
                f"{style_prompt} "
                f"只解释一个交易概念：{zh_name}，英文原词是 {term}。用图说明：{entry['plain']} "
                f"这张图要让初学者立刻看懂它解决的问题：{entry['why']} "
                "图内只放 3 到 6 个短中文标签，避免长段文字。不要出现提示词、生成过程、AI、模型、总结图这些词。"
            ),
            "size": "1600x900",
        })
    return prompts



def build_analysis_outputs(metadata: dict[str, Any], segments: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    summary = build_summary(metadata, segments)
    debate = build_debate(summary, segments)
    frame_plan = build_frame_plan(metadata, segments)
    image_prompts = build_image_prompts(summary, debate)
    return summary, debate, frame_plan, image_prompts


def cmd_analyze(args: argparse.Namespace) -> Path:
    out = Path(args.out).expanduser().resolve()
    metadata = read_json(out / "metadata.json")
    segments = normalize_segments(read_json(out / "transcript.json"))
    summary, debate, frame_plan, image_prompts = build_analysis_outputs(metadata, segments)
    write_json(out / "summary.json", summary)
    write_json(out / "debate.json", debate)
    write_json(out / "frame_plan.json", frame_plan)
    write_json(out / "image_prompts.json", image_prompts)
    write_json(out / "generated_images.json", [])
    print(f"Analyzed transcript and wrote summary/debate/frame/image-prompt artifacts at: {out}")
    return out


def write_run_review(out: Path, mode: str) -> None:
    metadata = load_optional_json(out / "metadata.json", {})
    transcript = load_optional_json(out / "transcript.json", [])
    summary = load_optional_json(out / "summary.json", {})
    debate = load_optional_json(out / "debate.json", {})
    frame_plan = load_optional_json(out / "frame_plan.json", [])
    frames_index = out / "frames" / "index.json"
    selected_frames = load_optional_json(out / "frames" / "selected_frames.json", [])
    has_saved_frames = frames_index.exists() or bool(selected_frames)
    storyboard_only = bool(selected_frames) and all(item.get("source") == "youtube_storyboard" for item in selected_frames)
    authorized_selected_frames = bool(selected_frames) and all(
        item.get("source") != "youtube_short_clip_highres" or item.get("authorized_for_private_study")
        for item in selected_frames
    )
    labels_seen = set()
    for chapter in summary.get("chapters", []):
        for item in chapter.get("key_points", []):
            labels_seen.add(item.get("label"))
    if debate:
        labels_seen.update({LABEL_AUTHOR, LABEL_COUNTER, LABEL_JUDGMENT})
    required = [LABEL_FACT, LABEL_AUTHOR, LABEL_INFERENCE, LABEL_COUNTER, LABEL_JUDGMENT]
    review = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "source": metadata.get("webpage_url") or metadata.get("original_url") or metadata.get("local_path"),
        "transcript_segments": len(transcript),
        "chapters": len(summary.get("chapters", [])),
        "frame_plan_items": len(frame_plan),
        "saved_frames": has_saved_frames,
        "label_coverage": {label: label in labels_seen for label in required},
        "scores": {
            "summary_coverage": min(1.0, len(summary.get("chapters", [])) / 4) if transcript else 0.0,
            "timestamp_evidence_quality": 1.0 if transcript and frame_plan else 0.0,
            "boundary_compliance": 1.0 if mode == "authorized" or not has_saved_frames or storyboard_only or authorized_selected_frames else 0.0,
            "reviewability": 1.0 if (out / "report.md").exists() else 0.0,
        },
        "next_optimization_suggestions": [
            "Manually enrich key claims that matter with deeper domain judgment.",
            "Use authorized frame mode only for timestamps where visual evidence changes understanding.",
            "Promote verified recurring lessons into references/video-patterns only after review.",
        ],
    }
    write_json(out / "run_review.json", review)
    notes = [
        "# Notes for next run",
        "",
        f"- Source: {review['source']}",
        f"- Transcript segments: {review['transcript_segments']}",
        f"- Chapters generated: {review['chapters']}",
        f"- Safe-mode frame boundary respected: {review['scores']['boundary_compliance'] == 1.0}",
        "- Suggested next step: replace deterministic analysis sections with deeper model-assisted notes for high-value videos.",
        "",
    ]
    (out / "notes_for_next_run.md").write_text("\n".join(notes), encoding="utf-8")


def source_video_for_frames(input_value: str, out: Path, timestamp: float, window: float, mode: str, index: int, log: Path, cookies_from_browser: str | None = None, js_runtime: str | None = None, tool_timeout: float | None = None, cookies_file: str | None = None) -> Path:
    clips_dir = out / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    if not is_url(input_value):
        return Path(input_value).expanduser().resolve()
    if mode != "authorized":
        raise SystemExit("Frame extraction from URL requires --mode authorized. Otherwise use timestamp links only.")
    yt_dlp = tool_command("yt-dlp")
    start = max(0, timestamp - window / 2)
    end = timestamp + window / 2
    clip_template = clips_dir / f"clip_{index:03d}_%(id)s.%(ext)s"
    before = set(clips_dir.glob(f"clip_{index:03d}_*"))
    run([
        *yt_dlp, *yt_dlp_extra_args(cookies_from_browser, js_runtime, cookies_file), "--no-playlist",
        "-f", "bv*[height<=720]+ba/b[height<=720]/b",
        "--download-sections", f"*{seconds_to_hhmmss(start)}-{seconds_to_hhmmss(end)}",
        "--force-keyframes-at-cuts",
        "-o", str(clip_template),
        input_value,
    ], log_file=log, timeout=tool_timeout)
    after = set(clips_dir.glob(f"clip_{index:03d}_*"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_files:
        new_files = sorted(clips_dir.glob(f"clip_{index:03d}_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_files:
        raise RuntimeError("No clip produced for frame extraction.")
    return new_files[0]


def extract_frame(video_path: Path, out_path: Path, local_seek: float, log: Path) -> None:
    require("ffmpeg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-ss", f"{max(0, local_seek):.3f}", "-i", str(video_path),
        "-frames:v", "1", "-q:v", "2", str(out_path)
    ], log_file=log)


def cmd_frames(args: argparse.Namespace) -> None:
    out = Path(args.out).expanduser().resolve()
    plan = read_json(Path(args.frame_plan).expanduser().resolve())
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    log = out / "logs" / "frames.log"
    index: list[dict[str, Any]] = []
    for i, item in enumerate(plan, start=1):
        if not item.get("need_frame", True):
            continue
        ts = float(item["timestamp"])
        window = float(item.get("window_seconds", args.window_seconds))
        video_source = source_video_for_frames(args.input, out, ts, window, args.mode, i, log, args.cookies_from_browser, args.js_runtime, args.tool_timeout, args.cookies)
        # For URL clips, seek relative to clip window. For local files, seek absolute timestamp.
        offsets = [-2.0, 0.0, 2.0]
        for off in offsets:
            if is_url(args.input):
                seek = max(0.0, window / 2 + off)
            else:
                seek = max(0.0, ts + off)
            tag = "tm2" if off < 0 else "tp2" if off > 0 else "t0"
            frame_path = frames_dir / f"keyframe_{i:03d}_{tag}.jpg"
            extract_frame(video_source, frame_path, seek, log)
            index.append({
                "plan_index": i,
                "timestamp": ts + off,
                "requested_timestamp": ts,
                "offset": off,
                "topic": item.get("topic", ""),
                "reason": item.get("reason", ""),
                "path": str(frame_path.relative_to(out)),
                "source_clip_or_file": str(video_source),
            })
    write_json(frames_dir / "index.json", index)
    print(f"Extracted {len(index)} candidate frames. Review frames/index.json and write frames/selected_frames.json")


def load_optional_json(path: Path, default: Any) -> Any:
    return read_json(path) if path.exists() else default


def html_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def humanize_label_text(value: Any) -> str:
    text = clean_caption_text(str(value or ""))
    replacements = {
        LABEL_FACT: "事实：",
        LABEL_AUTHOR: "作者观点：",
        LABEL_INFERENCE: "Agent 摘要：",
        LABEL_COUNTER: "质疑：",
        LABEL_JUDGMENT: "判断：",
        LABEL_TODO: "待验证：",
    }
    for label, readable in replacements.items():
        text = text.replace(label, readable)
    return text


def html_block_text(value: Any) -> str:
    return html.escape(humanize_label_text(value), quote=False)


def item_label(value: Any) -> str:
    raw = str(value or "")
    return {
        LABEL_FACT: "事实",
        LABEL_AUTHOR: "作者观点",
        LABEL_INFERENCE: "Agent 摘要",
        LABEL_COUNTER: "质疑",
        LABEL_JUDGMENT: "判断",
        LABEL_TODO: "待验证",
    }.get(raw, raw.strip("[]") or "笔记")


def label_class(value: Any) -> str:
    raw = str(value or "")
    return {
        LABEL_FACT: "fact",
        LABEL_AUTHOR: "author",
        LABEL_INFERENCE: "inference",
        LABEL_COUNTER: "counter",
        LABEL_JUDGMENT: "judgment",
        LABEL_TODO: "todo",
    }.get(raw, "inference")


def first_timestamp_link(source_url: str, timestamps: list[Any]) -> str:
    if not timestamps:
        return ""
    try:
        return timestamp_link(source_url, float(timestamps[0]))
    except (TypeError, ValueError):
        return ""


def report_duration(metadata: dict[str, Any], summary: dict[str, Any], transcript: list[dict[str, Any]]) -> str:
    if metadata.get("duration"):
        try:
            return seconds_to_hhmmss(float(metadata["duration"]))
        except (TypeError, ValueError):
            pass
    chapters = summary.get("chapters") or []
    if chapters:
        try:
            return seconds_to_hhmmss(max(float(ch.get("end", 0)) for ch in chapters))
        except (TypeError, ValueError):
            pass
    if transcript:
        try:
            return seconds_to_hhmmss(max(float(seg.get("end", 0)) for seg in transcript))
        except (TypeError, ValueError):
            pass
    return "未知"


def render_timestamp(source_url: str, seconds: float) -> str:
    label = seconds_to_hhmmss(seconds)
    if source_url and is_url(source_url):
        return f'<a class="time-link" href="{html_escape(timestamp_link(source_url, seconds))}" target="_blank" rel="noreferrer">{html_escape(label)}</a>'
    return f'<span class="time-link">{html_escape(label)}</span>'


def chapter_index_for_timestamp(chapters: list[dict[str, Any]], timestamp: float) -> int:
    if not chapters:
        return 0
    total = len(chapters)
    for index, chapter in enumerate(chapters, start=1):
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        if index < total and start <= timestamp < end:
            return index
        if index == total and start <= timestamp <= end:
            return index
    centers = []
    for index, chapter in enumerate(chapters, start=1):
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        centers.append((abs(((start + end) / 2) - timestamp), index))
    return sorted(centers)[0][1]


def group_frames_by_chapter(selected_frames: list[dict[str, Any]], chapters: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for frame in selected_frames:
        try:
            ts = float(frame.get("timestamp", frame.get("requested_timestamp", 0)))
        except (TypeError, ValueError):
            ts = 0.0
        index = chapter_index_for_timestamp(chapters, ts)
        grouped.setdefault(index, []).append(frame)
    return grouped


def frame_timestamp(frame: dict[str, Any]) -> float:
    try:
        return float(frame.get("timestamp", frame.get("requested_timestamp", 0)))
    except (TypeError, ValueError):
        return 0.0


def nearest_selected_frame(
    *,
    timestamp: float,
    chapter_index: int,
    selected_frames: list[dict[str, Any]],
    chapters: list[dict[str, Any]],
    max_delta: float = 180.0,
) -> dict[str, Any] | None:
    if not selected_frames:
        return None
    exact = [
        frame
        for frame in selected_frames
        if round(frame_timestamp(frame), 1) == round(timestamp, 1)
    ]
    if exact:
        return exact[0]
    same_chapter = [
        frame
        for frame in selected_frames
        if chapters and chapter_index_for_timestamp(chapters, frame_timestamp(frame)) == chapter_index
    ]
    candidates = same_chapter or selected_frames
    ranked = sorted((abs(frame_timestamp(frame) - timestamp), frame) for frame in candidates)
    if ranked and ranked[0][0] <= max_delta:
        return ranked[0][1]
    return None


def normalize_chapter_reviews(debate: dict[str, Any], chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = debate.get("chapter_reviews")
    if isinstance(existing, list) and existing:
        return existing
    reviews: list[dict[str, Any]] = []
    author_by_index = {
        int(item.get("chapter_index")): item
        for item in debate.get("author_view", [])
        if isinstance(item, dict) and item.get("chapter_index")
    }
    for index, chapter in enumerate(chapters, start=1):
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        author = author_by_index.get(index, {})
        reviews.append({
            "chapter_index": index,
            "chapter_title": chapter.get("title") or f"第 {index} 节",
            "start": round(start, 3),
            "end": round(end, 3),
            "author_view": author.get("claim") or chapter.get("summary") or "",
            "skeptic_view": "需要回看原视频画面和时间戳，确认摘要没有把示例条件简化成结论。",
            "counter_view": "这一节也可能只是学习线索，不能单独构成可执行交易规则。",
            "judge_view": "先作为复习入口，再用自己的图表样本验证。",
            "what_to_verify_next": [f"回看 {seconds_to_hhmmss(start)} 至 {seconds_to_hhmmss(end)} 并补充自己的验证条件。"],
            "confidence": debate.get("judge", {}).get("overall_confidence", 0.0),
        })
    return reviews


def plain_note_text(value: Any) -> str:
    text = clean_caption_text(str(value or ""))
    for label in [LABEL_FACT, LABEL_AUTHOR, LABEL_INFERENCE, LABEL_COUNTER, LABEL_JUDGMENT, LABEL_TODO]:
        text = text.replace(label, "")
    text = re.sub(r"^\s*(本节内容|这一段的学习重点|开场重点|结尾重点|主线起点|收束观点|事实|作者观点|推断|判断|质疑|待验证|Agent 摘要)[：:]\s*", "", text)
    text = text.replace("transcript 摘要", "本章笔记")
    text = text.replace("Transcript 摘要", "本章笔记")
    text = re.sub(r"确认\s+本章笔记", "确认本章笔记", text)
    return clean_caption_text(text)


def is_process_note(value: Any) -> bool:
    text = str(value or "").lower()
    markers = [
        "transcript",
        "metadata",
        "generated",
        "imagegen",
        "debug",
        "source_transcripts",
        "报告按",
        "报告把",
        "运行复核",
        "生成信息",
        "提示词",
        "本地文件",
        "字幕文本",
        "围绕本章内容建立复习问题",
    ]
    return any(marker in text for marker in markers)


def text_sentences(value: Any) -> list[str]:
    text = plain_note_text(value)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def first_sentence(value: Any) -> str:
    sentences = text_sentences(value)
    return sentences[0] if sentences else plain_note_text(value)


def first_sentences(value: Any, limit: int = 2) -> str:
    sentences = text_sentences(value)
    if not sentences:
        return plain_note_text(value)
    return " ".join(sentences[:limit])


def chapter_bullets(chapter: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in chapter.get("key_points") or []:
        if is_process_note(item.get("text")):
            continue
        text = plain_note_text(item.get("text"))
        if not text or text in seen:
            continue
        seen.add(text)
        bullets.append({
            "label": item.get("label") or LABEL_INFERENCE,
            "text": text,
            "evidence_timestamps": item.get("evidence_timestamps") or [],
        })
        if len(bullets) >= limit:
            break
    if not bullets:
        main = first_sentence(chapter.get("summary"))
        if main:
            bullets.append({"label": LABEL_INFERENCE, "text": main, "evidence_timestamps": [chapter.get("start", 0)]})
    return bullets


def chunked_route_groups(chapters: list[dict[str, Any]]) -> list[tuple[str, list[tuple[int, dict[str, Any]]]]]:
    if not chapters:
        return []
    phase_names = ["建立框架", "理解价格位置", "识别图表结构", "回看验证"]
    group_count = min(len(phase_names), max(1, len(chapters)))
    groups: list[tuple[str, list[tuple[int, dict[str, Any]]]]] = [(phase_names[i], []) for i in range(group_count)]
    for index, chapter in enumerate(chapters, start=1):
        bucket = min(group_count - 1, int((index - 1) * group_count / max(1, len(chapters))))
        groups[bucket][1].append((index, chapter))
    return [(name, items) for name, items in groups if items]


def chunked_indexed_route_groups(indexed_chapters: list[tuple[int, dict[str, Any]]]) -> list[tuple[str, list[tuple[int, dict[str, Any]]]]]:
    if not indexed_chapters:
        return []
    phase_names = ["先定位置", "再看结构", "确认触发", "复盘验证"]
    group_count = min(len(phase_names), max(1, len(indexed_chapters)))
    groups: list[tuple[str, list[tuple[int, dict[str, Any]]]]] = [(phase_names[i], []) for i in range(group_count)]
    for list_index, item in enumerate(indexed_chapters):
        bucket = min(group_count - 1, int(list_index * group_count / max(1, len(indexed_chapters))))
        groups[bucket][1].append(item)
    return [(name, items) for name, items in groups if items]


def chapter_focus_score(chapter: dict[str, Any]) -> int:
    text = " ".join([
        str(chapter.get("title") or ""),
        str(chapter.get("summary") or ""),
        " ".join(str(item.get("text") or "") for item in chapter.get("key_points") or [] if isinstance(item, dict)),
    ])
    lower = text.lower()
    score = 0
    for keyword in CORE_CONTENT_KEYWORDS:
        if keyword.lower() in lower:
            score += 2
    for keyword in EDGE_CONTENT_KEYWORDS:
        if keyword.lower() in lower:
            score -= 3
    if "50%" in text:
        score += 2
    if "pd array" in lower and ("高价区" in text or "低价区" in text or "订单块" in text):
        score += 2
    return score


def split_core_chapters(chapters: list[dict[str, Any]]) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]]]:
    core: list[tuple[int, dict[str, Any]]] = []
    edge: list[tuple[int, dict[str, Any]]] = []
    for index, chapter in enumerate(chapters, start=1):
        if chapter_focus_score(chapter) >= 2:
            core.append((index, chapter))
        else:
            edge.append((index, chapter))
    if not core and chapters:
        core = list(enumerate(chapters, start=1))
        edge = []
    return core, edge


def chapters_only(indexed_chapters: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [chapter for _, chapter in indexed_chapters]


def build_plain_core_summary(chapters: list[dict[str, Any]], debate: dict[str, Any]) -> list[str]:
    text = " ".join(str(ch.get("summary") or "") for ch in chapters).lower()
    if "pd array" in text and ("premium" in text or "discount" in text or "订单块" in text):
        return [
            "这支视频的核心不是背 ICT 术语，而是建立入场前的检查顺序。",
            "先选定一个价格区间，用 50% 分界判断价格处在高价区还是低价区。",
            "再看 Order Block、FVG 等结构是否给出值得等待的位置。",
            "最后必须用小周期确认和失效条件过滤，不能把任何一个术语单独当成入场信号。",
        ]
    items = []
    for text_item in (debate.get("judge") or {}).get("useful_parts") or []:
        clean = plain_note_text(text_item)
        if clean and not is_process_note(clean):
            items.append(clean)
    return items[:4]


def build_glossary_entries(chapters: list[dict[str, Any]]) -> list[dict[str, str]]:
    corpus = " ".join([
        str(chapter.get("title") or "") + " " + str(chapter.get("summary") or "")
        for chapter in chapters
    ]).lower()
    entries: list[dict[str, str]] = []
    for entry in TRADING_GLOSSARY:
        if any(alias.lower() in corpus for alias in entry["aliases"]):
            entries.append({
                "term": entry["term"],
                "zh_name": entry.get("zh_name") or entry["term"],
                "plain": entry["plain"],
                "why": entry["why"],
            })
    return entries


def build_concept_course_cards(glossary_entries: list[dict[str, str]]) -> list[dict[str, Any]]:
    defaults = {
        "PD Array": {
            "video_example": "视频把它放在入场前，先判断价格位置和结构，再决定是否值得等待。",
            "judging_rule": "先选区间，再判断高低价区，最后只把 OB/FVG 等结构当成候选条件。",
            "common_misuse": "把 PD Array 当成直接买卖按钮。",
            "exercise": "如果你只看到一个 Order Block，但没有区间、半区和小周期确认，能不能直接入场？",
            "answer": "不能。它还缺少位置过滤、结构确认和失效条件。",
        },
        "Premium / Discount": {
            "video_example": "视频用 50% 分界说明价格处在相对高价区还是低价区。",
            "judging_rule": "先有明确 Dealing Range，50% 分界才有意义。",
            "common_misuse": "看到 Premium 就直接做空，看到 Discount 就直接做多。",
            "exercise": "价格在 Premium 区，是否一定可以做空？",
            "answer": "不一定。Premium 只是位置过滤，还需要结构、触发和风险条件。",
        },
        "Dealing Range": {
            "video_example": "视频把高低点之间的波段作为 Premium / Discount 的参照物。",
            "judging_rule": "区间边界必须清楚，否则 50% 分界会变成主观画线。",
            "common_misuse": "为了让结论成立，事后随便换一个区间。",
            "exercise": "为什么没有 Dealing Range，就不能谈 Premium / Discount？",
            "answer": "因为贵和便宜必须有参照区间，区间不清楚，50% 分界也不可靠。",
        },
        "Order Block": {
            "video_example": "视频用订单块说明机构可能留下订单的候选区域，并强调要看后续反应。",
            "judging_rule": "至少结合位移、吞没、回踩、小周期确认和失效条件。",
            "common_misuse": "看到最后一根反向 K 线就直接进场。",
            "exercise": "一个 Order Block 要更接近可用信号，至少还需要什么？",
            "answer": "需要后续强位移、结构变化、回踩反应、小周期确认和明确失效点。",
        },
        "FVG": {
            "video_example": "视频把 FVG 作为价格快速移动后的失衡区域，用来观察可能回补或反应。",
            "judging_rule": "FVG 要和位置、结构、流动性或小周期确认一起看。",
            "common_misuse": "把任何空档都当作独立入场信号。",
            "exercise": "FVG 为什么不能单独作为交易理由？",
            "answer": "因为它只说明失衡区域，不说明方向、胜率、风险和失效条件。",
        },
        "小周期确认": {
            "video_example": "视频在大区间找到候选区域后，要求切到小周期观察结构变化或 FVG。",
            "judging_rule": "大周期给位置，小周期给触发和风险边界。",
            "common_misuse": "大周期看到区域就马上进场。",
            "exercise": "小周期确认主要解决什么问题？",
            "answer": "解决触发和过滤假信号的问题，避免只凭大区间位置入场。",
        },
    }
    cards: list[dict[str, Any]] = []
    for entry in glossary_entries:
        extra = defaults.get(entry["term"], {})
        cards.append({
            "term": entry["term"],
            "zh_name": entry.get("zh_name") or entry["term"],
            "definition": entry["plain"],
            "why_it_matters": entry["why"],
            "video_example": extra.get("video_example") or "把视频里的说法转成一个可验证的学习问题。",
            "judging_rule": extra.get("judging_rule") or "先写清适用条件，再写清失效条件。",
            "common_misuse": extra.get("common_misuse") or "只记术语，不写判断条件。",
            "exercise": extra.get("exercise") or f"{entry['term']} 在本视频里解决什么问题？",
            "answer": extra.get("answer") or entry["why"],
        })
    return cards


def build_core_cards(summary: dict[str, Any], debate: dict[str, Any]) -> list[dict[str, str]]:
    corpus = " ".join(
        [str(summary.get("title") or "")]
        + [str(ch.get("title") or "") + " " + str(ch.get("summary") or "") for ch in summary.get("chapters") or []]
    ).lower()
    if "pd array" in corpus and ("order block" in corpus or "premium" in corpus):
        return [
            {
                "title": "PD Array 是位置过滤器，不是入场信号",
                "body": "它先帮你判断价格是否处在值得等待的区域，再决定是否继续看结构。",
                "tag": "判断",
            },
            {
                "title": "Premium / Discount 依赖 Dealing Range",
                "body": "先定义清楚波段高低点，50% 分界才有意义；区间选错，贵便宜判断会失真。",
                "tag": "前提",
            },
            {
                "title": "Order Block 必须结合小周期确认",
                "body": "订单块只是候选反应区，还需要位移、回踩、结构变化和明确失效条件。",
                "tag": "误用",
            },
            {
                "title": "FVG 只能说明失衡，不等于方向",
                "body": "FVG 更适合作为观察价格是否回补和反应的线索，不能单独证明入场价值。",
                "tag": "边界",
            },
            {
                "title": "术语越多，越需要反例验证",
                "body": "这支视频适合建立复盘框架，但不等于证明策略胜率；交易结论必须回到历史样本。",
                "tag": "风险",
            },
        ]

    cards: list[dict[str, str]] = []
    judge = debate.get("judge") or {}
    for text in judge.get("useful_parts") or []:
        if is_process_note(text):
            continue
        clean = plain_note_text(text)
        if clean:
            cards.append({"title": "可复用结论", "body": clean, "tag": "判断"})
        if len(cards) >= 3:
            break
    for chapter in summary.get("chapters") or []:
        title = chapter_display_title(int(chapter.get("chapter_index", 0) or len(cards) + 1), chapter)
        for item in chapter_bullets(chapter, limit=2):
            text = item["text"]
            if is_process_note(text):
                continue
            if text and all(text != existing["body"] for existing in cards):
                cards.append({"title": first_sentence(title), "body": text, "tag": item_label(item["label"])})
                break
        if len(cards) >= 6:
            break
    return cards[:6]


def build_global_controversies(summary: dict[str, Any], debate: dict[str, Any]) -> list[dict[str, str]]:
    corpus = " ".join(str(ch.get("summary") or "") for ch in summary.get("chapters") or []).lower()
    if "pd array" in corpus and ("premium" in corpus or "order block" in corpus):
        return [
            {
                "title": "PD Array 是有效框架，还是事后解释工具？",
                "author_view": "作者倾向于把它当作识别聪明钱价格输送的框架。",
                "counter_view": "如果没有统计样本，它也可能只是把普通价格行为重新命名。",
                "judgment": "适合作为观察清单，不适合作为单独交易系统。",
            },
            {
                "title": "Premium / Discount 的 50% 分界是否足够？",
                "author_view": "作者认为 50% 可以帮助判断价格相对贵便宜。",
                "counter_view": "区间选择高度主观，不同人可能画出不同 Dealing Range。",
                "judgment": "必须先固定区间边界，否则 50% 分界没有学习价值。",
            },
            {
                "title": "Order Block 能否稳定提供入场？",
                "author_view": "作者把订单块视为机构可能留下订单的候选区域。",
                "counter_view": "图上到处都能画订单块，缺少确认时容易过拟合。",
                "judgment": "只能作为候选区域，必须结合结构转换、FVG、小周期确认和失效条件。",
            },
        ]
    issues = debate.get("skeptic_view") or []
    rows: list[dict[str, str]] = []
    for item in issues[:3]:
        rows.append({
            "title": item.get("issue") or "需要审查的主张",
            "author_view": "作者观点需要结合原始证据理解。",
            "counter_view": item.get("why_it_matters") or "当前证据不足以直接得出强结论。",
            "judgment": "作为学习线索保留，应用前需要独立验证。",
        })
    return rows


def chapter_learning_judgment(chapter: dict[str, Any], review: dict[str, Any]) -> dict[str, str]:
    text = " ".join([str(chapter.get("title") or ""), str(chapter.get("summary") or ""), str(review.get("author_view") or "")]).lower()
    if "order block" in text or "订单块" in text:
        return {
            "useful_point": "Order Block 可以帮助定位候选反应区域。",
            "misuse": "看到最后一根反向 K 线就直接进场。",
            "verification": "必须看到后续强位移、结构变化，并在小周期出现确认。",
            "handling": "只把 Order Block 当候选区，不把它当买卖按钮。",
        }
    if "premium" in text or "discount" in text or "50%" in text or "高价区" in text or "低价区" in text:
        return {
            "useful_point": "Premium / Discount 可以把价格位置转成高低价区判断。",
            "misuse": "价格在高价区就直接做空，或在低价区就直接做多。",
            "verification": "先确认 Dealing Range 边界，再看 50% 分界和后续结构。",
            "handling": "只用它过滤位置，触发仍交给结构和小周期确认。",
        }
    if "pd array" in text:
        return {
            "useful_point": "PD Array 把入场前检查变成清单。",
            "misuse": "把清单里的任意一个术语当成单独信号。",
            "verification": "逐项确认区间、半区、结构、触发和失效条件。",
            "handling": "用它决定是否继续等待，而不是直接决定下单。",
        }
    if "fvg" in text or "fair value gap" in text or "失衡" in text:
        return {
            "useful_point": "FVG 可以提示价格失衡和可能回补的区域。",
            "misuse": "看到空档就当成方向信号。",
            "verification": "确认它是否处在合理位置，并结合结构变化。",
            "handling": "把它作为辅助条件，不让它单独决定交易。",
        }
    return {
        "useful_point": first_sentence(review.get("author_view") or chapter.get("summary")) or "这一章提供一个学习线索。",
        "misuse": "只记住结论，不记录适用条件和失效条件。",
        "verification": "把本章结论转成可观察条件，并用样本复核。",
        "handling": "先当作学习框架，不能直接当成行动指令。",
    }


def build_assessment(summary: dict[str, Any], glossary_entries: list[dict[str, str]]) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    terms = {entry["term"] for entry in glossary_entries}
    if "PD Array" in terms:
        questions.append({
            "id": "q_pd_array_role",
            "type": "single_choice",
            "question": "PD Array 在这支视频里主要解决什么问题？",
            "options": ["预测下一根 K 线方向", "判断价格位置和结构是否值得等待", "计算仓位大小", "识别新闻影响"],
            "answer_index": 1,
            "explanation": "PD Array 是入场前的检查清单，先判断位置和结构，不直接给买卖按钮。",
            "lesson_ref": "PD Array",
        })
    if "Premium / Discount" in terms:
        questions.append({
            "id": "q_premium_discount",
            "type": "single_choice",
            "question": "价格在 Dealing Range 的 50% 上方，是否可以直接做空？",
            "options": ["可以，因为这是 Premium", "不可以，还需要结构和触发确认", "可以，只要出现红色 K 线", "一定要先看成交量"],
            "answer_index": 1,
            "explanation": "Premium 只能说明相对高价区，不能单独构成入场信号。",
            "lesson_ref": "Premium / Discount",
        })
    if "Dealing Range" in terms:
        questions.append({
            "id": "q_dealing_range",
            "type": "single_choice",
            "question": "为什么必须先定义 Dealing Range？",
            "options": ["为了让 50% 分界有参照物", "为了让图表更好看", "为了避开所有亏损", "为了代替止损"],
            "answer_index": 0,
            "explanation": "高价区和低价区必须依赖一个明确区间，否则贵便宜判断会变得主观。",
            "lesson_ref": "Dealing Range",
        })
    if "Order Block" in terms:
        questions.append({
            "id": "q_order_block",
            "type": "single_choice",
            "question": "一个 Order Block 更接近可用候选区，至少还需要什么？",
            "options": ["名字听起来专业", "后续位移、回踩反应、小周期确认和失效点", "只要价格碰到区域", "只要它出现在日线"],
            "answer_index": 1,
            "explanation": "订单块是候选区域，需要结构确认和风险边界。",
            "lesson_ref": "Order Block",
        })
    if "FVG" in terms:
        questions.append({
            "id": "q_fvg",
            "type": "single_choice",
            "question": "FVG 最合理的用法是什么？",
            "options": ["单独作为交易方向", "观察失衡区域，并结合位置和结构", "替代 Dealing Range", "保证价格一定回补"],
            "answer_index": 1,
            "explanation": "FVG 只说明失衡，不说明方向、胜率或失效条件。",
            "lesson_ref": "FVG",
        })
    if "小周期确认" in terms:
        questions.append({
            "id": "q_small_tf",
            "type": "single_choice",
            "question": "小周期确认主要解决什么问题？",
            "options": ["把大周期区域变成更具体的触发条件", "让所有交易都盈利", "取消止损", "忽略高低价区"],
            "answer_index": 0,
            "explanation": "大周期给位置，小周期帮助确认触发、过滤假信号并控制风险。",
            "lesson_ref": "小周期确认",
        })
    if not questions:
        for index, question in enumerate(summary.get("review_questions") or [], start=1):
            questions.append({
                "id": f"q_{index:02d}",
                "type": "self_check",
                "question": question,
                "options": ["我能说清", "我还不确定"],
                "answer_index": 0,
                "explanation": "用自己的话复述，并回到对应章节检查条件是否完整。",
                "lesson_ref": "全片",
            })
    return {
        "mastery_threshold": 0.8,
        "quiz": questions,
        "score_bands": [
            {"min": 0.8, "label": "完成学习", "advice": "可以进入自己的图表样本验证。"},
            {"min": 0.6, "label": "需要补课", "advice": "重看错题对应概念卡和核心章节。"},
            {"min": 0.0, "label": "不建议认为已掌握", "advice": "先完成概念翻译和 5 分钟速学。"},
        ],
    }


def visual_objects_from_text(text: str) -> list[str]:
    lower = text.lower()
    objects: list[str] = []
    for keyword, label in [
        ("pd array", "PD Array"),
        ("premium", "Premium"),
        ("discount", "Discount"),
        ("dealing range", "Dealing Range"),
        ("order block", "Order Block"),
        ("fvg", "FVG"),
        ("50%", "50% 分界"),
        ("订单块", "订单块"),
        ("小周期", "小周期确认"),
        ("结构", "结构变化"),
    ]:
        if keyword in lower or keyword in text:
            objects.append(label)
    return sorted(set(objects))


def build_visual_storyboard(
    summary: dict[str, Any],
    frame_plan: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chapters = summary.get("chapters") or []
    rows: list[dict[str, Any]] = []
    used_frame_paths: set[str] = set()
    for item in frame_plan:
        ts = float(item.get("timestamp", 0))
        topic = plain_note_text(item.get("topic") or item.get("evidence_quote") or "")
        chapter_index = chapter_index_for_timestamp(chapters, ts) if chapters else 0
        selected = nearest_selected_frame(
            timestamp=ts,
            chapter_index=chapter_index,
            selected_frames=selected_frames,
            chapters=chapters,
        )
        frame_path = selected.get("selected_frame") if selected else ""
        if frame_path:
            used_frame_paths.add(str(frame_path))
        objects = visual_objects_from_text(topic)
        rows.append({
            "timestamp": ts,
            "chapter_index": chapter_index,
            "frame": frame_path,
            "visual_type": "chart_example" if objects else "source_moment",
            "teaching_role": topic,
            "must_explain": bool(item.get("need_frame")),
            "objects": objects,
            "replacement_text": "看图时先定位区间和分界，再看结构是否给出触发和失效条件。" if objects else "该时间点用于来源核对。",
            "needs_annotation": bool(item.get("need_frame")) and not selected,
        })
    for frame in selected_frames:
        frame_path = str(frame.get("selected_frame") or frame.get("path") or "")
        if not frame_path or frame_path in used_frame_paths:
            continue
        ts = frame_timestamp(frame)
        topic = plain_note_text(frame.get("caption") or frame.get("topic") or frame.get("why_selected") or "")
        chapter_index = chapter_index_for_timestamp(chapters, ts) if chapters else 0
        objects = visual_objects_from_text(topic)
        rows.append({
            "timestamp": ts,
            "chapter_index": chapter_index,
            "frame": frame_path,
            "visual_type": "chart_example" if objects else "source_moment",
            "teaching_role": topic,
            "must_explain": True,
            "objects": objects,
            "replacement_text": "这张图用于把本章文字结论落到具体画面上。" if not objects else "看图时先定位区间和分界，再看结构是否给出触发和失效条件。",
            "needs_annotation": False,
        })
    rows.sort(key=lambda row: float(row.get("timestamp", 0)))
    merged: list[dict[str, Any]] = []
    by_frame: dict[str, dict[str, Any]] = {}
    for row in rows:
        frame_path = str(row.get("frame") or "")
        if frame_path and frame_path in by_frame:
            existing = by_frame[frame_path]
            role = plain_note_text(row.get("teaching_role") or "")
            if role and role not in str(existing.get("teaching_role") or ""):
                existing["teaching_role"] = f'{existing.get("teaching_role", "")}；{role}'.strip("；")
            existing["must_explain"] = bool(existing.get("must_explain")) or bool(row.get("must_explain"))
            existing["needs_annotation"] = bool(existing.get("needs_annotation")) and bool(row.get("needs_annotation"))
            existing["objects"] = sorted(set(existing.get("objects") or []) | set(row.get("objects") or []))
            continue
        merged.append(row)
        if frame_path:
            by_frame[frame_path] = row
    return merged


def image_header_ok(path: Path) -> bool:
    try:
        data = path.read_bytes()[:16]
    except OSError:
        return False
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or (data.startswith(b"RIFF") and b"WEBP" in data)
    )


def build_asset_health(out: Path, selected_frames: list[dict[str, Any]], generated_images: list[dict[str, Any]]) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for frame in selected_frames:
        path = frame.get("selected_frame") or frame.get("path")
        if path:
            seen.add(str(path))
    for image in generated_images:
        path = image.get("path")
        if path:
            seen.add(str(path))
    for rel in sorted(seen):
        path = out / rel
        exists = path.exists()
        size = path.stat().st_size if exists and path.is_file() else 0
        decodable = exists and size > 0 and image_header_ok(path)
        assets.append({
            "path": rel,
            "exists": exists,
            "size": size,
            "decodable": decodable,
        })
    missing = [item["path"] for item in assets if not item["exists"] or item["size"] <= 0 or not item["decodable"]]
    return {
        "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
        "total": len(assets),
        "ok": len(missing) == 0,
        "missing_or_invalid": missing,
        "assets": assets,
    }


def build_lesson_units(
    summary: dict[str, Any],
    debate: dict[str, Any],
    selected_frames: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chapters = summary.get("chapters") or []
    core_indexed, _ = split_core_chapters(chapters)
    reviews = normalize_chapter_reviews(debate, chapters)
    reviews_by_index = {int(item.get("chapter_index", 0)): item for item in reviews}
    frames_by_chapter = group_frames_by_chapter(selected_frames, chapters)
    lessons: list[dict[str, Any]] = []
    for index, chapter in core_indexed:
        review = reviews_by_index.get(index, {})
        judgment = chapter_learning_judgment(chapter, review)
        title = chapter_display_title(index, chapter)
        lessons.append({
            "id": f"lesson_{index:02d}",
            "chapter_index": index,
            "title": title,
            "objective": judgment["useful_point"],
            "explanation": plain_note_text(chapter.get("summary")),
            "procedure": [item["text"] for item in chapter_bullets(chapter, limit=4)],
            "common_mistakes": [judgment["misuse"]],
            "verification_conditions": [judgment["verification"]],
            "my_handling": judgment["handling"],
            "visuals": [
                {
                    "frame": frame.get("selected_frame") or frame.get("path") or "",
                    "caption": plain_note_text(frame.get("caption") or frame.get("topic") or ""),
                    "what_to_look_at": visual_objects_from_text(str(frame.get("caption") or frame.get("topic") or "")),
                }
                for frame in frames_by_chapter.get(index, [])
            ],
            "checkpoint": {
                "question": f"这一课最容易被误用在哪里？",
                "answer": judgment["misuse"],
                "rubric": "能说出误用、验证条件和自己的处理方式，才算掌握。",
            },
        })
    return lessons


def build_replacement_review(
    *,
    summary: dict[str, Any],
    glossary_entries: list[dict[str, str]],
    lesson_units: list[dict[str, Any]],
    visual_storyboard: list[dict[str, Any]],
    assessment: dict[str, Any],
    asset_health: dict[str, Any],
    controversies: list[dict[str, str]],
) -> dict[str, Any]:
    content_score = 25 if lesson_units and glossary_entries else 15
    visual_required = [item for item in visual_storyboard if item.get("must_explain")]
    visual_ready = [item for item in visual_required if item.get("frame")]
    visual_score = 25 if visual_required and len(visual_ready) == len(visual_required) and asset_health.get("ok") else 12 if visual_required else 8
    practice_score = 20 if all("explanation" in item and "answer_index" in item for item in assessment.get("quiz", [])) else 8
    debate_score = 15 if len(controversies) >= 3 else 8
    ux_score = 15 if summary.get("tldr") and lesson_units else 10
    total = content_score + visual_score + practice_score + debate_score + ux_score
    fail_reasons: list[str] = []
    if not asset_health.get("ok"):
        fail_reasons.append("存在缺失或无法识别的图片资源。")
    if visual_required and len(visual_ready) < len(visual_required):
        fail_reasons.append("部分核心图表示例还没有本地关键帧或标注替代。")
    if not assessment.get("quiz"):
        fail_reasons.append("缺少可评分练习题。")
    if total < 85:
        fail_reasons.append("当前仍是课程化学习包，未达到完整替代视频标准。")
    return {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "replacement_score": total,
        "replacement_ready": total >= 85 and not fail_reasons,
        "score_breakdown": {
            "content_completeness": content_score,
            "visual_replacement": visual_score,
            "practice_answers": practice_score,
            "critical_review": debate_score,
            "reading_experience": ux_score,
        },
        "threshold": 85,
        "fail_reasons": fail_reasons,
    }


def render_edge_chapters(edge_chapters: list[tuple[int, dict[str, Any]]], source_url: str) -> str:
    if not edge_chapters:
        return ""
    rows = []
    for index, chapter in edge_chapters:
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        rows.append(
            '<li>'
            f'<a href="{html_escape(timestamp_link(source_url, start))}" target="_blank" rel="noreferrer">{html_escape(render_short_time_range(start, end))}</a>'
            f'<span>第 {index} 节：{html_escape(first_sentence(chapter.get("title")) or "略读内容")}</span>'
            '</li>'
        )
    return (
        '<details class="skim-details">'
        '<summary>略读内容</summary>'
        f'<ul>{"".join(rows)}</ul>'
        '</details>'
    )


def render_short_time_range(start: float, end: float) -> str:
    return f'{seconds_to_hhmmss(start)} 至 {seconds_to_hhmmss(end)}'


def render_frame_figure(frame: dict[str, Any], source_url: str, compact: bool = False) -> str:
    image_path = frame.get("selected_frame") or frame.get("path") or ""
    ts = float(frame.get("timestamp", frame.get("requested_timestamp", 0)))
    caption = frame.get("caption") or frame.get("why_selected") or frame.get("topic") or "关键截图"
    class_name = "chapter-frame" if compact else "frame-card reveal"
    return (
        f'<figure class="{class_name}">'
        f'<a href="{html_escape(image_path)}" target="_blank" rel="noreferrer">'
        f'<img src="{html_escape(image_path)}" alt="{html_escape(caption)}" loading="lazy">'
        '</a>'
        '<figcaption>'
        f'<strong>{html_block_text(frame.get("topic") or "关键画面")}</strong>'
        f'<span>{render_timestamp(source_url, ts)}</span>'
        f'<p>{html_block_text(caption)}</p>'
        '</figcaption>'
        '</figure>'
    )


def render_chapter_review(chapter: dict[str, Any], review: dict[str, Any], source_url: str) -> str:
    judgment = chapter_learning_judgment(chapter, review)
    start = float(review.get("start", 0))
    judgment_rows = "".join(
        '<article>'
        f'<h4>{html_escape(label)}</h4>'
        f'<p>{html_escape(text)}</p>'
        '</article>'
        for label, text in [
            ("本章可用点", judgment["useful_point"]),
            ("可能误用", judgment["misuse"]),
            ("验证条件", judgment["verification"]),
            ("我的处理", judgment["handling"]),
        ]
    )
    return (
        '<aside class="chapter-judgment">'
        '<strong>Agent 判断</strong>'
        f'<div class="judgment-grid">{judgment_rows}</div>'
        '</aside>'
        '<details class="chapter-detail">'
        '<summary>作者观点、质疑点和来源</summary>'
        '<div class="detail-stack">'
        '<article><h4>作者观点</h4>'
        f'<p>{html_escape(plain_note_text(review.get("author_view")))}</p>'
        f'{render_timestamp(source_url, start)}'
        '</article>'
        '<article><h4>Agent 质疑</h4>'
        f'<p>{html_escape(plain_note_text(review.get("skeptic_view")))}</p>'
        '</article>'
        '<article><h4>来源定位</h4>'
        f'<p>本段时间戳仅用于核对来源，不作为完成学习的必需步骤：{render_timestamp(source_url, start)}</p>'
        '</article>'
        '</div>'
        '</details>'
    )


def render_report_html(
    *,
    title: str,
    source_url: str,
    metadata: dict[str, Any],
    summary: dict[str, Any],
    debate: dict[str, Any],
    frame_plan: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
    image_prompts: list[dict[str, Any]],
    generated_images: list[dict[str, Any]],
    run_review: dict[str, Any],
    lesson_units: list[dict[str, Any]],
    assessment: dict[str, Any],
    visual_storyboard: list[dict[str, Any]],
    asset_health: dict[str, Any],
    replacement_review: dict[str, Any],
    transcript: list[dict[str, Any]],
) -> str:
    chapters = summary.get("chapters") or []
    review_questions = summary.get("review_questions") or []
    duration = report_duration(metadata, summary, transcript)
    transcript_count = run_review.get("transcript_segments") or len(transcript)
    confidence = debate.get("judge", {}).get("overall_confidence")
    replacement_score = replacement_review.get("replacement_score", 0)
    replacement_ready = bool(replacement_review.get("replacement_ready"))
    frames_by_chapter = group_frames_by_chapter(selected_frames, chapters)
    chapter_reviews = normalize_chapter_reviews(debate, chapters)
    reviews_by_index = {int(item.get("chapter_index", 0)): item for item in chapter_reviews}
    core_indexed_chapters, edge_indexed_chapters = split_core_chapters(chapters)
    core_chapters = chapters_only(core_indexed_chapters)
    core_indices = {index for index, _ in core_indexed_chapters}
    source_link = (
        f'<a class="button primary" href="{html_escape(source_url)}" target="_blank" rel="noreferrer">查看来源</a>'
        if source_url and is_url(source_url)
        else f'<span class="source-path">{html_escape(source_url or "本地来源")}</span>'
    )

    def stat(label: str, value: Any, hint: str) -> str:
        return (
            '<div class="meta-pill">'
            f'<span>{html_escape(label)}</span>'
            f'<strong>{html_escape(value)}</strong>'
            '</div>'
        )

    tldr_items = [
        plain_note_text(item)
        for item in summary.get("tldr", [])
        if plain_note_text(item) and not is_process_note(item)
    ]
    if len(tldr_items) < 3:
        for chapter in core_chapters or chapters:
            candidate = first_sentences(chapter.get("summary"), 1)
            if candidate and not is_process_note(candidate) and candidate not in tldr_items:
                tldr_items.append(candidate)
            if len(tldr_items) >= 4:
                break
    plain_core_summary = build_plain_core_summary(core_chapters or chapters, debate)
    if plain_core_summary:
        tldr_items = plain_core_summary
    lead_summary = tldr_items[0] if tldr_items else first_sentences(chapters[0].get("summary"), 2) if chapters else "这份笔记会先给出主线，再按章节回到证据、截图和判断。"
    hero_takeaways = "\n".join(f'<li>{html_escape(item)}</li>' for item in tldr_items[:3]) or '<li>先建立视频主线，再进入章节复习。</li>'
    tldr_html = "\n".join(
        f'<li>{html_escape(item)}</li>'
        for item in tldr_items
    ) or '<li>这次运行没有生成 TLDR，请查看分章节笔记。</li>'
    quick_lesson_links = []
    for index, ch in core_indexed_chapters[:4]:
        quick_lesson_links.append(
            f'<li><a href="#chapter-{index}">{html_escape(chapter_display_title(index, ch))}</a></li>'
        )
    quickstart_html = (
        '<div class="quick-grid">'
        '<article><span>01</span><h3>一句话</h3>'
        f'<p>{html_escape(lead_summary)}</p></article>'
        '<article><span>02</span><h3>先懂概念</h3>'
        f'<p>{html_escape(" / ".join((entry.get("zh_name") or entry["term"]) for entry in build_glossary_entries(core_chapters or chapters)[:4]) or "先看概念翻译。")}</p></article>'
        '<article><span>03</span><h3>只读核心课</h3>'
        f'<ol>{"".join(quick_lesson_links)}</ol></article>'
        '<article><span>04</span><h3>最后自测</h3>'
        '<p>完成底部测验，达到 80% 以上再认为完成第一轮学习。</p></article>'
        '</div>'
    )
    meta_html = "\n".join([
        stat("时长", duration, "视频总长度"),
        stat("核心章节", len(core_chapters), "学习路线节点"),
        stat("关键帧", len(selected_frames), "已按章节归位"),
        stat("置信度", confidence if confidence is not None else "待评估", "Agent 综合判断"),
        stat("替代分", f"{replacement_score}/100", "85 分以上才标记完整替代"),
    ])

    route_parts: list[str] = []
    for route_index, (phase, items) in enumerate(chunked_indexed_route_groups(core_indexed_chapters), start=1):
        links = []
        for chapter_index, ch in items:
            start = float(ch.get("start", 0))
            title_text = first_sentence(ch.get("title")) or f"第 {chapter_index} 节"
            links.append(
                '<li>'
                f'<a href="#chapter-{chapter_index}"><time>{html_escape(seconds_to_hhmmss(start))}</time><span>{html_escape(title_text)}</span></a>'
                '</li>'
            )
        route_parts.append(
            '<article class="route-phase">'
            f'<span class="route-number">{route_index:02d}</span>'
            f'<h3>{html_escape(phase)}</h3>'
            f'<ol>{"".join(links)}</ol>'
            '</article>'
        )
    chapter_preview_html = "\n".join(route_parts) or '<p class="empty">还没有学习路线。</p>'

    focused_summary = dict(summary)
    focused_summary["chapters"] = core_chapters
    concept_cards = build_core_cards(focused_summary, debate)
    concept_cards_html = "\n".join(
        '<article class="concept-card">'
        f'<span>{html_escape(card["tag"])}</span>'
        f'<h3>{html_escape(card["title"])}</h3>'
        f'<p>{html_escape(card["body"])}</p>'
        '</article>'
        for card in concept_cards
    ) or '<p class="empty">还没有抽取核心知识卡。</p>'
    glossary_entries = build_glossary_entries(core_chapters or chapters)
    concept_course_by_term = {
        item["term"]: item
        for item in build_concept_course_cards(glossary_entries)
    }
    concept_image_by_term = {
        str(item.get("concept_term") or item.get("term") or ""): item
        for item in generated_images
        if item.get("role") == "concept" and (item.get("concept_term") or item.get("term"))
    }
    glossary_html = "\n".join(
        '<article class="glossary-card">'
        + (
            f'<figure><img src="{html_escape(concept_image_by_term[item["term"]].get("path"))}" alt="{html_escape(item["term"])} 概念图" loading="lazy"></figure>'
            if item["term"] in concept_image_by_term and concept_image_by_term[item["term"]].get("path")
            else ""
        )
        + '<h3 class="glossary-title">'
        + f'<span class="term-cn">{html_escape(item.get("zh_name") or item["term"])}</span>'
        + (
            f'<span class="term-en">{html_escape(item["term"])}</span>'
            if (item.get("zh_name") or item["term"]) != item["term"]
            else ""
        )
        + '</h3>'
        + f'<p>{html_escape(item["plain"])}</p>'
        + f'<small>{html_escape(item["why"])}</small>'
        + (
            '<details class="concept-course">'
            '<summary>展开课程卡</summary>'
            '<dl>'
            f'<dt>视频里怎么用</dt><dd>{html_escape(concept_course_by_term[item["term"]]["video_example"])}</dd>'
            f'<dt>如何判断</dt><dd>{html_escape(concept_course_by_term[item["term"]]["judging_rule"])}</dd>'
            f'<dt>常见误用</dt><dd>{html_escape(concept_course_by_term[item["term"]]["common_misuse"])}</dd>'
            '<dt>小测验</dt>'
            '<dd class="concept-quiz">'
            f'<p>{html_escape(concept_course_by_term[item["term"]]["exercise"])}</p>'
            '<details class="concept-answer">'
            '<summary>查看参考答案</summary>'
            f'<p>{html_escape(concept_course_by_term[item["term"]]["answer"])}</p>'
            '</details>'
            '</dd>'
            '</dl>'
            '</details>'
            if item["term"] in concept_course_by_term
            else ""
        )
        + '</article>'
        for item in glossary_entries
    ) or '<p class="empty">这支视频没有明显需要单独翻译的术语。</p>'

    chapter_html_parts: list[str] = []
    for index, ch in core_indexed_chapters:
        start = float(ch.get("start", 0))
        end = float(ch.get("end", start))
        key_points = ch.get("key_points") or []
        key_points = [kp for kp in key_points if not is_process_note(kp.get("text"))]
        chapter_frames = frames_by_chapter.get(index, [])
        review = reviews_by_index.get(index, {})
        bullet_items = chapter_bullets(ch, limit=3)
        bullet_html = "\n".join(
            '<li>'
            f'<p>{html_escape(item["text"])}</p>'
            f'{render_timestamp(source_url, float(item.get("evidence_timestamps", [start])[0])) if item.get("evidence_timestamps") else ""}'
            '</li>'
            for item in bullet_items
        )
        key_html = "\n".join(
            '<li>'
            f'<span class="badge {label_class(kp.get("label"))}">{html_escape(item_label(kp.get("label")))}</span>'
            f'<p>{html_escape(plain_note_text(kp.get("text")))}</p>'
            f'{render_timestamp(source_url, float(kp.get("evidence_timestamps", [start])[0])) if kp.get("evidence_timestamps") else ""}'
            '</li>'
            for kp in key_points
        )
        chapter_frame_html = (
            '<div class="chapter-frame-strip">'
            + "\n".join(render_frame_figure(frame, source_url, compact=True) for frame in chapter_frames)
            + '</div>'
            if chapter_frames
            else '<p class="empty inline-empty">本章没有独立关键帧；可用文字课程完成学习，时间戳仅用于来源核对。</p>'
        )
        chapter_html_parts.append(
            f'<article class="chapter-card reveal" id="chapter-{index}">'
            '<div class="chapter-head">'
            f'<time>{html_escape(render_short_time_range(start, end))}</time>'
            f'<span>章节 {index}</span>'
            '</div>'
            f'<h3>{html_block_text(ch.get("title", f"章节 {index}"))}</h3>'
            f'<p class="chapter-main">{html_escape(first_sentences(ch.get("summary"), 2))}</p>'
            f'<ul class="chapter-bullets">{bullet_html}</ul>'
            '<div class="chapter-linked-block frame-block">'
            '<h4>本章关键帧</h4>'
            f'{chapter_frame_html}'
            '</div>'
            f'{render_chapter_review(ch, review, source_url) if review else ""}'
            '<details>'
            '<summary>完整摘要和证据时间</summary>'
            f'<p class="full-summary">{html_escape(plain_note_text(ch.get("summary")))}</p>'
            f'<ul class="key-list">{key_html}</ul>'
            '</details>'
            '</article>'
        )
    chapters_html = "\n".join(chapter_html_parts) or '<p class="empty">还没有章节摘要。</p>'

    frames_by_chapter_parts: list[str] = []
    for index, ch in core_indexed_chapters:
        chapter_frames = frames_by_chapter.get(index, [])
        if not chapter_frames:
            continue
        frame_links = []
        for frame in chapter_frames:
            ts = float(frame.get("timestamp", frame.get("requested_timestamp", 0)))
            frame_links.append(
                '<li>'
                f'{render_timestamp(source_url, ts)}'
                f'<span>{html_escape(plain_note_text(frame.get("topic") or frame.get("caption") or "关键画面"))}</span>'
                f'<a href="{html_escape(frame.get("selected_frame") or frame.get("path") or "")}" target="_blank" rel="noreferrer">打开图片</a>'
                '</li>'
            )
        frames_by_chapter_parts.append(
            '<article class="frame-index-group">'
            f'<a href="#chapter-{index}">第 {index} 节</a>'
            f'<h3>{html_escape(first_sentence(ch.get("title")) or f"章节 {index}")}</h3>'
            f'<ul>{"".join(frame_links)}</ul>'
            '</article>'
        )
    frames_html = "\n".join(frames_by_chapter_parts) or '<div class="empty panel">还没有选定关键截图；当前页面会降低视觉替代评分，并把时间戳作为来源核对入口。</div>'

    evidence_parts: list[str] = []
    for item in frame_plan:
        ts = float(item.get("timestamp", 0))
        if core_indices and chapter_index_for_timestamp(chapters, ts) not in core_indices:
            continue
        status = "核心来源" if item.get("need_frame") else "来源定位"
        link = item.get("timestamp_link") or timestamp_link(source_url, ts)
        reason = plain_note_text(item.get("reason"))
        if not reason or is_process_note(reason):
            reason = "这一处包含图表或示例，用于核对来源画面。"
        evidence_parts.append(
            '<article class="evidence-row">'
            f'<div>{render_timestamp(source_url, ts)}<span>{html_escape(status)}</span></div>'
            f'<p><strong>{html_block_text(item.get("topic"))}</strong></p>'
            f'<p>{html_escape(reason)}</p>'
            f'<a href="{html_escape(link)}" target="_blank" rel="noreferrer">核对来源</a>'
            '</article>'
        )
    evidence_html = "\n".join(evidence_parts) or '<p class="empty">没有单独的关键时间戳计划。</p>'

    def chapter_review_rows() -> str:
        rows = []
        for review in chapter_reviews:
            index = int(review.get("chapter_index", 0))
            if core_indices and index not in core_indices:
                continue
            start = float(review.get("start", 0))
            rows.append(
                '<article class="comparison-row">'
                f'<header><a href="#chapter-{index}">第 {index} 节</a>{render_timestamp(source_url, start)}</header>'
                '<div>'
                f'<p><strong>作者观点</strong>{html_escape(first_sentence(review.get("author_view")))}</p>'
                f'<p><strong>Agent 质疑</strong>{html_escape(first_sentence(review.get("skeptic_view")))}</p>'
                f'<p><strong>综合判断</strong>{html_escape(first_sentence(review.get("judge_view")))}</p>'
                '</div>'
                '</article>'
            )
        return "\n".join(rows) or '<p class="empty">暂无观点对照。</p>'

    controversies = build_global_controversies(summary, debate)
    controversy_html = "\n".join(
        '<article class="controversy-card">'
        f'<h3>{html_escape(item["title"])}</h3>'
        f'<p><strong>作者倾向</strong>{html_escape(item["author_view"])}</p>'
        f'<p><strong>反方质疑</strong>{html_escape(item["counter_view"])}</p>'
        f'<p><strong>综合判断</strong>{html_escape(item["judgment"])}</p>'
        '</article>'
        for item in controversies
    ) or '<p class="empty">暂无全片争议点。</p>'
    debate_html = (
        '<div class="controversy-list">'
        f'{controversy_html}'
        '</div>'
        '<h3 class="section-subtitle">章节观点对照</h3>'
        f'<div class="comparison-list">{chapter_review_rows()}</div>'
    )

    generated_parts = []
    for img in generated_images:
        if img.get("role") == "concept":
            continue
        path = img.get("path") or ""
        generated_parts.append(
            '<figure class="generated-image">'
            f'<img src="{html_escape(path)}" alt="{html_escape(img.get("title") or "原创总结图")}" loading="lazy">'
            f'<figcaption>{html_block_text(img.get("title") or img.get("id") or "原创总结图")}</figcaption>'
            '</figure>'
        )
    image_section_html = "\n".join(generated_parts) or '<p class="empty">本次没有生成手绘学习图。</p>'

    quiz_items = assessment.get("quiz") or []
    review_html = "\n".join(
        '<article class="quiz-card" data-quiz-card>'
        f'<h3>{index + 1}. {html_escape(item.get("question") or "复习题")}</h3>'
        '<div class="quiz-options">'
        + "".join(
            '<label>'
            f'<input type="radio" name="quiz-{index}" value="{option_index}" data-quiz="{index}" data-answer="{int(item.get("answer_index", 0))}">'
            f'<span>{html_escape(option)}</span>'
            '</label>'
            for option_index, option in enumerate(item.get("options") or [])
        )
        + '</div>'
        + '<details class="answer-detail">'
        + '<summary>查看答案和解析</summary>'
        + f'<p><strong>答案：</strong>{html_escape((item.get("options") or [""])[int(item.get("answer_index", 0))] if item.get("options") else "")}</p>'
        + f'<p>{html_escape(item.get("explanation") or "")}</p>'
        + f'<small>对应：{html_escape(item.get("lesson_ref") or "全片")}</small>'
        + '</details>'
        + '</article>'
        for index, item in enumerate(quiz_items)
    ) or "\n".join(
        '<label class="check-row">'
        f'<input type="checkbox" data-check="{index}">'
        f'<span>{html_block_text(question)}</span>'
        '</label>'
        for index, question in enumerate(review_questions)
    ) or '<p class="empty">还没有复习问题。</p>'
    quiz_score_html = (
        '<div class="quiz-score" data-quiz-score>完成测验后显示掌握度。</div>'
        if quiz_items
        else ""
    )

    toc_items = [
        ("quickstart", "速学"),
        ("concepts", "概念"),
        ("overview", "总览"),
        ("route", "路线"),
        ("chapters", "章节"),
        ("debate", "观点"),
        ("visuals", "观点图"),
        ("evidence", "来源"),
        ("practice", "复习"),
    ]
    toc_html = "\n".join(f'<a href="#{anchor}">{label}</a>' for anchor, label in toc_items)

    css = """
:root {
  color-scheme: light dark;
  --bg: #f6f8f2;
  --panel: #fffdf6;
  --panel-2: #edf3ed;
  --ink: #172121;
  --muted: #5a6663;
  --line: #d8e0d7;
  --accent: #c94f32;
  --accent-strong: #9f3923;
  --accent-soft: #ffe2d8;
  --shadow: 0 20px 60px rgb(23 33 33 / 0.08);
  --radius: 8px;
}

[data-theme="dark"] {
  --bg: #141817;
  --panel: #1d2422;
  --panel-2: #26312e;
  --ink: #f3f7f2;
  --muted: #b3c0ba;
  --line: #384641;
  --accent: #e07859;
  --accent-strong: #ff9a7c;
  --accent-soft: #3c2721;
  --shadow: 0 20px 60px rgb(0 0 0 / 0.28);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141817;
    --panel: #1d2422;
    --panel-2: #26312e;
    --ink: #f3f7f2;
    --muted: #b3c0ba;
    --line: #384641;
    --accent: #e07859;
    --accent-strong: #ff9a7c;
    --accent-soft: #3c2721;
    --shadow: 0 20px 60px rgb(0 0 0 / 0.28);
  }
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  letter-spacing: 0;
}
a { color: inherit; }
img { display: block; max-width: 100%; }
button, textarea, input { font: inherit; }
.progress {
  position: fixed;
  inset: 0 0 auto 0;
  height: 4px;
  z-index: 20;
  transform-origin: left center;
  transform: scaleX(0);
  background: var(--accent);
}
@supports (animation-timeline: scroll()) {
  .progress {
    animation: reading-progress linear both;
    animation-timeline: scroll(root);
  }
  @keyframes reading-progress {
    from { transform: scaleX(0); }
    to { transform: scaleX(1); }
  }
}
.topbar {
  position: sticky;
  top: 4px;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
  padding: 12px clamp(18px, 4vw, 48px);
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  backdrop-filter: blur(18px);
}
.brand { display: grid; gap: 2px; min-width: 0; }
.brand strong { font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: min(62vw, 780px); }
.brand span { color: var(--muted); font-size: 12px; }
.top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: nowrap; }
.button, .top-actions button {
  min-height: 40px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 9px 13px;
  background: var(--panel);
  color: var(--ink);
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}
.button.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}
.button:hover, .top-actions button:hover { border-color: var(--accent); }
.button:active, .top-actions button:active { transform: translateY(1px); }
.layout {
  display: grid;
  grid-template-columns: minmax(150px, 210px) minmax(0, 1fr);
  gap: clamp(18px, 4vw, 48px);
  width: min(1480px, 100%);
  margin: 0 auto;
  padding: clamp(18px, 4vw, 48px);
}
.toc {
  position: sticky;
  top: 88px;
  align-self: start;
  display: grid;
  gap: 8px;
}
.toc a {
  display: block;
  border-left: 2px solid transparent;
  padding: 9px 10px;
  color: var(--muted);
  text-decoration: none;
  border-radius: 0 var(--radius) var(--radius) 0;
}
.toc a:hover { color: var(--ink); background: var(--panel-2); border-color: var(--accent); }
main { min-width: 0; }
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: clamp(22px, 4vw, 56px);
  align-items: end;
  min-height: min(78dvh, 760px);
  padding: clamp(32px, 8vw, 96px) 0 clamp(28px, 6vw, 64px);
}
.kicker {
  margin: 0 0 16px;
  color: var(--accent-strong);
  font-weight: 700;
}
h1 {
  margin: 0;
  max-width: 980px;
  font-size: clamp(38px, 6vw, 76px);
  line-height: 0.98;
  letter-spacing: 0;
}
.hero-copy > p:not(.kicker) {
  max-width: 62ch;
  color: var(--muted);
  font-size: clamp(17px, 2vw, 20px);
  line-height: 1.8;
}
.hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 26px; }
.hero-panel {
  display: grid;
  gap: 12px;
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow);
  border-radius: var(--radius);
  padding: 18px;
}
.metric {
  border-bottom: 1px solid var(--line);
  padding: 4px 0 12px;
}
.metric:last-child { border-bottom: 0; padding-bottom: 4px; }
.metric span, .metric small { display: block; color: var(--muted); font-size: 13px; }
.metric strong { display: block; margin: 4px 0; font-size: clamp(24px, 3vw, 34px); line-height: 1; }
.section {
  scroll-margin-top: 96px;
  padding: clamp(42px, 8vw, 92px) 0;
  border-top: 1px solid var(--line);
}
.section h2 {
  margin: 0 0 18px;
  font-size: clamp(28px, 4vw, 46px);
  letter-spacing: 0;
}
.section > p {
  max-width: 70ch;
  color: var(--muted);
  line-height: 1.8;
}
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 0.45fr);
  gap: 18px;
}
.overview-followup {
  margin-top: 18px;
}
.overview-followup h3 {
  margin: 0 0 12px;
  font-size: 20px;
}
.note-stack, .source-card, .panel {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}
.note-row {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 14px;
  padding: 16px;
  border-bottom: 1px solid var(--line);
}
.note-row:last-child { border-bottom: 0; }
.note-row p, .chapter-card p, .frame-card p, .chapter-frame p, .evidence-row p, .tab-panel p, .controversy-card p, .judgment-grid p {
  margin: 0;
  line-height: 1.78;
  color: var(--ink);
}
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: max-content;
  min-width: 54px;
  height: 28px;
  border-radius: var(--radius);
  padding: 0 9px;
  color: var(--ink);
  background: var(--panel-2);
  border: 1px solid var(--line);
  font-size: 12px;
  white-space: nowrap;
}
.badge.fact { background: #dff1e6; color: #143a2b; }
.badge.author { background: #e4ecff; color: #1f3e6d; }
.badge.inference { background: #fff0cf; color: #614415; }
.badge.counter { background: #ffe1da; color: #6b2e21; }
.badge.judgment { background: #e8e3ff; color: #382b72; }
.badge.todo { background: var(--accent-soft); color: var(--accent-strong); }
.source-card {
  padding: 18px;
  display: grid;
  gap: 16px;
  align-content: start;
}
.source-card code, .source-path {
  display: block;
  overflow-wrap: anywhere;
  color: var(--muted);
  line-height: 1.6;
}
.chapter-preview-list {
  display: grid;
  gap: 10px;
}
.chapter-preview {
  display: grid;
  grid-template-columns: 132px 72px minmax(0, 1fr) 118px;
  gap: 12px;
  align-items: start;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  color: var(--ink);
  text-decoration: none;
}
.chapter-preview:hover { border-color: var(--accent); }
.chapter-preview time, .chapter-preview small {
  color: var(--muted);
  font-size: 13px;
}
.chapter-preview span {
  line-height: 1.55;
}
.chapter-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
.chapter-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 18px;
  box-shadow: var(--shadow);
}
.chapter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}
.chapter-card h3 {
  margin: 14px 0 10px;
  font-size: clamp(21px, 2.4vw, 30px);
  line-height: 1.45;
}
.chapter-linked-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.chapter-linked-block h4 {
  margin: 0 0 10px;
  font-size: 15px;
}
.chapter-frame-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.chapter-frame {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-2);
  overflow: hidden;
}
.chapter-frame img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--panel-2);
}
.chapter-frame figcaption {
  display: grid;
  gap: 7px;
  padding: 12px;
}
.chapter-frame figcaption strong { font-size: 15px; }
.chapter-frame small { color: var(--muted); }
.inline-empty {
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  padding: 12px;
}
details {
  margin-top: 14px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
summary {
  cursor: pointer;
  color: var(--accent-strong);
  font-weight: 700;
}
.key-list, .judge-grid ul {
  display: grid;
  gap: 10px;
  list-style: none;
  padding: 12px 0 0;
  margin: 0;
}
.key-list li {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
}
.time-link {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius);
  padding: 5px 8px;
  background: var(--panel-2);
  color: var(--accent-strong);
  text-decoration: none;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.frame-gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.frame-chapter-group {
  display: grid;
  gap: 12px;
  margin-bottom: 28px;
}
.frame-chapter-group > a {
  color: var(--accent-strong);
  font-weight: 800;
  text-decoration: none;
}
.frame-chapter-group h3 {
  margin: 0;
  font-size: 21px;
}
.frame-card {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  overflow: hidden;
  box-shadow: var(--shadow);
}
.frame-card img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: var(--panel-2);
}
.frame-card figcaption {
  display: grid;
  gap: 8px;
  padding: 14px;
}
.frame-card figcaption strong { font-size: 16px; }
.frame-card small { color: var(--muted); }
.evidence-list {
  display: grid;
  gap: 12px;
}
.evidence-row {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr) minmax(0, 1.2fr) auto;
  gap: 14px;
  align-items: start;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 14px;
}
.evidence-row div { display: grid; gap: 7px; color: var(--muted); }
.evidence-row a { color: var(--accent-strong); white-space: nowrap; }
.judge-grid li {
  display: grid;
  gap: 8px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}
.judge-grid li:last-child { border-bottom: 0; }
.review-row {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  border-bottom: 1px solid var(--line);
  padding: 13px 0;
}
.review-row:first-child { padding-top: 0; }
.review-row:last-child { border-bottom: 0; padding-bottom: 0; }
.review-row > a {
  color: var(--accent-strong);
  font-weight: 800;
  text-decoration: none;
}
.judge-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.judge-grid h3 { margin: 0 0 8px; }
.visual-tools {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.prompt-box, .generated-image {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 14px;
  margin: 0;
}
.prompt-box pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.7;
  color: var(--muted);
}
.generated-image img {
  width: 100%;
  aspect-ratio: 3 / 2;
  object-fit: contain;
  background: var(--panel-2);
  border-radius: var(--radius);
}
.generated-image figcaption {
  margin-top: 10px;
  font-weight: 800;
}
.practice-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 18px;
}
.checklist, .scratchpad {
  display: grid;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 16px;
}
.check-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  line-height: 1.65;
  color: var(--ink);
}
.check-row input { margin-top: 5px; accent-color: var(--accent); }
.quiz-score {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 10px 12px;
  color: var(--accent-strong);
  font-weight: 800;
}
.quiz-card {
  border-bottom: 1px solid var(--line);
  padding-bottom: 14px;
}
.quiz-card:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}
.quiz-card h3 {
  margin: 0 0 10px;
  font-size: 17px;
  line-height: 1.5;
}
.quiz-options {
  display: grid;
  gap: 8px;
}
.quiz-options label {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg);
  padding: 9px;
  line-height: 1.55;
}
.quiz-options input {
  margin-top: 4px;
  accent-color: var(--accent);
}
.answer-detail {
  margin-top: 10px;
}
.answer-detail small {
  color: var(--muted);
}
textarea {
  min-height: 260px;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--ink);
  padding: 14px;
  line-height: 1.7;
}
.scratch-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.empty {
  color: var(--muted);
  line-height: 1.7;
}
.footer {
  color: var(--muted);
  padding: 40px 0 10px;
}
.layout {
  grid-template-columns: minmax(140px, 180px) minmax(0, 920px);
  width: min(1180px, calc(100% - 32px));
  justify-content: center;
  padding: 32px 0 48px;
}
main {
  width: min(920px, 100%);
}
.hero {
  display: block;
  min-height: auto;
  padding: 48px 0 36px;
}
h1 {
  max-width: 880px;
  font-size: clamp(30px, 4vw, 48px);
  line-height: 1.18;
}
.hero-copy > p:not(.kicker) {
  max-width: 78ch;
  font-size: 18px;
  line-height: 1.82;
}
.hero-takeaways {
  display: grid;
  gap: 8px;
  max-width: 78ch;
  margin: 20px 0 0;
  padding: 0;
  list-style: none;
}
.hero-takeaways li {
  border-left: 3px solid var(--accent);
  padding: 7px 0 7px 12px;
  line-height: 1.7;
}
.meta-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}
.meta-pill {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 12px;
}
.meta-pill span, .meta-pill small {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.meta-pill strong {
  display: block;
  margin: 4px 0;
  font-size: 20px;
  line-height: 1.2;
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.quick-grid article {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 16px;
}
.quick-grid span {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-weight: 800;
  font-size: 12px;
}
.quick-grid h3 {
  margin: 12px 0 8px;
  font-size: 18px;
}
.quick-grid p {
  margin: 0;
  line-height: 1.72;
}
.quick-grid ol {
  display: grid;
  gap: 7px;
  margin: 0;
  padding-left: 18px;
  line-height: 1.6;
}
.section {
  padding: 56px 0;
}
.section h2 {
  font-size: clamp(26px, 3vw, 36px);
}
.tldr-list {
  display: grid;
  gap: 12px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}
.tldr-list li {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 16px 18px;
  line-height: 1.82;
}
.route-grid, .concept-grid, .glossary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.route-phase, .concept-card, .glossary-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 18px;
}
.route-number, .concept-card span {
  color: var(--accent-strong);
  font-weight: 800;
  font-size: 12px;
}
.route-phase h3, .concept-card h3, .glossary-card h3 {
  margin: 8px 0 12px;
  font-size: 19px;
}
.glossary-title {
  display: grid;
  gap: 4px;
}
.term-cn {
  font-size: 21px;
  line-height: 1.25;
}
.term-en {
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.route-phase ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 18px;
}
.route-phase a {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  color: var(--ink);
  text-decoration: none;
  line-height: 1.55;
}
.route-phase time {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.concept-card p, .glossary-card p {
  margin: 0;
  line-height: 1.78;
}
.glossary-card figure {
  margin: 0 0 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-2);
  overflow: hidden;
}
.glossary-card img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
}
.glossary-card small {
  display: block;
  margin-top: 10px;
  color: var(--muted);
  line-height: 1.65;
}
.concept-course dl {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
}
.concept-course dt {
  color: var(--muted);
  font-weight: 800;
  font-size: 13px;
}
.concept-course dd {
  margin: 0;
  line-height: 1.68;
}
.concept-quiz {
  display: grid;
  gap: 8px;
}
.concept-quiz p {
  margin: 0;
}
.concept-answer {
  margin-top: 0;
  border-top: 0;
  padding-top: 0;
}
.concept-answer summary {
  display: inline-flex;
  width: fit-content;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--bg);
  padding: 7px 10px;
  font-size: 13px;
}
.concept-answer p {
  margin-top: 8px !important;
}
.section-subtitle {
  margin-top: 28px !important;
  font-size: 22px !important;
}
.chapter-card {
  box-shadow: none;
  padding: 24px;
}
.chapter-main {
  border-left: 3px solid var(--accent);
  padding-left: 14px;
  font-size: 17px;
}
.chapter-bullets {
  display: grid;
  gap: 10px;
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
}
.chapter-bullets li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  border-top: 1px solid var(--line);
  padding-top: 10px;
}
.chapter-judgment {
  margin-top: 18px;
  border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--accent-soft) 48%, var(--panel));
  padding: 16px;
}
.chapter-judgment strong {
  display: block;
  margin-bottom: 8px;
}
.judgment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.judgment-grid article {
  border: 1px solid color-mix(in srgb, var(--accent) 24%, var(--line));
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--panel) 78%, white);
  padding: 12px;
}
.judgment-grid h4 {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 13px;
}
.detail-stack {
  display: grid;
  gap: 12px;
  padding-top: 12px;
}
.detail-stack article {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel-2);
  padding: 13px;
}
.full-summary {
  margin-top: 12px !important;
}
.chapter-frame img {
  object-fit: contain;
}
.comparison-list {
  display: grid;
  gap: 12px;
}
.controversy-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.controversy-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 16px;
}
.controversy-card h3 {
  margin: 0 0 12px;
  font-size: 18px;
  line-height: 1.45;
}
.controversy-card p {
  display: grid;
  gap: 4px;
  margin-top: 10px;
}
.controversy-card strong {
  color: var(--muted);
  font-size: 13px;
}
.comparison-row {
  display: grid;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 16px;
}
.comparison-row header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.comparison-row header a {
  color: var(--accent-strong);
  font-weight: 800;
  text-decoration: none;
}
.comparison-row div {
  display: grid;
  gap: 10px;
}
.comparison-row p strong {
  display: block;
  margin-bottom: 4px;
  color: var(--muted);
}
.frame-index-group {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 14px;
  margin-top: 12px;
}
.frame-index-group > a {
  color: var(--accent-strong);
  font-weight: 800;
  text-decoration: none;
}
.frame-index-group h3 {
  margin: 8px 0 12px;
  font-size: 17px;
}
.frame-index-group ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.frame-index-group li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}
.frame-index-group li > a {
  color: var(--accent-strong);
  white-space: nowrap;
}
.visual-tools {
  grid-template-columns: 1fr;
}
.generated-image {
  box-shadow: none;
}
.generated-image img {
  aspect-ratio: 16 / 9;
}
.skim-details {
  margin-top: 18px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 14px 16px;
}
.skim-details ul {
  display: grid;
  gap: 10px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.skim-details li {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.skim-details a {
  color: var(--accent-strong);
  font-variant-numeric: tabular-nums;
}
@media (prefers-reduced-motion: no-preference) {
  .reveal {
    animation: lift-in 520ms cubic-bezier(.16, 1, .3, 1) both;
  }
  @keyframes lift-in {
    from { opacity: 0; transform: translateY(18px); }
    to { opacity: 1; transform: translateY(0); }
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
    animation: none !important;
    transition: none !important;
  }
}
@media (max-width: 1020px) {
  .layout { grid-template-columns: 1fr; }
  .toc {
    position: static;
    display: flex;
    overflow-x: auto;
    padding-bottom: 6px;
  }
  .toc a { white-space: nowrap; border-left: 0; border-bottom: 2px solid transparent; border-radius: var(--radius); }
  .hero, .overview-grid, .practice-grid, .meta-strip, .quick-grid, .route-grid, .concept-grid, .glossary-grid, .judgment-grid, .controversy-list { grid-template-columns: 1fr; min-height: auto; }
  .chapter-list, .frame-gallery, .judge-grid, .visual-tools { grid-template-columns: 1fr; }
  .evidence-row { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .topbar { align-items: flex-start; flex-direction: column; }
  .top-actions { width: 100%; overflow-x: auto; padding-bottom: 2px; }
  .layout { padding: 18px; }
  h1 { font-size: 38px; }
  .note-row, .key-list li, .chapter-preview, .review-row, .chapter-bullets li, .frame-index-group li, .skim-details li { grid-template-columns: 1fr; }
  .chapter-preview span { white-space: normal; }
  .comparison-row header { align-items: flex-start; flex-direction: column; }
  .route-phase a { grid-template-columns: 1fr; }
}
"""

    script = """
(function () {
  const root = document.documentElement;
  const pageKey = "youtube-study-note:" + (root.dataset.videoId || location.pathname);

  function readStore() {
    try { return JSON.parse(localStorage.getItem(pageKey) || "{}"); }
    catch (_) { return {}; }
  }
  function writeStore(next) {
    try { localStorage.setItem(pageKey, JSON.stringify(next)); }
    catch (_) {}
  }
  const store = readStore();

  const savedTheme = store.theme;
  if (savedTheme) root.dataset.theme = savedTheme;
  document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    store.theme = next;
    writeStore(store);
  });

  document.querySelectorAll("[data-check]").forEach((box) => {
    const key = "check:" + box.getAttribute("data-check");
    box.checked = Boolean(store[key]);
    box.addEventListener("change", () => {
      store[key] = box.checked;
      writeStore(store);
    });
  });

  function updateQuizScore() {
    const scoreEl = document.querySelector("[data-quiz-score]");
    if (!scoreEl) return;
    const groups = {};
    document.querySelectorAll("[data-quiz]").forEach((input) => {
      const id = input.getAttribute("data-quiz");
      if (!groups[id]) {
        groups[id] = {
          answer: input.getAttribute("data-answer"),
          selected: null
        };
      }
      if (input.checked) groups[id].selected = input.value;
    });
    const rows = Object.values(groups);
    const total = rows.length;
    const answered = rows.filter((row) => row.selected !== null).length;
    const correct = rows.filter((row) => row.selected !== null && row.selected === row.answer).length;
    if (!total) {
      scoreEl.textContent = "";
      return;
    }
    const percent = Math.round((correct / total) * 100);
    const state = answered < total ? "未完成" : percent >= 80 ? "完成学习" : "需要补课";
    scoreEl.textContent = "掌握度：" + correct + "/" + total + "（" + percent + "%） " + state;
  }

  document.querySelectorAll("[data-quiz]").forEach((input) => {
    const key = "quiz:" + input.getAttribute("data-quiz");
    if (store[key] === input.value) input.checked = true;
    input.addEventListener("change", () => {
      if (!input.checked) return;
      store[key] = input.value;
      writeStore(store);
      updateQuizScore();
    });
  });
  updateQuizScore();

  const notes = document.querySelector("[data-notes]");
  if (notes) {
    notes.value = store.notes || "";
    notes.addEventListener("input", () => {
      store.notes = notes.value;
      writeStore(store);
    });
  }

  document.querySelector("[data-export-notes]")?.addEventListener("click", () => {
    const checkedItems = Array.from(document.querySelectorAll("[data-check]"))
      .map((box, index) => box.checked ? String(index + 1) : "")
      .filter(Boolean);
    const quizAnswers = Array.from(document.querySelectorAll("[data-quiz-card]"))
      .map((card) => {
        const question = card.querySelector("h3")?.textContent?.trim() || "";
        const checked = card.querySelector("input[data-quiz]:checked");
        const answer = checked?.closest("label")?.textContent?.trim() || "";
        return checked ? question + " -> " + answer : "";
      })
      .filter(Boolean);
    const content = [
      document.title,
      "",
      "我的笔记:",
      notes ? notes.value : "",
      "",
      "测验作答:",
    ].concat(quizAnswers).concat([
      "",
      "已完成复习问题:",
    ]).concat(checkedItems).join("\\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "personal-review-notes.txt";
    link.click();
    URL.revokeObjectURL(link.href);
  });
})();
"""

    html_doc = f"""<!doctype html>
<html lang="zh-CN" data-video-id="{html_escape(metadata.get("id") or title)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_escape(title)} - 视频学习笔记</title>
  <style>{css}</style>
</head>
<body>
  <div class="progress" aria-hidden="true"></div>
  <header class="topbar">
    <div class="brand">
      <strong>{html_escape(title)}</strong>
      <span>视频课程化学习包</span>
    </div>
    <div class="top-actions">
      <button type="button" data-theme-toggle>切换明暗</button>
    </div>
  </header>
  <div class="layout">
    <aside class="toc" aria-label="页面目录">{toc_html}</aside>
    <main>
      <section class="hero" id="top">
        <div class="hero-copy">
          <p class="kicker">{html_escape("完整替代学习包" if replacement_ready else "课程化学习包")}</p>
          <h1>{html_escape(title)}</h1>
          <p>{html_escape(lead_summary)}</p>
          <ul class="hero-takeaways">{hero_takeaways}</ul>
          <div class="hero-actions">
            {source_link}
            <a class="button" href="#quickstart">5 分钟速学</a>
            <a class="button" href="#concepts">先看概念</a>
            <a class="button" href="#practice">开始复习</a>
          </div>
        </div>
      </section>
      <div class="meta-strip" aria-label="视频笔记概况">{meta_html}</div>

      <section class="section" id="quickstart">
        <h2>5 分钟速学</h2>
        <p>先用这一段建立主线。原视频链接只作为来源核对，不是完成第一轮学习的必需步骤。</p>
        {quickstart_html}
      </section>

      <section class="section" id="concepts">
        <h2>概念翻译</h2>
        <div class="glossary-grid">{glossary_html}</div>
        <h2 class="section-subtitle">重点判断</h2>
        <div class="concept-grid">{concept_cards_html}</div>
      </section>

      <section class="section" id="overview">
        <h2>先懂核心</h2>
        <ol class="tldr-list">{tldr_html}</ol>
      </section>

      <section class="section" id="route">
        <h2>学习路线</h2>
        <div class="route-grid">{chapter_preview_html}</div>
      </section>

      <section class="section" id="chapters">
        <h2>核心章节</h2>
        <div class="chapter-list">{chapters_html}</div>
      </section>

      <section class="section" id="debate">
        <h2>全片争议和观点对照</h2>
        {debate_html}
      </section>

      <section class="section" id="visuals">
        <h2>观点总结图</h2>
        <div class="visual-tools">{image_section_html}</div>
      </section>

      <section class="section" id="evidence">
        <h2>来源证据</h2>
        <p>以下时间戳用于核对来源和图表出处。主学习路径已经在上方完成。</p>
        <div class="evidence-list">{evidence_html}</div>
        <div class="frames-by-chapter">{frames_html}</div>
      </section>

      <section class="section" id="practice">
        <h2>复习和个人笔记</h2>
        {quiz_score_html}
        <div class="practice-grid">
          <div class="checklist">{review_html}</div>
          <div class="scratchpad">
            <label for="personal-notes"><strong>我的补充</strong></label>
            <textarea id="personal-notes" data-notes placeholder="写下你的图表验证、反例、待复盘标的或下一次要问的问题。"></textarea>
            <div class="scratch-actions">
              <button class="button primary" type="button" data-export-notes>导出笔记</button>
            </div>
          </div>
        </div>
      </section>

      <footer class="footer"></footer>
    </main>
  </div>
  <script>{script}</script>
</body>
</html>
"""
    return html_doc


def chapter_display_title(index: int, chapter: dict[str, Any]) -> str:
    title = plain_note_text(chapter.get("title") or f"第 {index} 节")
    return re.sub(r"^第\s*\d+\s*节[：:]\s*", "", title).strip() or f"章节 {index}"


def chapter_dir_name(index: int, chapter: dict[str, Any]) -> str:
    title = chapter_display_title(index, chapter)
    return f"{index:02d}-{slugify(first_sentence(title) or title, f'chapter-{index:02d}')}"


def write_chapter_packages(
    out: Path,
    *,
    source_url: str,
    summary: dict[str, Any],
    debate: dict[str, Any],
    selected_frames: list[dict[str, Any]],
) -> None:
    chapters = summary.get("chapters") or []
    chapters_dir = out / "chapters"
    if chapters_dir.exists():
        shutil.rmtree(chapters_dir)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    core_indexed_chapters, _ = split_core_chapters(chapters)
    reviews = normalize_chapter_reviews(debate, chapters)
    reviews_by_index = {int(item.get("chapter_index", 0)): item for item in reviews}
    frames_by_chapter = group_frames_by_chapter(selected_frames, chapters)
    index_lines = [f"# {summary.get('title') or '视频章节目录'}", ""]

    for index, chapter in core_indexed_chapters:
        start = float(chapter.get("start", 0))
        end = float(chapter.get("end", start))
        title = chapter_display_title(index, chapter)
        folder = chapters_dir / chapter_dir_name(index, chapter)
        frame_folder = folder / "frames"
        folder.mkdir(parents=True, exist_ok=True)
        frame_folder.mkdir(parents=True, exist_ok=True)

        review = reviews_by_index.get(index, {})
        copied_frames: list[dict[str, Any]] = []
        for frame in frames_by_chapter.get(index, []):
            frame_record = dict(frame)
            selected = str(frame.get("selected_frame") or "")
            source_path = out / selected if selected else None
            if source_path and source_path.exists():
                dest = frame_folder / source_path.name
                shutil.copy2(source_path, dest)
                frame_record["chapter_frame"] = str(dest.relative_to(folder))
            copied_frames.append(frame_record)

        write_json(folder / "chapter.json", {
            "chapter_index": index,
            "title": title,
            "start": start,
            "end": end,
            "source_url": timestamp_link(source_url, start) if source_url else "",
            "chapter": chapter,
            "review": review,
            "frames": copied_frames,
        })

        md_lines = [
            f"# 第 {index} 节：{title}",
            "",
            f"- 时间：{render_short_time_range(start, end)}",
        ]
        if source_url:
            md_lines.append(f"- 来源：{timestamp_link(source_url, start)}")
        md_lines += ["", "## 本章摘要", "", plain_note_text(chapter.get("summary")), ""]
        key_points = chapter_bullets(chapter, limit=8)
        if key_points:
            md_lines += ["## 关键点", ""]
            for item in key_points:
                ts = item.get("evidence_timestamps") or [start]
                link = timestamp_link(source_url, float(ts[0])) if source_url and ts else ""
                suffix = f" [{seconds_to_hhmmss(float(ts[0]))}]({link})" if link and ts else ""
                md_lines.append(f"- {plain_note_text(item.get('text'))}{suffix}")
            md_lines.append("")
        if review:
            md_lines += [
                "## 作者观点",
                "",
                plain_note_text(review.get("author_view")),
                "",
                "## Agent 质疑",
                "",
                plain_note_text(review.get("skeptic_view")),
                "",
                "## 综合判断",
                "",
                plain_note_text(review.get("judge_view")),
                "",
            ]
        if copied_frames:
            md_lines += ["## 本章截图", ""]
            for frame in copied_frames:
                path = frame.get("chapter_frame")
                caption = plain_note_text(frame.get("caption") or frame.get("topic") or "关键截图")
                if path:
                    md_lines += [f"![{caption}]({path})", "", caption, ""]
        (folder / "chapter.md").write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")
        index_lines.append(f"- [{render_short_time_range(start, end)} 第 {index} 节：{title}]({folder.name}/chapter.md)")

    (chapters_dir / "index.md").write_text("\n".join(index_lines).strip() + "\n", encoding="utf-8")


def cmd_render(args: argparse.Namespace) -> None:
    out = Path(args.out).expanduser().resolve()
    ensure_note_package_dirs(out)
    metadata = load_optional_json(out / "metadata.json", {})
    transcript = load_optional_json(out / "transcript.json", [])
    summary = load_optional_json(out / "summary.json", {})
    debate = load_optional_json(out / "debate.json", {})
    frame_plan = load_optional_json(out / "frame_plan.json", [])
    selected_frames = load_optional_json(out / "frames" / "selected_frames.json", [])
    image_prompts = load_optional_json(out / "image_prompts.json", [])
    generated_images = load_optional_json(out / "generated_images.json", [])
    run_review = load_optional_json(out / "run_review.json", {})

    title = summary.get("title") or metadata.get("title") or "Video Study Note"
    source_url = metadata.get("webpage_url") or metadata.get("original_url") or metadata.get("local_path") or ""
    core_indexed_chapters, _ = split_core_chapters(summary.get("chapters") or [])
    core_chapters = chapters_only(core_indexed_chapters)
    glossary_entries = build_glossary_entries(core_chapters or summary.get("chapters") or [])
    lesson_units = build_lesson_units(summary, debate, selected_frames)
    assessment = build_assessment(summary, glossary_entries)
    visual_storyboard = build_visual_storyboard(summary, frame_plan, selected_frames)
    asset_health = build_asset_health(out, selected_frames, generated_images)
    controversies = build_global_controversies(summary, debate)
    replacement_review = build_replacement_review(
        summary=summary,
        glossary_entries=glossary_entries,
        lesson_units=lesson_units,
        visual_storyboard=visual_storyboard,
        assessment=assessment,
        asset_health=asset_health,
        controversies=controversies,
    )
    write_json(out / "lesson_units.json", lesson_units)
    write_json(out / "assessment.json", assessment)
    write_json(out / "visual_storyboard.json", visual_storyboard)
    write_json(out / "asset_health.json", asset_health)
    write_json(out / "replacement_review.json", replacement_review)
    write_chapter_packages(out, source_url=source_url, summary=summary, debate=debate, selected_frames=selected_frames)
    lines: list[str] = [f"# 视频学习笔记：{title}", ""]
    if source_url:
        lines += ["## 1. 视频信息", "", f"- Source: {source_url}"]
        if metadata.get("extractor_key"):
            lines.append(f"- Source type: {metadata.get('extractor_key')}")
        lines.append("")
    if metadata.get("duration"):
        lines += [f"- Duration: {seconds_to_hhmmss(float(metadata['duration']))}", ""]

    if summary.get("tldr"):
        lines += ["## 2. TL;DR", ""]
        for item in summary["tldr"]:
            lines.append(f"- {item}")
        lines.append("")

    if summary.get("chapters"):
        lines += ["## 3. 章节摘要", ""]
        for ch in summary["chapters"]:
            start = seconds_to_hhmmss(float(ch.get("start", 0)))
            end = seconds_to_hhmmss(float(ch.get("end", 0)))
            lines += [f"### {start} 至 {end} {ch.get('title','')}", "", ch.get("summary", ""), ""]
        lines += ["## 4. 核心知识点", ""]
        for ch in summary["chapters"]:
            for kp in ch.get("key_points", []):
                label = kp.get("label", "[MODEL_INFERENCE]")
                ts = ", ".join(seconds_to_hhmmss(float(x)) for x in kp.get("evidence_timestamps", []))
                lines.append(f"- {label} {kp.get('text','')}" + (f" `@ {ts}`" if ts else ""))
        lines.append("")

    if frame_plan:
        lines += ["## 5. 关键证据和时间戳", ""]
        for item in frame_plan:
            ts = seconds_to_hhmmss(float(item.get("timestamp", 0)))
            link = item.get("timestamp_link") or timestamp_link(source_url, float(item.get("timestamp", 0)))
            need = "需要关键帧复核" if item.get("need_frame") else "时间戳链接即可"
            lines.append(f"- `{ts}` [{need}] {item.get('topic','')} - {item.get('reason','')} ({link})")
        lines.append("")

    lines += ["## 6. 关键截图", ""]
    if selected_frames:
        for fr in selected_frames:
            path = fr.get("selected_frame") or fr.get("path")
            caption = fr.get("caption") or fr.get("why_selected") or ""
            ts = seconds_to_hhmmss(float(fr.get("timestamp", fr.get("requested_timestamp", 0))))
            source = fr.get("source")
            source_note = f"来源: {source}" if source else ""
            lines += [f"### {ts} {fr.get('topic','')}", "", f"![{caption}]({path})", "", caption]
            if source_note:
                lines.append(source_note)
            lines.append("")
    else:
        lines += ["当前报告还没有选定关键帧。可用来源时间戳核对图表出处，或在授权/私人学习场景下补充 `frames/selected_frames.json` 后重新渲染。", ""]

    if debate:
        if debate.get("author_view"):
            lines += ["## 7. 作者观点", ""]
            for item in debate["author_view"]:
                ts = ", ".join(seconds_to_hhmmss(float(x)) for x in item.get("evidence_timestamps", []))
                lines.append(f"- {LABEL_AUTHOR} {item.get('claim','')}" + (f" `@ {ts}`" if ts else ""))
            lines.append("")
        if debate.get("skeptic_view"):
            lines += ["## 8. 质疑点", ""]
            for item in debate["skeptic_view"]:
                lines.append(f"- {LABEL_COUNTER} {item.get('issue','')} - {item.get('why_it_matters','')}")
            lines.append("")
        if debate.get("counter_view"):
            lines += ["## 9. 反方观点", ""]
            for item in debate["counter_view"]:
                lines.append(f"- {LABEL_COUNTER} {item.get('claim','')} - {item.get('supporting_reason','')}")
            lines.append("")
        judge = debate.get("judge") or {}
        if judge:
            lines += ["## 10. Agent 综合判断", ""]
            for key, heading in [("useful_parts", "可用部分"), ("questionable_parts", "存疑部分"), ("what_to_verify_next", "下一步验证")]:
                if judge.get(key):
                    lines.append(f"**{heading}:**")
                    for item in judge[key]:
                        label = LABEL_TODO if key == "what_to_verify_next" else LABEL_JUDGMENT
                        lines.append(f"- {label} {item}")
                    lines.append("")
            if "overall_confidence" in judge:
                lines.append(f"置信度: {judge['overall_confidence']}")
                lines.append("")

    lines += ["## 11. 手绘学习图", ""]
    if generated_images:
        for img in generated_images:
            lines += [f"### {img.get('title', img.get('id',''))}", "", f"![{img.get('title','generated image')}]({img.get('path')})", ""]
    else:
        lines += ["本次没有生成手绘学习图。", ""]

    if summary.get("review_questions"):
        lines += ["## 12. 复习问题", ""]
        for q in summary["review_questions"]:
            lines.append(f"- {q}")
        lines.append("")

    verify_next = debate.get("judge", {}).get("what_to_verify_next", []) if debate else []
    lines += ["## 13. 待验证事项", ""]
    if verify_next:
        for item in verify_next:
            lines.append(f"- {LABEL_TODO} {item}")
    else:
        lines.append(f"- {LABEL_TODO} 阅读后补充你自己的验证目标。")
    lines.append("")

    lines += ["## 14. 我的个人笔记", "", "- ", ""]
    if run_review:
        lines += ["## 运行复核", "", f"- Transcript 片段数: {run_review.get('transcript_segments', 0)}", f"- 边界合规评分: {run_review.get('scores', {}).get('boundary_compliance', 'n/a')}", ""]

    report_md = "\n".join(lines)
    (out / "report.md").write_text(report_md, encoding="utf-8")
    report_html = render_report_html(
        title=title,
        source_url=source_url,
        metadata=metadata,
        summary=summary,
        debate=debate,
        frame_plan=frame_plan,
        selected_frames=selected_frames,
        image_prompts=image_prompts,
        generated_images=generated_images,
        run_review=run_review,
        lesson_units=lesson_units,
        assessment=assessment,
        visual_storyboard=visual_storyboard,
        asset_health=asset_health,
        replacement_review=replacement_review,
        transcript=transcript,
    )
    (out / "report.html").write_text(report_html, encoding="utf-8")
    (out / "index.html").write_text(report_html, encoding="utf-8")
    print(f"Rendered: {out / 'report.md'}, {out / 'report.html'}, and {out / 'index.html'}")


def cmd_image(args: argparse.Namespace) -> None:
    out = Path(args.out).expanduser().resolve()
    prompts = load_optional_json(Path(args.image_prompts).expanduser().resolve(), []) if args.image_prompts else []
    prompt_by_id = {str(item.get("id")): item for item in prompts if item.get("id")}
    img_dir = out / "generated"
    img_dir.mkdir(parents=True, exist_ok=True)

    existing_images = load_optional_json(out / "generated_images.json", [])
    generated: list[dict[str, Any]] = [item for item in existing_images if isinstance(item, dict)]
    replaced_ids: set[str] = set()
    new_records: list[dict[str, Any]] = []
    for asset in args.asset or []:
        if "=" in asset:
            asset_id, source_value = asset.split("=", 1)
        else:
            raise SystemExit("--asset must use id=/absolute/path.png, for example: --asset sketch_map_01=~/generated_images/example/image.png")
        asset_id = slugify(asset_id, "image")
        source_path = Path(source_value).expanduser().resolve()
        if not source_path.exists():
            raise SystemExit(f"Generated image not found: {source_path}")
        if source_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise SystemExit(f"Unsupported generated image type: {source_path}")

        ext = ".jpg" if source_path.suffix.lower() == ".jpeg" else source_path.suffix.lower()
        dest_path = img_dir / f"{asset_id}{ext}"
        if source_path != dest_path.resolve():
            shutil.copy2(source_path, dest_path)
        prompt_item = prompt_by_id.get(asset_id, {})
        record = {
            "id": asset_id,
            "title": prompt_item.get("title") or asset_id,
            "path": str(dest_path.relative_to(out)),
            "type": "built_in_imagegen_png" if ext == ".png" else "built_in_imagegen",
            "model": "image_gen",
            "source": str(source_path),
        }
        for key in ["role", "concept_term"]:
            if prompt_item.get(key):
                record[key] = prompt_item[key]
        replaced_ids.add(asset_id)
        new_records.append(record)
    generated = [item for item in generated if str(item.get("id")) not in replaced_ids]
    generated.extend(new_records)
    write_json(out / "generated_images.json", generated)
    print(f"Registered {len(new_records)} built-in imagegen image(s).")
    if args.render:
        cmd_render(argparse.Namespace(out=str(out)))


def cmd_remember(args: argparse.Namespace) -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    source = slugify(args.source, "source")
    path = skill_dir / "references" / "video-patterns" / f"{source}.md"
    today = dt.date.today().isoformat()
    entry = f"\n## Observation {today}\n\n- {args.note.strip()}\n"
    if path.exists():
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        path.write_text(f"---\nsource: {args.source}\nupdated: {today}\n---\n{entry}", encoding="utf-8")
    print(f"Updated experience file: {path}")


def cmd_run(args: argparse.Namespace) -> None:
    if args.mode != "safe":
        raise SystemExit("The one-shot run command supports safe mode only. Use the frames command with --mode authorized for frame extraction.")
    out = cmd_prepare(args)
    analyze_args = argparse.Namespace(out=str(out))
    cmd_analyze(analyze_args)
    render_args = argparse.Namespace(out=str(out))
    cmd_render(render_args)
    write_run_review(out, args.mode)
    cmd_render(render_args)
    print(f"Completed safe-mode note package at: {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="youtube-study-note skill helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="Collect metadata and transcript")
    p.add_argument("--input", help="YouTube URL or local video path")
    p.add_argument("--transcript", help="Existing transcript file (.json, .md, .txt, .srt, .vtt)")
    p.add_argument("--title", help="Optional display title when using an existing transcript")
    p.add_argument("--out", help=f"Output directory, defaults under {DEFAULT_NOTES_ROOT}")
    p.add_argument("--languages", default="zh.*,en.*", help="Subtitle language regex for yt-dlp")
    p.add_argument("--whisper-model", default="mlx-community/whisper-large-v3-turbo", help="MLX Whisper model or local path")
    p.add_argument("--js-runtime", default="node", help="yt-dlp JavaScript runtime, pass empty string to disable")
    p.add_argument("--cookies-from-browser", help="Optional yt-dlp browser cookie source, e.g. chrome or safari")
    p.add_argument("--cookies", help="Optional Netscape-format cookies file for yt-dlp")
    p.add_argument("--tool-timeout", type=float, default=120.0, help="Seconds before external media commands time out")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("analyze", help="Create deterministic summary/debate/frame/image-prompt artifacts")
    p.add_argument("--out", required=True, help="Prepared output directory")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("run", help="One-shot safe-mode note generation")
    p.add_argument("--input", help="YouTube URL or local video path")
    p.add_argument("--transcript", help="Existing transcript file (.json, .md, .txt, .srt, .vtt)")
    p.add_argument("--title", help="Optional display title when using an existing transcript")
    p.add_argument("--out", help=f"Output directory, defaults under {DEFAULT_NOTES_ROOT}")
    p.add_argument("--languages", default="zh.*,en.*", help="Subtitle language regex for yt-dlp")
    p.add_argument("--whisper-model", default="mlx-community/whisper-large-v3-turbo", help="MLX Whisper model or local path")
    p.add_argument("--js-runtime", default="node", help="yt-dlp JavaScript runtime, pass empty string to disable")
    p.add_argument("--cookies-from-browser", help="Optional yt-dlp browser cookie source, e.g. chrome or safari")
    p.add_argument("--cookies", help="Optional Netscape-format cookies file for yt-dlp")
    p.add_argument("--tool-timeout", type=float, default=120.0, help="Seconds before external media commands time out")
    p.add_argument("--mode", choices=["safe"], default="safe")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("frames", help="Extract candidate frames from a frame plan")
    p.add_argument("--input", required=True, help="YouTube URL or local video path")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--frame-plan", required=True, help="Path to frame_plan.json")
    p.add_argument("--mode", choices=["safe", "authorized"], default="safe")
    p.add_argument("--window-seconds", type=float, default=8.0)
    p.add_argument("--js-runtime", default="node", help="yt-dlp JavaScript runtime, pass empty string to disable")
    p.add_argument("--cookies-from-browser", help="Optional yt-dlp browser cookie source, e.g. chrome or safari")
    p.add_argument("--cookies", help="Optional Netscape-format cookies file for yt-dlp")
    p.add_argument("--tool-timeout", type=float, default=120.0, help="Seconds before external media commands time out")
    p.set_defaults(func=cmd_frames)

    p = sub.add_parser("render", help="Render Markdown/HTML report from JSON outputs")
    p.add_argument("--out", required=True, help="Output directory")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("image", help="Register PNG/JPEG/WebP images generated with the built-in imagegen tool")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--image-prompts", help="Optional path to image_prompts.json for titles")
    p.add_argument("--asset", action="append", required=True, help="Generated asset mapping, e.g. sketch_map_01=~/.codex/generated_images/.../image.png")
    p.add_argument("--render", action="store_true", help="Render report.md/report.html/index.html after updating generated_images.json")
    p.set_defaults(func=cmd_image)

    p = sub.add_parser("remember", help="Append verified local experience to references/video-patterns")
    p.add_argument("--out", required=False, help="Run output directory, optional")
    p.add_argument("--source", required=True, help="Domain/channel/source key")
    p.add_argument("--note", required=True, help="Verified observation to remember")
    p.set_defaults(func=cmd_remember)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
