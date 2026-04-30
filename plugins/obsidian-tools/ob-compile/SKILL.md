---
name: ob-compile
description: "将 raw/ 层已有的资料编译到 wiki/{theme}/，支持增量更新和按主题合并编译"
argument-hint: '[--author <作者名>] [--mode incremental|full|thematic] [--theme <主题目录>]'
---

<role>
Obsidian raw→wiki 编译器。将 raw/ 层已有的资料按主题归纳编译到 wiki/{theme}/，生成结构化 wiki 笔记并更新索引。独立于 ob-collect 的采集流程，专注于编译环节。
</role>

<purpose>
当用户需要将已采集到 raw/ 的资料编译归纳到 wiki 层时使用。支持单篇编译、按主题合并编译、增量更新已有 wiki 三种模式。
</purpose>

<trigger>

```text
触发词：
- 编译到 wiki / 编译 raw / 编译归纳
- ob-compile / compile
- 把 raw 编译到 wiki
- 增量编译 / 更新 wiki
- 重新编译 / 全量编译

示例：
- "ob-compile 王站岗"
- "编译王站岗的 raw 到 wiki"
- "增量编译王站岗新视频"
- "重新编译王站岗全部 wiki"
- "把 raw/战国时代_姜汁汽水/ 编译到 wiki"
```

</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>ob-compile</name>
    <trigger>编译到 wiki、ob-compile、编译 raw、增量编译、重新编译</trigger>
    <requires>OBSIDIAN_REPO,Read,Write,Edit,Bash,Glob,Grep,AskUserQuestion</requires>
    <checkpoints>
      <checkpoint order="1">已确认编译目标和模式</checkpoint>
      <checkpoint order="2">已确认主题分类方案</checkpoint>
      <checkpoint order="3">编译完成并验证输出</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>只读取 raw/ 层已有文件，不执行采集</constraint>
      <constraint>主题合并编译的文件名不加日期前缀（活文档）</constraint>
      <constraint>增量更新时不覆盖已有 wiki 的结构，追加新内容</constraint>
      <constraint>全量重编译时覆盖已有 wiki 文件</constraint>
      <constraint>每个 wiki 文件必须有唯一 article_id</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>将 raw/ 层资料编译归纳到 wiki/{theme}/，更新索引。</gsd:goal>

  <gsd:phase name="scan" order="1">
    <gsd:step>获取 OBSIDIAN_REPO 路径</gsd:step>
    <gsd:step>扫描 raw/{author}/ 下的文件，统计已编译和未编译数量</gsd:step>
    <gsd:step>确认编译模式和目标范围</gsd:step>
    <gsd:checkpoint>用户确认编译目标和模式</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="classify" order="2">
    <gsd:step>按文件标题/内容关键词自动分类到主题</gsd:step>
    <gsd:step>展示分类结果供用户调整</gsd:step>
    <gsd:checkpoint>用户确认主题分类方案</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="compile" order="3">
    <gsd:step>按主题分组，并行启动 Sub Agent 编译</gsd:step>
    <gsd:step>每个 Sub Agent 读取 raw 文件并生成 wiki 归纳笔记</gsd:step>
    <gsd:step>验证所有输出文件和 article_id 唯一性</gsd:step>
    <gsd:checkpoint>编译完成并验证</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="index" order="4">
    <gsd:step>更新 wiki/{theme}/index.md</gsd:step>
    <gsd:step>更新 wiki/index.md</gsd:step>
    <gsd:step>更新 wiki/log.md</gsd:step>
    <gsd:step>更新 raw/index.md（作者索引）</gsd:step>
    <gsd:step>将已编译的 raw 文件 status 改为 compiled</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Obsidian raw→wiki 编译 (ob-compile)

## 配置检查

1. 从全局 CLAUDE.md 获取 `OBSIDIAN_REPO` 路径
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 确认 `raw/` 和 `wiki/` 目录存在

## Phase 1: 扫描与目标确认

### 1.1 识别编译目标

