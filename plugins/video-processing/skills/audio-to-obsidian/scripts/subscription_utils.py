#!/usr/bin/env python3
"""
subscription_utils.py — 订阅管理工具函数。

提供订阅 JSON 读写、视频状态管理、临时文件清理等基础能力，
供 subscription.py 调用。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

CST = timezone(timedelta(hours=8))

SUBSCRIPTIONS_DIR = Path.home() / "Downloads" / "video-pipeline" / "subscriptions"

CLEANUPABLE_EXTENSIONS = {".wav", ".md", ".srt", ".vtt", ".txt", ".mp3", ".m4a", ".opus"}

# 视频状态机
STATUS_NEW = "new"
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

ALL_STATUSES = {STATUS_NEW, STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED, STATUS_SKIPPED}

# 可重试的状态
RETRYABLE_STATUSES = {STATUS_NEW, STATUS_FAILED}

# 活跃状态（sync 时不会变）
ACTIVE_STATUSES = {STATUS_PENDING, STATUS_PROCESSING}


# ---------------------------------------------------------------------------
# 时间工具
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """返回当前 ISO8601 时间戳（CST）。"""
    return datetime.now(CST).isoformat()


# ---------------------------------------------------------------------------
# 订阅 JSON 读写
# ---------------------------------------------------------------------------

def get_subscription_path(platform: str, uid: str) -> Path:
    """获取订阅文件路径。"""
    return SUBSCRIPTIONS_DIR / platform / f"{uid}.json"


def list_all_subscriptions() -> list[Path]:
    """列出所有订阅文件。"""
    if not SUBSCRIPTIONS_DIR.exists():
        return []
    return sorted(SUBSCRIPTIONS_DIR.rglob("*.json"))


def load_subscription(path: Path) -> dict[str, Any] | None:
    """读取订阅 JSON，失败返回 None。"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_subscription(path: Path, data: dict[str, Any]) -> None:
    """原子写入订阅 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updatedAt"] = now_iso()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def create_subscription(
    platform: str,
    uid: str,
    uploader: str,
    sync_policy: dict[str, Any] | None = None,
    pipeline_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """创建新的订阅数据结构。"""
    now = now_iso()
    return {
        "schema": 1,
        "platform": platform,
        "uploader": uploader,
        "uid": str(uid),
        "createdAt": now,
        "updatedAt": now,
        "lastSyncAt": None,
        "lastSyncSource": None,
        "lastSyncVideoCount": 0,
        "syncPolicy": sync_policy or {"order": "pubdate"},
        "pipelineDefaults": pipeline_defaults or {
            "engine": "local",
            "model": "large-v3-turbo",
            "category": "Audio",
        },
        "videos": {},
    }


# ---------------------------------------------------------------------------
# 视频状态管理
# ---------------------------------------------------------------------------

def add_video(
    sub: dict[str, Any],
    bvid: str,
    title: str,
    url: str,
    date: str = "",
    status: str = STATUS_NEW,
) -> bool:
    """添加视频到订阅。如果已存在则跳过。返回是否新增。"""
    videos = sub.setdefault("videos", {})
    if bvid in videos:
        return False
    videos[bvid] = {
        "title": title,
        "url": url,
        "date": date,
        "status": status,
        "addedAt": now_iso(),
        "processedAt": None,
        "pipelineDir": None,
        "cleanedUp": False,
    }
    return True


def update_video_status(
    sub: dict[str, Any],
    bvid: str,
    status: str,
    **kwargs: Any,
) -> bool:
    """更新视频状态。返回是否成功。"""
    videos = sub.get("videos", {})
    if bvid not in videos:
        return False
    video = videos[bvid]
    video["status"] = status
    for k, v in kwargs.items():
        video[k] = v
    return True


def get_videos_by_status(
    sub: dict[str, Any],
    statuses: set[str] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """获取指定状态的视频列表。返回 [(bvid, video_data), ...]"""
    statuses = statuses or ALL_STATUSES
    videos = sub.get("videos", {})
    return [(bvid, v) for bvid, v in videos.items() if v.get("status") in statuses]


def get_subscription_summary(sub: dict[str, Any]) -> dict[str, int]:
    """按状态统计视频数量。"""
    counts = {s: 0 for s in ALL_STATUSES}
    for v in sub.get("videos", {}).values():
        status = v.get("status", STATUS_NEW)
        if status in counts:
            counts[status] += 1
    counts["total"] = sum(counts.values())
    return counts


# ---------------------------------------------------------------------------
# 临时文件清理
# ---------------------------------------------------------------------------

def cleanup_pipeline_artifacts(
    pipeline_dir: Path,
    keep_meta: bool = True,
) -> dict[str, Any]:
    """清理视频工作目录中的临时文件。

    保留 meta.json，删除音频、字幕、转录等文件。
    返回 {"deleted": [文件列表], "freedBytes": N}。
    """
    deleted: list[str] = []
    freed = 0

    if not pipeline_dir.exists():
        return {"deleted": deleted, "freedBytes": freed}

    for f in pipeline_dir.iterdir():
        if keep_meta and f.name == "meta.json":
            continue
        if f.is_file() and f.suffix.lower() in CLEANUPABLE_EXTENSIONS:
            try:
                size = f.stat().st_size
                f.unlink()
                deleted.append(f.name)
                freed += size
            except OSError:
                pass

    return {"deleted": deleted, "freedBytes": freed}


def format_bytes(n: int) -> str:
    """格式化字节数。"""
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f}MB"
    return f"{n / (1024 * 1024 * 1024):.2f}GB"


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------

def format_summary(sub: dict[str, Any]) -> str:
    """格式化订阅摘要用于终端输出。"""
    counts = get_subscription_summary(sub)
    lines = [
        f"UP 主: {sub.get('uploader', 'unknown')} (UID: {sub.get('uid', '?')})",
        f"平台: {sub.get('platform', '?')}",
        f"创建时间: {sub.get('createdAt', '?')}",
        f"上次同步: {sub.get('lastSyncAt', '从未')}",
        f"视频总数: {counts['total']}",
        "",
        "状态分布:",
        f"  ✅ 已完成: {counts[STATUS_COMPLETED]}",
        f"  🆕 新增:   {counts[STATUS_NEW]}",
        f"  ⏳ 待处理: {counts[STATUS_PENDING]}",
        f"  🔄 处理中: {counts[STATUS_PROCESSING]}",
        f"  ❌ 失败:   {counts[STATUS_FAILED]}",
        f"  ⏭ 跳过:   {counts[STATUS_SKIPPED]}",
    ]
    return "\n".join(lines)


def format_video_list(
    videos: list[tuple[str, dict[str, Any]]],
    max_show: int = 20,
) -> str:
    """格式化视频列表用于终端输出。"""
    if not videos:
        return "（无视频）"

    status_icons = {
        STATUS_NEW: "🆕",
        STATUS_PENDING: "⏳",
        STATUS_PROCESSING: "🔄",
        STATUS_COMPLETED: "✅",
        STATUS_FAILED: "❌",
        STATUS_SKIPPED: "⏭",
    }

    lines = []
    for i, (bvid, v) in enumerate(videos[:max_show], 1):
        icon = status_icons.get(v.get("status", ""), "?")
        title = v.get("title", "?")
        if len(title) > 40:
            title = title[:37] + "..."
        date = v.get("date", "")
        lines.append(f"  {i:>3}. {icon} {bvid}  {date}  {title}")

    if len(videos) > max_show:
        lines.append(f"  ... 还有 {len(videos) - max_show} 个")

    return "\n".join(lines)
