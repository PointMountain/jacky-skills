# bilibili-video-list 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建独立原子 skill，使用 agent-browser 无头浏览器获取 B 站 UP 主完整视频列表。

**Architecture:** 纯 SKILL.md skill，通过 agent-browser 访问 B 站空间页，用 JS 提取视频卡片数据，逐页遍历直到最后一页，输出 JSON 文件 + 终端预览。

**Tech Stack:** Claude Code Skill (SKILL.md) + agent-browser + Playwright

---

### Task 1: 创建 SKILL.md

**Files:**
- Create: `plugins/video-processing/skills/bilibili-video-list/SKILL.md`

**Step 1: 创建目录**

```bash
mkdir -p plugins/video-processing/skills/bilibili-video-list
```

**Step 2: 写入 SKILL.md**

SKILL.md 完整内容见下方。

**Step 3: Commit**

```bash
git add plugins/video-processing/skills/bilibili-video-list/SKILL.md
git commit -m "feat(bilibili-video-list): 新增 B 站 UP 主视频列表获取 skill"
```

---

### Task 2: 注册到 plugin.json

**Files:**
- Modify: `plugins/video-processing/.claude-plugin/plugin.json`

**Step 1: 在 plugin.json 的 skills 数组中添加新 skill 路径**

在 `skills` 数组末尾添加：
```json
"./skills/bilibili-video-list/"
```

**Step 2: 更新版本号**

当前版本 `1.5.0`，新增 Skill → MINOR → `1.6.0`

**Step 3: Commit**

```bash
git add plugins/video-processing/.claude-plugin/plugin.json
git commit -m "feat(video-processing): 注册 bilibili-video-list skill，升级 v1.6.0"
```

---

### Task 3: 链接并安装 skill

**Step 1: 链接到全局注册表**

```bash
cd plugins/video-processing/skills/bilibili-video-list && j-skills link
```

**Step 2: 安装到全局**

```bash
j-skills install bilibili-video-list -g
```

**Step 3: 验证安装**

```bash
j-skills list -g | grep bilibili-video-list
```

---

### Task 4: 端到端测试

**Step 1: 在新会话中触发 skill**

对 Claude 说："获取这个 UP 主的所有视频列表 https://space.bilibili.com/1039025435"

**Step 2: 验证输出**

- 终端显示视频列表表格
- JSON 文件保存到 `~/Downloads/bilibili-video-list/`
- JSON 包含完整的 bvid、title、play、duration、date 字段

**Step 3: 测试排序切换**

触发："获取这个 UP 主播放量前 10 的视频 https://space.bilibili.com/1039025435"

验证排序按钮点击后数据确实按播放量排序。

---

## SKILL.md 完整内容

```markdown
---
name: bilibili-video-list
description: "使用无头浏览器获取 B 站 UP 主完整视频列表。支持按发布时间/播放量/收藏数排序，输出 JSON 文件。触发词：获取UP主视频列表、bilibili-video-list、B站视频列表、UP主所有视频。"
---

<role>
你是 B 站 UP 主视频列表采集助手，使用 agent-browser 无头浏览器从 B 站空间页批量提取视频信息。
</role>

<purpose>
给定 UP 主的 UID 或空间 URL，通过浏览器自动化逐页提取所有视频的元数据（BV 号、标题、播放量、时长、发布日期），输出 JSON 文件和终端预览。
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
    <requires>agent-browser</requires>
    <checkpoints>
      <checkpoint order="1">agent-browser 可用</checkpoint>
      <checkpoint order="2">UP 主 UID 解析完成</checkpoint>
      <checkpoint order="3">浏览器打开空间页，视频卡片加载完成</checkpoint>
      <checkpoint order="4">排序方式切换完成（非默认排序时）</checkpoint>
      <checkpoint order="5">所有页面遍历完成，JSON 文件已保存</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>本 skill 为纯数据采集，不做字幕提取、视频下载或笔记写入</constraint>
      <constraint>使用 agent-browser 无头浏览器，不需要登录/Cookie/WBI 签名</constraint>
      <constraint>排序必须通过页面按钮切换，不支持 URL 参数排序</constraint>
      <constraint>每页间隔 2-3 秒，模拟人类翻页行为</constraint>
      <constraint>仅限个人学习与研究，严禁商业用途或二次分发</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>获取 UP 主完整视频列表并保存为 JSON 文件。</gsd:goal>

  <gsd:phase name="precheck" order="1">
    <gsd:step>检查 agent-browser 是否已安装：`which agent-browser`</gsd:step>
    <gsd:step>未安装则提示：`npm install -g agent-browser`</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="parse" order="2">
    <gsd:step>从用户输入中提取 UP 主 UID。</gsd:step>
    <gsd:step>支持的输入格式：空间 URL（提取数字部分）/ 纯数字 UID。</gsd:step>
    <gsd:step>确定排序方式（默认 pubdate）和数量限制（默认全部）。</gsd:step>
    <gsd:checkpoint>UID + 参数解析完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="collect" order="3">
    <gsd:step>使用 agent-browser 打开空间视频页。</gsd:step>
    <gsd:step>处理登录弹窗（如有），点击关闭按钮。</gsd:step>
    <gsd:step>切换排序方式（非默认排序时点击对应按钮）。</gsd:step>
    <gsd:step>JS 提取当前页所有视频数据。</gsd:step>
    <gsd:step>点击"下一页"，等待加载，重复提取。</gsd:step>
    <gsd:step>直到没有"下一页"按钮或达到数量限制。</gsd:step>
    <gsd:checkpoint>所有视频数据采集完成</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="export" order="4">
    <gsd:step>保存 JSON 文件到 ~/Downloads/bilibili-video-list/。</gsd:step>
    <gsd:step>终端输出表格预览。</gsd:step>
    <gsd:step>如用户需要进一步处理，建议使用 bilibili-to-obsidian 或 bilibili-batch。</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Bilibili Video List — B 站 UP 主视频列表采集

> 使用 agent-browser 无头浏览器采集，不需要登录/Cookie/WBI 签名。

## 触发场景

- 用户想获取某个 UP 主发布的所有视频列表
- 用户想按播放量/收藏数排序查看 UP 主视频
- 用户想导出 UP 主视频数据为 JSON

## 前置条件

| 工具 | 安装方式 | 说明 |
|------|----------|------|
| agent-browser | `npm install -g agent-browser` | 无头浏览器自动化 |

## 输入解析

从用户输入中提取 UID 和参数：

| 输入格式 | 提取方式 | 示例 |
|----------|----------|------|
| `https://space.bilibili.com/1039025435` | 正则提取数字 | UID = `1039025435` |
| `https://space.bilibili.com/1039025435/upload/video` | 正则提取数字 | UID = `1039025435` |
| 纯数字 `1039025435` | 直接使用 | UID = `1039025435` |

