#!/bin/bash
# repo-study-sync-ob.sh — 将 study 项目的 notes 同步到 Obsidian
#
# 功能：
#   1. 扫描 GitHub 项目目录下所有 *-study 项目
#   2. 为缺少 article_id 的笔记自动分配 OBA-xxx 标识
#   3. 为每个有笔记的项目创建 symlink（OB → study/notes）
#   4. 生成/更新每个项目的 index.md 概述页
#   5. 生成/更新 open-source/index.md 总索引
#
# 用法：
#   ./repo-study-sync-ob.sh              # 全量同步
#   ./repo-study-sync-ob.sh --dry-run    # 预览变更
#   ./repo-study-sync-ob.sh --project xxx-study  # 只同步指定项目

set -euo pipefail

# ============ 配置 ============
OB_VAULT="${OBSIDIAN_REPO:-$HOME/jacky-github/jacky-obsidian}"
STUDY_BASE="${GITHUB_PROJECTS_DIR:-$HOME/jacky-github}"
OB_OPEN_SOURCE="$OB_VAULT/wiki/open-source"

# ============ 参数解析 ============
DRY_RUN=false
TARGET_PROJECT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=true; shift ;;
    --project) TARGET_PROJECT="$2"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ============ 工具函数 ============

info() { echo "ℹ️  $*"; }
ok()   { echo "✅ $*"; }
skip() { echo "⏭️  $*"; }
dry()  { echo "🔍 [DRY] $*"; }

run_cmd() {
  if $DRY_RUN; then
    dry "$@"
  else
    "$@"
  fi
}

# 读取 study 项目的元数据
get_meta_value() {
  local meta_file="$1"
  local key="$2"
  if [ -f "$meta_file" ]; then
    python3 -c "import json; d=json.load(open('$meta_file')); print(d.get('$key','—'))" 2>/dev/null || echo "—"
  else
    echo "—"
  fi
}

# 获取项目的简短描述
get_project_description() {
  local claude_md="$1"
  if [ -f "$claude_md" ]; then
    # 读取第一行 > 开头的描述
    sed -n '/^>/p' "$claude_md" | head -1 | sed 's/^> //'
  fi
}

# 统计笔记数（排除 RESEARCH-LOG.md）
count_notes() {
  local notes_dir="$1"
  if [ -d "$notes_dir" ]; then
    find "$notes_dir" -name "*.md" ! -name "RESEARCH-LOG.md" | wc -l | tr -d ' '
  else
    echo "0"
  fi
}

# 生成 8 位随机 ID（小写字母 + 数字）
generate_id() {
  python3 -c "import random,string; print(''.join(random.choices(string.ascii_lowercase+string.digits,k=8)))"
}

# 验证 article_id 在 OB 仓库中全局唯一
is_id_unique() {
  local id="$1"
  local ob_dir="${2:-$OB_VAULT}"
  # 搜索所有 wiki 下的 md 文件
  if [ -d "$ob_dir/wiki" ]; then
    result=$(grep -rh "article_id: $id" "$ob_dir/wiki/" --include="*.md" 2>/dev/null || true)
    [ -z "$result" ]
  else
    true
  fi
}

# 生成全局唯一的 OBA-xxx ID
generate_unique_id() {
  local ob_dir="${1:-$OB_VAULT}"
  local max_attempts=10
  local attempt=0
  while [ $attempt -lt $max_attempts ]; do
    local id="OBA-$(generate_id)"
    if is_id_unique "$id" "$ob_dir"; then
      echo "$id"
      return 0
    fi
    attempt=$((attempt + 1))
  done
  echo "ERROR: 无法生成唯一 ID" >&2
  return 1
}

# 为单个 md 文件分配 article_id（如果缺失）
assign_article_id() {
  local file="$1"
  local ob_dir="${2:-$OB_VAULT}"

  # 检查是否已有 article_id
  if grep -q "^article_id:" "$file"; then
    return 0
  fi

  # 生成唯一 ID
  local new_id
  new_id=$(generate_unique_id "$ob_dir")
  if [ $? -ne 0 ]; then
    echo "  ⚠️ 无法为 $(basename "$file") 生成唯一 ID"
    return 1
  fi

  # 获取今天的日期
  local today
  today=$(date +%Y-%m-%d)

  # 检查文件是否有 frontmatter
  if head -1 "$file" | grep -q "^---"; then
    # 有 frontmatter，在 --- 后面插入 article_id
    # 使用 python 安全地插入到 frontmatter
    python3 -c "
import sys
lines = open('$file').readlines()
# 找到第一个 --- 后插入 article_id
for i, line in enumerate(lines):
    if i > 0 and line.strip() == '---':
        # 在第一个 --- 之后、闭合 --- 之前插入
        break
# 插入到第一行 --- 之后
insert_pos = 1
new_line = 'article_id: $new_id\n'
# 检查 frontmatter 中是否有 article_id
has_article_id = any('article_id:' in l for l in lines[1:i+1] if i > 0)
if not has_article_id:
    lines.insert(insert_pos, new_line)
    open('$file', 'w').writelines(lines)
"
  else
    # 没有 frontmatter，创建新的
    local title
    title=$(head -1 "$file" | sed 's/^# *//')
    python3 -c "
lines = open('$file').readlines()
frontmatter = '''---
article_id: $new_id
tags: [study-note]
type: note
created_at: $today
updated_at: $today
---

'''
open('$file', 'w').write(frontmatter + ''.join(lines))
"
  fi

  echo "$new_id"
}

