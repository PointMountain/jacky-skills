#!/usr/bin/env python3
"""初始化可恢复的教程学习 run，并在规划后原子绑定 Demo 目录。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0.0"
WORKFLOW_VERSION = "1.1.0"
LEARNING_CONTRACT_VERSION = "1.0.0"
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEMO_RE = re.compile(r"^(\d+)-[a-z0-9][a-z0-9-]*$")
PRIVATE_IGNORE_RULES = {
    "runs": "/.learning/runs/",
    "lock": "/.learning.lock",
}
PRIVATE_IGNORE_BLOCK_BEGIN = "# >>> tutorial-to-hyperframes-demo private state >>>"
PRIVATE_IGNORE_BLOCK_END = "# <<< tutorial-to-hyperframes-demo private state <<<"
LEGACY_PRIVATE_IGNORE_COMMENT = "# tutorial-to-hyperframes-demo 私有运行状态"
NESTED_IGNORE_BLOCK_BEGIN = "# >>> tutorial-to-hyperframes-demo private runs >>>"
NESTED_IGNORE_BLOCK_END = "# <<< tutorial-to-hyperframes-demo private runs <<<"
NESTED_RUNS_IGNORE_RULE = "/runs/"
BIND_INTENT_NAME = "binding-intent.json"
BIND_OWNER_NAME = "binding-owner.json"
FAULT_ENV = "TUTORIAL_TO_HYPERFRAMES_FAULT"
SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = SKILL_ROOT / "references" / "workflows" / f"{WORKFLOW_VERSION}.json"


class ContractError(ValueError):
    """表示输入或 run 状态不满足契约。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"run 不存在：{path.parent.name}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"run.json 不是合法 JSON：{error}") from error
    if not isinstance(value, dict):
        raise ContractError("run.json 顶层必须是对象")
    return value


