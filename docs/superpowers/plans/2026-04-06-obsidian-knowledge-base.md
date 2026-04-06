# Obsidian 知识库管理 Skills 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 obsidian-tools 插件下新增 4 个知识库管理 Skills（ob-learn、ob-index、ob-chat、ob-tidy），实现基于 llm-wiki 理念的 Obsidian 知识库管理。

**Architecture:** 四层架构（raw/wiki/outputs/.kb）+ 索引优先检索。4 个 Skills 通过 wiki/index.md 和 .kb/manifest.json 协作，形成采集→编译→消费→维护的复利循环。

**Tech Stack:** Claude Code SKILL.md 纯 Markdown，无代码依赖。读写文件用 Read/Write/Edit 工具。

**Spec:** `docs/superpowers/specs/2026-04-06-obsidian-knowledge-base-design.md`

---

## Chunk 1: 项目结构与基础设施

### Task 1: 创建 Skills 目录结构

**Files:**
- Create: `plugins/obsidian-tools/ob-learn/SKILL.md`
- Create: `plugins/obsidian-tools/ob-index/SKILL.md`
- Create: `plugins/obsidian-tools/ob-chat/SKILL.md`
- Create: `plugins/obsidian-tools/ob-tidy/SKILL.md`

- [ ] **Step 1: 创建 4 个 Skill 目录**

```bash
mkdir -p plugins/obsidian-tools/ob-learn
mkdir -p plugins/obsidian-tools/ob-index
mkdir -p plugins/obsidian-tools/ob-chat
mkdir -p plugins/obsidian-tools/ob-tidy
```

- [ ] **Step 2: 创建占位 SKILL.md 文件**

为每个 skill 创建最小 frontmatter 占位文件，确保目录结构正确：

`plugins/obsidian-tools/ob-learn/SKILL.md`:
```markdown
---
name: ob-learn
description: "TODO"
---
# ob-learn (占位)
```

同理创建 ob-index、ob-chat、ob-tidy 的占位文件。

- [ ] **Step 3: 验证目录结构**

```bash
ls -la plugins/obsidian-tools/*/
```

Expected: 看到 6 个目录（config-obsidian、ob-summary、ob-learn、ob-index、ob-chat、ob-tidy）

- [ ] **Step 4: Commit**

```bash
git add plugins/obsidian-tools/ob-learn/ plugins/obsidian-tools/ob-index/ plugins/obsidian-tools/ob-chat/ plugins/obsidian-tools/ob-tidy/
git commit -m "chore: 创建 4 个知识库管理 skill 目录占位"
```

### Task 2: 更新 plugin.json

**Files:**
- Modify: `plugins/obsidian-tools/.claude-plugin/plugin.json`

- [ ] **Step 1: 更新 plugin.json**

将版本从 `1.1.0` 升级为 `2.0.0`（新增 4 个 skills，属于 MAJOR 变更），添加新 skills 到列表：

```json
{
  "name": "obsidian-tools",
  "version": "2.0.0",
  "description": "Obsidian 工具集 - 笔记同步、知识库管理",
  "author": {
    "name": "Jacky Wang",
    "email": "wangjs.jacky@gmail.com",
    "url": "https://github.com/wangjs-jacky"
  },
  "homepage": "https://github.com/wangjs-jacky/jacky-skills/tree/main/plugins/obsidian-tools",
  "repository": "https://github.com/wangjs-jacky/jacky-skills",
  "license": "MIT",
  "keywords": [
    "claude-code",
    "obsidian",
    "notes",
    "sync",
    "knowledge"
  ],
  "skills": [
    "./config-obsidian/",
    "./ob-summary/",
    "./ob-learn/",
    "./ob-index/",
    "./ob-chat/",
    "./ob-tidy/"
  ]
}
```

- [ ] **Step 2: 验证 JSON 格式**

```bash
cat plugins/obsidian-tools/.claude-plugin/plugin.json | python3 -m json.tool
```

Expected: 无报错，输出格式化 JSON

- [ ] **Step 3: Commit**

