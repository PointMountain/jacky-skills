#!/bin/bash
# hooks/auto-project-log.sh
# Stop Hook：对话结束时自动检查是否有项目知识需要沉淀到 Obsidian
# skill: ob-project-log

SESSION_PID=$PPID

# 防死循环：如果刚处理过，允许停止
MARKER="/tmp/ob-project-log-synced-$SESSION_PID"
if [ -f "$MARKER" ]; then
  rm -f "$MARKER"
  exit 0
fi

# 检查当前目录是否在 git 项目中
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  exit 0
fi

# 非阻塞模式：不注入内容到上下文
# 依靠 SessionStart 注入的项目知识索引，Claude 自行判断是否沉淀
exit 0
