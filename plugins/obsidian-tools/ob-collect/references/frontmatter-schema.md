# Frontmatter 规范

> 所有写入 `wiki/` 的 `.md` 文件必须遵循此规范。三个写入 skill（ob-topic、ob-collect、ob-project-log）共享。

## 预定义 type 值

| type | 含义 | 典型场景 |
|------|------|---------|
| `concept` | 概念解释 | 解释某个技术概念、术语、模式 |
| `tutorial` | 教程/操作指南 | 手把手步骤、配置流程、发布指南 |
| `troubleshooting` | 问题解决 | Bug 排查、踩坑记录、修复方案 |
| `learning` | 学习笔记 | 从项目/资源中学习的记录 |
| `reference` | 参考资料 | API 文档、速查表、技术栈分析、对比报告、决策记录 |
| `note` | 普通笔记 | 时事归纳、观点收集、综合分析 |
| `index` | 索引文件 | 目录索引（自动生成，不手动设置） |

**禁止使用**：`topic`、`synthesis`、`wiki`、`analysis`、`project-knowledge`、`decision`、`insight`、`transcript` 等非标准值。

## type 选择指南

```
这篇文章的主要目的是什么？
├─ 解释"是什么" → concept
├─ 教"怎么做" → tutorial
├─ 解决"出了什么问题" → troubleshooting
├─ 记录"学到了什么" → learning
├─ 提供"查阅参考" → reference
└─ 其他 → note
```

**特殊情况**：
- 视频/音频归纳笔记 → `note`（归纳性内容）
- 项目架构文档 → `reference`
- 技术选型决策 → `reference`
- 踩坑修复记录 → `troubleshooting`

## 必填字段

```yaml
---
tags: [{标签数组，至少 1 个}]    # 必填：非空数组
type: {预定义类型}               # 必填：必须是上表中的值
updated_at: {YYYY-MM-DD}        # 必填：有效的日期格式
---
```

## 推荐字段

```yaml
---
created_at: {YYYY-MM-DD}        # 推荐：创建日期
source: {来源}                   # 推荐：conversation / URL / 项目名
---
```

## 写入后验证清单

写入文件后，自动执行以下验证：

1. **Frontmatter 完整性**：确认 tags（非空）、type（预定义值）、updated_at（有效日期）三个必填字段存在
2. **Wikilink 有效性**：扫描所有 `[[xxx]]` 引用，确认目标文件存在于 vault 中
3. **索引一致性**：确认文章已出现在对应目录的 `index.md` 中
4. **交叉引用**：扫描同目录已有文章的 tags，在主题相关的文章中添加 `[[新文章名]]` 反向链接

验证失败时的处理：
- frontmatter 缺失字段 → 立即补充
- wikilink 无效 → 移除或替换为有效链接
- 索引未更新 → 立即更新 index.md
- 无交叉引用 → 在最相关的 1-2 篇文章中添加链接

## raw 层契约

> **raw 层契约与 wiki 层契约并列存在，两者契约对象不同**：wiki 是编译产物（面向阅读），raw 是原始资料（面向编译/索引引擎）。raw 层 frontmatter 是 ob-collect / ob-compile / ob-index 之间的接口协议。

### 必填字段

```yaml
---
status: {uncompiled | compiled}    # 必填：编译状态
type: source                       # 必填：raw 层固定为 source
tags: [{标签数组，至少 1 个}]       # 必填：非空数组
updated_at: {YYYY-MM-DD}           # 必填：有效的日期格式
---
```

### 推荐字段

```yaml
---
source_url: {原始 URL}              # 推荐：来源链接
publish_date: {YYYY-MM-DD}          # 推荐：原文发布日期
author: {作者名}                    # 推荐：作者/账号
article_id: OBA-{8位随机}           # 推荐：全局唯一 ID
---
```

### status 字段语义

| 值 | 含义 |
|----|------|
| `uncompiled` | 已采集但未编译到 wiki/。属于待处理状态，ob-compile 会扫描此状态批量编译。 |
| `compiled` | 已被 ob-compile 编译过，或长文一站式模式下 ob-collect 同步完成编译。 |

### status 翻转责任方

| 责任 | 责任方 | 时机 |
|------|--------|------|
| **写入初始 status** | ob-collect | 写 raw/*.md 时强制带 status |
| **翻转 uncompiled → compiled** | ob-compile | 完成 wiki 编译后回写 raw 层 status |
| **消费 status 做差异筛选** | ob-index | 扫描时跳过 uncompiled，仅索引 compiled |

### 契约违约后果

- raw 缺失 status → ob-compile 无法判断哪些待编译，ob-index 索引漂移
- ob-collect 不写 status → 契约链断裂，下游引擎需要兜底逻辑（不可接受）
- 长文一站式忘记标 `compiled` → 重复编译

### 写入示例

**长文一站式模式**：
```yaml
---
status: compiled
type: source
tags: [ai, llm]
updated_at: 2026-05-21
source_url: https://example.com/article
author: 唱山羊
article_id: OBA-k7jm2p9q
---
```

**集锦批量模式**：
```yaml
---
status: uncompiled
type: source
tags: [ai, llm]
updated_at: 2026-05-21
source_url: https://example.com/article
author: 唱山羊
---
```
