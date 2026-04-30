# CLAUDE.md Obsidian 索引段格式规范

## 概述

项目 CLAUDE.md 中的 Obsidian 索引段是一个**自动生成和维护**的区域，用于实现渐进式知识加载。LLM 通过 CLAUDE.md 获得紧凑概览，需要详情时再读取 Obsidian 索引和文章。

## 渐进式加载层级

| 层级 | 位置 | 加载时机 | 内容 |
|------|------|----------|------|
| Level 1 | 项目 CLAUDE.md `<!-- ob-index -->` 区域 | 会话开始自动加载 | 紧凑表格：文件名 + 主题 + 何时读取 |
| Level 2 | `{OBSIDIAN_REPO}/wiki/{path}/index.md` | LLM 需要定位具体文章时 | 完整表格：ID + 文件 + 主题 + 维度 + 日期 |
| Level 3 | `{OBSIDIAN_REPO}/wiki/{path}/{article}.md` | LLM 需要具体内容时 | 完整文章内容 |

## 标记区域格式

CLAUDE.md 中使用 HTML 注释标记自动生成区域：

```markdown
<!-- ob-index:start -->
## Obsidian 知识库

> 索引路径：`{OBSIDIAN_REPO}/wiki/{section}/{project}/index.md`
> 渐进式加载：先读本概览，需要详情时读取索引文件（含完整 ID 和维度），再读取具体文章。

| 文件 | 主题 | 何时读取 |
|------|------|----------|
| chrome-cdp-debugging.md | Chrome CDP 远程调试踩坑 | 遇到 CDP 连接问题时 |
| mvp-flow-design.md | MVP 调研流程架构设计 | 理解探索流程设计时 |
| business-context-and-planning.md | 业务背景与项目规划 | 需要理解项目目标时 |
<!-- ob-index:end -->
```

### 标记说明

- `<!-- ob-index:start -->` — 自动生成区域起始标记
- `<!-- ob-index:end -->` — 自动生成区域结束标记
- 两个标记之间的所有内容由 ob-project-log / ob-index 自动维护
- **不要手动编辑标记区域内的内容**，下次自动更新会被覆盖

### 区域位置

- 位于 CLAUDE.md 文件**末尾**
- 如果 CLAUDE.md 已有手动维护的 "Obsidian 知识库" 部分，替换为标记区域
- 如果 CLAUDE.md 没有该部分，在末尾追加

## 表格列说明

| 列 | 来源 | 说明 |
|----|------|------|
| **文件** | Obsidian index.md 的文件名列 | 文件名（不含路径） |
| **主题** | Obsidian index.md 的主题列 | 一句话主题描述（≤ 30 字） |
| **何时读取** | 基于主题和类型自动推导 | 什么场景下应该读取该文章 |

### "何时读取" 推导规则

根据文章主题和类型自动生成：

| 文章类型 | 推导模板 |
|----------|----------|
| 架构设计 | 理解 {主题关键词} 架构时 |
| 踩坑记录 | 遇到 {主题关键词} 问题时 |
| 决策记录 | 回顾 {主题关键词} 选型理由时 |
| 性能优化 | 分析 {主题关键词} 性能时 |
| 技术选型 | 回顾 {主题关键词} 选型理由时 |
| 使用指南 | 使用 {主题关键词} 时 |
| 默认 | 需要了解 {主题关键词} 时 |

## 多位置合并

如果一个项目在 Obsidian 中有多个位置的索引（如 `projects/` + 主题目录），合并到同一个标记区域内，用三级标题分组：

```markdown
<!-- ob-index:start -->
## Obsidian 知识库

> 渐进式加载：先读本概览，需要详情时读取索引文件，再读取具体文章。

### 项目文档

> 索引路径：`{OBSIDIAN_REPO}/wiki/projects/{project}/index.md`

| 文件 | 主题 | 何时读取 |
|------|------|----------|
| ... | ... | ... |

### 主题研究

> 索引路径：`{OBSIDIAN_REPO}/wiki/{theme}/{project}/index.md`

| 文件 | 主题 | 何时读取 |
|------|------|----------|
| ... | ... | ... |
<!-- ob-index:end -->
```

## 生成流程

1. 读取 Obsidian 索引文件（`index.md`）
2. 解析表格中的文件名和主题列
3. 根据主题和涵盖维度推导 "何时读取" 列
4. 生成标记区域内容
5. 在 CLAUDE.md 中查找 `<!-- ob-index:start -->` 标记
   - 存在：替换标记区域内容
   - 不存在：在 CLAUDE.md 末尾追加
6. 如果 CLAUDE.md 中有旧的手动维护 "Obsidian 知识库" 部分（无标记），替换为标记区域

## 更新触发时机

| 触发来源 | 时机 |
|----------|------|
| ob-project-log | 写入新文章后 |
| ob-index | 重建索引后 |
| ob-collect | 编译新内容到 wiki 后 |
| ob-topic | 写入知识点后 |

## 共享更新流程

> 以下流程供所有 ob skills 在写入 Obsidian 内容后统一调用，确保项目 CLAUDE.md 始终与 Obsidian 知识库保持同步。

### 前置条件检查

写入完成后，执行以下检查：

1. **是否在 git 项目中**：`git rev-parse --show-toplevel`（失败则跳过）
2. **CLAUDE.md 是否存在**：`{git_root}/CLAUDE.md`（不存在则跳过）
3. **OBSIDIAN_REPO 是否配置**：检查环境变量或全局 CLAUDE.md

任一条件不满足则跳过，不影响主流程。

### Obsidian 索引路径发现

查找当前项目在 Obsidian 中的索引文件（按优先级）：

1. **已有标记路径**：读取 CLAUDE.md 中 `<!-- ob-index:start -->` 区域内的 `> 索引路径：` 行
2. **项目精确匹配**：`$OBSIDIAN_REPO/wiki/projects/{project_name}/index.md`
3. **frontmatter 搜索**：`grep -rl "project: {project_name}" "$OBSIDIAN_REPO/wiki/" --include="index.md"`
4. **目录名匹配**：`find "$OBSIDIAN_REPO/wiki/" -type d -name "*{project_name}*"`

project_name 获取：`basename "$(git remote get-url origin)" .git`

### 生成索引段内容

从 Obsidian 索引文件读取表格，生成紧凑的 CLAUDE.md 索引段：

1. 读取 `$OBSIDIAN_REPO/wiki/{path}/index.md`
2. 解析表格中的文件名、主题、涵盖维度列
3. 根据 "何时读取" 推导规则生成第三列
4. 组装标记区域内容

### 写入 CLAUDE.md

| 场景 | 操作 |
|------|------|
| CLAUDE.md 已有 `<!-- ob-index:start -->` 标记 | 替换两个标记之间的全部内容 |
| CLAUDE.md 有旧的手动 "Obsidian 知识库" 部分（`## Obsidian 知识库` 或 `## Obsidian 知识库（按需加载）`） | 替换该部分为标记区域 |
| CLAUDE.md 没有任何 Obsidian 相关内容 | 在文件末尾追加标记区域 |

### 跳过场景（静默跳过，不报错）

- 项目不在 git 仓库中
- CLAUDE.md 不可写
- 未找到对应的 Obsidian 索引文件
- ob-collect/ob-topic 写入的内容在主题目录（非项目目录），且没有已建立的项目索引
