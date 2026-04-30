---
name: ob-collect
description: "Obsidian 万物采集器。基于 OpenCLI 统一输入层，从 100+ 站点（文章、视频、播客、社交媒体、书籍、新闻）采集内容到 raw/ 并编译为结构化 wiki 笔记。支持批量并行、断点续传。触发词：采集、导入知识库、ob-collect、视频转笔记、采集书签、批量采集。"
---

<role>Obsidian 万物采集器。基于 OpenCLI 统一输入层，从网页、社交媒体、视频平台、播客、书籍、新闻等来源提取内容，编译为结构化 wiki 笔记。</role>
<purpose>采集模式 — 将 URL/PDF/视频/文本采集到 raw/ 并编译到 wiki/{theme}/。建议 ≤ 500 字，超出部分用 [[reference]] 链接补充。</purpose>
<trigger>

```text
触发词：
- 采集文章 / 导入到知识库 / 学习记录 / 摄入资料
- ob-collect / ob-learn / 把这个加到知识库
- 采集视频 / 视频转笔记 / 导入视频字幕
- 采集公众号 / 微信文章
- 采集书签 / 采集收藏 / 采集稍后观看
- 批量采集 / 处理这些链接
- 采集我的 Twitter 书签 / B站收藏 / YouTube 稍后

示例：
- "ob-collect https://example.com/article"
- "帮我采集这篇文章到知识库"
- "把这个 PDF 导入知识库"
- "采集一下这篇文章：RLHF 和 CoT 的关系"
- "采集这个 B 站视频的字幕"
- "批量采集这些链接：url1, url2, url3"
- "采集我的 YouTube 稍后观看"
```

</trigger>
<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>requires=OBSIDIAN_REPO,opencli; focus=ingest,compile</gsd:meta>
  <gsd:deps>
    <dep name="audio-to-subtitle" source="plugin" pluginName="video-processing" skillName="audio-to-subtitle" />
  </gsd:deps>
  <gsd:goal>将来源采集到 raw/ 编译到 wiki/{theme}/。</gsd:goal>
  <gsd:phase>获取 OBSIDIAN_REPO 路径，识别输入类型和来源平台。</gsd:phase>
  <gsd:phase>OpenCLI 路由 → 获取内容 → 主题分类 → 预览确认 → 写入 raw/ → 编译到 wiki/{theme}/。</gsd:phase>
  <gsd:phase>更新索引：wiki/{theme}/index.md、wiki/index.md（新主题时）、wiki/log.md、.kb/manifest.json。如果当前在 git 项目中，同步更新项目 CLAUDE.md 的 Obsidian 索引段。</gsd:phase>
</gsd:workflow>

# Obsidian 万物采集 (ob-collect)

## 配置检查

**执行前必读**：本 skill 需要以下配置。

1. 检查全局 CLAUDE.md 中是否定义了 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 将用户提供的路径保存为 `$OBSIDIAN_REPO` 变量供后续使用
4. 检查 `opencli` 是否可用：`opencli doctor`，三项全绿才继续

**脚本依赖检查**：

掘金小册采集功能需要本地脚本依赖。执行相关功能前检查：

1. 检查 `{SKILL_DIR}/scripts/node_modules/` 是否存在
2. 如果不存在，执行：`cd {SKILL_DIR}/scripts && npm install`
3. 安装完成后继续执行

> `{SKILL_DIR}` 为本 SKILL.md 所在目录的绝对路径。

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
├── juejin/         # 掘金小册（全书提取，含图片）
└── [作者名]/       # 音视频按作者归档

