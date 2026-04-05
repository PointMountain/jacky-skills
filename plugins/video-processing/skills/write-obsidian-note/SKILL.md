---
name: write-obsidian-note
description: "生成统一格式的 Obsidian 笔记（原文 + 归纳），写入指定目录。支持 category 和 extraContent 参数适配不同来源。触发词：写入obsidian笔记、生成笔记、write-obsidian-note。"
---

<role>
你是 Obsidian 笔记生成器，负责将元信息和文案转化为结构化的 Obsidian 笔记文件。
</role>

<purpose>
统一管理所有来源（视频、播客、录音等）的 Obsidian 笔记模板，确保格式一致，一处修改全局生效。
</purpose>

<trigger>
```text
触发词/示例：
- 写入 Obsidian 笔记
- 生成原文和归纳笔记
- write-obsidian-note
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>write-obsidian-note</name>
    <owner>video-processing</owner>
    <requires>OBSIDIAN_REPO</requires>
    <checkpoints>
      <checkpoint order="1">OBSIDIAN_REPO 配置就绪</checkpoint>
      <checkpoint order="2">笔记文件已写入 Obsidian</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>笔记中必须标注来源 URL 和版权信息</constraint>
      <constraint>目标文件已存在时，默认跳过不覆盖（需明确授权才覆盖）</constraint>
      <constraint>文件名中的特殊字符（/ \ ? % * : | " < >）替换为下划线</constraint>
      <constraint>归纳笔记的「我的思考」部分留空，由用户自行补充</constraint>
      <constraint>原子写入：先写临时文件再 rename，防止中途崩溃产生半写文件</constraint>
      <constraint>文件名长度 ≤ 200 字符，超出截断</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>输入元信息 + 文案 → 输出原文.md + 归纳.md 到 Obsidian 仓库。</gsd:goal>

  <gsd:phase name="precheck" order="1">
    <gsd:step>验证 OBSIDIAN_REPO 目录存在。</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="generate" order="2">
    <gsd:step>基于模板生成原文笔记内容。</gsd:step>
    <gsd:step>基于模板 + AI 归纳生成归纳笔记内容。</gsd:step>
    <gsd:checkpoint>笔记内容生成完毕</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="write" order="3">
    <gsd:step>创建目标目录：$OBSIDIAN_REPO/00-Inbox/Audio/[作者]/</gsd:step>
    <gsd:step>写入原文笔记和归纳笔记。</gsd:step>
    <gsd:step>检查已存在文件：存在则跳过或询问覆盖。</gsd:step>
    <gsd:checkpoint>笔记已写入</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

# Write Obsidian Note - Obsidian 笔记生成器

统一管理所有来源的 Obsidian 笔记模板，确保格式一致。

## 可执行脚本

```bash
# 方式 1：通过契约 JSON 写入
python3 scripts/write_note.py \
  --input-json /path/to/payload.json \
  --obsidian-repo "$OBSIDIAN_REPO"

# 方式 2：通过参数直接写入
python3 scripts/write_note.py \
  --obsidian-repo "$OBSIDIAN_REPO" \
  --title "标题" \
  --author "作者" \
  --url "https://example.com" \
  --transcript-file /path/to/transcript.md

# 覆盖已存在文件
python3 scripts/write_note.py --input-json /path/to/payload.json \
  --obsidian-repo "$OBSIDIAN_REPO" --overwrite
