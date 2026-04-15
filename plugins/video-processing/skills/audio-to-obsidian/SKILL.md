---
name: audio-to-obsidian
description: "渐进式音视频处理编排器：URL/本地视频/本地音频/URL文件 → 提取字幕 → 同步到 Obsidian。支持断点续传、Sub Agent 并行、UP主订阅管理。触发词：视频转笔记、提取字幕到obsidian、订阅UP主、同步视频、audio-to-obsidian。"
---

<role>
你是音视频内容处理编排器，协调 extract-url-media、audio-to-subtitle 两个原子 skill，以及 ob-collect（Obsidian 笔记写入）完成端到端流程。
</role>

<purpose>
给定一个输入（URL / 本地视频 / 本地音频 / URL 文件），一次性收集所有参数后自动走完处理管线，中途零交互。支持断点续传和 Sub Agent 并行加速。
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
  <yolo:defaults>
    <engine>local</engine>
    <model>large-v3-turbo</model>
    <format>md</format>
    <overwrite>false</overwrite>
    <language>auto</language>
    <category>Audio</category>
    <max-retries>3</max-retries>
    <retry-delay>2.0</retry-delay>
  </yolo:defaults>
  <yolo:safety-gates>
    <gate condition="engine=doubao">云端引擎费用确认（按量计费）</gate>
    <gate condition="batch>=10">大批量任务确认</gate>
  </yolo:safety-gates>
</yolo:config>

