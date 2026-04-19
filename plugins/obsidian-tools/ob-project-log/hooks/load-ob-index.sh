#!/bin/bash
# hooks/load-ob-index.sh
# SessionStart Hook：会话开始时自动加载当前项目的 Obsidian 知识索引
# skill: ob-project-log

# 获取项目名称：优先 git remote basename，其次目录名
PROJECT_NAME=$(basename "$(git remote get-url origin 2>/dev/null)" .git 2>/dev/null)
if [ -z "$PROJECT_NAME" ]; then
  PROJECT_NAME=$(basename "$(pwd)")
fi

# 优先使用 OBSIDIAN_REPO 环境变量，其次尝试 CLAUDE.md 中配置的路径，最后回退
OB_REPO="${OBSIDIAN_REPO}"
if [ -z "$OB_REPO" ] || [ ! -d "$OB_REPO" ]; then
  # 尝试从全局 CLAUDE.md 读取 OBSIDIAN_REPO
  CLAUDE_MD="$HOME/.claude/CLAUDE.md"
  if [ -f "$CLAUDE_MD" ]; then
    OB_REPO=$(grep -m1 'OBSIDIAN_REPO.*|.*`/' "$CLAUDE_MD" | sed -n 's/.*`\([^`]*\)`.*/\1/p' | head -1)
  fi
  # 最终回退
  if [ -z "$OB_REPO" ] || [ ! -d "$OB_REPO" ]; then
    OB_REPO="$HOME/jacky-github/jacky-obsidian"
  fi
fi

PROJECT_INDEX="$OB_REPO/wiki/projects/$PROJECT_NAME/index.md"

if [ ! -f "$PROJECT_INDEX" ]; then
  exit 0
fi

# 读取项目知识索引
CONTENT=$(cat "$PROJECT_INDEX")

cat << EOF
<system-reminder>
## 项目知识库 (ob-project-log)

当前项目在 Obsidian 中有沉淀的知识文章，可在需要时用 \`Read\` 读取详细内容：

$(echo "$CONTENT")

使用方式：
- 需要了解某方面知识时，读取对应文件获取详情
- 用户说"追问文章"时，进入浏览追问模式
</system-reminder>
EOF