```bash
git add plugins/obsidian-tools/.claude-plugin/plugin.json
git commit -m "feat(obsidian-tools): 升级 v2.0.0，新增 4 个知识库管理 skills"
```

---

## Chunk 2: ob-learn Skill

### Task 3: 编写 ob-learn SKILL.md

**Files:**
- Modify: `plugins/obsidian-tools/ob-learn/SKILL.md`

**参考模式:** `plugins/obsidian-tools/ob-summary/SKILL.md` 的 frontmatter 和结构

- [ ] **Step 1: 编写完整 SKILL.md**

```markdown
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

**URL** → `$OBSIDIAN_REPO/raw/web/{slug}.md`
**PDF** → `$OBSIDIAN_REPO/raw/pdf/{slug}.md`
**视频** → `$OBSIDIAN_REPO/raw/notes/{slug}.md`
**笔记** → `$OBSIDIAN_REPO/raw/notes/{slug}.md`

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

更新 `$OBSIDIAN_REPO/.kb/manifest.json`，将新条目的 status 改为 `compiled`。

### 异常处理

| 场景 | 处理 |
|------|------|
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突（新旧信息矛盾） | 在概念文章中标注矛盾，追加说明 |
```

- [ ] **Step 2: 验证文件格式**

```bash
head -5 plugins/obsidian-tools/ob-learn/SKILL.md
```

Expected: 看到 frontmatter（---name: ob-learn）

- [ ] **Step 3: Commit**

```bash
git add plugins/obsidian-tools/ob-learn/SKILL.md
git commit -m "feat(obsidian-tools): 新增 ob-learn 采集与编译 skill"
```

---

## Chunk 3: ob-index Skill

### Task 4: 编写 ob-index SKILL.md

**Files:**
- Modify: `plugins/obsidian-tools/ob-index/SKILL.md`

- [ ] **Step 1: 编写完整 SKILL.md**

```markdown
---
name: ob-index
description: "Obsidian 知识库索引构建与维护。当用户想要编译未处理资料、更新索引、整理知识库、发现笔记关联时触发此 skill。"
---

<role>Obsidian 知识库索引引擎，负责编译原始资料、构建/更新索引、发现知识关联、生成综合文章。</role>
<purpose>维护 wiki/index.md 作为知识库的导航核心，确保所有内容可被发现和关联。运行反思引擎发现二阶知识。</purpose>
<trigger>

```text
触发词：
- 编译知识库
- 更新索引
- 整理知识库
- ob-index
- 处理未编译内容
- 发现关联
- 反思引擎

示例：
- "ob-index"
- "编译知识库"
- "帮我整理一下知识库索引"
- "有哪些内容还没处理"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=compile,index,reflect</gsd:meta>
  <gsd:goal>处理所有未编译内容，维护索引完整性，发现知识间关联并生成综合文章。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO，检查 .kb/manifest.json 中未编译的条目。</gsd:phase>
  <gsd:phase>对每个未编译条目执行编译流程（同 ob-learn 的第五步）。</gsd:phase>
  <gsd:phase>编译完成后运行反思引擎：从索引摘要中发现跨领域主题、隐含关系、矛盾和空白。</gsd:phase>
  <gsd:phase>对证据充分的关联生成 synthesis 综合文章，更新索引。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库索引 (ob-index)

编译未处理内容，构建/更新知识库索引，发现关联并生成综合文章。

## 配置检查

1. 检查全局 CLAUDE.md 中 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户

## 执行流程

### 第一步：检查未编译内容

读取 `$OBSIDIAN_REPO/.kb/manifest.json`，筛选 `status: uncompiled` 的条目。

如果没有未编译内容：
```
所有资料已编译。是否需要：
1. 重建完整索引
2. 运行反思引擎
3. 退出
```

使用 AskUserQuestion 让用户选择。

### 第二步：编译未处理资料

对每个 `status: uncompiled` 的条目：

1. 读取 `$OBSIDIAN_REPO/raw/{type}/{slug}.md`
2. 执行编译流程（与 ob-learn 第五步相同）：
   - 生成 wiki/sources/{slug}.md
   - 创建/更新 wiki/concepts/{concept}.md
   - 更新 wiki/index.md
   - 追加 wiki/log.md
