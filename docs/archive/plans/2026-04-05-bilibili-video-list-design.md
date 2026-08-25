# bilibili-video-list Skill 设计文档

> 日期: 2026-04-05
> 状态: 已批准

## 目标

创建独立原子 skill，使用无头浏览器（agent-browser）获取 B 站 UP 主的完整视频列表，输出 JSON 文件 + 终端预览。

## 背景

现有 `bilibili-batch` 使用 `yt-dlp --flat-playlist` 获取视频列表，存在风控问题。经过实测验证，无头浏览器方案更稳定：
- 不需要登录/Cookie
- 不需要 WBI 签名
- TLS 指纹为真实浏览器
- 支持三种排序方式

## 架构

```
输入：UP 主 UID / 空间 URL + 排序方式 + 数量限制
  ↓
agent-browser 访问空间页 → 切换排序 → 逐页提取 → 汇总
  ↓
输出：JSON 文件 + 终端表格预览
```

## 技术验证结果

### 页面 URL

- 空间视频页：`https://space.bilibili.com/{UID}/upload/video`
- 不支持 URL 参数排序（`?order=click` 会导致空白页），必须通过页面按钮切换

### DOM 关键选择器

| 元素 | 选择器 |
|------|--------|
| 视频卡片 | `.upload-video-card` |
| 视频链接 | `a[href*="bilibili.com/video/"]` |
| 标题 | `.bili-video-card__title a` |
| 排序区域 | `.video-order-filter` |
| 排序按钮 | 最新发布 / 最多播放 / 最多收藏 |
| 分页按钮 | 底部 `button`（"下一页"） |
| 登录弹窗关闭 | `.bili-mini-close` |

### 每页数据

- 每页 40 个视频
- 通过底部"下一页"按钮翻页

### 提取数据字段

```json
{
  "bvid": "BV15cAYzkEb8",
  "title": "地缘分析：美伊以冲突推演（26年2月至3月）",
  "play": "127.2万",
  "duration": "32:31",
  "date": "02-28",
  "isExclusive": false,
  "url": "https://www.bilibili.com/video/BV15cAYzkEb8"
}
```

## 排序方式

| 参数值 | 页面操作 |
|--------|----------|
| `pubdate`（默认） | 点击"最新发布" |
| `click` | 点击"最多播放" |
| `stow` | 点击"最多收藏" |

## 输出

1. JSON 文件：`~/Downloads/bilibili-video-list/{UP主名}_{排序方式}.json`
2. 终端预览：表格形式显示

## 支持的输入格式

- `https://space.bilibili.com/1039025435`
- `https://space.bilibili.com/1039025435/upload/video`
- 纯 UID：`1039025435`

## 边界处理

- 登录弹窗：自动关闭
- 空间页无视频：提示用户
- 999+ 视频：默认获取全部，支持 `--limit` 限制
- 每页间隔 2-3 秒

## 不做的事（YAGNI）

- 不做字幕提取
- 不做视频下载
- 不做 Obsidian 笔记写入
- 不需要登录/Cookie

## 文件位置

- Skill 目录：`plugins/video-processing/skills/bilibili-video-list/`
- 仅包含 `SKILL.md`（纯 Claude Code skill，无 CLI 工具）
