---
name: ob-collect
description: "Obsidian 知识库采集与项目沉淀。采集网页/PDF/视频/文本到知识库，编译为结构化 wiki 笔记；或将项目知识沉淀到项目工作区。触发词：采集、导入知识库、ob-collect、ob-learn、项目沉淀。"
---

<role>Obsidian 知识库采集与项目沉淀助手。从多种来源提取内容，或从对话/项目中沉淀有价值知识，编译为结构化 wiki 笔记。</role>
<purpose>两种模式：(1) 采集模式 — 将 URL/PDF/视频/文本采集到 raw/ 并编译到 wiki/；(2) 项目沉淀模式 — 将对话或项目中的有价值内容沉淀到 wiki/projects/{project}/。建议 ≤ 500 字，超出部分用 [[reference]] 链接补充。</purpose>
<trigger>

```text
触发词：
- 采集文章 / 导入到知识库 / 学习记录 / 摄入资料
- ob-collect / ob-learn / 把这个加到知识库 / 记录一下这篇文章
- 项目沉淀 / 沉淀到项目 / 记录到项目 / 保存到项目知识库
- 项目工作区 / project workspace

示例：
- "ob-collect https://example.com/article"
- "帮我采集这篇文章到知识库"
- "把这个 PDF 导入知识库"
- "记录一下：RLHF 和 CoT 的关系"
- "把这个架构分析沉淀到 jacky-skills-package 项目"
- "保存这个设计决策到项目工作区"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=ingest,compile,project</gsd:meta>
  <gsd:goal>将来源采集到 raw/ 编译到 wiki/，或将项目知识沉淀到 wiki/projects/{project}/。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO 路径，判断模式：采集模式（URL/PDF/视频/文本）或项目沉淀模式（对话内容/项目知识）。</gsd:phase>
  <gsd:phase>采集模式：提取内容，预览确认，写入 raw/ 编译到 wiki/。项目沉淀模式：识别项目名，提取有价值内容，预览确认，写入 wiki/projects/{project}/。</gsd:phase>
  <gsd:phase>更新索引：wiki/index.md、wiki/log.md、.kb/manifest.json。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库采集与项目沉淀 (ob-collect)

## 配置检查

**执行前必读**：本 skill 需要使用 Obsidian 仓库路径。

1. 首先检查全局 CLAUDE.md 中是否定义了 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 将用户提供的路径保存为 `$OBSIDIAN_REPO` 变量供后续使用

**目录初始化检查**：

首次使用时，确认以下目录存在（不存在则创建）：

```
$OBSIDIAN_REPO/raw/{web,pdf,images,notes}/
$OBSIDIAN_REPO/wiki/{concepts,entities,sources,synthesis,archive,projects}/
$OBSIDIAN_REPO/outputs/
$OBSIDIAN_REPO/.kb/
```

如果 `wiki/index.md` 不存在，创建初始索引（含 `## 项目` 分区）。

## 模式判断

| 用户意图 | 模式 | 输入类型 |
|----------|------|----------|
| 提供 URL/PDF/视频/文本 | 采集 | web/pdf/video/note |
| "沉淀到项目"/"保存到项目" | 项目沉淀 | project |
| 当前对话中有分析内容，用户说"记录一下" | 自动判断 | note/project |

## 采集模式

详见 [references/collect-mode.md](references/collect-mode.md)

### 流程概要

1. **识别输入类型**：URL → WebFetch，PDF → Read，视频 → audio-to-obsidian，文本 → 直接使用
2. **提取内容**：抓取/读取正文，提取关键要点（3-5 条）
3. **预览确认**：展示标题、来源、要点、标签、相关 wiki，等待用户确认
4. **写入 raw/**：带 frontmatter 的原始笔记
5. **编译到 wiki/**：生成 source 摘要 → 创建/更新 concept → 更新 index/log/manifest

### 关键规则

- 文件名规范：`{YYYY-MM-DD}-{slug}.md`
- 概念文章已存在时：读取并合并，不覆盖
- 概念冲突时：标注矛盾，追加说明
- 详细模板见 [references/compile-templates.md](references/compile-templates.md)

## 项目沉淀模式

详见 [references/project-mode.md](references/project-mode.md)

### 目录结构

```
wiki/projects/{project-slug}/
├── README.md              — 项目概述（名称、仓库、技术栈、描述）
├── decisions/             — 架构/设计决策记录（ADR）
│   └── {YYYY-MM-DD}-{slug}.md
├── insights/              — 从对话中沉淀的知识洞察
│   └── {YYYY-MM-DD}-{slug}.md
├── architecture/          — 架构分析文档
│   └── {slug}.md
└── changelog.md           — 项目知识变更日志
```

### 流程概要

1. **识别项目**：从当前工作目录 git 信息或用户指定获取项目名
2. **提取内容**：从对话中提取有价值的知识（架构决策、设计模式、踩坑经验等）
3. **预览确认**：展示项目名、内容分类、摘要，等待确认
4. **写入项目目录**：按分类写入对应子目录
5. **更新项目 README.md 和 changelog.md**
6. **更新 wiki/index.md 的 `## 项目` 分区**

### 项目 README.md 模板

```markdown
---
type: project
repo: {仓库路径或 URL}
tech_stack: [{技术栈}]
created_at: {日期}
updated_at: {日期}
---
# {项目名称}

> {一句话描述}

## 架构概览

{简要架构说明}

## 知识索引

### 设计决策
### 知识洞察
### 架构分析
```

## 异常处理

| 场景 | 处理 |
|------|------|
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念/项目文章已存在 | 读取并更新，不创建重复 |
| 项目目录不存在 | 自动创建完整目录结构 |
| 概念冲突 | 在文章中标注矛盾，追加说明 |
