---
name: ob-sync
description: "管理 jacky-github 项目到 Obsidian Vault 的软链接同步，支持 link/unlink/list/doctor 操作"
argument-hint: 'link {project} | unlink {project} | list | doctor'
---

<role>
你是 Obsidian 代码同步管理工具，负责通过软链接把 jacky-github 中的项目接入 Obsidian Vault，让 remotely-save 插件能跨设备同步源码。link 时自动读取项目 .gitignore 并生成对应的 .syncignore 规则，避免同步依赖和构建产物。
</role>

<purpose>
当用户需要把某个 jacky-github 项目同步到另一台电脑时，通过软链接将项目挂载到 Obsidian Vault 的 code/ 目录下，由 remotely-save 自动同步。代码本体保持在原始 Git 仓库位置不变。
</purpose>

<trigger>
ob-sync link article-to-podcast
ob-sync unlink my-project
ob-sync list
ob-sync doctor
ob-sync doctor --fix
开启项目同步
关闭项目同步
查看已同步的项目
检查同步环境
</trigger>

<yolo:config>
  <yolo:mode>auto-advance</yolo:mode>
  <yolo:safety-gates>
    <gate>unlink 操作前需确认软链接存在，避免误操作</gate>
    <gate>doctor --fix 修改 .syncignore 前需展示变更内容</gate>
  </yolo:safety-gates>
</yolo:config>

<gsd:workflow>
  <gsd:meta>
    <name>ob-sync</name>
    <trigger>ob-sync link, ob-sync unlink, ob-sync list, ob-sync doctor</trigger>
    <requires>Bash</requires>
    <constraints>
      <constraint>GITHUB_DIR 固定为 /Users/jiashengwang/jacky-github</constraint>
      <constraint>CODE_DIR 固定为 /Users/jiashengwang/jacky-github/jacky-obsidian/code</constraint>
      <constraint>OBSIDIAN_DIR 固定为 /Users/jiashengwang/jacky-github/jacky-obsidian</constraint>
      <constraint>SYNCIGNORE 固定为 /Users/jiashengwang/jacky-github/jacky-obsidian/.obsidian/plugins/remotely-save/.syncignore</constraint>
      <constraint>只操作软链接，不移动或复制实际文件</constraint>
      <constraint>unlink 只删除软链接本身，不影响原始项目</constraint>
      <constraint>link 时必须读取项目 .gitignore，为每条规则加上 code/{project-name}/ 前缀后追加到 .syncignore</constraint>
      <constraint>unlink 时必须从 .syncignore 中删除对应项目的规则块</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>根据子命令管理项目软链接，实现 Obsidian 按需同步</gsd:goal>

  <gsd:phase name="parse" order="1">
    <gsd:step>解析 $ARGUMENTS，提取子命令（link/unlink/list/doctor）和项目名或标志</gsd:step>
    <gsd:step>若参数为空或子命令无效，展示用法说明</gsd:step>
  </gsd:phase>

  <gsd:phase name="execute" order="2">
    <gsd:step>根据子命令执行对应操作</gsd:step>
  </gsd:phase>
</gsd:workflow>

## 路径配置

| 变量 | 值 |
|------|-----|
| GITHUB_DIR | `/Users/jiashengwang/jacky-github` |
| CODE_DIR | `/Users/jiashengwang/jacky-github/jacky-obsidian/code` |
| OBSIDIAN_DIR | `/Users/jiashengwang/jacky-github/jacky-obsidian` |
| SYNCIGNORE | `/Users/jiashengwang/jacky-github/jacky-obsidian/.obsidian/plugins/remotely-save/.syncignore` |

## 执行逻辑

解析 `$ARGUMENTS` 后按以下逻辑执行：

### `doctor`

健康检查，逐项扫描同步环境并报告状态。支持 `--fix` 自动修复。

**检查项（按顺序执行）：**

#### 检查 1：remotely-save 插件是否安装

```bash
OBSIDIAN_DIR="/Users/jiashengwang/jacky-github/jacky-obsidian"
PLUGIN_DIR="$OBSIDIAN_DIR/.obsidian/plugins/remotely-save"

if [ -f "$PLUGIN_DIR/main.js" ]; then
  echo "  ✅ remotely-save 插件已安装"
else
  echo "  ❌ remotely-save 插件未安装"
  echo "     → 在 Obsidian 中安装 Remotely Save 社区插件"
fi
```

