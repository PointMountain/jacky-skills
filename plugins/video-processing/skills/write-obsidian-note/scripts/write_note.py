#!/usr/bin/env python3
"""
write-obsidian-note: metadata + transcript -> Obsidian original/summary notes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


INVALID_FILENAME_CHARS = r'[\/\\\?\%\*\:\|\"<>\n\r\t]'


@dataclass
class NoteError(Exception):
    message: str


def sanitize_filename(value: str, max_len: int) -> str:
    cleaned = re.sub(INVALID_FILENAME_CHARS, "_", value).strip()
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_len]


def split_key_points(transcript: str, max_points: int = 5) -> list[str]:
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    points: list[str] = []
    for line in lines:
        if len(points) >= max_points:
            break
        if line.startswith("#"):
            continue
        points.append(line[:120])
    if not points:
        points = ["（待补充）"]
    return points


def normalize_tag(tag: str) -> str:
    value = tag.strip()
    if not value:
        return ""
    if value.startswith("#"):
        value = value[1:]
    value = value.replace(" ", "_")
    value = re.sub(INVALID_FILENAME_CHARS, "_", value).strip("_")
    if not value:
        return ""
    return f"#{value}"


def build_original_note(
    title: str,
    author: str,
    author_tag: str,
    url: str,
    duration: str,
    extract_date: str,
    transcript: str,
    embed_code: str | None,
    tags: list[str],
) -> str:
    extra_embed = (embed_code + "\n\n") if embed_code else ""
    tags_text = " ".join(tags).strip()
    if tags_text:
        tags_text = " " + tags_text
    transcript_block = transcript if transcript.strip() else "（无转录内容）"
    return (
        f"# {title}\n\n"
        f"> **作者**: {author}\n"
        f"> **来源**: {url}\n"
        f"> **提取时间**: {extract_date}\n"
        f"> **时长**: {duration or '未知'}\n"
        f"> **版权声明**: 内容仅用于个人学习与研究\n\n"
        f"{extra_embed}"
        "## 音频来源\n\n"
        f"> [!quote] 🔗 [点击播放]({url})\n\n"
        "---\n\n"
        "## 完整文案（带时间戳）\n\n"
        f"{transcript_block}\n\n"
        "---\n"
        f"#音频笔记 {author_tag}{tags_text}\n"
    )


def build_summary_note(
    title: str,
    author: str,
    author_tag: str,
    url: str,
    points: list[str],
    quote_line: str,
    tags: list[str],
) -> str:
    tags_text = " ".join(tags).strip()
    if tags_text:
        tags_text = " " + tags_text
    points_md = "\n".join(f"- {p}" for p in points)
    return (
        f"# {title} - 归纳\n\n"
        f"> **作者**: {author}\n"
        f"> **来源**: {url}\n"
        f"> **原文**: [[{title}-原文]]\n\n"
        "## 核心要点\n\n"
        f"{points_md}\n\n"
        "## 关键引用\n\n"
        f"> {quote_line}\n\n"
        "## 我的思考\n\n"
        "[待补充]\n\n"
        "---\n"
        f"#音频笔记 {author_tag} #归纳{tags_text}\n"
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        prefix=".tmp_",
        suffix=".md",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def parse_payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_json:
        return json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    if not args.title or not args.author or not args.url:
        raise NoteError("未提供 --input-json 时，必须提供 --title/--author/--url")

    transcript = ""
    if args.transcript_file:
        transcript = Path(args.transcript_file).read_text(encoding="utf-8")
    elif args.transcript:
        transcript = args.transcript

    return {
        "metadata": {
            "title": args.title,
            "author": args.author,
            "url": args.url,
            "duration": args.duration or "",
            "date": args.date or str(date.today()),
            "platform": args.platform or "",
        },
        "transcript": transcript,
        "category": args.category,
        "extraContent": {
            "embedCode": args.embed_code,
            "extraTags": args.extra_tag or [],
        },
    }


def write_notes(
    payload: dict[str, Any],
    obsidian_repo: Path,
    overwrite: bool,
) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    transcript = str(payload.get("transcript") or "")
    category = str(payload.get("category") or "Audio")
    extra_content = payload.get("extraContent") or {}

    title_raw = str(metadata.get("title") or "")
    author_raw = str(metadata.get("author") or "unknown")
    url = str(metadata.get("url") or "")
    if not title_raw or not url:
        raise NoteError("metadata.title 和 metadata.url 不能为空")

    title = sanitize_filename(title_raw, max_len=200)
    author = sanitize_filename(author_raw, max_len=50)
    extract_date = str(metadata.get("date") or date.today())
    duration = str(metadata.get("duration") or "")

    output_dir = obsidian_repo / "00-Inbox" / category / author
    original_path = output_dir / f"{title}-原文.md"
    summary_path = output_dir / f"{title}-归纳.md"

    if (original_path.exists() or summary_path.exists()) and not overwrite:
        return {
            "success": True,
            "skipped": True,
            "reason": "target_exists",
            "files": {
                "originalPath": str(original_path),
                "summaryPath": str(summary_path),
            },
        }

    author_tag = normalize_tag(author_raw) or "#unknown"
    extra_tags = []
    for t in extra_content.get("extraTags", []):
        normalized = normalize_tag(str(t))
        if normalized:
            extra_tags.append(normalized)
    quote_line = next((ln.strip() for ln in transcript.splitlines() if ln.strip()), "（待补充）")
    points = split_key_points(transcript)

    original_content = build_original_note(
        title=title,
        author=author,
        author_tag=author_tag,
        url=url,
        duration=duration,
        extract_date=extract_date,
        transcript=transcript,
        embed_code=extra_content.get("embedCode"),
        tags=extra_tags,
    )
    summary_content = build_summary_note(
        title=title,
        author=author,
        author_tag=author_tag,
        url=url,
        points=points,
        quote_line=quote_line,
        tags=extra_tags,
    )

    atomic_write(original_path, original_content)
    atomic_write(summary_path, summary_content)

    return {
        "success": True,
        "files": {
            "originalPath": str(original_path),
            "summaryPath": str(summary_path),
        },
    }


def print_json(obj: dict[str, Any], exit_code: int) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="写入 Obsidian 原文/归纳笔记")
    parser.add_argument("--input-json", help="输入契约 JSON 文件路径")

    parser.add_argument("--title")
    parser.add_argument("--author")
    parser.add_argument("--url")
    parser.add_argument("--duration")
    parser.add_argument("--date")
    parser.add_argument("--platform")
    parser.add_argument("--transcript")
    parser.add_argument("--transcript-file")
    parser.add_argument("--category", default="Audio")
    parser.add_argument("--embed-code")
    parser.add_argument("--extra-tag", action="append")

    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在文件")
    parser.add_argument(
        "--obsidian-repo",
        default=os.environ.get("OBSIDIAN_REPO", ""),
        help="Obsidian 仓库路径（默认读取 OBSIDIAN_REPO）",
    )
    args = parser.parse_args()

    if not args.obsidian_repo:
        print_json(
            {"success": False, "error": "OBSIDIAN_REPO 未设置，请通过 --obsidian-repo 或环境变量提供"},
            exit_code=1,
        )

    repo = Path(args.obsidian_repo).expanduser().resolve()
    if not repo.exists():
        print_json(
            {"success": False, "error": f"OBSIDIAN_REPO 不存在: {repo}"},
            exit_code=1,
        )

    try:
        payload = parse_payload_from_args(args)
        result = write_notes(payload, obsidian_repo=repo, overwrite=args.overwrite)
        print_json(result, exit_code=0)
    except NoteError as exc:
        print_json({"success": False, "error": exc.message}, exit_code=1)
    except Exception as exc:  # noqa: BLE001
        print_json({"success": False, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    main()
