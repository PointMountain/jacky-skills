---
name: write-obsidian-note
description: "生成 Obsidian 笔记，遵循 llm-wiki 模式：raw/ 保存原始字幕，wiki/ 保存归纳笔记并引用 raw。触发词：写入obsidian笔记、生成笔记、write-obsidian-note。"
---

<role>
你是 Obsidian 笔记生成器，遵循 llm-wiki 模式，将元信息和文案转化为 raw 原始层和 wiki 归纳层的结构化笔记。
</role>

<purpose>
遵循 llm-wiki 的分层架构，将所有来源（视频、播客、录音等）的字幕/文案分离为两层：
- **raw 层**：按作者名归档的原始字幕（不可变，LLM 只读不写）
- **wiki 层**：LLM 编译的归纳笔记，引用 raw 层原文

确保格式一致，一处修改全局生效。
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
      <checkpoint order="2">raw 原始笔记已写入</checkpoint>
      <checkpoint order="3">wiki 归纳笔记已写入</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>笔记中必须标注来源 URL 和版权信息</constraint>
      <constraint>目标文件已存在时，默认跳过不覆盖（需明确授权才覆盖）</constraint>
      <constraint>文件名中的特殊字符（/ \ ? % * : | " < >）替换为下划线</constraint>
      <constraint>归纳笔记的「我的思考」部分留空，由用户自行补充</constraint>
      <constraint>归纳笔记必须用 `[[raw/作者名/标题]]` 引用 raw 层原文</constraint>
      <constraint>raw 层笔记带 frontmatter 元数据，遵循 llm-wiki raw 规范</constraint>
      <constraint>原文笔记统一使用时间轴分段格式，不输出无分段的纯文本墙</constraint>
      <constraint>原子写入：先写临时文件再 rename，防止中途崩溃产生半写文件</constraint>
      <constraint>文件名长度 ≤ 200 字符，超出截断</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>输入元信息 + 文案 → 输出 raw/作者名/标题.md（原始字幕）+ wiki/标题-归纳.md（归纳 + 引用 raw）到 Obsidian 仓库。</gsd:goal>

  <gsd:phase name="precheck" order="1">
    <gsd:step>验证 OBSIDIAN_REPO 目录存在。</gsd:step>
    <gsd:checkpoint>环境就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="generate-raw" order="2">
    <gsd:step>基于模板 + frontmatter 生成 raw 原始字幕笔记。</gsd:step>
    <gsd:step>写入 $OBSIDIAN_REPO/raw/[作者]/[标题].md</gsd:step>
    <gsd:checkpoint>raw 笔记已写入</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="generate-wiki" order="3">
    <gsd:step>基于模板 + AI 归纳生成 wiki 归纳笔记。</gsd:step>
    <gsd:step>写入 $OBSIDIAN_REPO/wiki/[标题]-归纳.md</gsd:step>
    <gsd:checkpoint>wiki 笔记已写入</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

# Write Obsidian Note — llm-wiki 风格笔记生成器

遵循 llm-wiki 分层架构，将字幕/文案分离为 raw 原始层和 wiki 归纳层。

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
| `metadata.author` | ✅ | 作者名（用于 raw 层目录划分） |
| `metadata.url` | ✅ | 来源 URL |
| `metadata.duration` | ❌ | 时长 |
| `metadata.date` | ❌ | 提取日期，默认今天 |
| `metadata.platform` | ❌ | 平台标识 |
| `transcript` | ✅ | 完整文案（带时间戳） |
| `category` | ❌ | 分类，默认 `Audio`（写入 frontmatter） |
| `extraContent.embedCode` | ❌ | 嵌入代码（写入 wiki 层） |
| `extraContent.extraTags` | ❌ | 额外标签 |

### 输出

```json
{
  "success": true,
  "files": {
    "originalPath": "$OBSIDIAN_REPO/raw/作者名/标题.md",
    "summaryPath": "$OBSIDIAN_REPO/wiki/标题-归纳.md"
  }
}
```

## 目录结构

遵循 llm-wiki 的 raw/wiki 分层：

```
$OBSIDIAN_REPO/
├── raw/                        # 原始资料层（不可变，LLM 只读不写）
│   ├── index.md                # 作者索引（自动维护）
│   └── [作者名]/
│       ├── 标题A.md
│       └── 标题B.md
└── wiki/                       # wiki 归纳层（LLM 编译维护）
    ├── 标题A-归纳.md
    └── 标题B-归纳.md
```

> `category` 不再影响目录路径，而是记录在 raw 层的 frontmatter 中。

## 笔记模板

### raw 原始笔记 `raw/[作者名]/[标题].md`

**格式规则：带 frontmatter 元数据 + heading 分段时间轴。**

```markdown
---
source: "https://..."
author: "作者名"
ingested_at: 2026-04-06
type: transcript
category: Audio
duration: "10:30"
status: uncompiled
---

# 标题

### 0:00 主题段落标题

句子内容，可以多句组成一个语义完整的段落。
每段以 `### M:SS 主题标题` 开头，方便 Obsidian heading 跳转。

### 1:30 下一个主题段落标题

下一段内容...

---
#音频笔记 #[author] [extraContent.extraTags]
```

**Frontmatter 字段说明（遵循 llm-wiki raw 规范）：**

| 字段 | 说明 |
|------|------|
| `source` | 来源 URL |
| `author` | 作者名 |
| `ingested_at` | 摄入日期 |
| `type` | 固定 `transcript` |
| `category` | 分类（Audio/B站等） |
| `duration` | 音频时长 |
| `status` | 编译状态：`uncompiled` / `compiled` |

**关键规则：**
- 每个语义段落用 `### M:SS 标题` 作为 heading
- raw 层不可变：写入后 LLM 不再修改
- Frontmatter 便于后续 llm-wiki 编译流程识别和处理

