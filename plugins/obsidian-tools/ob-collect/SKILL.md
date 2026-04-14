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
- ob-collect / ob-learn / 把这个加到知识库 / 记录一下这篇文章
- 采集视频 / 导入视频字幕 / 视频笔记
- 采集公众号 / 微信文章

示例：
- "ob-collect https://example.com/article"
- "帮我采集这篇文章到知识库"
- "把这个 PDF 导入知识库"
- "记录一下：RLHF 和 CoT 的关系"
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
└── notes/          # 自由笔记

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
| 纯文本 | 无 URL | `raw/notes/` | 用户自由输入 |

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
- 概念文章已存在时：读取并合并，不覆盖
- 概念冲突时：标注矛盾，追加说明
- 详细模板见 [references/compile-templates.md](references/compile-templates.md)

## 异常处理

| 场景 | 处理 |
|------|------|
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突 | 在文章中标注矛盾，追加说明 |
| 主题无法自动匹配 | 归入 synthesis/，用户可在确认时修改 |
| 视频字幕提取失败 | 调用 audio-to-obsidian skill，不可用时提示用户提供文字稿 |
