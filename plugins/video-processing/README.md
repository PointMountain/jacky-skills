# Video Processing Plugin

音视频 ASR 转录工具集。采集和 Obsidian 写入已迁移到 `obsidian-tools/ob-collect`。

## 当前包含的 Skills

`plugins/video-processing/.claude-plugin/plugin.json` 当前注册 1 个 skill：

1. `audio-to-subtitle`（ASR 转录）

> `audio-to-obsidian` 和 `write-obsidian-note` 已删除。视频/音频采集和 Obsidian 写入统一由 `ob-collect` 处理。

## 用法

### 1) 用 j-skills 链接并安装

```bash
j-skills link ./plugins/video-processing/skills/audio-to-subtitle
j-skills install audio-to-subtitle --env claude-code,codex
```

### 2) 运行前置依赖

- `python3`
- `ffmpeg`（音频转码）
- 本地引擎需要 `mlx-whisper`，云端引擎需要豆包 API 凭证

### 3) 常用命令（audio-to-subtitle）

```bash
# 音频转字幕（本地引擎）
python3 plugins/video-processing/skills/audio-to-subtitle/scripts/transcribe.py \
  /path/to/audio.mp3 \
  --engine local -m large-v3-turbo -f md --yolo

# 视频转字幕
python3 plugins/video-processing/skills/audio-to-subtitle/scripts/transcribe.py \
  /path/to/video.mp4 \
  --engine local -f srt --yolo

# 云端引擎（中文优化）
python3 plugins/video-processing/skills/audio-to-subtitle/scripts/transcribe.py \
  /path/to/audio.wav \
  --engine doubao -f md
```

## 当前架构

```
ob-collect（obsidian-tools 插件，统一采集入口）
├── OpenCLI 路由层（文章/视频/播客/社交媒体）
│   ├── 有字幕 → 直接采集
│   └── 无字幕 → download → audio-to-subtitle（ASR）
└── WebFetch（回退）

audio-to-subtitle（本插件，纯 ASR 能力）
└── 音频/视频 → 文字（SRT/VTT/TXT/MD）
```
