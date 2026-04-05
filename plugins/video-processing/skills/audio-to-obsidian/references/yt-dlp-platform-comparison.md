# yt-dlp 多平台下载难度对比

> 本文档对比 yt-dlp 在 B 站、YouTube、TikTok/抖音、小红书四个平台上的下载稳定性、反爬难度和最佳实践，帮助选择合适的采集策略。

## 一、总览：难度排序

| 排名 | 平台 | 稳定性 | 反爬强度 | 需要登录 | 批量友好 | 维护优先级 |
|------|------|--------|----------|----------|----------|------------|
| 1 | **YouTube** | 高 | 中 | 通常不需要 | 中 | 最高 |
| 2 | **Bilibili** | 较高 | 中 | 高画质需要 | 中高 | 高 |
| 3 | **小红书** | 中低 | 中高 | 通常不需要 | 中 | 低 |
| 4 | **TikTok/抖音** | 低 | 极高 | 部分需要 | 差 | 中 |

## 二、逐平台详细分析

### 2.1 YouTube — 最稳定，修复最快

**官方支持状态**：核心目标站点，yt-dlp 的首要维护对象

**Extractor 特点**：
- 代码量最大、功能最完整的 Extractor
- 支持 `web`、`mweb`、`android_vr`、`tv`、`web_embedded` 等多种客户端
- 支持 PO Token 自动生成（配合插件）

**反爬机制**：

| 机制 | 说明 | 应对方案 |
|------|------|----------|
| n-signature 挑战 | YouTube 定期更新签名算法 | 保持 yt-dlp 更新，通常几天内修复 |
| PO Token | 证明请求来自合法客户端 | 安装 `bgutil-ytdlp-pot-provider` 插件 |
| IP 限流 | 匿名 ~300 个/小时，登录 ~2000 个/小时 | 频率控制 + Cookie |
| Cookie 轮换 | 浏览器标签页中频繁更换 Cookie | 隐身窗口导出法 |

**推荐配置**：

```bash
# 日常下载（匿名模式）
yt-dlp --extractor-args "youtube:player_client=mweb,android_vr" \
  --sleep-interval 8 --max-sleep-interval 15 "URL"

# 稳定大量下载（PO Token + Cookie）
yt-dlp --cookies-from-browser safari \
  --extractor-args "youtube:player_client=mweb" \
  --sleep-interval 5 --max-sleep-interval 10 "URL"
```

**已知风险**：
- n-sig 变更导致临时失效，但 yt-dlp 维护者响应最快（通常 1-3 天修复）
- 传 Cookie 有账号被封风险，建议使用小号（详见 [yt-dlp-safe-config.md](./yt-dlp-safe-config.md)）

---

### 2.2 Bilibili — 功能最全面

**官方支持状态**：完整官方支持，拥有 20+ 个 Extractor 类

**Extractor 覆盖范围**：

| Extractor | 功能 | URL 格式 |
|-----------|------|----------|
| `BiliBiliIE` | 普通视频 | BV/AV 链接 |
| `BiliBiliBangumiIE` | 番剧/影视 | bangumi/play |
| `BilibiliCheeseIE` | 课程视频 | cheese/ |
| `BilibiliSpaceVideoIE` | 用户空间视频 | space.bilibili.com |
| `BiliLiveIE` | 直播 | live.bilibili.com |
| `BiliIntlIE` | 国际版 | bilibili.tv |
| `BilibiliPlaylistIE` | 播放列表 | favlist/medialist |
| `BiliBiliDynamicIE` | 动态 | dynamic/ |

**反爬机制**：

| 机制 | 说明 | 应对方案 |
|------|------|----------|
| WBI 签名 | API 请求参数签名验证 | yt-dlp 已自动实现 `_sign_wbi`，密钥缓存 30 秒 |
| 画质限制 | 720P 以下公开，1080P+ 需登录 | 传 SESSDATA Cookie |
| DRM 保护 | 番剧和部分影视内容 | **无法绕过**，只能下载无 DRM 的内容 |
| 频率限制 | 频繁请求触发风控 | 控制间隔 ≥ 5 秒 |
| CC 字幕 | 需要登录才能获取 | 传 Cookie |

**推荐配置**：

