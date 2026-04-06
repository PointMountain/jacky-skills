---
name: ob-learn
description: "Obsidian 知识库采集与编译。当用户想要采集网页/PDF/视频/文本到知识库、学习记录、摄入新资料、导入文章时触发此 skill。"
---

<role>Obsidian 知识库采集助手，负责从多种来源提取内容，预览确认后编译为结构化 wiki 笔记。</role>
<purpose>将任何来源（URL/PDF/视频/文本）采集到知识库 raw/ 层，编译为 ≤ 500 字的 wiki 文章，建立概念索引和双链。</purpose>
<trigger>

```text
触发词：
- 采集文章
- 导入到知识库
- 学习记录
- 摄入资料
- ob-learn
- 把这个加到知识库
- 记录一下这篇文章

示例：
- "ob-learn https://example.com/article"
- "帮我采集这篇文章到知识库"
- "把这个 PDF 导入知识库"
- "记录一下：RLHF 和 CoT 的关系"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=ingest,compile</gsd:meta>
  <gsd:goal>将用户提供的来源采集到 raw/ 并编译到 wiki/，生成结构化笔记、概念文章和索引条目。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO 路径，识别输入类型（URL/PDF/视频/文本）。</gsd:phase>
  <gsd:phase>提取内容：URL 用 WebFetch 抓取正文，PDF 用 Read 读取，视频调用视频转文本能力，文本直接使用。</gsd:phase>
  <gsd:phase>展示提取的关键点和摘要给用户预览，等待确认。</gsd:phase>
  <gsd:phase>确认后写入 raw/（带 frontmatter），编译到 wiki/：生成 source 摘要、创建/更新 concept 文章、更新 index.md 和 log.md。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库采集 (ob-learn)

将任何来源采集到知识库，编译为结构化 wiki 笔记。

## 配置检查

**执行前必读**：本 skill 需要使用 Obsidian 仓库路径。

1. 首先检查全局 CLAUDE.md 中是否定义了 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户：
   ```
   请提供您的 Obsidian 仓库路径：
   ```
3. 将用户提供的路径保存为 `$OBSIDIAN_REPO` 变量供后续使用

**目录初始化检查**：

首次使用时，确认以下目录存在（不存在则创建）：

```
$OBSIDIAN_REPO/raw/web/
$OBSIDIAN_REPO/raw/pdf/
$OBSIDIAN_REPO/raw/images/
$OBSIDIAN_REPO/raw/notes/
$OBSIDIAN_REPO/wiki/concepts/
$OBSIDIAN_REPO/wiki/entities/
$OBSIDIAN_REPO/wiki/sources/
$OBSIDIAN_REPO/wiki/synthesis/
$OBSIDIAN_REPO/wiki/archive/
$OBSIDIAN_REPO/outputs/
$OBSIDIAN_REPO/.kb/
```

如果 `$OBSIDIAN_REPO/wiki/index.md` 不存在，创建初始索引：

```markdown
# 知识库索引

> 最后更新：{当前日期}

## 概念

## 实体

## 来源

## 综合
```

如果 `$OBSIDIAN_REPO/.kb/manifest.json` 不存在，创建：

```json
{
  "version": 1,
  "items": []
}
```

## 执行流程

### 第一步：识别输入类型

根据用户输入判断类型：

| 输入特征 | 类型 | 处理方式 |
|----------|------|----------|
| 以 `http://` 或 `https://` 开头 | URL | WebFetch 抓取正文 |
| 以 `.pdf` 结尾的本地路径 | PDF | Read 工具读取 |
| 以视频平台域名开头（youtube/bilibili 等） | 视频 | 调用视频转文本能力 |
| 纯文本内容 | 笔记 | 直接使用 |

### 第二步：提取内容

**URL**：
```
使用 WebFetch 或 mcp__web_reader__webReader 抓取 URL
提取正文内容，去除导航/广告/页脚
```

**PDF**：
```
使用 Read 工具读取 PDF 文件
提取文本内容
```

**视频**：
```
如果已有视频转文本 skill（如 video-to-text），调用它提取文字稿
否则提示用户先提供视频的文字稿或摘要
```

**笔记**：
```
直接使用用户提供的文本
```

### 第三步：预览确认

**展示给用户**：

1. **标题**：自动生成或用户指定
2. **来源信息**：URL/文件路径/「个人笔记」
3. **关键要点**（3-5 条）：从内容中提取
4. **建议标签**：自动生成 2-4 个标签
5. **相关概念**：检测是否与 wiki 中已有概念相关

使用 AskUserQuestion 展示预览并等待确认：

```
标题：{标题}
来源：{来源}
关键要点：
  1. {要点 1}
  2. {要点 2}
  3. {要点 3}
标签：{标签}
相关 wiki 文章：{如有}

确认采集？可修改标题、标签等。
```

### 第四步：写入 raw/

根据输入类型写入对应子目录：

**文件名规范**：`{YYYY-MM-DD}-{slug}.md`

| 类型 | 目录 |
|------|------|
| URL | `$OBSIDIAN_REPO/raw/web/{slug}.md` |
| PDF | `$OBSIDIAN_REPO/raw/pdf/{slug}.md` |
| 视频 | `$OBSIDIAN_REPO/raw/notes/{slug}.md` |
| 笔记 | `$OBSIDIAN_REPO/raw/notes/{slug}.md` |

**Frontmatter 格式**：

```yaml
---
source: {原始 URL 或文件路径}
ingested_at: {ISO 时间戳}
type: {web|pdf|video|note}
status: uncompiled
---
```

### 第五步：编译到 wiki/

**5.1 生成来源摘要**

写入 `$OBSIDIAN_REPO/wiki/sources/{slug}.md`：

```markdown
---
tags: [{标签列表}]
type: source
updated_at: {日期}
---

# {标题}

> 来源：{原始来源}

## 核心要点
- {要点 1}
- {要点 2}
- {要点 3}

## 详细内容

{≤ 500 字的结构化摘要}

## 关联概念
- [[concepts/{概念 1}]] — 关联原因
- [[concepts/{概念 2}]] — 关联原因

## 原始资料
- [[raw/{类型}/{slug}]]
```

**5.2 创建/更新概念文章**

对提取的每个关键概念：

- 如果 `$OBSIDIAN_REPO/wiki/concepts/{concept-slug}.md` **已存在**：读取现有内容，用新信息更新（不覆盖，合并）
- 如果 **不存在**：创建新概念文章

```markdown
---
tags: [{相关标签}]
type: concept
updated_at: {日期}
---

# {概念名称}

一句话定义。

## 核心要点
- {要点}

## 关联
- [[{相关概念}]] — 关联原因

## 来源
- [[sources/{source-slug}]]
```

**5.3 更新索引**

在 `$OBSIDIAN_REPO/wiki/index.md` 中追加条目：

```markdown
## 概念
- [[concepts/{slug}]] — {一句话描述}

## 来源
- [[sources/{slug}]] — {一句话描述}
```

**5.4 追加日志**

在 `$OBSIDIAN_REPO/wiki/log.md` 中追加（文件不存在则创建）：

```markdown
## [{日期}] ingest | {标题}
- 类型：{类型}
- 来源：{来源}
- 新增概念：{概念列表}
- 编译状态：compiled
```

**5.5 更新 manifest**

更新 `$OBSIDIAN_REPO/.kb/manifest.json`，将新条目追加到 items 数组，status 为 `compiled`。

### 异常处理

| 场景 | 处理 |
|------|------|
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突（新旧信息矛盾） | 在概念文章中标注矛盾，追加说明 |
