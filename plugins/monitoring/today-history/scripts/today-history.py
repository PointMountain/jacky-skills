#!/usr/bin/env python3
"""
快速过滤 Claude Code 会话记录（按日期）
通过读取本地 JSONL 文件提取指定日期的工作内容，无需大模型分析。

用法:
  python3 today-history.py                       # 查看今天（当前项目）
  python3 today-history.py --all                 # 查看今天（所有项目）
  python3 today-history.py --all --summary       # 全项目汇总（一行一条工作）
  python3 today-history.py --all --ticktick      # 输出滴答清单 JSON
  python3 today-history.py --project /path/to/prj # 查看指定项目今天
  python3 today-history.py --yesterday           # 查看昨天
  python3 today-history.py --date 2026-04-04     # 查看指定日期
  python3 today-history.py --all --yesterday     # 所有项目昨天
"""

import json
import os
import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC8 = timezone(timedelta(hours=8))

# Claude 项目会话存储根目录
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


# ─── 路径工具 ───────────────────────────────────────────────


def encode_path(path):
    """将路径编码为 Claude 项目目录名。/Users/jiashengwang → -Users-jiashengwang"""
    return path.replace("/", "-")


def get_cwd_from_project_dir(project_dir):
    """从项目目录的 JSONL 文件中读取实际工作目录（cwd）。

    遍历每个 JSONL 文件的前 50 行，提取 cwd 字段。
    找到 cwd 后立即返回，避免不必要的文件读取。
    """
    jsonl_files = sorted(project_dir.glob("*.jsonl"))
    for fpath in jsonl_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                line_count = 0
                for line in f:
                    line_count += 1
                    if line_count > 50:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    # 顶层 cwd 字段（progress/summary 等类型都有）
                    cwd = obj.get("cwd", "")
                    if cwd:
                        return cwd
                    # 也检查 message 里的 cwd
                    msg = obj.get("message", {})
                    if isinstance(msg, dict):
                        cwd = msg.get("cwd", "")
                        if cwd:
                            return cwd
        except (json.JSONDecodeError, OSError):
            continue
    return None


def decode_project_dir(project_dir):
    """将项目目录解码为可读的项目名。

    优先从 JSONL 文件获取真实 cwd，回退为编码名。
    """
    home = str(Path.home())
    encoded = project_dir.name

    # 尝试从 JSONL 头部获取 cwd
    cwd = get_cwd_from_project_dir(project_dir)
    if cwd:
        if cwd.startswith(home):
            return cwd.replace(home, "~", 1)
        return cwd

    # 回退: 直接用编码名
    return encoded


def get_all_project_dirs():
    """获取 ~/.claude/projects/ 下所有项目目录，返回 [(编码名, 可读名, 路径)]"""
    if not CLAUDE_PROJECTS_DIR.is_dir():
        return []
    projects = []
    for d in CLAUDE_PROJECTS_DIR.iterdir():
        if d.is_dir() and d.name.startswith("-"):
            readable = decode_project_dir(d)
            projects.append((d.name, readable, d))
    return projects


def get_sessions_dir_by_project(project_path):
    """根据指定的项目路径定位 Claude 会话目录。"""
    encoded = encode_path(os.path.abspath(project_path))
    d = CLAUDE_PROJECTS_DIR / encoded
    return d if d.is_dir() else None


def get_sessions_dir_cwd():
    """根据当前工作目录定位 Claude 会话目录。"""
    return get_sessions_dir_by_project(os.getcwd())


# ─── 日期解析 ───────────────────────────────────────────────


def parse_date_arg():
    """解析日期参数，默认今天。"""
    if "--yesterday" in sys.argv:
        return (datetime.now(UTC8) - timedelta(days=1)).strftime("%Y-%m-%d")
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return datetime.now(UTC8).strftime("%Y-%m-%d")


