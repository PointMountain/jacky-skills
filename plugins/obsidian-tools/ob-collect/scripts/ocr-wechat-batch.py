#!/usr/bin/env python3
"""ob-collect 微信批量采集的 OCR 阶段工具（解耦设计）。

本脚本只负责文件层操作：扫描待 OCR 任务、应用 OCR 结果、翻转 status。
OCR 调用本身（多模态模型）由调用方在主会话中完成（Read 工具 / Anthropic API /
本地 mlx-vlm），通过 JSON 任务文件交接。

## 用法

### scan：扫描待 OCR 任务，输出 JSON 任务清单

```bash
python3 ocr-wechat-batch.py scan \
  --raw-dir <vault>/raw/wechat/ETF网格交易 \
  --output tasks.json \
  [--limit-md 10] [--limit-images-per-md 5]
```

输出 JSON 结构：
```json
{
  "tasks": [
    {
      "md_path": "/abs/path/2026-05-19-ETF网格交易.md",
      "images": [
        {"index": 1, "wikilink": "attachments/2026-05-19-ETF网格交易/img_001.jpeg",
         "abs_path": "/abs/.../img_001.jpeg"},
        ...
      ]
    },
    ...
  ]
}
```

### apply-noop：用 `[pending OCR]` 占位填充所有 TODO，方便骨架生成

```bash
python3 ocr-wechat-batch.py apply-noop --task-json tasks.json
```

### apply：传入 OCR 结果 JSON，写回 md 文件，翻转 status

```bash
python3 ocr-wechat-batch.py apply --result-json results.json
```

results.json 结构：
```json
{
  "results": [
    {
      "md_path": "...",
      "ocr": [
        {"index": 1, "text": "OCR 识别出的文字内容（多行支持）"},
        {"index": 2, "text": "..."}
      ]
    }
  ]
}
```

apply 行为：
- 把 `<!-- TODO OCR -->\n![[...]]` 替换为 `> [!note] OCR · 图片NNN\n> {text}\n\n![[...]]`
- 当某 md 所有 TODO 都被替换 → 翻转 frontmatter status: uncompiled → compiled

## 设计说明

- **幂等**：scan 跳过 status: compiled 的 md；apply 跳过已无 TODO 的 md
- **失败安全**：apply 先写临时文件再 rename，崩溃不会损坏原 md
- **可分批**：scan 支持 limit；apply 可以多次跑（每次处理部分图片）
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


# Frontmatter 检测
FM_PAT = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# TODO OCR + 紧跟 wikilink 的两行块
# group 1 = wikilink 完整文本 attachments/.../img_NNN.jpeg
TODO_BLOCK_PAT = re.compile(
    r"<!-- TODO OCR -->\n!\[\[(attachments/[^\]]+)\]\]"
)

# 已应用 OCR callout 的检测（避免重复处理）
APPLIED_CALLOUT_PAT = re.compile(
    r"> \[!note\] OCR · 图片(\d+)\n((?:> .*\n)+)\n!\[\[(attachments/[^\]]+)\]\]"
)


def parse_frontmatter(content):
    """返回 (fm_dict_text, body_start_index)。"""
    m = FM_PAT.match(content)
    if not m:
        return None, 0
    return m.group(1), m.end()


def get_status(content):
    fm, _ = parse_frontmatter(content)
    if not fm:
        return None
    m = re.search(r"^status:\s*(\S+)\s*$", fm, re.MULTILINE)
    return m.group(1) if m else None


def set_status(content, new_status):
    fm, body_start = parse_frontmatter(content)
    if fm is None:
        return content
    new_fm = re.sub(
        r"^status:\s*\S+\s*$",
        f"status: {new_status}",
        fm,
        flags=re.MULTILINE,
    )
    return f"---\n{new_fm}\n---\n" + content[body_start:]


def extract_image_tasks(md_path: Path):
    """扫描 md 中所有 <!-- TODO OCR --> 块，返回 [(index, wikilink_rel, abs_path)]。"""
    content = md_path.read_text(encoding="utf-8")
    tasks = []
    for i, m in enumerate(TODO_BLOCK_PAT.finditer(content), 1):
        wikilink_rel = m.group(1)
        # wikilink 是相对 md 同目录的，转绝对路径
        abs_path = md_path.parent / wikilink_rel
        tasks.append({
            "index": i,
            "wikilink": wikilink_rel,
            "abs_path": str(abs_path),
        })
    return tasks


def cmd_scan(args):
    raw_dir = Path(args.raw_dir).resolve()
    if not raw_dir.is_dir():
        sys.exit(f"raw-dir not a directory: {raw_dir}")

    tasks = []
    md_count = 0
    md_files = sorted(p for p in raw_dir.glob("*.md") if p.name != "index.md")
    for md_path in md_files:
        if args.limit_md and md_count >= args.limit_md:
            break
        content = md_path.read_text(encoding="utf-8")
        status = get_status(content)
        if status != "uncompiled":
            continue  # already compiled or no status field
        images = extract_image_tasks(md_path)
        if not images:
            continue
        if args.limit_images_per_md:
            images = images[: args.limit_images_per_md]
        tasks.append({
            "md_path": str(md_path),
            "images": images,
        })
        md_count += 1

    output = {"tasks": tasks, "total_md": len(tasks),
              "total_images": sum(len(t["images"]) for t in tasks)}
    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scanned: {len(tasks)} md, {output['total_images']} images → {out_path}")


def replace_todo_block(content, image_index, ocr_text, wikilink_rel):
    """替换第 image_index 个 TODO 块为 [!note] callout。

    Note: image_index 是按 TODO 块在文档中出现的顺序（1-based），
    这与 scan 输出的 index 一致。
    """
    # 收集所有 TODO 块的位置
    matches = list(TODO_BLOCK_PAT.finditer(content))
    if image_index < 1 or image_index > len(matches):
        return content, False
    target = matches[image_index - 1]
    if target.group(1) != wikilink_rel:
        # wikilink 不匹配，可能 md 已被改动过，保护性跳过
        return content, False

    # 多行 OCR 文字转为 callout 行
    callout_lines = "\n".join(
        f"> {line}" if line else ">"
        for line in (ocr_text or "[pending OCR]").splitlines()
    )
    replacement = (
        f"> [!note] OCR · 图片{image_index:03d}\n"
        f"{callout_lines}\n\n"
        f"![[{wikilink_rel}]]"
    )
    new_content = content[: target.start()] + replacement + content[target.end():]
    return new_content, True


def apply_md_results(md_path: Path, ocr_list, noop_text=None):
    """对单个 md 应用 OCR 结果。ocr_list = [{"index": N, "text": "..."}].

    若 noop_text 不为 None，则忽略 ocr_list，把所有 TODO 用 noop_text 替换（noop 模式）。
    """
    content = md_path.read_text(encoding="utf-8")
    # 收集当前所有 TODO 块的 wikilink
    matches = list(TODO_BLOCK_PAT.finditer(content))
    if not matches:
        return ("no_todo", 0)

    applied = 0
    if noop_text is not None:
        # noop 模式：批量替换全部
        # 从后往前替换避免索引位移
        for i in range(len(matches), 0, -1):
            wl = matches[i - 1].group(1)
            content, ok = replace_todo_block(content, i, noop_text, wl)
            if ok:
                applied += 1
    else:
        # 真 OCR 模式
        for entry in sorted(ocr_list, key=lambda x: x["index"], reverse=True):
            i = entry["index"]
            text = entry.get("text", "")
            # 重新计算 matches（因为前面替换可能影响位置）
            matches_now = list(TODO_BLOCK_PAT.finditer(content))
            if not matches_now or i > len(matches_now):
                continue
            wl = matches_now[i - 1].group(1)
            content, ok = replace_todo_block(content, i, text, wl)
            if ok:
                applied += 1

    # 检查是否还剩 TODO；若全部处理完，翻转 status
    remaining = len(TODO_BLOCK_PAT.findall(content))
    if remaining == 0:
        content = set_status(content, "compiled")

    # 原子写入
    tmp = md_path.with_suffix(md_path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(md_path)
    return ("ok", applied) if applied else ("skip", 0)


def cmd_apply(args):
    data = json.loads(Path(args.result_json).read_text(encoding="utf-8"))
    results = data.get("results", [])
    stats = {"ok": 0, "skip": 0, "no_todo": 0, "missing": 0}
    for r in results:
        md_path = Path(r["md_path"])
        if not md_path.exists():
            stats["missing"] += 1
            continue
        status, applied = apply_md_results(md_path, r.get("ocr", []))
        stats[status] = stats.get(status, 0) + 1
    print(f"Apply done: {stats}")


def cmd_apply_noop(args):
    data = json.loads(Path(args.task_json).read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    stats = {"ok": 0, "skip": 0, "no_todo": 0}
    for t in tasks:
        md_path = Path(t["md_path"])
        status, applied = apply_md_results(md_path, [], noop_text="[pending OCR]")
        stats[status] = stats.get(status, 0) + 1
    print(f"Apply-noop done: {stats}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="扫描待 OCR 任务输出 JSON")
    p_scan.add_argument("--raw-dir", required=True, help="raw/wechat/{author}/ 目录")
    p_scan.add_argument("--output", required=True, help="任务 JSON 输出路径")
    p_scan.add_argument("--limit-md", type=int, default=None)
    p_scan.add_argument("--limit-images-per-md", type=int, default=None)
    p_scan.set_defaults(func=cmd_scan)

    p_apply = sub.add_parser("apply", help="应用 OCR 结果（真 OCR 文字）")
    p_apply.add_argument("--result-json", required=True)
    p_apply.set_defaults(func=cmd_apply)

    p_noop = sub.add_parser("apply-noop", help="用 [pending OCR] 占位填充全部 TODO（骨架）")
    p_noop.add_argument("--task-json", required=True)
    p_noop.set_defaults(func=cmd_apply_noop)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
