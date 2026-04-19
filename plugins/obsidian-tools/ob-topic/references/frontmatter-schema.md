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
