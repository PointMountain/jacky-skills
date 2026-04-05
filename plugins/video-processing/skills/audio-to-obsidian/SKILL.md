---
name: audio-to-obsidian
description: "渐进式音视频处理编排器：URL/本地视频/本地音频/URL文件 → 提取字幕 → 同步到 Obsidian。支持 yt-dlp 1000+ 平台，meta.json 断点续传。触发词：视频转笔记、提取字幕到obsidian、audio-to-obsidian。"
---

<role>
你是音视频内容处理编排器，协调 extract-url-media、audio-to-subtitle、write-obsidian-note 三个原子 skill 完成端到端流程。
</role>

<purpose>
给定一个输入（URL / 本地视频 / 本地音频 / URL 文件），自动走完处理管线，每步检测已有产物跳过已完成步骤，最终产出 Obsidian 原文笔记 + 归纳笔记。
</purpose>

<trigger>
```text
触发词/示例：
- 把这个视频转成 Obsidian 笔记
- 提取这个链接的音频转文字
- 处理这个本地视频文件到 Obsidian
- 把这段音频转录整理到笔记
- 批量处理这些视频链接
- 处理这个 URL 文件中的所有链接
- audio-to-obsidian
```
</trigger>

<yolo:config>
  <yolo:mode>auto-advance</yolo:mode>
  <yolo:safety-gates>
    <gate>豆包云端引擎调用（按量计费）</gate>
    <gate>覆盖已存在的 Obsidian 笔记</gate>
    <gate>批量 ≥10 时的处理计划确认</gate>
  </yolo:safety-gates>
</yolo:config>

<gsd:workflow>
  <gsd:meta>
    <name>audio-to-obsidian</name>
    <owner>video-processing</owner>
    <requires>extract-url-media, audio-to-subtitle, write-obsidian-note, OBSIDIAN_REPO</requires>
    <deps>
      <dep name="extract-url-media" source="local" localPath="../extract-url-media/" />
      <dep name="audio-to-subtitle" source="local" localPath="../audio-to-subtitle/" />
      <dep name="write-obsidian-note" source="local" localPath="../write-obsidian-note/" />
    </deps>
    <checkpoints>
      <checkpoint order="1">环境依赖就绪</checkpoint>
      <checkpoint order="2">输入识别完成，任务列表已构建</checkpoint>
      <checkpoint order="3">所有任务处理完成，笔记已写入 Obsidian</gsd:checkpoint>
    </checkpoints>
    <constraints>
      <constraint>本 skill 为纯编排器，不直接调用 yt-dlp 或 ffmpeg</constraint>
      <constraint>四种输入类型：URL / 本地视频 / 本地音频 / URL 文件，自动检测</constraint>
      <constraint>每步执行前做 meta.json + 文件存在性双重校验</constraint>
      <constraint>字幕获取优先级：内嵌字幕（extract-url-media）→ ASR（audio-to-subtitle）</constraint>
      <constraint>批量模式首次确认引擎后复用</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
      <constraint>批量间隔 ≥3 秒，单批上限 50，连续运行 ≤1 小时</constraint>
      <constraint>HTTP 429/403、验证码、连续 3 次失败自动停止</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>输入 → 协调三个原子 skill → Obsidian 原文 + 归纳笔记。</gsd:goal>

  <gsd:phase name="precheck" order="1">
    <gsd:step>检查 OBSIDIAN_REPO、extract-url-media、audio-to-subtitle、write-obsidian-note 四个依赖。</gsd:step>
    <gsd:step>任一缺失 → AskUserQuestion 告知安装命令。</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="collect" order="2">
    <gsd:step>识别输入类型：① URL ② 本地视频 ③ 本地音频 ④ URL 文件（.txt）。</gsd:step>
    <gsd:step>检测平台并选择策略：YouTube → yt-dlp 原生 / B站UP主 → 浏览器方案 / TikTok → curl_cffi / 抖音/小红书 → 仅单视频。</gsd:step>
    <gsd:step>URL 批量时：YouTube 频道可按播放量本地排序取 Top N；≥10 时 HARD_GATE 确认。</gsd:step>
    <gsd:step>URL 文件：逐行读取，去除空行和注释（# 开头），每个 URL 独立处理。</gsd:step>
    <gsd:step>为每个任务创建工作目录 + meta.json。</gsd:step>
    <gsd:checkpoint>输入收集完毕，任务列表已构建</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="process" order="3">
    <gsd:step>对每个任务按输入类型走对应管线（跳过已完成步骤）：</gsd:step>
    <gsd:step>URL 管线：extract-url-media → audio-to-subtitle（无内嵌字幕时）→ write-obsidian-note</gsd:step>
    <gsd:step>本地管线：audio-to-subtitle → write-obsidian-note</gsd:step>
    <gsd:step>单个失败 → 记录错误，继续下一个（批量时）。</gsd:step>
    <gsd:checkpoint>所有笔记已写入 Obsidian</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="deliver" order="4">
    <gsd:step>输出报告：✅成功 / ❌失败 / ⏭跳过。</gsd:step>
    <gsd:step>列出所有生成文件路径。</gsd:step>
    <gsd:step>失败项列出原因和重试建议。</gsd:step>
    <gsd:step>批量未完成 → 输出 Resume Signal。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Audio to Obsidian — 渐进式音视频处理编排器