#### 检查 2：remotely-save 是否启用

```bash
if grep -q '"remotely-save"' "$OBSIDIAN_DIR/.obsidian/community-plugins.json" 2>/dev/null; then
  echo "  ✅ remotely-save 插件已启用"
else
  echo "  ❌ remotely-save 插件未启用"
  echo "     → 在 Obsidian 设置 → 社区插件中启用 Remotely Save"
fi
```

#### 检查 3：code/ 目录是否存在

```bash
CODE_DIR="$OBSIDIAN_DIR/code"

if [ -d "$CODE_DIR" ]; then
  echo "  ✅ code/ 目录存在"
else
  echo "  ❌ code/ 目录不存在"
  if [ "$FIX_MODE" = true ]; then
    mkdir -p "$CODE_DIR"
    echo "     → 已自动创建 code/ 目录"
  else
    echo "     → 运行 --fix 自动创建，或手动 mkdir"
  fi
fi
```

#### 检查 4：.syncignore 是否存在且包含通用规则

```bash
SYNCIGNORE="$OBSIDIAN_DIR/.obsidian/plugins/remotely-save/.syncignore"
REQUIRED_PATTERNS=("node_modules" "dist/" ".next/" ".env" ".DS_Store" ".log" ".cache" "coverage")

if [ ! -f "$SYNCIGNORE" ]; then
  echo "  ❌ .syncignore 不存在"
  if [ "$FIX_MODE" = true ]; then
    # 写入默认通用规则（见下方模板）
    write_default_syncignore
    echo "     → 已创建 .syncignore 并写入通用规则"
  else
    echo "     → 运行 --fix 自动创建"
  fi
else
  MISSING=()
  for pattern in "${REQUIRED_PATTERNS[@]}"; do
    grep -Fq "$pattern" "$SYNCIGNORE" || MISSING+=("$pattern")
  done
  if [ ${#MISSING[@]} -eq 0 ]; then
    echo "  ✅ .syncignore 规则完整（通用规则已覆盖）"
  else
    echo "  ⚠️  .syncignore 缺少通用规则：${MISSING[*]}"
    if [ "$FIX_MODE" = true ]; then
      append_missing_patterns
      echo "     → 已补充缺失规则"
    else
      echo "     → 运行 --fix 自动补充"
    fi
  fi
fi
```

#### 检查 5：已链接项目的 .gitignore 是否已同步到 .syncignore

逐个检查 `code/` 下的软链接项目：

```bash
CODE_DIR="$OBSIDIAN_DIR/code"
SYNCIGNORE="$OBSIDIAN_DIR/.obsidian/plugins/remotely-save/.syncignore"

for link in "$CODE_DIR"/*; do
  [ ! -L "$link" ] && continue
  PROJECT=$(basename "$link")
  TARGET=$(readlink "$link")

  # 检查软链接目标是否存在
  if [ ! -d "$TARGET" ]; then
    echo "  ❌ $PROJECT → 软链接目标不存在: $TARGET"
    continue
  fi

  # 检查项目是否有 .gitignore
  GITIGNORE="$TARGET/.gitignore"
  if [ ! -f "$GITIGNORE" ]; then
    echo "  ℹ️  $PROJECT → 无 .gitignore（仅使用通用规则）"
    continue
  fi

  # 检查 .syncignore 中是否有该项目的规则块
  if grep -q "^# >>> $PROJECT$" "$SYNCIGNORE" 2>/dev/null; then
    # 检查规则是否需要更新（对比 .gitignore 行数 vs syncignore 中该块的非注释行数）
    GITIGNORE_COUNT=$(grep -cvE '^\s*$|^#' "$GITIGNORE" 2>/dev/null || echo 0)
    BLOCK_COUNT=$(sed -n "/^# >>> $PROJECT$/,/^# <<< $PROJECT$/p" "$SYNCIGNORE" | grep -cvE '^\s*$|^#' || echo 0)
    if [ "$GITIGNORE_COUNT" != "$BLOCK_COUNT" ]; then
      echo "  ⚠️  $PROJECT → .gitignore 规则已变更，需要更新（$GITIGNORE_COUNT → $BLOCK_COUNT 条）"
      if [ "$FIX_MODE" = true ]; then
        # 删除旧规则块，重新生成
        sed -i '' "/^# >>> $PROJECT$/,/^# <<< $PROJECT$/d" "$SYNCIGNORE"
        generate_gitignore_block "$PROJECT" "$GITIGNORE" >> "$SYNCIGNORE"
        echo "     → 已更新 $PROJECT 的忽略规则"
      else
        echo "     → 运行 --fix 自动更新，或重新 link"
      fi
    else
      echo "  ✅ $PROJECT → .gitignore 规则已同步"
    fi
  else
    echo "  ❌ $PROJECT → 有 .gitignore 但未生成 .syncignore 规则"
    if [ "$FIX_MODE" = true ]; then
      generate_gitignore_block "$PROJECT" "$GITIGNORE" >> "$SYNCIGNORE"
      echo "     → 已生成 $PROJECT 的忽略规则"
    else
      echo "     → 运行 --fix 自动生成"
    fi
  fi
done
```

