# TODO Skill 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个项目级持久化任务追踪 Skill，管理临时代码清理、待办事项、想法和临时文件，支持跨会话恢复

**Architecture:** Skill 由一个 SKILL.md 主文档（Claude 解读执行的指令集）、4 个 hooks 脚本（SessionStart/Stop/PreCompact/PreToolUse 自动化）和 3 个参考文档组成。数据存储在项目根目录的 `.todo.md` Markdown 文件中。

**Tech Stack:** Markdown (SKILL.md)、Bash (hooks)、Claude Code hooks API

**Spec:** `docs/superpowers/specs/2026-04-25-todo-skill-design.md`

**Skill 位置:** `/Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/`

**Workdir:** `/Users/jiashengwang/jacky-github/jacky-skills`

---

## File Structure

```
plugins/dev-tools/todo/
├── SKILL.md                              # 主文档：Claude 解读执行的完整指令
├── hooks/                                # Hook 自动化脚本
│   ├── hooks.json                        # Hook 事件注册
│   ├── session-start.sh                  # SessionStart：注入 TODO 提醒
│   ├── stop-check.sh                     # Stop：检查未清理项
│   ├── pre-compact.sh                    # PreCompact：保存进展提醒
│   └── pre-tool-use.sh                   # PreToolUse：临时文件检测
└── references/                           # 详细参考文档
    ├── file-format.md                    # .todo.md 格式说明
    ├── commands.md                       # 命令详细说明
    └── setup-guide.md                    # Setup 配置指南
```

> **约定**：所有文件路径默认相对于 WORKDIR。每个 Task 中的 code block 内容即为要写入文件的实际内容（不含首尾的 ``` 标记）。

---

## Chunk 1: Core Skill - SKILL.md

### Task 1: 创建目录结构

**Files:**
- Create: `plugins/dev-tools/todo/hooks/` (目录)
- Create: `plugins/dev-tools/todo/references/` (目录)

- [ ] **Step 1: 创建所有目录**

```bash
mkdir -p /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks
mkdir -p /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/references
```

- [ ] **Step 2: 验证目录结构**

```bash
ls -la /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/
```

Expected: 显示 hooks/ 和 references/ 目录

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/
git commit -m "chore: 创建 todo skill 目录结构"
```

---

### Task 2: 编写 SKILL.md — Frontmatter 和核心定义

**Files:**
- Create: `plugins/dev-tools/todo/SKILL.md`

**说明**：使用 Write 工具创建文件，将以下内容（从 `---` 开始到 `</gsd:goal>` 结束）写入文件。

- [ ] **Step 1: 创建 SKILL.md**

写入文件 `plugins/dev-tools/todo/SKILL.md`，内容如下：

```
---
name: todo
description: "项目级 TODO 追踪：管理临时代码清理、待办事项、想法和临时文件，支持跨会话恢复"
argument-hint: '[add|done|clean|list|setup|save|restore|add-file] [内容]'
---

<role>你是一个任务管理专家，帮助用户追踪和管理项目中的临时代码、待办事项、想法和临时文件。</role>

<purpose>当用户需要管理项目中的临时任务、记录想法、追踪临时代码或恢复上下文时，使用此 skill。</purpose>

<trigger>
用户说 /todo、TODO、任务列表、临时文件清理、恢复上下文 时触发
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>todo</name>
    <trigger>/todo, TODO, 任务列表, 临时文件, 清理, 想法</trigger>
    <requires>Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion</requires>
    <checkpoints>
      <checkpoint order="1">命令解析完成</checkpoint>
      <checkpoint order="2">文件操作确认</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>所有清理操作（delete/git-checkout）必须经过用户确认</constraint>
      <constraint>删除操作必须校验路径在项目目录内</constraint>
      <constraint>不修改 .todo.md 之外的任何项目文件（setup 命令除外）</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>为项目提供持久化的任务追踪，管理临时代码、待办事项、想法和临时文件</gsd:goal>
```

- [ ] **Step 2: 验证文件已创建**

```bash
head -20 /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
```

