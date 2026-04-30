---
name: article-with-images
description: "生成带配图的 Obsidian 文章。AI 撰写文章 + 为每个段落生成上下文配图 + 生成封面图。触发词：生成图文文章、article-with-images、带图文章、写文章配图、图文文章、图文笔记"
---

<role>Obsidian 图文文章生成专家。根据主题或参考资料生成结构化文章，并为每个段落生成上下文配图和封面图。</role>
<purpose>一键生成视觉丰富的 Obsidian 文章。输入主题或来源，输出带封面图和段落配图的完整笔记。</purpose>

<philosophy>
**核心理念：文字 + 配图 = 双通道认知。**

- 每个段落配图强化理解，不是装饰
- 封面图传递文章核心意象
- 风格统一，视觉语言一致
- 图片服务于内容，不喧宾夺主
- 图片生成失败不阻塞文章输出
</philosophy>

<trigger>

```text
触发词：
- 生成图文文章 / 带图文章 / 图文笔记
- article-with-images / write article with images
- 给这个主题写篇文章配图
- 写文章配图 / 图文文章

示例：
- "article-with-images Prompt-Driven Knowledge Sedimentation"
- "帮我生成一篇带图的文章，主题是 AI Agent 经验积累"
- "给这篇笔记配上插图"
- "把这个主题写成图文文章"
```

</trigger>

<gsd:workflow xmlns:gsd="urn:gsd:workflow">
  <gsd:meta>
    <name>article-with-images</name>
    <trigger>生成图文文章、带图文章、article-with-images、写文章配图、图文文章、图文笔记</trigger>
    <requires>Read, Write, Bash, Glob, Grep, AskUserQuestion</gsd:meta>

  <gsd:goal>生成一篇带封面图和段落配图的完整 Obsidian 文章，写入 wiki/{theme}/。</gsd:goal>

  <gsd:phase name="collect-context" order="1">
    <gsd:step>读取 OBSIDIAN_REPO 路径</gsd:step>
    <gsd:step>识别输入类型：主题关键词 / 现有笔记路径 / URL</gsd:step>
    <gsd:step>确定目标主题目录 wiki/{theme}/</gsd:step>
    <gsd:step>收集文章元数据：标题、风格偏好</gsd:step>
    <gsd:checkpoint>输入来源、目标目录、风格偏好已确认</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="write-and-illustrate" order="2">
    <gsd:step>撰写文章正文（4-8 个段落，800-2000 字）</gsd:step>
    <gsd:step>为每个段落生成英文配图提示词（使用风格预设）</gsd:step>
    <gsd:step>并行生成所有图片（封面 + 段落配图）</gsd:step>
    <gsd:step>验证图片有效性，失败的重试或跳过</gsd:step>
    <gsd:checkpoint>文章内容和配图已生成，用户确认</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="assemble-output" order="3">
    <gsd:step>组装最终文章：frontmatter + 封面图 + 正文 + 配图</gsd:step>
    <gsd:step>写入 wiki/{theme}/{slug}.md</gsd:step>
    <gsd:step>更新索引：theme index、global index、log.md、manifest</gsd:step>
    <gsd:checkpoint>文章已写入，索引已更新</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

---

# Article with Images — 图文文章生成

## 配置

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `OBSIDIAN_REPO` | ✅ | — | Obsidian 仓库路径（全局 CLAUDE.md） |
| `IMAGE_PROVIDER` | ❌ | `pollinations` | 图片方案：`pollinations` / `openai` |
| `IMAGE_STYLE` | ❌ | `tech-illustration` | 风格预设名称 |
| `OPENAI_API_KEY` | 条件 | — | OpenAI 方案时必需（环境变量） |

### 图片方案对比

| 方案 | API Key | 费用 | 质量 | 推荐 |
|------|---------|------|------|------|
| **Pollinations.ai** | 不需要 | 免费 | 中等 | 日常使用 |
| **OpenAI DALL-E 3** | `OPENAI_API_KEY` | ~$0.04-0.12/张 | 高 | 正式发布 |

### 风格预设

见 [references/style-presets.md](references/style-presets.md)。常用：

| 预设 | 适用场景 |
|------|---------|
| `tech-illustration`（默认） | 技术、编程、AI |
| `minimal-line` | 概念讲解、方法论 |
| `watercolor` | 人文、创意、随笔 |
| `isometric` | 系统架构、流程 |
| `pixel-art` | 趣味、游戏 |
| `dark-cyberpunk` | 科幻、前沿技术 |

---

## Phase 1: 收集上下文

### 1.1 识别输入

| 输入类型 | 处理 |
|----------|------|
| 主题关键词 | AI 研究并撰写 |
| 现有笔记路径 | 读取 → 改写为图文版本 |
| URL | 抓取 → 提炼为图文文章 |
| 文本内容 | 结构化 + 添加配图 |

### 1.2 确定输出

1. **主题目录**：按 ob-collect 的关键词映射匹配 `wiki/{theme}/`
2. **文章 slug**：标题转 kebab-case
3. **风格**：默认 `tech-illustration`，用户可修改