#### 检查 6：孤立规则（已删除项目但 .syncignore 中残留规则）

```bash
SYNCIGNORE="$OBSIDIAN_DIR/.obsidian/plugins/remotely-save/.syncignore"
CODE_DIR="$OBSIDIAN_DIR/code"

ORPHANS=()
while IFS= read -r line; do
  if [[ "$line" =~ ^#\ >>>\ (.+)$ ]]; then
    PROJECT="${BASH_REMATCH[1]}"
    [ ! -L "$CODE_DIR/$PROJECT" ] && ORPHANS+=("$PROJECT")
  fi
done < <(grep "^# >>> " "$SYNCIGNORE" 2>/dev/null)

if [ ${#ORPHANS[@]} -eq 0 ]; then
  echo "  ✅ 无孤立规则"
else
  echo "  ⚠️  发现孤立规则：${ORPHANS[*]}"
  if [ "$FIX_MODE" = true ]; then
    for p in "${ORPHANS[@]}"; do
      sed -i '' "/^# >>> $p$/,/^# <<< $p$/d" "$SYNCIGNORE"
    done
    echo "     → 已清理 ${#ORPHANS[@]} 个孤立规则"
  else
    echo "     → 运行 --fix 自动清理"
  fi
fi
```

#### 检查 7：已链接项目总量和估算文件数

```bash
LINK_COUNT=$(find "$CODE_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')
echo "  ℹ️  已链接项目：$LINK_COUNT 个"

# 统计 code/ 下可能被同步的文件数（排除 .syncignore 中的目录）
if command -v fd &>/dev/null; then
  FILE_COUNT=$(fd --type f --ignore-file "$SYNCIGNORE" . "$CODE_DIR" 2>/dev/null | wc -l | tr -d ' ')
  echo "  ℹ️  预估同步文件数：$FILE_COUNT 个"
else
  TOTAL=$(find -L "$CODE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
  echo "  ℹ️  code/ 下总文件数：$TOTAL 个（含忽略目录，实际同步数更少）"
fi
```

**`--fix` 模式说明：**

`--fix` 会自动修复以下问题（不涉及破坏性操作）：
- 创建缺失的 `code/` 目录
- 创建 `.syncignore` 并写入通用规则
- 补充缺失的通用忽略模式
- 为已链接项目生成 .gitignore → .syncignore 规则
- 更新已变更的 .gitignore 规则
- 清理孤立规则

**不会自动修复的（需用户操作）：**
- 安装/启用 remotely-save 插件

**默认通用规则模板：**

当 `.syncignore` 不存在时，`--fix` 会写入以下内容：

```
# code/ 目录下项目的忽略规则
# 对应 .gitignore 常见模式，避免同步大量依赖和构建产物

# === 依赖目录 ===
code/**/node_modules/**
code/**/.pnp
code/**/.pnp.js
code/**/vendor/bundle/**

# === 构建产物 ===
code/**/dist/**
code/**/build/**
code/**/.next/**
code/**/.nuxt/**
code/**/.output/**
code/**/.svelte-kit/**
code/**/.vercel/**
code/**/.netlify/**

# === 缓存 ===
code/**/.cache/**
code/**/.turbo/**
code/**/.eslintcache
code/**/.stylelintcache
code/**/.tsbuildinfo

# === 测试覆盖率 ===
code/**/coverage/**
code/**/.nyc_output/**

# === IDE / 编辑器 ===
code/**/.idea/**
code/**/.vscode/**
code/**/*.swp
code/**/*.swo

# === 系统文件 ===
code/**/.DS_Store
code/**/Thumbs.db
code/**/desktop.ini

# === 日志 ===
code/**/*.log
code/**/npm-debug.log*
code/**/yarn-debug.log*
code/**/yarn-error.log*
code/**/pnpm-debug.log*

# === 环境和密钥 ===
code/**/.env
code/**/.env.*
code/**/.env.local
code/**/.env.*.local

# === 大型二进制文件 ===
code/**/*.wasm
code/**/*.exe
code/**/*.dll
```

