# 编译模板参考

## 主题文章模板

写入 `wiki/{theme}/{slug}.md`：

```markdown
---
tags: [{标签列表}]
type: {预定义类型}    # concept/tutorial/troubleshooting/learning/reference/note，见 frontmatter-schema
---

# {标题}

> 来源：{原始来源}

## 核心要点
- {要点 1}
- {要点 2}
- {要点 3}

## 详细内容

{结构化摘要，建议 ≤ 500 字，超出部分拆分到关联文章并通过 [[reference]] 链接}

## 关联

- [[{theme}/concepts/{概念 1}]] — 关联原因
- [[{theme}/concepts/{概念 2}]] — 关联原因
- [[{其他主题}/{文章}]] — 跨主题关联

## 原始资料

- [[raw/{类型}/{slug}]]
```

## Concept 文章模板

写入 `wiki/{theme}/concepts/{concept-slug}.md`：

- 已存在：读取现有内容，用新信息合并（不覆盖）
- 不存在：创建新文件

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
- [[{theme}/concepts/{相关概念}]] — 关联原因
- [[{theme}/{相关文章}]] — 相关文章

## 来源
- [[{theme}/{source-slug}]]
```

## 主题 Index 更新格式

在 `wiki/{theme}/index.md` 追加：

```markdown
## {类型分类}

- [[{slug}]] — {一句话描述}
```

类型分类示例：
- `## 概念` — 概念文章
- `## 文章` — 主题文章
- `## 指南` — 教程指南

## 全局 Index 更新格式

仅当 `wiki/index.md` 中不存在该主题入口时，追加：

```markdown
## {主题名}

- [[{theme}/index|{主题名}]] — {一句话描述}
```

## Log 更新格式

在 `wiki/log.md` 追加：

```markdown
## [{日期}] {操作类型} | {标题}
- 类型：{类型}
- 主题：{主题目录}
- 来源：{来源}
- 新增概念：{概念列表}
- 编译状态：compiled
```

操作类型：
- `ingest`：采集模式