3. 更新 manifest.json 中该条目 status 为 `compiled`

**概念去重**（关键步骤）：

编译时如果发现 `wiki/concepts/` 中已有相似概念文章：
1. 读取现有文章
2. 用新信息更新，不创建重复文件
3. 如果新旧信息矛盾，在文章中用 `> [!warning] 矛盾标注` callout 标注

### 第三步：重建索引（可选）

如果用户选择重建完整索引：

1. 扫描 `$OBSIDIAN_REPO/wiki/` 下所有 `.md` 文件（排除 index.md、log.md）
2. 读取每个文件的 frontmatter 和第一段
3. 重新生成 `$OBSIDIAN_REPO/wiki/index.md`：

```markdown
# 知识库索引

> 最后更新：{日期}
> 文章总数：{数量}

## 概念
{按字母排序的概念条目，每行一个}

## 实体
{按字母排序的实体条目}

## 来源
{按日期倒序排列的来源条目}

## 综合
{按日期倒序排列的综合条目}
```

**索引条目格式**（每行一个）：
```
- [[{相对路径}]] — {一句话描述，≤ 80 字}
```

**渐进式索引**：

当文章总数超过 200 篇时，拆分为子索引：
- `wiki/concepts/index.md` 只含概念条目
- `wiki/entities/index.md` 只含实体条目
- `wiki/sources/index.md` 只含来源条目
- 主 `wiki/index.md` 只保留分类标题和子索引链接

### 第四步：运行反思引擎

编译完成后自动运行两阶段反思：

**阶段 1 — 发现（仅读索引）**

读取 `$OBSIDIAN_REPO/wiki/index.md`，从单行摘要中识别：

| 发现类型 | 检测方法 |
|----------|----------|
| 跨领域主题 | 一个概念出现在多个不相关来源中 |
| 隐含关系 | 两个概念看似相关但无 wikilink |
| 矛盾 | 不同来源对同一概念持对立立场 |
| 空白 | 多来源暗示但无专门文章的主题 |

输出 3-5 个候选关联，展示给用户：

```
发现以下潜在关联：
1. [[concepts/attention]] 和 [[concepts/rlhf]] — 都涉及"为相关性分配标量分数"
2. [[concepts/transformer]] 和 [[concepts/rlhf]] — transformer 是 RLHF 的基础架构
3. 空白：缺少 "scaling laws" 概念文章（3 个来源引用但无独立文章）

是否生成综合文章？（可选择感兴趣的关联）
```

**阶段 2 — 综合（定向深度阅读）**

对用户确认的候选：
1. 读取相关文章全文
2. 如果证据充分，生成 `$OBSIDIAN_REPO/wiki/synthesis/{slug}.md`

```markdown
---
tags: [synthesis, {相关标签}]
type: synthesis
created_by: ob-index-reflect
updated_at: {日期}
---

# {综合标题}

> 这是一篇综合文章，从已有知识中发现的新关联。

## 关联发现

{描述发现的关联或模式}

## 分析

{≤ 500 字的综合分析}

## 证据
- [[sources/{来源 1}]] — {贡献}
- [[sources/{来源 2}]] — {贡献}

## 相关概念
- [[concepts/{概念 1}]]
- [[concepts/{概念 2}]]
```

3. 更新 index.md 在"综合"分类下追加条目
4. 追加 log.md

### 第五步：首次初始化

如果检测到 `$OBSIDIAN_REPO/raw/` 和 `$OBSIDIAN_REPO/wiki/` 不存在，执行首次初始化：

1. 创建完整目录结构（raw/、wiki/ 及子目录、outputs/、.kb/）
2. 扫描 `$OBSIDIAN_REPO/` 中所有 `.md` 文件（排除 `.obsidian/`、`.kb/`）
3. 分类现有笔记：
   - **结构化笔记**（有标题、有内容、> 100 字）→ 复制到 `wiki/concepts/` 或 `wiki/sources/`
   - **碎片笔记**（短文本、速记、< 100 字）→ 复制到 `raw/notes/`