Expected: 显示 frontmatter（`---`、`name: todo`）和 XML 标签（`<role>`、`<gsd:workflow>`）

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/SKILL.md
git commit -m "feat(todo): 添加 SKILL.md frontmatter 和核心定义"
```

---

### Task 3: 编写 SKILL.md — Phase 1: 命令解析

**Files:**
- Modify: `plugins/dev-tools/todo/SKILL.md` (追加到 `</gsd:goal>` 行之后)

**说明**：使用 Edit 工具，在 `</gsd:goal>` 行之后追加以下内容。

- [ ] **Step 1: 追加 Phase 1**

在 `</gsd:goal>` 行之后追加以下内容：

```
  <gsd:phase name="parse" order="1">
    <gsd:step>读取用户输入的参数，解析子命令</gsd:step>
    <gsd:step>支持子命令：add, done, clean, list, setup, save, restore, add-file</gsd:step>
    <gsd:step>解析选项：--cleanup, --idea, @file:, @action:</gsd:step>
    <gsd:step>如果没有子命令，默认执行 list</gsd:step>
    <checkpoint>命令解析完成，确认操作意图</checkpoint>
  </gsd:phase>
```

- [ ] **Step 2: 验证追加成功**

```bash
tail -5 /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
```

Expected: 显示 `</gsd:phase>`

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/SKILL.md
git commit -m "feat(todo): 添加 SKILL.md Phase 1 命令解析"
```

---

### Task 4: 编写 SKILL.md — Phase 2: 执行操作（所有命令）

**Files:**
- Modify: `plugins/dev-tools/todo/SKILL.md` (追加到 Phase 1 的 `</gsd:phase>` 行之后)

**说明**：使用 Edit 工具，在 Phase 1 的 `</gsd:phase>` 行之后追加。

> **注意**：Phase 2 包含所有命令的执行逻辑（add/list/done/clean/save/restore/setup），Phase 3 仅负责结果反馈和状态更新，与 Spec 保持一致。

- [ ] **Step 1: 追加 Phase 2**

在 Phase 1 的 `</gsd:phase>` 行之后追加以下内容：

```
  <gsd:phase name="execute" order="2">
    <gsd:step>检查 .todo.md 是否存在，不存在则创建初始模板</gsd:step>
    <gsd:step>
根据子命令执行对应操作：

**add 命令：**
1. 确定目标分区：`--cleanup` → 🧹 Cleanup，`--idea` → 💡 Ideas，默认 → 📋 Todo
2. 解析内容中的 @file: 和 @action: 标记
3. 在目标分区末尾添加 `- [ ] <内容>`
4. 更新 `最后更新` 时间戳

**add-file 命令：**
1. 验证文件路径在项目内
2. 在 📁 Temp Files 分区添加 `- [ ] 删除 <filename> @file:<path> @action:delete`

**list 命令：**
1. 读取 .todo.md 全部分区
2. 按分类展示未完成项，统计各分区数量

**done 命令：**
1. 查找匹配的项（支持编号或关键词）
2. 将 `- [ ]` 改为 `- [x]`
    </gsd:step>
    <gsd:step>
**clean 命令：**
1. 读取 🧹 Cleanup 和 📁 Temp Files 分区的未完成项
2. 对每项执行路径安全校验：
   - 解析 @file: 路径为绝对路径
   - 验证绝对路径以项目根目录开头
   - 验证路径不包含 .. 穿越
   - 验证文件是否存在
   - 不安全的项标注 ⚠️
3. 展示待清理项列表，按编号排列
4. 使用 AskUserQuestion 让用户选择要清理的项
5. 执行对应操作：
   - @action:delete → 删除文件（仅项目内路径）
   - @action:git-checkout → `git checkout -- <file>`（node_modules 需二次确认）
   - 无 @action → 仅提醒手动处理
    </gsd:step>
    <gsd:step>
**save 命令：**
1. 在 📋 Todo 分区追加进展描述作为新项
2. 更新时间戳

**restore 命令：**
1. 读取 .todo.md 全部内容
2. 展示各分区的未完成项摘要
3. 建议用户下一步操作（如先 /todo clean）
    </gsd:step>
    <gsd:step>
**setup 命令：**
1. 读取 hooks/hooks.json 配置
2. 将 hooks 配置合并到 ~/.claude/settings.json 中
3. 在当前项目根目录创建 .todo-enabled 开关文件
4. 如果 .todo.md 不存在，创建初始模板
5. 询问用户是否将 .todo.md 和 .todo-enabled 加入 .gitignore
    </gsd:step>
    <checkpoint>操作完成，反馈结果</checkpoint>
  </gsd:phase>
```

