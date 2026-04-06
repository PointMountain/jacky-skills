---
name: bilibili-video-list
description: "获取 B 站 UP 主完整视频列表。支持 API（Cookie）和浏览器双模式，输出 JSON。触发词：获取UP主视频列表、bilibili-video-list、B站视频列表、热门视频。"
---

<role>
你是 B 站 UP 主视频列表采集助手，支持 API 和浏览器两种模式获取视频列表。
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
    <requires>python3 + requests | agent-browser</requires>
    <checkpoints>
      <checkpoint order="1">Cookie 可用性检查完成，确定采集模式</checkpoint>
      <checkpoint order="2">UP 主 UID 解析完成</checkpoint>
      <checkpoint order="3">视频数据采集完成，JSON 文件已保存</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>纯数据采集，不做字幕提取、视频下载或笔记写入</constraint>
      <constraint>API 模式需要 SESSDATA Cookie（配置方式见 references/api-mode.md）</constraint>
      <constraint>浏览器模式必须使用 --headed，无头模式会触发 -352 风控</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>获取 UP 主完整视频列表并保存为 JSON 文件。</gsd:goal>

  <gsd:phase name="mode-select" order="1">
    <gsd:step>优先尝试 API 模式：运行 python3 scripts/api-fetch.py。</gsd:step>
    <gsd:step>如果脚本退出码为 2（NO_COOKIE）或执行失败 → 自动降级到浏览器模式（agent-browser）。</gsd:step>
    <gsd:step>如果 API 模式成功 → 跳过浏览器模式，直接进入导出阶段。</gsd:step>
    <gsd:checkpoint>采集模式确定</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="parse" order="2">
    <gsd:step>从输入中提取 UID / URL / 名字，确定排序方式和数量限制。</gsd:step>
    <gsd:step>排序参数：未指定→pubdate，"播放量"/"热门"→click，"收藏"→stow。</gsd:step>
    <gsd:step>如果输入是名字且降级到浏览器模式 → 先用 references/uid-resolution.md 搜索 UID。</gsd:step>
    <gsd:checkpoint>UID + 参数解析完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="api-collect" order="3" condition="API 模式">
    <gsd:step>运行 python3 scripts/api-fetch.py（见 API 模式执行流程）。</gsd:step>
    <gsd:step>检查退出码：0=成功 → 进入导出；2=NO_COOKIE → 降级到浏览器模式；其他=错误。</gsd:step>
    <gsd:checkpoint>数据采集完成或降级到浏览器模式</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="browser-collect" order="3" condition="浏览器模式（API 降级）">
    <gsd:step>用 agent-browser --headed 模式打开空间页，等待 8 秒（SPA 渲染）。</gsd:step>
    <gsd:step>关闭登录弹窗，验证视频卡片数量。</gsd:step>
    <gsd:step>如遇 -352 风控，按 references/anti-detection.md 处理。</gsd:step>
    <gsd:step>切换排序（非默认时点击 `.radio-filter__item` 按钮）。</gsd:step>
    <gsd:step>提取视频数据（见 references/extract-scripts.md），翻页重复。</gsd:step>
    <gsd:checkpoint>数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="export" order="4">
    <gsd:step>JSON 已保存到 ~/Downloads/bilibili-video-list/，终端输出表格预览。</gsd:step>
    <gsd:step>如需进一步处理，建议 bilibili-to-obsidian 或 bilibili-batch。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Bilibili Video List — B 站 UP 主视频列表采集

> 支持双模式：API（Cookie，推荐）和浏览器（兜底）。API 模式速度快、数据精确、无风控风险。

## 模式选择

### 检查 Cookie 可用性

```bash
# 检查环境变量
echo $BILIBILI_SESSDATA

# 检查配置文件
cat ~/.config/bilibili-cookies.json 2>/dev/null
```

**决策逻辑**：

| 条件 | 模式 | 优势 |
|------|------|------|
| Cookie 可用 | **API 模式** | 快速、精确、额外字段（评论/收藏/弹幕数） |
| Cookie 不可用 | **浏览器模式**（自动降级） | 无需登录，但有风控风险 |

> **降级机制**：优先尝试 API 模式（`api-fetch.py`），如果脚本输出 `NO_COOKIE` 并以退出码 2 退出，自动降级到 agent-browser 浏览器模式。

> **推荐**：配置 Cookie 后使用 API 模式。获取方式见 [api-mode.md](references/api-mode.md)。

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

脚本位置：`plugins/video-processing/skills/bilibili-video-list/scripts/api-fetch.py`

### 直接运行

