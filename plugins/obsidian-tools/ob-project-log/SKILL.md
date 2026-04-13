---
name: ob-project-log
description: "AI 对话沉淀到 Obsidian 项目知识库。根据对话内容动态创建和更新项目知识文件。触发词：ob-project-log、记录到项目、沉淀对话。"
---

<role>Obsidian 项目知识沉淀助手。从 AI 对话中提取有价值内容，按主题动态写入项目目录。</role>
<purpose>将对话中的项目知识写入 wiki/projects/{project}/，按主题组织为活文档。</purpose>
<trigger>

```text
触发词：
- ob-project-log / 记录到项目 / 沉淀对话

示例：
- "ob-project-log"
- "把这次对话沉淀到项目"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO</gsd:meta>
  <gsd:goal>从对话中提取项目知识，按主题写入对应文件。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO，识别 project（git remote → 目录名 → 询问）。</gsd:phase>
  <gsd:phase>分析当前对话，提取有价值内容，确定主题和文件。</gsd:phase>
  <gsd:phase>读取已有文件，合并新内容（不覆盖），去重。无匹配文件则新建。</gsd:phase>
  <gsd:phase>写入更新，输出摘要。</gsd:phase>
</gsd:workflow>

# Obsidian 项目知识沉淀 (ob-project-log)

## 做什么

从 AI 对话中提取项目知识，按**主题**写入项目目录。文件根据内容动态创建，不预设固定结构。

## 执行步骤

### 1. 识别项目

```
git remote origin → basename → 当前目录名 → 询问用户
```

目录：`$OBSIDIAN_REPO/wiki/projects/{project}/`

### 2. 提取内容

分析当前对话，按 [references/study-dimensions.md](references/study-dimensions.md) 中的维度提取有价值内容。

每个内容块包含：
- **维度**：属于哪个知识维度（架构设计、核心机制、设计规范等）
- **主题**：具体讲什么（如"插件架构"、"错误处理规范"）
- **内容**：核心知识，简洁精准

**提取标准**：只取有长期参考价值的内容。闲聊、临时调试、重复内容不取。

### 3. 匹配或创建文件

列出 `$OBSIDIAN_REPO/wiki/projects/{project}/` 下已有文件，对每个内容块：

- 已有文件主题匹配 → 追加到该文件对应位置
- 无匹配文件 → 新建 `{slug}.md`，slug 从主题生成（短英文+连字符）

**不预设固定文件名**，完全根据对话内容动态决定。

### 4. 写入规则

- **不覆盖**：已有内容保留，新内容追加或合并
- **去重**：相同主题合并，不重复
- **敏感信息**：API key、密码、token → `{REDACTED}`
- **简洁**：每条点到为止

### 5. 输出摘要

```
📝 已沉淀到 wiki/projects/{project}/

更新：
  - {filename}.md  → {做了什么}
  - {filename}.md  → {做了什么}（新建）
```

## 异常处理

| 场景 | 处理 |
|------|------|
| OBSIDIAN_REPO 未配置 | 询问用户 |
| 项目识别失败 | 询问用户 |
| 目录不存在 | 自动创建 |
| 对话无有价值内容 | 告知用户，不写空内容 |
