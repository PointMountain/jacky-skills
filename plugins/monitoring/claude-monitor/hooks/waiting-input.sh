#!/bin/bash
# hooks/waiting-input.sh
# Claude Code 等待用户输入时调用 (PreToolUse - AskUserQuestion)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 更新会话状态为 waiting_input
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"waiting_input","message":"等待用户输入"}' > /dev/null 2>&1

# 检查是否启用悬浮窗
if is_scenario_enabled "waitingInput"; then
  DURATION=$(get_scenario_duration "waitingInput" 0)
  ~/.claude-monitor/claude-float-window waiting_input "$PROJECT_NAME" "等待用户输入" "$TERMINAL" "$DURATION" &
fi

exit 0
