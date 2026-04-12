#!/bin/bash
# hooks/waiting-input.sh
# 等待用户输入：更新守护进程状态 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 1. 始终向守护进程更新状态
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"waiting_input","message":"等待用户输入"}' > /dev/null 2>&1

# 2. 悬浮弹窗（受开关控制）
if is_floating_window_enabled; then
  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    "$FLOAT_BIN" waiting_input "$PROJECT_NAME" "等待用户输入" "$TERMINAL" 0 &
    disown 2>/dev/null || true
  fi
fi

exit 0
