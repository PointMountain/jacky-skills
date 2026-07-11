#!/usr/bin/env python3
"""采集 Skill 的客观结构事实，不执行评分，也不修改目标文件。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote


IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "archived",
    "build",
    "dist",
    "node_modules",
}
RESOURCE_NAMES = ("references", "scripts", "assets", "tests", "templates", "agents")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def find_skill_files(target: Path) -> list[Path]:
    target = target.resolve()
    if target.is_file():
        return [target] if target.name == "SKILL.md" else []
    direct = target / "SKILL.md"
    if direct.is_file():
        return [direct]
    return sorted(path for path in target.rglob("SKILL.md") if not is_ignored(path))


def frontmatter_value(content: str, key: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return ""
    for index, line in enumerate(lines[1:end], 1):
        match = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if value in {"|", ">"}:
            block: list[str] = []
            for following in lines[index + 1 : end]:
                if following and not following[0].isspace():
                    break
                block.append(following.strip())
            return " ".join(item for item in block if item).strip()
        return value.strip("\"'")
    return ""


def count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file() and not is_ignored(path))


def markdown_destination(raw_target: str) -> str:
    value = raw_target.strip()
    if value.startswith("<"):
        closing = value.find(">")
        return value[1:closing] if closing > 0 else value.strip("<>")
    return value.split(maxsplit=1)[0]


def local_link_facts(skill_dir: Path) -> tuple[int, list[str]]:
    total = 0
    missing: list[str] = []
    for markdown in sorted(skill_dir.rglob("*.md")):
        if is_ignored(markdown):
            continue
        content = markdown.read_text(encoding="utf-8", errors="replace")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = markdown_destination(raw_target)
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            if "${" in target or target.startswith("{"):
                continue
            total += 1
            path_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            resolved = Path(path_part) if Path(path_part).is_absolute() else markdown.parent / path_part
            if not resolved.exists() and raw_target not in missing:
                missing.append(raw_target)
    return total, missing


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def collect_one(skill_file: Path, root: Path) -> dict[str, object]:
    skill_dir = skill_file.parent
    content = skill_file.read_text(encoding="utf-8", errors="replace")
    local_links, missing_local_links = local_link_facts(skill_dir)
    return {
        "name": frontmatter_value(content, "name") or skill_dir.name,
        "path": relative_display(skill_dir, root),
        "line_count": len(content.splitlines()),
        "non_empty_line_count": sum(1 for line in content.splitlines() if line.strip()),
        "description_length": len(frontmatter_value(content, "description")),
        "markdown_files": sum(
            1
            for path in skill_dir.rglob("*.md")
            if path.is_file() and not is_ignored(path)
        ),
        "resources": {name: count_files(skill_dir / name) for name in RESOURCE_NAMES},
        "local_links": local_links,
        "missing_local_links": missing_local_links,
    }


def render_text(payload: dict[str, object]) -> str:
    lines = ["name\tlines\tnon-empty\treferences\tscripts\ttests\tmissing-links\tpath"]
    for skill in payload["skills"]:  # type: ignore[index]
        resources = skill["resources"]
        lines.append(
            "\t".join(
                [
                    str(skill["name"]),
                    str(skill["line_count"]),
                    str(skill["non_empty_line_count"]),
                    str(resources["references"]),
                    str(resources["scripts"]),
                    str(resources["tests"]),
                    str(len(skill["missing_local_links"])),
                    str(skill["path"]),
                ]
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Skill 文件、Skill 目录或待扫描仓库")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    target = args.target.resolve()
    if not target.exists():
        parser.error(f"目标不存在：{target}")
    skill_files = find_skill_files(target)
    payload = {
        "root": target.as_posix(),
        "skills": [collect_one(path, target) for path in skill_files],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
