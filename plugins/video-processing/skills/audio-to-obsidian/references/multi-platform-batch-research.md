# 多平台创作者内容批量获取调研

> 调研时间：2026-04-05
> 目标：调研 B 站、抖音、YouTube、小红书、TikTok 五个平台的创作者内容批量获取方案

---

## 平台对比总览

| 维度 | B 站 | 抖音 | YouTube | 小红书 | TikTok |
|------|------|------|---------|--------|--------|
| **推荐方案** | yt-dlp + 浏览器辅助 | douyin-downloader | yt-dlp 单一方案 | MediaCrawler | yt-dlp + curl_cffi |
| **yt-dlp 支持创作者页** | 支持（不稳定） | **不支持** | **完全支持** | **不支持** | 部分支持（需 curl_cffi） |
| **yt-dlp 支持字幕** | 支持（CC 字幕） | 不支持 | **完全支持** | 不适用 | 支持（自动字幕） |
| **需要浏览器自动化** | 可选 | 是 | 否 | 是 | 可选 |
| **需要登录/Cookie** | 可选 | 是 | 否 | 是 | 可选 |
| **反爬难度** | 中 | **高** | 低 | **高** | 中高 |
| **创作者主页 URL** | `space.bilibili.com/{uid}` | `douyin.com/user/{sec_uid}` | `youtube.com/@name/videos` | `xiaohongshu.com/user/profile/{uid}` | `tiktok.com/@username` |

---

## 一、B 站 UP 主空间批量获取

### 当前方案：yt-dlp

```bash
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(view_count)s|%(uploader)s" \
  "https://space.bilibili.com/316568752/upload/video"
```

### 浏览器方案（备选）

当 yt-dlp 不稳定时，可通过 B 站 API 直接获取：

```
GET https://api.bilibili.com/x/space/wbi/arc/search
参数: mid={uid}&pn={page}&ps=30&order=pubdate
排序: order=pubdate(发布时间) | order=click(播放量) | order=stow(收藏量)
```

需要 wbi 签名（`w_rid` + `wts`），社区已有公开实现。

---

## 二、抖音创作者批量获取

> 抖音无公开 API，yt-dlp **不支持**创作者主页批量获取，必须使用专用工具。

### 推荐方案：douyin-downloader

| 项目 | 信息 |
|------|------|
| GitHub | https://github.com/jiji262/douyin-downloader |
| Stars | 7,183+ |
| 语言 | Python |
| 特点 | 开箱即用，内置视频转文字 |

**核心能力**：

| 功能 | 说明 |
|------|------|
| 创作者主页批量下载 | `douyin.com/user/{sec_uid}` |
| 无水印下载 | 自动选择无水印源 |
| 视频转文字 | 内置 OpenAI Transcriptions API（`gpt-4o-mini-transcribe`） |
| 浏览器回退 | API 被封时自动启动浏览器滚动获取 |
| 增量下载 | SQLite 去重 |
| Docker 部署 | 支持 |

**配置示例**：

```yaml
# config.yaml
link:
  - https://www.douyin.com/user/MS4wLjABAAAAxxxx
mode:
  - post        # post(发布)/like(点赞)/mix(合集)/music(音乐)
number:
  post: 50      # 0 = 全部

transcript:
  enabled: true
  model: gpt-4o-mini-transcribe
  api_key_env: OPENAI_API_KEY
```

### 备选工具

