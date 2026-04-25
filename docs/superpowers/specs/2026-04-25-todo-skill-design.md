# TODO Skill 设计文档

> 项目级持久化任务追踪 Skill，管理临时代码清理、待办事项、想法和临时文件，支持跨会话恢复

## 一、问题背景

在执行长任务时，经常遇到以下痛点：

1. **临时代码遗忘**：添加了 console.log、修改了 node_modules 等临时代码，事后忘记清理
2. **上下文丢失**：会话关闭或上下文压缩后，未完成的工作丢失
3. **临时文件残留**：创建的测试文件、调试文件没有被删除
4. **想法流失**：来不及实现的好想法没有记录下来

需要一个轻量级的、文件持久化的任务追踪机制，确保这些信息不会丢失。

## 二、设计目标

- **持久化**：所有任务信息存储在项目根目录的 `.todo.md` 文件中，Git 友好
- **跨会话**：会话关闭后可通过文件恢复上下文
- **自动化**：通过 hooks 自动提醒和检测，减少遗忘
- **安全**：清理操作需要确认，不会自动删除文件
- **轻量**：纯 Markdown 格式，可手动编辑，不依赖额外工具

## 三、文件格式

### `.todo.md` 结构

```markdown
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

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

### 格式约定

| 约定 | 说明 | 示例 |
|------|------|------|
| `- [ ]` | 未完成项 | `- [ ] 完成单元测试` |
| `- [x]` | 已完成项 | `- [x] 修复样式问题` |
| `@file:<path>` | 关联文件路径 | `@file:src/app.tsx` |
| `@action:<action>` | 清理动作 | `@action:delete` 或 `@action:git-checkout` |
| 无标记 | 纯文本任务 | `- [ ] 完成文档` |

### 动作类型

| 动作 | 说明 | 执行命令 |
|------|------|----------|
| `@action:delete` | 删除文件 | `rm <file>` |
| `@action:git-checkout` | 恢复 Git 修改 | `git checkout -- <file>` |
| 无 @action | 手动清理 | 仅提醒，不自动执行 |

## 四、命令体系

### SKILL.md Frontmatter

```yaml
---
name: todo
description: "项目级 TODO 追踪：管理临时代码清理、待办事项、想法和临时文件，支持跨会话恢复"
argument-hint: '[add|done|clean|list|setup|save|restore|add-file] [内容]'
---
```

### 命令列表

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

### `/todo clean` 详细流程

1. 读取 `.todo.md` 中 🧹 Cleanup 和 📁 Temp Files 的未完成项
2. 展示待清理项列表，按编号排列
3. 用户确认选择要清理的项（全部/选择编号/取消）
4. 执行对应操作：
   - `@action:delete` → `rm <file>`
   - `@action:git-checkout` → `git checkout -- <file>`
   - 无 @action → 仅提醒手动处理
5. 标记对应项为 `[x]` 已完成

## 五、Hooks 机制

### Hook 注册结构

```
hooks/
├── hooks.json              # Hook 注册声明
├── session-start.sh        # SessionStart：注入 TODO 提醒
├── stop-check.sh           # Stop：检查未清理项
├── pre-compact.sh          # PreCompact：保存进展提醒
└── pre-tool-use.sh         # PreToolUse：临时文件检测
```

### Hook 1：SessionStart

**目的**：会话启动时提醒用户有待处理项

**行为**：
1. 检查 `.todo-enabled` 开关文件是否存在
2. 检查当前目录是否有 `.todo.md`
3. 读取各分区未完成项数量
4. 注入 system-reminder 到上下文

**输出示例**：
```
<system-reminder>
📋 TODO 提醒：当前项目有 5 个待处理项
  - 🧹 2 个清理项
  - 📋 2 个待办项
  - 💡 1 个想法
