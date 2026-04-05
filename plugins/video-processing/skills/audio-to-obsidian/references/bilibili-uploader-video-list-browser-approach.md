# B 站 UP 主视频列表批量获取 — 无头浏览器方案

> **状态**: 方案验证通过（2026-04-05）
> **备选方案**: [API 方案](../../bilibili-to-obsidian/bilibili-uploader-api-research.md)（需要 SESSDATA + WBI 签名，风控严格）

## 方案概述

使用无头浏览器（agent-browser / Playwright）访问 B 站 UP 主空间页，通过 DOM 提取视频列表数据。

**核心优势**：真实浏览器 TLS 指纹，不需要登录，不需要 WBI 签名，风控风险极低。

## 实测验证结果

### 测试目标

| 项目 | 值 |
|------|------|
| UP 主 | 战国时代_姜汁汽水 |
| UID | 1039025435 |
| 空间页 | `https://space.bilibili.com/1039025435` |
| 视频列表页 | `https://space.bilibili.com/1039025435/upload/video` |
| 总视频数 | 999+（约 25+ 页） |
| 粉丝数 | 73.9 万 |

### 测试结论

| 测试项 | 结果 |
|--------|------|
| 页面访问 | 正常加载，无风控拦截 |
| 登录要求 | **不需要登录** |
| BV 号提取 | ✅ 在链接 `href` 中，正则 `/BV[\w]+/` 提取 |
| 标题提取 | ✅ 在 `a` 标签的 `textContent` 中 |
| 分页方式 | 底部分页按钮（1/2/3/4/5/下一页） |
| 每页数量 | 40 个视频 |

## 页面 DOM 结构

### 视频卡片结构

```html
<div class="upload-video-card grid-mode">
  <div class="upload-video-card__left">
    <div class="upload-video-card__main">
      <div class="bili-video-card">
        <div class="bili-video-card__wrap">
          <div class="bili-video-card__cover">
            <a href="//www.bilibili.com/video/BV1Gi95BYE2s/?spm_id_from=...">
              <img src="//i0.hdslb.com/bfs/archive/xxx.jpg@672w_378h_1c.webp" alt="视频标题">
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### 关键 CSS 选择器

| 数据 | 选择器 | 说明 |
|------|--------|------|
| 视频卡片 | `.upload-video-card` | 每个视频的容器 |
| 视频链接 | `a[href*="bilibili.com/video/"]` | 包含 BV 号的链接 |
| BV 号 | 链接 `href` 中 `/BV[\w]+/` | 正则提取 |
| 视频标题 | `a` 标签 `textContent` | 卡片内链接文本 |
| 分页按钮 | 底部 `button`（"下一页"） | 翻页用 |

### 可提取的数据

从每个视频卡片可提取：

| 字段 | 提取方式 | 示例 |
|------|----------|------|
| BV 号 | `href.match(/BV[\w]+/)` | `BV15cAYzkEb8` |
| 标题 | `a.textContent.trim()` | `地缘分析：美伊以冲突推演（26年2月至3月）` |
| 播放量 | 卡片文本中提取 | `127.2万` |
| 时长 | 卡片文本中提取 | `32:31` |
| 是否充电专属 | 卡片文本包含"充电专属" | 是/否 |

## JS 数据提取脚本

```javascript
// 提取当前页所有视频数据
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

## 完整实现流程

```
1. agent-browser open https://space.bilibili.com/{UID}/upload/video
2. wait --load networkidle
3. JS 提取当前页所有视频（BV 号 + 标题 + 播放量 + 时长）
4. 保存到结果数组
5. snapshot -i 找到"下一页"按钮
6. click 下一页
7. wait --load networkidle
8. 重复 3-7 直到没有"下一页"按钮
9. agent-browser close
10. 导出完整视频列表 JSON
```

## 分页策略

- B 站空间页使用**传统分页**（不是无限滚动），底部有页码按钮
- 每页显示 **40 个视频**
- 翻页方式：点击底部"下一页"按钮
- 页码按钮选择器：`button` 文本为数字或"下一页"

## 风控与注意事项

| 风险级别 | 说明 |
|----------|------|
| TLS 指纹检测 | **无风险** — 真实 Chromium 引擎 |
| 登录要求 | **不需要** — 空间页是公开页面 |
| WBI 签名 | **不需要** — 浏览器自己处理 |
| 请求频率 | 建议每页间隔 **2-3 秒**，模拟人类翻页 |
| webdriver 检测 | Playwright 默认已处理，风险极低 |
| IP 封禁 | 极低风险，正常浏览行为 |

## 与 API 方案对比

| 维度 | 无头浏览器方案 | API 方案 |
|------|--------------|----------|
| 登录要求 | 不需要 | 需要 SESSDATA |
| 签名机制 | 不需要 | 需要 WBI 签名 |
| TLS 指纹 | 真实浏览器 | 需要额外处理 |
| 风控风险 | 极低 | 高 |
| 实现复杂度 | 中 | 高 |
| 数据格式 | DOM 提取 | 结构化 JSON |
| 速度 | 较慢（需渲染页面） | 快（纯 API 调用） |
| 稳定性 | 高（模拟真实用户） | 中（密钥/签名可能变化） |

## 推荐方案

**首选无头浏览器方案**，原因：
1. 不需要用户登录或提供 Cookie
2. 不需要实现和维护 WBI 签名算法
3. 风控风险极低
4. 数据提取简单直接

API 方案作为备选，适用于：
- 需要更高性能的批量场景
- 服务器端定时任务
- 已有有效 SESSDATA 的场景
