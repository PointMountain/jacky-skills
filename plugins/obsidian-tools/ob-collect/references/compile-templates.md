# 编译模板参考

## Source 摘要模板

写入 `wiki/sources/{slug}.md`：

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

{结构化摘要，建议 ≤ 500 字，超出部分拆分到关联文章并通过 [[reference]] 链接}

## 关联概念
- [[concepts/{概念 1}]] — 关联原因
- [[concepts/{概念 2}]] — 关联原因

## 原始资料
- [[raw/{类型}/{slug}]]
```

## Concept 文章模板

写入 `wiki/concepts/{concept-slug}.md`：

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
- [[{相关概念}]] — 关联原因

## 来源
- [[sources/{source-slug}]]
```

## Index 更新格式

在 `wiki/index.md` 追加：

```markdown
## 概念
- [[concepts/{slug}]] — {一句话描述}

## 来源
- [[sources/{slug}]] — {一句话描述}

## 项目
- [[projects/{project-slug}/README]] — {一句话描述}
```

初始 index.md：

```markdown
# 知识库索引

> 最后更新：{当前日期}

## 概念

## 实体

## 来源

## 综合

## 项目
```

## Log 更新格式

在 `wiki/log.md` 追加：

```markdown
## [{日期}] {操作类型} | {标题}
- 类型：{类型}
- 来源：{来源}
- 新增概念：{概念列表}
- 编译状态：compiled
```

操作类型：
- `ingest`：采集模式
- `project`：项目沉淀模式
