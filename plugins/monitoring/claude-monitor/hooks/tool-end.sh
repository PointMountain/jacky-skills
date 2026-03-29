#!/bin/bash
# hooks/tool-end.sh
# 工具调用结束时调用 (PostToolUse Hook)
# stdin 包含: {"tool": "Read", "success": true, "error": "..."}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 标记文件目录
MARKER_DIR="/tmp/claude-monitor"
MARKER_FILE="$MARKER_DIR/tool_active_$SESSION_PID"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取字段
if command -v jq &> /dev/null; then
  TOOL=$(echo "$INPUT" | jq -r '.tool // empty')
  SUCCESS=$(echo "$INPUT" | jq -r '.success // true')
  ERROR=$(echo "$INPUT" | jq -r '.error // empty')
  TOOL_CALL_ID=$(echo "$INPUT" | jq -r '.toolCallId // empty')
else
  TOOL=$(echo "$INPUT" | sed 's/.*"tool"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  SUCCESS="true"
  ERROR=""
  TOOL_CALL_ID=""
fi

# 尝试从临时文件获取 toolCallId
if [ -z "$TOOL_CALL_ID" ] && [ -n "$TOOL" ]; then
  TOOL_ID_FILE="$MARKER_DIR/tool_id_${SESSION_PID}_${TOOL}"
  if [ -f "$TOOL_ID_FILE" ]; then
    TOOL_CALL_ID=$(cat "$TOOL_ID_FILE")
    rm -f "$TOOL_ID_FILE" 2>/dev/null
  fi
fi

# 如果有 tool_call_id，更新状态（守护进程会自动更新会话状态）
if [ -n "$TOOL_CALL_ID" ]; then
  ERROR_PART=""
  if [ -n "$ERROR" ]; then
    ESCAPED_ERROR=$(echo "$ERROR" | sed 's/\\/\\\\/g; s/"/\\"/g')
    ERROR_PART=",\"error\":\"$ESCAPED_ERROR\""
  fi

  RESPONSE=$(curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID/tools/$TOOL_CALL_ID" \
    -H "Content-Type: application/json" \
    -d "{\"success\":$SUCCESS$ERROR_PART}" 2>/dev/null)

  # 检查会话状态，如果所有工具完成则显示弹窗
  SESSION_STATUS=$(curl --noproxy "*" -s "$DAEMON_URL/api/sessions/$SESSION_PID" 2>/dev/null | jq -r '.data.status // empty')

  if [ "$SESSION_STATUS" = "tool_done" ]; then
    # 所有工具完成，显示工具完成弹窗（但不显示任务完成）
    if is_scenario_enabled "executing"; then
      DURATION=1  # 短暂显示
      ~/.claude-monitor/claude-float-window tool_done "$PROJECT_NAME" "✓ $TOOL 完成" "$TERMINAL" "$DURATION" &
    fi
  elif [ "$SESSION_STATUS" = "error" ]; then
    # 出错
    if is_scenario_enabled "executing"; then
      DURATION=2
      ~/.claude-monitor/claude-float-window error "$PROJECT_NAME" "✗ $TOOL 失败" "$TERMINAL" "$DURATION" &
    fi
  fi
fi

exit 0