根据用户输入确定编译目标：

| 输入 | 目标 |
|------|------|
| `ob-compile 王站岗` | `raw/王站岗/` 下所有文件 |
| `ob-compile --author 王站岗` | 同上 |
| `ob-compile` （无参数） | 扫描所有 `raw/{author}/` 和 `raw/{category}/`，展示可编译列表供选择 |

### 1.2 扫描 raw 层

```bash
# 统计目标目录下文件数量和编译状态
grep -l "status: uncompiled" raw/{author}/*.md | wc -l   # 未编译
grep -l "status: compiled" raw/{author}/*.md | wc -l     # 已编译
ls raw/{author}/*.md | wc -l                               # 总数
```

### 1.3 确认编译模式

| 模式 | 触发条件 | 行为 |
|------|----------|------|
| **增量** (incremental) | 默认；已有 wiki 存在时 | 只编译 `status: uncompiled` 的 raw 文件，追加到已有 wiki |
| **全量** (full) | 用户说"重新编译"/`--mode full` | 重新编译所有 raw 文件，覆盖已有 wiki |
| **主题合并** (thematic) | raw 文件 ≥ 20 篇时默认推荐 | 按主题分组，每组生成一篇综合 wiki（活文档） |

展示扫描结果，让用户确认编译模式。

> ⚠️ **Checkpoint** — 用户确认编译目标和模式后继续

## Phase 2: 主题分类

### 2.1 自动分类

读取所有 raw 文件的 frontmatter（标题、tags、source）和前 20 行内容，按关键词自动分类：

| 主题 | 目录 | 关键词 |
|------|------|--------|
| AI 技术 | `wiki/ai/` | AI, LLM, GPT, transformer, 机器学习 |
| Claude 生态 | `wiki/claude/` | Claude, Claude Code, Skills, MCP |
| 开发工具 | `wiki/dev-tools/` | VSCode, IDE, CLI, Git |
| 前端开发 | `wiki/front-end/` | React, JavaScript, TypeScript, CSS |
| 时事分析 | `wiki/current-affairs/` | 经济, 政治, 金融, 投资, 股市 |
| 职业发展 | `wiki/career/` | 职级, 面试, 职业规划 |
| Obsidian | `wiki/obsidian/` | Obsidian, 知识管理 |

无匹配时归入最接近的主题，或自动创建新主题目录。

### 2.2 子主题分类（主题合并模式）

在主题目录内，进一步按内容关键词分组。例如时事分析下的子主题：
- 投资哲学/方法论
- 个股分析/估值
- 美股/港股/商品
- 实盘操作/战绩
- 市场复盘

### 2.3 展示分类结果

```
📁 编译分类方案：
├── 时事分析 (current-affairs/)
│   ├── 投资哲学与方法论 → 王站岗-投资哲学与方法论.md (21 篇)
│   ├── 个股分析与估值 → 王站岗-个股分析与估值.md (53 篇)
│   ├── 美股港股与商品投资 → 王站岗-美股港股与商品投资.md (36 篇)
│   ├── 实盘操作与战绩 → 王站岗-实盘操作与战绩.md (19 篇)
│   └── A股市场复盘编年 → 王站岗-A股市场复盘编年.md (163 篇)
└── [其他主题...]
```

> ⚠️ **Checkpoint** — 用户确认分类方案后继续（可调整分组、合并或拆分）

## Phase 3: 编译执行

### 3.1 编译策略

| 任务数 | 策略 |
|--------|------|
| 1-4 篇 raw → 1 篇 wiki | 主会话直接处理 |
| 5-50 篇 raw → 1 篇 wiki | 1 个 Sub Agent |
| 多组主题 | 并行 Sub Agent（≤ 4 并发） |

### 3.2 Sub Agent 编译指令

每个 Sub Agent 接收：
1. 分配的 raw 文件列表
2. 输出 wiki 文件路径
3. 编译模板和规则
4. article_id 生成指令

### 3.3 编译模板