$OBSIDIAN_REPO/wiki/{ai,claude,current-affairs,career,dev-tools,front-end,obsidian,tauri,distill}/
$OBSIDIAN_REPO/.kb/
```

如果 `wiki/index.md` 不存在，创建初始索引。

## OpenCLI 路由层

> **核心原则**：OpenCLI 为主引擎，WebFetch 为回退。

### 来源平台检测 + 命令映射

根据 URL 域名自动识别平台，选择最佳获取方式：

| 平台 | 域名 | raw 目录 | OpenCLI 命令（主引擎） | 回退 |
|------|------|----------|----------------------|------|
| 知乎 | `zhihu.com` | `raw/web/` | `opencli zhihu answer <id>` | WebFetch |
| 36氪 | `36kr.com` | `raw/web/` | `opencli 36kr article <id>` | WebFetch |
| Hacker News | `news.ycombinator.com` | `raw/news/` | `opencli hackernews read <id>` | WebFetch |
| Reddit | `reddit.com` | `raw/news/` | `opencli reddit read <id>` | WebFetch |
| Twitter/X | `twitter.com`, `x.com` | `raw/web/` | `opencli twitter thread <id>` | WebFetch |
| B站 | `bilibili.com` | `raw/videos/` | `opencli bilibili subtitle <bv>` → `video <bv>` | — |
| YouTube | `youtube.com`, `youtu.be` | `raw/videos/` | `opencli youtube transcript <url>` → `video <url>` | — |
| 小宇宙 | `xiaoyuzhou.fm` | `raw/videos/` | `opencli xiaoyuzhou transcript <id>` → `episode <id>` | — |
| 微信公众号 | `mp.weixin.qq.com` | `raw/wechat/` | `opencli web read <url>` | WebFetch |
| Medium | `medium.com` | `raw/web/` | `opencli web read <url>` | WebFetch |
| Substack | `substack.com` | `raw/web/` | `opencli web read <url>` | WebFetch |
| 豆瓣 | `douban.com` | `raw/web/` | `opencli douban subject <id>` | WebFetch |
| 掘金小册 | `juejin.cn/book/` | `raw/juejin/` | 专用脚本（见掘金小册章节） | — |
| 通用网页 | 其他 HTTP URL | `raw/web/` | `opencli web read <url>` | WebFetch |
| PDF | 本地 `.pdf` 文件 | `raw/web/` | Read 工具 | — |
| 纯文本 | 无 URL，人工输入 | `raw/notes/` | 直接使用 | — |
| AI 调研 | 无 URL，AI 产出 | `raw/ai-notes/` | 直接使用 | — |

**检测优先级**：域名精确匹配 → 平台关键词 → 默认归类

**路由逻辑**：
1. 平台有 OpenCLI 命令映射 → 优先用 OpenCLI（`-f json` 获取结构化数据）
2. OpenCLI 失败 → 文章类回退 WebFetch，视频类报告失败原因
3. 无 OpenCLI 映射的平台 → 直接 WebFetch

### 路由执行模板

```bash
# 文章类：OpenCLI 优先 + WebFetch 回退
opencli zhihu answer <id> -f json     # 优先
# 失败时回退 WebFetch

# 视频类：字幕优先 + ASR 回退
opencli youtube transcript <url> -f json   # 第一步：获取字幕
opencli youtube video <url> -f json        # 同时获取元信息
# 无字幕时：
opencli youtube download <url> -o /tmp/    # 下载
python3 {A2S_DIR}/scripts/transcribe.py /tmp/audio.wav --engine local -f md --yolo  # ASR