### wiki 归纳笔记 `wiki/[标题]-归纳.md`

**格式规则：核心观点拆解 + `[[raw/作者名/标题]]` 引用 raw 层。**

```markdown
# 标题 - 归纳

> **作者**: [author]
> **来源**: [url]
> **时长**: [duration]
> **提取时间**: [date]
> **原文**: [[raw/作者名/标题]]

[extraContent.embedCode — 如有则插入]

## 音频来源

> [!quote] 🔗 [点击播放]([url])

---

## 核心观点

### 1. [观点标题]

简明扼要地概括这个观点（2-5句话）。
包括论据、因果逻辑、关键数据。

→ [[raw/作者名/标题#1:30]] ~ [[raw/作者名/标题#3:45]]

### 2. [观点标题]

下一个核心观点的概括。

→ [[raw/作者名/标题#5:00]] ~ [[raw/作者名/标题#7:20]]

## 关键引用

> [原文金句1] — [[raw/作者名/标题#2:15]]

> [原文金句2] — [[raw/作者名/标题#8:30]]

## 我的思考

[待补充]

---
#音频笔记 #[author] #归纳 [extraContent.extraTags]
```

## 作者索引 `raw/index.md`

**遵循 llm-wiki 索引地图层理念：紧凑、可导航、一行一描述。**

每次写入笔记后自动重建，无需手动维护。

```markdown
---
type: index
updated_at: 2026-04-06
authors: 3
files: 12
---

# 作者索引

> 自动维护 · 3 位作者 · 12 篇资料

## 作者A

- [[raw/作者A/标题1]] — 2026-04-06
- [[raw/作者A/标题2]] — 2026-04-05

## 作者B

- [[raw/作者B/标题3]] — 2026-04-04
```

**设计要点：**
- **自动重建**：每次 `write_notes` 写入后扫描 `raw/` 目录重新生成
- **frontmatter 统计**：`authors`/`files` 数量，便于 Obsidian Dataview 查询
- **一行一描述**：每个条目 = wikilink + 日期，符合 llm-wiki 索引规范
- **按作者分组**：Obsidian 中可直接折叠/导航

## 归纳生成规则

AI 归纳遵循以下原则：

1. **观点拆解**：将内容拆解为 3-7 个核心观点/论点，每个有独立标题
2. **raw 引用**：每个观点必须用 `[[raw/作者名/标题#M:SS]]` 链接到 raw 层原文的 heading
3. **时间范围**：观点跨多段时用 `~` 连接起止：`[[raw/作者名/标题#1:30]] ~ [[raw/作者名/标题#3:45]]`
4. **不搬运原文**：归纳用自己的话概括，不直接复制原文句子
5. **关键结论**：提炼 3-5 条一句话可消化的结论，附链接
6. **金句引用**：选取 2-4 条原文中最有表达力的原话，附链接
7. **我的思考**：留空，供用户自行补充
8. **不做延伸**：只归纳，不添加 transcript 中没有的观点

## 写入逻辑

```bash
# 清理文件名 + 限制长度
SAFE_TITLE=$(echo "$TITLE" | sed 's/[/\\?%*:|"<>]/_/g' | cut -c1-200)
SAFE_AUTHOR=$(echo "$AUTHOR" | sed 's/[/\\?%*:|"<>]/_/g' | cut -c1-50)

# 创建 raw 和 wiki 目录
mkdir -p "$OBSIDIAN_REPO/raw/$SAFE_AUTHOR"
mkdir -p "$OBSIDIAN_REPO/wiki"

# 检查已存在
if [ -f "$OBSIDIAN_REPO/raw/$SAFE_AUTHOR/$SAFE_TITLE.md" ]; then
  echo "EXISTS"  # 由调用方决定是否覆盖
fi

# 原子写入（先写临时文件，再 rename）
for TARGET in "raw/$SAFE_AUTHOR/$SAFE_TITLE.md" "wiki/$SAFE_TITLE-归纳.md"; do
  TARGET_FILE="$OBSIDIAN_REPO/$TARGET"
  TMP_FILE="$(dirname "$TARGET_FILE")/.tmp_$(basename "$TARGET_FILE")_$$.md"

  # 写入临时文件
  cat > "$TMP_FILE" <<CONTENT

  # 原子重命名
  mv -f "$TMP_FILE" "$TARGET_FILE"
done
```

## 错误处理

| 错误 | 处理 |
|------|------|
| OBSIDIAN_REPO 不存在 | 返回错误 + 配置提示 |
| 文件名过长 | 截断至 200 字符 |
| 写入权限不足 | 返回错误 + chmod 建议 |
| transcript 为空 | 仍生成 raw 笔记，标注「无转录内容」 |

## 与 llm-wiki 的协作

本 skill 产出的 raw/wiki 结构与 llm-wiki 知识库兼容：

- **raw 层**：`raw/[作者名]/标题.md` 可被 llm-wiki 的 `/kb-compile` 识别和编译
- **wiki 层**：`wiki/标题-归纳.md` 可被 llm-wiki 的索引系统纳入
- **frontmatter**：`status: uncompiled` 标记让 llm-wiki 知道哪些需要编译
- 编译后 llm-wiki 可更新 `status` 为 `compiled`，并在 `wiki/` 中创建概念文章

## 复用场景

| 调用方 | category | extraContent |
|--------|----------|-------------|
| `audio-to-obsidian` | `Audio` | 无 |
| `bilibili-to-obsidian` | `B站` | `embedCode: iframe`, `extraTags: [#B站]` |
| 本地录音整理 | `Audio` | 无 embed |
| 播客笔记 | `Audio` | `extraTags: [#播客]` |