<gsd:workflow>
  <gsd:meta>
    <name>audio-to-obsidian</name>
    <owner>video-processing</owner>
    <requires>extract-url-media, audio-to-subtitle, OBSIDIAN_REPO</requires>
    <deps>
      <dep name="extract-url-media" source="local" localPath="../extract-url-media/" />
      <dep name="audio-to-subtitle" source="local" localPath="../audio-to-subtitle/" />
    </deps>
    <checkpoints>
      <checkpoint order="1">环境依赖就绪</checkpoint>
      <checkpoint order="2">所有参数已确认，准备执行</checkpoint>
      <checkpoint order="3">输入识别完成，任务列表已构建</checkpoint>
      <checkpoint order="4">所有任务处理完成，笔记已写入 Obsidian</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>本 skill 为纯编排器，不直接调用 yt-dlp 或 ffmpeg</constraint>
      <constraint>四种输入类型：URL / 本地视频 / 本地音频 / URL 文件，自动检测</constraint>
      <constraint>每步执行前做 meta.json + 文件存在性双重校验</constraint>
      <constraint>字幕获取优先级：内嵌字幕（extract-url-media）→ ASR（audio-to-subtitle）</constraint>
      <constraint>所有用户交互集中在 Phase 2（configure），Phase 4（process）零交互</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
      <constraint>批量间隔 ≥3 秒，单批上限 50，连续运行 ≤1 小时</constraint>
      <constraint>HTTP 429/403、验证码、连续 3 次失败自动停止</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>输入 → 一次性确认参数 → 自动协调三个原子 skill → Obsidian raw 原始字幕 + wiki 归纳笔记（llm-wiki 模式）。</gsd:goal>

  <!-- ==================== Phase 1: 环境检查 ==================== -->
  <gsd:phase name="precheck" order="1">
    <gsd:step>检查 OBSIDIAN_REPO、extract-url-media、audio-to-subtitle 三个依赖。</gsd:step>
    <gsd:step>任一缺失 → AskUserQuestion 告知安装命令。</gsd:step>
    <gsd:step>检查是否有可恢复任务：扫描 pipeline-dir 下 meta.json，发现 status != completed 的任务。</gsd:step>
    <gsd:step>如有可恢复任务，在 Phase 2 中展示恢复选项。</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 2: 参数确认（一次性交互） ==================== -->
  <gsd:phase name="configure" order="2">
    <gsd:step>
      📝 【一次性参数确认 — 使用 AskUserQuestion 收集所有配置】

      必须收集的参数（一次交互完成）：

      1. **引擎选择**（核心决策）：
         - local：MLX-Whisper 本地引擎（免费、快速、隐私保护）
         - doubao：豆包云端 ASR（中文优化、大模型增强，按量计费）
         → 智能默认：local

      2. **条件确认**（仅特定场景触发，合并到同一次交互）：
         - 引擎=doubao → 展示费用估算表
         - 批量 ≥10 → 展示任务数量和预估耗时
         - 目标笔记已存在 → 展示文件列表，确认覆盖/跳过

      不需要问的参数（使用智能默认值）：
      - model：large-v3-turbo（最快且准确率很高）
      - format：md（最适合 Obsidian）
      - language：auto（自动检测）
      - category：Audio
      - max-retries：3
      - retry-delay：2.0

      交互完成后，所有参数固定，后续阶段零交互。
    </gsd:step>
    <gsd:step>确认豆包 API 凭证（仅 engine=doubao 时）：检查 ~/.audio2subtitle/config.json 或环境变量，缺失则引导配置。</gsd:step>
    <gsd:checkpoint>所有参数已确认，准备执行</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 3: 输入收集 ==================== -->
  <gsd:phase name="collect" order="3">
    <gsd:step>识别输入类型：① URL ② 本地视频 ③ 本地音频 ④ URL 文件（.txt）。</gsd:step>
    <gsd:step>检测平台并选择策略：YouTube → yt-dlp 原生 / B站UP主 → 浏览器方案 / TikTok → curl_cffi / 抖音/小红书 → 仅单视频。</gsd:step>
    <gsd:step>URL 文件：逐行读取，去除空行和注释（# 开头），每个 URL 独立处理。</gsd:step>
    <gsd:step>为每个任务创建工作目录 + meta.json（v2 schema，含时间追踪字段）。</gsd:step>
    <gsd:step>根据任务数量选择执行策略（见调度决策表）。</gsd:step>
    <gsd:checkpoint>输入收集完毕，任务列表已构建</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 4: 任务处理（零交互） ==================== -->
  <gsd:phase name="process" order="4">
    <gsd:step>根据调度决策表执行任务（直接或 Sub Agent 并行）。</gsd:step>
    <gsd:step>对每个任务按输入类型走对应管线（跳过已完成步骤）：</gsd:step>
    <gsd:step>URL 管线：extract-url-media → audio-to-subtitle（无内嵌字幕时）→ ob-collect（笔记写入）</gsd:step>
    <gsd:step>本地管线：audio-to-subtitle → ob-collect（笔记写入）</gsd:step>
    <gsd:step>每个阶段自动记录 startedAt/completedAt/duration 到 meta.json。</gsd:step>
    <gsd:step>阶段失败：自动重试（指数退避，最多 3 次），清理部分产物。</gsd:step>
    <gsd:step>单个失败 → 记录错误，继续下一个（批量时）。</gsd:step>
    <gsd:checkpoint>所有笔记已写入 Obsidian</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 5: 输出报告 ==================== -->
  <gsd:phase name="deliver" order="5">
    <gsd:step>输出报告：✅成功 / ❌失败 / ⏭跳过，含每个任务的耗时。</gsd:step>
    <gsd:step>列出所有生成文件路径。</gsd:step>
    <gsd:step>失败项列出原因和重试建议。</gsd:step>
    <gsd:step>批量未完成 → 输出 Resume Signal（--resume 命令）。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Audio to Obsidian — 渐进式音视频处理编排器

> 🚀 **一次确认，全程自动** — 所有交互集中在 Phase 2，Phase 4 零交互。
> 🧩 **纯编排器** — 业务逻辑委托给 extract-url-media / audio-to-subtitle，笔记写入由 ob-collect 统一管理。
> ⚡ **Sub Agent 加速** — 大批量自动并行处理。

## 可执行脚本

