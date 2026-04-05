# Video Pipeline 渐进式处理流水线设计

> 日期：2026-04-05
> 状态：设计中

## 核心目标

用户给一个输入（URL / 本地视频 / 本地音频），自动走完流水线，最终产物是 **Obsidian 中的原文笔记 + 归纳笔记**。每个阶段自动检测已有产物，跳过已完成步骤，避免重复工作。

## 流水线四阶段

```
阶段1: 获取视频 → 阶段2: 提取音频 → 阶段3: 提取字幕 → 阶段4: 同步到 Obsidian
(URL下载/         (ffmpeg)          (B站内嵌/ASR)        (原文.md + 归纳.md)
 本地导入)
```

**全部阶段必须完成，终点始终是 Obsidian 里的笔记。**

## 三种输入场景

| 输入 | 示例 | 起点阶段 | download 状态 |
|------|------|---------|---------------|
| B 站 URL | `https://bilibili.com/video/BV1xx...` | 阶段 1 | 正常执行 |
| 本地视频文件 | `/path/to/video.mp4` | 阶段 2 | `skipped` |
| 本地音频文件 | `/path/to/audio.mp3` | 阶段 3 | `skipped` |

## 目录结构

### 本地工作目录（媒体文件）

```
~/Downloads/video-pipeline/
├── bilibili/                   # 按平台分目录
│   └── BV1xx411x7xx/           # 以视频 ID 命名
│       ├── meta.json           # 元数据 + 状态跟踪
│       ├── video.mp4           # 阶段1: 下载的视频
│       ├── audio.mp3           # 阶段2: 提取的音频
│       └── subtitle.srt        # 阶段3: 提取的字幕
├── douyin/
│   └── 7123456789/
│       └── ...
└── local/                      # 本地导入的文件
    └── {文件名hash}/
        ├── meta.json
        ├── video.mp4           # 可能有
        ├── audio.mp3           # 可能有
        └── subtitle.srt
```

### Obsidian 仓库（最终产物）

```
$OBSIDIAN_REPO/00-Inbox/B站/[作者名]/
├── [标题]-原文.md
└── [标题]-归纳.md

$OBSIDIAN_REPO/00-Inbox/本地/[用户指定分类或默认]/
├── [标题]-原文.md
└── [标题]-归纳.md
```

## meta.json 设计

### URL 输入示例

```json
{
  "id": "BV1xx411x7xx",
  "platform": "bilibili",
  "url": "https://www.bilibili.com/video/BV1xx411x7xx",
  "title": "视频标题",
  "author": "UP主名",
  "duration": "12:34",
  "publishDate": "2025-01-15",
  "stages": {
    "download": { "status": "done", "file": "video.mp4", "at": "2025-04-05T10:00:00Z" },
    "audio":    { "status": "done", "file": "audio.mp3", "at": "2025-04-05T10:01:00Z" },
    "subtitle": { "status": "done", "file": "subtitle.srt", "source": "bilibili-embedded", "at": "2025-04-05T10:02:00Z" },
    "obsidian": { "status": "done", "files": ["原文.md", "归纳.md"], "at": "2025-04-05T10:03:00Z" }
  }
}
```

### 本地文件导入示例

```json
{
  "id": "local_20250405_a3f2b1",
  "platform": "local",
  "source": "/Users/jacky/Downloads/某个视频.mp4",
  "sourceType": "video",
  "title": "用户指定或文件名",
  "stages": {
    "download": { "status": "skipped", "reason": "本地文件导入" },
    "audio":    { "status": "done", "file": "audio.mp3", "at": "2025-04-05T10:01:00Z" },
    "subtitle": { "status": "pending" },
    "obsidian": { "status": "pending" }
  }
}
```

## 状态检测逻辑

每个阶段执行前，统一执行以下检测：

```
1. meta.json 中 status == "done"
   ├─ 且对应文件存在 → 跳过
   └─ 但文件不存在（被手动删除）→ 重置 status 为 pending，重新执行

2. meta.json 中 status != "done"
   ├─ 目录下已存在目标文件且大小 > 0 → 补写 status 为 done，跳过执行
   └─ 无文件 → 执行该阶段
```

**meta.json 和文件存在性双重校验，互相补位：**
- meta.json 丢了但文件还在 → 靠文件存在性恢复
- 文件被删了但 meta.json 还在 → 靠 meta.json 发现不一致，重新执行

## 各阶段详细设计

### 阶段 1：获取视频（Download）

| 项目 | 说明 |
|------|------|
| **触发条件** | `meta.json` 不存在 或 `stages.download.status` 非 done/skipped |
| **输入** | B 站 URL |
| **输出** | `video.mp4` |
| **检测** | 文件存在且大小 > 0 |
| **工具** | `yt-dlp` |
| **失败处理** | 标记 `status: "failed"`，记录 error，中止后续阶段 |

### 阶段 2：提取音频（Audio）

| 项目 | 说明 |
|------|------|
| **触发条件** | 阶段 1 done/skipped，且 `stages.audio.status != "done"` |
| **输入** | `video.mp4` |
| **输出** | `audio.mp3` |
| **检测** | 文件存在且大小 > 0 |
| **工具** | `ffmpeg -i video.mp4 -vn -acodec libmp3lame audio.mp3` |
| **失败处理** | 标记失败，中止后续 |

### 阶段 3：提取字幕（Subtitle）

| 项目 | 说明 |
|------|------|
| **触发条件** | 阶段 2 done，且 `stages.subtitle.status != "done"` |
| **输入** | `audio.mp3`（或 `video.mp4`） |
| **输出** | `subtitle.srt` |
| **检测** | 文件存在且非空 |
| **策略** | 优先获取 B 站内嵌字幕，无字幕时走 ASR |
| **失败处理** | 标记失败，中止后续 |

#### 字幕获取优先级

```
1. 尝试 yt-dlp --write-sub 获取 B 站内嵌字幕
   ├─ 成功 → source: "bilibili-embedded"
   └─ 失败 → 进入 ASR
2. ASR 路径
   ├─ MLX-Whisper（本地免费）
   └─ 豆包云端 ASR（中文效果更好）
3. 最终输出 subtitle.srt
```

### 阶段 4：同步到 Obsidian（Obsidian）

| 项目 | 说明 |
|------|------|
| **触发条件** | 阶段 3 done，且 `stages.obsidian.status != "done"` |
| **输入** | `subtitle.srt` + `meta.json` |
| **输出** | Obsidian 中的 `原文.md` + `归纳.md` |
| **检测** | Obsidian 目标路径下两个文件是否都已存在 |
| **输出路径** | `$OBSIDIAN_REPO/00-Inbox/B站/[作者名]/` |
| **内容** | 原文：带时间戳的字幕文本；归纳：AI 总结核心要点 |

## 批量处理与断点续传

meta.json 天然支持断点续传：

- 批量处理多个 URL 时，每个视频独立目录、独立 meta.json
- 中途中断后重新运行，已完成的阶段自动跳过
- 失败的视频标记为 `failed`，不影响其他视频继续处理

## 配置项

| 配置 | 说明 | 默认值 |
|------|------|--------|
| `VIDEO_PIPELINE_DIR` | 工作目录根路径 | `~/Downloads/video-pipeline` |
| `OBSIDIAN_REPO` | Obsidian 仓库路径 | 从全局 CLAUDE.md 读取 |
| `ASR_ENGINE` | ASR 引擎偏好 | `mlx-whisper`（本地优先） |
| `WHISPER_MODEL` | Whisper 模型大小 | `base` |