> 🚀 **YOLO 模式** — 自动推进，安全门仍会暂停。
> 🧩 **纯编排器** — 业务逻辑委托给 extract-url-media / audio-to-subtitle / write-obsidian-note。

## 架构

```
audio-to-obsidian（编排器，Layer 2）
│
├── extract-url-media      ← Layer 1: URL → 元信息 + 音频 + 内嵌字幕
├── audio-to-subtitle      ← Layer 0: 音频/视频 → ASR 转录文字
└── write-obsidian-note    ← Layer 1: 元信息 + 文案 → Obsidian 笔记
```

## 处理管线

```
URL 输入:
  extract-url-media ──→ (无内嵌字幕?) ──→ audio-to-subtitle ──→ write-obsidian-note
  [元信息+音频+字幕]                       [ASR 转录]              [笔记写入]

本地视频/音频:
  audio-to-subtitle ──→ write-obsidian-note
  [ASR 转录]              [笔记写入]
```

## 四种输入场景

| 输入类型 | 示例 | 管线路径 |
|----------|------|---------|
| 在线 URL | `youtube.com/watch?v=xxx` | extract-url-media → subtitle → obsidian |
| URL 文件 | `/path/to/urls.txt` | 逐行读取，按 URL 处理 |
| 本地视频 | `/path/to/video.mp4` | audio-to-subtitle → obsidian |
| 本地音频 | `/path/to/audio.mp3` | audio-to-subtitle → obsidian |

## 工作目录

```
~/Downloads/video-pipeline/
└── {platform}/{video-id}/
    ├── meta.json           # 元数据 + 状态跟踪
    ├── audio.wav           # extract-url-media 产物
    └── subtitle.srt        # 内嵌字幕或 ASR 产物
```

## meta.json 状态跟踪

```json
{
  "id": "dQw4w9WgXcQ",
  "platform": "youtube",
  "url": "https://...",
  "title": "标题",
  "author": "作者",
  "stages": {
    "media":    { "status": "done|skipped|pending|failed" },
    "subtitle": { "status": "done|pending|failed", "source": "embedded|asr-mlx-whisper|asr-doubao" },
    "obsidian": { "status": "done|pending|failed" }
  }
}
```

**双重校验**：meta.json + 文件存在性互为备份，任一缺失则重新执行。

## 执行流程

### Phase 1: 环境检查

检查三个依赖 skill 均可用 + OBSIDIAN_REPO 配置。

### Phase 2: 输入收集

```
URL → 检测平台 → 进入 URL 管线
本地视频 → file --mime-type → 进入本地管线
本地音频 → file --mime-type → 进入本地管线
URL 文件 → 逐行读取 → 每行按 URL 处理
```

批量 URL ≥10 → 🛑 HARD_GATE 展示列表确认。

#### B站 UP主空间批量获取

当 URL 为 B站 UP主空间页时，委托 `extract-url-media` 使用 agent-browser 浏览器方案提取视频列表（无需登录、无 WBI 签名、低风控风险）。流程：

