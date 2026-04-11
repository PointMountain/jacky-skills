---
name: bilibili-video-list
description: "获取 B 站 UP 主完整视频列表。四级降级：API（Cookie 自动提取）→ PagePilot（复用浏览器+分页提取）→ CDP（Chrome DevTools）→ agent-browser（兜底）。触发词：获取UP主视频列表、bilibili-video-list、B站视频列表、热门视频。"
---

<role>
你是 B 站 UP 主视频列表采集助手，支持 API、PagePilot、CDP 和 agent-browser 四种模式获取视频列表。优先使用 API 模式（自动从浏览器提取 Cookie），其次 PagePilot 模式（复用浏览器 + 自动分页提取），再次 CDP 模式（Chrome DevTools MCP），最后 agent-browser（兜底）。
</role>

<purpose>
给定 UP 主的 UID、空间 URL 或名字，获取视频元数据（BV 号、标题、播放量、时长、日期），输出 JSON 文件和终端预览。
</purpose>

<trigger>
```text
触发词/示例：
- 获取这个 UP 主的所有视频列表
- 获取 https://space.bilibili.com/1039025435 的视频列表
- 列出 UP 主 1039025435 的全部视频
- 获取这个 UP 主播放量最高的视频
- 按收藏数排序导出这个 UP 主的视频
- bilibili-video-list
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>bilibili-video-list</name>
    <owner>video-processing</owner>
    <requires>python3 + requests | PagePilot MCP | Chrome DevTools MCP | agent-browser</requires>
    <checkpoints>
      <checkpoint order="1">采集模式确定（API / PagePilot / CDP / agent-browser）</checkpoint>
      <checkpoint order="2">UP 主 UID 解析完成</checkpoint>
      <checkpoint order="3">视频数据采集完成，JSON 文件已保存</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>纯数据采集，不做字幕提取、视频下载或笔记写入</constraint>
      <constraint>API 模式需要 SESSDATA Cookie（配置方式见 references/api-mode.md）</constraint>
      <constraint>PagePilot 模式需要 PagePilot Chrome 扩展已连接（SidePanel 中点击「连接 MCP」）</constraint>
      <constraint>CDP 模式需要 Chrome DevTools MCP 服务已连接到用户的 Chrome 浏览器</constraint>
      <constraint>agent-browser 模式必须使用 --headed，无头模式会触发 -352 风控</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>获取 UP 主完整视频列表并保存为 JSON 文件。</gsd:goal>

  <gsd:phase name="mode-select" order="1">
    <gsd:step>优先尝试 API 模式：运行 python3 脚本（自动从 Chrome Cookie 数据库提取 SESSDATA）。</gsd:step>
    <gsd:step>如果 API 模式成功 → 直接进入导出阶段。</gsd:step>
    <gsd:step>如果脚本退出码为 2（NO_COOKIE）或执行失败 → 尝试 PagePilot 模式（browser_ping 检查连接）。</gsd:step>
    <gsd:step>如果 PagePilot 未连接 → 尝试 CDP 模式（Chrome DevTools MCP）。</gsd:step>
    <gsd:step>如果 CDP 模式不可用（MCP 未连接）→ 降级到 agent-browser 浏览器模式（最后兜底）。</gsd:step>
    <gsd:step>如果所有浏览器模式均不可用 → AskUserQuestion 询问用户：提供 UID / 连接 PagePilot / 更新 Cookie。</gsd:step>
    <gsd:checkpoint>采集模式确定</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="parse" order="2">
    <gsd:step>从输入中提取 UID / URL / 名字，确定排序方式和数量限制。</gsd:step>
    <gsd:step>排序参数：未指定→pubdate，"播放量"/"热门"→click，"收藏"→stow。</gsd:step>
    <gsd:step>如果输入是名字且非 API 模式 → 用浏览器搜索 UID（见 references/uid-resolution.md 或 pagepilot-mode.md）。</gsd:step>
    <gsd:checkpoint>UID + 参数解析完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="api-collect" order="3" condition="API 模式">
    <gsd:step>运行 python3 脚本（见 API 模式执行流程）。</gsd:step>
    <gsd:step>检查退出码：0=成功 → 进入导出；2=NO_COOKIE → 降级到 PagePilot 模式；其他=错误。</gsd:step>
    <gsd:checkpoint>数据采集完成或降级</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="pagepilot-collect" order="3" condition="PagePilot 模式（推荐降级方案）">
    <gsd:step>检查连接：browser_ping。</gsd:step>
    <gsd:step>UID 解析（名字时）：browser_navigate 搜索页 → browser_get_url 验证 → browser_execute_script 提取 UID。</gsd:step>
    <gsd:step>导航空间页：browser_navigate → browser_get_url 验证（关键！）。</gsd:step>
    <gsd:step>初始化：browser_execute_script 关闭弹窗 + 等待视频卡片。</gsd:step>
    <gsd:step>探测分页：browser_execute_script 获取总页数和 next 按钮选择器。</gsd:step>
    <gsd:step>全量提取：browser_execute_paginated 一次性获取所有页面数据。</gsd:step>
    <gsd:step>保存 JSON：Write 工具写入 ~/Downloads/bilibili-video-list/。</gsd:step>
    <gsd:checkpoint>数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="cdp-collect" order="3" condition="CDP 模式（PagePilot 不可用时）">
    <gsd:step>检查 CDP 连接：调用 mcp__chrome-devtools__list_pages。</gsd:step>
    <gsd:step>**关键检查**：如果返回只有 about:blank → 连接的是独立实例，告知用户需要用 --remote-debugging-port=9222 启动 Chrome，并停止当前操作。</gsd:step>
    <gsd:step>如果返回多个页面（非 about:blank）→ 确认连接到用户浏览器，继续。</gsd:step>
    <gsd:step>如 CDP 不可用或连接独立实例 → 降级到 agent-browser 模式。</gsd:step>
    <gsd:step>导航到空间页，等待 SPA 渲染，关闭弹窗，提取数据翻页。</gsd:step>
    <gsd:checkpoint>CDP 数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="browser-collect" order="3" condition="agent-browser 模式（最后兜底）">
    <gsd:step>用 agent-browser --headed 模式打开空间页，等待 8 秒（SPA 渲染）。</gsd:step>
    <gsd:step>关闭登录弹窗，验证视频卡片数量。</gsd:step>
    <gsd:step>如遇 -352 风控，按 references/anti-detection.md 处理。</gsd:step>
    <gsd:step>提取视频数据，翻页重复。</gsd:step>
    <gsd:checkpoint>数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="export" order="4">
    <gsd:step>JSON 已保存到 ~/Downloads/bilibili-video-list/，终端输出表格预览。</gsd:step>
    <gsd:step>如需进一步处理，建议 bilibili-to-obsidian 或 bilibili-batch。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Bilibili Video List — B 站 UP 主视频列表采集

> 四级降级模式：API（自动提取 Cookie）→ PagePilot（复用浏览器+自动分页）→ CDP（Chrome DevTools）→ agent-browser（兜底）。PagePilot 模式零风控 + 自动分页提取，是 API 失败后的最优降级方案。

## 模式选择

### 四级降级策略

```
API 模式（自动提取 Cookie）→ 成功 → 导出
  ↓ 失败（NO_COOKIE / 执行错误）