def get_utc_range(date_str):
    """本地日期 → UTC 时间范围（用于 JSONL 内部时间戳比对）。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC8)
    start = dt.astimezone(timezone.utc)
    end = (dt + timedelta(days=1)).astimezone(timezone.utc)
    return start, end


# ─── 时间工具 ───────────────────────────────────────────────


def in_range(ts_str, start, end):
    """判断时间戳是否在 UTC 范围内。"""
    ts = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    return start <= dt < end


def to_local(ts_str):
    """UTC 时间戳转本地时间字符串。"""
    ts = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts).astimezone(UTC8).strftime("%H:%M")


# ─── 内容提取 ───────────────────────────────────────────────


def extract_user_text(content):
    """提取用户实际输入，过滤 skill 加载内容。"""
    if isinstance(content, str):
        # 命令触发消息: <command-args>...</command-args>
        m = re.search(r"<command-args>(.*?)</command-args>", content, re.DOTALL)
        if m:
            cmd = re.search(r"<command-name>(.*?)</command-name>", content)
            prefix = cmd.group(1) if cmd else ""
            return f"{prefix} {m.group(1).strip()}".strip()
        # 跳过超长内容（通常是 skill 全文加载）
        if len(content) > 500:
            return None
        return content.strip()[:200]

    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text", "")
            # 提取 ARGUMENTS 行
            arg = re.search(r"^ARGUMENTS:\s*(.+)", text, re.MULTILINE)
            if arg:
                parts.append(arg.group(1).strip()[:200])
                continue
            # 跳过超长 skill 内容
            if len(text) > 500:
                continue
            # 命令触发
            if "<command-name>" in text:
                m = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
                if m:
                    parts.append(m.group(1).strip()[:200])
                continue
            if text.strip() and len(text.strip()) > 3:
                parts.append(text.strip()[:200])
        return " | ".join(parts) if parts else None

    return None


def extract_actions(content):
    """从 assistant 消息中提取关键操作（Edit/Write/Bash）。"""
    actions = []
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                name = item.get("name", "")
                inp = item.get("input", {})
                if name == "Bash":
                    desc = inp.get("description", "")
                    cmd = inp.get("command", "")[:80]
                    actions.append(("Bash", desc or cmd))
                elif name in ("Edit", "Write"):
                    fp = inp.get("file_path", "")
                    actions.append((name, os.path.basename(fp) if fp else ""))
    return actions


# ─── 文件处理 ───────────────────────────────────────────────


def process_file(filepath, start, end):
    """处理单个 JSONL 文件，返回当天的活动事件列表。"""
    events = []
    found = False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts = obj.get("timestamp", "")
            if not ts or not in_range(ts, start, end):
                continue
            found = True

            entry_type = obj.get("type", "")
            msg = obj.get("message", {})
            content = msg.get("content", "") if isinstance(msg, dict) else ""

            if entry_type == "user":
                text = extract_user_text(content)
                if text:
                    events.append((to_local(ts), "user", text))
            elif entry_type == "assistant":
                for name, detail in extract_actions(content):
                    events.append((to_local(ts), name, detail))

    return events if found else None


def process_project(sessions_dir, start, end):
    """处理一个项目目录下的所有会话文件，返回 [(会话摘要, 事件列表)]。"""
    results = []
    for fpath in sorted(sessions_dir.glob("*.jsonl")):
        events = process_file(str(fpath), start, end)
        if events:
            results.append((fpath, events))
    return results


# ─── 输出格式化 ───────────────────────────────────────────────


def print_separator(char="=", width=60):
    print(f"\n{char * width}")


def print_session_detail(fpath, events, home):
    """输出单个会话的详细内容。"""
    sid = fpath.stem
    short = f"{sid[:8]}...{sid[-4:]}"
    fp_display = str(fpath).replace(home, "~")

    user_count = sum(1 for _, t, _ in events if t == "user")
    edit_count = sum(1 for _, t, _ in events if t in ("Edit", "Write"))
    bash_count = sum(1 for _, t, _ in events if t == "Bash")

    print(f"\n--- {short} ({events[0][0]} -> {events[-1][0]}) ---")
    print(f"    文件: {fp_display}")
    print(f"    用户消息: {user_count} | 编辑: {edit_count} | 命令: {bash_count}")

    for time, etype, content in events:
        if etype == "user":
            print(f"    [{time}] > {content[:120]}")
        elif etype in ("Edit", "Write"):
            print(f"    [{time}] ~ {etype}: {content}")
        elif etype == "Bash":
            print(f"    [{time}] $ {content[:100]}")


def print_single_project(project_display, results, home):
    """输出单个项目的查询结果（原有格式）。"""
    print_separator()
    print(f"  Claude Code 工作记录 - {parse_date_arg()}")
    print(f"  项目: {project_display}")
    print_separator()

    any_found = False
    for fpath, events in results:
        any_found = True
        print_session_detail(fpath, events, home)

    if not any_found:
        print(f"\n  未找到 {parse_date_arg()} 的会话记录。")
    print()


def summarize_session(events):
    """从会话事件中提取一句话摘要。"""
    # 取第一条用户消息作为摘要
    for _, etype, content in events:
        if etype == "user":
            return content[:60]
    return "（无用户消息）"


def infer_task_title(user_text):
    """从用户消息推断简短任务标题（≤15字）。"""
    # 提取关键动作词和对象
    keywords = ["优化", "创建", "发布", "修复", "更新", "研究", "调试", "写", "设计", "配置", "安装"]
    for kw in keywords:
        if kw in user_text:
            # 取关键词前后的片段
            idx = user_text.index(kw)
            start = max(0, idx - 2)
            end = min(len(user_text), idx + len(kw) + 8)
            title = user_text[start:end].strip()
            if len(title) > 15:
                title = title[:15]
            return title
    # 回退：取前 15 字
    return user_text[:15].strip()


def print_summary(date_str, project_results, home):
    """汇总模式：按项目分组，每个会话一行摘要。"""
    print_separator()
    print(f"  Claude Code 今日工作汇总 - {date_str}")
    print_separator()

    total_sessions = 0
    total_ops = 0

    for readable_name, results in project_results:
        project_sessions = len(results)
        project_ops = sum(len(events) for _, events in results)
        total_sessions += project_sessions
        total_ops += project_ops

        print(f"\n📂 {readable_name} ({project_sessions} 个会话)")
        for fpath, events in results:
            sid = fpath.stem[:8] + "..."
            time_range = f"{events[0][0]}-{events[-1][0]}"
            summary = summarize_session(events)
            user_msg = sum(1 for _, t, _ in events if t == "user")
            edit_msg = sum(1 for _, t, _ in events if t in ("Edit", "Write"))
            bash_msg = sum(1 for _, t, _ in events if t == "Bash")
            ops = user_msg + edit_msg + bash_msg
            print(f"  {time_range}  {summary} ({ops} 个操作)")

    print(f"\n{'─' * 50}")
    print(f"  合计: {len(project_results)} 个项目 | {total_sessions} 个会话 | {total_ops} 个操作")
    print(f"{'─' * 50}")
    print()


def print_ticktick(date_str, project_results, ticktick_project_id):
    """滴答清单模式：输出 JSON 数组，可直接用 tt task-batch-add --stdin 创建。"""
    import json as _json

    tasks = []
    for readable_name, results in project_results:
        for fpath, events in results:
            time_start = events[0][0]
            time_end = events[-1][0]
            summary = summarize_session(events)
            title = infer_task_title(summary)

            # 构建内容：列出关键操作
            edit_files = set()
            bash_descs = []
            for _, etype, content in events:
                if etype in ("Edit", "Write"):
                    edit_files.add(content)
                elif etype == "Bash" and len(bash_descs) < 5:
                    bash_descs.append(content[:60])

            content_parts = []
            if edit_files:
                content_parts.append("文件: " + ", ".join(sorted(edit_files)[:8]))
            if bash_descs:
                content_parts.extend([f"- {d}" for d in bash_descs])
            content_str = "\n".join(content_parts) if content_parts else summary

            # 构建日期时间
            dt_start = f"{date_str}T{time_start}:00+08:00"
            dt_end = f"{date_str}T{time_end}:00+08:00"

            tasks.append({
                "title": title,
                "content": content_str,
                "projectId": ticktick_project_id,
                "startDate": dt_start,
                "dueDate": dt_end,
            })

    print(_json.dumps(tasks, ensure_ascii=False, indent=2))


def print_all_projects(date_str, project_results, home):
    """输出所有项目的查询结果（按项目分组）。"""
    # 按可读项目名排序
    project_results.sort(key=lambda x: x[0])

    print_separator()
    print(f"  Claude Code 工作记录（全部项目）- {date_str}")
    print_separator()

    total_sessions = 0
    total_events = 0

    for readable_name, results in project_results:
        project_events = sum(len(events) for _, events in results)
        total_sessions += len(results)
        total_events += project_events

        print(f"\n{'─' * 50}")
        print(f"  📂 {readable_name}  ({len(results)} 个会话, {project_events} 条记录)")
        print(f"{'─' * 50}")

        for fpath, events in results:
            print_session_detail(fpath, events, home)

    if not project_results:
        print(f"\n  未找到 {date_str} 的会话记录。")
    else:
        print(f"\n{'─' * 50}")
        print(f"  合计: {len(project_results)} 个项目 | {total_sessions} 个会话 | {total_events} 条记录")
        print(f"{'─' * 50}")
    print()


# ─── 参数解析 ───────────────────────────────────────────────


def has_flag(flag):
    """检查命令行参数中是否包含指定标志。"""
    return flag in sys.argv


def get_project_arg():
    """获取 --project 参数值。"""
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


# ─── 主流程 ───────────────────────────────────────────────


def get_ticktick_project_arg():
    """获取 --ticktick-project 参数值（滴答清单项目 ID）。"""
    for i, a in enumerate(sys.argv):
        if a == "--ticktick-project" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def collect_all_results(start, end):
    """收集所有项目的扫描结果，返回 [(可读名, [(fpath, events)])]"""
    all_projects = get_all_project_dirs()
    if not all_projects:
        return []
    project_results = []
    for encoded, readable, project_dir in all_projects:
        results = process_project(project_dir, start, end)
        if results:
            project_results.append((readable, results))
    return project_results


def main():
    date_str = parse_date_arg()
    try:
        start, end = get_utc_range(date_str)
    except ValueError:
        print(f"日期格式错误: {date_str}，请使用 YYYY-MM-DD")
        sys.exit(1)

    home = str(Path.home())
    mode_all = has_flag("--all")
    mode_summary = has_flag("--summary")
    mode_ticktick = has_flag("--ticktick")
    project_arg = get_project_arg()

    if mode_ticktick:
        # ── 滴答清单 JSON 模式 ──
        project_results = collect_all_results(start, end)
        if not project_results:
            print("[]")
            sys.exit(0)
        # 默认大模型清单 ID，可通过 --ticktick-project 覆盖
        ticktick_pid = get_ticktick_project_arg() or "69d12132e4b05178c14facf2"
        print_ticktick(date_str, project_results, ticktick_pid)

    elif mode_summary:
        # ── 汇总模式 ──
        if mode_all or not has_flag("--project"):
            project_results = collect_all_results(start, end)
        else:
            sessions_dir = get_sessions_dir_by_project(project_arg) if project_arg else get_sessions_dir_cwd()
            if not sessions_dir:
                print(f"未找到会话记录")
                sys.exit(1)
            results = process_project(sessions_dir, start, end)
            readable = (project_arg or os.getcwd()).replace(home, "~")
            project_results = [(readable, results)] if results else []

        print_summary(date_str, project_results, home)

    elif mode_all:
        # ── 全项目详细模式 ──
        project_results = collect_all_results(start, end)
        print_all_projects(date_str, project_results, home)

    elif project_arg:
        # ── 指定项目模式 ──
        sessions_dir = get_sessions_dir_by_project(project_arg)
        if not sessions_dir:
            print(f"未找到指定项目的 Claude 会话: {project_arg}")
            sys.exit(1)
        results = process_project(sessions_dir, start, end)
        project_display = project_arg.replace(home, "~")
        print_single_project(project_display, results, home)

    else:
        # ── 默认模式：当前项目 ──
        sessions_dir = get_sessions_dir_cwd()
        if not sessions_dir:
            print(f"未找到当前项目的 Claude 会话: {os.getcwd()}")
            print(f"提示: 使用 --all 查看所有项目，或 --project <路径> 指定项目")
            sys.exit(1)
        results = process_project(sessions_dir, start, end)
        cwd_display = os.getcwd().replace(home, "~")
        print_single_project(cwd_display, results, home)


if __name__ == "__main__":
    main()
