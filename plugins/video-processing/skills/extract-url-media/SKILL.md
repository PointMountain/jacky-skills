---
name: extract-url-media
description: "从 URL 提取媒体元信息和音频文件。封装 yt-dlp 的元信息获取 + 音频提取为标准化接口。触发词：提取视频信息、获取音频、extract-url-media。"
---

<role>
你是 URL 媒体提取器，负责从任意平台 URL 获取结构化元信息 + 音频文件。
</role>

<purpose>
封装 yt-dlp 的元信息获取和音频提取能力，返回标准化的 JSON 结构，供下游 skill 消费。
</purpose>

<trigger>
```text
触发词/示例：
- 提取这个视频的元信息和音频
- 获取视频信息
- extract-url-media
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>extract-url-media</name>
    <owner>video-processing</owner>
    <requires>yt-dlp, ffmpeg</requires>
    <checkpoints>
      <checkpoint order="1">yt-dlp 和 ffmpeg 可用</checkpoint>
      <checkpoint order="2">元信息获取成功</checkpoint>
      <checkpoint order="3">音频文件已提取到工作目录</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>仅下载音频流，不下载视频（-x 参数）</constraint>
      <constraint>输出格式为 WAV（16kHz 单声道，Whisper 最优输入）</constraint>
      <constraint>工作目录统一使用 VIDEO_PIPELINE_DIR（默认 ~/Downloads/video-pipeline/）</constraint>
      <constraint>URL 下载失败时返回结构化错误，不抛异常</constraint>
      <constraint>所有 yt-dlp 调用必须设置 --socket-timeout 30 --retries 3</constraint>
      <constraint>下载前必须检查磁盘剩余空间 ≥ 500MB</constraint>
      <constraint>失败时指数退避重试（1s → 2s → 4s），最多 3 次</constraint>
      <constraint>所有 subprocess 调用使用列表参数，禁止字符串拼接（防命令注入）</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>输入 URL → 输出标准化元信息 JSON + 音频文件路径。</gsd:goal>

  <gsd:phase name="precheck" order="1">
    <gsd:step>验证 yt-dlp 和 ffmpeg 已安装。</gsd:step>
    <gsd:step>验证 VIDEO_PIPELINE_DIR 可写。</gsd:step>
    <gsd:step>磁盘空间预检：剩余空间 ≥ 500MB，不足则报错。</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="extract" order="2">
    <gsd:step>检测 URL 类型：单个视频 / 播放列表 / B站UP主空间。</gsd:step>
    <gsd:step>单个视频 → yt-dlp 获取元信息 + 提取音频。</gsd:step>
    <gsd:step>播放列表 → yt-dlp --flat-playlist 获取列表，逐个处理。</gsd:step>
    <gsd:step>B站UP主空间 → agent-browser 浏览器方案提取视频列表（无需登录/WBI签名）。</gsd:step>
    <gsd:step>尝试提取内嵌字幕（yt-dlp --write-sub），无内嵌则跳过。</gsd:step>
    <gsd:step>创建工作目录 + 写入 meta.json + 提取音频。</gsd:step>
    <gsd:checkpoint>元信息 + 音频 + 字幕（如有）提取完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="deliver" order="3">
    <gsd:step>返回标准化 JSON 输出。</gsd:step>
    <gsd:checkpoint>输出交付</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

# Extract URL Media - URL 媒体提取器

从任意平台 URL 获取结构化元信息 + 音频文件的原子 Skill。

## 可执行脚本

```bash
# 基础用法
python3 scripts/extract.py "https://www.youtube.com/watch?v=xxxx"

# 指定工作目录
python3 scripts/extract.py "https://www.youtube.com/watch?v=xxxx" \
  --video-pipeline-dir "~/Downloads/video-pipeline"

# 跳过字幕提取
python3 scripts/extract.py "https://www.youtube.com/watch?v=xxxx" --skip-subs

