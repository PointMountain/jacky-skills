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
2. 如有必要创建 `.todo.md` 初始文件
3. 询问是否加入 `.gitignore`

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
