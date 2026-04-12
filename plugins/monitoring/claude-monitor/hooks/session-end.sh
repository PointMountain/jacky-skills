#!/bin/bash
# hooks/session-end.sh
# 会话结束：从守护进程注销 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 1. 始终从守护进程注销
curl --noproxy "*" -s -X DELETE "$DAEMON_URL/api/sessions/$SESSION_PID" > /dev/null 2>&1

# 2. 悬浮弹窗（受开关控制）
if is_floating_window_enabled; then
  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    "$FLOAT_BIN" done "$PROJECT_NAME" "会话已结束" "$TERMINAL" 3 &
    disown 2>/dev/null || true
  fi
fi

exit 0