4. 生成初始 `wiki/index.md`
5. 创建 `.kb/manifest.json`
6. 生成初始 `wiki/log.md`

**注意**：不删除或移动原始文件，只读取和复制到新目录。

### 输出

执行完成后展示：

```
编译完成：
- 新编译：{数量} 篇
- 新概念：{数量} 个
- 新综合文章：{数量} 篇
- 索引更新：{数量} 条

索引总计：{总文章数} 篇文章
```
```

- [ ] **Step 2: 验证文件格式**

```bash
head -5 plugins/obsidian-tools/ob-index/SKILL.md
```

Expected: 看到 frontmatter（---name: ob-index）

- [ ] **Step 3: Commit**

```bash
git add plugins/obsidian-tools/ob-index/SKILL.md
git commit -m "feat(obsidian-tools): 新增 ob-index 索引构建与维护 skill"
```

---

## Chunk 4: ob-chat Skill

### Task 5: 编写 ob-chat SKILL.md

**Files:**
- Modify: `plugins/obsidian-tools/ob-chat/SKILL.md`

- [ ] **Step 1: 编写完整 SKILL.md**

```markdown
---
name: ob-chat
description: "Obsidian 知识库问答。当用户想要查询知识库、基于笔记回答问题、在知识库中搜索信息时触发此 skill。"
---

<role>Obsidian 知识库问答助手，通过索引优先的方式从知识库中检索并综合回答用户问题，答案归档回 wiki。</role>
<purpose>基于 wiki/index.md 导航知识库，选择最相关的文章综合回答，实现知识复利——每个答案都让知识库更丰富。</purpose>
<trigger>

```text
触发词：
- 问一下知识库
- 查询笔记
- ob-chat
- 知识库问答
- 在我的笔记中查找
- 根据我的知识库回答

示例：
- "ob-chat RLHF 和 chain-of-thought 有什么关系？"
- "在我的知识库中查找关于 Transformer 的内容"
- "问一下：注意力机制和 RLHF 有什么共同点？"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=query,answer,archive</gsd:meta>
  <gsd:goal>通过索引优先检索从知识库中找到最相关文章，综合回答用户问题，并将答案归档回 wiki 实现知识复利。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO，读取 wiki/index.md 作为导航入口。</gsd:phase>
  <gsd:phase>从索引中定位 1-2 个最相关子分类，选择 3-5 篇具体文章。</gsd:phase>
  <gsd:phase>读取选中的完整文章，综合回答用户问题，带 [[wikilinks]] 引用。</gsd:phase>
  <gsd:phase>将答案归档到 outputs/ 并追加回 index.md。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库问答 (ob-chat)

基于索引的知识库问答，答案归档实现知识复利。

## 配置检查

1. 检查全局 CLAUDE.md 中 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 检查 `$OBSIDIAN_REPO/wiki/index.md` 是否存在
4. 如果不存在，提示用户先运行 ob-index 初始化知识库

## 执行流程

### 第一步：读取索引

读取 `$OBSIDIAN_REPO/wiki/index.md`，获取知识库全局导航。

**如果索引文件过长**（超过 200 行）：
1. 先读取主索引中的分类标题
2. 根据问题定位到最相关的 1-2 个子分类
3. 读取对应的子索引文件

**如果知识库为空**：
```
知识库索引为空。请先使用 ob-learn 采集内容或使用 ob-index 初始化知识库。
```

### 第二步：定位相关文章

从索引的一行摘要中，选择 3-5 篇最相关的文章。

**选择标准**：
1. 标题或摘要直接包含问题关键词
2. 概念文章优先于来源文章（更凝练）
3. 综合文章优先（已经过二次提炼）

**展示检索过程**：
```
索引检索：
→ 分类：概念 → 选中 3 篇
  - [[concepts/rlhf]] — "用人类反馈强化学习对齐语言模型"
  - [[concepts/chain-of-thought]] — "引导模型逐步推理的提示技术"
  - [[concepts/attention]] — "让模型动态权衡 token 相关性"