```
1. agent-browser 打开 UP主空间页
2. DOM 提取 BV 号 + 标题（每页 40 个）
3. 翻页直到结束（间隔 2-3 秒）
4. 导出视频列表 JSON → 逐个进入管线
```

> 详见 `references/bilibili-uploader-video-list-browser-approach.md`

#### URL 文件格式

```text
# 支持 # 开头的注释行和空行
https://www.youtube.com/watch?v=xxx
https://www.bilibili.com/video/BV1xxx

# 这是注释，会被忽略
https://v.douyin.com/xxx
```

#### 多平台能力矩阵

| 平台 | 批量获取 | 内嵌/自动字幕 | 注意事项 |
|------|---------|---------------|---------|
| YouTube | ✅ yt-dlp 原生 | ✅ 手动 + 自动生成 | **最佳支持**，全功能 |
| B站 | ⚠️ UP主需浏览器 | ✅ CC 字幕 | yt-dlp 划列表不稳定 |
| TikTok | ⚠️ 需 curl_cffi | ✅ 自动字幕 | 必须安装 curl_cffi |
| 抖音 | ❌ 不支持创作者页 | ❌ | 仅单视频，需 Cookie，限中文口播 |
| 小红书 | ❌ 不支持博主页 | ❌ | 仅视频笔记 | 图文笔记不支持 |
| Twitter/X | ❌ | ❌ | 需 Cookie |

> 不支持批量获取的平台，用户仍可提供单个视频 URL 进行处理。

#### YouTube 批量排序

YouTube 频道批量处理时，可先按播放量排序取 Top N：

```bash
# 获取频道视频列表 + 播放量
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(view_count)s" \
  "https://www.youtube.com/@ChannelName/videos"

# 本地排序取 Top 20
python3 -c "
import json, sys
videos = [json.loads(l) for l in sys.stdin if l.strip()]
videos.sort(key=lambda x: x.get('view_count', 0) or 0, reverse=True)
for v in videos[:20]:
    print(f'{v[\"view_count\"]:>10}  {v[\"id\"]}  {v[\"title\"][:60]}')
"
```

#### 跨平台采集策略

同一创作者多平台同步发布时，按平台稳定性选择最优源：

```
平台优先级：YouTube ≈ B站 > 小红书 >>> TikTok/抖音
```

| 策略 | 说明 |
|------|------|
| **优先 B站/YouTube** | 稳定性高，Extractor 成熟，支持批量 |
| **小红书作补充** | 大部分时候能用，接受偶尔失败 |
| **TikTok 谨慎依赖** | 仅用于偶尔的单视频下载 |
| **去重** | 通过标题相似度匹配，避免同一内容多平台重复处理 |
| **降级** | 主平台失败 → 尝试其他平台获取同一内容 |

**采集模式适配**：

| 模式 | YouTube | B站 | 小红书 | TikTok |
|------|---------|------|--------|--------|
| 单视频 | ✅ | ✅ | ✅ | ⚠️ |
| 仅提取字幕 | ✅ | ✅（需Cookie）| ❌ | ❌ |
| 批量用户空间 | ✅ | ✅（浏览器）| ❌ | ❌ |
| 自动化定时 | ✅（Cookie+PO Token）| ⚠️（Cookie）| ❌ | ❌ |

### Phase 3: 任务处理

#### URL 管线（3 步）

**Step 1: 提取媒体** — 委托 `extract-url-media`
- 获取元信息（标题、作者、时长等）
- 提取音频文件（WAV 格式）
- 尝试获取内嵌字幕
- 返回：`{ metadata, audioPath, subtitlePath?, subtitleSource? }`

**Step 2: 转录文字** — 条件执行
- extract-url-media 已获取内嵌字幕 → 跳过
- 无内嵌字幕 → 委托 `audio-to-subtitle` 进行 ASR 转录

**Step 3: 写入 Obsidian** — 委托 `write-obsidian-note`
- 输入：元信息 + 转录文本
- 输出：原文.md + 归纳.md
- 🛑 目标文件已存在 → 询问覆盖或跳过

#### 本地文件管线（2 步）

