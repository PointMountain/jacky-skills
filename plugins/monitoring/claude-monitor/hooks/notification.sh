#!/bin/bash
# hooks/notification.sh
# Claude Code 发送通知时调用 (Notification Hook)
# 触发场景:
# 1. Claude 需要用户权限使用工具时
# 2. 提示输入空闲超过 60 秒时
# stdin 包含: {"message": "...", "reason": "permission"|"idle"}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
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

# 更新会话状态为 waiting_input
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"waiting_input\",\"message\":\"$MESSAGE\"}" > /dev/null 2>&1

# 检查是否启用悬浮窗
if is_scenario_enabled "waitingInput"; then
  DURATION=$(get_scenario_duration "waitingInput" 0)

  # 根据 reason 选择显示内容
  case "$REASON" in
    "permission")
      TITLE="需要权限"
      BODY="${MESSAGE:-Claude 需要您的授权}"
      ;;
    "idle")
      TITLE="等待输入"
      BODY="${MESSAGE:-Claude 正在等待您的输入}"
      ;;
    *)
      TITLE="通知"
      BODY="${MESSAGE:-Claude 需要注意}"
      ;;
  esac

  # 关闭之前的等待输入弹窗（避免重复）
  pkill -9 -f "claude-float-window.*waiting_input" 2>/dev/null || true
  pkill -9 -f "claude-float-window.*notification" 2>/dev/null || true

  # 显示悬浮窗
  if [ "$DURATION" -eq 0 ]; then
    # 持续显示直到用户关闭
    ~/.claude-monitor/claude-float-window waiting_input "$PROJECT_NAME" "$TITLE" "$TERMINAL" 0 &
  else
    ~/.claude-monitor/claude-float-window waiting_input "$PROJECT_NAME" "$TITLE" "$TERMINAL" "$DURATION" &
  fi
  disown 2>/dev/null || true
fi

exit 0