PagePilot 模式（browser_ping 检查）→ 成功 → 导出
  ↓ 失败（扩展未连接）
CDP 模式（Chrome DevTools MCP）→ 成功 → 导出
  ↓ 失败（MCP 未连接）
agent-browser 模式（兜底，高风险）
```

**决策逻辑**：

| 优先级 | 模式 | 触发条件 | 优势 | 劣势 |
|--------|------|----------|------|------|
| 1 | **API 模式** | Cookie 可用 | 最快、数据最精确、额外字段 | 需要 Cookie |
| 2 | **PagePilot** | PagePilot 扩展已连接 | 零风控 + 自动分页 + 一步全量提取 | 数据近似值 |
| 3 | **CDP 模式** | Chrome DevTools MCP 已连接 | 零风控、复用登录状态 | 需手动翻页、需 MCP 服务 |
| 4 | **agent-browser** | 以上均不可用 | 无需任何配置 | 频繁触发 -352 风控 |

> **API 模式自动提取**：脚本会自动从 Chrome Cookie 数据库提取 SESSDATA（macOS），无需手动配置。
> **PagePilot 模式**：通过 `mcp__page-pilot__*` 工具操控 Chrome 扩展，复用浏览器登录状态，`browser_execute_paginated` 一次调用完成全量提取。详见 [pagepilot-mode.md](references/pagepilot-mode.md)。
> **CDP 模式**：通过 `mcp__chrome-devtools__*` 工具连接 Chrome，复用登录状态。详见 [cdp-mode.md](references/cdp-mode.md)。

---

## 输入解析

| 输入格式 | 提取方式 | 示例 |
|----------|----------|------|
| 空间 URL | 正则提取数字 | `https://space.bilibili.com/1039025435` → UID `1039025435` |
| 纯数字 | 直接使用 | `1039025435` |
| UP 主名字 | API 搜索或浏览器搜索 | "摩的司机徐师傅" |

