# Audio-to-Obsidian 文件路径参考

> 基于 BV1NGQoBAEVv 实际运行生成的路径示例，供后续重构对照。

## 全局配置变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `OBSIDIAN_REPO` | `/Users/jiashengwang/jacky-github/jacky-obsidian` | Obsidian 仓库根目录 |
| `VIDEO_PIPELINE_DIR` | `~/Downloads/video-pipeline/` | 管线工作目录根 |

## 管线工作目录（每个视频一个）

```
~/Downloads/video-pipeline/
└── {platform}/{video-id}/
    ├── meta.json           # 状态跟踪（媒体/字幕/Obsidian 三阶段）
    ├── audio.wav           # extract-url-media 产物（16kHz 单声道）
    └── audio.md            # audio-to-subtitle 产物（Markdown 带时间轴）
```

### 实际示例

```
~/Downloads/video-pipeline/bilibili/BV1NGQoBAEVv/
├── meta.json       # 2KB   状态跟踪文件
├── audio.wav       # 76MB  提取的音频
└── audio.md        # 82KB  ASR 转录结果（1066 段）
```

### meta.json 结构

```json
{
  "id": "BV1NGQoBAEVv",
  "platform": "bilibili",
  "url": "https://www.bilibili.com/video/BV1NGQoBAEVv",
  "title": "北漂猛男，十几年来靠打游戏住上大别墅，时间自由，快乐无比",
  "author": "摩的司机徐师傅",
  "duration": "41:41",
  "stages": {
    "media": {
      "status": "done",
      "audioFile": "audio.wav",
      "at": "2026-04-06T02:11:00+08:00"
    },
    "subtitle": {
      "status": "done",
      "source": "asr-mlx-whisper",
      "file": "audio.md",
      "at": "2026-04-06T02:15:00+08:00"
    },
    "obsidian": {
      "status": "done",
      "files": [
        "北漂猛男，十几年来靠打游戏住上大别墅，时间自由，快乐无比-原文.md",
        "北漂猛男，十几年来靠打游戏住上大别墅，时间自由，快乐无比-归纳.md"
      ],
      "at": "2026-04-06T02:26:00+08:00"
    }
  }
}
```

## Obsidian 输出目录

```
$OBSIDIAN_REPO/00-Inbox/Audio/{作者名}/
├── {标题}-原文.md     # 完整转录（带时间戳）
└── {标题}-归纳.md     # AI 归纳笔记
```

### 实际示例

```
/Users/jiashengwang/jacky-github/jacky-obsidian/00-Inbox/Audio/摩的司机徐师傅/
├── 北漂猛男，十几年来靠打游戏住上大别墅，时间自由，快乐无比-原文.md   # 23KB
└── 北漂猛男，十几年来靠打游戏住上大别墅，时间自由，快乐无比-归纳.md   # 2.5KB
```

## 配置文件

### audio-to-subtitle 配置

```
~/.audio2subtitle/config.json
```

```json
{
  "engine": "doubao",
  "model": "large-v3-turbo",
  "format": "srt",
  "language": null,
  "doubao": {
    "app_id": "***",
    "access_token": "***",
    "resource_id": "volc.seedasr.auc"
  }
}
```

## Skills 文件位置

```
# 已安装的全局 Skills
~/.claude/skills/
├── extract-url-media/
│   ├── SKILL.md
│   └── scripts/extract.py
├── audio-to-subtitle/
│   ├── SKILL.md
│   └── scripts/transcribe.py
├── audio-to-obsidian/
│   ├── SKILL.md                    # 编排器
│   ├── scripts/pipeline.py
│   └── references/                 # ← 本文件所在位置
│       └── file-paths-example.md
└── write-obsidian-note/
    ├── SKILL.md
    └── scripts/write_note.py

# 源码仓库（git 管理）
~/jacky-github/jacky-skills/plugins/video-processing/skills/
├── audio-to-obsidian/
├── extract-url-media/
├── audio-to-subtitle/
├── write-obsidian-note/
├── bilibili-video-list/
└── youtube-video-list/
```

## 文件命名规则

| 规则 | 说明 |
|------|------|
| 工作目录 | `{platform}/{video-id}` — video-id 无特殊字符，安全可靠 |
| 音频文件 | `audio.wav` — 固定名称，不依赖标题 |
| 字幕文件 | `audio.md` / `subtitle.srt` — 固定名称 |
| Obsidian 笔记 | `{标题}-原文.md` / `{标题}-归纳.md` |
| 文件名清理 | `/\?%*:\|"<>` → 替换为下划线 |
| 文件名长度 | ≤ 200 字符，超出截断 |

## 管线三阶段状态流转

```
meta.json stages.status:

media:    pending → done / failed
subtitle: pending → done / skipped / failed
obsidian: pending → done / failed

跳过条件:
  media:    meta.status=done + audio.wav 存在且 size>0
  subtitle: meta.status=done + audio.md 存在 且 source="embedded"（有内嵌字幕时 skip）
  obsidian: meta.status=done + 目标文件存在
```

## 原子写入机制

```bash
# 1. 先写临时文件（以 .tmp_ 开头）
TARGET_DIR="$OBSIDIAN_REPO/00-Inbox/Audio/$SAFE_AUTHOR"
TMP_FILE="$TARGET_DIR/.tmp_${SAFE_TITLE}-原文_$$.md"
TARGET_FILE="$TARGET_DIR/${SAFE_TITLE}-原文.md"

# 2. 写入临时文件
cat > "$TMP_FILE" <<CONTENT
...
CONTENT

# 3. 原子重命名（同文件系统 mv 是原子操作）
mv -f "$TMP_FILE" "$TARGET_FILE"
```
