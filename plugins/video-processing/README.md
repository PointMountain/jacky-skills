# Video Processing Plugin

音视频处理插件，聚焦于”媒体提取 → 转录 → 笔记落盘”的技能编排。

## Included Skills

当前 `plugin.json` 实际注册了以下 6 个 skills：

1. `audio-to-obsidian`
2. `extract-url-media`
3. `audio-to-subtitle`
4. `write-obsidian-note`
5. `bilibili-video-list`
6. `youtube-video-list`

## Capability Summary

| Skill | 主要能力 | 当前实现状态 |
|---|---|---|
| `audio-to-subtitle` | 本地/云端音视频转字幕（SRT/VTT/TXT/MD） | 含可执行脚本 |
| `extract-url-media` | URL 媒体元信息与音频提取 | 含可执行脚本 |
| `write-obsidian-note` | llm-wiki 模式写入 Obsidian raw/wiki 笔记 | 含可执行脚本 |
| `audio-to-obsidian` | 端到端编排（提取 + 转录 + 写笔记） | 含可执行脚本 |
| `bilibili-video-list` | B 站 UP 主视频列表采集（API/浏览器双模式） | 含可执行脚本 |
| `youtube-video-list` | YouTube 频道视频列表采集（yt-dlp） | 含可执行脚本 |

## 架构总览

### 三层结构

```
┌─────────────────────────────────────────────────────────┐
│                    Layer 2: 编排器                         │
│                audio-to-obsidian                          │
│    (端到端编排，协调 3 个原子 skill 完成全流程)                │
└────────┬──────────────┬──────────────┬───────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼──────────┐
    │ Layer 1  │   │ Layer 0   │  │   Layer 1      │
    │ extract  │   │ audio-to  │  │   write        │
    │ -url     │   │ -subtitle │  │   -obsidian    │
    │ -media   │   │           │  │   -note        │
    └──────────┘   └───────────┘  └────────────────┘

    ┌──────────────────┐  ┌──────────────────┐
    │ bilibili-video   │  │ youtube-video    │    ← 独立数据采集 skills
    │ -list            │  │ -list            │      (为编排器提供 URL 列表)
    └──────────────────┘  └──────────────────┘
```

### 核心工作流

```
                        ┌──────────┐
                        │ 用户输入  │
                        └────┬─────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ① 在线 URL     ② 本地视频/音频   ③ URL 文件(.txt)
        (YouTube/B站     (.mp3/.mp4      (逐行读取,
         /TikTok等)      /.wav等)       每行按 URL 处理)
              │              │              │
              ▼              │              │
    ┌─────────────────┐     │              │
    │ extract-url-media│     │              │
    │  (元信息+音频     │     │              │
    │   +内嵌字幕)     │     │              │
    └────────┬────────┘     │              │
             │              │              │
             ▼              │              │
      有内嵌字幕？           │              │
       ┌────┴────┐          │              │
       ▼ Yes     ▼ No       │              │
       │         │          │              │
       │    ┌────▼──────────▼──────────────▼──┐
       │    │      audio-to-subtitle           │
       │    │  (ASR 转录: MLX-Whisper / 豆包)   │
       │    └────────────┬─────────────────────┘
       │                 │
       ▼                 ▼
    ┌──────────────────────────────┐
    │      write-obsidian-note      │
    │  (raw/作者/标题.md 原始字幕    │
    │   wiki/标题-归纳.md 归纳笔记   │
    │   写入 Obsidian 仓库)         │
    └──────────────┬───────────────┘
                   │
                   ▼
            ┌─────────────┐
            │  Obsidian    │
            │  raw/作者/   │
            │  ├ 标题.md   │ ← 原始字幕
            │  wiki/       │
            │  └ 标题-归纳 │ ← 引用 raw
            └─────────────┘
```

### 两种处理管线

| 输入类型 | 管线路径 |
|----------|---------|
| 在线 URL | extract-url-media → audio-to-subtitle（无内嵌字幕时）→ write-obsidian-note |
| 本地视频/音频 | audio-to-subtitle → write-obsidian-note |
| URL 文件 | 逐行读取，按 URL 管线处理 |

### 关键设计

- **纯编排器模式**：`audio-to-obsidian` 不直接调用 yt-dlp/ffmpeg，全部委托给原子 skill
- **字幕优先级**：优先使用内嵌字幕，没有时才走 ASR 转录
- **断点续传**：通过 `meta.json` 状态机追踪每个阶段，支持中断恢复
- **并行加速**：批量任务（5-50）自动拆分并行执行
- **独立采集 skills**：`bilibili-video-list` 和 `youtube-video-list` 可单独使用，也可为编排器提供 URL 列表

## Installation

### From CLI (Recommended)

```bash
npx skills add wangjs-jacky/video-processing
```

### From GitHub

```bash
git clone https://github.com/wangjs-jacky/jacky-skills.git
```

然后使用你当前的 skill 管理方式加载 `plugins/video-processing` 下的 skills。

### Update

```bash
npx skills update
```
