#!/bin/bash
# hooks/tool-start.sh
# 工具调用开始：记录到守护进程 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

MARKER_DIR="/tmp/claude-monitor"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取 tool 和 input 字段
if command -v jq &> /dev/null; then
  TOOL=$(echo "$INPUT" | jq -r '.tool // empty')
  TOOL_INPUT=$(echo "$INPUT" | jq -c '.input // {}')
else
  TOOL=$(echo "$INPUT" | sed 's/.*"tool"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  TOOL_INPUT="{}"
fi

# 1. 始终向守护进程记录工具调用
if [ -n "$TOOL" ]; then
  mkdir -p "$MARKER_DIR"
  echo "$SESSION_PID" > "$MARKER_DIR/tool_active_$SESSION_PID"

  RESPONSE=$(curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions/$SESSION_PID/tools" \
    -H "Content-Type: application/json" \
    -d "{\"tool\":\"$TOOL\",\"input\":$TOOL_INPUT}" 2>/dev/null)

  # 提取 toolCallId 供 tool-end.sh 使用
  if command -v jq &> /dev/null; then
    TOOL_CALL_ID=$(echo "$RESPONSE" | jq -r '.data.id // empty')
    if [ -n "$TOOL_CALL_ID" ]; then
      echo "$TOOL_CALL_ID" > "$MARKER_DIR/tool_id_${SESSION_PID}_${TOOL}"
    fi
  fi

  # 2. 悬浮弹窗（受开关控制）
  if is_floating_window_enabled; then
    FLOAT_BIN=$(get_float_binary)
    if [[ -n "$FLOAT_BIN" ]]; then
      # 检查是否并行执行
      SESSION_DATA=$(curl --noproxy "*" -s "$DAEMON_URL/api/sessions/$SESSION_PID" 2>/dev/null)
      ACTIVE_COUNT=$(echo "$SESSION_DATA" | jq -r '.data.activeToolsCount // 1' 2>/dev/null)

      if [ "$ACTIVE_COUNT" -gt 1 ] 2>/dev/null; then
        "$FLOAT_BIN" multi_executing "$PROJECT_NAME" "执行 $ACTIVE_COUNT 个工具..." "$TERMINAL" 2 &
      else
        "$FLOAT_BIN" executing "$PROJECT_NAME" "执行: $TOOL" "$TERMINAL" 2 &
      fi
      disown 2>/dev/null || true
    fi
  fi
fi

exit 0