### 排序参数

| 用户说法 | 排序方式 |
|----------|----------|
| "最新"/"按时间"/"默认" | `pubdate` |
| "播放量"/"热门"/"最多播放" | `click` |
| "收藏"/"最多收藏" | `stow` |
| 未指定 | `pubdate` |

### 数量限制

- 未指定：获取全部 | "前 N 个"：仅获取前 N 个 | "第 N 页到第 M 页"：指定范围

---

## API 模式执行流程（推荐）

> 前提：已配置 SESSDATA Cookie。详见 [api-mode.md](references/api-mode.md)。

**脚本路径发现**（脚本可能在 jacky-skills 仓库中）：

```bash
# 方法 1：直接使用已知路径
SCRIPT_PATH="/Users/jiashengwang/jacky-github/jacky-skills/plugins/video-processing/skills/bilibili-video-list/scripts/api-fetch.py"

# 方法 2：动态发现
SCRIPT_PATH=$(find /Users/jiashengwang/jacky-github -path "*/bilibili-video-list/scripts/api-fetch.py" 2>/dev/null | head -1)
```

### 直接运行

```bash
# 基础用法
python3 "$SCRIPT_PATH" --mid ${UID} --order ${ORDER:-pubdate}

# 按播放量排序
python3 "$SCRIPT_PATH" --mid ${UID} --order click

# 通过名字搜索
python3 "$SCRIPT_PATH" --name "UP主名字" --order click

# 限制数量
python3 "$SCRIPT_PATH" --mid ${UID} --limit 50

# 指定 Cookie（一次性）
python3 "$SCRIPT_PATH" --mid ${UID} --sessdata "YOUR_SESSDATA"

# 缓存相关
python3 "$SCRIPT_PATH" --mid ${UID} --order pubdate         # 首次调用 → API，后续 24h 内读缓存
python3 "$SCRIPT_PATH" --mid ${UID} --no-cache              # 强制刷新，忽略缓存
python3 "$SCRIPT_PATH" --mid ${UID} --cache-ttl 3600        # 自定义缓存有效期 1 小时
```

### 脚本特性

- **自动 WBI 签名**：内置混淆表，无需手动处理
- **自动翻页**：每页 50 条，自动获取全部
- **UID 解析**：支持纯数字、空间 URL、UP 主名字（自动搜索）
- **多字段输出**：播放量（精确值）、评论数、收藏数、弹幕数、简介
- **终端预览**：自动显示前 20 个视频的表格
- **缓存机制**：默认缓存 24 小时，重复查询同一 UP 主直接读缓存

---

## PagePilot 模式执行流程（推荐降级方案）

> API 模式失败后的首选降级方案。通过 PagePilot MCP 工具操控 Chrome 扩展，复用浏览器登录状态，`browser_execute_paginated` 一次调用完成全量提取。详见 [pagepilot-mode.md](references/pagepilot-mode.md)。

### Step 1: 检查连接

```
browser_ping()
```

失败则告知用户在 SidePanel 中点击「连接 MCP」，或降级到 CDP/agent-browser。

### Step 2: UID 解析（输入是名字时）

```
browser_navigate({ url: "https://search.bilibili.com/upuser?keyword=" + encodeURIComponent(name) })
browser_get_url()  // 验证导航成功（关键！）
```

