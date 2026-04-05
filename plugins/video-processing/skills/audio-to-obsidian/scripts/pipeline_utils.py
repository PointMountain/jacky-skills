#!/usr/bin/env python3
"""
pipeline_utils.py — audio-to-obsidian 管线通用工具。

提供 meta.json 读写、阶段执行器（时间追踪 + 重试 + 清理）、
断点续传检测等基础能力，供 pipeline.py 和未来消费者复用。
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# 时间工具
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """返回当前 ISO8601 时间戳（本地时区）。"""
    return datetime.now().astimezone().isoformat()


def _parse_iso(ts: str) -> datetime:
    """解析 ISO8601 时间戳。"""
    return datetime.fromisoformat(ts)


def calc_duration_seconds(start_iso: str, end_iso: str) -> float:
    """计算两个 ISO 时间戳之间的秒数。"""
    return (_parse_iso(end_iso) - _parse_iso(start_iso)).total_seconds()


# ---------------------------------------------------------------------------
# meta.json 读写
# ---------------------------------------------------------------------------

def read_meta(work_dir: Path) -> dict[str, Any] | None:
    """读取 meta.json，不存在或解析失败返回 None。"""
    meta_path = work_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def update_meta(work_dir: Path, updates: dict[str, Any]) -> None:
    """原子更新 meta.json：读取 → 深度合并 → 写回。"""
    meta_path = work_dir / "meta.json"
    meta = read_meta(work_dir) or {}
    _deep_merge(meta, updates)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _deep_merge(base: dict, override: dict) -> None:
    """将 override 深度合并到 base（就地修改）。"""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# 清理函数
# ---------------------------------------------------------------------------

def cleanup_media_stage(work_dir: Path) -> None:
    """删除 extract 阶段的部分产物（空文件或音频文件）。"""
    for pattern in ["audio.*"]:
        for f in work_dir.glob(pattern):
            if f.stat().st_size == 0:
                f.unlink(missing_ok=True)


def cleanup_transcribe_stage(work_dir: Path) -> None:
    """删除 ASR 转录阶段的部分产物。"""
    for ext in ["*.md", "*.srt", "*.vtt", "*.txt"]:
        for f in work_dir.glob(ext):
            # 只删除非 meta.json 的文件
            if f.name != "meta.json" and f.stat().st_size == 0:
                f.unlink(missing_ok=True)


def cleanup_obsidian_stage(note_files: dict[str, str]) -> None:
    """删除部分写入的 Obsidian 笔记。"""
    for key in ("originalPath", "summaryPath"):
        path = note_files.get(key)
        if path:
            p = Path(path)
            if p.exists() and p.stat().st_size == 0:
                p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 阶段执行器
# ---------------------------------------------------------------------------

def execute_stage(
    stage_name: str,
    work_dir: Path,
    stage_fn: Callable[[], dict[str, Any]],
    max_retries: int = 3,
    retry_delay: float = 2.0,
    cleanup_fn: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    """
    执行管线的一个阶段，包含：
    - 时间追踪（startedAt / completedAt / duration）
    - 重试（指数退避，最多 max_retries 次）
    - 失败清理（调用 cleanup_fn 删除部分产物）
    - meta.json 状态更新

    返回:
      {"status": "done", ...result}      成功
      {"status": "skipped", "reason": …} 已完成（跳过）
      {"status": "permanently_failed", "lastError": …} 重试耗尽
    """
    meta = read_meta(work_dir) or {}
    stages = meta.setdefault("stages", {})
    stage = stages.setdefault(stage_name, {})

    # 已完成且无错误 → 跳过
    if stage.get("status") == "done":
        return {"status": "skipped", "reason": "already_done"}

    prev_attempts = stage.get("attempts", 0)
    last_error: str | None = None

    for attempt in range(1, max_retries + 1):
        started_at = now_iso()
        update_meta(work_dir, {
            "stages": {
                stage_name: {
                    "status": "in_progress",
                    "startedAt": started_at,
                    "attempts": prev_attempts + attempt,
                }
            }
        })

        try:
            result = stage_fn()
            completed_at = now_iso()
            duration = calc_duration_seconds(started_at, completed_at)

            stage_update: dict[str, Any] = {
                "status": "done",
                "completedAt": completed_at,
                "duration": duration,
                "lastError": None,
            }
            stage_update.update(result)
            update_meta(work_dir, {"stages": {stage_name: stage_update}})
            return {"status": "done", **result}

        except Exception as exc:
            last_error = str(exc)

            # 失败清理
            if cleanup_fn:
                try:
                    cleanup_fn(work_dir)
                except Exception:
                    pass  # 清理失败不影响主流程

            update_meta(work_dir, {
                "stages": {
                    stage_name: {
                        "status": "failed",
                        "lastError": last_error,
                        "attempts": prev_attempts + attempt,
                    }
                }
            })

            if attempt < max_retries:
                delay = retry_delay * (2 ** (attempt - 1))
                time.sleep(delay)

    # 所有重试耗尽
    update_meta(work_dir, {
        "stages": {
            stage_name: {
                "status": "permanently_failed",
                "lastError": last_error,
            }
        }
    })
    return {"status": "permanently_failed", "lastError": last_error}


# ---------------------------------------------------------------------------
# 断点续传
# ---------------------------------------------------------------------------

RESUMABLE_STATUSES = {"pending", "failed", "in_progress", "permanently_failed"}


def find_resumable_tasks(pipeline_dir: Path) -> list[dict[str, Any]]:
    """扫描 pipeline_dir 下所有 meta.json，返回可恢复的任务列表。"""
    tasks: list[dict[str, Any]] = []
    if not pipeline_dir.exists():
        return tasks

    for meta_path in sorted(pipeline_dir.rglob("meta.json")):
        meta = read_meta(meta_path.parent)
        if not meta:
            continue

        # 检查是否有未完成的阶段
        stages = meta.get("stages", {})
        has_resumable = any(
            s.get("status") in RESUMABLE_STATUSES
            for s in stages.values()
        )
        if has_resumable:
            tasks.append({
                "type": "resume",
                "workDir": str(meta_path.parent),
                "meta": meta,
            })
    return tasks


def reset_for_resume(meta: dict[str, Any]) -> dict[str, Any]:
    """将中断/失败的阶段重置为 pending，准备恢复。"""
    for stage_name, stage in meta.get("stages", {}).items():
        if stage.get("status") in RESUMABLE_STATUSES:
            stage["status"] = "pending"
            stage["lastError"] = None
    # 更新 pipeline 级别
    pipeline = meta.setdefault("pipeline", {})
    pipeline["status"] = "resuming"
    pipeline["resumeCount"] = pipeline.get("resumeCount", 0) + 1
    return meta


def format_duration(seconds: float) -> str:
    """将秒数格式化为人类可读的时长。"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m{secs:.0f}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h{mins}m"