> 🛑 **Checkpoint** — 输入来源、目标目录、风格已确认

---

## Phase 2: 撰写文章 + 生成配图

### 2.1 撰写文章

结构规范：

```
封面图（1792×1024）
├── 引言段落（150-200 字）
├── 核心段落 × 3-6（200-400 字/段）
└── 总结段落（100-150 字）
```

写作规则：

1. **面向零基础**：不跳过概念解释，术语首次出现需说明
2. **每段一主题**：独立标题，内容自洽
3. **具体例子**：抽象概念必须配实例
4. **总字数 800-2000 字**

### 2.2 规划配图提示词

为每个段落和封面生成英文提示词，使用风格预设的 prefix/suffix：

```
# 封面图
{style_prefix}, {文章核心意象}, cinematic composition, {style_suffix}

# 段落配图
{style_prefix}, {段落核心概念视觉化}, {style_suffix}
```

**提示词规则**：
- 与段落内容强相关，直观表达核心概念
- **不使用文字**（AI 绘图文字效果差）
- 所有图片共用同一风格前缀/后缀，保证一致性
- 封面图加 `cinematic composition` 增强视觉冲击

### 2.3 生成图片

使用 `scripts/generate-image.cjs` 生成图片。**所有图片并行生成**。

#### 准备工作

```bash
# 确保 scripts 依赖已安装（首次执行）
SKILL_DIR="{SKILL.md 所在目录的绝对路径}"
# 无额外依赖，Node.js 原生 fetch 即可
```

#### 并行生成命令

```bash
# 设置变量
IMAGE_DIR="$OBSIDIAN_REPO/wiki/{theme}/images/{slug}"
mkdir -p "$IMAGE_DIR"

# 并行生成：封面 + 所有段落配图（每张用 Bash run_in_background）
# 封面图
node "$SKILL_DIR/scripts/generate-image.cjs" \
  --prompt "封面提示词" \
  --output "$IMAGE_DIR/cover.jpg" \
  --width 1792 --height 1024 --seed 42

# 段落 1 配图
node "$SKILL_DIR/scripts/generate-image.cjs" \
  --prompt "段落1提示词" \
  --output "$IMAGE_DIR/section-1.jpg" \
  --width 1024 --height 1024 --seed 10

# 段落 2 配图（...以此类推）
```

> **重要**：所有图片使用 Bash `run_in_background` 并行生成，然后用 `TaskOutput` 等待完成。封面 1 张 + 段落 3-6 张，总耗时 ≈ 单张耗时。

#### 图片路径规则

- 图片文件用 `.jpg` 后缀（Pollinations 返回 JPEG）
- 存储路径：`$OBSIDIAN_REPO/wiki/{theme}/images/{slug}/`
- 文章中用相对路径引用：`images/{slug}/cover.jpg`

#### 失败处理

- 单张图片失败：跳过该配图，文章中不插入该图片
- 封面图失败：文章仍输出，`cover_image` frontmatter 留空
- 全部失败：降级为纯文字文章，提示用户图片生成不可用

> 🛑 **Checkpoint** — 展示文章结构 + 配图效果，用户确认

---

## Phase 3: 组装输出

### 3.1 文章模板

```markdown
---
article_id: OBA-{随机8位}
tags: [{主题标签}, 图文文章]
type: topic
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
cover_image: "images/{slug}/cover.jpg"
style: "{风格预设名}"
---

# {文章标题}

![cover](images/{slug}/cover.jpg)

## {引言标题}

{引言内容}

![{段落1配图描述}](images/{slug}/section-1.jpg)

## {段落2标题}

{段落2内容}

![{段落2配图描述}](images/{slug}/section-2.jpg)

...

## 总结

{总结内容}
```

### 3.2 写入规则

1. **article_id**：`OBA-{8位随机字母数字}`，生成后验证全局唯一
2. **图片位置**：段落正文之后、下一个标题之前
3. **图片 alt**：简短中文描述（如 `知识积累的闭环流程`）
4. **相对路径**：`images/{slug}/xxx.jpg`，确保 Obsidian 可渲染

### 3.3 索引更新

遵循 ob-collect 的索引规则：

1. `wiki/{theme}/index.md` — 添加文章条目
2. `wiki/index.md` — 添加全局索引
3. `wiki/log.md` — 追加变更日志
4. `.kb/manifest.json` — 添加文件记录

> ✅ **Checkpoint** — 文章已写入，索引已更新

---

## 成功标准

<success_criteria>
完成以下所有项目即视为任务成功：

- [ ] **文章内容**：结构完整，800-2000 字
- [ ] **封面图**：已生成或已优雅降级
- [ ] **段落配图**：≥ 3 张，风格统一
- [ ] **Frontmatter**：article_id、tags、type、cover_image 齐全
- [ ] **图片路径**：相对路径，Obsidian 可渲染
- [ ] **索引更新**：theme index、global index、log.md 已更新
</success_criteria>
