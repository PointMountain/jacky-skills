#!/bin/bash
# hooks/notification.sh
# 通知触发：更新守护进程状态 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取 message 和 reason
if command -v jq &> /dev/null; then
  MESSAGE=$(echo "$INPUT" | jq -r '.message // empty')
  REASON=$(echo "$INPUT" | jq -r '.reason // empty')
else
  MESSAGE=$(echo "$INPUT" | sed 's/.*"message"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  REASON=$(echo "$INPUT" | sed 's/.*"reason"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi

# 1. 始终向守护进程更新状态
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"waiting_input\",\"message\":\"$MESSAGE\"}" > /dev/null 2>&1

# 2. 悬浮弹窗（受开关控制）
if is_floating_window_enabled; then
  # 关闭之前的等待输入弹窗（避免重复）
  pkill -9 -f "claude-float-window.*waiting_input" 2>/dev/null || true
  pkill -9 -f "claude-float-window.*notification" 2>/dev/null || true

  case "$REASON" in
    "permission") TITLE="需要权限" ;;
    "idle") TITLE="等待输入" ;;
    *) TITLE="通知" ;;
  esac

  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    "$FLOAT_BIN" waiting_input "$PROJECT_NAME" "$TITLE" "$TERMINAL" 0 &
    disown 2>/dev/null || true
  fi
fi

exit 0
