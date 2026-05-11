---
name: ob-collect
description: "Obsidian 万物采集器。委托 web-search 路由层获取内容（100+ 站点 + Layer 1-4 全栈），采集到 raw/ 并编译为结构化 wiki 笔记。支持批量并行、断点续传。触发词：采集、导入知识库、ob-collect、视频转笔记、采集书签、批量采集。"
---

<role>Obsidian 万物采集器。委托 web-search 拿内容，自身专注于编译为结构化 wiki 笔记（raw/ 归档 + 主题分类 + 索引维护 + 批量并行 + 断点续传）。</role>
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
  <gsd:phase>委托 web-search 获取内容 → 主题分类 → 预览确认 → 写入 raw/ → 编译到 wiki/{theme}/。</gsd:phase>
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

## 获取内容（硬委托 web-search）

> **【硬约束】所有「如何拿到内容」的决策由 [web-search](../../dev-tools/web-search/SKILL.md) skill 负责。本 skill 不维护路由表。**

### 调用流程

收到 URL / 主题 / 文件后：

1. **本地 PDF / 纯文本 / AI 调研产出** → 跳过 web-search，直接用 Read / 内容本身
2. **掘金小册 URL（`juejin.cn/book/*`）** → 跳过 web-search，使用本 skill 的[掘金小册采集模式](#掘金小册采集模式)
3. **其他 URL** → 委托 web-search：
   - web-search Layer 1（OpenCLI 路由 / External CLI 桥接 / 本机扩展 CLI）拿内容
   - Layer 1 未命中 → web-search 自动走 Layer 3（opencli web read / web_reader / WebFetch）
   - 登录或反爬失败 → web-search 自动走 Layer 4（opencli browser / web-access CDP）
4. **无 URL（如「采集 RLHF 这个话题」）** → 先调 web-search Layer 2（WebSearch → Tavily → DDG）拿候选列表，用户选定后回到步骤 3
5. **视频/音频专用**：URL 命中 YouTube/B站/小宇宙/播客等时，仍由 web-search 调 OpenCLI subtitle/transcript；**无字幕时**回到本 skill 的 [ASR 回退流程](#asr-回退流程)

**为什么硬委托**：路由表是单一真理来源。两份路由会必然分裂，LLM 选错的成本远高于多一次 skill 跳转。

### 平台 → raw 子目录映射（采集独有）

web-search 负责"怎么拿"，ob-collect 负责"放哪儿"。raw/ 归档目录按平台类别映射：

| 平台类别 | raw 子目录 | 域名示例 |
|---------|-----------|---------|
| 视频 / 播客 | `raw/{作者名}/` | youtube / bilibili / xiaoyuzhou |
| 微信公众号 | `raw/wechat/` | mp.weixin.qq.com |
| 资讯聚合 | `raw/news/` | hackernews / reddit / 36kr |
| 通用网页 | `raw/web/` | medium / substack / zhihu / douban |
| 掘金小册 | `raw/juejin/` | juejin.cn/book |
| 本地 PDF | `raw/web/` | — |
| 人工输入 | `raw/notes/` | — |
| AI 调研 | `raw/ai-notes/` | — |

> `{A2S_DIR}` 为 audio-to-subtitle skill 所在目录：`/Users/jiashengwang/jacky-github/jacky-skills/plugins/video-processing/skills/audio-to-subtitle`（ASR 回退流程会用到）

## 可扩展模式与约束（核心范式）

> 与 web-search 同范式：**能力按需累加 + 经验沉淀 + 约束在范式之内**。
> - web-search 沉淀「怎么找到内容」（站点路由 / 工具降级链 / 本机扩展 CLI）
> - ob-collect 沉淀「哪些内容值得保留 + 怎么归档」（raw 子目录 / 主题分类 / 提取约束）

### 可扩展点（按需添加，不要预先列满）

| 扩展点 | 怎么扩展 | 落地位置 |
|--------|---------|---------|
| 新增 raw 子目录类型 | 在上方「平台 → raw 子目录映射」表追加一行 + 约定该类型 frontmatter | 本 SKILL.md + [references/frontmatter-schema.md](references/frontmatter-schema.md) |
| 新增主题分类 | 在下方「主题关键词映射」表追加（kebab-case 英文目录 + 关键词）| 本 SKILL.md |
| 新增内容类型的提取规则 | 例如「行业研报」「论文」要哪些字段、wiki 模板长什么样 | [references/compile-templates.md](references/compile-templates.md) |
| 新增视频平台字幕来源 | 由 web-search Layer 1 路由表负责，本 skill 不维护 | web-search SKILL.md 第 2.2 节 |

### 必须遵守的范式（硬约束，不可扩展）

> 这些是采集质量的底线，**新增扩展点不能破坏这些约束**。

1. **视频类只存字幕，不存视频本身**
   - 优先 OpenCLI `subtitle`/`transcript`（web-search Layer 1 自动调用）
   - 字幕缺失 → 调用 audio-to-subtitle skill 做 ASR（用本地音视频大模型转字幕）
   - ASR 完成后**立即删除**临时视频/音频文件（详见 ASR 回退流程）
   - 例外：用户**显式**要求保留视频时才下载，且事前确认
2. **raw 层一次写入不可修改**（要改进 → 在 wiki 层追加引用，不动 raw）
3. **每篇 wiki 文章必须有 article_id**（`OBA-{8 位 lowercase}` 格式）
4. **新主题目录用 kebab-case 英文命名**（如 `wiki/llm-evals/`，不用中文目录名）
5. **frontmatter 必须三件套**：`tags`（非空）/ `type`（预定义值）/ `updated_at`（YYYY-MM-DD）
6. **不为一次性需求扩展**：模式 ≥ 3 次重复才固化为新子目录 / 新主题；否则归入 `raw/notes/` 或现有目录

### 沉淀机制 & 职能边界

经验沉淀写入 `${OBSIDIAN_REPO}/.kb/collect-experience.md`（含模板 / 写入规则 / 固化回流），与 web-search 的职能边界划分，详见 **[references/extension-protocol.md](references/extension-protocol.md)**。

一句话总结：
- **web-search 管「怎么拿」**（URL 路由 + 本机 CLI + 通用搜索降级）
- **ob-collect 管「放哪 + 留什么」**（raw 子目录 + 主题分类 + 视频字幕范式 + frontmatter）

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

1. **识别输入类型**：URL → 委托 web-search，PDF → Read，视频 → 委托 web-search（含 ASR 兜底），文本 → 直接使用
2. **平台检测**：根据 URL 域名确定 raw/ 子目录（命令路由由 web-search 决定）
3. **获取内容**：web-search 返回正文后，提取关键要点（3-5 条）
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

### 模板与归纳规则

完整模板细节见 **[references/video-collect.md](references/video-collect.md)**：

- **raw 模板**：按作者归档（`raw/[作者名]/标题.md`）+ 时间轴分段（`### M:SS 标题`）+ frontmatter
- **wiki 归纳模板**：核心观点 + raw 引用（含时间范围 `#1:30 ~ #3:45`）+ 关键金句 + 我的思考
- **归纳生成 8 条规则**：观点拆解 / raw 引用 / 不搬运原文 / 不做延伸 等
- **作者索引模板**：`raw/index.md` 按作者分组的自动索引

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

### 状态追踪 + 断点续传

批量任务在 `~/Downloads/collect-pipeline/{platform}-{id}/meta.json` 记录状态（pending/in_progress/completed/failed/skipped）+ 时间。下次启动时扫描所有 meta.json，从 `status != completed` 的位置继续。

meta.json schema、字段说明、报告模板见 **[references/batch-collect.md](references/batch-collect.md)**。

### 自动停止

- 连续 3 个任务失败 → 暂停整个批量，报告失败项
- 单个任务失败 → 记录错误，继续下一个
- HTTP 429/403 → 立即停止

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

URL 匹配 `juejin.cn/book/{booklet_id}` 时走专用脚本（不经 web-search）：

```bash
node scripts/extract-juejin-booklet.mjs <booklet_url_or_id> \
  --output-dir "$OBSIDIAN_REPO/raw/juejin/{slug}" \
  --download-images
```

完整流程（API 解析 / HTML→Markdown 转换 / 图片并发下载 / 付费小册的 web-access 兜底 / 注意事项）见 **[references/juejin-booklet.md](references/juejin-booklet.md)**。

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
| 视频无字幕 | OpenCLI download → A2S ASR 转录（见 ASR 回退流程） |
| A2S 转录失败 | 提示用户提供文字稿 |
| web-search 全部 Layer 失败 | 提示用户检查 URL 或手动粘贴内容（路由失败由 web-search 内部处理）|
| 内容为空或过短 | 提示用户确认是否继续 |
| 概念文章已存在 | 读取并更新，不创建重复 |
| 概念冲突 | 在文章中标注矛盾，追加说明 |
| 主题无法自动匹配 | 自动创建新主题目录（kebab-case 英文命名） |
| 批量连续失败（≥3 次） | 自动暂停，报告失败项 |
| HTTP 429/403 | 立即停止，提示等待后重试 |
