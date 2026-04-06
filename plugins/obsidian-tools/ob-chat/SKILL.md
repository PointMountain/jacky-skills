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