# ============ 主逻辑 ============

info "开始同步 study 项目到 Obsidian..."

# 确保 OB 目录存在
if [ ! -d "$OB_OPEN_SOURCE" ]; then
  run_cmd mkdir -p "$OB_OPEN_SOURCE"
  ok "创建目录: $OB_OPEN_SOURCE"
fi

# 收集项目数据
declare -a PROJECTS=()
declare -a DESCS=()
declare -a NOTES_COUNTS=()
declare -a SOURCE_REPOS=()

total_notes=0

for dir in "$STUDY_BASE"/*-study; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")

  # 如果指定了项目，只处理该项目
  if [ -n "$TARGET_PROJECT" ] && [ "$name" != "$TARGET_PROJECT" ]; then
    continue
  fi

  notes_count=$(count_notes "$dir/notes")

  # 跳过没有笔记的项目
  if [ "$notes_count" -eq 0 ]; then
    skip "$name — 0 篇笔记，跳过"
    continue
  fi

  source_repo=$(get_meta_value "$dir/.study-meta.json" "sourceRepo")
  desc=$(get_project_description "$dir/CLAUDE.md")
  [ -z "$desc" ] && desc="（暂无描述）"

  PROJECTS+=("$name")
  DESCS+=("$desc")
  NOTES_COUNTS+=("$notes_count")
  SOURCE_REPOS+=("$source_repo")
  total_notes=$((total_notes + notes_count))

  # Step 0: 为缺少 article_id 的笔记分配 ID
  id_count=0
  while IFS= read -r -d '' md_file; do
    # 跳过 RESEARCH-LOG.md
    [ "$(basename "$md_file")" = "RESEARCH-LOG.md" ] && continue
    # 检查是否缺少 article_id
    if ! grep -q "^article_id:" "$md_file"; then
      if $DRY_RUN; then
        dry "为 $(basename "$md_file") 分配 article_id"
      else
        assigned_id=$(assign_article_id "$md_file" "$OB_VAULT")
        if [ $? -eq 0 ] && [ -n "$assigned_id" ]; then
          ok "$name/$(basename "$md_file") → $assigned_id"
          id_count=$((id_count + 1))
        fi
      fi
    fi
  done < <(find "$dir/notes" -name "*.md" -print0 2>/dev/null)

  if [ $id_count -gt 0 ]; then
    info "$name — 分配了 $id_count 个 article_id"
  fi

  # Step 1: 创建项目目录和 symlink
  run_cmd mkdir -p "$OB_OPEN_SOURCE/$name"

  if [ -L "$OB_OPEN_SOURCE/$name/notes" ]; then
    # symlink 已存在，检查是否指向正确
    current_target=$(readlink "$OB_OPEN_SOURCE/$name/notes")
    if [ "$current_target" = "$dir/notes" ]; then
      ok "$name — notes symlink 已正确"
    else
      run_cmd rm "$OB_OPEN_SOURCE/$name/notes"
      run_cmd ln -s "$dir/notes" "$OB_OPEN_SOURCE/$name/notes"
      ok "$name — notes symlink 已更新 → $dir/notes"
    fi
  elif [ -e "$OB_OPEN_SOURCE/$name/notes" ]; then
    info "$name — notes 不是 symlink，跳过"
  else
    run_cmd ln -s "$dir/notes" "$OB_OPEN_SOURCE/$name/notes"
    ok "$name — notes symlink 已创建 → $dir/notes"
  fi

  # 创建 explorer symlink（如果存在）
  if [ -d "$dir/explorer" ]; then
    if [ -L "$OB_OPEN_SOURCE/$name/explorer" ]; then
      current_target=$(readlink "$OB_OPEN_SOURCE/$name/explorer")
      if [ "$current_target" = "$dir/explorer" ]; then
        ok "$name — explorer symlink 已正确"
      else
        run_cmd rm "$OB_OPEN_SOURCE/$name/explorer"
        run_cmd ln -s "$dir/explorer" "$OB_OPEN_SOURCE/$name/explorer"
        ok "$name — explorer symlink 已更新 → $dir/explorer"
      fi
    elif [ -e "$OB_OPEN_SOURCE/$name/explorer" ]; then
      info "$name — explorer 不是 symlink，跳过"
    else
      run_cmd ln -s "$dir/explorer" "$OB_OPEN_SOURCE/$name/explorer"
      ok "$name — explorer symlink 已创建 → $dir/explorer"
    fi
  fi

  # 创建 Question.md symlink（如果存在）
  if [ -f "$dir/Question.md" ]; then
    if [ -L "$OB_OPEN_SOURCE/$name/Question.md" ]; then
      current_target=$(readlink "$OB_OPEN_SOURCE/$name/Question.md")
      if [ "$current_target" = "$dir/Question.md" ]; then
        ok "$name — Question.md symlink 已正确"
      else
        run_cmd rm "$OB_OPEN_SOURCE/$name/Question.md"
        run_cmd ln -s "$dir/Question.md" "$OB_OPEN_SOURCE/$name/Question.md"
        ok "$name — Question.md symlink 已更新 → $dir/Question.md"
      fi
    elif [ -e "$OB_OPEN_SOURCE/$name/Question.md" ]; then
      info "$name — Question.md 不是 symlink，跳过"
    else
      run_cmd ln -s "$dir/Question.md" "$OB_OPEN_SOURCE/$name/Question.md"
      ok "$name — Question.md symlink 已创建 → $dir/Question.md"
    fi
  fi
done

echo ""
info "共 ${#PROJECTS[@]} 个项目，$total_notes 篇笔记"
echo ""

if $DRY_RUN; then
  info " Dry run 模式，未修改任何文件"
  exit 0
fi

# Step 2: 生成 index.md（仅当文件不存在时）
for i in "${!PROJECTS[@]}"; do
  name="${PROJECTS[$i]}"
  index_file="$OB_OPEN_SOURCE/$name/index.md"

  if [ -f "$index_file" ]; then
    skip "$name/index.md — 已存在，不覆盖"
  else
    # 生成简单的 index.md
    source_repo="${SOURCE_REPOS[$i]}"
    desc="${DESCS[$i]}"
    notes="${NOTES_COUNTS[$i]}"

    cat > "$index_file" << EOF
---
tags: [open-source, study]
source_repo: $source_repo
type: project-index
updated_at: $(date +%Y-%m-%d)
---

# $name

> $desc

## 笔记索引

- 📂 [[open-source/$name/notes|notes/]] — 所有研究笔记（symlink，$notes 篇）

## 笔记列表

EOF
    # 列出每个笔记及其 article_id
    study_dir="$STUDY_BASE/$name"
    if [ -d "$study_dir/notes" ]; then
      for md_file in "$study_dir/notes"/*.md; do
        [ -f "$md_file" ] || continue
        [ "$(basename "$md_file")" = "RESEARCH-LOG.md" ] && continue
        note_title=$(grep "^# " "$md_file" | head -1 | sed 's/^# *//')
        [ -z "$note_title" ] && note_title=$(basename "$md_file" .md)
        note_id=$(grep "^article_id:" "$md_file" | head -1 | sed 's/article_id: *//')
        if [ -n "$note_id" ]; then
          echo "- [$note_title](notes/$(basename "$md_file")) \`$note_id\`" >> "$index_file"
        else
          echo "- [$note_title](notes/$(basename "$md_file"))" >> "$index_file"
        fi
      done
    fi
    ok "$name/index.md — 已生成"
  fi