→ 分类：来源 → 选中 2 篇
  - [[sources/instructgpt]] — "OpenAI 的 RLHF 实践"
  - [[sources/cot-paper]] — "Chain-of-Thought 原始论文"
```

### 第三步：读取并综合回答

1. 读取选中的 3-5 篇文章全文
2. 综合回答用户问题
3. 回答中所有知识库概念使用 `[[wikilinks]]` 引用
4. 底部列出参考文章

**回答格式**：

```markdown
## {回答标题}

{综合回答内容，使用 [[wikilinks]] 引用相关概念}

---

### 参考
- [[sources/{来源 1}]]
- [[concepts/{概念 1}]]
- [[synthesis/{综合文章}]]
```

### 第四步：归档答案

将答案归档到 `$OBSIDIAN_REPO/outputs/{YYYY-MM-DD}-{slug}.md`：

```markdown
---
tags: [qa, {相关标签}]
type: output
question: {用户原始问题}
created_at: {日期}
---

# {回答标题}

> 原始问题：{用户问题}

{完整回答内容}

### 参考
- [[sources/{来源 1}]]
- [[concepts/{概念 1}]]
```

### 第五步：更新索引（知识复利）

在 `$OBSIDIAN_REPO/wiki/index.md` 的"综合"或新增"输出"分类下追加：

```
- [[outputs/{slug}]] — Q&A: {问题简述}
```

追加 `$OBSIDIAN_REPO/wiki/log.md`：

```markdown
## [{日期}] ask | {问题简述}
- 参考文章：{引用列表}
- 输出：outputs/{slug}.md
```

### 无法回答时

如果知识库中没有足够信息回答问题：

```
知识库中未找到足够信息回答此问题。

已有相关内容：
- [[concepts/{相关概念}]] — 部分相关

建议采集以下内容以补充知识库：
1. {建议的来源/文章}
2. {建议的来源/文章}
```

将"无法回答"本身也记录为知识缺口，追加到 log.md。
```

- [ ] **Step 2: 验证文件格式**

```bash
head -5 plugins/obsidian-tools/ob-chat/SKILL.md
```

Expected: 看到 frontmatter（---name: ob-chat）

- [ ] **Step 3: Commit**

```bash
git add plugins/obsidian-tools/ob-chat/SKILL.md
git commit -m "feat(obsidian-tools): 新增 ob-chat 知识库问答 skill"
```

---

## Chunk 5: ob-tidy Skill

### Task 6: 编写 ob-tidy SKILL.md

**Files:**
- Modify: `plugins/obsidian-tools/ob-tidy/SKILL.md`

- [ ] **Step 1: 编写完整 SKILL.md**

```markdown
---
name: ob-tidy
description: "Obsidian 知识库健康检查与维护。当用户想要检查知识库健康度、修复断链、发现重复概念、整理知识库时触发此 skill。"
---

<role>Obsidian 知识库维护助手，负责检测并修复知识库中的断链、孤立、重复、缺失等问题。</role>
<purpose>保持知识库健康，确保索引完整、链接有效、概念无重复、文章结构规范。</purpose>
<trigger>

```text
触发词：
- 检查知识库
- 健康检查
- 知识库 lint
- ob-tidy
- 整理知识库
- 修复断链
- 去重

示例：
- "ob-tidy"
- "检查一下知识库健康状况"
- "帮我整理一下知识库"
- "知识库有没有断链"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=lint,fix,health</gsd:meta>
  <gsd:goal>检测知识库健康问题，生成报告并提供修复建议或自动修复。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO，扫描 wiki/ 目录下所有文件。</gsd:phase>
  <gsd:phase>运行六项健康检查：断链、孤立、重复、缺失、长文章、缺失索引。</gsd:phase>
  <gsd:phase>生成健康报告，展示问题清单（按优先级排序）。</gsd:phase>
  <gsd:phase>对可自动修复的问题提供修复选项，等待用户确认后执行。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库维护 (ob-tidy)

检测并修复知识库健康问题，生成健康报告。

## 配置检查

