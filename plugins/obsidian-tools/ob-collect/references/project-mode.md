# 项目沉淀模式详细流程

## 触发条件

- 用户明确说"沉淀到项目"、"保存到项目工作区"
- 用户说"记录一下"且当前对话上下文在某个项目目录中
- 用户指定了项目名称

## 项目识别

1. 优先使用用户指定的项目名
2. 其次从当前工作目录的 git remote 或目录名推导
3. 生成 slug：项目名转小写，空格和特殊字符转 `-`

## 内容分类

| 分类 | 子目录 | 说明 | 适用场景 |
|------|--------|------|----------|
| 设计决策 | `decisions/` | ADR 格式的架构/技术决策 | 选型、方案变更、权衡取舍 |
| 知识洞察 | `insights/` | 对话中提炼的知识 | 踩坑经验、调试结论、最佳实践 |
| 架构分析 | `architecture/` | 代码/系统架构分析 | 模块关系、数据流、状态管理 |

## 目录初始化

首次为项目创建时，生成完整结构：

```
wiki/projects/{project-slug}/
├── README.md
├── decisions/
├── insights/
├── architecture/
└── changelog.md
```

## 预览确认格式

```
项目：{项目名}
分类：{decisions|insights|architecture}
标题：{标题}
摘要：
  {2-3 句话概述}
标签：{标签}

确认沉淀？
```

## 文件写入模板

### 设计决策 (ADR)

`decisions/{YYYY-MM-DD}-{slug}.md`：

```markdown
---
type: adr
status: {accepted|deprecated|superseded}
date: {日期}
tags: [{标签}]
---

# {标题}

## 背景

{为什么需要做这个决策}

## 决策

{选择了什么方案}

## 理由

- {理由 1}
- {理由 2}

## 影响

{这个决策带来的影响}

## 相关
- [[projects/{project}/README]]
```

### 知识洞察

`insights/{YYYY-MM-DD}-{slug}.md`：

```markdown
---
type: insight
date: {日期}
tags: [{标签}]
source: {对话上下文或来源}
---

# {标题}

{洞察内容，建议 ≤ 300 字}

## 关联
- [[concepts/{相关概念}]] — 关联原因
- [[projects/{project}/README]]
```

### 架构分析

`architecture/{slug}.md`：

```markdown
---
type: architecture
date: {日期}
tags: [{标签}]
---

# {标题}

> {一句话概述}

## 架构图

{文字描述或 Mermaid 图}

## 核心模块

| 模块 | 职责 | 关键文件 |
|------|------|----------|
| {模块名} | {职责} | {文件路径} |

## 数据流

{数据如何在模块间流转}

## 关联
- [[projects/{project}/README]]
- [[concepts/{相关概念}]]
```

## 项目 README 更新

每次沉淀后更新 README.md：

1. 更新 `updated_at` 日期
2. 在对应分类下追加链接：
   ```markdown
   ### 设计决策
   - [[decisions/{slug}]] — {一句话描述}

   ### 知识洞察
   - [[insights/{slug}]] — {一句话描述}

   ### 架构分析
   - [[architecture/{slug}]] — {一句话描述}
   ```

## Changelog 更新

追加到 `changelog.md`：

```markdown
## [{日期}] {操作}
- 分类：{分类}
- 标题：{标题}
- 新增文件：{文件路径}
```

## 与 wiki 全局的联动

1. 在 `wiki/index.md` 的 `## 项目` 分区追加项目链接
2. 如果沉淀内容涉及新的通用概念，同时在 `wiki/concepts/` 创建概念文章
3. 在 `wiki/log.md` 追加操作记录
4. 更新 `.kb/manifest.json`