```bash
# 公开视频（无需 Cookie）
yt-dlp --sleep-interval 5 --max-sleep-interval 10 \
  "https://www.bilibili.com/video/BV1xx411c7mD"

# 高画质 + 字幕（需要 Cookie）
yt-dlp --cookies-from-browser chrome \
  --sleep-interval 5 "URL"

# 批量下载用户空间视频
yt-dlp --sleep-interval 8 --max-sleep-interval 15 \
  "https://space.bilibili.com/UID/video"
```

**已知风险**：
- WBI 密钥更新可能导致临时失效（yt-dlp 通常已自动处理）
- 部分老视频的 `__INITIAL_STATE__` 提取失败
- 番剧/课程等 DRM 内容无法下载
- Festival 活动页面 URL 重定向有 bug

---

### 2.3 小红书 — 能用但经常出问题

**官方支持状态**：官方支持（内置 `XiaoHongShuIE` Extractor）

**Extractor 工作原理**（最简单的 Extractor 之一）：
1. 下载页面 HTML
2. 从 `window.__INITIAL_STATE__` 提取 JSON 数据
3. 解析视频流 URL（`masterUrl` + `backupUrls`）
4. 尝试通过 `originVideoKey` 获取原始画质

**反爬机制**：

| 机制 | 说明 | 应对方案 |
|------|------|----------|
| `__INITIAL_STATE__` 变更 | 页面结构变化导致提取失败 | 等 yt-dlp 更新 |
| 画质降级 | 2026 年起最高 1080P，4K 已不可用 | 无法解决 |
| 短链拦截 | xhslink.com 短链被服务端拒绝 | 先在浏览器打开获取完整 URL |
| URL 格式限制 | 仅支持 `/explore/` 和 `/discovery/item/` | 确保使用正确的 URL 格式 |

**支持和不支持的 URL 格式**：

```bash
# 支持
yt-dlp "https://www.xiaohongshu.com/explore/NOTE_ID"
yt-dlp "https://www.xiaohongshu.com/discovery/item/NOTE_ID"

# 不支持（需先在浏览器打开获取完整 URL）
yt-dlp "https://www.xiaohongshu.com/user/profile/USER_ID"
yt-dlp "https://xhslink.com/a/XXXXX"  # 短链，会被拦截
```

**推荐配置**：

```bash
# 基本下载（通常不需要 Cookie）
yt-dlp --sleep-interval 5 "https://www.xiaohongshu.com/explore/NOTE_ID"

# 如果触发反爬，尝试传 Cookie
yt-dlp --cookies-from-browser chrome "URL"
```

**已知风险**：
- Extractor 功能基础，社区维护力度低
- 2026 年 1 月曾出现过 Extractor 完全失效的情况
- 4K 原始画质已不可用，平台主动限制
- 不适合批量采集，容易触发反爬

---

### 2.4 TikTok/抖音 — 最不稳定

**官方支持状态**：官方支持，但稳定性最差

**反爬机制**（最激进）：

| 机制 | 说明 | 应对方案 |
|------|------|----------|
| App 参数模拟 | 需要模拟设备 ID、App 版本、Install ID | yt-dlp 内置处理，但参数经常失效 |
| IP 限流 | 部分 IP 范围需要登录才能访问公开内容 | 传 Cookie 或换 IP |
| 直播流保护 | Live 的 m3u8 流经常返回 404 | 基本无解 |
| 抖音 Cookie 验证 | 传入 Cookie 也经常报 "fresh cookies" 错误 | 几乎无法解决 |
| 地理隔离 | TikTok（海外）和抖音（国内）完全隔离 | 各自处理 |

**TikTok vs 抖音对比**：

| 维度 | TikTok（海外） | 抖音（国内） |
|------|---------------|-------------|
| 公开视频下载 | 大部分能用 | 几乎不可用 |
| 直播下载 | 经常 404 | 经常 404 |
| Cookie 效果 | 部分有效 | 即使传入也经常失败 |
| yt-dlp 相关 Issue | ~10 个 | 持续 open，长期未解决 |
| 建议 | 偶尔可用 | **不建议依赖 yt-dlp** |

**推荐配置**：

```bash
# TikTok 基本下载（先尝试匿名）
yt-dlp --sleep-interval 10 "https://www.tiktok.com/@user/video/ID"

# 如果失败，尝试传 Cookie
yt-dlp --cookies-from-browser chrome "URL"

# 抖音 — 不推荐使用 yt-dlp，成功率极低
# 建议考虑其他方式：录屏、官方 App 缓存等
```

