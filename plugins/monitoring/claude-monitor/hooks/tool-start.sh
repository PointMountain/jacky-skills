#!/bin/bash
# hooks/tool-start.sh
# 工具调用开始时调用 (PreToolUse Hook)
# stdin 包含: {"tool": "Read", "input": {"file_path": "..."}}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 标记文件目录
MARKER_DIR="/tmp/claude-monitor"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取 tool 和 input 字段
if command -v jq &> /dev/null; then
  TOOL=$(echo "$INPUT" | jq -r '.tool // empty')
  TOOL_INPUT=$(echo "$INPUT" | jq -c '.input // {}')
else
  # 简单提取
  TOOL=$(echo "$INPUT" | sed 's/.*"tool"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  TOOL_INPUT="{}"
fi

# 如果有 tool 名称，发送到守护进程
if [ -n "$TOOL" ]; then
  # 标记工具调用开始（用于延迟弹窗检测）
  mkdir -p "$MARKER_DIR"
  echo "$SESSION_PID" > "$MARKER_DIR/tool_active_$SESSION_PID"

  # 记录工具调用（守护进程会自动更新状态为 executing 或 multi_executing）
  RESPONSE=$(curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions/$SESSION_PID/tools" \
    -H "Content-Type: application/json" \
    -d "{\"tool\":\"$TOOL\",\"input\":$TOOL_INPUT}" 2>/dev/null)

  # 提取 toolCallId 和会话状态
  if command -v jq &> /dev/null; then
    TOOL_CALL_ID=$(echo "$RESPONSE" | jq -r '.data.id // empty')
    if [ -n "$TOOL_CALL_ID" ]; then
      # 保存 toolCallId 到临时文件，供 tool-end.sh 使用
      echo "$TOOL_CALL_ID" > "$MARKER_DIR/tool_id_${SESSION_PID}_${TOOL}"
    fi
  fi

  # 检查是否启用悬浮窗
  if is_scenario_enabled "executing"; then
    # 检查工具是否在过滤列表中
    if is_tool_in_filter "$TOOL"; then
      DURATION=$(get_scenario_duration "executing" 2)

      # 获取当前会话状态（检查是否并行执行）
      SESSION_DATA=$(curl --noproxy "*" -s "$DAEMON_URL/api/sessions/$SESSION_PID" 2>/dev/null)
      STATUS=$(echo "$SESSION_DATA" | jq -r '.data.status // "executing"')
      ACTIVE_COUNT=$(echo "$SESSION_DATA" | jq -r '.data.activeToolsCount // 1')

      # 根据状态决定显示的消息
      if [ "$STATUS" = "multi_executing" ] || [ "$ACTIVE_COUNT" -gt 1 ]; then
        FLOAT_STATUS="multi_executing"
        MESSAGE="执行 $ACTIVE_COUNT 个工具..."
      else
        FLOAT_STATUS="executing"
        MESSAGE="执行: $TOOL"
      fi

      ~/.claude-monitor/claude-float-window "$FLOAT_STATUS" "$PROJECT_NAME" "$MESSAGE" "$TERMINAL" "$DURATION" &
    fi
  fi
fi

exit 0