# 强制刷新（忽略已有 meta/audio 缓存）
python3 scripts/extract.py "https://www.youtube.com/watch?v=xxxx" --force-refresh
```

## 输入输出契约

### 输入

```json
{
  "url": "https://www.youtube.com/watch?v=xxx",
  "videoPipelineDir": "~/Downloads/video-pipeline"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `url` | ✅ | 任意 yt-dlp 支持的 URL |
| `videoPipelineDir` | ❌ | 工作目录根路径，默认 `~/Downloads/video-pipeline` |

### 输出（成功）

```json
{
  "success": true,
  "data": {
    "id": "dQw4w9WgXcQ",
    "platform": "youtube",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "author": "Rick Astley",
    "duration": "3:33",
    "audioPath": "~/Downloads/video-pipeline/youtube/dQw4w9WgXcQ/audio.wav",
    "subtitlePath": "~/Downloads/video-pipeline/youtube/dQw4w9WgXcQ/subtitle.srt",
    "subtitleSource": "embedded",
    "workDir": "~/Downloads/video-pipeline/youtube/dQw4w9WgXcQ",
    "metaPath": "~/Downloads/video-pipeline/youtube/dQw4w9WgXcQ/meta.json"
  }
}
```

### 输出（失败）

```json
{
  "success": false,
  "error": {
    "url": "https://...",
    "stage": "download",
    "message": "HTTP Error 403: Forbidden",
    "suggestion": "使用 yt-dlp --cookies-from-browser chrome 重试"
  }
}
```

## 执行步骤

### Step 1: 环境检查

```bash
which yt-dlp && echo "OK"
which ffmpeg && echo "OK"

# 磁盘空间预检（至少 500MB）
df -h "$VIDEO_PIPELINE_DIR" | awk 'NR==2 && $4+0 < 500 { exit 1 }'
```

> 磁盘不足时返回错误，建议用户清理空间后再试。

### Step 2: 获取元信息

```bash
yt-dlp --socket-timeout 30 --retries 3 \
  --print "%(uploader)s|%(title)s|%(id)s|%(duration_string)s|%(extractor_key)s" "<URL>"
```

输出：`作者|标题|视频ID|时长|平台标识`

> `--socket-timeout 30` 防止网络挂起，`--retries 3` 内置重试。

### Step 3: 创建工作目录

```bash
WORK_DIR="$VIDEO_PIPELINE_DIR/$PLATFORM/$VIDEO_ID"
mkdir -p "$WORK_DIR"
```

### Step 4: 提取音频

```bash
yt-dlp -x --audio-format wav --audio-quality 0 \
  --socket-timeout 30 --retries 3 \
  --postprocessor-args "-ar 16000 -ac 1" \
  -o "$WORK_DIR/audio.%(ext)s" \
  "<URL>"
```

> `-x` 只下载音频流，`--audio-format wav` 转 WAV，`--postprocessor-args` 降采样为 16kHz 单声道。
> `--socket-timeout 30` 防止网络挂起，`--retries 3` yt-dlp 内置重试。

**失败重试策略（指数退避）**：

```
第 1 次失败 → 等待 1 秒 → 重试
第 2 次失败 → 等待 2 秒 → 重试
第 3 次失败 → 返回结构化错误
```

### Step 5: 提取内嵌字幕（可选）

```bash
# 优先下载手动上传字幕
yt-dlp --write-sub --write-auto-subs --sub-lang "zh-Hans,zh-CN,zh,en" \
  --convert-subs srt --skip-download \
  -o "$WORK_DIR/subtitle" "$URL"
```

> `--write-sub` 下载手动字幕，`--write-auto-subs` 下载自动生成字幕（YouTube 等），`--convert-subs srt` 统一转 SRT 格式。

- 成功 → `subtitleSource: "embedded"`，`subtitlePath` 指向字幕文件
- 无内嵌字幕 → `subtitleSource: null`，`subtitlePath: null`（由 audio-to-subtitle ASR 补充）

### Step 6: 写入 meta.json

```json
{
  "id": "dQw4w9WgXcQ",
  "platform": "youtube",
  "url": "https://...",
  "title": "标题",
  "author": "作者",
  "duration": "3:33",
  "stages": {
    "media":    { "status": "done", "audioFile": "audio.wav", "at": "2026-04-05T10:00:00Z" },
    "subtitle": { "status": "done|pending", "source": "embedded|null", "file": "subtitle.srt|null" },
    "obsidian": { "status": "pending" }
  }
}
```

## 状态检测（跳过逻辑）

如果 `meta.json` 存在且 `stages.audio.status == "done"` 且 `audio.wav` 文件存在且大小 > 0，则跳过提取步骤，直接返回已有结果。

## 错误处理

| 错误 | 返回 suggestion |
|------|----------------|
| HTTP 403 | `yt-dlp --cookies-from-browser chrome "$URL"` |
| HTTP 429 | 等待 30 分钟后重试 |
| 视频不可用 | 检查 URL 是否有效 |
| ffmpeg 缺失 | `brew install ffmpeg` |

## 多平台能力矩阵

| 平台 | extractor | URL 格式 | 批量获取 | 手动字幕 | 自动字幕 | 备注 |
|------|-----------|---------|---------|---------|---------|------|
| **YouTube** | `youtube` | `youtube.com/watch?v=xxx` / `@name/videos` | ✅ yt-dlp 原生 | ✅ | ✅ | **最佳支持**，全功能可用 |
| **B站** | `bilibili` | `bilibili.com/video/BVxxx` | ⚠️ 不稳定 | ✅ CC 字幕 | ❌ | UP主空间用浏览器方案 |
| **TikTok** | `tiktok` | `tiktok.com/@user/video/xxx` | ⚠️ 需 curl_cffi | ✅ | ✅ | **必须安装 curl_cffi** |
| **抖音** | `douyin` | `v.douyin.com/xxx` | ❌ 不支持创作者页 | ❌ | ❌ | 仅支持单视频，需 Cookie |
| **Twitter/X** | `twitter` | `x.com/user/status/xxx` | ❌ | ❌ | ❌ | 需 Cookie 认证 |
| **小红书** | `xhs` | `xiaohongshu.com/explore/xxx` | ❌ 不支持创作者页 | ❌ | ❌ | 仅支持单条视频笔记 |

> ✅ 完全支持 | ⚠️ 有限/不稳定 | ❌ 不支持

## 多平台策略决策树

```
输入 URL → 检测平台
│
├── YouTube → yt-dlp 单一方案
│   ├── 单视频: yt-dlp -x + --write-sub --write-auto-subs
│   ├── 频道页: yt-dlp --flat-playlist → 获取列表 → 逐个处理
│   └── 大频道(>200): 可选 YouTube Data API v3 获取列表 + yt-dlp 下载字幕
│
├── B站 → yt-dlp + 浏览器辅助
│   ├── 单视频(BV号): yt-dlp -x + --write-sub
│   └── UP主空间: agent-browser 浏览器方案（详见专节）
│
├── TikTok → yt-dlp + curl_cffi
│   ├── 前置: pip install curl_cffi
│   ├── 单视频: yt-dlp -x --cookies-from-browser chrome
│   └── 创作者: yt-dlp --flat-playlist（不稳定时用 Cookie）
│
├── 抖音 → yt-dlp 单视频（仅此）
│   ├── 单视频: yt-dlp -x --cookies-from-browser chrome
│   └── 创作者批量: ❌ 不支持，建议使用 douyin-downloader 工具
│
├── 小红书 → yt-dlp 单条视频（仅此）
│   ├── 视频笔记: yt-dlp -x
│   ├── 图文笔记: ❌ 不支持（非视频内容）
│   └── 博主批量: ❌ 不支持，建议使用 MediaCrawler
│
└── 其他 → yt-dlp 默认处理
    └── 1000+ 站点，按 yt-dlp 默认行为
```

### 平台特有参数

**YouTube 安全配置**（防 429 封禁）：

```bash
# 日常下载（匿名模式）
yt-dlp --extractor-args "youtube:player_client=mweb,android_vr" \
  --sleep-interval 8 --max-sleep-interval 15 \
  --sleep-requests 3 --limit-rate 3M \
  "$URL"

# 稳定大量下载（PO Token + Cookie）
yt-dlp --cookies-from-browser safari \
  --extractor-args "youtube:player_client=mweb" \
  --sleep-interval 5 --max-sleep-interval 10 \
  "$URL"
```

| 反爬机制 | 说明 | 应对 |
|---------|------|------|
| n-signature | 定期更新签名算法 | 保持 yt-dlp 更新，通常 1-3 天修复 |
| PO Token | 证明请求来自合法客户端 | 安装 `bgutil-ytdlp-pot-provider` 插件 |
| IP 限流 | 匿名 ~300/h，登录 ~2000/h | 频率控制 + Cookie |
| 客户端切换 | web/mweb/android_vr/tv | `--extractor-args` 切换 |

**B站反爬机制**：

```bash
# 高画质 + 字幕（需要 SESSDATA Cookie）
yt-dlp --cookies-from-browser chrome \
  --sleep-interval 5 --max-sleep-interval 10 \
  "$URL"
```

| 反爬机制 | 说明 | 应对 |
|---------|------|------|
| WBI 签名 | API 参数签名验证 | yt-dlp 已自动实现 `_sign_wbi` |
| 画质限制 | 720P 以下公开，1080P+ 需登录 | 传 SESSDATA Cookie |
| CC 字幕 | 需要登录才能获取 | 传 Cookie |
| DRM | 番剧/影视内容 | **无法绕过**，只能下载无 DRM 内容 |
| 频率限制 | 频繁请求触发风控 | 控制间隔 ≥ 5 秒 |

**TikTok 前置依赖**：

```bash
pip install -U curl_cffi   # 强制要求，否则请求被拦截
```

**抖音 Cookie 要求**：

```bash
yt-dlp --cookies-from-browser chrome "$URL"   # 必须提供 Cookie
```

> ⚠️ 抖音 yt-dlp 稳定性极差（476+ 相关 issue），不建议在自动化流程中依赖。建议使用 douyin-downloader 工具替代。

**小红书 URL 限制**：

```bash
# ✅ 支持
yt-dlp "https://www.xiaohongshu.com/explore/NOTE_ID"
yt-dlp "https://www.xiaohongshu.com/discovery/item/NOTE_ID"

# ❌ 不支持
yt-dlp "https://www.xiaohongshu.com/user/profile/USER_ID"  # 博主页
yt-dlp "https://xhslink.com/a/XXXXX"                        # 短链，被拦截
```

### 风控参数对照表

| 参数 | YouTube | B站 | 小红书 | TikTok/抖音 |
|------|---------|------|--------|-------------|
| Cookie | 小号推荐 | 高画质必须 | 遇反爬时用 | 部分有效 |
| PO Token | 强烈推荐 | 不适用 | 不适用 | 不适用 |
| 代理 | IP 被封时 | 部分地区限制 | 基本不需要 | 换 IP 有效 |
| 请求间隔 | ≥ 8 秒 | ≥ 5 秒 | ≥ 5 秒 | ≥ 10 秒 |
| 限速 | 3 MB/s | 不严格要求 | 不严格要求 | 不严格要求 |
| 客户端切换 | mweb ↔ android_vr | 不适用 | 不适用 | 不适用 |

## B站 UP主空间批量获取（浏览器方案）

当 URL 为 B站 UP主空间页（`space.bilibili.com/{UID}/upload/video`）时，yt-dlp 无法直接获取完整视频列表。使用 agent-browser 无头浏览器方案提取。

### 为什么用浏览器方案

| 维度 | 浏览器方案 | yt-dlp / API |
|------|-----------|-------------|
| 登录要求 | 不需要 | yt-dlp 部分需要 / API 需要 SESSDATA |
| 签名机制 | 不需要 | API 需要 WBI 签名 |
| TLS 指纹 | 真实 Chromium | 需额外处理 |
| 风控风险 | 极低 | 高 |

### 执行流程

```
1. agent-browser open https://space.bilibili.com/{UID}/upload/video
2. wait --load networkidle
3. JS 提取当前页所有视频（BV 号 + 标题）
4. 保存到结果数组
5. snapshot -i 找到"下一页"按钮
6. click 下一页
7. wait --load networkidle
8. 重复 3-7 直到没有"下一页"按钮
9. agent-browser close
10. 导出完整视频列表 JSON
```

### JS 提取脚本

```javascript
JSON.stringify(
  Array.from(document.querySelectorAll('.upload-video-card')).map(card => {
    const link = card.querySelector('a[href*="bilibili.com/video/"]');
    const href = link ? link.href : '';
    const bvid = (href.match(/BV[\w]+/) || [])[0] || '';
    const title = link ? link.textContent.trim() : '';
    return { bvid, title: title.substring(0, 80), href };
  })
)
```

### URL 检测规则

```
space.bilibili.com/{UID}/upload/video → 浏览器方案
space.bilibili.com/{UID}              → 浏览器方案（补充 /upload/video）
bilibili.com/video/BVxxx              → yt-dlp 直接处理
```

### 分页参数

- 每页 40 个视频
- 翻页间隔 2-3 秒（模拟人类行为）
- 底部分页按钮选择器：`button` 文本为数字或"下一页"

> 详细方案见 `references/bilibili-uploader-video-list-browser-approach.md`

```

## 安全机制

### 命令注入防护

所有 yt-dlp/ffmpeg 调用使用列表参数，禁止字符串拼接：
```python
# ✅ 正确 — 列表参数
subprocess.run(["yt-dlp", "-x", "--audio-format", "wav", url], timeout=300)

# ❌ 错误 — 字符串拼接（可注入恶意 URL）
subprocess.run(f"yt-dlp -x {url}", shell=True)
```
### 文件名安全
使用视频 ID（非标题）命名文件，防止路径遍历攻击：
```
$WORK_DIR/$PLATFORM/$VIDEO_ID/audio.wav   # 视频 ID 格式固定，无特殊字符
# 而非：
$WORK_DIR/$TITLE/audio.wav            # 标题可能含 / \ ? * 等非法字符
```
## 风控检查清单

| 检查项 | 检查时机 | 实现 |
|--------|-----------|------|
| 磁盘空间 ≥ 500MB | Step 1 预检 | `df -h` + `awk` |
| 网络超时 30s | Step 2/4 | `--socket-timeout 30` |
| 重试 3 次 | Step 2/4 | `--retries 3` |
| 指数退避 | 失败重试 | 1s → 2s → 4s |
| 命令注入 | 所有 subprocess | 列表参数调用 |
| 文件存在性 | 跳过逻辑 | `meta.json` + 文件大小 > 0 |
| 文件名安全 | 工作目录 | 视频 ID 命名，非标题 |
