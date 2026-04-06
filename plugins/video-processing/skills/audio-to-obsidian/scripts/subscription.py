#!/usr/bin/env python3
"""
subscription.py — UP 主订阅管理核心脚本。

串联 bilibili-video-list（获取列表）和 audio-to-obsidian pipeline（处理视频），
提供增量同步、状态追踪、临时文件清理等能力。

用法：
    # 订阅 UP 主
    python3 subscription.py subscribe --uid 3546392779491985
    python3 subscription.py subscribe --name "姜汁汽水"

    # 增量同步
    python3 subscription.py sync --uid 3546392779491985
    python3 subscription.py sync --all

    # 查看状态
    python3 subscription.py status --uid 3546392779491985

    # 导出未处理 URL
    python3 subscription.py export --uid 3546392779491985 --output /tmp/new.txt

    # 处理新视频
    python3 subscription.py process --uid 3546392779491985 --obsidian-repo /path/to/ob

    # 跳过视频
    python3 subscription.py skip --uid 3546392779491985 --bvids BV1xx,BV1yy

    # 刷新状态（从 pipeline meta.json 同步）
    python3 subscription.py refresh --uid 3546392779491985

    # 清理临时文件
    python3 subscription.py cleanup --uid 3546392779491985

    # 取消订阅
    python3 subscription.py unsubscribe --uid 3546392779491985
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# 同级导入
from subscription_utils import (
    SUBSCRIPTIONS_DIR,
    STATUS_NEW,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_SKIPPED,
    RETRYABLE_STATUSES,
    ACTIVE_STATUSES,
    ALL_STATUSES,
    now_iso,
    get_subscription_path,
    list_all_subscriptions,
    load_subscription,
    save_subscription,
    create_subscription,
    add_video,
    update_video_status,
    get_videos_by_status,
    get_subscription_summary,
    cleanup_pipeline_artifacts,
    format_bytes,
    format_summary,
    format_video_list,
)

# 跨 skill 导入 bilibili-video-list 的 API 客户端
_BILIBILI_LIST_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "bilibili-video-list" / "scripts"
)
sys.path.insert(0, str(_BILIBILI_LIST_SCRIPTS))

# pipeline.py 路径
PIPELINE_SCRIPT = Path(__file__).resolve().parent / "pipeline.py"
PIPELINE_DIR = Path.home() / "Downloads" / "video-pipeline"


# ---------------------------------------------------------------------------
# 订阅管理器
# ---------------------------------------------------------------------------


class SubscriptionManager:
    """订阅管理核心类。"""

    def __init__(self, subscriptions_dir: Path | None = None):
        self.subscriptions_dir = subscriptions_dir or SUBSCRIPTIONS_DIR

    # ---- 基础 CRUD ----

    def _resolve_path(self, platform: str, uid: str) -> Path:
        return self.subscriptions_dir / platform / f"{uid}.json"

    def _resolve_uid(self, uid: str, name: str | None = None) -> tuple[str, str]:
        """解析 UID，支持名字搜索。返回 (uid, uploader)。"""
        if uid:
            return uid, ""

        if not name:
            raise ValueError("必须指定 --uid 或 --name")

        try:
            from api_fetch import BilibiliAPI, get_cookie, resolve_uid
        except ImportError:
            raise RuntimeError(
                "无法导入 bilibili-video-list/api-fetch.py，"
                "请确认 skill 目录结构完整"
            )

        cookies = get_cookie()
        api = BilibiliAPI(cookies)
        resolved = resolve_uid(api, name)
        # 获取 UP 主名称
        user_info = api.get_user_info(resolved)
        uploader = user_info.get("name", "")
        return str(resolved), uploader

    def subscribe(
        self,
        *,
        uid: str = "",
        name: str | None = None,
        platform: str = "bilibili",
    ) -> dict[str, Any]:
        """订阅一个 UP 主。返回订阅数据。"""
        resolved_uid, uploader = self._resolve_uid(uid, name)

        # 如果没有从 UID 直接获取到名字，尝试 API
        if not uploader:
            try:
                from api_fetch import BilibiliAPI, get_cookie

                cookies = get_cookie()
                api = BilibiliAPI(cookies)
                user_info = api.get_user_info(int(resolved_uid))
                uploader = user_info.get("name", f"uid_{resolved_uid}")
            except Exception:
                uploader = f"uid_{resolved_uid}"

        path = self._resolve_path(platform, resolved_uid)
        existing = load_subscription(path)
        if existing:
            return {
                "success": True,
                "action": "already_subscribed",
                "uploader": existing.get("uploader", uploader),
                "uid": resolved_uid,
                "totalVideos": len(existing.get("videos", {})),
            }

        sub = create_subscription(
            platform=platform,
            uid=resolved_uid,
            uploader=uploader,
        )
        save_subscription(path, sub)
        return {
            "success": True,
            "action": "subscribed",
            "uploader": uploader,
            "uid": resolved_uid,
            "totalVideos": 0,
        }

    def unsubscribe(
        self, *, uid: str, platform: str = "bilibili"
    ) -> dict[str, Any]:
        """取消订阅。"""
        path = self._resolve_path(platform, uid)
        sub = load_subscription(path)
        if not sub:
            return {"success": False, "error": f"未找到订阅: {uid}"}

        path.unlink()
        return {
            "success": True,
            "action": "unsubscribed",
            "uploader": sub.get("uploader", ""),
            "uid": uid,
        }

    # ---- 同步 ----

    def sync(
        self,
        *,
        uid: str = "",
        platform: str = "bilibili",
        sync_all: bool = False,
        order: str = "pubdate",
        limit: int = 0,
    ) -> dict[str, Any]:
        """增量同步：从 API 获取视频列表，diff 发现新视频。"""
        if sync_all:
            targets = self._load_all_subscriptions(platform)
        else:
            if not uid:
                return {"success": False, "error": "必须指定 --uid 或 --all"}
            path = self._resolve_path(platform, uid)
            sub = load_subscription(path)
            if not sub:
                return {"success": False, "error": f"未找到订阅: {uid}"}
            targets = [(path, sub)]

        total_added = 0
        results = []

        for path, sub in targets:
            added = self._sync_single(sub, path, order=order, limit=limit)
            total_added += added
            results.append(
                {
                    "uploader": sub.get("uploader", ""),
                    "uid": sub.get("uid", ""),
                    "added": added,
                    "total": len(sub.get("videos", {})),
                }
            )

        return {
            "success": True,
            "totalAdded": total_added,
            "subscriptions": results,
        }

    def _sync_single(
        self,
        sub: dict[str, Any],
        path: Path,
        order: str = "pubdate",
        limit: int = 0,
    ) -> int:
        """同步单个订阅，返回新增数量。"""
        try:
            from api_fetch import BilibiliAPI, get_cookie

            cookies = get_cookie()
            api = BilibiliAPI(cookies)
            uid = int(sub["uid"])
            videos, total = api.get_all_videos(uid, order, limit)
        except Exception as e:
            sub["lastSyncAt"] = now_iso()
            sub["lastSyncSource"] = "error"
            save_subscription(path, sub)
            raise RuntimeError(f"同步失败: {e}") from e

        existing_bvids = set(sub.get("videos", {}).keys())
        added = 0

        for v in videos:
            bvid = v.get("bvid", "")
            if not bvid or bvid in existing_bvids:
                continue
            add_video(
                sub,
                bvid=bvid,
                title=v.get("title", ""),
                url=v.get("url", f"https://www.bilibili.com/video/{bvid}"),
                date=v.get("date", ""),
            )
            added += 1

        sub["lastSyncAt"] = now_iso()
        sub["lastSyncSource"] = "api"
        sub["lastSyncVideoCount"] = len(videos)
        save_subscription(path, sub)
        return added

    # ---- 状态 ----

    def status(
        self,
        *,
        uid: str = "",
        platform: str = "bilibili",
        show_all: bool = False,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """查看订阅状态。"""
        if show_all:
            subs = []
            for path in list_all_subscriptions():
                sub = load_subscription(path)
                if sub:
                    subs.append(
                        {
                            "uploader": sub.get("uploader", ""),
                            "uid": sub.get("uid", ""),
                            "summary": get_subscription_summary(sub),
                            "lastSyncAt": sub.get("lastSyncAt"),
                        }
                    )
            return {"success": True, "subscriptions": subs}

        if not uid:
            return {"success": False, "error": "必须指定 --uid 或 --all"}

        path = self._resolve_path(platform, uid)
        sub = load_subscription(path)
        if not sub:
            return {"success": False, "error": f"未找到订阅: {uid}"}

        result: dict[str, Any] = {
            "success": True,
            "uploader": sub.get("uploader", ""),
            "uid": sub.get("uid", ""),
            "summary": get_subscription_summary(sub),
            "lastSyncAt": sub.get("lastSyncAt"),
        }

        if verbose:
            actionable = get_videos_by_status(sub, RETRYABLE_STATUSES)
            result["actionableVideos"] = [
                {"bvid": bvid, "title": v.get("title", ""), "status": v.get("status")}
                for bvid, v in actionable
            ]

        return result

    # ---- 导出 ----

    def export(
        self,
        *,
        uid: str,
        output: str,
        statuses: set[str] | None = None,
        platform: str = "bilibili",
    ) -> dict[str, Any]:
        """导出视频 URL 到文件。"""
        statuses = statuses or RETRYABLE_STATUSES
        path = self._resolve_path(platform, uid)
        sub = load_subscription(path)
        if not sub:
            return {"success": False, "error": f"未找到订阅: {uid}"}

        videos = get_videos_by_status(sub, statuses)
        urls = [v.get("url", "") for _, v in videos if v.get("url")]

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(urls), encoding="utf-8")

        return {
            "success": True,
            "count": len(urls),
            "output": str(output_path),
        }

    # ---- 处理 ----

    def process(
        self,
        *,
        uid: str,
        obsidian_repo: str,
        platform: str = "bilibili",
        engine: str = "local",
        model: str = "large-v3-turbo",
        transcript_format: str = "md",
        category: str = "Audio",
        max_items: int = 0,
        overwrite: bool = False,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> dict[str, Any]:
        """处理新视频：收集 → 写临时文件 → 调 pipeline.py → 更新状态。"""
        path = self._resolve_path(platform, uid)
        sub = load_subscription(path)
        if not sub:
            return {"success": False, "error": f"未找到订阅: {uid}"}

        # 收集待处理视频
        actionable = get_videos_by_status(sub, RETRYABLE_STATUSES)
        if max_items > 0:
            actionable = actionable[:max_items]
        if not actionable:
            return {"success": True, "processed": 0, "message": "没有待处理的视频"}

        # 标记为 pending
        for bvid, _ in actionable:
            update_video_status(sub, bvid, STATUS_PENDING)
        save_subscription(path, sub)

        # 写临时 URL 文件
        urls = [v.get("url", "") for _, v in actionable if v.get("url")]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("\n".join(urls))
            tmp_path = Path(tmp.name)

        try:
            # 调用 pipeline.py
            cmd = [
                "python3",
                str(PIPELINE_SCRIPT),
                str(tmp_path),
                "--obsidian-repo",
                obsidian_repo,
                "--video-pipeline-dir",
                str(PIPELINE_DIR),
                "--engine",
                engine,
                "--model",
                model,
                "--transcript-format",
                transcript_format,
                "--category",
                category,
                "--max-retries",
                str(max_retries),
                "--retry-delay",
                str(retry_delay),
            ]
            if overwrite:
                cmd.append("--overwrite")

            result = subprocess.run(cmd, capture_output=True, text=True)
            report = self._parse_pipeline_output(result.stdout + result.stderr)

            # 更新视频状态
            bvid_set = {bvid for bvid, _ in actionable}
            items = report.get("items", [])
            completed_bvids = set()
            failed_bvids = set()

            for item in items:
                input_url = item.get("input", "")
                for bvid, v in actionable:
                    if bvid in input_url or v.get("url", "") == input_url:
                        if item.get("status") == "success":
                            completed_bvids.add(bvid)
                            update_video_status(
                                sub,
                                bvid,
                                STATUS_COMPLETED,
                                processedAt=now_iso(),
                                pipelineDir=item.get("workDir", ""),
                            )
                        else:
                            failed_bvids.add(bvid)
                            update_video_status(
                                sub,
                                bvid,
                                STATUS_FAILED,
                                lastError=item.get("error", ""),
                            )
                        break

            # 未出现在报告中的 → 回退为 new（下次可重试）
            for bvid, _ in actionable:
                if bvid not in completed_bvids and bvid not in failed_bvids:
                    update_video_status(sub, bvid, STATUS_NEW)

            save_subscription(path, sub)

            return {
                "success": True,
                "processed": len(completed_bvids),
                "failed": len(failed_bvids),
                "total": len(actionable),
            }

        except Exception as e:
            # 异常 → 所有 pending 回退为 new
            for bvid, _ in actionable:
                update_video_status(sub, bvid, STATUS_NEW)
            save_subscription(path, sub)
            return {"success": False, "error": str(e)}

        finally:
            tmp_path.unlink(missing_ok=True)

    # ---- 跳过 ----

    def skip(
        self, *, uid: str, bvids: list[str], platform: str = "bilibili"
    ) -> dict[str, Any]:
        """跳过指定视频。"""
        path = self._resolve_path(platform, uid)
        sub = load_subscription(path)
        if not sub:
            return {"success": False, "error": f"未找到订阅: {uid}"}

        skipped = 0
        for bvid in bvids:
            if update_video_status(sub, bvid, STATUS_SKIPPED):
                skipped += 1

        save_subscription(path, sub)
        return {"success": True, "skipped": skipped}

    # ---- 刷新 ----

    def refresh(
        self, *, uid: str = "", platform: str = "bilibili", refresh_all: bool = False
    ) -> dict[str, Any]:
        """从 pipeline meta.json 同步视频处理状态。"""
        if refresh_all:
            targets = self._load_all_subscriptions(platform)
        else:
            if not uid:
                return {"success": False, "error": "必须指定 --uid 或 --all"}
            path = self._resolve_path(platform, uid)
            sub = load_subscription(path)
            if not sub:
                return {"success": False, "error": f"未找到订阅: {uid}"}
            targets = [(path, sub)]

        total_updated = 0
        results = []

        for path, sub in targets:
            updated = self._refresh_single(sub)
            if updated > 0:
                save_subscription(path, sub)
            total_updated += updated
            results.append(
                {
                    "uploader": sub.get("uploader", ""),
                    "uid": sub.get("uid", ""),
                    "updated": updated,
                }
            )

        return {"success": True, "totalUpdated": total_updated, "subscriptions": results}

    def _refresh_single(self, sub: dict[str, Any]) -> int:
        """刷新单个订阅的状态。返回更新数量。"""
        updated = 0
        check_statuses = {STATUS_PENDING, STATUS_PROCESSING}

        for bvid, v in sub.get("videos", {}).items():
            if v.get("status") not in check_statuses:
                continue

            pipeline_dir = v.get("pipelineDir")
            if not pipeline_dir:
                continue

            meta_path = PIPELINE_DIR / pipeline_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            pipeline_status = meta.get("pipeline", {}).get("status", "")
            if pipeline_status == "completed":
                update_video_status(
                    sub, bvid, STATUS_COMPLETED, processedAt=now_iso()
                )
                updated += 1
            elif pipeline_status == "failed":
                update_video_status(sub, bvid, STATUS_FAILED)
                updated += 1

        return updated

    # ---- 清理 ----

    def cleanup(
        self,
        *,
        uid: str = "",
        platform: str = "bilibili",
        cleanup_all: bool = False,
    ) -> dict[str, Any]:
        """清理已完成任务的临时文件。"""
        if cleanup_all:
            targets = self._load_all_subscriptions(platform)
        else:
            if not uid:
                return {"success": False, "error": "必须指定 --uid 或 --all"}
            path = self._resolve_path(platform, uid)
            sub = load_subscription(path)
            if not sub:
                return {"success": False, "error": f"未找到订阅: {uid}"}
            targets = [(path, sub)]

        total_freed = 0
        total_cleaned = 0
        results = []

        for path, sub in targets:
            freed, cleaned = self._cleanup_single(sub)
            if cleaned > 0:
                save_subscription(path, sub)
            total_freed += freed
            total_cleaned += cleaned
            results.append(
                {
                    "uploader": sub.get("uploader", ""),
                    "uid": sub.get("uid", ""),
                    "cleaned": cleaned,
                    "freed": format_bytes(freed),
                }
            )

        return {
            "success": True,
            "totalCleaned": total_cleaned,
            "totalFreed": format_bytes(total_freed),
            "subscriptions": results,
        }

    def _cleanup_single(self, sub: dict[str, Any]) -> tuple[int, int]:
        """清理单个订阅的临时文件。返回 (freed_bytes, cleaned_count)。"""
        total_freed = 0
        cleaned = 0

        for bvid, v in sub.get("videos", {}).items():
            if v.get("status") != STATUS_COMPLETED or v.get("cleanedUp"):
                continue

            pipeline_dir = v.get("pipelineDir")
            if not pipeline_dir:
                continue

            dir_path = PIPELINE_DIR / pipeline_dir
            result = cleanup_pipeline_artifacts(dir_path)
            total_freed += result["freedBytes"]

            if result["deleted"]:
                update_video_status(sub, bvid, STATUS_COMPLETED, cleanedUp=True)
                cleaned += 1

        return total_freed, cleaned

    # ---- 内部工具 ----

    def _load_all_subscriptions(
        self, platform: str = ""
    ) -> list[tuple[Path, dict[str, Any]]]:
        """加载所有订阅。"""
        result = []
        for path in list_all_subscriptions():
            if platform and platform not in str(path):
                continue
            sub = load_subscription(path)
            if sub:
                result.append((path, sub))
        return result

    @staticmethod
    def _parse_pipeline_output(text: str) -> dict[str, Any]:
        """解析 pipeline.py 的 JSON 输出（兼容日志+JSON 混合输出）。"""
        stripped = text.strip()
        if not stripped:
            return {"items": []}

        # 尝试直接解析
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 提取最后一个 JSON 对象
        from json import JSONDecoder

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

        return last_obj or {"items": []}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UP 主订阅管理 — 增量同步 + 状态追踪 + 临时文件清理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ---- subscribe ----
    p_sub = subparsers.add_parser("subscribe", help="订阅 UP 主")
    p_sub.add_argument("--uid", default="", help="UP 主 UID")
    p_sub.add_argument("--name", default="", help="UP 主名字（自动搜索 UID）")
    p_sub.add_argument("--platform", default="bilibili")

    # ---- sync ----
    p_sync = subparsers.add_parser("sync", help="增量同步视频列表")
    p_sync.add_argument("--uid", default="", help="UP 主 UID")
    p_sync.add_argument("--all", dest="sync_all", action="store_true", help="同步所有订阅")
    p_sync.add_argument("--platform", default="bilibili")
    p_sync.add_argument("--order", default="pubdate", choices=["pubdate", "click", "stow"])
    p_sync.add_argument("--limit", type=int, default=0, help="获取数量限制（0=全部）")

    # ---- status ----
    p_status = subparsers.add_parser("status", help="查看订阅状态")
    p_status.add_argument("--uid", default="", help="UP 主 UID")
    p_status.add_argument("--all", dest="show_all", action="store_true", help="显示所有订阅")
    p_status.add_argument("--platform", default="bilibili")
    p_status.add_argument("-v", "--verbose", action="store_true", help="显示待处理视频列表")

    # ---- export ----
    p_export = subparsers.add_parser("export", help="导出未处理 URL")
    p_export.add_argument("--uid", required=True, help="UP 主 UID")
    p_export.add_argument("--output", required=True, help="输出文件路径")
    p_export.add_argument("--platform", default="bilibili")
    p_export.add_argument(
        "--statuses",
        default="new,failed",
        help="状态过滤（逗号分隔，默认: new,failed）",
    )

    # ---- process ----
    p_proc = subparsers.add_parser("process", help="处理新视频（调用 pipeline.py）")
    p_proc.add_argument("--uid", required=True, help="UP 主 UID")
    p_proc.add_argument("--obsidian-repo", required=True, help="Obsidian 仓库路径")
    p_proc.add_argument("--platform", default="bilibili")
    p_proc.add_argument("--engine", default="local", choices=["local", "doubao"])
    p_proc.add_argument("--model", default="large-v3-turbo")
    p_proc.add_argument("--transcript-format", default="md", choices=["md", "txt", "srt", "vtt"])
    p_proc.add_argument("--category", default="Audio")
    p_proc.add_argument("--max-items", type=int, default=0, help="最多处理 N 个（0=全部）")
    p_proc.add_argument("--overwrite", action="store_true")
    p_proc.add_argument("--max-retries", type=int, default=3)
    p_proc.add_argument("--retry-delay", type=float, default=2.0)

    # ---- skip ----
    p_skip = subparsers.add_parser("skip", help="跳过视频")
    p_skip.add_argument("--uid", required=True, help="UP 主 UID")
    p_skip.add_argument("--bvids", required=True, help="BV 号列表（逗号分隔）")
    p_skip.add_argument("--platform", default="bilibili")

    # ---- refresh ----
    p_refresh = subparsers.add_parser("refresh", help="从 pipeline 同步状态")
    p_refresh.add_argument("--uid", default="", help="UP 主 UID")
    p_refresh.add_argument("--all", dest="refresh_all", action="store_true", help="刷新所有订阅")
    p_refresh.add_argument("--platform", default="bilibili")

    # ---- cleanup ----
    p_cleanup = subparsers.add_parser("cleanup", help="清理临时文件")
    p_cleanup.add_argument("--uid", default="", help="UP 主 UID")
    p_cleanup.add_argument("--all", dest="cleanup_all", action="store_true", help="清理所有订阅")
    p_cleanup.add_argument("--platform", default="bilibili")

    # ---- unsubscribe ----
    p_unsub = subparsers.add_parser("unsubscribe", help="取消订阅")
    p_unsub.add_argument("--uid", required=True, help="UP 主 UID")
    p_unsub.add_argument("--platform", default="bilibili")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    mgr = SubscriptionManager()

    # ---- 分发 ----
    if args.command == "subscribe":
        result = mgr.subscribe(uid=args.uid, name=args.name, platform=args.platform)

    elif args.command == "sync":
        result = mgr.sync(
            uid=args.uid,
            platform=args.platform,
            sync_all=args.sync_all,
            order=args.order,
            limit=args.limit,
        )

    elif args.command == "status":
        result = mgr.status(
            uid=args.uid,
            platform=args.platform,
            show_all=args.show_all,
            verbose=args.verbose,
        )

    elif args.command == "export":
        statuses = set(args.statuses.split(",")) if args.statuses else None
        result = mgr.export(
            uid=args.uid, output=args.output, statuses=statuses, platform=args.platform
        )

    elif args.command == "process":
        result = mgr.process(
            uid=args.uid,
            obsidian_repo=args.obsidian_repo,
            platform=args.platform,
            engine=args.engine,
            model=args.model,
            transcript_format=args.transcript_format,
            category=args.category,
            max_items=args.max_items,
            overwrite=args.overwrite,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
        )

    elif args.command == "skip":
        bvids = [b.strip() for b in args.bvids.split(",") if b.strip()]
        result = mgr.skip(uid=args.uid, bvids=bvids, platform=args.platform)

    elif args.command == "refresh":
        result = mgr.refresh(
            uid=args.uid,
            platform=args.platform,
            refresh_all=args.refresh_all,
        )

    elif args.command == "cleanup":
        result = mgr.cleanup(
            uid=args.uid,
            platform=args.platform,
            cleanup_all=args.cleanup_all,
        )

    elif args.command == "unsubscribe":
        result = mgr.unsubscribe(uid=args.uid, platform=args.platform)

    else:
        parser.print_help()
        return

    # 终端美化输出（stderr）+ JSON（stdout）
    _print_human_output(args.command, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _print_human_output(command: str, result: dict[str, Any]) -> None:
    """在 stderr 输出人类可读的摘要。"""
    import sys as _sys

    if not result.get("success", True):
        _print(f"❌ {result.get('error', '未知错误')}", file=_sys.stderr)
        return

    if command == "subscribe":
        action = result.get("action", "")
        if action == "already_subscribed":
            _print(
                f"ℹ️ 已订阅: {result['uploader']} (UID: {result['uid']}), "
                f"共 {result.get('totalVideos', 0)} 个视频",
                file=_sys.stderr,
            )
        else:
            _print(
                f"✅ 已订阅: {result['uploader']} (UID: {result['uid']})",
                file=_sys.stderr,
            )

    elif command == "sync":
        subs = result.get("subscriptions", [])
        for s in subs:
            _print(
                f"📡 {s['uploader']}: +{s['added']} 新视频 (总计 {s['total']})",
                file=_sys.stderr,
            )

    elif command == "status":
        if result.get("subscriptions"):
            for s in result["subscriptions"]:
                summary = s.get("summary", {})
                _print(
                    f"📊 {s['uploader']}: "
                    f"✅{summary.get(STATUS_COMPLETED, 0)} "
                    f"🆕{summary.get(STATUS_NEW, 0)} "
                    f"❌{summary.get(STATUS_FAILED, 0)} "
                    f"⏭{summary.get(STATUS_SKIPPED, 0)} "
                    f"/ 共{summary.get('total', 0)}",
                    file=_sys.stderr,
                )
        else:
            summary = result.get("summary", {})
            _print(format_summary_stub(result, summary), file=_sys.stderr)
            if result.get("actionableVideos"):
                _print("\n待处理视频:", file=_sys.stderr)
                for v in result["actionableVideos"][:20]:
                    _print(f"  • {v['bvid']} [{v['status']}] {v['title']}", file=_sys.stderr)

    elif command == "export":
        _print(
            f"📤 导出 {result.get('count', 0)} 个 URL → {result.get('output', '')}",
            file=_sys.stderr,
        )

    elif command == "process":
        _print(
            f"🎬 处理完成: ✅{result.get('processed', 0)} "
            f"❌{result.get('failed', 0)} / 共{result.get('total', 0)}",
            file=_sys.stderr,
        )

    elif command == "skip":
        _print(f"⏭ 跳过 {result.get('skipped', 0)} 个视频", file=_sys.stderr)

    elif command == "refresh":
        _print(
            f"🔄 刷新完成: 更新 {result.get('totalUpdated', 0)} 个视频状态",
            file=_sys.stderr,
        )

    elif command == "cleanup":
        _print(
            f"🧹 清理完成: {result.get('totalCleaned', 0)} 个任务, "
            f"释放 {result.get('totalFreed', '0B')}",
            file=_sys.stderr,
        )

    elif command == "unsubscribe":
        _print(
            f"🗑️ 已取消订阅: {result.get('uploader', '')} (UID: {result.get('uid', '')})",
            file=_sys.stderr,
        )


def _print(msg: str, *, file=None) -> None:
    """安全打印到 stderr。"""
    (file or sys.stderr).write(msg + "\n")


def format_summary_stub(result: dict, summary: dict) -> str:
    """格式化单个订阅的状态摘要。"""
    return (
        f"📊 {result.get('uploader', '?')} (UID: {result.get('uid', '?')})\n"
        f"   ✅ 已完成: {summary.get(STATUS_COMPLETED, 0)}  "
        f"🆕 新增: {summary.get(STATUS_NEW, 0)}  "
        f"⏳ 待处理: {summary.get(STATUS_PENDING, 0)}  "
        f"❌ 失败: {summary.get(STATUS_FAILED, 0)}  "
        f"⏭ 跳过: {summary.get(STATUS_SKIPPED, 0)}  "
        f"/ 共 {summary.get('total', 0)}"
    )


if __name__ == "__main__":
    main()
