# Obsidian 知识库管理 Skills 设计文档

> 日期：2026-04-06
> 状态：已确认
> 插件：obsidian-tools（v1.0.0 → v2.0.0）

## 概述

在 obsidian-tools 插件下新增 4 个 Skills，打造一套可持续更新、持续记录的 Obsidian 知识库管理系统。参考 llm-wiki 的知识复利理念和四层架构，重新设计适合技术学习笔记场景的操作集。

### 核心原则

- **知识复利**：每次采集、每次问答都让知识库变得更好
- **索引优先**：通过 index.md 导航，而非 RAG 向量检索
- **半自动交互**：AI 先分析预览，用户确认后生成
- **扁平 + MOC 索引**：笔记扁平存放，通过 wikilinks 和 index.md 组织
- **不碰用户原有目录**：新增 raw/、wiki/、outputs/、.kb/ 四个管理目录

## 四个 Skills

```
采集 → 编译 → 消费 → 维护
ob-learn → ob-index → ob-chat → ob-tidy
  ↑                                │
  └──────── 知识复利循环 ←─────────┘
```

| Skill | 职责 | 触发词 |
|-------|------|--------|
| `ob-learn` | 采集任何来源（URL/PDF/视频/文本），编译到 wiki | 采集、摄入、导入、learn |
| `ob-index` | 构建/更新索引，发现关联，运行反思引擎 | 索引、编译、整理、index |
| `ob-chat` | 基于索引的知识库问答，答案归档回 wiki | 问答、查询、问一下 |
| `ob-tidy` | 健康检查：断链、孤立、重复、缺失 | 检查、健康检查、lint |

## 目录结构

```
jacky-obsidian/
├── raw/                        # 原始资料（不可变，LLM 只读）
│   ├── web/                    # 网页裁剪
│   ├── pdf/                    # PDF 文档
│   ├── images/                 # 图片（本地化）
│   └── notes/                  # 自由笔记
├── wiki/                       # LLM 编译维护
│   ├── index.md                # 全局索引（核心导航入口）
│   ├── log.md                  # 变更日志（只追加）
│   ├── concepts/               # 概念文章（≤ 500 字/篇）
│   │   └── index.md            # 概念子索引
│   ├── entities/               # 实体页面（人/组织/项目）
│   ├── sources/                # 来源摘要
│   ├── synthesis/              # 综合文章（LLM 自动生成）
│   └── archive/                # 归档（合并后的旧文章）
├── outputs/                    # 输出归档
│   ├── 2026-04-06-*.md         # 问答/分析输出
│   └── lint-2026-04-06.md      # 健康报告
├── .kb/                        # 系统状态（LLM 内部用）
│   ├── manifest.json           # 编译状态跟踪
│   └── reflect_state.json      # 反思状态
│
│   ─── 以下为用户原有目录，保持不动 ───
├── 00-Inbox/
├── 10-工作/
├── 20-学习/
├── ...（用户其他目录）
└── 99-模板/
```

## Skill 详细设计

### 1. ob-learn — 采集与编译

**半自动流程**：
```
用户输入来源 → 识别类型（URL/PDF/视频/文本）
    → 提取/抓取内容
    → 展示提取的关键点（预览）
    → 用户确认
    → 写入 raw/（带 frontmatter）
    → 编译到 wiki/：
        - 生成 wiki/sources/<slug>.md（结构化摘要 ≤ 500 字）
        - 提取概念，创建或更新 wiki/concepts/<concept>.md
        - 更新 wiki/index.md（追加单行条目）
        - 追加 wiki/log.md
    → 更新 .kb/manifest.json
```

**raw 文件 frontmatter**：
```yaml
---
source: https://example.com/article
ingested_at: 2026-04-06T10:00:00Z
type: web | pdf | video | note
status: uncompiled
---
```

**wiki 文章模板**：
```markdown
---
tags: [tag1, tag2]
type: concept | source | entity | synthesis
updated_at: 2026-04-06
---
# 标题

一句话定义。

## 核心要点
- 要点 1
- 要点 2

## 关联
- [[related-concept-1]] — 关联原因

## 来源
- [[sources/source-1]]
```

### 2. ob-index — 索引构建与维护

| 操作 | 说明 |
|------|------|
| 编译未处理 | 处理 raw/ 中所有 status: uncompiled 的文件 |
| 更新索引 | 扫描 wiki/ 所有文章，重建 wiki/index.md |
| 发现关联 | 从索引摘要中识别跨领域主题、隐含关系、矛盾、空白 |
| 生成综合文章 | 证据充分时生成 wiki/synthesis/ 文章（二阶知识） |

**index.md 格式**：
```markdown
# 知识库索引

## 概念
- [[concepts/attention]] — 让模型动态权衡 token 相关性的机制

## 实体
- [[entities/vaswani]] — Google Brain 研究员

## 来源
- [[sources/attention-is-all-you-need]] — Vaswani 2017

## 综合
- [[synthesis/scoring-mechanisms]] — RLHF 和注意力本质上解决同类问题
```

**渐进式索引**：文章超过 200 篇时，拆分为子索引。

### 3. ob-chat — 知识库问答

**查询流程**：
```
用户提问 → 读取 wiki/index.md
    → 定位 1-2 个最相关的子分类
    → 选择 3-5 篇具体文章
    → 读取完整文章，综合回答（带 [[wikilinks]] 引用）
    → 展示答案给用户
    → 答案归档到 outputs/YYYY-MM-DD-topic.md
    → 将输出追加回 wiki/index.md（知识复利）
```

### 4. ob-tidy — 健康检查与维护

| 检查项 | 说明 | 修复建议 |
|--------|------|----------|
| 断裂链接 | wikilinks 指向不存在的文件 | 创建占位文章或移除链接 |
| 孤立文章 | 无入链的文章（> 10%） | 建议补充关联 |
| 重复概念 | 近似 slug 或内容重叠 | 建议合并 |
| 缺失概念 | 来源中引用但无对应文章 | 列出待创建 |
| 长文章 | 超过 500 字的文章 | 建议拆分 |
| 缺失索引 | 文章未在 index.md 中 | 补充索引条目 |

**输出**：终端摘要 + outputs/lint-YYYY-MM-DD.md 完整报告。

## 与现有 Skill 集成

| 现有 Skill | 协作方式 |
|------------|----------|
| write-obsidian-note | ob-learn 编译完后调用它写入 Obsidian（REST/URI 同步） |
| ob-summary | ob-index 编译时复用其目录扫描能力 |
| config-obsidian | 提供同步模式配置，ob-learn 写文件时读取 |
| 视频处理 Skills | ob-learn 接收视频来源时调用视频转文本能力 |

不改动现有 Skill，新 Skills 在流程中按需调用。

## 首次使用：从现有 Vault 启动

ob-index 首次运行自动执行初始化：
1. 扫描 vault 中所有 .md 文件
2. 结构化笔记识别为候选 wiki 文章
3. 碎片笔记识别为原始资料，移入 raw/notes/
4. 生成初始 wiki/index.md
5. 创建 .kb/manifest.json

不删除任何用户文件，只读取、分类、建立索引。

## 版本升级

obsidian-tools：v1.0.0（2 skills） → v2.0.0（6 skills）
