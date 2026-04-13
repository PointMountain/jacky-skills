# ob-project-log 设计文档

> 将 AI 对话自动归档到 Obsidian Wiki 的项目目录，持续提取有价值内容并分析

## 背景

obsidian-tools 插件已有 `ob-collect`（手动内容收集）和 `ob-chat`（知识问答），但缺少"自动持续记录 AI 对话"的能力。每次与 AI 的对话都包含有价值的决策、知识点和问题解决过程，这些内容目前随会话结束而丢失。

## 目标

- 每次与 AI 的对话归档到 `wiki/projects/{project}/` 目录
- 从对话中提取：决策记录、知识点、问题解决方案
- 维护项目状态汇总，形成项目知识沉淀
- 与现有 ob-collect 项目目录结构兼容

## 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 与 ob-collect 关系 | 独立 skill，共享项目目录 | ob-collect 处理手动收集，ob-project-log 处理对话记录，两者共存于 wiki/projects/ |
| 记录粒度 | 摘要 + 关键片段提取 | 宏观和微观兼顾 |
| 触发方式 | 手动为主 + Hook 标记辅助 | Hook 只做标记文件，实际 AI 分析由手动调用执行 |
| Project 识别 | 自动识别 + 降级询问 | 从 git/workdir 自动判断，识别不出时询问 |
| 文件命名 | 统一使用 YYYY-MM-DD-slug | 与 ob-collect 保持一致，无需维护计数器 |

## 目录结构

与 ob-collect 共享 `wiki/projects/` 命名空间。ob-project-log 新增 `conversations/` 和 `troubleshooting/` 子目录，复用 ob-collect 已有的 `decisions/` 和 `insights/`。

```
wiki/projects/{project}/
├── README.md                    # 项目概览（ob-collect 或 ob-project-log 创建）
├── conversations/               # [ob-project-log 新增] 对话记录
│   ├── 2026-04-12-143022.md    # 日期 + 时间戳，无需计数器
│   └── ...
├── insights/                    # [共享] 知识点（ob-collect + ob-project-log 都可写入）
│   ├── 2026-04-12-react-patterns.md
│   └── ...
├── decisions/                   # [共享] 技术决策（ob-collect + ob-project-log 都可写入）
│   ├── 2026-04-12-use-vitest.md
│   └── ...
├── troubleshooting/             # [ob-project-log 新增] 问题解决记录
│   ├── 2026-04-12-build-error-fix.md
│   └── ...
├── architecture/                # [ob-collect 已有] 架构分析
└── changelog.md                 # [ob-collect 已有] 变更日志
```

**兼容规则**：
- `decisions/` 和 `insights/` 由两个 skill 共享，都使用 `YYYY-MM-DD-slug.md` 命名
- ob-project-log 写入时检查已有文件，相同主题合并而非重复创建
- README.md 如果已由 ob-collect 创建，ob-project-log 追加 conversations 和 troubleshooting 的目录说明

## 文件格式

### 对话记录 (conversations/YYYY-MM-DD-HHMMSS.md)

使用时间戳后缀避免并发冲突，无需维护计数器。

```markdown
---
type: conversation
project: {project-name}
date: 2026-04-12
session_id: {claude-session-id 短后缀}
status: archived
tags: [tag1, tag2]
---

# {AI 自动生成的标题}

## 摘要
{2-3 句话概括}

## 关键决策
- **{决策}** — {原因}

## 知识点
- **{知识点}** — {说明}

## 问题解决
- **{问题}** → {解决方案}

## 未完成事项
- [ ] {待办}

## 原始对话亮点
> {代表性对话片段}
```

### 决策记录 (decisions/YYYY-MM-DD-slug.md)

与 ob-collect 共享目录，使用统一命名规范。通过 `type: adr` frontmatter 区分。

```markdown
---
type: adr
project: {project-name}
date: 2026-04-12
status: accepted
source: ob-project-log
---

# ADR: {决策标题}

## 上下文
{为什么需要做这个决策}

## 决策
{选择了什么方案}

## 理由
{为什么选择这个方案}

## 来源
> 对话: [[conversations/2026-04-12-143022]]
```

### 知识点 (insights/YYYY-MM-DD-slug.md)

```markdown
---
type: insight
project: {project-name}
date: 2026-04-12
tags: [tag1]
source: ob-project-log
---

# {知识点标题}

{知识点内容，包含示例和适用场景}

## 来源
> 对话: [[conversations/2026-04-12-143022]]
```

### 问题解决 (troubleshooting/YYYY-MM-DD-slug.md)

```markdown
---
type: troubleshooting
project: {project-name}
date: 2026-04-12
tags: [tag1]
symptoms: [症状关键词]
source: ob-project-log
---

# {问题描述}

## 症状
{表现}

## 根因
{原因分析}

## 解决方案
{步骤}

## 来源
> 对话: [[conversations/2026-04-12-143022]]
```

### 项目状态 (status.md) — 仅按需生成

`/ob-project-log --status` 时才生成/更新，不做每次归档后的自动更新。

