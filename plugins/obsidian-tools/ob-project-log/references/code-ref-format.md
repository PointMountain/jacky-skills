# Code Reference 格式规范

> 项目沉淀笔记中的代码不内嵌，而是通过 code-ref callout 引用实际代码位置。

## 为什么用 reference 而非嵌入

| 嵌入代码 | Code Reference |
|----------|----------------|
| 仓库改了代码，笔记里还是旧的 | 链接永远指向最新代码 |
| 同一份代码存两份 | 只存一份，笔记存链接 |
| 想复用还得自己找文件 | 点击直达具体行号 |
| 笔记越来越长，难以维护 | 笔记只承载知识，保持精简 |

## 格式定义

使用 Obsidian Callout 语法：

```markdown
> [!code-ref] {简要描述代码的作用}
> **仓库**: {repo-name} | **路径**: `{relative-path}:{start_line}-{end_line}`
> 🔗 [GitHub]({github-url}#L{start_line}-L{end_line})
>
> {1-3 句话说明这段代码的设计意图、在架构中的角色、或值得复用的要点}
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| 描述 | 是 | 简要说明这段代码做什么，作为 callout 标题 |
| 仓库 | 是 | GitHub 仓库名（非完整 URL） |
| 路径 | 是 | 相对于仓库根目录的路径 + 行号范围 |
| GitHub 链接 | 是 | 可点击的完整 GitHub URL，带行号锚点 |
| 设计意图 | 是 | 1-3 句话，说明为什么这样写、在架构中的角色 |

## 生成规则

### 1. 提取 GitHub 信息

```bash
# 从 git remote 获取仓库信息
git remote get-url origin
# → git@github.com:wangjs-jacky/CodeIsland.git
# 或 → https://github.com/wangjs-jacky/CodeIsland.git

# 提取仓库路径部分
# → wangjs-jacky/CodeIsland
```

如果 remote URL 不是 GitHub 格式，使用本地路径作为 fallback：

```markdown
> **仓库**: {project-name} | **路径**: `{relative-path}:{start_line}-{end_line}`
```

### 2. 确定行号

- 对话中讨论了具体文件时，从上下文中提取行号
- 如果对话中使用了 `file_path:line_number` 格式，直接提取
- 如果无法确定精确行号，使用函数/类名定位：

```markdown
> **路径**: `{relative-path}#L{function_or_class_name}`
```

### 3. 编写设计意图

设计意图应该回答：
- **为什么**这样实现（设计决策）
- 这段代码在**架构中的角色**（属于哪一层、解决什么问题）
- 有什么**值得复用**的设计模式

避免简单重复代码本身做了什么 — 读者可以点链接看代码。

## 完整示例

### 示例 1：终端激活策略

```markdown
> [!code-ref] VS Code 集成终端环境变量读取
> **仓库**: CodeIsland | **路径**: `CodeIslandBridge/main.swift:252-257`
> 🔗 [GitHub](https://github.com/wangjs-jacky/CodeIsland/blob/main/CodeIslandBridge/main.swift#L252-L257)
>
> VS Code 并没有专门提供"让外部应用跳转到特定窗口"的 API。
> CodeIsland 利用 macOS 自动给 GUI 进程设置的 `__CFBundleIdentifier` 和
> VS Code 给集成终端设置的 `TERM_PROGRAM` 环境变量，实现了无需 IDE 配合的窗口识别。
> 这是一个"利用系统副作用而非正式 API"的设计模式。
```

### 示例 2：Hooks 生命周期管理

```markdown
> [!code-ref] Monitor Hooks 注册与卸载
> **仓库**: j-skills-package | **路径**: `src-tauri/src/commands/monitor.rs:45-82`
> 🔗 [GitHub](https://github.com/wangjs-jacky/j-skills-package/blob/main/src-tauri/src/commands/monitor.rs#L45-L82)
>
> 通过操控 `~/.claude/settings.json` 实现 hooks 的注入和卸载，
> 而非通过 Claude Code 的正式 API。这种方式的风险是 settings.json 格式变化可能导致兼容性问题，
> 但好处是无需 Claude Code 配合即可工作。
```

### 示例 3：非 GitHub 项目（本地项目 fallback）

```markdown
> [!code-ref] WebSocket 消息路由分发
> **仓库**: my-local-project | **路径**: `src/websocket/handler.ts:30-58`
>
> 使用 Map<type, Handler> 模式实现消息类型到处理函数的路由分发，
> 新增消息类型只需注册 handler，无需修改分发逻辑。
```

## 与普通内容的搭配

笔记中不是所有内容都需要 code-ref。正确的搭配是：

```markdown
# 终端激活机制

## 设计思路（纯文字描述）

CodeIsland 使用 5 级分发策略来激活不同类型的终端窗口。
核心思路是按优先级匹配，从最精准（Native App）到最通用（窗口标题匹配）。

> [!code-ref] 激活策略优先级分发
> **仓库**: CodeIsland | **路径**: `CodeIslandBridge/Activator.swift:15-45`
> 🔗 [GitHub](https://github.com/wangjs-jacky/CodeIsland/blob/main/CodeIslandBridge/Activator.swift#L15-L45)
>
> 分发逻辑使用 switch-case 瀑布模式，每个 case 独立处理一种终端类型。
> 关键设计：匹配失败时 fallthrough 到下一级，而非报错。

## 注意事项（纯文字，无 code-ref）

- 窗口激活依赖 macOS Accessibility API，需要用户授权
- tmux 场景下需要 session name 唯一，否则会匹配到错误的 pane
```

原则：**知识用文字描述，代码用 reference 链接**。
