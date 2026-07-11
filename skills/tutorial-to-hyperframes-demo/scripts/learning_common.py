#!/usr/bin/env python3
"""教程学习闭环共享的确定性与隐私安全原语。"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import time
from typing import Any
import unicodedata
from urllib.parse import parse_qsl, unquote, urlsplit


_SLASH_TRANSLATION = str.maketrans(
    {
        "\u2044": "/",  # fraction slash
        "\u2215": "/",  # division slash
        "\u29f8": "\\",  # big solidus
        "\uff0f": "/",  # fullwidth solidus
        "\uff3c": "\\",  # fullwidth reverse solidus
    }
)
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_WINDOWS_HOME_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+",
    re.IGNORECASE,
)
_POSIX_HOME_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:Users|home)/[^/\s]+", re.IGNORECASE
)
_BOUNDARY_POSIX_ABSOLUTE_RE = re.compile(
    r"(?<![A-Za-z0-9._~-])/(?!/)[^/\s<>\"']+(?:/[^\s<>\"']+)*"
)
_BOUNDARY_HOME_RELATIVE_RE = re.compile(
    r"(?<![A-Za-z0-9._~-])~(?:[A-Za-z0-9._-]+)?[\\/]"
)
_EMBEDDED_WINDOWS_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]+[^\\/\s<>\"']+"
    r"(?:[\\/]+[^\s<>\"']+)+"
)
_AUTH_HEADER_RE = re.compile(r"\bauthorization\s*:\s*\S+", re.IGNORECASE)
_COOKIE_HEADER_RE = re.compile(r"\b(?:set-)?cookie\s*:\s*\S+", re.IGNORECASE)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:access[_-]?token|refresh[_-]?token|api[_-]?key|"
    r"client[_-]?secret|private[_-]?key|password|passwd|credential|cookie)"
    r"\s*[:=]\s*[^\s,;&]+",
    re.IGNORECASE,
)
_KNOWN_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"npm_[A-Za-z0-9]{20,})\b"
)
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(
    os, "O_CLOEXEC", 0
)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_LINK_WINDOW_ATTEMPTS = 8
_LINK_WINDOW_DELAY_SECONDS = 0.005
_URL_DECODE_ROUNDS = 4


class _MultipleLinksError(ValueError):
    """表示文件当前有多个 hardlink，可能是短暂 publish 窗口。"""


def _normalize_json(value: Any, *, location: str = "$") -> Any:
    """递归生成只含原生 JSON 类型且 NFC 规范化的副本。"""

    if value is None or type(value) is bool or type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{location} 包含非有限浮点数")
        return value
    if type(value) is str:
        return unicodedata.normalize("NFC", value)
    if type(value) is list:
        return [
            _normalize_json(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        normalized: dict[str, Any] = {}
        original_keys: dict[str, str] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{location} 的 JSON 对象键必须是字符串")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                first = original_keys[normalized_key]
                raise ValueError(
                    f"{location} 的键在 NFC 规范化后冲突：{first!r} 与 {key!r}"
                )
            original_keys[normalized_key] = key
            normalized[normalized_key] = _normalize_json(
                item, location=f"{location}.{normalized_key}"
            )
        return normalized
    raise TypeError(f"{location} 包含非 JSON 类型：{type(value).__name__}")


def _security_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).translate(_SLASH_TRANSLATION)


def _sensitive_key(key: str) -> bool:
    name = re.sub(r"[-\s]+", "_", _security_text(key).casefold())
    if name in {
        "authorization",
        "cookie",
        "set_cookie",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "client_secret",
        "private_key",
        "password",
        "passwd",
        "credential",
        "credentials",
        "private_locator",
    }:
        return True
    return bool(
        re.search(
            r"(?:^|_)(?:access_token|refresh_token|api_key|client_secret|"
            r"private_key|password|passwd|credential|cookie|token)$",
            name,
        )
    )


def _decode_url_security_component(value: str) -> str:
    current = value
    for _ in range(_URL_DECODE_ROUNDS):
        decoded = _security_text(unquote(current))
        if decoded == current:
            break
        current = decoded
    return current.replace(";", "&")


def _reject_sensitive_url(value: str) -> None:
    for raw_url in _URL_RE.findall(value):
        parsed = urlsplit(raw_url)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("payload 包含 URL credential")
        decoded_query = _decode_url_security_component(parsed.query)
        decoded_fragment = _decode_url_security_component(parsed.fragment)
        pairs = parse_qsl(decoded_query, keep_blank_values=True)
        pairs.extend(parse_qsl(decoded_fragment, keep_blank_values=True))
        for key, _ in pairs:
            normalized_key = re.sub(
                r"[-\s]+", "_", _security_text(key).casefold()
            )
            if _sensitive_key(key) or re.search(
                r"(?:^|_)(?:signature|sig)$", normalized_key
            ):
                raise ValueError("payload 包含敏感 URL query/fragment")
        if re.search(
            r"(?:^|[?&#;])(?:access[_-]?token|refresh[_-]?token|api[_-]?key|"
            r"client[_-]?secret|signature|sig|credential|password|cookie)\s*=",
            f"{decoded_query}&{decoded_fragment}",
            re.IGNORECASE,
        ):
            raise ValueError("payload 包含敏感 URL query/fragment")


def _reject_sensitive_string(value: str) -> None:
    security_value = _security_text(value)
    _reject_sensitive_url(security_value)
    path_scan = _URL_RE.sub("", security_value)
    if _POSIX_HOME_RE.search(path_scan) or _WINDOWS_HOME_RE.search(
        path_scan
    ):
        raise ValueError("payload 包含用户主目录绝对路径")
    if _BOUNDARY_POSIX_ABSOLUTE_RE.search(
        path_scan
    ) or _EMBEDDED_WINDOWS_PATH_RE.search(path_scan):
        raise ValueError("payload 包含绝对路径")
    if _BOUNDARY_HOME_RELATIVE_RE.search(path_scan):
        raise ValueError("payload 包含 home-relative 路径")
    stripped = path_scan.strip()
    if (
        stripped.startswith(("~/", "~\\", "//", "\\\\"))
        or _WINDOWS_DRIVE_RE.match(stripped)
        or stripped.startswith("/")
    ):
        raise ValueError("payload 包含绝对路径")
    if _AUTH_HEADER_RE.search(security_value):
        raise ValueError("payload 包含 Authorization")
    if _COOKIE_HEADER_RE.search(security_value):
        raise ValueError("payload 包含 Cookie")
    if _PRIVATE_KEY_RE.search(security_value):
        raise ValueError("payload 包含私钥")
    if _SECRET_ASSIGNMENT_RE.search(security_value) or _KNOWN_TOKEN_RE.search(
        security_value
    ):
        raise ValueError("payload 包含凭证")


def _require_secure_dir_fd_support() -> None:
    if not _NOFOLLOW or not getattr(os, "O_DIRECTORY", 0):
        raise OSError("当前平台缺少安全目录遍历所需的 O_NOFOLLOW/O_DIRECTORY")


def _absolute_path(path: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return Path(os.path.abspath(os.fspath(candidate)))


def _raise_component_error(error: OSError, path: Path) -> None:
    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
        raise ValueError(f"路径组件不是无 symlink 的目录：{path}") from error
    raise error


def _open_absolute_directory(path: Path, *, create: bool) -> int:
    """从 `/` 逐组件打开目录；既不解析也不跟随任一 symlink。"""

    _require_secure_dir_fd_support()
    absolute = _absolute_path(path)
    descriptor = os.open("/", _DIRECTORY_FLAGS | _NOFOLLOW)
    try:
        current_path = Path("/")
        for component in absolute.parts[1:]:
            current_path /= component
            try:
                child = os.open(
                    component,
                    _DIRECTORY_FLAGS | _NOFOLLOW,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                    _fsync_directory(descriptor)
                except FileExistsError:
                    pass
                try:
                    child = os.open(
                        component,
                        _DIRECTORY_FLAGS | _NOFOLLOW,
                        dir_fd=descriptor,
                    )
                except OSError as error:
                    _raise_component_error(error, current_path)
            except OSError as error:
                _raise_component_error(error, current_path)
            try:
                os.close(descriptor)
            except BaseException:
                os.close(child)
                raise
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_parent_directory(path: Path, *, create: bool) -> tuple[int, str, Path]:
    absolute = _absolute_path(path)
    if absolute == Path("/") or absolute.name in {"", ".", ".."}:
        raise ValueError("JSON 目标必须是带文件名的路径")
    descriptor = _open_absolute_directory(absolute.parent, create=create)
    return descriptor, absolute.name, absolute


def _fsync_directory(descriptor: int) -> None:
    os.fsync(descriptor)


def _lstat_entry(directory_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _reject_non_regular_or_symlink(entry: os.stat_result, label: str) -> None:
    if stat.S_ISLNK(entry.st_mode):
        raise ValueError(f"{label} 不能是 symlink")
    if not stat.S_ISREG(entry.st_mode):
        raise ValueError(f"{label} 必须是普通文件")


def _unlink_and_fsync(directory_fd: int, name: str) -> bool:
    try:
        os.unlink(name, dir_fd=directory_fd)
    except FileNotFoundError:
        return False
    _fsync_directory(directory_fd)
    return True


def _write_all(descriptor: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(descriptor, content[offset:])
        if written <= 0:
            raise OSError("写入临时 JSON 时没有取得进展")
        offset += written


def _create_temp_file(directory_fd: int, leaf: str, content: bytes) -> str:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | _NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    for _ in range(128):
        name = f".{leaf}.{secrets.token_hex(12)}.tmp"
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            continue
        try:
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise ValueError("新建临时 JSON 不是单链接普通文件")
                _write_all(descriptor, content)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except BaseException:
            _unlink_and_fsync(directory_fd, name)
            raise
        return name
    raise FileExistsError("无法分配唯一的临时 JSON 文件名")


def _read_single_link_regular(
    directory_fd: int, name: str, *, label: str
) -> bytes | None:
    before = _lstat_entry(directory_fd, name)
    if before is None:
        return None
    _reject_non_regular_or_symlink(before, label)
    if before.st_nlink != 1:
        raise _MultipleLinksError(f"{label} 必须是单链接普通文件")

    flags = os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        _raise_component_error(error, Path(name))
    try:
        opened = os.fstat(descriptor)
        if opened.st_nlink != 1:
            raise _MultipleLinksError(f"{label} 在 open 时不是单链接文件")
        if not stat.S_ISREG(opened.st_mode) or (
            opened.st_dev,
            opened.st_ino,
        ) != (before.st_dev, before.st_ino):
            raise ValueError(f"{label} 在 lstat/open 之间发生变化")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if after.st_nlink != 1:
            raise _MultipleLinksError(f"{label} 在读取时不是单链接文件")
        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ):
            raise ValueError(f"{label} 在读取期间发生变化")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_after_link_window(
    directory_fd: int, name: str, *, label: str
) -> bytes | None:
    for attempt in range(_LINK_WINDOW_ATTEMPTS):
        try:
            return _read_single_link_regular(directory_fd, name, label=label)
        except _MultipleLinksError:
            if attempt == _LINK_WINDOW_ATTEMPTS - 1:
                raise
            time.sleep(_LINK_WINDOW_DELAY_SECONDS)
    raise AssertionError("不可达的 hardlink 重试状态")


def canonical_json_bytes(value: Any) -> bytes:
    """返回 NFC、键排序、紧凑分隔且恰有一个末尾换行的 UTF-8 JSON。"""

    normalized = _normalize_json(value)
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return encoded + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def secure_run_relative(run_dir: Path, value: str, *, must_exist: bool) -> Path:
    if type(value) is not str:
        raise TypeError("run-relative path 必须是字符串")
    if not value or not value.strip() or value != value.strip() or "\x00" in value:
        raise ValueError("run-relative path 不能为空、含 NUL 或首尾空白")
    security_value = _security_text(value)
    if (
        security_value.startswith(("/", "\\", "~"))
        or _WINDOWS_DRIVE_RE.match(security_value)
        or "\\" in security_value
    ):
        raise ValueError("run-relative path 不能是绝对、home 或 Windows 路径")
    original_parts = unicodedata.normalize("NFC", value).split("/")
    security_parts = security_value.split("/")
    if len(original_parts) != len(security_parts) or any(
        part in {"", ".", ".."} for part in (*original_parts, *security_parts)
    ):
        raise ValueError("run-relative path 含空、点或父目录组件")

    root = _absolute_path(Path(run_dir))
    try:
        descriptor = _open_absolute_directory(root, create=False)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"run 根目录不存在：{run_dir}") from error

    try:
        candidate = root.joinpath(*original_parts)
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError("run-relative path 越界") from error
        for index, part in enumerate(original_parts):
            entry = _lstat_entry(descriptor, part)
            is_final = index == len(original_parts) - 1
            if entry is None:
                if must_exist:
                    raise FileNotFoundError(f"run-relative path 不存在：{value}")
                return candidate
            if stat.S_ISLNK(entry.st_mode):
                raise ValueError("run-relative path 不能经过 symlink")
            if is_final:
                return candidate
            if not stat.S_ISDIR(entry.st_mode):
                raise ValueError("run-relative path 的中间组件必须是目录")
            try:
                child = os.open(
                    part,
                    _DIRECTORY_FLAGS | _NOFOLLOW,
                    dir_fd=descriptor,
                )
            except OSError as error:
                _raise_component_error(error, root / part)
            try:
                os.close(descriptor)
            except BaseException:
                os.close(child)
                raise
            descriptor = child
        return candidate
    finally:
        os.close(descriptor)


def reject_private_payload(value: Any) -> None:
    """递归拒绝不应进入长期 memory 或公开工件的路径与凭证。"""

    normalized = _normalize_json(value)

    def visit(item: Any) -> None:
        if type(item) is dict:
            for key, child in item.items():
                if _sensitive_key(key):
                    raise ValueError(f"payload 包含敏感字段：{key}")
                _reject_sensitive_string(key)
                visit(child)
        elif type(item) is list:
            for child in item:
                visit(child)
        elif type(item) is str:
            _reject_sensitive_string(item)

    visit(normalized)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    if type(value) is not dict:
        raise TypeError("JSON 文件顶层必须是对象")
    content = canonical_json_bytes(value)
    directory_fd, leaf, _ = _open_parent_directory(Path(path), create=True)
    temp_name: str | None = None
    try:
        existing = _lstat_entry(directory_fd, leaf)
        if existing is not None:
            _reject_non_regular_or_symlink(existing, "JSON 目标")
        temp_name = _create_temp_file(directory_fd, leaf, content)
        os.replace(
            temp_name,
            leaf,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        temp_name = None
        _fsync_directory(directory_fd)
    finally:
        try:
            if temp_name is not None:
                _unlink_and_fsync(directory_fd, temp_name)
        finally:
            os.close(directory_fd)


def write_immutable_or_adopt(path: Path, value: dict[str, Any]) -> None:
    if type(value) is not dict:
        raise TypeError("JSON 文件顶层必须是对象")
    content = canonical_json_bytes(value)
    directory_fd, leaf, absolute = _open_parent_directory(Path(path), create=True)
    temp_name: str | None = None
    try:
        existing = _read_after_link_window(
            directory_fd, leaf, label="不可变 JSON"
        )
        if existing is not None:
            if existing == content:
                return
            raise FileExistsError(f"不可变 JSON 已存在且内容不同：{absolute}")

        temp_name = _create_temp_file(directory_fd, leaf, content)
        try:
            os.link(
                temp_name,
                leaf,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            _unlink_and_fsync(directory_fd, temp_name)
            temp_name = None
            try:
                winner = _read_after_link_window(
                    directory_fd, leaf, label="并发写入的不可变 JSON"
                )
            except _MultipleLinksError:
                raise
            except ValueError as error:
                raise FileExistsError(
                    f"不可变 JSON 已被并发占用：{absolute}"
                ) from error
            if winner == content:
                return
            raise FileExistsError(
                f"不可变 JSON 已被并发写入不同内容：{absolute}"
            )

        _unlink_and_fsync(directory_fd, temp_name)
        temp_name = None
    finally:
        try:
            if temp_name is not None:
                _unlink_and_fsync(directory_fd, temp_name)
        finally:
            os.close(directory_fd)
