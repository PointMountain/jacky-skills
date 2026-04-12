#!/bin/bash
# hooks/prompt-submit.sh
# 用户提交提问：更新守护进程状态 + 可选弹窗

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# 提取 prompt 字段
if command -v jq &> /dev/null; then
  PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty')
else
  PROMPT=$(echo "$INPUT" | sed 's/.*"prompt"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi

# 1. 始终向守护进程更新状态
if [ -n "$PROMPT" ]; then
  ESCAPED_PROMPT=$(echo "$PROMPT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g')

  curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
    -H "Content-Type: application/json" \
    -d '{"status":"thinking"}' > /dev/null 2>&1

  curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions/$SESSION_PID/prompts" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\":\"$ESCAPED_PROMPT\"}" > /dev/null 2>&1
fi

# 2. 悬浮弹窗（受开关控制）
if is_floating_window_enabled && [ -n "$PROMPT" ]; then
  FLOAT_BIN=$(get_float_binary)
  if [[ -n "$FLOAT_BIN" ]]; then
    TRUNCATED_PROMPT=$(echo "$PROMPT" | cut -c1-30)
    [ ${#PROMPT} -gt 30 ] && TRUNCATED_PROMPT="${TRUNCATED_PROMPT}..."
    "$FLOAT_BIN" thinking "$PROJECT_NAME" "$TRUNCATED_PROMPT" "$TERMINAL" 3 &
    disown 2>/dev/null || true
  fi
fi

exit 0