本地视频和音频直接从转录步骤开始（audio-to-subtitle 支持视频输入，无需预先提取音频）：

**Step 1: 转录文字** — 委托 `audio-to-subtitle`

**Step 2: 写入 Obsidian** — 委托 `write-obsidian-note`

### Phase 4: 输出报告

```
📊 处理完成
✅ 成功: 8    ❌ 失败: 1    ⏭ 跳过: 1

生成文件:
  • $OBSIDIAN_REPO/00-Inbox/Audio/作者/标题-原文.md
  • $OBSIDIAN_REPO/00-Inbox/Audio/作者/标题-归纳.md
```

## Resume 协议

meta.json 天然支持断点续传：

1. 新会话触发本 skill
2. 扫描 `~/Downloads/video-pipeline/` 下所有 meta.json
3. 找到存在 `pending`/`failed` 的目录
4. 从最早未完成步骤继续

### Next Up 契约

```
---
## ▶ Next Up

**Phase 3: process** — 还有 17/25 个任务待处理

回复 "继续" 或在新会话中触发 `audio-to-obsidian`
---
```

## 技术防护

| 参数 | 限制 |
|------|------|
| 单次间隔 | ≥ 3 秒 |
| 批量上限 | ≤ 50 个 |
| 连续运行 | ≤ 1 小时 |
| IP 限流 | 停止，等 30 分钟 |
| 磁盘预检 | ≥ 500MB 剩余 |

自动停止条件：HTTP 429/403、验证码、连续 3 次失败。

### 豆包费用估算

使用豆包引擎前，自动估算费用并展示给用户确认：

| 音频时长 | 预估费用 | 说明 |
|---------|---------|------|
| 5 分钟 | ~¥0.05 | 按量计费 |
| 30 分钟 | ~¥0.30 | 标准费率 |
| 60 分钟 | ~¥0.60 | 建议分段处理 |
| 120 分钟 | ~¥1.20 | 需拆分为 ≤30min 段 |

> 费用 = 音频时长（分钟）× ¥0.01/分钟（参考价）。实际以火山引擎账单为准。
> 每次调用豆包引擎前展示预估费用，等待用户确认。

### 批量重试策略

```
任务失败 → 等待 1s → 重试
第 2 次失败 → 等待 2s → 重试
第 3 次失败 → 标记为 failed，继续下一个任务
连续 3 个任务失败 → 暂停整个批量，等待用户决策
```

### Dry Run 模式

批量 ≥10 时，先执行 Dry Run 展示处理计划，不实际下载：

```
📊 Dry Run 预览
  共 25 个任务，预计下载 ~125MB 音频
  预估豆包费用: ~¥7.50（如使用豆包引擎）
  预计耗时: ~15 分钟

  确认执行？ [Y/n]
```

> 用户确认后才实际执行，避免意外资源消耗。

## 免责声明

> [!warning] ⚠️ 法律风险提示
> **本 Skill 仅用于个人学习和研究目的。** 因不当使用造成的法律后果由使用者自行承担。
> 详见 `references/video-download-guidelines.md`

### 允许 ✅ / 禁止 ❌

| ✅ 允许 | ❌ 禁止 |
|---------|---------|
| 个人离线学习 | 上传到其他平台分发 |
| 下载自己上传的内容 | 批量商业盈利 |
| CC 授权 / 无版权内容 | 绕过付费墙并分享 |
| 语言学习字幕提取 | 侵犯知识产权 |

## 用户交互点

| 阶段 | 标记 | 触发条件 | YOLO 行为 |
|------|------|---------|-----------|
| Phase 1 | ✅ | 环境检查 | 自动通过 |
| Phase 2 | 🛑 | 批量 ≥10 | 展示计划确认 |
| Phase 3 ASR | 📝 | 转录引擎选择 | 完整交互 |
| Phase 3 豆包 | 🛑 | 付费引擎 | 必须确认 |
| Phase 3 写入 | 🛑 | 笔记已存在 | 覆盖或跳过 |
| Phase 4 | ✅ | 输出报告 | 自动展示 |

🛑 安全门 | 📝 用户输入 | ✅ 自动执行