```

## 输入输出契约

### 输入

```json
{
  "metadata": {
    "title": "视频标题",
    "author": "作者名",
    "url": "https://...",
    "duration": "10:30",
    "date": "2026-04-05",
    "platform": "youtube"
  },
  "transcript": "完整文案内容（带时间戳）...",
  "category": "Audio",
  "extraContent": {
    "embedCode": "<iframe src='...'></iframe>",
    "extraTags": ["#B站"]
  }
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `metadata.title` | ✅ | 笔记标题 |
| `metadata.author` | ✅ | 作者名 |
| `metadata.url` | ✅ | 来源 URL |
| `metadata.duration` | ❌ | 时长 |
| `metadata.date` | ❌ | 提取日期，默认今天 |
| `metadata.platform` | ❌ | 平台标识 |
| `transcript` | ✅ | 完整文案（带时间戳） |
| `category` | ❌ | 分类目录，默认 `Audio` |
| `extraContent.embedCode` | ❌ | 额外嵌入代码（如 B站 iframe） |
| `extraContent.extraTags` | ❌ | 额外标签 |

### 输出

```json
{
  "success": true,
  "files": {
    "originalPath": "$OBSIDIAN_REPO/00-Inbox/Audio/作者名/标题-原文.md",
    "summaryPath": "$OBSIDIAN_REPO/00-Inbox/Audio/作者名/标题-归纳.md"
  }
}
```

## 目录结构

```
$OBSIDIAN_REPO/00-Inbox/Audio/
└── [作者名]/
    ├── [标题]-原文.md
    └── [标题]-归纳.md
```

> `category` 控制目录层级：`Audio` → `00-Inbox/Audio/`，自定义则 `00-Inbox/{category}/`

## 笔记模板

### 原文笔记 `[标题]-原文.md`

```markdown
# [标题]

> **作者**: [author]
> **来源**: [url]
> **提取时间**: [date]
> **时长**: [duration]

[extraContent.embedCode — 如有则插入]

## 音频来源

> [!quote] 🔗 [点击播放]([url])

---

## 完整文案（带时间戳）

[transcript]

---
#音频笔记 #[author] [extraContent.extraTags]
```

### 归纳笔记 `[标题]-归纳.md`

```markdown
# [标题] - 归纳

> **作者**: [author]
> **来源**: [url]
> **原文**: [[标题-原文]]

## 核心要点

- [AI 从 transcript 中归纳的要点 1]
- [要点 2]
- [要点 3]

## 关键引用

> [transcript 中的关键原文引用]

## 我的思考

[待补充]

---
#音频笔记 #[author] #归纳 [extraContent.extraTags]
```

## 归纳生成规则

AI 归纳遵循以下原则：

1. **核心要点**：从 transcript 中提取 3-7 个关键论点
2. **关键引用**：选取最有代表性的原文片段（保留时间戳）
3. **我的思考**：留空，供用户自行补充
4. **不做延伸**：只归纳，不添加 transcript 中没有的观点

## 写入逻辑

```bash
# 清理文件名 + 限制长度
SAFE_TITLE=$(echo "$TITLE" | sed 's/[/\\?%*:|"<>]/_/g' | cut -c1-200)
SAFE_AUTHOR=$(echo "$AUTHOR" | sed 's/[/\\?%*:|"<>]/_/g' | cut -c1-50)

# 创建目录
mkdir -p "$OBSIDIAN_REPO/00-Inbox/$CATEGORY/$SAFE_AUTHOR"

# 检查已存在
if [ -f "$OBSIDIAN_REPO/00-Inbox/$CATEGORY/$SAFE_AUTHOR/$SAFE_TITLE-原文.md" ]; then
  echo "EXISTS"  # 由调用方决定是否覆盖
fi

# 原子写入（先写临时文件，再 rename）
TARGET_DIR="$OBSIDIAN_REPO/00-Inbox/$CATEGORY/$SAFE_AUTHOR"
for NOTE_TYPE in "原文" "归纳"; do
  TMP_FILE="$TARGET_DIR/.tmp_${SAFE_TITLE}-${NOTE_TYPE}_$$.md"
  TARGET_FILE="$TARGET_DIR/${SAFE_TITLE}-${NOTE_TYPE}.md"

  # 写入临时文件
  cat > "$TMP_FILE" <<CONTENT

  # 原子重命名
  mv -f "$TMP_FILE" "$TARGET_FILE"
done
```

> **原子写入**：`cat > tmp → mv` 确保文件要么完整写入要么不变，不会出现半写文件。
> macOS `mv -f` 在同文件系统上是原子操作。

## 错误处理

| 错误 | 处理 |
|------|------|
| OBSIDIAN_REPO 不存在 | 返回错误 + 配置提示 |
| 文件名过长 | 截断至 200 字符 |
| 写入权限不足 | 返回错误 + chmod 建议 |
| transcript 为空 | 仍生成原文笔记，标注「无转录内容」 |

## 复用场景

| 调用方 | category | extraContent |
|--------|----------|-------------|
| `audio-to-obsidian` | `Audio` | 无 |
| `bilibili-to-obsidian` | `B站` | `embedCode: iframe`, `extraTags: [#B站]` |
| 本地录音整理 | `Audio` | 无 embed |
| 播客笔记 | `Audio` | `extraTags: [#播客]` |
