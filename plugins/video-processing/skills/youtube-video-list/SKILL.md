---
name: youtube-video-list
description: "获取 YouTube 频道完整视频列表。基于 yt-dlp，无需 API Key。支持频道 ID、handle、URL 和名字搜索，输出 JSON。触发词：获取YouTube视频列表、youtube-video-list、YouTube频道视频。"
---

<role>
你是 YouTube 频道视频列表采集助手，使用 yt-dlp 获取视频列表，无需 API Key。
</role>

<purpose>
给定频道的 ID、handle、URL 或名字，获取视频元数据（视频 ID、标题、播放量、点赞数、时长），输出 JSON 文件和终端预览。
</purpose>

<trigger>
```text
触发词/示例：
- 获取这个 YouTube 频道的视频列表
- 获取 https://www.youtube.com/@username/videos 的视频列表
- 列出 YouTube 频道的全部视频
- 获取这个频道播放量最高的视频
- 搜索 YouTube 上摩的司机徐师傅的视频
- youtube-video-list
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>youtube-video-list</name>
    <owner>video-processing</owner>
    <requires>python3 + yt-dlp</requires>
    <checkpoints>
      <checkpoint order="1">yt-dlp 可用性检查完成</checkpoint>
      <checkpoint order="2">频道 ID 解析完成</checkpoint>
      <checkpoint order="3">视频数据采集完成，JSON 文件已保存</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>纯数据采集，不做字幕提取、视频下载或笔记写入</constraint>
      <constraint>需要 yt-dlp（pip3 install yt-dlp）</constraint>
      <constraint>--detailed 模式较慢（需逐个获取视频详情），建议配合 --limit 使用</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>获取 YouTube 频道完整视频列表并保存为 JSON 文件。</gsd:goal>

  <gsd:phase name="check" order="1">
    <gsd:step>检查 yt-dlp 是否安装（yt-dlp --version）。</gsd:step>
    <gsd:step>未安装 → 提示 pip3 install yt-dlp。</gsd:step>
    <gsd:checkpoint>yt-dlp 确认可用</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="parse" order="2">
    <gsd:step>从输入中提取频道 ID / URL / handle / 名字。</gsd:step>
    <gsd:step>名字搜索：通过 yt-dlp ytsearch 查找频道。</gsd:step>
    <gsd:checkpoint>频道 ID 解析完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="collect" order="3">
    <gsd:step>运行 python3 scripts/api-fetch.py。</gsd:step>
    <gsd:step>默认模式：--flat-playlist 快速获取列表（标题、时长）。</gsd:step>
    <gsd:step>--detailed 模式：额外获取播放量、点赞数等（较慢）。</gsd:step>
    <gsd:checkpoint>数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="export" order="4">
    <gsd:step>JSON 已保存到 ~/Downloads/youtube-video-list/，终端输出表格预览。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# YouTube Video List — YouTube 频道视频列表采集

> 基于 yt-dlp，无需 API Key，开箱即用。

## 模式选择

| 模式 | 命令 | 数据 | 速度 |
|------|------|------|------|
| **快速模式**（默认） | 无需额外参数 | 标题、时长、视频ID | 几秒内 |
| **详细模式** | `--detailed` | 额外含播放量、点赞数、评论数、日期 | 较慢（逐个获取） |

> **推荐**：先用快速模式获取完整列表，再用 `--detailed --limit 20` 获取前 20 个视频的详细数据。

---

## 执行流程

### 前提检查

```bash
yt-dlp --version
# 未安装：pip3 install yt-dlp
```

### 直接运行

脚本位置：`plugins/video-processing/skills/youtube-video-list/scripts/api-fetch.py`

```bash
SCRIPT_PATH="plugins/video-processing/skills/youtube-video-list/scripts/api-fetch.py"

# 通过名字搜索
python3 "$SCRIPT_PATH" --name "摩的司机徐师傅"

# 通过频道 ID
python3 "$SCRIPT_PATH" --channel-id UCWHg8GXDTAYj39Yo6XQuCLQ

# 通过 handle
python3 "$SCRIPT_PATH" --handle @username

# 通过 URL
python3 "$SCRIPT_PATH" --url "https://www.youtube.com/@username/videos"

# 详细模式（含播放量）+ 限制数量
python3 "$SCRIPT_PATH" --name "摩的司机徐师傅" --detailed --limit 20

# 格式化输出
python3 "$SCRIPT_PATH" --name "摩的司机徐师傅" --pretty
```

### 输入解析

| 输入格式 | 提取方式 | 示例 |
|----------|----------|------|
| 频道 ID | 直接使用 | `UCWHg8GXDTAYj39Yo6XQuCLQ` |
| Handle | 转为 URL | `@username` → `youtube.com/@username/videos` |
| 频道 URL | 直接使用 | `https://www.youtube.com/@username` |
| 频道名字 | yt-dlp 搜索 | "摩的司机徐师傅" |

---

## 输出文件

- **路径**：`~/Downloads/youtube-video-list/{频道名}_{日期}.json`

### JSON 字段

#### 快速模式

| 字段 | 说明 |
|------|------|
| `videoId` | 视频 ID |
| `title` | 标题 |
| `url` | 视频链接 |
| `duration` | 时长 |
| `channel` | 频道名 |
| `channelId` | 频道 ID |

#### 详细模式（额外字段）

| 字段 | 说明 |
|------|------|
| `play` | 播放量（精确值） |
| `likes` | 点赞数 |
| `comment` | 评论数 |
| `date` | 发布日期 |
| `description` | 简介（前200字） |

## 边界情况

| 情况 | 处理方式 |
|------|----------|
| yt-dlp 未安装 | 提示 pip3 install yt-dlp |
| 频道不存在 | 搜索无结果时提示 |
| 私密视频 | 不包含在列表中 |
| 网络问题 | yt-dlp 自动重试 |
| 详细模式超时 | 建议使用 --limit 减少数量 |

## 免责声明

> [!warning] 本 Skill 仅用于个人学习和研究目的。因不当使用造成的法律后果由使用者自行承担。