```bash
# URL 输入（local 引擎）
python3 scripts/pipeline.py "https://www.youtube.com/watch?v=xxxx" \
  --obsidian-repo "$OBSIDIAN_REPO" --engine local

# 本地媒体输入（doubao 引擎）
python3 scripts/pipeline.py "/path/to/audio.mp3" \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --engine doubao --transcript-format md

# URL 文件批量输入
python3 scripts/pipeline.py "/path/to/urls.txt" \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --engine local --overwrite

# 仅处理前 20 条
python3 scripts/pipeline.py "/path/to/urls.txt" \
  --obsidian-repo "$OBSIDIAN_REPO" --max-items 20

# Dry-run：仅查看计划
python3 scripts/pipeline.py "/path/to/urls.txt" \
  --obsidian-repo "$OBSIDIAN_REPO" --dry-run

# 恢复中断的任务
python3 scripts/pipeline.py --resume \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --video-pipeline-dir ~/Downloads/video-pipeline

# 自定义重试策略
python3 scripts/pipeline.py "/path/to/urls.txt" \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --max-retries 5 --retry-delay 3.0 --stop-on-error
```

## 架构

```
audio-to-obsidian（编排器，Layer 2）
│
├── extract-url-media      ← Layer 1: URL → 元信息 + 音频 + 内嵌字幕
├── audio-to-subtitle      ← Layer 0: 音频/视频 → ASR 转录文字
└── ob-collect (笔记写入)  ← Layer 1: 元信息 + 文案 → Obsidian 笔记（模板见 ob-collect 视频/音频模式）
```

## 处理管线

```
URL 输入:
  extract-url-media ──→ (无内嵌字幕?) ──→ audio-to-subtitle ──→ ob-collect
  [元信息+音频+字幕]                       [ASR 转录]              [笔记写入]

本地视频/音频:
  audio-to-subtitle ──→ ob-collect
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
    ├── meta.json           # 元数据 + 状态跟踪 + 时间记录
    ├── audio.wav           # extract-url-media 产物
    └── subtitle.srt        # 内嵌字幕或 ASR 产物
```

## meta.json 状态跟踪（v2 schema）

```json
{
  "id": "dQw4w9WgXcQ",
  "platform": "youtube",
  "url": "https://...",
  "title": "标题",
  "author": "作者",
  "pipeline": {
    "version": 2,
    "engine": "local",
    "model": "large-v3-turbo",
    "format": "md",
    "startedAt": "2026-04-06T10:00:00+08:00",
    "completedAt": "2026-04-06T10:05:30+08:00",
    "duration": 330,
    "status": "completed",
    "resumeCount": 0
  },
  "stages": {
    "media": {
      "status": "done",
      "startedAt": "2026-04-06T10:00:00+08:00",
      "completedAt": "2026-04-06T10:00:45+08:00",
      "duration": 45,
      "attempts": 1,
      "lastError": null
    },
    "subtitle": {
      "status": "done",
      "source": "embedded",
      "startedAt": "2026-04-06T10:00:45+08:00",
      "completedAt": "2026-04-06T10:00:45+08:00",
      "duration": 0,
      "attempts": 1,
      "lastError": null
    },
    "obsidian": {
      "status": "done",
      "startedAt": "2026-04-06T10:00:46+08:00",
      "completedAt": "2026-04-06T10:05:30+08:00",
      "duration": 284,
      "attempts": 1,
      "lastError": null
    }
  }
}
```

### 阶段状态机

```
pending → in_progress → done
                      → failed → retrying → in_progress (指数退避，最多 3 次)
                                         → permanently_failed
pending → skipped（阶段不适用时）
```

**双重校验**：meta.json + 文件存在性互为备份，任一缺失则重新执行。

## 执行流程

### Phase 1: 环境检查

检查三个依赖 skill 均可用 + OBSIDIAN_REPO 配置。
同时扫描 pipeline-dir 检测是否有可恢复的中断任务。

### Phase 2: 参数确认（一次性交互）

**一次 AskUserQuestion 收集所有参数**：

| 参数 | 是否必问 | 默认值 | 说明 |
|------|----------|--------|------|
| engine | ✅ 必问 | local | 核心决策 |
| model | ❌ 智能默认 | large-v3-turbo | engine=local 时生效 |
| format | ❌ 智能默认 | md | 输出格式 |
| overwrite | 条件确认 | false | 仅当目标文件已存在时问 |
| 批量确认 | 条件确认 | — | 仅 batch≥10 时展示 |