使用 /todo list 查看详情，/todo restore 恢复上下文
</system-reminder>
```

### Hook 2：Stop

**目的**：AI 响应结束时检查是否有未清理项

**行为**：
1. 检查 `.todo-enabled` 开关
2. 检查 `.todo.md` 中是否有 cleanup/temp-file 类型的未完成项
3. 如果有，注入提醒
4. 使用标记文件（`/tmp/todo-checked-$PPID`）防止死循环

### Hook 3：PreCompact

**目的**：上下文压缩前提醒保存进展

**行为**：
1. 检查 `.todo-enabled` 开关
2. 输出提醒文本，建议 Claude 将当前进展写入 `.todo.md`
3. 不阻止压缩，仅提醒

### Hook 4：PreToolUse

**目的**：检测临时文件创建

**行为**：
1. matcher: `"Write|Bash"`
2. 检测文件名是否匹配临时文件模式
3. 匹配模式：`test-*`、`tmp-*`、`debug-*`、`*.tmp`、`*.bak`、`*.temp`
4. 如果匹配，注入提醒询问是否加入 `.todo.md`

### hooks.json 配置

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

### Setup 命令

`/todo setup` 执行流程：

1. 将 hooks 配置注入到 `~/.claude/settings.json`
2. 在当前项目创建 `.todo-enabled` 开关文件
3. 如有必要创建 `.todo.md` 初始文件
4. 提示用户将 `.todo.md` 加入 `.gitignore`（可选）

### 开关控制

```bash
# 在当前项目启用
echo "enabled" > .todo-enabled

# 禁用
rm .todo-enabled
```

Hook 脚本在开头检查 `.todo-enabled` 文件，不存在则 `exit 0` 静默退出。

## 六、Skill 目录结构

```
todo/
├── SKILL.md                          # 主文档（GSD workflow 格式）
├── hooks/                            # Hook 自动化
│   ├── hooks.json                    # Hook 注册声明
│   ├── session-start.sh              # SessionStart hook
│   ├── stop-check.sh                 # Stop hook
│   ├── pre-compact.sh                # PreCompact hook
│   └── pre-tool-use.sh              # PreToolUse hook
└── references/                       # 参考文档
    ├── file-format.md               # .todo.md 文件格式详细说明
    ├── commands.md                  # 命令使用详细说明
    └── setup-guide.md               # Setup 和 hooks 配置指南
```

## 七、GSD Workflow 设计

### Phase 1：命令解析

1. 读取用户输入的命令和参数
2. 解析子命令（add/done/clean/list/setup/save/restore/add-file）
3. 解析选项（`--cleanup`、`--idea`、`@file:`、`@action:`）

### Phase 2：文件操作

1. 检查 `.todo.md` 是否存在，不存在则创建初始模板
2. 根据命令执行对应操作（读取/写入/更新）
3. 更新 `最后更新` 时间戳

### Phase 3：结果反馈

1. 展示操作结果
2. 对于 clean 命令，执行确认流程
3. 更新 `.todo.md` 中的 checkbox 状态

## 八、安全考虑

1. **清理操作需确认**：所有 delete 和 git-checkout 操作都需要用户确认
2. **静默失败**：所有 hook 脚本以 `exit 0` 结束，不影响正常流程
3. **开关控制**：`.todo-enabled` 文件控制 hooks 是否激活
4. **防死循环**：Stop hook 使用标记文件机制
5. **Git 友好**：`.todo.md` 可选择加入 `.gitignore` 或提交到仓库

## 九、使用场景示例

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

### 场景 3：临时文件追踪

```
# Claude 创建了一个临时测试文件
# PreToolUse hook 检测到 test-debug.tsx 匹配临时文件模式
# 注入提醒：检测到临时文件 test-debug.tsx，是否加入追踪？

用户: /todo add-file test-debug.tsx
Claude: ✅ 已添加到 Temp Files 追踪列表
```

### 场景 4：想法记录

```
用户: /todo add --idea 可以用 WebSocket 实现实时通知
Claude: ✅ 已记录想法
```

### 场景 5：上下文压缩前保存

```
# PreCompact hook 触发，提醒 Claude 保存进展
# Claude 将当前进展写入 .todo.md
用户: /todo save 完成了用户认证模块的 API 集成，还有错误处理未完成
Claude: ✅ 进展已保存到 .todo.md
```
