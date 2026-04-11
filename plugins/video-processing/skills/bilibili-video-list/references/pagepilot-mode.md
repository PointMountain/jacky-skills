# PagePilot 模式参考文档

> 通过 PagePilot MCP 工具（`mcp__page-pilot__*`）操控用户 Chrome 浏览器获取 B 站视频列表。
> 核心优势：复用浏览器登录状态 + `browser_execute_paginated` 一次性全量提取。

## 连接检查

```javascript
// 工具：browser_ping
// 成功返回 Bridge/Extension 连接信息
// 失败则告知用户：
//   1. 确认 Chrome 浏览器已打开
//   2. 确认 PagePilot 扩展已安装并启用
//   3. 打开任意网页，在 SidePanel 中点击「连接 MCP」
```

## B 站空间页选择器清单

以下选择器经过实战验证（2026-04-09）：

| 用途 | 选择器 | 备注 |
|------|--------|------|
| 视频卡片 | `.upload-video-card` | 稳定 |
| UP 主名称 | `#h-name, .nickname` | 双选择器备用 |
| 分页区域 | `.vui_pagenation` | B 站新版分页组件 |
| 下一页按钮 | `.vui_pagenation--btn-side:not(.vui_button--disabled):last-of-type` | 跳过禁用状态的"上一页" |
| 页码按钮 | `.vui_pagenation--btn-num` | 页码 1,2,3... |
| 总页数文本 | `.vui_pagenation-go__count` | 如"共 7 页 / 279 个" |
| 登录弹窗关闭 | `.bili-mini-close-icon` | 点击关闭 |
| 搜索结果用户链接 | `a[href*="space.bilibili.com"]` | UID 解析用 |
| 排序按钮 | `.radio-filter__item` | 最新/最多播放/最多收藏 |

## UID 解析（名字 → UID）

当输入是 UP 主名字时，通过 PagePilot 浏览器搜索解析 UID：

```javascript
// Step 1: 导航到搜索页
// browser_navigate({ url: "https://search.bilibili.com/upuser?keyword=" + encodeURIComponent(name) })

// Step 2: 验证导航（关键！）
// browser_get_url() → 确认 URL 包含 search.bilibili.com

// Step 3: 提取 UID
// browser_execute_script({ code: ... })
const links = document.querySelectorAll('a[href*="space.bilibili.com"]');
const results = [];
links.forEach(a => {
  results.push({ href: a.href, text: a.textContent.trim().substring(0, 50) });
});
return JSON.stringify(results.slice(0, 5));
```

从返回的 `href` 中提取 UID：`https://space.bilibili.com/3546869816887527` → `3546869816887527`。

**注意**：搜索结果可能有多个同名用户，根据 `text` 字段中的粉丝数和视频数辅助判断。

## 导航校验模式（必须执行）

`browser_navigate` 返回成功**不代表**页面确实导航到了目标 URL。必须校验：

```javascript
// 导航后立即验证
// browser_get_url() → 检查 URL 是否包含目标域名

// 错误模式：导航返回成功但页面在 github.com（实际未导航）
// 正确模式：get_url 返回包含 bilibili.com 的 URL
```

## 视频提取脚本

### 单页提取

```javascript
const cards = document.querySelectorAll('.upload-video-card');
const videos = [];
cards.forEach(card => {
  const link = card.querySelector('a[href*="bilibili.com/video/"], a[href*="/video/"]');
  const href = link ? link.href : '';
  const bvid = (href.match(/BV[\w]+/) || [''])[0] || '';
  const titleEl = card.querySelector('.bili-video-card__title a, .video-title, .title');
  const title = titleEl ? titleEl.textContent.trim() : '';
  const rawText = card.innerText;
  const playMatch = rawText.match(/([\d.]+万?)\s*\n?\d+\s*\n/);
  const play = playMatch ? playMatch[1] : '';
  const durationMatch = rawText.match(/(\d{1,2}:\d{2}(?::\d{2})?)/);
  const duration = durationMatch ? durationMatch[1] : '';
  const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
  const date = lines[lines.length - 1] || '';
  videos.push({ bvid, title, play, duration, date, url: 'https://www.bilibili.com/video/' + bvid });
});
return videos;
```

