#!/usr/bin/env python3
"""
audio-to-obsidian orchestration script.

Pipeline:
URL -> extract-url-media -> (subtitle or transcribe) -> write-obsidian-note
Local media -> transcribe -> write-obsidian-note

支持：
- 时间记录（meta.json startedAt/completedAt/duration）
- 重试 + 失败清理（指数退避，permanently_failed 标记）
- --resume 断点续传（扫描 pipeline_dir 恢复中断任务）
- --cleanup-on-failure 失败时删除部分产物后重试
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from json import JSONDecoder
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 导入管线工具
from pipeline_utils import (
    execute_stage,
    cleanup_media_stage,
    cleanup_transcribe_stage,
    cleanup_obsidian_stage,
    read_meta,
    update_meta,
    now_iso,
    calc_duration_seconds,
    find_resumable_tasks,
    reset_for_resume,
    format_duration,
)


MEDIA_EXTS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".aac",
    ".ogg",
    ".wma",
    ".opus",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".ts",
    ".flv",
}


@dataclass
class PipelineError(Exception):
    message: str


def parse_json_output(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise PipelineError("子命令无输出，无法解析 JSON")

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 兼容：日志 + JSON 混合输出，提取最后一个可解析 JSON 对象
    decoder = JSONDecoder()
    last_obj: dict[str, Any] | None = None
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            last_obj = obj
    if last_obj is not None:
        return last_obj

    raise PipelineError(f"子命令未返回合法 JSON: {text[:500]}")


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_script_paths() -> dict[str, Path]:
    skill_dir = Path(__file__).resolve().parents[1]
    skills_root = skill_dir.parent
    return {
        "extract": skills_root / "extract-url-media" / "scripts" / "extract.py",
        "transcribe": skills_root / "audio-to-subtitle" / "scripts" / "transcribe.py",
        "write_note": skills_root / "write-obsidian-note" / "scripts" / "write_note.py",
    }


def validate_script_paths(paths: dict[str, Path]) -> None:
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        details = ", ".join(f"{name}:{paths[name]}" for name in missing)
        raise PipelineError(f"缺少依赖脚本: {details}")


def read_urls_from_file(path: Path) -> list[str]:
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def infer_inputs(input_arg: str) -> list[dict[str, str]]:
    if input_arg.startswith("http://") or input_arg.startswith("https://"):
        return [{"type": "url", "value": input_arg}]

    path = Path(input_arg).expanduser().resolve()
    if not path.exists():
        raise PipelineError(f"输入不存在: {path}")

    if path.suffix.lower() == ".txt":
        urls = read_urls_from_file(path)
        if not urls:
            raise PipelineError(f"URL 文件为空: {path}")
        return [{"type": "url", "value": u} for u in urls]

    if path.suffix.lower() in MEDIA_EXTS:
        return [{"type": "local", "value": str(path)}]

    raise PipelineError(f"不支持的输入类型: {path}")


# ---------------------------------------------------------------------------
# 阶段执行函数（供 execute_stage 调用）
# ---------------------------------------------------------------------------

def _do_extract(
    url: str,
    scripts: dict[str, Path],
    pipeline_dir: Path,
) -> dict[str, Any]:
    """执行 extract-url-media 阶段，返回提取数据。"""
    extract_cmd = [
        "python3",
        str(scripts["extract"]),
        url,
        "--video-pipeline-dir",
        str(pipeline_dir),
    ]
    result = run_cmd(extract_cmd)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    data = parse_json_output(output)
    if result.returncode != 0 or not data.get("success"):
        raise PipelineError(f"extract-url-media 失败: {output[:1200]}")
    return data["data"]


def _do_transcribe(
    audio_path: Path,
    work_dir: Path,
    engine: str,
    model: str,
    transcript_format: str,
    transcribe_script: Path,
) -> dict[str, Any]:
    """执行 ASR 转录阶段，返回转录文件路径。"""
    ext = ".md" if transcript_format == "md" else f".{transcript_format}"
    output_path = work_dir / f"{audio_path.stem}{ext}"
    if output_path.exists() and output_path.stat().st_size > 0:
        return {"transcriptPath": str(output_path), "source": "cache"}

    cmd = [
        "python3",
        str(transcribe_script),
        str(audio_path),
        "--yolo",
        "--engine",
        engine,
        "-m",
        model,
        "-f",
        transcript_format,
        "-o",
        str(work_dir),
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise PipelineError((result.stdout + "\n" + result.stderr).strip()[:1500])
    if not output_path.exists():
        raise PipelineError(f"转录完成但未找到输出文件: {output_path}")
    return {"transcriptPath": str(output_path), "source": f"asr-{engine}"}


def _do_write_note(
    write_note_script: Path,
    obsidian_repo: Path,
    payload: dict[str, Any],
    overwrite: bool,
) -> dict[str, Any]:
    """执行 Obsidian 笔记写入阶段。"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            "python3",
            str(write_note_script),
            "--input-json",
            str(tmp_path),
            "--obsidian-repo",
            str(obsidian_repo),
        ]
        if overwrite:
            cmd.append("--overwrite")
        result = run_cmd(cmd)
        output_text = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        data = parse_json_output(output_text)
        if result.returncode != 0 or not data.get("success", False):
            raise PipelineError(f"写入 Obsidian 失败: {output_text[:1200]}")
        return data
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 任务处理（使用 execute_stage 包装）
# ---------------------------------------------------------------------------

