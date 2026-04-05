#!/usr/bin/env python3
"""
extract-url-media: URL -> metadata + audio + optional subtitle.

Output contract:
{
  "success": true,
  "data": {...}
}
or
{
  "success": false,
  "error": {...}
}
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MIN_FREE_MB = 500


@dataclass
class ExtractError(Exception):
    stage: str
    message: str
    suggestion: str


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def check_disk_space(target_dir: Path) -> None:
    usage = shutil.disk_usage(target_dir)
    free_mb = usage.free / (1024 * 1024)
    if free_mb < MIN_FREE_MB:
        raise ExtractError(
            stage="precheck",
            message=f"磁盘剩余空间不足: {free_mb:.1f}MB (< {MIN_FREE_MB}MB)",
            suggestion="清理磁盘空间后重试",
        )


def run_cmd_with_retry(
    cmd: list[str],
    stage: str,
    retries: int = 3,
    backoff_seconds: list[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    if backoff_seconds is None:
        backoff_seconds = [1, 2, 4]

    last_result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(retries):
        last_result = subprocess.run(cmd, capture_output=True, text=True)
        if last_result.returncode == 0:
            return last_result
        if attempt < retries - 1:
            time.sleep(backoff_seconds[min(attempt, len(backoff_seconds) - 1)])

    assert last_result is not None
    raise ExtractError(
        stage=stage,
        message=(last_result.stderr or last_result.stdout or "未知错误").strip(),
        suggestion=build_suggestion(last_result.stderr or ""),
    )


def build_suggestion(stderr: str) -> str:
    lowered = stderr.lower()
    if "403" in lowered:
        return '可尝试: yt-dlp --cookies-from-browser chrome "<URL>"'
    if "429" in lowered:
        return "可能触发频率限制，建议等待 30 分钟后重试"
    if "ffmpeg" in lowered and "not found" in lowered:
        return "安装 ffmpeg: brew install ffmpeg"
    return "检查 URL 可用性、网络连接或 Cookie 设置后重试"


def load_video_info(url: str) -> dict[str, Any]:
    cmd = [
        "yt-dlp",
        "--socket-timeout",
        "30",
        "--retries",
        "3",
        "--dump-single-json",
        "--no-playlist",
        url,
    ]
    result = run_cmd_with_retry(cmd, stage="metadata")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExtractError(
            stage="metadata",
            message=f"解析元信息失败: {exc}",
            suggestion="更新 yt-dlp 到最新版本后重试",
        ) from exc
    if not isinstance(info, dict) or not info.get("id"):
        raise ExtractError(
            stage="metadata",
            message="yt-dlp 返回元信息不完整（缺少视频 ID）",
            suggestion="检查 URL 是否为单视频页面",
        )
    return info


def find_first_file(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    return files[0] if files else None


def write_meta(
    meta_path: Path,
    info: dict[str, Any],
    audio_file: Path | None,
    subtitle_file: Path | None,
) -> None:
    data = {
        "id": info.get("id"),
        "platform": str(info.get("extractor_key", "unknown")).lower(),
        "url": info.get("webpage_url") or info.get("original_url") or "",
        "title": info.get("title") or "",
        "author": info.get("uploader") or info.get("channel") or "unknown",
        "duration": info.get("duration_string") or "",
        "stages": {
            "media": {
                "status": "done" if audio_file else "failed",
                "audioFile": audio_file.name if audio_file else None,
            },
            "subtitle": {
                "status": "done" if subtitle_file else "pending",
                "source": "embedded" if subtitle_file else None,
                "file": subtitle_file.name if subtitle_file else None,
            },
            "obsidian": {"status": "pending"},
        },
    }
    meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing_result(work_dir: Path) -> dict[str, Any] | None:
    """已有产物复用：meta.json + audio 文件存在时直接返回。"""
    meta_path = work_dir / "meta.json"
    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    audio_file: Path | None = None
    audio_name = ((meta.get("stages") or {}).get("media") or {}).get("audioFile")
    if isinstance(audio_name, str) and audio_name.strip():
        candidate = work_dir / audio_name
        if candidate.exists() and candidate.stat().st_size > 0:
            audio_file = candidate
    if audio_file is None:
        audio_file = find_first_file(work_dir, "audio*.wav")
        if audio_file is None or audio_file.stat().st_size <= 0:
            return None

    subtitle_file: Path | None = None
    subtitle_name = ((meta.get("stages") or {}).get("subtitle") or {}).get("file")
    if isinstance(subtitle_name, str) and subtitle_name.strip():
        candidate = work_dir / subtitle_name
        if candidate.exists() and candidate.stat().st_size > 0:
            subtitle_file = candidate
    if subtitle_file is None:
        subtitle_file = find_first_file(work_dir, "subtitle*.srt")

    return {
        "id": meta.get("id") or work_dir.name,
        "platform": meta.get("platform") or work_dir.parent.name,
        "url": meta.get("url") or "",
        "title": meta.get("title") or "",
        "author": meta.get("author") or "unknown",
        "duration": meta.get("duration") or "",
        "audioPath": str(audio_file),
        "subtitlePath": str(subtitle_file) if subtitle_file else None,
        "subtitleSource": "embedded" if subtitle_file else None,
        "workDir": str(work_dir),
        "metaPath": str(meta_path),
    }


def guess_platform_and_id(url: str) -> tuple[str, str] | None:
    """从常见 URL 快速猜测平台和视频 ID。"""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path

    if "youtube.com" in host or "youtu.be" in host:
        if "youtu.be" in host:
            video_id = path.strip("/").split("/")[0] if path.strip("/") else ""
        else:
            qs = parse_qs(parsed.query)
            video_id = (qs.get("v") or [""])[0]
            if not video_id:
                m = re.search(r"/shorts/([A-Za-z0-9_-]+)", path)
                video_id = m.group(1) if m else ""
        if video_id:
            return ("youtube", video_id)

    if "bilibili.com" in host or "b23.tv" in host:
        m = re.search(r"(BV[0-9A-Za-z]+)", url)
        if m:
            return ("bilibili", m.group(1))

    return None


def extract_media(url: str, root_dir: Path, skip_subs: bool, force_refresh: bool = False) -> dict[str, Any]:
    if not command_exists("yt-dlp"):
        raise ExtractError(
            stage="precheck",
            message="未检测到 yt-dlp",
            suggestion="安装 yt-dlp: brew install yt-dlp",
        )
    if not command_exists("ffmpeg"):
        raise ExtractError(
            stage="precheck",
            message="未检测到 ffmpeg",
            suggestion="安装 ffmpeg: brew install ffmpeg",
        )

    root_dir.mkdir(parents=True, exist_ok=True)
    check_disk_space(root_dir)

    if not force_refresh:
        guessed = guess_platform_and_id(url)
        if guessed:
            guessed_platform, guessed_id = guessed
            guessed_work_dir = root_dir / guessed_platform / guessed_id
            existing = load_existing_result(guessed_work_dir)
            if existing is not None:
                return existing

    info = load_video_info(url)
    video_id = str(info["id"])
    platform = str(info.get("extractor_key", "unknown")).lower()
    work_dir = root_dir / platform / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    if not force_refresh:
        existing = load_existing_result(work_dir)
        if existing is not None:
            return existing

    audio_file = work_dir / "audio.wav"
    if not (audio_file.exists() and audio_file.stat().st_size > 0):
        extract_cmd = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "wav",
            "--audio-quality",
            "0",
            "--socket-timeout",
            "30",
            "--retries",
            "3",
            "--postprocessor-args",
            "ffmpeg:-ar 16000 -ac 1",
            "-o",
            str(work_dir / "audio.%(ext)s"),
            url,
        ]
        run_cmd_with_retry(extract_cmd, stage="download")

    audio_file = find_first_file(work_dir, "audio*.wav")
    if audio_file is None:
        raise ExtractError(
            stage="download",
            message="音频提取后未找到 WAV 文件",
            suggestion="检查 ffmpeg 后处理参数并重试",
        )

    subtitle_file: Path | None = None
    if not skip_subs:
        sub_cmd = [
            "yt-dlp",
            "--write-sub",
            "--write-auto-subs",
            "--sub-lang",
            "zh-Hans,zh-CN,zh,en",
            "--convert-subs",
            "srt",
            "--skip-download",
            "--socket-timeout",
            "30",
            "--retries",
            "3",
            "-o",
            str(work_dir / "subtitle.%(ext)s"),
            url,
        ]
        subprocess.run(sub_cmd, capture_output=True, text=True)
        subtitle_file = find_first_file(work_dir, "subtitle*.srt")

    meta_path = work_dir / "meta.json"
    write_meta(meta_path, info, audio_file, subtitle_file)

    return {
        "id": video_id,
        "platform": platform,
        "url": info.get("webpage_url") or info.get("original_url") or url,
        "title": info.get("title") or "",
        "author": info.get("uploader") or info.get("channel") or "unknown",
        "duration": info.get("duration_string") or "",
        "audioPath": str(audio_file),
        "subtitlePath": str(subtitle_file) if subtitle_file else None,
        "subtitleSource": "embedded" if subtitle_file else None,
        "workDir": str(work_dir),
        "metaPath": str(meta_path),
    }


def print_json(obj: dict[str, Any], exit_code: int) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 URL 提取媒体元信息、音频和字幕（可选）",
    )
    parser.add_argument("url", help="视频 URL")
    parser.add_argument(
        "--video-pipeline-dir",
        default="~/Downloads/video-pipeline",
        help="工作目录根路径（默认: ~/Downloads/video-pipeline）",
    )
    parser.add_argument(
        "--skip-subs",
        action="store_true",
        help="跳过字幕提取",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="忽略已有产物，强制重新拉取",
    )
    args = parser.parse_args()

    root_dir = Path(args.video_pipeline_dir).expanduser().resolve()
    try:
        data = extract_media(
            args.url,
            root_dir=root_dir,
            skip_subs=args.skip_subs,
            force_refresh=args.force_refresh,
        )
        print_json({"success": True, "data": data}, exit_code=0)
    except ExtractError as exc:
        print_json(
            {
                "success": False,
                "error": {
                    "url": args.url,
                    "stage": exc.stage,
                    "message": exc.message,
                    "suggestion": exc.suggestion,
                },
            },
            exit_code=1,
        )
    except Exception as exc:  # noqa: BLE001
        print_json(
            {
                "success": False,
                "error": {
                    "url": args.url,
                    "stage": "unknown",
                    "message": str(exc),
                    "suggestion": "检查输入与环境依赖后重试",
                },
            },
            exit_code=1,
        )


if __name__ == "__main__":
    main()
