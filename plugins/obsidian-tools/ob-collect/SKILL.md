---
name: ob-collect
description: "Obsidian 知识库采集助手。从多种来源（网页、微信公众号、视频、资讯、官方文档）采集内容到 raw/ 并编译为结构化 wiki 笔记。触发词：采集、导入知识库、ob-collect、ob-learn。"
---

<role>Obsidian 知识库采集助手。从网页、微信公众号、视频平台、资讯聚合、官方文档等来源提取内容，编译为结构化 wiki 笔记。</role>
<purpose>采集模式 — 将 URL/PDF/视频/文本采集到 raw/ 并编译到 wiki/{theme}/。建议 ≤ 500 字，超出部分用 [[reference]] 链接补充。</purpose>
<trigger>

```text
触发词：
- 采集文章 / 导入到知识库 / 学习记录 / 摄入资料
- ob-collect / ob-learn / 把这个加到知识库
- 采集视频 / 导入视频字幕 / 视频笔记
- 采集公众号 / 微信文章

示例：
- "ob-collect https://example.com/article"
- "帮我采集这篇文章到知识库"
- "把这个 PDF 导入知识库"
- "采集一下这篇文章：RLHF 和 CoT 的关系"
- "采集这个微信公众号文章"
- "把这个 B 站视频的字幕导入"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO; focus=ingest,compile</gsd:meta>
  <gsd:goal>将来源采集到 raw/ 编译到 wiki/{theme}/。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO 路径，识别输入类型和来源平台。</gsd:phase>
  <gsd:phase>平台检测 → 主题分类 → 提取内容 → 预览确认 → 写入 raw/ → 编译到 wiki/{theme}/。</gsd:phase>
  <gsd:phase>更新索引：wiki/{theme}/index.md、wiki/index.md（新主题时）、wiki/log.md、.kb/manifest.json。</gsd:phase>
</gsd:workflow>

# Obsidian 知识库采集 (ob-collect)

## 配置检查

**执行前必读**：本 skill 需要使用 Obsidian 仓库路径。

1. 首先检查全局 CLAUDE.md 中是否定义了 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 将用户提供的路径保存为 `$OBSIDIAN_REPO` 变量供后续使用

**目录初始化检查**：

首次使用时，确认以下目录存在（不存在则创建）：

```
$OBSIDIAN_REPO/raw/
├── web/            # 通用网页采集（博客、技术文章等）
├── wechat/         # 微信公众号文章
├── videos/         # 视频平台字幕（B站、抖音、小红书等）
├── news/           # 资讯聚合（Hacker News、Reddit 等）
├── official/       # 官方文档和文章（Claude Code、OpenAI 等）
├── notes/          # 自由笔记（人工输入的原始文档）
├── ai-notes/       # AI 调研产出（AI 查询/分析/整理的原始资料）
└── [作者名]/       # 音视频按作者归档（write-obsidian-note 兼容）

