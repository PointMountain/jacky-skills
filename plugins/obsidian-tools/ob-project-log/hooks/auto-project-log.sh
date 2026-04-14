#!/bin/bash
# hooks/auto-project-log.sh
# Stop Hook：对话结束时自动检查是否有项目知识需要沉淀到 Obsidian
# skill: ob-project-log

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_PID=$PPID

# 检查是否开启了自动沉淀
if [ ! -f "$HOME/.claude/ob-auto-sync.enabled" ]; then
  exit 0
fi

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

# 所有条件满足 → 阻止停止，让 Claude 检查是否需要沉淀
# Claude 处理完后会创建标记文件，下次触发时标记文件存在就放行
cat << 'HOOKMSG'
{"decision":"block","reason":"请检查本次对话是否有项目知识需要沉淀到 Obsidian。\n\n判断标准：\n- 讨论了项目架构、技术决策、踩坑经验等有价值内容（≥1条）→ 沉淀\n- 纯闲聊、临时调试、无结论讨论 → 不沉淀\n\n操作：\n1. 如果有内容需要沉淀 → 使用 ob-project-log 自动沉淀模式执行\n2. 如果没有 → 直接说\"本次对话无需沉淀\"\n3. 无论哪种情况，完成后执行: echo $(date +%s) > /tmp/ob-project-log-synced-$PPID"}
HOOKMSG
