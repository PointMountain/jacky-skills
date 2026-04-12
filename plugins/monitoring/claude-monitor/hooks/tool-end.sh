#!/bin/bash
# hooks/tool-end.sh
# 工具调用结束：更新守护进程状态 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

MARKER_DIR="/tmp/claude-monitor"

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

# 1. 始终向守护进程更新工具状态
if [ -n "$TOOL_CALL_ID" ]; then
  ERROR_PART=""
  if [ -n "$ERROR" ]; then
    ESCAPED_ERROR=$(echo "$ERROR" | sed 's/\\/\\\\/g; s/"/\\"/g')
    ERROR_PART=",\"error\":\"$ESCAPED_ERROR\""
  fi

  curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID/tools/$TOOL_CALL_ID" \
    -H "Content-Type: application/json" \
    -d "{\"success\":$SUCCESS$ERROR_PART}" > /dev/null 2>&1

  # 2. 悬浮弹窗（受开关控制）
  if is_floating_window_enabled; then
    SESSION_STATUS=$(curl --noproxy "*" -s "$DAEMON_URL/api/sessions/$SESSION_PID" 2>/dev/null | jq -r '.data.status // empty')

    FLOAT_BIN=$(get_float_binary)
    if [[ -n "$FLOAT_BIN" ]]; then
      if [ "$SESSION_STATUS" = "tool_done" ]; then
        "$FLOAT_BIN" tool_done "$PROJECT_NAME" "✓ $TOOL 完成" "$TERMINAL" 1 &
      elif [ "$SESSION_STATUS" = "error" ]; then
        "$FLOAT_BIN" error "$PROJECT_NAME" "✗ $TOOL 失败" "$TERMINAL" 2 &
      fi
      disown 2>/dev/null || true
    fi
  fi
fi

exit 0
