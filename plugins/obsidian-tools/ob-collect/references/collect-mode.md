# 采集模式详细流程

## 输入类型识别

| 输入特征 | 类型 | 处理方式 |
|----------|------|----------|
| 以 `http://` 或 `https://` 开头 | URL | WebFetch 或 mcp__web_reader__webReader 抓取正文 |
| 以 `.pdf` 结尾的本地路径 | PDF | Read 工具读取 |
| 以视频平台域名开头（youtube/bilibili 等） | 视频 | 直接调用 `audio-to-obsidian` skill |
| 纯文本内容 | 笔记 | 直接使用 |

**视频注意**：使用 `audio-to-obsidian`（路径：`/Users/jiashengwang/jacky-github/jacky-skills/plugins/video-processing/skills/audio-to-obsidian`），不要使用已废弃的 `video-to-text`。如果不可用，提示用户提供文字稿。

## 预览确认格式

使用 AskUserQuestion 展示：

```
标题：{标题}
来源：{来源}
关键要点：
  1. {要点 1}
  2. {要点 2}
  3. {要点 3}
标签：{标签}
相关 wiki 文章：{如有}

确认采集？可修改标题、标签等。
```

## 写入 raw/

文件名：`{YYYY-MM-DD}-{slug}.md`

| 类型 | 目录 |
|------|------|
| URL | `$OBSIDIAN_REPO/raw/web/` |
| PDF | `$OBSIDIAN_REPO/raw/pdf/` |
| 视频/笔记 | `$OBSIDIAN_REPO/raw/notes/` |

Frontmatter：

```yaml
---
source: {原始 URL 或文件路径}
ingested_at: {ISO 时间戳}
type: {web|pdf|video|note}
status: uncompiled
---
```

## 编译到 wiki/

详见 [compile-templates.md](compile-templates.md) 获取完整模板。

### 编译步骤

1. **生成 source 摘要**：写入 `wiki/sources/{slug}.md`
2. **创建/更新 concept 文章**：每个关键概念一个文件，已存在则合并
3. **更新 index.md**：追加到对应分区
4. **追加 log.md**：记录本次 ingest 操作
5. **更新 manifest.json**：追加条目到 items 数组