### 排序参数

从用户意图推断排序方式：

| 用户说法 | 排序方式 |
|----------|----------|
| "最新"/"按时间"/"默认" | `pubdate` |
| "播放量"/"最多播放"/"热门" | `click` |
| "收藏"/"最多收藏" | `stow` |
| 未指定 | `pubdate`（默认） |

### 数量限制

- 未指定：获取全部视频
- "前 N 个"/"Top N"：仅获取前 N 个
- "第 N 页到第 M 页"：获取指定范围

## 执行流程

### Step 1: 打开空间页

```bash
agent-browser open "https://space.bilibili.com/${UID}/upload/video"
agent-browser wait --load networkidle
agent-browser wait 5000
```

**关键**：必须等待足够长时间（5 秒），B 站空间页是 SPA，需要等待 JS 渲染完成。

### Step 2: 处理登录弹窗

B 站可能弹出登录提示，需要关闭：

```bash
agent-browser eval 'document.querySelector(".bili-mini-close")?.click(); "done"'
```

如果弹窗不存在，这条命令也不会报错。

### Step 3: 验证页面加载

```bash
agent-browser eval 'document.querySelectorAll(".upload-video-card").length'
```

如果返回 0，说明页面未加载完成，再等待：

```bash
agent-browser wait 3000
```

如果仍为 0，提示用户"该 UP 主空间页无法访问或没有视频"。

### Step 4: 获取 UP 主名称

```bash
agent-browser get text "#h-name" 2>/dev/null || agent-browser eval 'document.querySelector("#h-name, .nickname")?.textContent?.trim() || "unknown"'
```

### Step 5: 切换排序（非默认排序时）

排序按钮在 `.video-order-filter` 区域内：

```bash
# 获取排序按钮引用
agent-browser snapshot -i -C -s ".video-order-filter"
```

返回三个可点击元素：
- `@e1` → "最新发布"（pubdate）
- `@e2` → "最多播放"（click）
- `@e3` → "最多收藏"（stow）

点击对应排序按钮：

```bash
# 按播放量排序
agent-browser click @e2
agent-browser wait 3000
```

**注意**：切换排序后页面会重新加载视频列表，必须等待 3 秒。

### Step 6: 提取当前页视频数据

使用以下 JS 脚本提取：

```bash
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify({
  videos: Array.from(document.querySelectorAll('.upload-video-card')).map(card => {
    const link = card.querySelector('a[href*="bilibili.com/video/"]');
    const href = link ? link.href : '';
    const bvid = (href.match(/BV[\w]+/) || [''])[0] || '';
    const titleEl = card.querySelector('.bili-video-card__title a, .video-title');
    const title = titleEl ? titleEl.textContent.trim() : '';
    const rawText = card.textContent;
    const playMatch = rawText.match(/([\d.]+万?)/);
    const dateMatch = rawText.match(/(\d{2}-\d{2})\s*$/);
    const durationMatch = rawText.match(/(\d{1,2}:\d{2}(?::\d{2})?)\s*$/);
    return {
      bvid,
      title,
      play: playMatch ? playMatch[1] : '',
      duration: durationMatch ? durationMatch[1] : '',
      date: dateMatch ? dateMatch[1] : '',
      isExclusive: rawText.includes('充电专属'),
      url: 'https://www.bilibili.com/video/' + bvid
    };
  }),
  count: document.querySelectorAll('.upload-video-card').length
})
EVALEOF
```