done

# Step 3: 生成总索引
info "生成 open-source/index.md ..."

{
  echo "---"
  echo "tags: [open-source, index]"
  echo "type: index"
  echo "updated_at: $(date +%Y-%m-%d)"
  echo "---"
  echo ""
  echo "# 开源研究"
  echo ""
  echo "> 通过 repo-study 研究的开源项目索引。每个项目通过 symlink 直接引用 study 仓库的 notes，在 OB 中编辑即可同步到 GitHub。"
  echo ""

  # 按类别分组（简单版：全部列在一个表格中）
  echo "| 项目 | 描述 | Notes |"
  echo "|------|------|-------|"
  for i in "${!PROJECTS[@]}"; do
    name="${PROJECTS[$i]}"
    desc="${DESCS[$i]}"
    notes="${NOTES_COUNTS[$i]}"
    # 截断过长描述
    short_desc=$(echo "$desc" | cut -c1-60)
    [ ${#desc} -gt 60 ] && short_desc="${short_desc}..."
    echo "| [[open-source/$name/index\\|$name]] | $short_desc | $notes |"
  done

  echo ""
  echo "## 统计"
  echo ""
  echo "- **项目总数**：${#PROJECTS[@]} 个"
  echo "- **笔记总数**：$total_notes 篇"
  echo "- **Symlink 同步**：所有 notes 目录通过 symlink 引用，OB 中编辑直接同步"
} > "$OB_OPEN_SOURCE/index.md"

ok "open-source/index.md — 已更新"

echo ""
ok "同步完成！"