- [ ] **Step 2: 验证追加成功**

```bash
tail -5 /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
```

Expected: 显示 `</gsd:phase>`

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/SKILL.md
git commit -m "feat(todo): 添加 SKILL.md Phase 2 执行操作（所有命令）"
```

---

### Task 5: 编写 SKILL.md — Phase 3 + 关闭标签

**Files:**
- Modify: `plugins/dev-tools/todo/SKILL.md` (追加到 Phase 2 的 `</gsd:phase>` 行之后)

**说明**：Phase 3 仅负责结果反馈和状态更新，与 Spec 保持一致。

- [ ] **Step 1: 追加 Phase 3 + 文件格式 + 安全规则 + 关闭标签**

在 Phase 2 的 `</gsd:phase>` 行之后追加以下内容：

```
  <gsd:phase name="cleanup" order="3">
    <gsd:step>展示操作结果</gsd:step>
    <gsd:step>对于 clean 操作，标记已清理的项为 [x]</gsd:step>
    <gsd:step>更新 .todo.md 最后更新时间戳</gsd:step>
  </gsd:phase>
</gsd:workflow>

## .todo.md 文件格式

> 详细格式说明见 references/file-format.md

文件存储在项目根目录 `.todo.md`，包含四个分区：

## 🧹 Cleanup（需要清理的临时代码）
## 📋 Todo（待办事项）
## 💡 Ideas（想法记录）
## 📁 Temp Files（需要删除的临时文件）

每条项格式：`- [ ] 描述内容 @file:path @action:type`

## 安全规则

> 详细安全说明见 references/setup-guide.md

1. 所有清理操作必须经用户确认
2. 路径安全校验：解析后绝对路径必须在项目目录内
3. 禁止操作绝对路径（以 / 开头）
4. node_modules 的 git-checkout 需二次确认
5. 所有 hook 脚本以 exit 0 结束
```

- [ ] **Step 2: 验证 SKILL.md 完整性**

```bash
wc -l /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
tail -3 /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
```

Expected: 约 120-140 行，最后 3 行显示安全规则

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/SKILL.md
git commit -m "feat(todo): 添加 SKILL.md Phase 3 + 文件格式 + 安全规则"
```

---

## Chunk 2: Hook Scripts

### Task 6: 创建 hooks.json

**Files:**
- Create: `plugins/dev-tools/todo/hooks/hooks.json`

- [ ] **Step 1: 创建 hooks.json**

写入文件 `plugins/dev-tools/todo/hooks/hooks.json`，内容如下：

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/stop-check.sh"
      }]
    }],
    "PreCompact": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/pre-compact.sh"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Bash",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/pre-tool-use.sh \"$TOOL_INPUT\""
      }]
    }]
  }
}
```

- [ ] **Step 2: 验证 JSON 有效**

```bash
python3 -m json.tool /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/hooks.json > /dev/null && echo "JSON valid"
```

Expected: `JSON valid`

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/hooks/hooks.json
git commit -m "feat(todo): 添加 hooks.json 事件注册配置"
```

---

### Task 7: 编写 session-start.sh

**Files:**
- Create: `plugins/dev-tools/todo/hooks/session-start.sh`

- [ ] **Step 1: 创建 session-start.sh**

写入文件 `plugins/dev-tools/todo/hooks/session-start.sh`，内容如下：