# 通用网页
opencli web read <url>                     # OpenCLI 渲染感知读取
# 失败时回退 WebFetch
```

> `{A2S_DIR}` 为 audio-to-subtitle skill 所在目录。路径：`/Users/jiashengwang/jacky-github/jacky-skills/plugins/video-processing/skills/audio-to-subtitle`

## 主题分类

采集内容需要确定目标 wiki 主题目录。按以下优先级判断：

1. **用户指定**：用户说"放到 Claude"、"归类到时事" → 直接使用
2. **关键词匹配**：根据内容关键词自动推荐

### 主题关键词映射

| 主题 | 目录 | 关键词 |
|------|------|--------|
| AI 技术 | `wiki/ai/` | AI, LLM, GPT, transformer, 机器学习, 深度学习 |
| Claude 生态 | `wiki/claude/` | Claude, Claude Code, Skills, MCP, hooks, Subagents |
| Tauri | `wiki/tauri/` | Tauri, 桌面应用, tauri-app, Sidecar, invoke |
| 开发工具 | `wiki/dev-tools/` | VSCode, IDE, 编辑器, CLI, 终端, Git |
| 前端开发 | `wiki/front-end/` | React, JavaScript, TypeScript, CSS, 前端, 算法 |
| 时事分析 | `wiki/current-affairs/` | 经济, 政治, 国际, 金融, 投资, 时事 |
| 职业发展 | `wiki/career/` | 职级, 面试, 求职, 职业规划 |
| Obsidian | `wiki/obsidian/` | Obsidian, 知识管理, 笔记, 双链 |

无匹配时自动创建新主题目录（kebab-case 英文命名）。

匹配后展示推荐主题，用户可在确认时修改。

## 采集流程

### 流程概要

1. **识别输入类型**：URL → OpenCLI 路由，PDF → Read，视频 → 视频/音频流，文本 → 直接使用
2. **平台检测**：根据 URL 域名确定 raw/ 子目录和 OpenCLI 命令
3. **获取内容**：通过 OpenCLI 或 WebFetch 抓取正文，提取关键要点（3-5 条）
4. **主题分类**：根据关键词映射确定目标主题目录
5. **预览确认**：展示平台、主题、标题、来源、要点、标签，等待用户确认。**必须同时展示 raw 层和 wiki 层两步路径**：
   - raw 层：`raw/{子目录}/文件名`（原始内容存放位置）
   - wiki 层：`wiki/{theme}/文件名`（编译归纳目标位置）
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

当采集来源为视频（YouTube/B站/播客等）或音频时，使用以下专用流程。

### 处理管线

```
URL 输入：
  1. OpenCLI 获取元信息（video/episode）
  2. OpenCLI 获取字幕（subtitle/transcript）
  3. 有字幕？→ YES → 写入 raw/ → 编译 wiki/
               → NO → OpenCLI download → A2S ASR 转录 → 写入 raw/ → 编译 wiki/

本地音视频文件：
  A2S ASR 转录 → 写入 raw/ → 编译 wiki/
```

### 平台能力矩阵

| 平台 | 字幕/Transcript | 元信息 | 下载 | 策略 |
|------|-----------------|--------|------|------|
| YouTube | `transcript`（带时间戳） | `video` | `download`（需 yt-dlp） | 字幕优先，无字幕→下载+ASR |
| B站 | `subtitle`（部分有） | `video` | `download`（需 yt-dlp） | 字幕优先，很多无字幕→下载+ASR |
| 小宇宙 | `transcript` | `episode` | `download` | transcript 优先 |
| 通用网页 | `web read` | — | — | 直接提取文字 |

### ASR 回退流程

当视频无字幕时，使用 audio-to-subtitle 进行 ASR 转录：

1. `opencli <site> download <url> -o /tmp/collect-download/` 下载视频
2. `ffmpeg -i /tmp/collect-download/video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/collect-download/audio.wav` 提取音频
3. `python3 {A2S_DIR}/scripts/transcribe.py /tmp/collect-download/audio.wav --engine local -m large-v3-turbo -f md -o /tmp/collect-download/ --yolo` ASR 转录
4. 读取转录结果，继续正常 raw/ → wiki/ 流程
5. 清理临时文件：`rm -rf /tmp/collect-download/`

> **超时设置**：OpenCLI download 命令设置超时 `OPENCLI_BROWSER_COMMAND_TIMEOUT=120000`（120s）

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

## 批量采集模式

### 触发条件

- 用户提供多个 URL（逗号/换行分隔）
- 用户提供 URL 文件（.txt，每行一个 URL）
- 用户说"采集我的书签/收藏"类指令

### 执行策略

| 任务数 | 策略 | 实现方式 |
|--------|------|----------|
| 1-4 | 顺序执行 | 主会话逐个处理 |
| 5-50 | 并行执行 | Sub Agent 并行（3-4 个/组，上限 4 并发） |

**并行要求**：所有 Sub Agent 的 Bash 调用**必须在同一条响应中发起**。

### 状态追踪

批量任务使用工作目录追踪状态：

```
~/Downloads/collect-pipeline/
└── {platform}-{id}/
    ├── meta.json    # 状态 + 时间记录
    └── (临时文件)