def process_url_task(
    *,
    url: str,
    scripts: dict[str, Path],
    pipeline_dir: Path,
    obsidian_repo: Path,
    engine: str,
    model: str,
    transcript_format: str,
    category: str,
    overwrite: bool,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    """处理单个 URL 任务，三阶段（extract → transcribe → write）。"""
    pipeline_started = now_iso()
    extract_data: dict[str, Any] = {}

    # Stage 1: 提取媒体
    def stage_extract() -> dict[str, Any]:
        nonlocal extract_data
        extract_data = _do_extract(url, scripts, pipeline_dir)
        return {
            "audioFile": extract_data.get("audioPath", ""),
            "subtitlePath": extract_data.get("subtitlePath"),
            "subtitleSource": extract_data.get("subtitleSource"),
        }

    # 先执行 extract 获取 work_dir
    # extract-url-media 会创建工作目录和 meta.json
    # 所以我们需要先调用 extract，获取 work_dir 后再继续
    extract_cmd = [
        "python3",
        str(scripts["extract"]),
        url,
        "--video-pipeline-dir",
        str(pipeline_dir),
    ]
    extract_result = run_cmd(extract_cmd)
    extract_output = (extract_result.stdout or "") + ("\n" + extract_result.stderr if extract_result.stderr else "")
    extract_json = parse_json_output(extract_output)
    if extract_result.returncode != 0 or not extract_json.get("success"):
        raise PipelineError(f"extract-url-media 失败: {extract_output[:1200]}")

    data = extract_json["data"]
    work_dir = Path(data["workDir"])

    # 初始化 pipeline 级 meta
    update_meta(work_dir, {
        "pipeline": {
            "version": 2,
            "engine": engine,
            "model": model,
            "format": transcript_format,
            "category": category,
            "overwrite": overwrite,
            "startedAt": pipeline_started,
            "status": "in_progress",
            "resumeCount": 0,
        },
        "stages": {
            "media": {"status": "done", "completedAt": now_iso(), "attempts": 1},
        },
    })

    # Stage 2: 获取转录文本
    subtitle_path = Path(data["subtitlePath"]) if data.get("subtitlePath") else None
    if subtitle_path and subtitle_path.exists():
        transcript_text = subtitle_path.read_text(encoding="utf-8", errors="ignore")
        update_meta(work_dir, {
            "stages": {
                "subtitle": {
                    "status": "done",
                    "source": "embedded",
                    "file": str(subtitle_path),
                    "completedAt": now_iso(),
                    "attempts": 1,
                }
            }
        })
    else:
        audio_path = Path(data["audioPath"])

        def stage_transcribe() -> dict[str, Any]:
            result = _do_transcribe(
                audio_path=audio_path,
                work_dir=work_dir,
                engine=engine,
                model=model,
                transcript_format=transcript_format,
                transcribe_script=scripts["transcribe"],
            )
            return {
                "source": result["source"],
                "file": result["transcriptPath"],
            }

        trans_result = execute_stage(
            "subtitle", work_dir,
            stage_fn=stage_transcribe,
            cleanup_fn=cleanup_transcribe_stage,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        if trans_result["status"] == "permanently_failed":
            update_meta(work_dir, {"pipeline": {"status": "failed", "completedAt": now_iso()}})
            raise PipelineError(trans_result.get("lastError", "转录阶段失败"))

        transcript_path = Path(trans_result["file"])
        transcript_text = transcript_path.read_text(encoding="utf-8", errors="ignore")

    # Stage 3: 写入 Obsidian
    payload = {
        "metadata": {
            "title": data.get("title") or data.get("id"),
            "author": data.get("author") or "unknown",
            "url": data.get("url") or url,
            "duration": data.get("duration") or "",
            "platform": data.get("platform") or "",
        },
        "transcript": transcript_text,
        "category": category,
        "extraContent": {},
    }

    note_result_holder: dict[str, Any] = {}

    def stage_write() -> dict[str, Any]:
        result = _do_write_note(
            write_note_script=scripts["write_note"],
            obsidian_repo=obsidian_repo,
            payload=payload,
            overwrite=overwrite,
        )
        note_result_holder.update(result)
        return result.get("files", {})

    write_result = execute_stage(
        "obsidian", work_dir,
        stage_fn=stage_write,
        cleanup_fn=lambda wd: None,  # Obsidian 写入失败不清理（由用户决定）
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    if write_result["status"] == "permanently_failed":
        update_meta(work_dir, {"pipeline": {"status": "failed", "completedAt": now_iso()}})
        raise PipelineError(write_result.get("lastError", "写入 Obsidian 失败"))

    # 更新 pipeline 级完成状态
    update_meta(work_dir, {
        "pipeline": {
            "status": "completed",
            "completedAt": now_iso(),
        }
    })

    return {
        "input": url,
        "type": "url",
        "status": "success",
        "workDir": str(work_dir),
        "noteFiles": note_result_holder.get("files", {}),
        "skipped": bool(note_result_holder.get("skipped", False)),
    }


def process_local_task(
    *,
    media_path: Path,
    scripts: dict[str, Path],
    pipeline_dir: Path,
    obsidian_repo: Path,
    engine: str,
    model: str,
    transcript_format: str,
    category: str,
    overwrite: bool,
    max_retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    """处理本地媒体任务，两阶段（transcribe → write）。"""
    pipeline_started = now_iso()
    work_dir = pipeline_dir / "local" / media_path.stem
    work_dir.mkdir(parents=True, exist_ok=True)

    # 初始化 meta
    update_meta(work_dir, {
        "id": media_path.stem,
        "platform": "local",
        "source": str(media_path),
        "title": media_path.stem,
        "pipeline": {
            "version": 2,
            "engine": engine,
            "model": model,
            "format": transcript_format,
            "category": category,
            "overwrite": overwrite,
            "startedAt": pipeline_started,
            "status": "in_progress",
            "resumeCount": 0,
        },
        "stages": {
            "media": {"status": "skipped", "reason": "local_file"},
            "subtitle": {"status": "pending"},
            "obsidian": {"status": "pending"},
        },
    })

    # Stage 1: 转录
    def stage_transcribe() -> dict[str, Any]:
        result = _do_transcribe(
            audio_path=media_path,
            work_dir=work_dir,
            engine=engine,
            model=model,
            transcript_format=transcript_format,
            transcribe_script=scripts["transcribe"],
        )
        return {
            "source": result["source"],
            "file": result["transcriptPath"],
        }

    trans_result = execute_stage(
        "subtitle", work_dir,
        stage_fn=stage_transcribe,
        cleanup_fn=cleanup_transcribe_stage,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    if trans_result["status"] == "permanently_failed":
        update_meta(work_dir, {"pipeline": {"status": "failed", "completedAt": now_iso()}})
        raise PipelineError(trans_result.get("lastError", "转录阶段失败"))

    transcript_path = Path(trans_result["file"])
    transcript_text = transcript_path.read_text(encoding="utf-8", errors="ignore")

    # Stage 2: 写入 Obsidian
    payload = {
        "metadata": {
            "title": media_path.stem,
            "author": "local",
            "url": str(media_path),
            "duration": "",
            "platform": "local",
        },
        "transcript": transcript_text,
        "category": category,
        "extraContent": {},
    }

    note_result_holder: dict[str, Any] = {}

    def stage_write() -> dict[str, Any]:
        result = _do_write_note(
            write_note_script=scripts["write_note"],
            obsidian_repo=obsidian_repo,
            payload=payload,
            overwrite=overwrite,
        )
        note_result_holder.update(result)
        return result.get("files", {})

    write_result = execute_stage(
        "obsidian", work_dir,
        stage_fn=stage_write,
        cleanup_fn=lambda wd: None,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    if write_result["status"] == "permanently_failed":
        update_meta(work_dir, {"pipeline": {"status": "failed", "completedAt": now_iso()}})
        raise PipelineError(write_result.get("lastError", "写入 Obsidian 失败"))

    # 更新 pipeline 级完成状态
    update_meta(work_dir, {
        "pipeline": {
            "status": "completed",
            "completedAt": now_iso(),
        }
    })

    return {
        "input": str(media_path),
        "type": "local",
        "status": "success",
        "workDir": str(work_dir),
        "noteFiles": note_result_holder.get("files", {}),
        "skipped": bool(note_result_holder.get("skipped", False)),
    }


# ---------------------------------------------------------------------------
# 恢复模式
# ---------------------------------------------------------------------------

def resume_tasks(
    pipeline_dir: Path,
    scripts: dict[str, Path],
    obsidian_repo: Path,
    engine: str,
    model: str,
    transcript_format: str,
    category: str,
    overwrite: bool,
    max_retries: int,
    retry_delay: float,
) -> list[dict[str, Any]]:
    """扫描并恢复中断的任务。"""
    resumable = find_resumable_tasks(pipeline_dir)
    if not resumable:
        return []

    results: list[dict[str, Any]] = []
    for task in resumable:
        work_dir = Path(task["workDir"])
        meta = task["meta"]
        reset_for_resume(meta)
        update_meta(work_dir, meta)

        # 判断是 URL 还是本地任务
        platform = meta.get("platform", "local")
        if platform == "local":
            source = meta.get("source", "")
            if not source or not Path(source).exists():
                results.append({
                    "input": source,
                    "type": "local",
                    "status": "failed",
                    "error": f"源文件不存在: {source}",
                })
                continue
            result = process_local_task(
                media_path=Path(source),
                scripts=scripts,
                pipeline_dir=pipeline_dir,
                obsidian_repo=obsidian_repo,
                engine=engine,
                model=model,
                transcript_format=transcript_format,
                category=category,
                overwrite=overwrite,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
        else:
            url = meta.get("url", "")
            if not url:
                results.append({
                    "input": str(work_dir),
                    "type": "resume",
                    "status": "failed",
                    "error": "meta.json 中无 URL 信息",
                })
                continue
            result = process_url_task(
                url=url,
                scripts=scripts,
                pipeline_dir=pipeline_dir,
                obsidian_repo=obsidian_repo,
                engine=engine,
                model=model,
                transcript_format=transcript_format,
                category=category,
                overwrite=overwrite,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="audio-to-obsidian 编排脚本")
    parser.add_argument("input", nargs="?", default="", help="URL / 本地媒体文件 / URL 列表 .txt")
    parser.add_argument(
        "--obsidian-repo",
        default=os.environ.get("OBSIDIAN_REPO", ""),
        help="Obsidian 仓库路径（默认取 OBSIDIAN_REPO）",
    )
    parser.add_argument(
        "--video-pipeline-dir",
        default="~/Downloads/video-pipeline",
        help="工作目录根路径",
    )
    parser.add_argument("--engine", choices=["local", "doubao"], default="local")
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--transcript-format", choices=["md", "txt", "srt", "vtt"], default="md")
    parser.add_argument("--category", default="Audio")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-items", type=int, default=0, help="批量任务最多处理 N 条（0 表示不限）")
    parser.add_argument("--dry-run", action="store_true", help="仅解析输入并输出计划，不执行实际处理")
    parser.add_argument("--stop-on-error", action="store_true", help="遇到失败立即停止后续任务")
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="任务间延迟秒数，默认 0")
    parser.add_argument("--resume", action="store_true", help="恢复中断的任务（扫描 pipeline-dir 中未完成的 meta.json）")
    parser.add_argument("--max-retries", type=int, default=3, help="每阶段最大重试次数（默认 3）")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="重试基础延迟秒数（默认 2.0，指数退避）")
    args = parser.parse_args()

    if not args.obsidian_repo:
        print(json.dumps({"success": False, "error": "缺少 --obsidian-repo 或 OBSIDIAN_REPO"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    obsidian_repo = Path(args.obsidian_repo).expanduser().resolve()
    if not obsidian_repo.exists():
        print(json.dumps({"success": False, "error": f"Obsidian 仓库不存在: {obsidian_repo}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    pipeline_dir = Path(args.video_pipeline_dir).expanduser().resolve()
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    scripts = get_script_paths()
    validate_script_paths(scripts)

    # ---- 恢复模式 ----
    if args.resume:
        resumed = resume_tasks(
            pipeline_dir=pipeline_dir,
            scripts=scripts,
            obsidian_repo=obsidian_repo,
            engine=args.engine,
            model=args.model,
            transcript_format=args.transcript_format,
            category=args.category,
            overwrite=args.overwrite,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
        )
        success_count = sum(1 for r in resumed if r.get("status") == "success")
        report = {
            "success": success_count == len(resumed),
            "mode": "resume",
            "summary": {
                "total": len(resumed),
                "success": success_count,
                "failed": len(resumed) - success_count,
            },
            "items": resumed,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if report["success"] else 1)

    # ---- 正常模式 ----
    if not args.input:
        print(json.dumps({"success": False, "error": "缺少输入参数，或使用 --resume 恢复中断任务"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        tasks = infer_inputs(args.input)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    if args.max_items > 0:
        tasks = tasks[: args.max_items]

    if args.dry_run:
        report = {
            "success": True,
            "summary": {
                "total": len(tasks),
                "success": 0,
                "failed": 0,
            },
            "items": [{"input": t["value"], "type": t["type"], "status": "planned"} for t in tasks],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 执行任务
    report_items: list[dict[str, Any]] = []
    for idx, task in enumerate(tasks):
        try:
            if task["type"] == "url":
                result = process_url_task(
                    url=task["value"],
                    scripts=scripts,
                    pipeline_dir=pipeline_dir,
                    obsidian_repo=obsidian_repo,
                    engine=args.engine,
                    model=args.model,
                    transcript_format=args.transcript_format,
                    category=args.category,
                    overwrite=args.overwrite,
                    max_retries=args.max_retries,
                    retry_delay=args.retry_delay,
                )
            else:
                result = process_local_task(
                    media_path=Path(task["value"]),
                    scripts=scripts,
                    pipeline_dir=pipeline_dir,
                    obsidian_repo=obsidian_repo,
                    engine=args.engine,
                    model=args.model,
                    transcript_format=args.transcript_format,
                    category=args.category,
                    overwrite=args.overwrite,
                    max_retries=args.max_retries,
                    retry_delay=args.retry_delay,
                )
            report_items.append(result)
        except Exception as exc:  # noqa: BLE001
            report_items.append(
                {
                    "input": task["value"],
                    "type": task["type"],
                    "status": "failed",
                    "error": str(exc),
                }
            )
            if args.stop_on_error:
                break
        if args.delay_seconds > 0 and idx < len(tasks) - 1:
            time.sleep(args.delay_seconds)

    success_count = sum(1 for i in report_items if i["status"] == "success")
    total = len(report_items)
    report = {
        "success": success_count == total,
        "summary": {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
        },
        "items": report_items,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