```bash
#!/bin/bash
# session-start.sh — SessionStart Hook：注入 TODO 提醒
# 功能：会话启动时检查 .todo.md 并注入未完成项统计

TODO_FILE="$(pwd)/.todo.md"
ENABLED_FILE="$(pwd)/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 守卫：检查 .todo.md 是否存在
[ -f "$TODO_FILE" ] || exit 0

# 统计各分区未完成项数量
cleanup_count=$(awk '/^## 🧹 Cleanup/,/^## [📋💡📁]|^$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)
todo_count=$(awk '/^## 📋 Todo/,/^## [🧹💡📁]|^$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)
ideas_count=$(awk '/^## 💡 Ideas/,/^## [🧹📋📁]|^$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)
temp_count=$(awk '/^## 📁 Temp Files/,/^## [🧹📋💡]|$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)

total=$((cleanup_count + todo_count + ideas_count + temp_count))

# 如果没有未完成项，不注入
[ "$total" -eq 0 ] && exit 0

# 注入提醒
cat <<EOF
<system-reminder>
## TODO 提醒 (todo-skill)

当前项目有 ${total} 个待处理项：
  - 🧹 ${cleanup_count} 个清理项
  - 📋 ${todo_count} 个待办项
  - 💡 ${ideas_count} 个想法
  - 📁 ${temp_count} 个临时文件

使用 \`/todo list\` 查看详情，\`/todo restore\` 恢复上下文，\`/todo clean\` 执行清理
</system-reminder>
EOF

exit 0
```

- [ ] **Step 2: 设置可执行权限并验证**

```bash
chmod +x /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/session-start.sh
ls -la /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/session-start.sh
```

Expected: 显示 `-rwxr-xr-x` 权限

- [ ] **Step 3: 功能验证（可选）**

```bash
# 创建临时测试文件
cd /tmp && mkdir -p test-todo && cd test-todo
echo "enabled" > .todo-enabled
cat > .todo.md <<'TESTEOF'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

- [ ] 移除 console.log @file:src/app.tsx

## 📋 Todo

- [ ] 完成测试

## 💡 Ideas

- [ ] 想法1

## 📁 Temp Files

- [ ] 删除临时文件 @file:test.tsx @action:delete
TESTEOF

# 运行脚本验证
bash /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/session-start.sh
# 清理
rm -rf /tmp/test-todo
```

Expected: 输出包含 `4 个待处理项` 的 system-reminder

- [ ] **Step 4: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/hooks/session-start.sh
git commit -m "feat(todo): 添加 SessionStart hook 脚本"
```

---

### Task 8: 编写 stop-check.sh

**Files:**
- Create: `plugins/dev-tools/todo/hooks/stop-check.sh`

- [ ] **Step 1: 创建 stop-check.sh**

写入文件 `plugins/dev-tools/todo/hooks/stop-check.sh`，内容如下：

```bash
#!/bin/bash
# stop-check.sh — Stop Hook：检查未清理项
# 功能：AI 响应结束时检查是否有未清理的 cleanup/temp-file 项

SESSION_PID="$PPID"
TODO_FILE="$(pwd)/.todo.md"
ENABLED_FILE="$(pwd)/.todo-enabled"
MARKER="/tmp/todo-checked-${SESSION_PID}"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 守卫：检查 .todo.md 是否存在
[ -f "$TODO_FILE" ] || exit 0

# 防死循环：如果刚处理过，允许停止
if [ -f "$MARKER" ]; then
  rm -f "$MARKER"
  exit 0
fi