1. 检查全局 CLAUDE.md 中 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 检查 `$OBSIDIAN_REPO/wiki/` 目录是否存在
4. 如果不存在，提示用户先运行 ob-index 初始化

## 执行流程

### 第一步：扫描知识库

扫描 `$OBSIDIAN_REPO/wiki/` 下所有 `.md` 文件（排除 `index.md`、`log.md`）：

1. 读取每个文件的 frontmatter（tags、type、updated_at）
2. 提取所有 `[[wikilinks]]` 引用
3. 统计文件字数
4. 读取 `$OBSIDIAN_REPO/wiki/index.md` 获取索引条目

### 第二步：运行六项检查

#### 检查 1：断裂链接

**检测**：收集所有文章中的 `[[xxx]]` 引用，检查对应文件是否存在。

```python
# 伪代码
for file in wiki_files:
    links = extract_wikilinks(file)
    for link in links:
        if not file_exists(f"wiki/{link}.md"):
            broken_links.append((file, link))
```

**修复建议**：
- 创建占位概念文章（含 stub 标记）
- 或移除断裂链接（如果概念不再相关）

#### 检查 2：孤立文章

**检测**：统计每篇文章的入链数（被其他文章引用的次数）。入链为 0 的文章为孤立文章。

**标准**：孤立文章比例应 < 10%

**修复建议**：
- 检查是否有相关文章应该链接到它
- 考虑是否应该从索引中补充引用

#### 检查 3：重复概念

**检测**：比较 concepts/ 下所有文章的标题和内容相似度。

**检测方法**：
1. 标题相似（如 `attention` vs `attention-mechanism`）
2. 内容重叠度 > 60%
3. 引用了相同的来源文章

**修复建议**：使用合并功能，将两篇合并为一篇：
1. 读取两篇文章
2. 合并内容（去重保留所有独特信息）
3. 更新所有引用了旧文章的 wikilinks
4. 将旧文章移到 wiki/archive/（保留重定向说明）

#### 检查 4：缺失概念

**检测**：扫描所有来源文章和概念文章中的 `[[concepts/xxx]]` 引用，检查对应概念文章是否存在。

**修复建议**：列出待创建的概念文章清单。

#### 检查 5：长文章

**检测**：统计每篇文章字数。

**标准**：80% 的文章应在 200-500 字之间。

**修复建议**：对超过 500 字的文章，建议拆分为多个子概念。

#### 检查 6：缺失索引

**检测**：比较 wiki/ 下实际文件与 index.md 中的条目。

**修复建议**：直接补充缺失的索引条目（可自动修复）。

### 第三步：生成健康报告

**终端摘要**：

```
📊 知识库健康报告

总览：
- 文章总数：87
- 平均长度：420 字 ✅
- 索引覆盖率：92% ⚠️（7 篇未在索引中）
- 平均链接数：2.8 ⚠️（建议 ≥ 3）

问题清单（按优先级）：
1. 🔴 3 个断裂链接 → 需修复
2. 🔴 2 对重复概念 → 建议合并
3. 🟡 7 篇文章缺少索引条目 → 可自动修复
4. 🟡 12 篇文章链接数 < 2 → 建议补充
5. 🟢 4 篇孤立文章 → 可选修复
6. 🟢 1 篇文章 > 500 字 → 建议拆分
```

**完整报告**写入 `$OBSIDIAN_REPO/outputs/lint-{YYYY-MM-DD}.md`：

```markdown
---
tags: [lint, health-report]
type: output
created_at: {日期}
---

# 知识库健康报告 {日期}

## 总览

| 指标 | 值 | 状态 |
|------|-----|------|
| 文章总数 | {n} | — |
| 平均长度 | {n} 字 | ✅/⚠️/🔴 |
| 索引覆盖率 | {n}% | ✅/⚠️/🔴 |
| 平均链接数 | {n} | ✅/⚠️/⚠️ |

## 问题详情

### 🔴 断裂链接（{n} 个）
{每个断裂链接的详情：哪个文件引用了哪个不存在的文章}

### 🔴 重复概念（{n} 对）
{每对重复的详情：两篇文章路径和相似度}

### 🟡 缺失索引（{n} 篇）
{缺少索引条目的文章列表}

### 🟡 低链接文章（{n} 篇）
{链接数 < 2 的文章列表}

### 🟢 孤立文章（{n} 篇）
{无入链的文章列表}

### 🟢 长文章（{n} 篇）
{超过 500 字的文章及其字数}

## 修复建议

{按优先级排列的可执行修复步骤}
```

