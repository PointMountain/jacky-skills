# Video Processing Plugin

音视频处理插件，聚焦于“媒体提取 → 转录 → 笔记落盘”的技能编排。

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
| `write-obsidian-note` | 统一格式写入 Obsidian 原文/归纳笔记 | 含可执行脚本 |
| `audio-to-obsidian` | 端到端编排（提取 + 转录 + 写笔记） | 含可执行脚本 |
| `bilibili-video-list` | B 站 UP 主视频列表采集（agent-browser） | 以 Skill 文档流程为主 |
| `youtube-video-list` | YouTube 频道视频列表采集（Data API） | 含可执行脚本 |

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