def read_optional_json(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ContractError(f"{label} 不是合法 JSON：{error}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label} 顶层必须是对象")
    return value


def validate_identifier(value: str, label: str) -> None:
    if not IDENTIFIER_RE.fullmatch(value) or value in {".", ".."}:
        raise ContractError(f"{label} 不安全：只允许字母、数字、点、下划线和连字符")


def resolve_repo(value: str) -> Path:
    repo = Path(value).expanduser().resolve()
    if not repo.is_dir():
        raise ContractError(f"仓库目录不存在：{value}")
    return repo


def git_root(repo: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as error:
        raise ContractError("无法验证私有状态：系统未找到 git") from error
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    if "not a git repository" in result.stderr.lower():
        return None
    detail = result.stderr.strip() or result.stdout.strip() or "未知 Git 错误"
    raise ContractError(f"无法验证私有状态的 Git 仓库：{detail}")


def git_ignores(git_repository: Path, candidate: Path) -> bool:
    try:
        relative = candidate.resolve().relative_to(git_repository).as_posix()
    except ValueError as error:
        raise ContractError("私有状态路径不在 Git 工作树内") from error
    result = subprocess.run(
        ["git", "-C", str(git_repository), "check-ignore", "-q", "--", relative],
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.strip() or result.stdout.strip() or "未知 Git 错误"
    raise ContractError(f"无法检查 Git ignore：{detail}")


def rewrite_authoritative_ignore_block(
    path: Path,
    *,
    rules: tuple[str, ...],
    block_begin: str,
    block_end: str,
    legacy_comments: tuple[str, ...] = (),
) -> None:
    """保留用户规则，将唯一权威保护 block 幂等移动到当前层末尾。"""

    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ContractError(f"非 Git 目录的 {path} 必须是普通文件")
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    retained: list[str] = []
    inside_managed_block = False
    protected_rules = set(rules)
    for line in existing.splitlines():
        if line == block_begin:
            inside_managed_block = True
            continue
        if inside_managed_block:
            if line == block_end:
                inside_managed_block = False
            continue
        if line in protected_rules or line in legacy_comments:
            continue
        retained.append(line)
    if inside_managed_block:
        raise ContractError(f"非 Git 目录的 {path} 含未闭合私有保护 block")

    base = "\n".join(retained).rstrip()
    block = "\n".join([block_begin, *rules, block_end])
    updated = f"{base}\n\n{block}\n" if base else f"{block}\n"
    if updated == existing:
        return
    fd, temp_name = tempfile.mkstemp(prefix=".gitignore.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def bootstrap_non_git_ignore(repo: Path) -> None:
    """为临时非 Git 目录预置未来 git init 后仍生效的隐私保护。"""

    rewrite_authoritative_ignore_block(
        repo / ".gitignore",
        rules=tuple(PRIVATE_IGNORE_RULES.values()),
        block_begin=PRIVATE_IGNORE_BLOCK_BEGIN,
        block_end=PRIVATE_IGNORE_BLOCK_END,
        legacy_comments=(LEGACY_PRIVATE_IGNORE_COMMENT,),
    )

    learning = repo / ".learning"
    if not learning.exists():
        return
    if learning.is_symlink() or not learning.is_dir():
        raise ContractError("非 Git 目录的 .learning 必须是普通目录")
    nested_ignore = learning / ".gitignore"
    if nested_ignore.exists() or nested_ignore.is_symlink():
        rewrite_authoritative_ignore_block(
            nested_ignore,
            rules=(NESTED_RUNS_IGNORE_RULE,),
            block_begin=NESTED_IGNORE_BLOCK_BEGIN,
            block_end=NESTED_IGNORE_BLOCK_END,
        )


def ensure_private_state_protected(repo: Path, run_id: str) -> str:
    """在任何私有定位信息落盘前，证明运行状态不会被 Git 收录。"""

    repository = git_root(repo)
    if repository is None:
        bootstrap_non_git_ignore(repo)
        return "non_git_gitignore_bootstrapped"

    candidates = (
        (
            repo / ".learning" / "runs" / run_id,
            f".learning/runs/{run_id}",
            PRIVATE_IGNORE_RULES["runs"],
        ),
        (repo / ".learning.lock", ".learning.lock", PRIVATE_IGNORE_RULES["lock"]),
    )
    missing = [
        (label, rule)
        for candidate, label, rule in candidates
        if not git_ignores(repository, candidate)
    ]
    if missing:
        repairs = "；".join(
            f"{label} 未忽略，请在 {repo / '.gitignore'} 添加 `{rule}`"
            for label, rule in missing
        )
        raise ContractError(f"私有学习状态未被 Git 忽略，已在写入前阻断：{repairs}")
    return "git_ignore_verified"


def source_contract(locator: str, source_id: str | None) -> dict[str, Any]:
    parsed = urlparse(locator)
    locator_hash = sha256_bytes(locator.encode("utf-8"))
    effective_id = source_id or f"source-{locator_hash[:12]}"
    validate_identifier(effective_id, "source-id")
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return {
            "kind": "url",
            "source_id": effective_id,
            "locator": locator,
            "locator_sha256": locator_hash,
            "media_sha256": None,
            "fingerprint_state": "provisional",
        }

    path = Path(locator).expanduser().resolve()
    if not path.is_file():
        raise ContractError(f"本地 source 不存在或不是文件：{locator}")
    return {
        "kind": "local_file",
        "source_id": effective_id,
        "private_locator": str(path),
        "locator_sha256": sha256_bytes(str(path).encode("utf-8")),
        "media_sha256": sha256_file(path),
        "fingerprint_state": "verified",
    }


def command_start(args: argparse.Namespace) -> dict[str, Any]:
    repo = resolve_repo(args.repo)
    validate_identifier(args.run_id, "run-id")
    if args.schema_version != SCHEMA_VERSION:
        raise ContractError(f"schema-version 必须是当前支持的 {SCHEMA_VERSION}")
    if args.workflow_version != WORKFLOW_VERSION:
        raise ContractError(f"workflow-version 必须是当前支持的 {WORKFLOW_VERSION}")
    if not WORKFLOW_PATH.is_file():
        raise ContractError("当前 Skill 缺少 references/workflow.json")
    privacy_guard = ensure_private_state_protected(repo, args.run_id)
    source = source_contract(args.source, args.source_id)
    run_dir = repo / ".learning" / "runs" / args.run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ContractError(f"run-id 已存在：{args.run_id}") from error

    try:
        for name in ("evidence", "frames", "logs"):
            (run_dir / name).mkdir()
        payload: dict[str, Any] = {
            "schema_version": args.schema_version,
            "workflow_version": args.workflow_version,
            "workflow_sha256": sha256_file(WORKFLOW_PATH),
            "run_id": args.run_id,
            "status": "running",
            "current_stage": "preflight",
            "next_stage": "ingest",
            "completed_stages": [],
            "invalidated_stages": [],
            "source": source,
            "artifacts": {},
            "bindings": [],
            "extensions": {
                "learning_loop": {
                    "required": True,
                    "state": "collecting",
                    "contract_version": LEARNING_CONTRACT_VERSION,
                    "selection": None,
                    "sidecars": {},
                }
            },
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        atomic_write_json(run_dir / "run.json", payload)
    except BaseException:
        for child in sorted(run_dir.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
            else:
                child.unlink()
        run_dir.rmdir()
        raise

    return {
        "ok": True,
        "run_id": args.run_id,
        "run_dir": str(run_dir.relative_to(repo)),
        "source_kind": source["kind"],
        "fingerprint_state": source["fingerprint_state"],
        "privacy_guard": privacy_guard,
    }


def demos_path(repo: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as error:
        raise ContractError("demos-dir 必须位于仓库内") from error
    if not resolved.is_dir():
        raise ContractError(f"demos-dir 不存在：{value}")
    return resolved


def used_demo_numbers(directory: Path) -> set[int]:
    numbers: set[int] = set()
    for item in directory.iterdir():
        if not item.is_dir():
            continue
        match = DEMO_RE.fullmatch(item.name)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def binding_paths(run_path: Path) -> tuple[Path, Path]:
    return run_path.parent / BIND_INTENT_NAME, run_path.parent / BIND_OWNER_NAME


def validate_intent(
    intent: dict[str, Any],
    *,
    repo: Path,
    demos: Path,
    run_id: str,
    slug: str,
) -> tuple[Path, int, str]:
    if intent.get("run_id") != run_id or intent.get("slug") != slug:
        raise ContractError("已有 bind-demo intent 与本次 run-id/slug 不一致")
    number = intent.get("number")
    relative = intent.get("relative_path")
    token = intent.get("token")
    if not isinstance(number, int) or number < 0:
        raise ContractError("binding-intent.number 非法")
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ContractError("binding-intent.relative_path 必须是仓库内相对路径")
    if not isinstance(token, str) or len(token) < 16:
        raise ContractError("binding-intent.token 非法")
    target = (repo / relative).resolve()
    expected_name = f"{number:0{len(Path(relative).name.split('-', 1)[0])}d}-{slug}"
    if target.parent != demos or target.name != expected_name:
        raise ContractError("binding-intent 的 Demo 路径与编号或 slug 不一致")
    return target, number, token


def ensure_owner_matches(
    owner: dict[str, Any], target: Path, relative: str, token: str
) -> None:
    if owner.get("token") != token or owner.get("relative_path") != relative:
        raise ContractError("binding-owner 与 intent 不一致")
    stat = target.stat()
    if owner.get("st_dev") != stat.st_dev or owner.get("st_ino") != stat.st_ino:
        raise ContractError("Demo 目录已被替换，拒绝恢复绑定")


def maybe_inject_fault(point: str) -> None:
    if os.environ.get(FAULT_ENV) == point:
        os.kill(os.getpid(), signal.SIGKILL)


def persist_binding_state(
    intent_path: Path,
    owner_path: Path,
    intent: dict[str, Any],
    owner: dict[str, Any],
    status: str,
) -> None:
    now = utc_now()
    intent.update({"status": status, "updated_at": now})
    owner.update({"status": status, "updated_at": now})
    atomic_write_json(intent_path, intent)
    atomic_write_json(owner_path, owner)


def command_bind_demo(args: argparse.Namespace) -> dict[str, Any]:
    repo = resolve_repo(args.repo)
    validate_identifier(args.run_id, "run-id")
    if not SLUG_RE.fullmatch(args.slug):
        raise ContractError("slug 只允许小写字母、数字和单连字符分段")
    if args.number_width < 1 or args.number_width > 6:
        raise ContractError("number-width 必须在 1 到 6 之间")
    if args.start_number < 0:
        raise ContractError("start-number 不能为负数")

    ensure_private_state_protected(repo, args.run_id)
    run_path = repo / ".learning" / "runs" / args.run_id / "run.json"
    demos = demos_path(repo, args.demos_dir)
    lock_path = repo / ".learning.lock"
    lock_path.touch(exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        run = read_json(run_path)
        completed = run.get("completed_stages")
        if not isinstance(completed, list) or "plan_demo" not in completed:
            raise ContractError("bind-demo 只能在 plan_demo 完成后执行")
        bindings = run.get("bindings")
        if not isinstance(bindings, list):
            raise ContractError("run.bindings 必须是数组")
        if bindings:
            binding = bindings[0] if len(bindings) == 1 else None
            if not isinstance(binding, dict) or binding.get("slug") != args.slug:
                raise ContractError(f"run-id 已绑定 Demo：{args.run_id}")
            relative = binding.get("relative_path")
            if not isinstance(relative, str):
                raise ContractError("已有 binding.relative_path 非法")
            target = (repo / relative).resolve()
            if target.parent != demos or not target.is_dir():
                raise ContractError("已有绑定的 Demo 目录不存在或不匹配 demos-dir")
            intent_path, owner_path = binding_paths(run_path)
            intent = read_optional_json(intent_path, "binding-intent") or {
                "transaction_version": 1,
                "run_id": args.run_id,
                "slug": args.slug,
                "number": binding.get("number"),
                "relative_path": relative,
                "token": secrets.token_hex(16),
                "created_at": utc_now(),
            }
            _, _, token = validate_intent(
                intent,
                repo=repo,
                demos=demos,
                run_id=args.run_id,
                slug=args.slug,
            )
            owner = read_optional_json(owner_path, "binding-owner") or {
                "transaction_version": 1,
                "run_id": args.run_id,
                "relative_path": relative,
                "token": token,
                "st_dev": target.stat().st_dev,
                "st_ino": target.stat().st_ino,
                "created_at": utc_now(),
            }
            ensure_owner_matches(owner, target, relative, token)
            persist_binding_state(
                intent_path, owner_path, intent, owner, "committed"
            )
            return {
                "ok": True,
                "run_id": args.run_id,
                "demo_dir": relative,
                **binding,
            }

        intent_path, owner_path = binding_paths(run_path)
        intent = read_optional_json(intent_path, "binding-intent")
        if intent is None:
            used = used_demo_numbers(demos)
            number = (
                max(max(used, default=args.start_number - 1), args.start_number - 1)
                + 1
            )
            directory_name = f"{number:0{args.number_width}d}-{args.slug}"
            target = demos / directory_name
            relative = str(target.relative_to(repo))
            intent = {
                "transaction_version": 1,
                "status": "reserved",
                "run_id": args.run_id,
                "slug": args.slug,
                "number": number,
                "relative_path": relative,
                "token": secrets.token_hex(16),
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            atomic_write_json(intent_path, intent)
        else:
            target, number, _ = validate_intent(
                intent,
                repo=repo,
                demos=demos,
                run_id=args.run_id,
                slug=args.slug,
            )
            relative = str(target.relative_to(repo))
            directory_name = target.name

        target, number, token = validate_intent(
            intent,
            repo=repo,
            demos=demos,
            run_id=args.run_id,
            slug=args.slug,
        )
        owner = read_optional_json(owner_path, "binding-owner")
        created = False
        if target.exists():
            if not target.is_dir():
                raise ContractError(f"Demo 路径不是目录：{target.name}")
            if owner is None:
                if any(target.iterdir()):
                    raise ContractError(
                        f"Demo 目录非空且没有 owner marker，拒绝接管：{target.name}"
                    )
            else:
                ensure_owner_matches(owner, target, relative, token)
        else:
            target.mkdir()
            created = True

        if created:
            maybe_inject_fault("kill_after_demo_mkdir")

        stat = target.stat()
        if owner is None:
            owner = {
                "transaction_version": 1,
                "status": "directory_created",
                "run_id": args.run_id,
                "relative_path": relative,
                "token": token,
                "st_dev": stat.st_dev,
                "st_ino": stat.st_ino,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            atomic_write_json(owner_path, owner)

        binding = {
            "number": number,
            "slug": args.slug,
            "relative_path": relative,
            "bound_at": utc_now(),
        }
        run["bindings"] = [binding]
        run["updated_at"] = utc_now()
        try:
            atomic_write_json(run_path, run)
            persist_binding_state(
                intent_path, owner_path, intent, owner, "committed"
            )
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    return {"ok": True, "run_id": args.run_id, "demo_dir": relative, **binding}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="初始化教程学习 run，或在规划后原子绑定 Demo 目录。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="创建仓库级私有 run")
    start.add_argument("--repo", required=True, help="目标仓库根目录")
    start.add_argument("--run-id", required=True, help="唯一 run ID")
    start.add_argument("--source", required=True, help="本地媒体文件或 HTTP(S) URL")
    start.add_argument("--source-id", help="脱敏 source ID")
    start.add_argument("--schema-version", default=SCHEMA_VERSION)
    start.add_argument("--workflow-version", default=WORKFLOW_VERSION)
    start.add_argument("--json", action="store_true", help="输出 JSON")
    start.set_defaults(handler=command_start)

    bind = subparsers.add_parser("bind-demo", help="规划后加锁分配 Demo 编号")
    bind.add_argument("--repo", required=True, help="目标仓库根目录")
    bind.add_argument("--run-id", required=True, help="已有 run ID")
    bind.add_argument("--slug", required=True, help="Demo slug")
    bind.add_argument("--demos-dir", default="demos", help="仓库内 Demo 父目录")
    bind.add_argument("--start-number", type=int, default=1)
    bind.add_argument("--number-width", type=int, default=2)
    bind.add_argument("--json", action="store_true", help="输出 JSON")
    bind.set_defaults(handler=command_bind_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except (ContractError, OSError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(result.get("demo_dir") or result.get("run_dir"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
