#!/bin/bash
# hooks/load-ob-index.sh
# SessionStart Hook：会话开始时自动加载当前项目的 Obsidian 知识索引
# skill: ob-project-log
#
# 渐进式加载逻辑：
# - 如果项目 CLAUDE.md 已有 <!-- ob-index --> 标记 → 只注入简短提示（Level 1 由 CLAUDE.md 承载）
# - 如果没有标记（向后兼容）→ 注入完整项目索引

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

# 检查项目 CLAUDE.md 是否已有 ob-index 标记
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$GIT_ROOT" ] && [ -f "$GIT_ROOT/CLAUDE.md" ]; then
  if grep -q '<!-- ob-index:start -->' "$GIT_ROOT/CLAUDE.md" 2>/dev/null; then
    # CLAUDE.md 已有自动索引标记，Level 1 由 CLAUDE.md 承载
    # 只注入一条简短提示，引导 LLM 使用渐进式加载
    cat << EOF
<system-reminder>
## 项目知识库 (ob-project-log)

当前项目 CLAUDE.md 已包含 Obsidian 知识库索引（Level 1）。
需要详情时：读取 CLAUDE.md 中 \`<!-- ob-index -->\` 区域指向的索引文件（Level 2），再读取具体文章（Level 3）。
用户提到文章 ID（如 OBA-xxx）时，直接定位对应文章并读取。
</system-reminder>
EOF
    exit 0
  fi
fi

# 向后兼容：CLAUDE.md 没有 ob-index 标记，注入完整项目索引
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
- 每篇文章有唯一 ID（如 OBA-k7jm2p9q），用户提到 ID 时直接定位对应文章并读取
</system-reminder>
EOF
