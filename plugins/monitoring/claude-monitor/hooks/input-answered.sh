#!/bin/bash
# hooks/input-answered.sh
# Claude Code 用户输入已响应时调用 (PostToolUse - AskUserQuestion)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"

DAEMON_URL="http://127.0.0.1:17530"
# 使用父进程 ID 作为会话标识
SESSION_PID=$PPID

# 关闭 waiting_input 状态的悬浮窗
# 使用 pkill 匹配进程参数中包含 "waiting_input" 的 claude-float-window
pkill -9 -f "claude-float-window.*waiting_input" 2>/dev/null || true
# 备用方案：直接杀掉所有 waiting_input 相关进程
pgrep -f "waiting_input" | xargs kill -9 2>/dev/null || true

# 更新会话状态为 thinking，并清除消息
curl --noproxy "*" -s -X PATCH "$DAEMON_URL/api/sessions/$SESSION_PID" \
  -H "Content-Type: application/json" \
  -d '{"status":"thinking","message":""}' > /dev/null 2>&1

exit 0
