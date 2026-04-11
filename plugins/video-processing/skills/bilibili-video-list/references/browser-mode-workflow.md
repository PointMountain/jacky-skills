# 浏览器模式采集方案 - 实战案例

> 本文档记录了 2026-04-07 采集 UP 主"战国时代_姜汁汽水"(UID: 1039025435) 的完整流程和命令。

## 采集概况

- **UP 主**: 战国时代_姜汁汽水
- **UID**: 1039025435
- **采集模式**: 浏览器模式 (API 模式因风控失败降级)
- **排序方式**: 按时间排序 (pubdate)
- **视频总数**: 80
- **采集时间**: 2026-04-07

## 完整采集流程

### Step 1: 检查 Cookie 可用性

```bash
# 检查环境变量
echo $BILIBILI_SESSDATA

# 检查配置文件
cat ~/.config/bilibili-cookies.json 2>/dev/null
```

**结果**: Cookie 配置存在但 API 模式遭遇风控，自动降级到浏览器模式。

---

### Step 2: 尝试 API 模式（失败）

```bash
python3 "/Users/jiashengwang/.config/opencode/skills/bilibili-video-list/scripts/api-fetch.py" --mid 1039025435 --order pubdate
```

**结果**: 提示"风控校验失败"，访问权限不足，切换到浏览器模式。

---

### Step 3: 打开 UP 主空间页

```bash
agent-browser open --headed "https://space.bilibili.com/1039025435/upload/video"
```

**注意**: 必须使用 `--headed` 参数，无头模式会触发 -352 风控。

---

### Step 4: 等待页面加载

```bash
agent-browser wait --load networkidle && agent-browser wait 8000
```

**说明**:
- `--load networkidle`: 等待网络请求完成
- `wait 8000`: 额外等待 8 秒让 SPA 渲染完成

---

### Step 5: 关闭登录弹窗

```bash
agent-browser eval 'document.querySelector(".bili-mini-close-icon")?.click(); "done"'

agent-browser wait 3000
```

---

### Step 6: 验证视频加载

```bash
agent-browser eval 'JSON.stringify({
  videoCount: document.querySelectorAll(".upload-video-card").length,
  hasError: document.body?.innerText?.includes("-352")
})'
```

**输出示例**:
```json
{
  "videoCount": 40,
  "hasError": false
}
```

---

### Step 7: 获取 UP 主名称

```bash
agent-browser eval 'document.querySelector("#h-name, .nickname")?.textContent?.trim() || "unknown"'
```

**输出**: `战国时代_姜汁汽水`

---

### Step 8: 提取视频数据（第一页）

```bash
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify({
  videos: Array.from(document.querySelectorAll('.upload-video-card')).map(card => {
    const link = card.querySelector('a[href*="bilibili.com/video/"]');
    const href = link ? link.href : '';
    const bvid = (href.match(/BV[\w]+/) || [''])[0] || '';
    const titleEl = card.querySelector('.bili-video-card__title a, .video-title');
    const title = titleEl ? titleEl.textContent.trim() : '';
    const rawText = card.innerText;
    const playMatch = rawText.match(/([\d.]+万?)\n\d+\n/);
    const play = playMatch ? playMatch[1] : '';
    const durationMatch = rawText.match(/(\d{1,2}:\d{2}(?::\d{2})?)/);
    const duration = durationMatch ? durationMatch[1] : '';
    const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
    const date = lines[lines.length - 1] || '';
    return { bvid, title, play, duration, date, url: 'https://www.bilibili.com/video/' + bvid };
  }),
  count: document.querySelectorAll('.upload-video-card').length
})
EVALEOF
```

---

### Step 9: 翻页并重复采集

```bash
# 点击下一页
agent-browser eval --stdin <<'EVALEOF'
const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('下一页'));
if (nextBtn) { nextBtn.click(); 'clicked'; } else { 'last_page'; }
EVALEOF

# 等待加载
agent-browser wait --load networkidle && agent-browser wait 8000

# 提取数据（重复 Step 8）
```