### 关闭弹窗 + 获取 UP 主信息

```javascript
document.querySelector('.bili-mini-close-icon')?.click();
return JSON.stringify({
  name: document.querySelector('#h-name, .nickname')?.textContent?.trim() || '',
  videoCount: document.querySelectorAll('.upload-video-card').length,
  hasError: document.body?.innerText?.includes('-352')
});
```

### 探测分页信息

```javascript
const pager = document.querySelector('.vui_pagenation');
if (!pager) return JSON.stringify({ hasPagination: false, totalPages: 1 });
const countText = document.querySelector('.vui_pagenation-go__count')?.textContent || '';
const pageMatch = countText.match(/共\s*(\d+)\s*页/);
return JSON.stringify({
  hasPagination: true,
  totalPages: pageMatch ? parseInt(pageMatch[1]) : 1,
  nextSelector: '.vui_pagenation--btn-side:not(.vui_button--disabled):last-of-type'
});
```

## 分页配置

### browser_execute_paginated 参数

```json
{
  "code": "// 上面的「单页提取」脚本",
  "pagination": "{\"mode\":\"click\",\"nextButtonSelector\":\".vui_pagenation--btn-side:not(.vui_button--disabled):last-of-type\",\"maxPages\":50,\"waitMs\":3000}"
}
```

### 关键参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| mode | `click` | 点击"下一页"按钮翻页 |
| nextButtonSelector | `.vui_pagenation--btn-side:not(.vui_button--disabled):last-of-type` | **已验证的正确选择器** |
| maxPages | 50 | 安全上限，实际会在最后一页自动停止 |
| waitMs | 3000 | 翻页后等待 3 秒让 SPA 渲染 |

### 自动停止机制

`browser_execute_paginated` 内置以下停止条件，无需手动处理：
- 空页面（`items.length === 0`）
- 重复页面（首项与上一页重复）
- 选择器无效
- 翻页失败
- 达到 maxPages

## 排序切换

```javascript
// 非默认排序时使用
const items = document.querySelectorAll('.radio-filter__item');
let clicked = null;
items.forEach(item => {
  if (item.textContent.trim().includes('最多播放')) {  // 或 '最多收藏'
    item.click();
    clicked = item.textContent.trim();
  }
});
return JSON.stringify({ clicked });
```

切换排序后需要等待 3 秒再执行提取。建议排序后再执行 `browser_execute_paginated`。

## 输出格式

PagePilot 模式的 JSON 输出 `source` 字段标记为 `"pagepilot"`，字段与 CDP/agent-browser 一致（播放量为近似值）。

```json
{
  "uploader": "王站岗",
  "uid": "3546869816887527",
  "totalVideos": 279,
  "pages": 7,
  "source": "pagepilot",
  "fetchedAt": "2026-04-09",
  "videos": [
    {
      "bvid": "BV1Y7D7BaEpH",
      "title": "视频标题",
      "play": "2325",
      "duration": "01:08",
      "date": "5小时前",
      "url": "https://www.bilibili.com/video/BV1Y7D7BaEpH"
    }
  ]
}
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| browser_ping 失败 | 扩展未连接 | 用户在 SidePanel 点击「连接 MCP」 |
| navigate 成功但 get_url 不对 | 页面未实际跳转 | 重试 navigate，或检查是否有弹窗阻塞 |
| execute_script 返回 CSP 错误 | 页面不在 B 站 | 检查 get_url，重新导航 |
| execute_paginated 只获取 1 页 | nextButtonSelector 错误 | 先用 execute_script 探测分页 DOM |
| -352 风控 | 浏览器未登录 B 站 | 在 Chrome 中登录 bilibili.com 后重试 |
