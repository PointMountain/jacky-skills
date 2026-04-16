#!/bin/bash
# hooks/load-ob-index.sh
# SessionStart Hook：会话开始时自动加载 Obsidian 知识库索引
# skill: ob-project-log

# 优先使用 OBSIDIAN_REPO 环境变量，回退到默认路径
OB_REPO="${OBSIDIAN_REPO:-$HOME/jacky-obsidian}"
OBSIDIAN_INDEX="$OB_REPO/index.md"

if [ ! -f "$OBSIDIAN_INDEX" ]; then
  exit 0
fi

# 读取 index.md 内容并注入为 system-reminder
CONTENT=$(cat "$OBSIDIAN_INDEX")

cat << EOF
<system-reminder>
以下为用户 Obsidian 知识库索引，供参考定位相关文档：

$(echo "$CONTENT")
</system-reminder>
EOF