### 第四步：交互式修复

展示问题后，使用 AskUserQuestion 提供修复选项：

```
发现 {n} 个可自动修复的问题：
1. 补充 7 条缺失索引（自动）
2. 修复 3 个断裂链接（需确认修复方式）
3. 合并 2 对重复概念（需确认合并内容）

选择要执行的修复（可多选）：
□ 补充缺失索引
□ 修复断裂链接
□ 合并重复概念
□ 全部执行
```

**执行修复**：

对用户选择的每项修复：
1. 展示修复预览（将做什么改动）
2. 确认后执行
3. 每项修复一个 commit

### 追加日志

修复完成后追加 `$OBSIDIAN_REPO/wiki/log.md`：

```markdown
## [{日期}] lint | 健康检查
- 问题总数：{n}
- 已修复：{n}
- 报告：outputs/lint-{日期}.md
```
```

- [ ] **Step 2: 验证文件格式**

```bash
head -5 plugins/obsidian-tools/ob-tidy/SKILL.md
```

Expected: 看到 frontmatter（---name: ob-tidy）

- [ ] **Step 3: Commit**

```bash
git add plugins/obsidian-tools/ob-tidy/SKILL.md
git commit -m "feat(obsidian-tools): 新增 ob-tidy 健康检查与维护 skill"
```

---

## Chunk 6: 最终验证

### Task 7: 全量验证与链接

**Files:**
- Verify: `plugins/obsidian-tools/.claude-plugin/plugin.json`
- Verify: `plugins/obsidian-tools/ob-learn/SKILL.md`
- Verify: `plugins/obsidian-tools/ob-index/SKILL.md`
- Verify: `plugins/obsidian-tools/ob-chat/SKILL.md`
- Verify: `plugins/obsidian-tools/ob-tidy/SKILL.md`

- [ ] **Step 1: 验证 plugin.json 中所有 skills 可发现**

```bash
cat plugins/obsidian-tools/.claude-plugin/plugin.json | python3 -c "
import json, sys, os
data = json.load(sys.stdin)
base = 'plugins/obsidian-tools'
for skill in data['skills']:
    path = os.path.join(base, skill, 'SKILL.md')
    exists = os.path.exists(path)
    print(f'{'✅' if exists else '❌'} {skill} → {path}')
"
```

Expected: 所有 6 个 skills 显示 ✅

- [ ] **Step 2: 验证 SKILL.md frontmatter 格式**

```bash
for dir in ob-learn ob-index ob-chat ob-tidy; do
  echo "=== $dir ==="
  head -4 "plugins/obsidian-tools/$dir/SKILL.md"
  echo
done
```

Expected: 每个文件都有正确的 frontmatter（---、name、description、---）

- [ ] **Step 3: 链接到全局**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
j-skills link plugins/obsidian-tools/ob-learn
j-skills link plugins/obsidian-tools/ob-index
j-skills link plugins/obsidian-tools/ob-chat
j-skills link plugins/obsidian-tools/ob-tidy
```

- [ ] **Step 4: 安装到全局**

```bash
j-skills install ob-learn -g
j-skills install ob-index -g
j-skills install ob-chat -g
j-skills install ob-tidy -g
```

- [ ] **Step 5: 验证安装**

```bash
j-skills list -g | grep "ob-"
```

Expected: 看到 ob-learn、ob-index、ob-chat、ob-tidy 四个

- [ ] **Step 6: Final commit**

```bash
git add -A plugins/obsidian-tools/
git commit -m "feat(obsidian-tools): v2.0.0 完成，4 个知识库管理 skills 就绪"
```