**豆包费用估算**（engine=doubao 时展示）：

| 音频时长 | 预估费用 | 说明 |
|---------|---------|------|
| 5 分钟 | ~¥0.05 | 按量计费 |
| 30 分钟 | ~¥0.30 | 标准费率 |
| 60 分钟 | ~¥0.60 | 建议分段处理 |
| 120 分钟 | ~¥1.20 | 需拆分为 ≤30min 段 |

> 费用 = 音频时长（分钟）× ¥0.01/分钟（参考价）。实际以火山引擎账单为准。

### Phase 3: 输入收集

```
URL → 检测平台 → 进入 URL 管线
本地视频 → file --mime-type → 进入本地管线
本地音频 → file --mime-type → 进入本地管线
URL 文件 → 逐行读取 → 每行按 URL 处理
```

#### 多平台能力矩阵

| 平台 | 批量获取 | 内嵌/自动字幕 | 注意事项 |
|------|---------|---------------|---------|
| YouTube | ✅ yt-dlp 原生 | ✅ 手动 + 自动生成 | **最佳支持**，全功能 |
| B站 | ⚠️ UP主需浏览器 | ✅ CC 字幕 | yt-dlp 划列表不稳定 |
| TikTok | ⚠️ 需 curl_cffi | ✅ 自动字幕 | 必须安装 curl_cffi |
| 抖音 | ❌ 不支持创作者页 | ❌ | 仅单视频，需 Cookie，限中文口播 |
| 小红书 | ❌ 不支持博主页 | ❌ | 仅视频笔记 |
| Twitter/X | ❌ | ❌ | 需 Cookie |

### Phase 4: 任务处理

#### 调度决策表

| 任务数 | 策略 | 实现方式 |
|--------|------|----------|
| 1-4 | 直接执行 | 主会话顺序调用 pipeline.py |
| 5-50 | 并行执行 | 多个 Bash(run_in_background=true) |

**并行分组策略**：
- 分组大小：3-4 个任务/组
- 并行数上限：4（MacBook Air M2 资源限制）
- 所有 Bash 调用**在同一条响应中发起**（关键）

#### Sub Agent 并行执行模板

```bash
# 生成临时 URL 文件给每个 Agent
echo "url1\nurl2\nurl3" > /tmp/pipeline-batch-1.txt
echo "url4\nurl5\nurl6" > /tmp/pipeline-batch-2.txt

# 同一条响应中发起所有后台任务
python3 scripts/pipeline.py /tmp/pipeline-batch-1.txt --engine local ... &
python3 scripts/pipeline.py /tmp/pipeline-batch-2.txt --engine local ... &
wait
```

#### 阶段执行（带时间追踪 + 重试 + 清理）

每个阶段由 `execute_stage()` 包装：
1. 记录 startedAt → 执行 → 记录 completedAt + duration
2. 失败 → 清理部分产物 → 指数退避重试
3. 重试耗尽 → 标记 permanently_failed，继续下一个任务

```
阶段失败 → 清理空文件 → 等待 2s → 重试
第 2 次失败 → 等待 4s → 重试
第 3 次失败 → 标记 permanently_failed
连续 3 个任务失败 → 暂停整个批量
```

### Phase 5: 输出报告

```
📊 处理完成
✅ 成功: 8 (耗时: 12m30s)    ❌ 失败: 1    ⏭ 跳过: 1

生成文件:
  • $OBSIDIAN_REPO/raw/作者/标题.md
  • $OBSIDIAN_REPO/wiki/标题-归纳.md

失败项:
  • https://... → 转录失败: API timeout
    重试: python3 scripts/pipeline.py --resume --engine local
```

## Resume 协议

meta.json v2 天然支持断点续传：

