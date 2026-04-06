#!/usr/bin/env python3
"""
write-obsidian-note: metadata + transcript -> Obsidian raw/wiki notes.

Following the llm-wiki pattern:
- raw/[author]/title.md  — Raw subtitle/transcript (immutable)
- wiki/title-归纳.md     — Compiled summary referencing raw
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


# ---------------------------------------------------------------------------
# Transcript segmentation
# ---------------------------------------------------------------------------

_TS_HEADING = re.compile(r"^###\s+(\d+:\d{2})\s+(.+)$")
_TS_LIST_ITEM = re.compile(r"^(?:-\s+)?\*\*(\d+:\d{2})\*\*\s+(.+)$")
_TS_PLAIN = re.compile(r"^(\d+:\d{2})\s+(.+)$")


def _segment_transcript(transcript: str) -> list[tuple[str, str, str]]:
    """将 transcript 按语义分段。

    支持三种输入格式：
      - heading:  ### M:SS 标题
      - list item: - **M:SS** 内容
      - plain:    M:SS 内容

    返回 [(timecode, title, content), ...]
    """
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    segments: list[tuple[str, str, str]] = []
    current_time = "0:00"
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        m = _TS_HEADING.match(line)
        if m:
            if current_lines:
                segments.append((current_time, current_title, "\n".join(current_lines)))
            current_time = m.group(1)
            current_title = m.group(2).strip()
            current_lines = []
            continue

        m = _TS_LIST_ITEM.match(line)
        if m:
            if current_lines:
                segments.append((current_time, current_title, "\n".join(current_lines)))
            current_time = m.group(1)
            current_title = m.group(2).strip()[:50]
            current_lines = []
            continue

        m = _TS_PLAIN.match(line)
        if m:
            if current_lines:
                segments.append((current_time, current_title, "\n".join(current_lines)))
            current_time = m.group(1)
            current_title = m.group(2).strip()[:50]
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        segments.append((current_time, current_title, "\n".join(current_lines)))

    return segments


def _group_segments(
    segments: list[tuple[str, str, str]],
    target_count: int = 12,
    min_duration_s: float = 20.0,
) -> list[tuple[str, str, str]]:
    """将碎片段落合并为语义完整的段落（target_count 个左右）。"""
    if not segments:
        return []

    def _ts_to_seconds(ts: str) -> float:
        parts = ts.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

    merged: list[tuple[str, str, str]] = []
    for timecode, title, content in segments:
        duration_est = 0.0
        if merged:
            prev_ts = _ts_to_seconds(merged[-1][0])
            cur_ts = _ts_to_seconds(timecode)
            duration_est = cur_ts - prev_ts

        if duration_est < min_duration_s and merged:
            prev_time, prev_title, prev_content = merged[-1]
            new_content = prev_content + "\n" + content
            merged[-1] = (prev_time, prev_title, new_content)
        else:
            merged.append((timecode, title, content))

    if len(merged) > target_count * 2:
        step = len(merged) // target_count
        result = []
        for i in range(0, len(merged), step):
            batch = merged[i : i + step]
            timecode = batch[0][0]
            title = batch[0][1] if batch[0][1] else batch[-1][1]
            content = "\n".join(c for _, _, c in batch)
            result.append((timecode, title, content))
        return result[:target_count]

    return merged


# ---------------------------------------------------------------------------
# Note builders
# ---------------------------------------------------------------------------


def build_raw_note(
    title: str,
    author: str,
    author_tag: str,
    url: str,
    duration: str,
    extract_date: str,
    transcript: str,
    category: str,
    tags: list[str],
) -> str:
    """构建 raw 层笔记 — 直接保存字幕/文案原始内容。

    遵循 llm-wiki 的 raw 层规范：
    - 带有标准 frontmatter 元数据
    - 不可变，后续 wiki 编译时只读不写
    """
    tags_text = " ".join(tags).strip()

    # 构建时间轴分段
    raw_segments = _segment_transcript(transcript)
    grouped = _group_segments(raw_segments)

    if grouped:
        timeline_parts = []
        for timecode, seg_title, content in grouped:
            heading = f"### {timecode} {seg_title}" if seg_title else f"### {timecode}"
            timeline_parts.append(f"{heading}\n\n{content}")
        timeline_md = "\n\n".join(timeline_parts)
    else:
        timeline_md = transcript if transcript.strip() else "（无转录内容）"

    tags_line = f"#音频笔记 {author_tag}"
    if tags_text:
        tags_line += f" {tags_text}"

    return (
        "---\n"
        f"source: \"{url}\"\n"
        f"author: \"{author}\"\n"
        f"ingested_at: {extract_date}\n"
        f"type: transcript\n"
        f"category: {category}\n"
        f"duration: \"{duration or 'unknown'}\"\n"
        f"status: uncompiled\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{timeline_md}\n\n"
        "---\n"
        f"{tags_line}\n"
    )


def build_summary_note(
    title: str,
    author: str,
    author_tag: str,
    url: str,
    duration: str,
    extract_date: str,
    points: list[str],
    quote_line: str,
    embed_code: str | None,
    tags: list[str],
) -> str:
    """构建 wiki 层归纳笔记 — 引用 raw 层原文。"""
    tags_text = " ".join(tags).strip()
    if tags_text:
        tags_text = " " + tags_text

    # raw 层引用路径
    raw_ref = f"raw/{author}/{title}"
    extra_embed = (embed_code + "\n\n") if embed_code else ""

    points_md = ""
    for i, p in enumerate(points, 1):
        points_md += f"### {i}. {p[:60]}\n\n{p}\n\n→ [[{raw_ref}]]\n\n"

    return (
        f"# {title} - 归纳\n\n"
        f"> **作者**: {author}\n"
        f"> **来源**: {url}\n"
        f"> **时长**: {duration or '未知'}\n"
        f"> **提取时间**: {extract_date}\n"
        f"> **原文**: [[{raw_ref}]]\n\n"
        f"{extra_embed}"
        "## 音频来源\n\n"
        f"> [!quote] 🔗 [点击播放]({url})\n\n"
        "---\n\n"
        "## 核心观点\n\n"
        f"{points_md}"
        "## 关键引用\n\n"
        f"> {quote_line} — [[{raw_ref}]]\n\n"
        "## 我的思考\n\n"
        "[待补充]\n\n"
        "---\n"
        f"#音频笔记 {author_tag} #归纳{tags_text}\n"
    )


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Raw 索引维护
# ---------------------------------------------------------------------------


def _read_frontmatter_date(md_path: Path) -> str:
    """从 frontmatter 读取 ingested_at 日期。"""
    try:
        text = md_path.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                for line in text[3:end].splitlines():
                    if line.strip().startswith("ingested_at:"):
                        return line.split(":", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "unknown"


def rebuild_raw_index(obsidian_repo: Path) -> None:
    """重建 raw/index.md 作者索引（扫描 raw/ 目录）。

    遵循 llm-wiki 的索引地图层理念：紧凑、可导航、一行一描述。
    """
    raw_dir = obsidian_repo / "raw"
    if not raw_dir.exists():
        return

    # 扫描所有作者目录
    authors: dict[str, list[tuple[str, str]]] = {}
    for author_dir in sorted(raw_dir.iterdir()):
        if not author_dir.is_dir() or author_dir.name.startswith("."):
            continue
        author = author_dir.name
        entries = []
        for md_file in sorted(author_dir.glob("*.md")):
            if md_file.name.startswith("."):
                continue
            title = md_file.stem
            date_str = _read_frontmatter_date(md_file)
            entries.append((title, date_str))
        if entries:
            authors[author] = entries

    if not authors:
        return

    # 生成索引
    total_files = sum(len(e) for e in authors.values())
    lines = [
        "---",
        "type: index",
        f"updated_at: {date.today()}",
        f"authors: {len(authors)}",
        f"files: {total_files}",
        "---",
        "",
        "# 作者索引",
        "",
        f"> 自动维护 · {len(authors)} 位作者 · {total_files} 篇资料",
        "",
    ]

    for author, entries in authors.items():
        lines.append(f"## {author}")
        lines.append("")
        for entry_title, entry_date in entries:
            lines.append(f"- [[raw/{author}/{entry_title}]] — {entry_date}")
        lines.append("")

    atomic_write(raw_dir / "index.md", "\n".join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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

    # llm-wiki 风格的输出路径：raw/ 按作者区分，wiki/ 保存归纳
    raw_dir = obsidian_repo / "raw" / author
    wiki_dir = obsidian_repo / "wiki"
    raw_path = raw_dir / f"{title}.md"
    summary_path = wiki_dir / f"{title}-归纳.md"

    if (raw_path.exists() or summary_path.exists()) and not overwrite:
        return {
            "success": True,
            "skipped": True,
            "reason": "target_exists",
            "files": {
                "originalPath": str(raw_path),
                "summaryPath": str(summary_path),
            },
        }

    author_tag = normalize_tag(author_raw) or "#unknown"
    extra_tags = []
    for t in extra_content.get("extraTags", []):
        normalized = normalize_tag(str(t))
        if normalized:
            extra_tags.append(normalized)
    quote_line = next(
        (ln.strip() for ln in transcript.splitlines() if ln.strip()),
        "（待补充）",
    )
    points = split_key_points(transcript)

    raw_content = build_raw_note(
        title=title,
        author=author,
        author_tag=author_tag,
        url=url,
        duration=duration,
        extract_date=extract_date,
        transcript=transcript,
        category=category,
        tags=extra_tags,
    )
    summary_content = build_summary_note(
        title=title,
        author=author,
        author_tag=author_tag,
        url=url,
        duration=duration,
        extract_date=extract_date,
        points=points,
        quote_line=quote_line,
        embed_code=extra_content.get("embedCode"),
        tags=extra_tags,
    )

    atomic_write(raw_path, raw_content)
    atomic_write(summary_path, summary_content)

    # 写入后自动重建 raw/index.md 作者索引
    rebuild_raw_index(obsidian_repo)

    return {
        "success": True,
        "files": {
            "originalPath": str(raw_path),
            "summaryPath": str(summary_path),
        },
    }


def split_key_points(transcript: str, max_points: int = 7) -> list[str]:
    """从 transcript 中提取核心观点（每条对应一个语义段落）"""
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    points: list[str] = []
    for line in lines:
        if len(points) >= max_points:
            break
        if line.startswith("#"):
            continue
        # 跳过纯时间戳行
        if re.match(r"^\d+:\d{2}\s", line):
            continue
        text = re.sub(r"^\d+:\d{2}\s*", "", line).strip()
        if len(text) > 10:
            points.append(text)
    if not points:
        points = ["（待补充）"]
    return points


def print_json(obj: dict[str, Any], exit_code: int) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="写入 Obsidian raw/wiki 笔记")
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