```

**meta.json schema**：

```json
{
  "id": "task-identifier",
  "url": "https://...",
  "platform": "youtube",
  "title": "标题",
  "status": "pending|in_progress|completed|failed|skipped",
  "startedAt": "ISO8601",
  "completedAt": "ISO8601",
  "duration": 123.4,
  "error": null
}
```

**断点续传**：扫描 `~/Downloads/collect-pipeline/` 下所有 meta.json，找到 status != completed 的任务，从断点继续。

### 自动停止

- 连续 3 个任务失败 → 暂停整个批量，报告失败项
- 单个任务失败 → 记录错误，继续下一个
- HTTP 429/403 → 立即停止

### 批量报告

```
📊 批量采集完成
✅ 成功: 8 (耗时: 12m30s)    ❌ 失败: 1    ⏭ 跳过: 1

生成文件:
  • $OBSIDIAN_REPO/raw/作者/标题.md
  • $OBSIDIAN_REPO/wiki/标题-归纳.md

失败项:
  • https://... → 原因: OpenCLI download 超时
```

## 采集收藏/书签

利用 OpenCLI 的个人数据命令，批量采集用户的收藏内容：

### 支持的来源

| 指令 | OpenCLI 命令 | 认证要求 |
|------|-------------|----------|
| 采集 Twitter 书签 | `opencli twitter bookmarks --limit 20` | 🔐 需登录 |
| 采集 B站收藏夹 | `opencli bilibili favorite --limit 20` | 🔐 需登录 |
| 采集 YouTube 稍后观看 | `opencli youtube watch-later --limit 20` | 🔐 需登录 |
| 采集 YouTube 订阅流 | `opencli youtube feed --limit 20` | 🔐 需登录 |
| 采集微信读书划线 | `opencli weread highlights --limit 20` | 🔐 需登录 |

### 执行流程

1. 调用对应 OpenCLI 命令获取列表（`-f json`）
2. 从返回数据中提取 URL/ID 列表
3. 进入批量采集模式处理

## 掘金小册采集模式

当采集来源为掘金小册 URL（`juejin.cn/book/xxx`）时，使用专用提取脚本。

### 触发条件

- URL 匹配 `juejin.cn/book/{booklet_id}`
- 或用户说"采集掘金小册"、"提取掘金小册"

### 提取流程

1. **解析 URL**：提取 `booklet_id`（19 位数字）
2. **获取元数据**：调用掘金 API 获取小册标题、作者、章节列表
3. **批量提取**：逐章获取内容（Markdown/HTML），下载所有图片
4. **保存到 raw/juejin/**：
   ```
   raw/juejin/{booklet-slug}/
   ├── README.md          # 小册索引（标题、作者、目录）
   ├── 01-章节标题.md      # 每章一篇，带 frontmatter
   ├── 02-章节标题.md
   ├── ...
   └── images/
       ├── cover.png       # 封面图
       ├── 01-1.png        # 章节图片
       └── ...
   ```
5. **图片处理**：Markdown 中的图片 URL 替换为本地相对路径 `./images/xx`

### 脚本位置

```bash
# 提取脚本（ob-collect 内置）
node scripts/extract-juejin-booklet.mjs <booklet_url_or_id> \
  --output-dir "$OBSIDIAN_REPO/raw/juejin/{slug}" \
  --download-images
