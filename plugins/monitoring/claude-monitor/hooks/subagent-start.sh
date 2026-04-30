#!/bin/bash
# hooks/subagent-start.sh
# 子代理启动时触发 (SubagentStart Hook)
# stdin 包含: {"agentType": "general-purpose", "description": "..."}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

SOCKET_PATH="$HOME/.claude-monitor/monitor.sock"
SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"

# 从 stdin 读取 JSON 数据
INPUT=$(cat)

# Debug: 记录实际收到的数据格式
echo "$(date +%s) PID=$SESSION_PID INPUT=$INPUT" >> /tmp/claude-subagent-debug.log

# 提取字段
if command -v jq &> /dev/null; then
  AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // .agentType // "unknown"')
  DESCRIPTION=$(echo "$INPUT" | jq -r '.description // empty' | head -c 200)
else
  AGENT_TYPE=$(echo "$INPUT" | sed 's/.*"agent_type"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  DESCRIPTION=""
fi

if [ -n "$AGENT_TYPE" ]; then
  # 发送到守护进程
  ESCAPED_DESC=$(echo "$DESCRIPTION" | sed 's/\\/\\\\/g; s/"/\\"/g')
  RESPONSE=$(curl -s --unix-socket "$SOCKET_PATH" -X POST "http://localhost/api/sessions/$SESSION_PID/subagents" \
    -H "Content-Type: application/json" \
    -d "{\"agentType\":\"$AGENT_TYPE\",\"description\":\"$ESCAPED_DESC\"}" 2>/dev/null)

  # 显示子代理启动提示
  if is_scenario_enabled "executing"; then
    DURATION=$(get_scenario_duration "executing" 2)

    # 获取当前活跃子代理数
    ACTIVE_COUNT=$(echo "$RESPONSE" | jq -r '.data // empty' 2>/dev/null | head -1)

    ~/.claude-monitor/claude-float-window executing "$PROJECT_NAME" "派发子代理: $AGENT_TYPE" "$TERMINAL" "$DURATION" &
  fi
fi

exit 0
