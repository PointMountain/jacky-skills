#!/bin/bash
# hooks/session-start.sh
# Claude Code 会话开始时调用

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
# 使用父进程 ID 作为会话标识（所有 hooks 都由同一父进程启动）
SESSION_PID=$PPID
PARENT_PID=$(ps -o ppid= -p $$ | tr -d ' ')
TERMINAL="${TERM_PROGRAM:-unknown}"
CWD="$PWD"

# 首次自动初始化：检查依赖和编译悬浮窗
ensure_dependencies
ensure_float_window_binary

# 自动创建默认配置文件（如果不存在）
if [[ ! -f "$CONFIG_FILE" ]]; then
  cat > "$CONFIG_FILE" << 'DEFAULT_CONFIG'
{
  "floatingWindow": {
    "enabled": true,
    "scenarios": {
      "thinking": { "enabled": true, "duration": 3 },
      "executing": { "enabled": true, "duration": 2 },
      "waitingInput": { "enabled": true, "duration": 0 },
      "sessionEnd": { "enabled": true, "duration": 3 }
    }
  }
}
DEFAULT_CONFIG
fi

# 发送到守护进程
curl --noproxy "*" -s -X POST "$DAEMON_URL/api/sessions" \
  -H "Content-Type: application/json" \
  -d "{
    \"pid\": $SESSION_PID,
    \"ppid\": $PARENT_PID,
    \"terminal\": \"$TERMINAL\",
    \"cwd\": \"$CWD\"
  }" > /dev/null 2>&1

# 静默退出
exit 0