| 工具 | Stars | 说明 |
|------|-------|------|
| [f2](https://github.com/Johnserf-Seed/f2) | 2,358+ | Python 库，编程集成友好，`pip install f2` |
| [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | 47,000+ | 多平台爬虫（抖音/小红书/B站/快手等） |
| yt-dlp | - | 仅支持单视频 `douyin.com/video/{id}`，需 Cookie |

### 抖音反爬要点

| 反爬措施 | 应对方式 |
|----------|----------|
| `a_bogus` 签名 | 浏览器环境执行 JS 或使用专用工具 |
| Cookie 验证 | 需 `ttwid`、`s_v_web_id` 等 cookie |
| 请求频率限制 | 间隔 1-3 秒，随机化 |
| 验证码 | 触发后需手动处理 |

### 抖音 Web API（逆向接口）

| API 端点 | 用途 |
|----------|------|
| `/aweme/v1/web/aweme/post/` | 获取创作者发布的视频列表 |
| `/aweme/v1/web/aweme/detail/` | 获取单个视频详情 |
| `/aweme/v1/web/general/search/single/` | 关键词搜索视频 |
| `/aweme/v1/web/comment/list/` | 获取视频评论 |

URL 格式：
- 创作者主页：`https://www.douyin.com/user/{sec_user_id}`
- 单视频：`https://www.douyin.com/video/{aweme_id}`
- 短链接：`https://v.douyin.com/xxxxxxx/`

---

## 三、YouTube 频道批量获取

> YouTube 是 yt-dlp 支持最好的平台，**推荐 yt-dlp 单一方案，无需浏览器自动化**。

### 推荐方案：yt-dlp

**完整工作流**：

```bash
# 1. 获取频道视频列表 + 元信息（含播放量）
yt-dlp --dump-json --no-download \
  "https://www.youtube.com/@ChannelName/videos" > channel.json

# 2. 按播放量排序取 Top N（本地排序）
cat channel.json | python3 -c "
import json, sys
videos = [json.loads(l) for l in sys.stdin if l.strip()]
videos.sort(key=lambda x: x.get('view_count', 0) or 0, reverse=True)
for v in videos[:20]:
    print(f'{v[\"view_count\"]:>12}  {v[\"id\"]}  {v[\"title\"][:60]}')
"

# 3. 批量下载字幕（手动 + 自动生成）
yt-dlp --write-subs --write-auto-subs \
  --sub-langs "zh-Hans,en.*" \
  --convert-subs srt \
  --skip-download \
  -o "output/%(title)s.%(ext)s" \
  "TOP_VIDEO_URL_1" "TOP_VIDEO_URL_2" ...
```

**快速列表模式**（仅 URL，不获取详情，极快）：

```bash
yt-dlp --flat-playlist --print "%(id)s|%(title)s" \
  "https://www.youtube.com/@ChannelName/videos"
```

### 安全配置

```bash
yt-dlp \
  --extractor-args "youtube:player_client=mweb,android_vr" \
  --sleep-interval 8 --max-sleep-interval 15 \
  --sleep-requests 3 \
  --limit-rate 3M \
  "URL"
```

### 备选方案：YouTube Data API v3

| 项目 | 说明 |
|------|------|
| 配额 | 10,000 单位/天（免费） |
| 获取列表 | `channels.list` → `playlistItems.list`（~2 配额/频道） |
| 获取详情 | `videos.list`（1 配额/次，最多 50 ID） |
| 字幕下载 | **不支持**（需 yt-dlp） |
| 适用场景 | 视频数量 > 200，需频繁使用 |

YouTube API 获取列表极快（秒级），但不能下载字幕，需配合 yt-dlp。

### 字幕获取能力

```bash
# 查看可用字幕
yt-dlp --list-subs "VIDEO_URL"

# 下载手动上传字幕
yt-dlp --write-subs --sub-langs "zh-Hans,en" --skip-download "VIDEO_URL"

# 下载自动生成字幕
yt-dlp --write-auto-subs --sub-langs "zh-Hans,en" --skip-download "VIDEO_URL"

# 转为 SRT 格式
yt-dlp --write-auto-subs --sub-langs "zh-Hans" --convert-subs srt --skip-download "VIDEO_URL"
```

---

## 四、小红书博主批量获取

> 小红书无公开 API，yt-dlp **不支持**创作者主页，必须使用浏览器自动化方案。

### 推荐方案：MediaCrawler

| 项目 | 信息 |
|------|------|
| GitHub | https://github.com/NanmiCoder/MediaCrawler |
| Stars | 47,000+ |
| 技术 | Playwright + httpx + asyncio |
| 平台支持 | 小红书、抖音、B站、快手、微博、贴吧、知乎 |

**核心能力**：

| 功能 | 说明 |
|------|------|
| 博主主页批量获取 | `creator` 模式，自动分页 |
| 关键词搜索 | `search` 模式 |
| 单条笔记详情 | `detail` 模式 |
| CDP 模式 | 使用用户真实浏览器，反检测最佳 |
| IP 代理池 | 支持 |
| 数据存储 | csv/json/db/sqlite/excel/postgres |

**使用步骤**：

```bash
# 1. 克隆并安装
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler && uv sync && uv run playwright install

# 2. 配置 config/base_config.py
# PLATFORM = "xhs"
# CRAWLER_TYPE = "creator"
# XHS_CREATOR_ID_LIST = ["5c31698d0000000007018a31"]
# ENABLE_CDP_MODE = True

# 3. 运行（扫码登录）
uv run main.py --platform xhs --lt qrcode --type creator
```

### 备选工具

| 工具 | Stars | 说明 |
|------|-------|------|
| [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) | 10,667+ | 单条笔记下载，支持 MCP 模式集成 Claude Code |
| yt-dlp | - | 仅支持单条视频笔记 `xiaohongshu.com/explore/{id}` |
| [ReaJason/xhs](https://github.com/ReaJason/xhs) | 2,099+ | Python API 封装，`pip install xhs` |

### 小红书反爬要点

| 反爬措施 | 应对方式 |
|----------|----------|
| `X-s` / `X-t` 签名 | Playwright 注入 JS 获取（MediaCrawler 方案） |
| Cookie 校验 | 扫码登录获取 `web_session` |
| xsec_token | 每条笔记需要独立 token |
| 验证码 | 触发 HTTP 471/461，需手动处理 |

### 内容类型

| 类型 | 字段值 | 处理方式 |
|------|--------|----------|
| 图文笔记 | `type: "normal"` | 提取图片 + 文字描述 |
| 视频笔记 | `type: "video"` | yt-dlp 下载视频 + 转录 |
| LivePhoto | - | XHS-Downloader 支持 |

URL 格式：`https://www.xiaohongshu.com/user/profile/{user_id}`

---

## 五、TikTok 创作者批量获取

> TikTok 和抖音是**完全独立的平台**，工具不通用。

### 推荐方案：yt-dlp + curl_cffi

```bash
# 1. 安装依赖（关键！）
pip install -U yt-dlp curl_cffi

# 2. 获取创作者视频列表
yt-dlp --flat-playlist --dump-json --skip-download \
  "https://www.tiktok.com/@username" > user_videos.json

# 3. 获取特定视频的字幕/文案
yt-dlp --write-subs --write-auto-subs \
  --write-info-json --skip-download \
  "https://www.tiktok.com/@username/video/VIDEO_ID"

# 4. 如遇反爬，使用浏览器 Cookie
yt-dlp --cookies-from-browser chrome \
  "https://www.tiktok.com/@username"
```

### 注意事项

| 项目 | 说明 |
|------|------|
| **必须安装 `curl_cffi`** | TikTok 强制要求浏览器指纹模拟，否则请求被拦截 |
| `tiktok:sound` / `tiktok:tag` / `tiktok:effect` | 源码标记 CURRENTLY BROKEN，仅 `tiktok:user` 可用 |
| Cookie | `--cookies-from-browser` 传入浏览器 cookies |
| 请求频率 | 使用 `--sleep-requests 3` 控制频率 |
| 定期更新 | TikTok 频繁更新反爬，需保持 yt-dlp 最新版本 |

### TikTok vs 抖音对比

| 维度 | TikTok | 抖音 |
|------|--------|------|
| 域名 | `tiktok.com` | `douyin.com` |
| App Name | `musical_ly` / `trill` | `aweme` |
| App ID | 1233 / 1180 | 1128 |
| API Host | 海外服务器 | 中国服务器 |
| 创作者 URL | `tiktok.com/@username` | `douyin.com/user/{sec_uid}` |
| yt-dlp 批量 | 支持（需 curl_cffi） | **不支持** |
| 反爬核心 | 浏览器指纹（TLS） | a_bogus 签名 |
| 推荐工具 | yt-dlp | douyin-downloader |

### TikTok 反爬机制

| 反爬类型 | 说明 |
|----------|------|
| 浏览器指纹检测 | 强制 impersonation，需 `curl_cffi` |
| WAF JS 挑战 | "Please wait..." 页面，SHA256 哈希计算 |
| 登录墙 | 部分内容重定向 `/login`，需 Cookie |
| IP 封锁 | 状态码 10204 |
| API 重复页 | 有时返回相同视频页，yt-dlp 自动重试 |

---

## 决策树

```
需要批量获取创作者内容？
│
├── B 站 → yt-dlp --flat-playlist（首选）
│         └── 失败？ → 浏览器方案（Playwright 滚动 + API）
│
├── YouTube → yt-dlp 单一方案（完全覆盖，无需浏览器）
│            └── 视频数量大？ → YouTube Data API v3 + yt-dlp
│
├── 抖音 → douyin-downloader（开箱即用）
│        ├── 需编程集成？ → f2（Python 库）
│        └── 多平台需求？ → MediaCrawler
│
├── 小红书 → MediaCrawler（creator 模式）
│          └── 只需单条？ → yt-dlp 或 XHS-Downloader
│
└── TikTok → yt-dlp + curl_cffi
           └── 不稳定？ → MediaCrawler 或 Apify
```

---

## 关键结论

1. **YouTube 最简单**：yt-dlp 一个工具搞定一切，支持最完善
2. **抖音/小红书最复杂**：必须用专用工具，yt-dlp 不支持创作者页
3. **TikTok ≠ 抖音**：完全独立的平台，API、反爬、工具都不通用
4. **所有平台排序都需要本地排序**：API/CLI 都无法直接按播放量返回结果
5. **MediaCrawler 是通用备选**：支持 7+ 平台（小红书、抖音、B站、快手、微博、贴吧、知乎），47,000+ Stars
