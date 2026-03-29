#!/bin/bash
# hooks/prompt-submit.sh
# 用户提交提问时调用 (UserPromptSubmit Hook)
# stdin 包含: {"prompt": "用户的问题..."}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取 prompt 字段 (使用 jq)
if command -v jq &> /dev/null; then
  PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty')
else
  # 简单提取 (如果没有 jq)
  PROMPT=$(echo "$INPUT" | sed 's/.*"prompt"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi

# 如果有 prompt 内容，发送到守护进程
if [ -n "$PROMPT" ]; then
  # 转义 JSON 特殊字符
  ESCAPED_PROMPT=$(echo "$PROMPT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g')

  # 更新状态为 thinking
  curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
    -H "Content-Type: application/json" \
    -d '{"status":"thinking"}' > /dev/null 2>&1

  # 记录提问
  curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions/$SESSION_PID/prompts" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\":\"$ESCAPED_PROMPT\"}" > /dev/null 2>&1

  # 检查是否启用悬浮窗
  if is_scenario_enabled "thinking"; then
    DURATION=$(get_scenario_duration "thinking" 3)
    TRUNCATED_PROMPT=$(echo "$PROMPT" | cut -c1-30)
    [ ${#PROMPT} -gt 30 ] && TRUNCATED_PROMPT="${TRUNCATED_PROMPT}..."
    ~/.claude-monitor/claude-float-window thinking "$PROJECT_NAME" "$TRUNCATED_PROMPT" "$TERMINAL" "$DURATION" &
  fi
fi

exit 0