```javascript
// browser_execute_script
const links = document.querySelectorAll('a[href*="space.bilibili.com"]');
const results = [];
links.forEach(a => {
  results.push({ href: a.href, text: a.textContent.trim().substring(0, 50) });
});
return JSON.stringify(results.slice(0, 5));
```

从返回的 `href` 中提取第一个匹配的 UID。

### Step 3: 导航到空间页

```
browser_navigate({ url: "https://space.bilibili.com/${UID}/upload/video" })
browser_get_url()  // 验证 URL 包含 space.bilibili.com（关键！）
```

> **关键**：`browser_navigate` 返回成功不代表页面确实导航到了目标 URL。必须用 `browser_get_url` 验证。

### Step 4: 初始化页面

```javascript
// browser_execute_script — 关闭弹窗 + 等待视频卡片
document.querySelector('.bili-mini-close-icon')?.click();
return JSON.stringify({
  name: document.querySelector('#h-name, .nickname')?.textContent?.trim() || '',
  videoCount: document.querySelectorAll('.upload-video-card').length
});
```

如果 `videoCount === 0`，等待 3 秒后重试。如果页面包含 `-352` 则为风控拦截。

### Step 5: 探测分页信息

```javascript
// browser_execute_script — 获取总页数
const countText = document.querySelector('.vui_pagenation-go__count')?.textContent || '';
const pageMatch = countText.match(/共\s*(\d+)\s*页/);
return JSON.stringify({
  hasPagination: !!document.querySelector('.vui_pagenation'),
  totalPages: pageMatch ? parseInt(pageMatch[1]) : 1
});
```

### Step 6: 全量提取（核心）

```
browser_execute_paginated({
  code: "// 视频提取脚本（见下方）",
  pagination: '{"mode":"click","nextButtonSelector":".vui_pagenation--btn-side:not(.vui_button--disabled):last-of-type","maxPages":50,"waitMs":3000}'
})
```

**视频提取脚本**：

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

`browser_execute_paginated` 自动处理翻页、重复检测、空页面停止，一次调用返回所有页面数据。

### Step 7: 保存结果

将返回的 `data` 数组保存为 JSON：

```python
# python3 解析保存
output = {
  "uploader": name,
  "uid": uid,
  "totalVideos": len(videos),
  "pages": result["pages"],
  "source": "pagepilot",
  "fetchedAt": "2026-04-09",
  "videos": videos
}
# Write 到 ~/Downloads/bilibili-video-list/{UP主名}_{排序}_{日期}.json
```

---

## 数据模式对比

| 字段 | API 模式 | PagePilot | CDP / agent-browser |
|------|----------|-----------|---------------------|
| 播放量 | `16310000`（精确值） | `1631.0万`（近似值） | `1631.0万`（近似值） |
| 评论数 | 有 | 无 | 无 |
| 收藏数 | 有 | 无 | 无 |
| 弹幕数 | 有 | 无 | 无 |
| 简介 | 有 | 无 | 无 |
| BV 号 | 有 | 有 | 有 |
| 时长 | 有 | 有 | 有 |
| 日期 | 有 | 有 | 有 |
| 翻页方式 | API 自动 | **自动（execute_paginated）** | 手动循环 |
| 风控风险 | 无 | **无** | 无 / **高** |

---

## CDP 模式执行流程（三级降级）

> PagePilot 和 API 均不可用时使用。通过 Chrome DevTools MCP 连接用户已打开的 Chrome 浏览器。详见 [cdp-mode.md](references/cdp-mode.md)。

### Step 0: 检查 CDP 连接

调用 `mcp__chrome-devtools__list_pages`，确认能连接到用户的 Chrome。

**⚠️ 关键检查**：

| 返回结果 | 含义 | 处理方式 |
|----------|------|----------|
| 多个页面（非 about:blank） | ✅ 连接到用户浏览器 | 可以使用 CDP 模式 |
| 只有 `about:blank` | ❌ 连接到独立实例 | **需要用户启动调试模式** |
| 报错 | ❌ MCP 未连接 | 降级到 agent-browser |

### 启动调试模式 Chrome

**macOS：**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Windows：**
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### 执行步骤