**已知风险**：
- 476 个相关 issue，远超其他平台
- Extractor 经常失效，修复周期不确定
- 直播下载问题自 2023 年 7 月仍未完全解决
- **抖音几乎不可用，不建议在自动化流程中依赖**

## 三、跨平台采集策略

### 3.1 同一作者多平台视频的场景

很多创作者会在 B 站、YouTube、小红书等平台同步发布内容。采集时建议按以下优先级：

```
优先级：YouTube ≈ B 站 > 小红书 >>> TikTok/抖音
```

**策略建议**：

| 策略 | 说明 |
|------|------|
| **优先 B 站/YouTube** | 稳定性高，Extractor 成熟，支持批量 |
| **小红书作补充** | 大部分时候能用，但接受偶尔失败 |
| **TikTok 谨慎依赖** | 仅用于偶尔的单视频下载 |
| **去重机制** | 通过标题相似度或内容匹配避免重复采集 |
| **降级方案** | 主平台失败时尝试其他平台获取同一内容 |

### 3.2 各平台适合的采集模式

| 采集模式 | YouTube | B 站 | 小红书 | TikTok |
|----------|---------|------|--------|--------|
| 单视频下载 | 推荐 | 推荐 | 可用 | 勉强可用 |
| 仅提取字幕 | 推荐 | 推荐（需 Cookie） | 不适用 | 不适用 |
| 仅提取音频 | 推荐 | 推荐 | 可用 | 勉强可用 |
| 批量用户空间 | 可用（注意限流） | 推荐 | 不推荐 | 不推荐 |
| 播放列表 | 推荐 | 推荐 | 不适用 | 不适用 |
| 自动化定时 | 可用（需 Cookie + PO Token） | 可用（需 Cookie） | 不推荐 | 不推荐 |

### 3.3 风控应对策略对比

| 措施 | YouTube | B 站 | 小红书 | TikTok |
|------|---------|------|--------|--------|
| Cookie | 小号推荐 | 高画质必须 | 遇到反爬时用 | 部分有效 |
| PO Token | 强烈推荐 | 不适用 | 不适用 | 不适用 |
| 代理 | IP 被封时用 | 部分视频地区限制 | 基本不需要 | 换 IP 有效 |
| 频率控制 | ≥ 8 秒 | ≥ 5 秒 | ≥ 5 秒 | ≥ 10 秒 |
| 限速 | 3 MB/s | 不严格要求 | 不严格要求 | 不严格要求 |
| 客户端切换 | mweb ↔ android_vr | 不适用 | 不适用 | 不适用 |

## 四、本项目中现有 Skill 覆盖

| 平台 | 已有 Skill | 支持程度 |
|------|-----------|----------|
| Bilibili | `bilibili-to-obsidian` + `bilibili-batch` | 完善：字幕提取、批量采集、按作者分类 |
| YouTube | `audio-to-obsidian` | 通用：音频提取 + 转录，支持 1000+ 平台 |
| TikTok/抖音 | `video-to-text` | 部分：支持抖音但稳定性差 |
| 小红书 | `yt-dlp`（通用 skill） | 基础：通过 yt-dlp 直接下载 |
| 通用转录 | `audio-to-subtitle` | 完善：支持 MLX-Whisper（本地）和豆包（云端） |

## 五、建议后续改进方向

1. **统一入口 Skill**：创建一个 `cross-platform-to-obsidian` skill，输入作者在各平台的链接，自动选择最优平台采集
2. **去重机制**：通过视频标题/时长匹配，避免同一内容在不同平台重复采集
3. **降级策略**：主平台失败时自动尝试其他平台获取同一内容
4. **抖音替代方案**：对于抖音平台，考虑录屏或 App 缓存提取等非 yt-dlp 方案

## 六、参考资料

- [yt-dlp GitHub 仓库](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp 支持站点列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- [yt-dlp Extractor 源码](https://github.com/yt-dlp/yt-dlp/tree/master/yt_dlp/extractor)
- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- 本项目相关文档：
  - [yt-dlp 风控解决方案](./yt-dlp-risk-control.md)
  - [yt-dlp 安全稳定配置](./yt-dlp-safe-config.md)
  - [视频下载使用规范](./video-download-guidelines.md)

---

> 最后更新：2026-04-05