#### 主题合并编译（活文档，无日期前缀）

```markdown
---
article_id: OBA-{随机8位}
tags: [{主题标签}, {作者名}, 归纳]
type: summary
updated_at: {YYYY-MM-DD}
---

# {作者}：{主题标题}

> **作者**: {author}
> **来源**: {来源平台}
> **提取时间**: {date}
> **涵盖视频/文章**: {N} 个

---

## 核心观点

### 1. {观点标题}

简明扼要地概括这个观点（2-5句话）。

→ [[raw/{author}/{filename}#M:SS]]

### 2. {观点标题}
...

## 关键引用

> [原文金句1] — [[raw/{author}/{filename}]]

## 我的思考

[待补充]

---
#音频笔记 #{author} #{主题} #归纳
```

#### 单篇编译（保留日期前缀）

```markdown
---
article_id: OBA-{随机8位}
tags: [{主题标签}, {作者名}, 归纳]
type: summary
updated_at: {YYYY-MM-DD}
---

# {标题} - 归纳

> **作者**: {author}
> **来源**: {url}
> **原文**: [[raw/{author}/{filename}]]

## 核心观点

### 1. {观点标题}

概括 + [[raw/{author}/{filename}#M:SS]]

## 关键引用

> [金句] — [[raw/{author}/{filename}]]

## 我的思考

[待补充]
```

### 3.4 编译规则

1. **观点拆解**：将内容拆解为 5-10 个核心观点，每个有独立标题
2. **raw 引用**：每个观点必须用 `[[raw/{author}/{filename}#M:SS]]` 链接
3. **不搬运原文**：归纳用自己的话概括
4. **金句引用**：选取 3-5 条原文中最有表达力的原话
5. **综合归纳**：跨文件综合提炼（主题合并模式），不逐文件搬运
6. **不做延伸**：只归纳 raw 中已有的观点

### 3.5 article_id 生成与验证

```bash
# 生成
python3 -c "import random,string; print(''.join(random.choices(string.ascii_lowercase+string.digits,k=8)))"

# 验证唯一性
grep -rh "OBA-{生成的ID}" "$OBSIDIAN_REPO/wiki/" --include="*.md"
```

### 3.6 增量更新已有 wiki

读取已有 wiki 文件，追加新 raw 内容的归纳：
- 在已有核心观点后追加新观点
- 更新 frontmatter 的 `updated_at`
- 更新涵盖数量
- **文件名不变**

### 3.7 全量重编译

直接覆盖已有 wiki 文件，重新生成全部内容。

> ⚠️ **Checkpoint** — 所有 Sub Agent 完成后，验证输出文件

## Phase 4: 更新索引

### 4.1 更新内容

| 文件 | 操作 |
|------|------|
| `wiki/{theme}/index.md` | 追加新文章条目 |
| `wiki/index.md` | 更新文章总数、主题篇数 |
| `wiki/log.md` | 追加编译日志 |
| `raw/index.md` | 添加或更新作者条目 |

### 4.2 更新 raw 文件状态

将已编译的 raw 文件的 frontmatter `status` 从 `uncompiled` 改为 `compiled`。

### 4.3 日志格式

```markdown
## [{date}] compile | {标题}

### 批次概要

- **来源**: raw/{author}/
- **编译模式**: thematic/incremental/full
- **输出目录**: wiki/{theme}/

### 生成文件

| 主题 | 文件 | article_id | raw 篇数 |
|------|------|-----------|----------|
| {主题} | {filename} | OBA-{id} | {N} |
```

## 文件命名规范

| 编译模式 | 命名格式 | 示例 |
|----------|----------|------|
| 主题合并 | `{作者}-{主题}.md`（无日期前缀） | `王站岗-投资哲学与方法论.md` |
| 单篇编译 | `{YYYY-MM-DD}-{slug}.md` | `2026-04-30-大电池单日涨15%-归纳.md` |
| 增量更新 | 保持原文件名不变 | — |
