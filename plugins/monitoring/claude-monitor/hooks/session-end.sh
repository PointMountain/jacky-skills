#!/bin/bash
# hooks/session-end.sh
# Claude Code 会话结束时调用

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
# 使用父进程 ID 作为会话标识
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 从守护进程注销
curl --noproxy "*" -s -X DELETE "$DAEMON_URL/api/sessions/$SESSION_PID" > /dev/null 2>&1

# 检查是否启用悬浮窗
if is_scenario_enabled "sessionEnd"; then
  DURATION=$(get_scenario_duration "sessionEnd" 3)
  ~/.claude-monitor/claude-float-window done "$PROJECT_NAME" "会话已结束" "$TERMINAL" "$DURATION" &
fi

exit 0