**辅助函数：**

```bash
# 从 .gitignore 生成 .syncignore 规则块
generate_gitignore_block() {
  local PROJECT="$1"
  local GITIGNORE="$2"
  echo "# >>> $PROJECT"
  echo "# 自动生成自 $PROJECT/.gitignore"
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    echo "code/$PROJECT/$line"
  done < "$GITIGNORE"
  echo "# <<< $PROJECT"
}
```

### `link {project-name}`

```bash
GITHUB_DIR="/Users/jiashengwang/jacky-github"
CODE_DIR="/Users/jiashengwang/jacky-github/jacky-obsidian/code"
SYNCIGNORE="/Users/jiashengwang/jacky-github/jacky-obsidian/.obsidian/plugins/remotely-save/.syncignore"
PROJECT="<project-name>"

# 1. 检查源项目是否存在
[ ! -d "$GITHUB_DIR/$PROJECT" ] && echo "❌ 项目不存在: $GITHUB_DIR/$PROJECT" && exit 1

# 2. 检查是否已链接
[ -L "$CODE_DIR/$PROJECT" ] && echo "⚠️  已存在软链接: $PROJECT" && exit 0

# 3. 创建软链接
ln -s "$GITHUB_DIR/$PROJECT" "$CODE_DIR/$PROJECT"

# 4. 读取项目 .gitignore，生成 .syncignore 规则
if [ -f "$GITHUB_DIR/$PROJECT/.gitignore" ]; then
  # 删除旧的同项目规则块（如果存在）
  sed -i '' "/^# >>> $PROJECT$/,/^# <<< $PROJECT$/d" "$SYNCIGNORE"

  # 生成新的规则块
  {
    echo "# >>> $PROJECT"
    echo "# 自动生成自 $PROJECT/.gitignore"
    while IFS= read -r line; do
      # 跳过空行和注释
      [[ -z "$line" || "$line" == \#* ]] && continue
      echo "code/$PROJECT/$line"
    done < "$GITHUB_DIR/$PROJECT/.gitignore"
    echo "# <<< $PROJECT"
  } >> "$SYNCIGNORE"
  echo "✅ 已开启同步: $PROJECT（已同步 .gitignore 规则）"
else
  echo "✅ 已开启同步: $PROJECT（无 .gitignore，仅使用通用忽略规则）"
fi
```

### `unlink {project-name}`

```bash
CODE_DIR="/Users/jiashengwang/jacky-github/jacky-obsidian/code"
SYNCIGNORE="/Users/jiashengwang/jacky-github/jacky-obsidian/.obsidian/plugins/remotely-save/.syncignore"
PROJECT="<project-name>"

# 1. 检查软链接是否存在（安全门）
[ ! -L "$CODE_DIR/$PROJECT" ] && echo "❌ 未找到软链接: $PROJECT" && exit 1

# 2. 删除软链接
rm "$CODE_DIR/$PROJECT"

# 3. 从 .syncignore 中删除对应项目的规则块
sed -i '' "/^# >>> $PROJECT$/,/^# <<< $PROJECT$/d" "$SYNCIGNORE"
echo "✅ 已关闭同步: $PROJECT"
```

### `list`

```bash
CODE_DIR="/Users/jiashengwang/jacky-github/jacky-obsidian/code"

echo "📦 当前已同步的项目："
ls -la "$CODE_DIR" | grep "^l" | awk '{print "  •", $9}'
```

### 无参数 / 未知子命令

```
用法：
  /ob-sync link {project-name}    开启项目同步（创建软链接 + 同步 .gitignore）
  /ob-sync unlink {project-name}  关闭项目同步（删除软链接 + 清理忽略规则）
  /ob-sync list                   查看所有已同步项目
  /ob-sync doctor                 检查同步环境健康状态
  /ob-sync doctor --fix           检查并自动修复问题
```
