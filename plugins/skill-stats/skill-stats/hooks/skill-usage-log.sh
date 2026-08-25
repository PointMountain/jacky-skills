#!/bin/bash
# skill-usage-log.sh —— skill 使用频率采集 hook（wrapper）
#
# 服务两个 hook（靠 stdin JSON 的 hook_event_name 分流，逻辑在 .py 里）：
#   1) PostToolUse(matcher=Skill)  —— AI 主动调用 skill，source=ai
#   2) UserPromptSubmit            —— 用户手输 /命令，source=user
#
# 本 wrapper 只做两件事：探测可用的 python3；把 stdin 透传给 .py。
# 永远 exit 0，绝不阻塞 / 干扰主流程。

LOG="$HOME/.claude/skill-usage.jsonl"
DIR="$(cd "$(dirname "$0")" && pwd)"

# 探测 python3（hook 在非交互 shell 跑，PATH 可能不全，逐个兜底）
PY=""
for c in python3 /usr/bin/python3 /opt/homebrew/bin/python3 /opt/anaconda3/bin/python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -z "$PY" ] && exit 0

# stdin（hook 的 JSON）透传给 python；python 源码来自文件，互不抢占 stdin
"$PY" "$DIR/skill-usage-log.py" "$LOG"

exit 0
