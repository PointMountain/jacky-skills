#!/bin/bash
# hooks/session-start.sh
# Claude Code 会话开始时调用

DAEMON_URL="http://127.0.0.1:17530"
# 使用父进程 ID 作为会话标识（所有 hooks 都由同一父进程启动）
SESSION_PID=$PPID
PARENT_PID=$(ps -o ppid= -p $$ | tr -d ' ')
TERMINAL="${TERM_PROGRAM:-unknown}"
CWD="$PWD"

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
