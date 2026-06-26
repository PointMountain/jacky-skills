#!/usr/bin/env python3
"""skill-usage-log.py —— skill 使用频率采集逻辑

由 skill-usage-log.sh 调用：stdin 收 hook 的 JSON，argv[1] 为日志文件路径。
靠 hook_event_name 分流两种来源：
  - PostToolUse(tool_name=Skill)  → AI 主动调用，source=ai
  - UserPromptSubmit(prompt 以 / 开头) → 用户手输命令，source=user
永不抛错影响主流程，解析失败直接静默退出。
"""
import sys
import json
import datetime
import re

log_path = sys.argv[1] if len(sys.argv) > 1 else None
if not log_path:
    sys.exit(0)

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

event = data.get("hook_event_name", "")
session = data.get("session_id", "")
cwd = data.get("cwd", "")
ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

skill = None
source = None

if event == "PostToolUse" and data.get("tool_name") == "Skill":
    # 本机 Skill 工具参数字段是 "skill"；兼容文档示例里的 "name"
    ti = data.get("tool_input", {}) or {}
    skill = ti.get("skill") or ti.get("name")
    source = "ai"

elif event == "UserPromptSubmit":
    prompt = (data.get("prompt") or "").lstrip()
    if prompt.startswith("/"):
        m = re.match(r"/([A-Za-z0-9_:\-]+)", prompt)
        if m:
            cmd = m.group(1)
            # 过滤 Claude Code 内置命令，只统计真正的 skill / slash command
            BUILTIN = {
                "help", "clear", "compact", "config", "model", "cost", "login",
                "logout", "doctor", "init", "bug", "memory", "status", "resume",
                "exit", "quit", "vim", "terminal-setup", "fast", "add-dir",
                "permissions", "hooks", "mcp", "ide", "pr-comments", "release-notes",
            }
            if cmd not in BUILTIN:
                skill = cmd
                source = "user"

if not skill:
    sys.exit(0)

rec = {
    "ts": ts,
    "skill": skill,
    "source": source,
    "session": session,
    "cwd": cwd,
}

try:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass

sys.exit(0)
