# Audio-to-Obsidian 原子化拆分方案

> 本文档分析 `audio-to-obsidian` skill 的职责边界，提出 3 层原子化拆分方案，使各 skill 可独立复用、测试和扩展。

## 一、现状分析

### 当前架构

`audio-to-obsidian` 目前承担了以下全部职责：

```
URL 收集 → 元信息获取 → 音频提取 → 转录文字 → 笔记生成 → 写入 Obsidian → 批量管理 → 进度恢复
```

这是一个**单体 skill**，混合了业务逻辑（笔记模板、目录规则）和流程控制（批量、Resume、安全门）。

### 存在的问题

| 问题 | 具体表现 |
|------|---------|
| **复用性差** | `bilibili-to-obsidian` 也需要"URL → 元信息 + 音频"，但只能自己重新实现 |
| **模板散落** | Obsidian 笔记格式分散在 `bilibili-to-obsidian` 和 `audio-to-obsidian` 两处，格式不统一 |
| **难以单独测试** | 只能端到端跑，无法单独验证"笔记生成"或"音频提取"是否正确 |
| **扩展成本高** | 想支持新平台或新笔记模板，需要改动整个 skill |

## 二、拆分方案：3 层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 2 — 编排层 (Orchestrator)                      │
│                                                      │
│  audio-to-obsidian                                   │
│  职责：URL 收集 / 批量调度 / Resume / 安全门            │
│                                                      │
├──────────────────────────────────────────────────────┤
│  Layer 1 — 组合 Skill 层                              │
│                                                      │
│  ┌───────────────────┐    ┌────────────────────────┐  │
│  │ extract-url-media │    │ write-obsidian-note    │  │
│  │                   │    │                        │  │
│  │ URL → 元信息+音频  │    │ 元信息+文案 → Obsidian  │  │
│  └────────┬──────────┘    └───────────▲────────────┘  │
│           │                           │               │
├───────────┼───────────────────────────┼───────────────┤
│  Layer 0 — 原子工具层（已有）            │               │
│           │                           │               │
│  ┌────────▼──────────┐    ┌──────────┴────────────┐   │
│  │ yt-dlp scripts    │    │ audio-to-subtitle     │   │
│  │                   │    │                       │   │
│  │ 下载 / 提取音频    │    │ 音频 → 文字转录        │   │
│  └───────────────────┘    └───────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### Layer 0 — 原子工具层（已有，无需改动）

| Skill | 输入 | 输出 | 状态 |
|-------|------|------|------|
| `yt-dlp scripts` | URL + 下载参数 | 音频/视频文件 | 已存在，作为 deps 引用 |
| `audio-to-subtitle` | 音频文件路径 | 转录文本（SRT/TXT/MD） | 已存在，支持 MLX-Whisper + 豆包双引擎 |

### Layer 1 — 组合 Skill 层（建议新建）

#### 1. `extract-url-media` — URL 媒体提取

| 项目 | 说明 |
|------|------|
| **输入** | URL（支持 yt-dlp 支持的所有平台） |
| **输出** | `{ author, title, id, duration, audioPath, sourceUrl }` |
| **职责** | 封装 yt-dlp 的元信息获取 + 音频提取，返回结构化数据 |
| **复用场景** | `audio-to-obsidian`、`bilibili-to-obsidian`、任何需要从 URL 获取音频的场景 |

核心逻辑：

```bash
# 步骤 1：获取元信息
yt-dlp --print "%(uploader)s|%(title)s|%(id)s|%(duration_string)s" "<URL>"

# 步骤 2：提取音频（只下载音频流，不下载视频）
yt-dlp -x --audio-format wav -o "/tmp/extract-url-media/%(id)s.%(ext)s" "<URL>"
```

返回结构：

```json
{
  "author": "作者名",
  "title": "视频标题",
  "id": "视频ID",
  "duration": "10:30",
  "audioPath": "/tmp/extract-url-media/BV1xxx.wav",
  "sourceUrl": "https://..."
}
```

#### 2. `write-obsidian-note` — Obsidian 笔记写入

| 项目 | 说明 |
|------|------|
| **输入** | `{ metadata, transcript, category, authorPath }` |
| **输出** | `{ originalPath, summaryPath }` |
| **职责** | 生成原文 + 归纳两种笔记，按统一模板写入 Obsidian 指定目录 |
| **复用场景** | `audio-to-obsidian`、`bilibili-to-obsidian`、播客笔记、本地录音整理… |

核心逻辑：

```
输入: metadata + transcript + category
  ├── 生成 [标题]-原文.md（带 frontmatter + 时间戳内容）
  ├── 生成 [标题]-归纳.md（核心要点 + 关键引用 + 思考）
  └── 写入 $OBSIDIAN_REPO/00-Inbox/[category]/[作者]/
```

统一笔记模板：

**原文笔记**：

```markdown
# [标题]

> **作者**: [作者名]
> **来源**: [URL]
> **提取时间**: [日期]
> **时长**: [时长]

## 音频/视频来源

> [!quote] 🔗 [点击播放]([URL])

---

## 完整文案（带时间戳）

[转录内容]

---
#音频笔记 #[作者名]
```

**归纳笔记**：