# 检查 cleanup 和 temp-files 分区是否有未完成项
cleanup_pending=$(awk '/^## 🧹 Cleanup/,/^## [📋💡📁]|^$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)
temp_pending=$(awk '/^## 📁 Temp Files/,/^## [🧹📋💡]|$/' "$TODO_FILE" | grep -c '^- \[ \]' 2>/dev/null || echo 0)

pending=$((cleanup_pending + temp_pending))

# 如果没有待清理项，放行
[ "$pending" -eq 0 ] && exit 0

# 有待清理项，创建标记并注入提醒
touch "$MARKER"

cat <<EOF
<system-reminder>
## TODO 清理提醒 (todo-skill)

还有 ${pending} 个待清理项未处理（${cleanup_pending} 个代码清理 + ${temp_pending} 个临时文件）。
建议使用 \`/todo clean\` 执行清理，避免遗忘。
</system-reminder>
EOF

exit 0
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/stop-check.sh
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/hooks/stop-check.sh
git commit -m "feat(todo): 添加 Stop hook 脚本（防死循环）"
```

---

### Task 9: 编写 pre-compact.sh

**Files:**
- Create: `plugins/dev-tools/todo/hooks/pre-compact.sh`

- [ ] **Step 1: 创建 pre-compact.sh**

写入文件 `plugins/dev-tools/todo/hooks/pre-compact.sh`，内容如下：

```bash
#!/bin/bash
# pre-compact.sh — PreCompact Hook：保存进展提醒
# 功能：上下文压缩前提醒 Claude 将进展写入 .todo.md

TODO_FILE="$(pwd)/.todo.md"
ENABLED_FILE="$(pwd)/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 守卫：检查 .todo.md 是否存在
[ -f "$TODO_FILE" ] || exit 0

# 注入提醒，不阻止压缩
cat <<EOF
<system-reminder>
## TODO 上下文保存提醒 (todo-skill)

上下文即将压缩。如果有未保存的进展，建议使用 \`/todo save "进展描述"\` 保存到 .todo.md。
这样即使上下文被压缩，任务信息也不会丢失。
</system-reminder>
EOF

exit 0
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/pre-compact.sh
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/hooks/pre-compact.sh
git commit -m "feat(todo): 添加 PreCompact hook 脚本"
```

---

### Task 10: 编写 pre-tool-use.sh

**Files:**
- Create: `plugins/dev-tools/todo/hooks/pre-tool-use.sh`

**说明**：此脚本修复了 JSON 解析问题——静默提取 file_path/command，不在 stdout 打印中间结果。

- [ ] **Step 1: 创建 pre-tool-use.sh**

写入文件 `plugins/dev-tools/todo/hooks/pre-tool-use.sh`，内容如下：

```bash
#!/bin/bash
# pre-tool-use.sh — PreToolUse Hook：临时文件检测
# 功能：检测 Write/Bash 操作是否创建临时文件，提醒加入追踪
# Matcher: Write|Bash

INPUT="$1"
ENABLED_FILE="$(pwd)/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 从输入中提取文件路径（静默，不在 stdout 打印中间结果）
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    fp = d.get('file_path', '')
    if fp:
        print(fp)
    else:
        cmd = d.get('command', '')
        print(cmd)
except:
    pass
" 2>/dev/null)

# 如果没有提取到内容，放行
[ -z "$FILE_PATH" ] && exit 0

# 提取文件名
FILENAME=$(basename "$FILE_PATH" 2>/dev/null)
[ -z "$FILENAME" ] && exit 0

# 临时文件匹配模式
MATCHED=false
for pattern in "test-*" "tmp-*" "debug-*" "*.tmp" "*.bak" "*.temp"; do
  case "$FILENAME" in
    $pattern)
      MATCHED=true
      break
      ;;
  esac
done

# 如果不匹配，放行
[ "$MATCHED" = false ] && exit 0

# 匹配到临时文件，注入提醒
cat <<EOF
<system-reminder>
## TODO 临时文件检测 (todo-skill)

检测到可能创建临时文件: ${FILENAME}
建议使用 \`/todo add-file ${FILENAME}\` 将此文件加入追踪列表，防止遗忘清理。
</system-reminder>
EOF

exit 0
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/pre-tool-use.sh
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/hooks/pre-tool-use.sh
git commit -m "feat(todo): 添加 PreToolUse hook 脚本（临时文件检测）"
```

---

## Chunk 3: Reference Documents

### Task 11: 编写 references/file-format.md

**Files:**
- Create: `plugins/dev-tools/todo/references/file-format.md`

- [ ] **Step 1: 创建 file-format.md**

写入文件 `plugins/dev-tools/todo/references/file-format.md`，内容如下：

```markdown
# .todo.md 文件格式说明

## 概述

`.todo.md` 是 todo skill 的数据存储文件，存储在项目根目录。使用纯 Markdown 格式，Git 友好，可手动编辑。

## 完整模板

```markdown
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: YYYY-MM-DD

## 🧹 Cleanup

- [ ] 移除 `src/app.tsx` 中的 console.log 调试代码 @file:src/app.tsx
- [ ] 恢复 node_modules/lodash/index.js 的修改 @file:node_modules/lodash/index.js @action:git-checkout

## 📋 Todo

- [ ] 完成用户认证模块的单元测试
- [x] 修复登录页面的样式问题
- [ ] 重构 API 错误处理逻辑

## 💡 Ideas

- [ ] 可以用 WebSocket 实现实时通知功能
- [ ] 考虑引入 Zustand 替代 Context 做状态管理

## 📁 Temp Files

- [ ] 删除临时测试文件 @file:test-debug.tsx @action:delete
- [ ] 删除调试用的 HTML 文件 @file:debug.html @action:delete
```

## 四个分区

| 分区 | 标题 | 用途 |
|------|------|------|
| 🧹 Cleanup | `## 🧹 Cleanup` | 需要清理的临时代码（console.log、node_modules 修改等） |
| 📋 Todo | `## 📋 Todo` | 常规待办事项 |
| 💡 Ideas | `## 💡 Ideas` | 未来可能实现的想法 |
| 📁 Temp Files | `## 📁 Temp Files` | 需要删除的临时文件 |

## 条目格式

### 基本格式

```
- [ ] 描述文字
```

- `- [ ]` 表示未完成
- `- [x]` 表示已完成

### 标记系统

| 标记 | 说明 | 示例 |
|------|------|------|
| `@file:<path>` | 关联的文件路径（相对路径） | `@file:src/app.tsx` |
| `@action:delete` | 清理动作：删除文件 | `@action:delete` |
| `@action:git-checkout` | 清理动作：恢复 Git 修改 | `@action:git-checkout` |

### 标记规则

1. `@file:` 后面跟相对路径（从项目根目录开始）
2. `@action:` 必须和 `@file:` 搭配使用
3. 没有 `@file:` 的条目是纯文本，不支持自动清理
4. 同一条目可以有多个标记

## 时间戳

文件头部的 `> 最后更新: YYYY-MM-DD` 在每次修改时自动更新。
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/references/file-format.md
git commit -m "docs(todo): 添加 .todo.md 文件格式参考文档"
```

---

### Task 12: 编写 references/commands.md

**Files:**
- Create: `plugins/dev-tools/todo/references/commands.md`

- [ ] **Step 1: 创建 commands.md**

写入文件 `plugins/dev-tools/todo/references/commands.md`，内容如下：

```markdown
# 命令详细说明

## 命令列表

| 命令 | 用途 | 参数 |
|------|------|------|
| `/todo add <内容>` | 添加 TODO 项（默认 Todo 区） | `--cleanup` `--idea` 指定分类 |
| `/todo add --cleanup <内容>` | 添加清理项 | 支持 `@file:` 和 `@action:` |
| `/todo add --idea <内容>` | 添加想法 | 纯文本 |
| `/todo add-file <path>` | 添加临时文件追踪 | 自动添加 `@action:delete` |
| `/todo done <编号或关键词>` | 标记完成 | 支持编号或关键词匹配 |
| `/todo clean` | 执行清理（列出 + 确认） | 交互式选择 |
| `/todo list` | 显示当前所有项 | 按分类展示 |
| `/todo setup` | 安装 hooks | 注入到 settings.json |
| `/todo save [进展描述]` | 保存当前进展 | 写入上下文信息 |
| `/todo restore` | 从 .todo.md 恢复上下文 | 读取并展示 |

## 详细说明

### /todo add

添加新的 TODO 项。

**默认行为**：添加到 `## 📋 Todo` 分区

**选项**：
- `--cleanup`：添加到 `## 🧹 Cleanup` 分区
- `--idea`：添加到 `## 💡 Ideas` 分区

**内联标记**：
- `@file:<path>`：关联文件路径
- `@action:<type>`：指定清理动作

**示例**：
```
/todo add 完成单元测试
/todo add --cleanup 移除 console.log @file:src/app.tsx
/todo add --cleanup 恢复 node_modules 修改 @file:node_modules/lodash/index.js @action:git-checkout
/todo add --idea 用 WebSocket 实现实时通知
```

### /todo add-file

将文件添加到临时文件追踪列表。

**行为**：
1. 验证文件路径在项目内
2. 自动添加 `@action:delete` 标记
3. 添加到 `## 📁 Temp Files` 分区

**示例**：
```
/todo add-file test-debug.tsx
/todo add-file tmp/output.json
```

### /todo done

标记 TODO 项为已完成。

**匹配方式**：
- 编号：按分区内的顺序编号
- 关键词：模糊匹配描述文字

**示例**：
```
/todo done 3
/todo done 单元测试
```

### /todo clean

执行清理操作。

**流程**：
1. 读取 🧹 Cleanup 和 📁 Temp Files 的未完成项
2. 路径安全校验
3. 展示列表并等待用户选择
4. 执行清理并标记为已完成

**路径安全校验**：
- 必须在项目目录内
- 禁止路径穿越（..）
- 禁止绝对路径
- node_modules 操作需二次确认

### /todo list

展示当前所有 TODO 项。

**输出格式**：按分区展示，统计各分区数量。

### /todo setup

安装 hooks 到 Claude Code。

**行为**：
1. 将 hooks.json 配置合并到 `~/.claude/settings.json`
2. 创建 `.todo-enabled` 开关文件
3. 如有必要创建 `.todo.md` 初始文件
4. 询问是否加入 `.gitignore`

### /todo save

保存当前进展到 .todo.md。

**用途**：上下文压缩前保存关键信息。

**示例**：
```
/todo save 完成了 API 集成，还有错误处理未完成
```

### /todo restore

从 .todo.md 恢复上下文。

**行为**：展示各分区的未完成项，建议下一步操作。

## 使用场景示例

### 场景 1：长任务中的临时代码管理

```
用户: /todo add --cleanup 添加了 console.log 调试 @file:src/app.tsx
Claude: ✅ 已添加清理项

...（长时间工作）...

用户: /todo clean
Claude: 🔍 待清理项：
  [1] 移除 src/app.tsx 的 console.log @file:src/app.tsx
确认清理？[全部/选择编号/取消]
用户: 1
Claude: ✅ 已清理 src/app.tsx 的 console.log
```

### 场景 2：上下文恢复

```
# 新会话启动，SessionStart hook 注入提醒
用户: /todo restore
Claude: 📋 从 .todo.md 恢复上下文：
  - 🧹 1 个清理项
  - 📋 2 个待办项
  建议先 /todo clean 清理临时项
```

### 场景 3：想法记录

```
用户: /todo add --idea 可以用 WebSocket 实现实时通知
Claude: ✅ 已记录想法
```

### 场景 4：上下文压缩前保存

```
用户: /todo save 完成了用户认证模块的 API 集成，还有错误处理未完成
Claude: ✅ 进展已保存到 .todo.md
```
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/references/commands.md
git commit -m "docs(todo): 添加命令详细说明参考文档（含使用场景）"
```

---

### Task 13: 编写 references/setup-guide.md

**Files:**
- Create: `plugins/dev-tools/todo/references/setup-guide.md`

- [ ] **Step 1: 创建 setup-guide.md**

写入文件 `plugins/dev-tools/todo/references/setup-guide.md`，内容如下：

```markdown
# Setup 和 Hooks 配置指南

## 快速开始

### 1. 安装 Skill

```bash
# 链接到全局
cd /Users/jiashengwang/jacky-github/jacky-skills
j-skills link todo

# 安装到全局
j-skills install todo -g
```

> 如果 j-skills 命令不可用，参考 jacky-skills-package 项目安装 CLI

### 2. 在项目中启用

```bash
# 在项目根目录执行
/todo setup
```

这会：
- 将 hooks 配置注入 `~/.claude/settings.json`
- 创建 `.todo-enabled` 开关文件
- 创建 `.todo.md` 初始文件（如果不存在）

### 3. 手动控制

```bash
# 启用
echo "enabled" > .todo-enabled

# 禁用
rm .todo-enabled
```

## Hooks 配置详情

### 事件类型

| 事件 | 脚本 | 触发时机 | 用途 |
|------|------|----------|------|
| SessionStart | session-start.sh | 会话启动 | 注入 TODO 统计提醒 |
| Stop | stop-check.sh | AI 响应结束 | 检查未清理项 |
| PreCompact | pre-compact.sh | 上下文压缩前 | 提醒保存进展 |
| PreToolUse | pre-tool-use.sh | Write/Bash 调用前 | 检测临时文件 |

### 手动配置 hooks（不使用 setup）

如果需要手动配置，在 `~/.claude/settings.json` 的 `hooks` 中添加：

```json
{
  "SessionStart": [{
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "bash /path/to/todo/hooks/session-start.sh # skill: todo"
    }]
  }]
}
```

## 安全规则

### 路径安全校验

所有文件操作（delete/git-checkout）都经过以下安全检查：

| 检查项 | 规则 | 不通过时 |
|--------|------|---------|
| 项目内路径 | 绝对路径必须在项目目录下 | 跳过，标注 ⚠️ |
| 路径穿越 | 禁止 .. 和符号链接指向项目外 | 跳过，标注 ⚠️ |
| 文件存在性 | @file: 标记的文件必须存在 | 跳过 |
| 绝对路径 | 禁止以 / 开头 | 拒绝执行 |

### 操作确认

- delete 操作：列出 + 用户选择确认
- git-checkout 操作：列出 + 用户选择确认
- node_modules 中的 git-checkout：二次确认

## .gitignore 建议

根据团队偏好选择：

**加入 .gitignore（推荐）**：
```
.todo.md
.todo-enabled
```

适合：个人项目，不想把 TODO 追踪提交到仓库

**提交到仓库**：
不做任何 gitignore 配置。

适合：团队项目，希望所有成员看到待办事项
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add plugins/dev-tools/todo/references/setup-guide.md
git commit -m "docs(todo): 添加 setup 和 hooks 配置指南"
```

---

## Chunk 4: Integration & Verification

### Task 14: 链接和安装 Skill

**Files:**
- 无新文件，执行 j-skills 命令

**前置检查**：先确认 j-skills CLI 是否可用。

- [ ] **Step 1: 检查 j-skills 是否可用**

```bash
which j-skills || echo "j-skills not found"
```

如果输出 `j-skills not found`，尝试使用完整路径：
```bash
ls /Users/jiashengwang/jacky-github/jacky-skills-package/bin/ 2>/dev/null || echo "CLI not found, will install manually"
```

- [ ] **Step 2: 链接 skill 到全局**

如果 j-skills 可用：
```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
j-skills link todo
```

如果不可用，手动创建符号链接：
```bash
# 确认全局 skills 目录
ls ~/.claude/skills/
# 创建链接（根据实际目录结构调整）
```

- [ ] **Step 3: 验证 skill 文件完整性**

```bash
# 验证所有文件都存在
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/SKILL.md
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/hooks.json
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/session-start.sh
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/stop-check.sh
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/pre-compact.sh
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/hooks/pre-tool-use.sh
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/references/file-format.md
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/references/commands.md
ls /Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo/references/setup-guide.md
```

Expected: 所有 9 个文件都存在

---

### Task 15: 手动验证（基本命令）

**Files:**
- 无新文件，手动测试

- [ ] **Step 1: 在测试项目中 setup**

```bash
cd /Users/jiashengwang/jacky-github/opencli-study
```

在新 Claude Code 会话中执行 `/todo setup`

- [ ] **Step 2: 测试 add/list/done 命令**

在新会话中测试：
1. `/todo add 测试待办事项` — 验证添加到 .todo.md
2. `/todo list` — 验证列表展示
3. `/todo add --idea 测试想法` — 验证想法添加
4. `/todo done 1` — 验证完成标记
5. `/todo add-file test-debug.tsx` — 验证文件追踪

- [ ] **Step 3: 清理测试数据**

```bash
rm -f .todo.md .todo-enabled test-debug.tsx
```

---

### Task 16: 手动验证（高级功能）

**Files:**
- 无新文件，手动测试

- [ ] **Step 1: 测试 clean/save/restore 命令**

1. `/todo add --cleanup 添加了 console.log @file:src/app.tsx @action:git-checkout` — 添加清理项
2. `/todo clean` — 验证清理流程（列出 + 确认）
3. `/todo save 测试保存进展描述` — 验证保存功能
4. `/todo restore` — 验证上下文恢复

- [ ] **Step 2: 测试 hooks 注入**

1. 创建 `.todo-enabled` 文件
2. 创建包含内容的 `.todo.md`
3. 重启 Claude Code 会话
4. 验证 SessionStart hook 是否注入提醒

- [ ] **Step 3: 最终清理**

```bash
rm -f .todo.md .todo-enabled
```
