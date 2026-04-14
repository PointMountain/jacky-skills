# 采集模式详细流程

## 输入类型识别

| 输入特征 | 类型 | 处理方式 |
|----------|------|----------|
| 以 `http://` 或 `https://` 开头 | URL | WebFetch 或 mcp__web_reader__webReader 抓取正文 |
| 以 `.pdf` 结尾的本地路径 | PDF | Read 工具读取 |
| 以视频平台域名开头（youtube/bilibili/douyin/xiaohongshu 等） | 视频 | 直接调用 `audio-to-obsidian` skill |
| 纯文本内容 | 笔记 | 直接使用 |

**视频注意**：使用 `audio-to-obsidian`（路径：`/Users/jiashengwang/jacky-github/jacky-skills/plugins/video-processing/skills/audio-to-obsidian`），不要使用已废弃的 `video-to-text`。如果不可用，提示用户提供文字稿。

## 平台检测

根据 URL 域名自动识别来源平台，决定 raw/ 写入目录：

### 检测规则

1. 从 URL 提取域名
2. 与平台域名表匹配（见 SKILL.md 来源平台检测表）
3. 匹配成功 → 写入对应 raw/ 子目录
4. 匹配失败 → 默认写入 `raw/web/`

### raw/ 子目录映射

| 原始目录 | 说明 | 内容示例 |
|----------|------|----------|
| `raw/web/` | 通用网页采集 | 博客文章、技术文档、个人网站 |
| `raw/wechat/` | 微信公众号 | 公众号文章（mp.weixin.qq.com） |
| `raw/videos/` | 视频平台 | B站字幕、抖音短视频、小红书、YouTube |
| `raw/news/` | 资讯聚合 | Hacker News、Reddit、技术资讯 |
| `raw/official/` | 官方文档 | Claude Code 博客、OpenAI 文档、框架 Release Notes |
| `raw/notes/` | 自由笔记 | 用户手动输入的文本内容 |

### 平台标签

每个采集的文件在 frontmatter 中自动添加 `platform` 标签：

```yaml
platform: {wechat|bilibili|douyin|xiaohongshu|youtube|hackernews|reddit|claude-code|openai|web}
```

## 主题分类

根据 SKILL.md 中的主题关键词映射，确定目标主题目录。

**分类步骤**：

1. 从内容标题、摘要、来源 URL 中提取关键词
2. 与主题关键词映射表匹配，计算各主题的匹配度
3. 选择匹配度最高的主题
4. 无匹配（匹配度均为 0）时归入 `wiki/synthesis/`

**主题确认**：在预览确认步骤中展示推荐主题，用户可修改。

## 预览确认格式

使用 AskUserQuestion 展示：

```
平台：{来源平台名} → raw/{子目录}/
主题：{推荐主题名}（wiki/{theme}/）
标题：{标题}
来源：{来源}
关键要点：
  1. {要点 1}
  2. {要点 2}
  3. {要点 3}
标签：{标签}
相关 wiki 文章：{如有}

确认采集？可修改主题、标题、标签等。
```

## 写入 raw/

文件名：`{YYYY-MM-DD}-{slug}.md`

**目录由平台检测自动决定**，写入对应 raw/ 子目录。

Frontmatter：

```yaml
---
source: {原始 URL 或文件路径}
platform: {平台标识}
ingested_at: {ISO 时间戳}
type: {web|pdf|video|note|wechat|news|official}
status: uncompiled
---
```

## 编译到 wiki/{theme}/

详见 [compile-templates.md](compile-templates.md) 获取完整模板。

### 编译步骤

1. **生成主题文章**：写入 `wiki/{theme}/{slug}.md`
2. **提取原子概念**（可选）：如果内容包含独立的可复用知识点，写入 `wiki/{theme}/concepts/{concept-slug}.md`
3. **更新主题 index.md**：在 `wiki/{theme}/index.md` 追加条目
4. **更新全局索引**：如果是新主题（`wiki/index.md` 中不存在该主题入口），追加主题入口
5. **更新日志和清单**：追加 `wiki/log.md`，更新 `.kb/manifest.json`

### 概念处理规则

- 已有同名概念：读取并合并新信息，不覆盖
- 概念矛盾：在文章中用 `> [!warning] 矛盾标注` callout 标注
- 跨主题概念：在各自主题下独立创建，通过 wikilink 互引
