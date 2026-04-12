#!/bin/bash
# hooks/session-start.sh
# 会话开始：注册到守护进程 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PARENT_PID=$(ps -o ppid= -p $$ | tr -d ' ')
TERMINAL="${TERM_PROGRAM:-unknown}"
CWD="$PWD"

# 1. 始终向守护进程注册会话
curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions" \
  -H "Content-Type: application/json" \
  -d "{
    \"pid\": $SESSION_PID,
    \"ppid\": $PARENT_PID,
    \"terminal\": \"$TERMINAL\",
    \"cwd\": \"$CWD\"
  }" > /dev/null 2>&1

# 2. 悬浮弹窗（受开关控制，默认关闭）
if is_floating_window_enabled; then
  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    PROJECT_NAME=$(basename "$PWD")
    "$FLOAT_BIN" thinking "$PROJECT_NAME" "会话已启动" "$TERMINAL" 2 &
    disown 2>/dev/null || true
  fi
fi

exit 0