1. 新会话触发本 skill
2. Phase 1 扫描 pipeline-dir 下所有 meta.json
3. 找到存在 `pending`/`failed`/`in_progress` 阶段的任务
4. Phase 2 展示恢复选项
5. 从最早未完成步骤继续

### 恢复命令

```bash
# 恢复所有中断任务
python3 scripts/pipeline.py --resume \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --engine local

# 恢复特定任务（指定 pipeline-dir）
python3 scripts/pipeline.py --resume \
  --video-pipeline-dir ~/Downloads/video-pipeline
```

### Next Up 契约

```
---
## ▶ Next Up

**Phase 4: process** — 还有 17/25 个任务待处理

恢复命令：
```bash
python3 scripts/pipeline.py --resume --engine local --obsidian-repo "$OBSIDIAN_REPO"
```

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
| 并行上限 | ≤ 4 个 Agent |

自动停止条件：HTTP 429/403、验证码、连续 3 次失败。

## 用户交互点

| 阶段 | 标记 | 触发条件 | YOLO 行为 |
|------|------|---------|-----------|
| Phase 1 | ✅ | 环境检查 | 自动通过 |
| Phase 2 | 📝 | **始终交互** | 使用智能默认值 |
| Phase 3 | ✅ | 输入收集 | 自动执行 |
| Phase 4 | ✅ | 任务处理 | **零交互** |
| Phase 5 | ✅ | 输出报告 | 自动展示 |

✅ 自动执行 | 📝 一次性交互确认 | 🚫 中途零交互

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

---

## 订阅管理（Subscription Layer）

> 持久化追踪 UP 主视频列表，增量发现新视频，一键处理。

### 触发词

```text
- 订阅这个UP主 / subscribe
- 同步视频 / sync
- 处理新视频 / process
- 查看订阅状态
- 清理临时文件
```

### 架构

```
subscription.py (Layer 2.5)
    │
    ├── bilibili-video-list/api-fetch.py → 获取视频列表
    ├── diff subscription.json        → 发现新视频
    ├── audio-to-obsidian/pipeline.py → 处理新视频
    └── pipeline meta.json             → 同步处理状态
```

### 数据模型

**路径**: `~/Downloads/video-pipeline/subscriptions/bilibili/{uid}.json`

每个 UP 主一个 JSON 文件，以 bvid 为 key 追踪每个视频状态：

| 状态 | 含义 |
|------|------|
| `new` | 刚发现，未处理 |
| `pending` | 已加入处理队列 |
| `processing` | 处理中 |
| `completed` | 处理完成 |
| `failed` | 处理失败（可重试） |
| `skipped` | 手动跳过 |

### CLI 命令

```bash
SCRIPT="plugins/video-processing/skills/audio-to-obsidian/scripts/subscription.py"

# 订阅
python3 "$SCRIPT" subscribe --name "姜汁汽水"

# 同步（发现新视频）
python3 "$SCRIPT" sync --uid <UID>
python3 "$SCRIPT" sync --all

# 状态
python3 "$SCRIPT" status --uid <UID>

# 导出未处理 URL
python3 "$SCRIPT" export --uid <UID> --output /tmp/new.txt

# 处理新视频
python3 "$SCRIPT" process --uid <UID> --obsidian-repo "$OBSIDIAN_REPO"

# 跳过
python3 "$SCRIPT" skip --uid <UID> --bvids BV1xx,BV1yy

# 刷新 pipeline 状态
python3 "$SCRIPT" refresh --uid <UID>

# 清理临时文件
python3 "$SCRIPT" cleanup --uid <UID>

# 取消订阅
python3 "$SCRIPT" unsubscribe --uid <UID>
```

### 典型工作流

```
用户: 订阅姜汁汽水
  → subscribe --name "姜汁汽水"
  → sync --uid <UID>

用户: 处理新视频
  → process --uid <UID> --obsidian-repo ... --max-items 10

用户: 清理临时文件
  → cleanup --uid <UID>
```

### 临时文件清理

`cleanup` 命令会删除已完成任务的 `audio.wav`、`audio.md`、`subtitle.srt` 等，
保留 `meta.json`，释放磁盘空间。
