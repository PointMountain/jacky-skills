#!/usr/bin/env python3
"""审计指定 pathspec 的 Git index blob，阻止私有资产与真实凭证进入提交。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any


POSIX_HOME_PATTERN = (
    r"/" + r"(?:Users|home)/[^\s/\\\"'<>]+(?:/[^\r\n\"'<>]+)+"
)
WINDOWS_HOME_PATTERN = (
    r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]+"
    + r"Users[\\/]+[^\s/\\\"'<>]+(?:[\\/]+[^\r\n\"'<>]+)+"
)

# 高风险字面量刻意拆分，避免审计器扫描自身源码时产生假阳性。
TEXT_RULES = [
    (
        "home_path",
        re.compile(
            rf"(?:{POSIX_HOME_PATTERN}|{WINDOWS_HOME_PATTERN})", re.IGNORECASE
        ),
    ),
    (
        "authorization",
        re.compile(
            (r"authori" + r"zation\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"),
            re.IGNORECASE,
        ),
    ),
    (
        "sensitive_query",
        re.compile(
            (
                r"https?://[^\s\"'<>?]+\?[^\s\"'<>]*"
                r"(?:access[_-]?token|token|api[_-]?key|signature|sig)="
                r"[A-Za-z0-9_./+~%=-]{12,}"
            ),
            re.IGNORECASE,
        ),
    ),
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?" + r"PRIVATE KEY-----",
            re.IGNORECASE,
        ),
    ),
    (
        "github_token_fine_grained",
        re.compile(r"\bgithub" + r"_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "github_token",
        re.compile(r"\bg" + r"h[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "npm_token",
        re.compile(r"\bn" + r"pm_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "embedded_data_uri",
        re.compile(
            (
                r"\bda"
                + r"ta\s*:\s*(?:(?:image|audio|video)/[A-Za-z0-9.+-]+|"
                r"application/(?:octet-stream|pdf))"
                r"(?:;[A-Za-z0-9.+-]+(?:=[^,;\s]+)?)*\s*,"
            ),
            re.IGNORECASE,
        ),
    ),
    (
        "blob_uri",
        re.compile(r"\bbl" + r"ob\s*:[^\s\"')>]+", re.IGNORECASE),
    ),
    (
        "large_base64",
        re.compile(
            r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{256,}={0,2}"
            r"(?![A-Za-z0-9+/=])"
        ),
    ),
]

ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"(?P<key_quote>[\"'])(?P<quoted_name>[A-Za-z][A-Za-z0-9_-]*)(?P=key_quote)|"
    r"(?P<bare_name>[A-Za-z][A-Za-z0-9_-]*))\s*[:=]\s*"
    r'(?:"(?P<double>[^"\r\n]*)"|\'(?P<single>[^\'\r\n]*)\'|'
    r"(?P<bare>[^\s,;]+))"
)
EXACT_SENSITIVE_NAME_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|npm[_-]?token|"
    r"password|passwd|client[_-]?secret|private[_-]?key|pat)\Z",
    re.IGNORECASE,
)
PREFIXED_SENSITIVE_NAME_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9_]*_(?:PASSWORD|PASSWD|CLIENT_SECRET|SECRET_KEY|"
    r"SECRET_ACCESS_KEY|PRIVATE_KEY|ACCESS_TOKEN|REFRESH_TOKEN|API_KEY|TOKEN)\Z",
    re.IGNORECASE,
)
ENVIRONMENT_REFERENCE_RE = re.compile(
    r"(?:\$[A-Za-z_][A-Za-z0-9_]*|\$\{[A-Za-z_][A-Za-z0-9_]*\}|"
    r"\{\{[A-Za-z_][A-Za-z0-9_.-]*\}\})\Z"
)
DOCUMENTATION_PLACEHOLDER_RE = re.compile(
    r"<(?:REDACTED|REMOVED|YOUR(?:_[A-Z0-9_]+)?|PLACEHOLDER|EXAMPLE)>\Z",
    re.IGNORECASE,
)
COOKIE_HEADER_RE = re.compile(
    r"\b(?P<header>(?:set-)?coo" + r"kie)\s*:\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)

MEDIA_EXTENSIONS = {
    ".3gp",
    ".aac",
    ".aiff",
    ".avif",
    ".avi",
    ".bmp",
    ".flac",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ogg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
}

PUBLIC_FONT_PATH_RE = re.compile(
    r"(?:[A-Za-z0-9._-]+/)*assets/(?:public/)?fonts/"
    r"[A-Za-z0-9][A-Za-z0-9._-]*\.(?:woff2?|ttf|otf)\Z",
    re.IGNORECASE,
)
MAX_PUBLIC_FONT_BYTES = 2 * 1024 * 1024
FONT_MAGIC = {
    ".woff": (b"wOFF",),
    ".woff2": (b"wOF2",),
    ".ttf": (b"\x00\x01\x00\x00", b"true"),
    ".otf": (b"OTTO",),
}


class GitError(RuntimeError):
    """表示 Git 暂存区读取失败。"""


def run_git(repo: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git 命令失败")
    return result.stdout


def run_git_bytes(repo: Path, arguments: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(detail or "git 命令失败")
    return result.stdout


def staged_files(repo: Path, paths: list[str]) -> list[str]:
    output = run_git(
        repo,
        [
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMRT",
            "--",
            *paths,
        ],
    )
    return [line for line in output.splitlines() if line]


def index_blob(repo: Path, path: str) -> bytes:
    """直接读取 index 中的 blob，不信任可能已经变化的工作区文件。"""

    return run_git_bytes(repo, ["cat-file", "blob", f":{path}"])


def index_mode(repo: Path, path: str) -> str:
    """读取目标 path 当前暂存区条目的 mode，不信任工作区文件类型。"""

    output = run_git_bytes(repo, ["ls-files", "--stage", "-z", "--", path])
    records = [record for record in output.split(b"\0") if record]
    if len(records) != 1 or b"\t" not in records[0]:
        raise GitError(f"无法唯一确定 index 条目类型：{path}")
    metadata, _ = records[0].split(b"\t", 1)
    fields = metadata.split()
    if len(fields) != 3 or fields[2] != b"0":
        raise GitError(f"index 条目不是唯一 stage-0 记录：{path}")
    return fields[0].decode("ascii")


def finding(rule: str, path: str, line: int) -> dict[str, Any]:
    return {
        "rule": rule,
        "path": path,
        "line": line,
        "excerpt": f"[已隐藏：{rule}]",
    }


def safe_public_font(path: str, blob: bytes) -> bool:
    """只放行小型、魔数匹配且位于明确 public/fonts 路径的字体。"""

    if not PUBLIC_FONT_PATH_RE.fullmatch(path):
        return False
    suffix = PurePosixPath(path).suffix.lower()
    magics = FONT_MAGIC.get(suffix)
    if magics is None or not (48 <= len(blob) <= MAX_PUBLIC_FONT_BYTES):
        return False
    return any(blob.startswith(magic) for magic in magics)


def decode_text_blob(blob: bytes) -> str | None:
    if b"\x00" in blob:
        return None
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # UTF-8 文件也可能塞入大量控制字符；这种内容按二进制处理。
    if any(ord(char) < 32 and char not in "\t\n\r\f" for char in text):
        return None
    return text


def cookie_is_redacted(value: str) -> bool:
    normalized = value.strip().strip('"\'').strip().lower()
    return normalized in {"<redacted>", "[redacted]", "redacted", "<removed>"}


def credential_is_safe_reference(value: str) -> bool:
    normalized = value.strip()
    return bool(
        ENVIRONMENT_REFERENCE_RE.fullmatch(normalized)
        or DOCUMENTATION_PLACEHOLDER_RE.fullmatch(normalized)
        or normalized.lower() in {"<redacted>", "[redacted]", "redacted", "<removed>"}
    )


def credential_findings(path: str, line: str, line_number: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for match in ASSIGNMENT_RE.finditer(line):
        name = match.group("quoted_name") or match.group("bare_name")
        value = next(
            match.group(group)
            for group in ("double", "single", "bare")
            if match.group(group) is not None
        )
        exact = EXACT_SENSITIVE_NAME_RE.fullmatch(name)
        prefixed = PREFIXED_SENSITIVE_NAME_RE.fullmatch(name)
        if not (exact or prefixed):
            continue
        if credential_is_safe_reference(value):
            continue
        rule = "secret_assignment" if exact else "credential_assignment"
        found.append(finding(rule, path, line_number))
    return found


def text_findings(path: str, text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in TEXT_RULES:
            if pattern.search(line):
                found.append(finding(rule, path, line_number))
        found.extend(credential_findings(path, line, line_number))
        cookie = COOKIE_HEADER_RE.search(line)
        if cookie and not cookie_is_redacted(cookie.group("value")):
            rule = (
                "set_cookie_header"
                if cookie.group("header").lower().startswith("set-")
                else "cookie_header"
            )
            found.append(finding(rule, path, line_number))
    return found


def audit(repo: Path, paths: list[str]) -> dict[str, Any]:
    files = staged_files(repo, paths)
    errors: list[str] = []
    findings: list[dict[str, Any]] = []
    scanned_lines = 0
    if not files:
        errors.append("指定 paths 中未暂存任何文件；拒绝空暂存假绿")
        return {
            "ok": False,
            "staged_files": [],
            "scanned_added_lines": 0,
            "scanned_index_lines": 0,
            "findings": [],
            "errors": errors,
        }

    for path in files:
        mode = index_mode(repo, path)
        if mode not in {"100644", "100755"}:
            findings.append(finding("non_regular_index_entry", path, 0))
            continue
        blob = index_blob(repo, path)
        suffix = PurePosixPath(path).suffix.lower()

        # 媒体扩展名即使内容伪装成文本或 Git LFS 指针，也默认拒绝。
        if suffix in MEDIA_EXTENSIONS:
            findings.append(finding("media_asset", path, 0))
            continue

        # 二进制默认拒绝；唯一内建例外是精确 public/fonts 策略。
        if safe_public_font(path, blob):
            continue
        text = decode_text_blob(blob)
        if text is None:
            findings.append(finding("binary_asset", path, 0))
            continue

        lines = text.splitlines()
        scanned_lines += len(lines)
        findings.extend(text_findings(path, text))

    if findings:
        errors.append(f"Git index blob 中发现 {len(findings)} 个隐私、凭证或资产风险")
    return {
        "ok": not errors,
        "staged_files": files,
        # 保留旧字段，避免已有调用方破坏；语义已升级为完整 index 文本行数。
        "scanned_added_lines": scanned_lines,
        "scanned_index_lines": scanned_lines,
        "findings": findings,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="审计指定 pathspec 的完整 Git index blob；没有目标暂存文件时失败。"
    )
    parser.add_argument("--repo", default=".", help="Git 仓库根目录，默认当前目录")
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="只审计这些 Git pathspec，不读取范围外的用户改动",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).expanduser().resolve()
    try:
        result = audit(repo, args.paths)
    except (GitError, OSError) as error:
        result = {
            "ok": False,
            "staged_files": [],
            "scanned_added_lines": 0,
            "scanned_index_lines": 0,
            "findings": [],
            "errors": [str(error)],
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
