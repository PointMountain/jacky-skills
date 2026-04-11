# CDP 模式 — Chrome DevTools Protocol

> 通过 `mcp__chrome-devtools__*` 工具连接用户已打开的 Chrome 浏览器，复用登录状态，零风控风险。

## ⚠️ 重要：CDP 必须连接用户实际浏览器

**CDP 模式的前提是连接到用户正在使用的 Chrome，而不是一个独立实例。**

### 如何判断连接状态

调用 `mcp__chrome-devtools__list_pages` 后：

| 返回结果 | 浏览器类型 | 是否可用 |
|----------|------------|----------|
| 多个页面（bilibili、google 等） | ✅ 用户浏览器 | 可用 |
| 只有 `about:blank` | ❌ 独立实例 | **不可用** |
| 只有空白页 | ❌ 独立实例 | **不可用** |

**如果返回 `about:blank`，说明 MCP 连接的是一个独立的 Chrome 实例，没有用户的登录态。此时必须：**
1. 停止当前操作
2. 告知用户需要启动调试模式的 Chrome
3. 不要尝试绕路（会触发风控）

---

## 为什么用 CDP 模式

| 对比项 | agent-browser | CDP 模式 |
|--------|---------------|----------|
| 浏览器实例 | 新启动（无登录状态） | 复用用户浏览器（已登录） |
| 风控检测 | 高风险（-352 频繁触发） | 无风险（真实浏览器环境） |
| Cookie | 需要手动配置 | 自动复用 |
| 依赖 | agent-browser 工具 | Chrome DevTools MCP 服务 |
| webdriver 标记 | `navigator.webdriver=true` | 无此标记 |

## 前提条件

### 1. 用户 Chrome 以调试模式启动

**macOS：**
```bash
# 关闭所有 Chrome 窗口后执行
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Windows：**
```bash
# 关闭所有 Chrome 后执行
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### 2. Chrome DevTools MCP 配置正确

确保 MCP 配置的 `cdpUrl` 指向调试端口：
```json
{
  "cdpUrl": "http://localhost:9222"
}
```

### 3. 在调试 Chrome 中登录 B 站

启动调试模式 Chrome 后，访问 bilibili.com 并登录。

### 检查连接

使用 `mcp__chrome-devtools__list_pages` 检查：

- ✅ 返回多个页面（非 about:blank）→ 连接到用户浏览器，可以使用
- ❌ 返回只有 `about:blank` → 连接到独立实例，需要用户按上述步骤配置
- ❌ 报错 → MCP 服务未连接，检查 MCP 配置

## 执行流程

### Step 1: 导航到空间页

```
mcp__chrome-devtools__navigate_page(
  type="url",
  url="https://space.bilibili.com/{UID}/upload/video"
)
```

### Step 2: 等待页面加载

```
mcp__chrome-devtools__wait_for(
  text=["upload-video-card"],
  timeout=15000
)
```

> SPA 页面需要较长等待时间，建议 15 秒。

### Step 3: 关闭登录弹窗（如有）

```
mcp__chrome-devtools__evaluate_script(
  function: () => {
    const closeBtn = document.querySelector(".bili-mini-close-icon");
    if (closeBtn) closeBtn.click();
    return { popupClosed: !!closeBtn };
  }
)
```

### Step 4: 验证页面状态

```
mcp__chrome-devtools__evaluate_script(
  function: () => {
    return {
      videoCount: document.querySelectorAll(".upload-video-card").length,
      uploaderName: document.querySelector("#h-name, .nickname")?.textContent?.trim() || "unknown",
      hasError: document.body?.innerText?.includes("-352")
    };
  }
)
```

- `videoCount > 0` → 继续采集
- `hasError: true` → 风控拦截（CDP 模式下极少发生）
- `videoCount === 0 && !hasError` → 检查是否"还没投过视频"

### Step 5: 切换排序（非默认时）

```
mcp__chrome-devtools__evaluate_script(
  function: () => {
    const items = document.querySelectorAll('.radio-filter__item');
    let clicked = null;
    items.forEach(item => {
      if (item.textContent.trim().includes('最多播放')) {  // 或 '最多收藏'
        item.click();
        clicked = item.textContent.trim();
      }
    });
    return { clicked };
  }
)
```

切换后等待 4 秒：
```
mcp__chrome-devtools__wait_for(text=["upload-video-card"], timeout=8000)
```

### Step 6: 提取视频数据

```
mcp__chrome-devtools__evaluate_script(
  function: () => {
    return {
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
    };
  }
)
```

### Step 7: 翻页

```
mcp__chrome-devtools__evaluate_script(
  function: () => {
    const nextBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('下一页'));
    if (nextBtn) {
      nextBtn.click();
      return { action: 'clicked' };
    }
    return { action: 'last_page' };
  }
)
```

返回 `last_page` 时停止。翻页后等待 3 秒再提取。

### Step 8: 保存结果

将所有页面数据合并为 JSON，使用 Write 工具保存到：
`~/Downloads/bilibili-video-list/{UP主名}_{排序}_{日期}.json`

## CDP 模式输出格式

```json
{
  "uploader": "UP主名称",
  "uid": "1039025435",
  "order": "click",
  "totalVideos": 416,
  "fetchedVideos": 416,
  "fetchedPages": 14,
  "fetchDate": "2026-04-07T10:00:00+08:00",
  "source": "cdp",
  "videos": [
    {
      "bvid": "BV1FkUxBbEcs",
      "title": "视频标题",
      "play": "1631.0万",
      "duration": "37:06",
      "date": "2025-11-27",
      "url": "https://www.bilibili.com/video/BV1FkUxBbEcs"
    }
  ]
}
```

> 注意：CDP 模式的播放量是页面显示的近似值（如 "1631.0万"），不如 API 模式精确。

## 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| list_pages 报错 | MCP 服务未连接到 Chrome | 检查 Chrome DevTools MCP 配置 |
| 页面空白 | SPA 未加载完成 | 增加等待时间到 15 秒 |
| 无视频卡片 | URL 格式错误或 UP 主无视频 | 检查 UID 是否正确 |
| 登录弹窗遮挡 | 未登录状态 | 关闭弹窗后继续（公开空间无需登录） |
