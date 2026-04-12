#!/bin/bash
# hooks/response-end.sh
# 任务完成：更新守护进程状态 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

MARKER_DIR="/tmp/claude-monitor"
MARKER_FILE="$MARKER_DIR/tool_active_$SESSION_PID"

# 清理工具活动标记
rm -f "$MARKER_FILE" 2>/dev/null

# 1. 始终向守护进程更新状态
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","message":"","activeToolsCount":0,"activeTools":[]}' > /dev/null 2>&1

# 2. 悬浮弹窗（受开关控制）
if is_floating_window_enabled; then
  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    "$FLOAT_BIN" completed "$PROJECT_NAME" "任务完成" "$TERMINAL" 3 &
    disown 2>/dev/null || true
  fi
fi

exit 0