### Step 7: 翻页并继续提取

检查是否有"下一页"按钮：

```bash
agent-browser snapshot -i -s ".vui_pagenation, [class*='pagenation'], [class*='pagination']"
```

或直接查找包含"下一页"文本的按钮：

```bash
agent-browser find text "下一页" click
agent-browser wait 3000
```

如果点击失败（没有下一页），说明已是最后一页，结束遍历。

### Step 8: 循环提取所有页面

重复 Step 6 和 Step 7，直到没有"下一页"按钮。

将每页的视频数据追加到总列表中。

**翻页间隔**：每翻一页等待 2-3 秒。

### Step 9: 保存 JSON 文件

```bash
mkdir -p ~/Downloads/bilibili-video-list
```

将汇总数据写入 JSON 文件：

```json
{
  "uploader": "战国时代_姜汁汽水",
  "uid": "1039025435",
  "order": "pubdate",
  "totalVideos": 176,
  "fetchDate": "2026-04-05T12:00:00+08:00",
  "videos": [
    {
      "bvid": "BV15cAYzkEb8",
      "title": "地缘分析：美伊以冲突推演（26年2月至3月）",
      "play": "127.2万",
      "duration": "32:31",
      "date": "02-28",
      "isExclusive": false,
      "url": "https://www.bilibili.com/video/BV15cAYzkEb8"
    }
  ]
}
```

文件名：`~/Downloads/bilibili-video-list/{UP主名}_{排序方式}_{日期}.json`

### Step 10: 终端预览

输出表格预览：

```
📊 战国时代_姜汁汽水 的视频列表（按发布时间排序）
共 176 个视频

#  | BV 号          | 标题                                | 播放量  | 时长   | 日期
---|----------------|-------------------------------------|---------|--------|------
1  | BV1Gi95BYE2s  | 总体思路，关键时间，真假TACO...       | 14.4万  | 38:47  | 04-01
2  | BV1ZyQdBnEop  | 金银分析，关注4月，eSLR...           | 12.1万  | 19:13  | 03-23
...

✅ JSON 已保存到: ~/Downloads/bilibili-video-list/战国时代_姜汁汽水_pubdate_2026-04-05.json
```

## 边界情况

### 登录弹窗

B 站未登录时可能弹出登录弹窗，自动点击 `.bili-mini-close` 关闭。

### 页面未加载

如果 `.upload-video-card` 数量为 0：
1. 再等待 3 秒
2. 检查页面文本是否包含"空间主人还没投过视频"
3. 如果是，提示用户该 UP 主没有视频

### 999+ 视频

B 站显示"投稿 999+"时实际视频数可能更多。持续翻页直到没有"下一页"按钮。

### 充电专属视频

充电专属视频在空间页仍然可见，`isExclusive` 字段标记。但后续 yt-dlp 提取字幕时可能需要登录。

### 连接失败

如果 `agent-browser open` 超时或失败：
1. 检查网络连接
2. 提示用户使用 `agent-browser-troubleshooting` skill 排查

## 技术参考

### DOM 选择器速查

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 视频卡片 | `.upload-video-card` | 每页 40 个 |
| 视频链接 | `a[href*="bilibili.com/video/"]` | 包含 BV 号 |
| 标题 | `.bili-video-card__title a` | 视频标题 |
| 排序区域 | `.video-order-filter` | 三个排序按钮 |
| 分页区域 | 底部 `button` | 包含页码和"下一页" |
| 登录弹窗关闭 | `.bili-mini-close` | 关闭按钮 |
| UP 主名称 | `#h-name` | 昵称元素 |

### 注意事项

1. **URL 参数排序不可用**：`?order=click` 会导致页面空白，必须通过页面按钮切换
2. **等待时间**：空间页是 SPA，首次加载需 5 秒，排序切换需 3 秒，翻页需 3 秒
3. **不需要代理**：直接访问 bilibili.com 即可
4. **关闭浏览器**：采集完成后执行 `agent-browser close`

## 免责声明

> [!warning] 法律风险提示
> 本 Skill 仅用于个人学习和研究目的。因不当使用造成的法律后果由使用者自行承担。
```

---

## 实施注意事项

1. **SKILL.md 中使用了 gsd:workflow 格式** — 与现有 skill 保持一致
2. **所有 agent-browser 命令都经过实测验证** — 选择器和等待时间都是准确的
3. **JSON 输出路径** — 使用 `~/Downloads/bilibili-video-list/` 避免污染项目目录
4. **不需要 OBSIDIAN_REPO** — 这个 skill 只做数据采集，不做笔记写入