```markdown
---
type: status
project: {project-name}
generated_at: 2026-04-12
---

# {project} 项目状态

## 最新进展
- {最近的关键活动}

## 活跃决策
- [[decisions/2026-04-12-use-vitest|ADR: Use Vitest]] — accepted

## 待办事项
- [ ] {未完成项}

## 知识沉淀统计
- 对话记录: {N} 篇
- 决策: {N} 个
- 知识点: {N} 条
- 问题解决: {N} 条

## 近期对话
- [[conversations/2026-04-12-143022|对话标题]]
```

## 触发机制

### v1 简化方案：手动为主 + Hook 标记

| 触发方式 | 行为 |
|----------|------|
| `/ob-project-log` | 立即归档当前对话（执行完整 AI 分析） |
| `/ob-project-log --status` | 生成项目状态汇总 |
| `/ob-project-log --setup` | 注册 session-end hook 到 settings.json |

### Hook 的实际能力

Hook 是 shell 脚本，**无法执行 AI 分析**。Hook 的作用仅限于：

- **session-end hook**：写入一个标记文件 `$OBSIDIAN_REPO/.ob-project-log-pending`，内容为 `{project}|{timestamp}`，表示有待归档的对话
- **下次 `/ob-project-log` 调用时**：检测标记文件，提示用户是否归档上次未记录的对话

这样 Hook 只做轻量标记，AI 分析始终由 skill 调用时执行。

### Hook 实现

```
ob-project-log/
├── SKILL.md
├── hooks/
│   ├── hooks.json           # Hook 注册配置
│   └── session-end.sh       # 写入 pending 标记文件
└── references/
    └── analysis-prompt.md   # AI 分析的提示词模板
```

### Project 识别逻辑

1. 从 `CLAUDE.md` 读取项目信息
2. 从 git remote URL 提取仓库名（`basename` 去掉 `.git`）
3. 从当前工作目录名推断
4. 以上均失败 → 询问用户

## 分析引擎

### 分析流程

整个分析是一个 **单次 AI 调用**，流程如下：

1. **收集上下文**：读取当前对话历史（Claude Code 内置上下文）
2. **执行提取**：使用 `references/analysis-prompt.md` 中的提示词，要求 AI 生成结构化 JSON
3. **写入文件**：解析 JSON，按模板写入各目录

### 提取提示词要求 AI 识别

| 类别 | 识别信号 | 输出 |
|------|----------|------|
| 决策 | "决定采用"、"选择"、"最终方案"、"不再使用" | → `decisions/YYYY-MM-DD-slug.md` |
| 知识点 | 新学到的技术知识、可复用模式、技巧 | → `insights/YYYY-MM-DD-slug.md` |
| 问题解决 | 错误修复、排查过程、调试结果 | → `troubleshooting/YYYY-MM-DD-slug.md` |

### 敏感信息过滤

提示词中明确指令：**归档内容必须排除 API key、密码、token、凭证等敏感信息**。遇到这类内容时用 `{REDACTED}` 替代。

### 去重机制

写入前检查已有内容：
- 相同主题的 insights → 合并补充到已有文件
- 相同决策 → 更新状态而非重复创建
- 相同问题 → 关联已有记录，追加新信息

### 跨对话关联

提取时检查 `conversations/` 目录下的历史记录，如果当前对话与历史主题相关，在文件中添加 `[[wikilink]]` 引用。

## Wiki 集成

与 ob-collect、ob-chat 共享的 wiki 基础设施：

### wiki/index.md 更新

每次归档后，在 `wiki/index.md` 的项目部分追加对话记录链接：

```markdown
## Projects

### {project}
- [[projects/{project}/conversations/2026-04-12-143022|对话: 标题]]
```

### wiki/log.md 更新

追加归档记录：

```markdown
- 2026-04-12: [对话归档] {project} - {标题} (decisions: {N}, insights: {N}, troubleshooting: {N})
```

### .kb/manifest.json 更新

在 manifest 中记录新的编译状态：

```json
{
  "projects/{project}/conversations/2026-04-12-143022.md": {
    "type": "conversation",
    "compiled": true,
    "date": "2026-04-12"
  }
}
```

## SKILL.md 结构

SKILL.md 遵循 obsidian-tools 插件的统一格式：

```yaml
---
name: ob-project-log
description: AI 对话归档到 Obsidian 项目目录，自动提取决策、知识点和问题解决记录
---
```

包含 XML 标签：`<role>`、`<purpose>`、`<trigger>`、`<gsd:workflow>`

GSD workflow 定义以下阶段：
1. **识别阶段**：确定当前 project，检查 pending 标记
2. **分析阶段**：使用提示词模板分析对话内容
3. **写入阶段**：生成对话记录 + 提取内容，去重检查
4. **集成阶段**：更新 wiki/index.md、wiki/log.md、manifest.json
5. **确认阶段**：输出归档摘要给用户

## Skill 交互设计

### 调用方式

```
/ob-project-log              # 归档当前对话
/ob-project-log --status     # 生成项目状态汇总
/ob-project-log --setup      # 注册 session-end hook
```

## 约束

1. 仅在 Obsidian 仓库路径下操作（`OBSIDIAN_REPO`）
2. 不修改已有的 wiki 内容，仅追加
3. 归档内容排除 API key、密码、token、凭证等敏感信息
4. 与 ob-collect 共享 `wiki/projects/` 目录，使用统一命名规范 `YYYY-MM-DD-slug.md`
5. 不在 `wiki/` 根目录创建文件，所有输出在 `wiki/projects/{project}/` 下