```bash
SCRIPT_PATH="plugins/video-processing/skills/bilibili-video-list/scripts/api-fetch.py"

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
- **缓存机制**：默认缓存 24 小时，重复查询同一 UP 主直接读缓存，跳过 API 调用

### API 与浏览器模式数据对比

| 字段 | API 模式 | 浏览器模式 |
|------|----------|------------|
| 播放量 | `16310000`（精确值） | `1631.0万`（近似值） |
| 评论数 | 有 | 无 |
| 收藏数 | 有 | 无 |
| 弹幕数 | 有 | 无 |
| 简介 | 有 | 无 |
| BV 号 | 有 | 有 |
| 时长 | 有 | 有 |
| 日期 | 有 | 有 |

---

## 缓存机制

API 模式自动缓存获取结果，避免重复请求。

| 项目 | 说明 |
|------|------|
| 缓存路径 | `~/.cache/bilibili-video-list/{uid}.json` |
| 缓存键 | UID + 排序方式 |
| 默认 TTL | 24 小时（86400 秒） |
| 旧版输出 | 同时写入 `~/Downloads/bilibili-video-list/`（向后兼容） |

### 缓存命中条件

所有条件同时满足时命中缓存：

1. 缓存文件存在且可解析
2. `cacheExpiresAt` 未过期
3. 缓存中的 `order` 与请求的排序方式一致

### 命中 vs 未命中

| 场景 | 行为 |
|------|------|
| 缓存命中 | 跳过 API，直接读文件，`source` 字段标记为 `"cache"` |
| 缓存过期 / 不存在 | 调用 API，更新缓存 |
| 排序方式不同 | 缓存未命中，重新获取 |
| `--no-cache` | 忽略缓存，始终调 API |

### 清理缓存

```bash
# 清理全部缓存
rm -rf ~/.cache/bilibili-video-list/

# 清理单个 UP 主
rm ~/.cache/bilibili-video-list/{UID}.json
```

---

## 浏览器模式执行流程（兜底）

> 无 Cookie 时的备选方案。必须用 --headed 模式。

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
agent-browser eval 'JSON.stringify({
  videoCount: document.querySelectorAll(".upload-video-card").length,
  hasError: document.body?.innerText?.includes("-352")
})'
```

- `videoCount > 0` → 继续采集
- `hasError: true` → 风控拦截，见 [anti-detection.md](references/anti-detection.md)
- `videoCount === 0 && !hasError` → 检查是否显示"还没投过视频"

### Step 3: 获取 UP 主名称

```bash
agent-browser eval 'document.querySelector("#h-name, .nickname")?.textContent?.trim() || "unknown"'
```

### Step 4: 切换排序（非默认时）

排序按钮在 `.radio-filter__item` 中（不是 button，是 div）：

```bash
agent-browser eval --stdin <<'EVALEOF'
const items = document.querySelectorAll('.radio-filter__item');
items.forEach(item => {
  if (item.textContent.trim().includes('最多播放')) item.click();  // 或 '最多收藏'
});
'done'
EVALEOF
agent-browser wait 4000
```

### Step 5: 提取视频数据

使用优化后的提取脚本（修复了时长/日期丢失问题）：

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

### Step 6: 翻页

```bash
agent-browser eval --stdin <<'EVALEOF'
const nextBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('下一页'));
if (nextBtn) { nextBtn.click(); 'clicked'; } else { 'last_page'; }
EVALEOF
agent-browser wait 3000
```

返回 `last_page` 时停止翻页。

### Step 7: 保存 + 关闭

```bash
mkdir -p ~/Downloads/bilibili-video-list
# 用 Write 工具写入 JSON：~/Downloads/bilibili-video-list/{UP主名}_{排序}_{日期}.json
agent-browser close
```

---

## Cookie 配置指南

### 快速配置（推荐）

引导用户完成 Cookie 配置：

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
| Cookie 过期 | API 返回错误，提示重新获取 SESSDATA |
| -352 风控（浏览器模式） | 必须用 --headed 模式，详见 [anti-detection.md](references/anti-detection.md) |
| 登录弹窗（浏览器模式） | 自动点击 `.bili-mini-close-icon` 关闭 |
| 视频数 999+ | API 模式自动翻页；浏览器模式持续翻页直到没有"下一页" |
| UP 主名字搜索 | API 模式：自动搜索；浏览器模式：见 [uid-resolution.md](references/uid-resolution.md) |
| 缓存文件损坏 | 忽略缓存，重新获取 |
| 排序方式与缓存不一致 | 缓存未命中，重新获取 |

## 免责声明

> [!warning] 本 Skill 仅用于个人学习和研究目的。因不当使用造成的法律后果由使用者自行承担。