$OBSIDIAN_REPO/wiki/{ai,claude,current-affairs,career,dev-tools,front-end,obsidian,synthesis}/
$OBSIDIAN_REPO/.kb/
```

如果 `wiki/index.md` 不存在，创建初始索引。

## 来源平台检测

根据 URL 域名或内容来源自动识别平台，决定 raw/ 子目录：

| 平台 | 域名/特征 | raw 子目录 | 说明 |
|------|-----------|------------|------|
| 微信公众号 | `mp.weixin.qq.com` | `raw/wechat/` | 微信公众号文章 |
| 通用网页 | 其他 HTTP URL | `raw/web/` | 博客、技术文章、个人网站 |
| B 站 | `bilibili.com` | `raw/videos/` | 视频字幕采集 |
| 抖音 | `douyin.com` | `raw/videos/` | 短视频 |
| 小红书 | `xiaohongshu.com` | `raw/videos/` | 图文+视频 |
| YouTube | `youtube.com`, `youtu.be` | `raw/videos/` | YouTube 视频 |
| Hacker News | `news.ycombinator.com` | `raw/news/` | 科技资讯 |
| Reddit | `reddit.com` | `raw/news/` | 社区讨论 |
| Claude Code | Claude Code 官方文档/博客 | `raw/official/` | Anthropic 官方 |
| OpenAI | OpenAI 官方文档/博客 | `raw/official/` | OpenAI 官方 |
| PDF | 本地 `.pdf` 文件 | `raw/web/` | PDF 文档 |
| 纯文本 | 无 URL，人工输入 | `raw/notes/` | 用户自由输入的原始文档 |
| AI 调研 | 无 URL，AI 查询产出 | `raw/ai-notes/` | AI 分析/调研/整理的原始资料 |

**检测优先级**：域名精确匹配 → 平台关键词 → 默认归类

## 主题分类

采集内容需要确定目标 wiki 主题目录。按以下优先级判断：

1. **用户指定**：用户说"放到 Claude"、"归类到时事" → 直接使用
2. **关键词匹配**：根据内容关键词自动推荐

### 主题关键词映射

| 主题 | 目录 | 关键词 |
|------|------|--------|
| AI 技术 | `wiki/ai/` | AI, LLM, GPT, transformer, 机器学习, 深度学习 |
| Claude 生态 | `wiki/claude/` | Claude, Claude Code, Skills, MCP, hooks, Subagents |
| 开发工具 | `wiki/dev-tools/` | VSCode, IDE, 编辑器, CLI, 终端, Git |
| 前端开发 | `wiki/front-end/` | React, JavaScript, TypeScript, CSS, 前端, 算法 |
| 时事分析 | `wiki/current-affairs/` | 经济, 政治, 国际, 金融, 投资, 时事 |
| 职业发展 | `wiki/career/` | 职级, 面试, 求职, 职业规划 |
| Obsidian | `wiki/obsidian/` | Obsidian, 知识管理, 笔记, 双链 |

无匹配时归入 `wiki/synthesis/`（跨主题综合）。

匹配后展示推荐主题，用户可在确认时修改。

## 采集模式

详见 [references/collect-mode.md](references/collect-mode.md)

### 流程概要

1. **识别输入类型**：URL → WebFetch，PDF → Read，视频 → audio-to-obsidian，文本 → 直接使用
2. **平台检测**：根据 URL 域名确定 raw/ 子目录
3. **主题分类**：根据关键词映射确定目标主题目录
4. **提取内容**：抓取/读取正文，提取关键要点（3-5 条）
5. **预览确认**：展示平台、主题、标题、来源、要点、标签，等待用户确认
6. **写入 raw/**：带 frontmatter 的原始笔记
7. **编译到 wiki/{theme}/**：生成主题文章 → 创建/更新概念 → 更新主题 index → 更新全局 index/log/manifest

### 关键规则

- 文件名规范：`{YYYY-MM-DD}-{slug}.md`
- **article_id 分配**：每篇新建的 wiki 文章必须在 frontmatter 中包含 `article_id` 字段
  - 格式：`OBA-{8位随机小写字母数字}`（如 `OBA-k7jm2p9q`）
  - 全局唯一：随机生成后验证唯一性
  - 生成命令：`python3 -c "import random,string; print(''.join(random.choices(string.ascii_lowercase+string.digits,k=8)))"`
  - 验证命令：`grep -rh "OBA-{生成的ID}" "$OBSIDIAN_REPO/wiki/" --include="*.md"`（无输出则唯一）
  - 如果碰撞则重新生成，直到唯一
- 概念文章已存在时：读取并合并，不覆盖
- 概念冲突时：标注矛盾，追加说明
- 详细模板见 [references/compile-templates.md](references/compile-templates.md)

## 视频/音频采集模式

当采集来源为视频（YouTube/B站/播客等）或音频时，使用以下专用模板和规则。

> 此模式合并自 write-obsidian-note skill，统一由 ob-collect 管理。

### raw 模板（带时间轴分段）

视频/音频的 raw 层按作者名归档：`raw/[作者名]/标题.md`

```markdown
---
source: "https://..."
author: "作者名"
ingested_at: {YYYY-MM-DD}
type: transcript
category: Audio
duration: "10:30"
status: uncompiled
tags: [音频笔记, {作者名}]
---