```markdown
# [标题] - 归纳

> **作者**: [作者名]
> **来源**: [URL]
> **原文**: [[标题-原文]]

## 核心要点

- [AI 自动归纳]

## 关键引用

> 原文引用...

## 我的思考

[待补充]

---
#音频笔记 #[作者名] #归纳
```

### Layer 2 — 编排层（瘦身后的 audio-to-obsidian）

拆分后，`audio-to-obsidian` 变为纯编排器，只负责流程控制：

```
audio-to-obsidian（编排器）
│
├── Phase 1: precheck
│     └── 并行检查：OBSIDIAN_REPO / yt-dlp / audio-to-subtitle
│
├── Phase 2: collect
│     ├── 单个 URL → 直接进入 Phase 3
│     ├── 频道/播放列表 → yt-dlp --flat-playlist 获取列表
│     ├── URL 文件 → 逐行读取
│     └── 批量 ≥10 → 🛑 确认处理计划
│
├── Phase 3: process（循环每个 URL）
│     ├── extract-url-media      ← Layer 1
│     ├── audio-to-subtitle      ← Layer 0
│     └── write-obsidian-note    ← Layer 1
│
└── Phase 4: deliver
      ├── 输出报告（成功/失败/跳过）
      ├── 列出文件路径
      └── 批量未完成 → 写入 Resume 状态
```

## 三、收益对比

| 维度 | 拆分前（单体） | 拆分后（3 层） |
|------|--------------|--------------|
| **复用性** | 笔记模板和音频提取逻辑锁死在 audio-to-obsidian 内 | `extract-url-media` 和 `write-obsidian-note` 可被任意 skill 调用 |
| **可测试性** | 只能端到端跑完整流程 | 每层可独立验证，比如只测试笔记生成逻辑 |
| **模板维护** | bilibili-to-obsidian 和 audio-to-obsidian 各维护一套笔记格式 | `write-obsidian-note` 统一管理，改一处全局生效 |
| **编排器复杂度** | 混合业务逻辑和流程控制，代码膨胀 | 编排器只管流程，薄而清晰 |
| **扩展性** | 加新平台需改整个 skill | 换 `extract-url-media` 的内部实现即可，编排层无感知 |

## 四、对 bilibili-to-obsidian 的影响

拆分后，`bilibili-to-obsidian` 也可以复用 Layer 1 的两个 skill：

```
bilibili-to-obsidian（编排器）
│
├── Phase 1: precheck
│
├── Phase 2: extract
│     ├── extract-url-media      ← 复用 Layer 1
│     └── audio-to-subtitle      ← 复用 Layer 0
│
└── Phase 3: organize
      └── write-obsidian-note    ← 复用 Layer 1（category = "B站"）
```

这样 B 站的笔记模板也由 `write-obsidian-note` 统一生成，格式一致，维护成本降低。

## 五、实施步骤

### Step 1：新建 `extract-url-media`

1. 在 `plugins/video-processing/skills/` 下创建目录和 `SKILL.md`
2. 封装 yt-dlp 元信息获取 + 音频提取逻辑
3. 定义标准输入输出契约（JSON 结构）
4. 测试：YouTube / B站 / 抖音 三个平台验证

### Step 2：新建 `write-obsidian-note`

1. 在 `plugins/video-processing/skills/` 下创建目录和 `SKILL.md`
2. 统一原文 + 归纳笔记模板（合并 bilibili 和 audio 两套格式）
3. 支持 `category` 参数（"B站" / "Audio" / 自定义）
4. 测试：传入模拟数据验证笔记生成

### Step 3：重构 `audio-to-obsidian`

1. 移除内部的 yt-dlp 调用逻辑 → 改为调用 `extract-url-media`
2. 移除内部的笔记生成逻辑 → 改为调用 `write-obsidian-note`
3. 保留编排逻辑（Phase 管理、Resume、安全门）
4. 回归测试：确保端到端流程不变

### Step 4：重构 `bilibili-to-obsidian`

1. 移除内部的 yt-dlp 调用逻辑 → 改为调用 `extract-url-media`
2. 移除内部的笔记生成逻辑 → 改为调用 `write-obsidian-note`
3. 保留 B 站特有逻辑（iframe 嵌入、BV 号解析等）
4. 回归测试：确保 B 站流程不变

## 六、Skill 依赖关系图

```
audio-to-obsidian
  ├── deps: extract-url-media
  ├── deps: audio-to-subtitle
  └── deps: write-obsidian-note

bilibili-to-obsidian
  ├── deps: extract-url-media
  ├── deps: audio-to-subtitle
  └── deps: write-obsidian-note

extract-url-media
  └── deps: yt-dlp scripts

audio-to-subtitle
  └── deps: MLX-Whisper / 豆包 ASR

write-obsidian-note
  └── deps: OBSIDIAN_REPO
```

## 七、风险与注意事项

| 风险 | 应对措施 |
|------|---------|
| 拆分后依赖链变长 | 在 `skill-deps.json` 中声明依赖，安装时自动检查 |
| `write-obsidian-note` 模板需兼容两种来源 | 用 `category` 参数区分，模板内按条件渲染 |
| 临时文件在 skill 间传递 | 统一使用 `/tmp/extract-url-media/` 目录，约定清理责任 |
| `bilibili-to-obsidian` 有 B 站特有的 iframe 嵌入 | `write-obsidian-note` 支持 `extraContent` 参数，传入平台特有内容 |
