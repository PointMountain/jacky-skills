#!/bin/bash
# hooks/response-end.sh
# LLM 响应结束时调用 (Stop Hook)
# 这表示整个任务完成（区别于单个工具完成）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 标记文件目录
MARKER_DIR="/tmp/claude-monitor"
MARKER_FILE="$MARKER_DIR/tool_active_$SESSION_PID"

# 清理工具活动标记
rm -f "$MARKER_FILE" 2>/dev/null

# 更新状态为 completed（任务完成）
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","message":"","activeToolsCount":0,"activeTools":[]}' > /dev/null 2>&1

# 显示任务完成弹窗
if is_scenario_enabled "sessionEnd"; then
  DURATION=$(get_scenario_duration "sessionEnd" 3)
  ~/.claude-monitor/claude-float-window completed "$PROJECT_NAME" "任务完成" "$TERMINAL" "$DURATION" &
fi

exit 0