1. 导航到空间页：`mcp__chrome-devtools__navigate_page`
2. 等待加载：`mcp__chrome-devtools__wait_for(text=["upload-video-card"])`
3. 关闭弹窗 + 验证：`mcp__chrome-devtools__evaluate_script`
4. 切换排序（非默认时点击 `.radio-filter__item`）
5. 提取数据并手动翻页循环（详见 [cdp-mode.md](references/cdp-mode.md)）
6. 保存 JSON（`source` 标记为 `"cdp"`）

---

## 缓存机制

API 模式自动缓存获取结果，避免重复请求。

| 项目 | 说明 |
|------|------|
| 缓存路径 | `~/.cache/bilibili-video-list/{uid}.json` |
| 缓存键 | UID + 排序方式 |
| 默认 TTL | 24 小时（86400 秒） |
| 旧版输出 | 同时写入 `~/Downloads/bilibili-video-list/`（向后兼容） |

### 清理缓存

```bash
rm -rf ~/.cache/bilibili-video-list/
rm ~/.cache/bilibili-video-list/{UID}.json
```

---

## agent-browser 模式执行流程（最后兜底）

> 所有模式均不可用时的最后手段。必须用 --headed 模式，风控风险高。

### Step 1: 打开空间页（必须 --headed）

```bash
agent-browser open --headed "https://space.bilibili.com/${UID}/upload/video"
agent-browser wait --load networkidle && agent-browser wait 8000
```

> **为什么必须 --headed**：无头模式 `navigator.webdriver=true`，B 站检测后返回 -352 风控。详见 [anti-detection.md](references/anti-detection.md)。

### Step 2: 关闭弹窗 + 验证加载

```bash
agent-browser eval 'document.querySelector(".bili-mini-close-icon")?.click(); "done"'
agent-browser wait 3000
```

### Step 3-7: 提取、翻页、保存

详见 [extract-scripts.md](references/extract-scripts.md) 和 [browser-mode-workflow.md](references/browser-mode-workflow.md)。

---

## Cookie 配置指南

### 快速配置（推荐）

1. 打开浏览器登录 [bilibili.com](https://www.bilibili.com)
2. 按 F12 → Application → Cookies → `https://www.bilibili.com`
3. 复制 `SESSDATA` 的值
4. 保存到配置文件：

```bash
mkdir -p ~/.config
cat > ~/.config/bilibili-cookies.json << EOF
{
  "SESSDATA": "用户提供的 SESSDATA 值"
}
EOF
chmod 600 ~/.config/bilibili-cookies.json
```

> 详细说明见 [api-mode.md](references/api-mode.md)。

---

## 输出文件

- **路径**：`~/Downloads/bilibili-video-list/{UP主名}_{排序}_{日期}.json`
- **格式**：见 [api-mode.md](references/api-mode.md) 中的 JSON 输出格式
- **终端预览**：>20 个视频时只显示前 20 个

## 边界情况

| 情况 | 处理方式 |
|------|----------|
| Cookie 过期 | API 返回错误，自动降级到 PagePilot 模式 |
| Chrome Cookie 自动提取失败 | 降级到 PagePilot 模式 |
| PagePilot 扩展未连接 | 降级到 CDP 模式或 AskUserQuestion |
| navigate 成功但页面在错误 URL | **必须 browser_get_url 验证**，重新导航 |
| 分页选择器不匹配 | 先用 execute_script 探测分页 DOM 再写选择器 |
| CDP 连接独立实例（about:blank） | 告知用户需要用 `--remote-debugging-port=9222` 启动 Chrome |
| -352 风控（agent-browser） | 必须用 --headed 模式，详见 [anti-detection.md](references/anti-detection.md) |
| -352 风控（PagePilot/CDP） | 极少发生，检查浏览器是否已登录 bilibili |
| 登录弹窗 | 自动关闭弹窗后继续 |
| 视频数 999+ | API 自动翻页；PagePilot execute_paginated 自动处理 |
| UP 主名字搜索 | API 自动搜索；PagePilot/CDP 浏览器搜索 |
| 缓存文件损坏 | 忽略缓存，重新获取 |

## 免责声明

> [!warning] 本 Skill 仅用于个人学习和研究目的。因不当使用造成的法律后果由使用者自行承担。