```

### 章节文件格式

```markdown
---
title: "章节标题"
booklet: "小册标题"
section_id: "7304230207517360169"
section_index: 2
date: "2026-04-28"
tags: ["掘金小册", "小册标题"]
---

章节内容（HTML 或 Markdown）
```

### HTML→Markdown 自动转换

脚本内置 HTML→Markdown 转换（基于 turndown 库），自动处理：

- **API 返回的 HTML**：免费小册 API 返回的内容可能是 HTML 格式
- **web-access 浏览器提取**：使用 web-access 从 DOM 提取的 innerHTML 会自动转为 Markdown
- **转换规则**：去掉 `<style>` 标签、data-v-* 属性、掘金特有 class；保留代码块语言标记
- **无需手动二次处理**：脚本输出即为干净的 Markdown

### 图片下载优化

v2 版本图片下载性能优化：

| 参数 | 值 | 说明 |
|------|-----|------|
| 并发数 | 20 | 高并发批量下载 |
| 超时 | 5s | 快速跳过失败图片 |
| 连接复用 | keepAlive | 减少 TCP 握手 |
| 去重 | URL hash | 相同 URL 只下载一次 |
| 跳过 | 已存在 | 断点续传友好 |

### web-access 模式

当 API 方式无法获取内容（如付费小册）时，可使用 web-access 通过浏览器 DOM 提取：

1. 启动 Chrome 调试模式 + cdp-proxy
2. 使用 web-access 导航到小册页面
3. 从 DOM 提取 innerHTML（得到的是 HTML）
4. 运行提取脚本 `--download-images` 自动完成 HTML→Markdown 转换 + 图片下载

### 注意事项

- **免费小册**：无需登录，直接 API 提取
- **付费小册**：需要通过 web-access 浏览器模式提取（API 方式返回空内容）
- **请求间隔**：脚本内置 300ms 延迟，避免频率限制
- **图片格式**：掘金 CDN 图片可能无标准扩展名，自动检测并保持原始格式
- **内容格式**：自动检测 HTML/Markdown，HTML 自动转换为 Markdown
- **版权**：仅下载用户已购买或免费的小册内容

## 写入后验证

遵循 [frontmatter-schema](references/frontmatter-schema.md) 中的验证清单：
1. **Frontmatter**：确认 tags（非空）、type（预定义值）、updated_at 存在
2. **Wikilink**：扫描所有 `[[xxx]]` 引用，确认目标文件存在于 vault 中
3. **索引**：确认文章已出现在对应 `wiki/{theme}/index.md` 中
4. **交叉引用**：在同目录已有文章中查找 tags 重叠的文章，添加反向链接

### 更新项目 CLAUDE.md 索引段

编译完成后，如果当前在 git 项目中，自动更新项目 CLAUDE.md 中的 Obsidian 索引段。流程参考 [ob-project-log/references/claude-index-format.md](../ob-project-log/references/claude-index-format.md) 中的"共享更新流程"。

**注意**：ob-collect 写入的内容通常在主题目录（wiki/{theme}/），不一定有项目级索引。此时更新会静默跳过，不影响主流程。如果用户已为当前项目建立了 Obsidian 项目索引（wiki/projects/{project}/），则同步更新 CLAUDE.md。

## 异常处理

| 场景 | 处理 |
|------|------|
| OpenCLI 命令失败 | 文章类回退 WebFetch，视频类报告失败原因 |
| 视频无字幕 | OpenCLI download → A2S ASR 转录 |
| A2S 转录失败 | 提示用户提供文字稿 |
| URL 抓取失败 | 提示用户检查 URL 或手动粘贴内容 |
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突 | 在文章中标注矛盾，追加说明 |
| 主题无法自动匹配 | 自动创建新主题目录（kebab-case 英文命名） |
| 批量连续失败（≥3 次） | 自动暂停，报告失败项 |
| HTTP 429/403 | 立即停止，提示等待后重试 |
