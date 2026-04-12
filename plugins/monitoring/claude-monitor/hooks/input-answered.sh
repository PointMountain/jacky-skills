#!/bin/bash
# hooks/input-answered.sh
# 用户输入已响应：更新守护进程状态 + 关闭弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID

# 1. 始终向守护进程更新状态
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"thinking","message":""}' > /dev/null 2>&1

# 2. 关闭可能存在的等待输入弹窗（只有弹窗开启时才需要关）
pkill -9 -f "claude-float-window.*waiting_input" 2>/dev/null || true

exit 0