**注意**: 本次采集发现"下一页"点击后视频列表未更新，说明 B 站可能采用无限滚动或虚拟列表。

---

### Step 10: 保存 JSON 文件

```bash
# 创建输出目录
mkdir -p ~/Downloads/bilibili-video-list

# 使用 Write 工具写入 JSON
# 文件路径: ~/Downloads/bilibili-video-list/战国时代_姜汁汽水_pubdate_2026-04-07.json
```

---

### Step 11: 关闭浏览器

```bash
agent-browser close
```

---

## 关键技术要点

### 1. 页面选择器

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 视频卡片 | `.upload-video-card` | 主容器 |
| 视频链接 | `a[href*="bilibili.com/video/"]` | 提取 BV 号 |
| 视频标题 | `.bili-video-card__title a` 或 `.video-title` | 标题文本 |
| 关闭按钮 | `.bili-mini-close-icon` | 登录弹窗关闭 |
| 下一页按钮 | `button:has-text("下一页")` | 翻页 |

### 2. 数据提取正则

```javascript
// BV 号
const bvid = (href.match(/BV[\w]+/) || [''])[0] || '';

// 播放量 (匹配 "数字万?\n数字\n" 模式)
const playMatch = rawText.match(/([\d.]+万?)\n\d+\n/);
const play = playMatch ? playMatch[1] : '';

// 时长 (HH:MM:SS 或 MM:SS)
const durationMatch = rawText.match(/(\d{1,2}:\d{2}(?::\d{2})?)/);
const duration = durationMatch ? durationMatch[1] : '';

// 日期 (取最后一行，兼容多种格式)
const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
const date = lines[lines.length - 1] || '';
```

### 3. 翻页策略

**当前方案**: 点击"下一页"按钮

```javascript
const nextBtn = Array.from(document.querySelectorAll('button'))
  .find(b => b.textContent.includes('下一页'));
if (nextBtn) { nextBtn.click(); 'clicked'; } else { 'last_page'; }
```

**问题**: 点击后视频列表未更新，可能原因：
- B 站采用虚拟列表
- 需要滚动触发加载
- AJAX 请求需要额外等待

**替代方案**: 滚动加载

```javascript
window.scrollTo(0, document.documentElement.scrollHeight);
```

---

## 输出格式

```json
{
  "uploader": "战国时代_姜汁汽水",
  "uid": 1039025435,
  "order": "pubdate",
  "totalVideos": 80,
  "collectedAt": "2026-04-07",
  "videos": [
    {
      "bvid": "BV1kUDcBKEUp",
      "title": "总体思路，关键时间，真假TACO，美国能否加息？（补）",
      "play": "2.7万",
      "duration": "21:15",
      "date": "2小时前",
      "url": "https://www.bilibili.com/video/BV1kUDcBKEUp"
    }
  ]
}
```

---

## 常见问题

### Q1: 为什么必须用 --headed 模式？

A: 无头模式 `navigator.webdriver=true`，B 站检测后返回 -352 风控页面。

### Q2: 翻页后视频列表不变怎么办？

A: 尝试滚动加载方案：
```javascript
window.scrollTo(0, document.documentElement.scrollHeight);
await new Promise(r => setTimeout(r, 3000));
```

### Q3: 播放量显示为空？

A: 检查正则表达式 `([\d.]+万?)\n\d+\n`，确保匹配播放量+弹幕数的模式。

### Q4: 日期格式不统一？

A: 使用 `innerText` 最后一行，自动兼容"2小时前"、"04-01"、"2025-12-31"等格式。

---

## 优化建议

1. **分页策略优化**: 结合滚动和翻页两种方式，确保数据完整性
2. **重复数据去重**: 使用 BV 号作为唯一标识，合并重复视频
3. **错误重试机制**: 遇到风控时自动重试，增加等待时间
4. **进度显示**: 实时输出采集进度（当前页/总页数）

---

## 相关文档

- [API 模式说明](./api-mode.md)
- [UID 解析方法](./uid-resolution.md)
- [反风控策略](./anti-detection.md)
- [数据提取脚本](./extract-scripts.md)