# 标题

### 0:00 主题段落标题

句子内容，可以多句组成一个语义完整的段落。
每段以 `### M:SS 主题标题` 开头，方便 Obsidian heading 跳转。

### 1:30 下一个主题段落标题

下一段内容...

---
#音频笔记 #{作者名}
```

**关键规则**：
- 每个语义段落用 `### M:SS 标题` 作为 heading
- raw 层不可变：写入后不再修改
- 文件名特殊字符替换为下划线，长度 ≤ 200 字符

### wiki 归纳模板

视频/音频的 wiki 层生成归纳笔记，用 `[[raw/作者名/标题]]` 引用 raw 层原文。

```markdown
---
article_id: OBA-k7jm2p9q
tags: [{主题标签}, {作者名}, 归纳]
type: {预定义类型}
updated_at: {YYYY-MM-DD}
---

# 标题 - 归纳

> **作者**: {author}
> **来源**: {url}
> **时长**: {duration}
> **提取时间**: {date}
> **原文**: [[raw/作者名/标题]]

[embedCode — 如有则插入，如 B 站 iframe]

## 音频来源

> [!quote] 🔗 [点击播放]({url})

---

## 核心观点

### 1. {观点标题}

简明扼要地概括这个观点（2-5句话）。
包括论据、因果逻辑、关键数据。

→ [[raw/作者名/标题#1:30]] ~ [[raw/作者名/标题#3:45]]

### 2. {观点标题}

下一个核心观点的概括。

→ [[raw/作者名/标题#5:00]] ~ [[raw/作者名/标题#7:20]]

## 关键引用

> [原文金句1] — [[raw/作者名/标题#2:15]]

> [原文金句2] — [[raw/作者名/标题#8:30]]

## 我的思考

[待补充]

---
#音频笔记 #{作者名} #归纳
```

### 归纳生成规则

AI 归纳视频/音频内容时遵循以下原则：

1. **观点拆解**：将内容拆解为 3-7 个核心观点/论点，每个有独立标题
2. **raw 引用**：每个观点必须用 `[[raw/作者名/标题#M:SS]]` 链接到 raw 层原文的 heading
3. **时间范围**：观点跨多段时用 `~` 连接起止：`[[raw/作者名/标题#1:30]] ~ [[raw/作者名/标题#3:45]]`
4. **不搬运原文**：归纳用自己的话概括，不直接复制原文句子
5. **关键结论**：提炼 3-5 条一句话可消化的结论，附链接
6. **金句引用**：选取 2-4 条原文中最有表达力的原话，附链接
7. **我的思考**：留空，供用户自行补充
8. **不做延伸**：只归纳，不添加 transcript 中没有的观点

### 作者索引

视频/音频写入后自动维护 `raw/index.md` 作者索引：

```markdown
---
type: index
updated_at: {YYYY-MM-DD}
authors: {N}
files: {N}
---

# 作者索引

> 自动维护 · {N} 位作者 · {N} 篇资料

## 作者A

- [[raw/作者A/标题1]] — {YYYY-MM-DD}
- [[raw/作者A/标题2]] — {YYYY-MM-DD}

## 作者B

- [[raw/作者B/标题3]] — {YYYY-MM-DD}
```

### 写入后验证

遵循 [frontmatter-schema](references/frontmatter-schema.md) 中的验证清单：
1. **Frontmatter**：确认 tags（非空）、type（预定义值）、updated_at 存在
2. **Wikilink**：扫描所有 `[[xxx]]` 引用，确认目标文件存在于 vault 中
3. **索引**：确认文章已出现在对应 `wiki/{theme}/index.md` 中
4. **交叉引用**：在同目录已有文章中查找 tags 重叠的文章，添加反向链接

## 异常处理

| 场景 | 处理 |
|------|------|
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突 | 在文章中标注矛盾，追加说明 |
| 主题无法自动匹配 | 归入 synthesis/，用户可在确认时修改 |
| 视频字幕提取失败 | 调用 audio-to-obsidian skill，不可用时提示用户提供文字稿 |
