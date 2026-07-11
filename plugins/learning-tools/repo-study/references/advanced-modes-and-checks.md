# 高级产出、同步、问答与验收流程

> 仅在进入教程、文章、实操、同步、翻译、蒸馏、Answer 或最终验收阶段时读取。

## 目录

- [教程与技术展示文章](#phase-6b-教程两阶段工作流-tutorial)
- [实操手册](#phase-6e-实操手册生成-practice)
- [Obsidian 同步与文档翻译](#phase-8-同步到-obsidian-sync)
- [蒸馏与问答](#phase-9-蒸馏-distill)
- [成功标准](#成功标准)
- [参考文档索引](#参考文档)

## Phase 6b: 教程两阶段工作流 (tutorial)

> 适用场景：研究的项目是工具/CLI/库，需要可执行教程时使用。
> 产出文件：`explorer/NN-{repo-name}-how-to-use-guide.md`（带编号）
>
> 📖 **完整教程工作流文档** → `references/tutorial-workflow.md`

---

## Phase 6c: 技术展示文章 (article)

> 适用场景：将研究成果对外分享到掘金/知乎等技术社区。
> 产出文件：`notes/{repo-name}-article.md`（非教程性质）
> 前置条件：至少完成过一轮研究（explorer/ 中有研究笔记）
>
> 📖 **完整文章模式指南** → `references/article-mode-guide.md`

### Step 6c.1: 研究素材收集

1. 读取 `explorer/` 和 `notes/` 目录下所有已有研究笔记
2. 读取源码中的 README、SKILL.md 等项目自述文档
3. 识别项目的「认知颠覆点」和「设计哲学」
4. 汇总素材清单

### Step 6c.2: 启动文章生成 subagent

使用 `references/article-mode-guide.md` §3 的 subagent prompt 模板，启动 Explore 类型 subagent 生成文章。

**输入**：
- 已有研究笔记内容摘要
- 项目自述文档关键内容
- 文章叙事模板（6 段式）

**输出**：
- 完整的面向技术社区的展示文章（3000-5000 字 Markdown）

### Step 6c.3: 质量检查

对照 `references/article-mode-guide.md` §4 质量检查清单逐项验证。

### Step 6c.4: 沉淀文章

1. 写入 `notes/{repo-name}-article.md`（文章为非教程性质，放入 notes/）
2. 更新 `.study-meta.json` 的 `topics[]` 进度
3. 在文章 frontmatter 中标注素材来源笔记

---

## Phase 6e: 实操手册生成 (practice)

> 适用场景：用户要求对工具/CLI 的命令进行逐个实测验证，生成可复现的操作手册。
> 产出文件：`practices/{topic}-practice.md`（不带编号，按主题命名）
> 前置条件：项目已完成 survey（surveyState = "completed"）+ 环境已配置（Phase 1 通过）

### Step 6e.1: 识别实操范围

1. 从用户请求中提取要验证的范围（如"B 站的所有命令"、"browser 命令"）
2. 从 explorer/ 和 notes/ 中提取已有研究素材，列出待验证的命令清单
3. 展示命令清单（命令 → 说明 → 认证模式），用户确认范围

### Step 6e.2: 逐个验证

1. 按分组逐个执行命令（如按功能模块、认证模式分组）
2. 每个命令记录：输入命令 → 真实输出 → 状态（✅/❌/⚠️）
3. 失败的命令：标注错误原因和替代方案
4. 可并行的命令使用 Bash 工具并行执行

### Step 6e.3: 写入实操手册

1. 创建 `practices/` 目录（如不存在）
2. 写入 `practices/{topic}-practice.md`，结构如下：

```markdown
---
article_id: OBA-xxx
title: {标题}
description: {一句话说明}
date: YYYY-MM-DD
status: verified
environment:
  opencli: x.x.x
  ...
---

# {标题}

> 所有命令均已在 YYYY-MM-DD 实测通过。

## 前置条件
（环境检查命令和期望输出）

## 命令全景
（表格：命令 / 功能 / 认证模式 / 实测状态）

## 第 1 章：xxx
（分章节，每章包含：命令 → 真实输出 → 说明）

## 已知问题
（表格：问题 / 影响 / 解决方案）

## 命令速查表
（紧凑的命令列表）
```

3. 写入时立即生成 `article_id` 并写入 frontmatter
4. 更新 `.study-meta.json` 的 `topics[]`（location: "practices"）
5. 更新 CLAUDE.md 笔记索引

### Step 6e.4: 同步到 Obsidian

执行 Phase 5.5 自动同步检测（包括 practices/ symlink）。

---

## Phase 8: 同步到 Obsidian (sync)

当用户使用 `/repo-study sync` 时：

1. 读取 CLAUDE.md 配置中的 `OBSIDIAN_REPO` 和 `GitHub 项目目录`
2. 目标目录：`{OBSIDIAN_REPO}/wiki/open-source/`
3. 扫描 `{GitHub 项目目录}/*-study` 下所有项目
4. **为缺少 `article_id` 的笔记自动分配 `OBA-xxx`**：
   - 格式：`OBA-{8位随机小写字母数字}`
   - 全局唯一性校验：在 OB 仓库 wiki/ 下搜索确认无碰撞
   - 生成后写入 frontmatter（无 frontmatter 时自动创建）
5. 对每个有笔记的项目：
   - 创建 `wiki/open-source/{project}/explorer` symlink → `{study项目}/explorer`
   - 创建 `wiki/open-source/{project}/notes` symlink → `{study项目}/notes`
   - 创建 `wiki/open-source/{project}/practices` symlink → `{study项目}/practices`（如存在）
   - 创建 `wiki/open-source/{project}/Question.md` symlink → `{study项目}/Question.md`（如存在）
   - 若 `index.md` 不存在，生成仓库概述页（含笔记列表和 article_id）
6. 重新生成 `wiki/open-source/index.md` 总索引
7. 输出同步结果摘要

> 📝 **同步脚本** → `scripts/repo-study-sync-ob.sh`（支持 `--dry-run` 和 `--project` 参数）

---

## Phase 8b: 文档翻译 (translate)

当用户使用 `/repo-study translate` 时：

1. 在 study 项目根目录运行翻译计划脚本：

```bash
scripts/repo-study-translate.sh --json
```

2. 读取任务清单中的 `tasks[]`（字段：`source`、`target`、`group`）  
   约束：`target` 必须是 `source` 对应的 `*.zh.md`

3. 按 `group` 字段并行派发 subagent（每组一个），只读源文件，只写目标 `*.zh.md`，禁止修改源文件

4. 默认跳过已存在的 `*.zh.md`  
   若用户明确要求全量重译，使用：

```bash
scripts/repo-study-translate.sh --json --force
```

6. 主会话收集各 subagent 结果并输出：
   - 成功翻译数
   - 失败文件列表（含错误原因）
   - 跳过文件数（已存在）

> 📝 **翻译计划脚本** → `scripts/repo-study-translate.sh`（支持 `--json`、`--force`、`--group-size`）
>
> 📝 **subagent prompt 模板与质量规则** → `references/translate-mode-guide.md`

---

## Phase 9: 蒸馏 (distill)

当用户使用 `/repo-study distill` 时：

### Step 9.1: 读取 Backlog

读取 `.study-meta.json` 的 `backlog[]` 数组，按 `priority` 排序（high > medium > low），过滤 `status: "pending"` 的条目。

### Step 9.2: 展示待蒸馏列表

以表格展示（ID / 标题 / 类型 / 优先级 / 来源笔记），用户选择条目。

### Step 9.3: 创建 Demo 工程（type=demo）

创建 `demos/{demo-name}/`（含 `package.json` + `index.mjs` + `README.md`）。README 需包含：学习目的、验证知识点、功能清单（MUST/SHOULD/COULD）、运行命令、预期输出。

验证独立运行：`cd demos/{name} && npm install && node index.mjs`

### Step 9.4: 创建设计文档（type=skill-design）

为 `skill-design` 类型的条目在 `notes/` 下生成 skill 设计文档。

### Step 9.5: 更新状态

更新 `backlog[]` 状态（`pending` → `in-progress` → `done`），更新 `demoPath`，将 artifact 添加到关联 topic 的 `artifacts[]`。

### 添加条目到 Backlog

在 Phase 5a/5b 研究过程中，当发现**可复用、自包含的模式**时，应自动追加到 `backlog[]`：

- **ID 格式**：`bl-{NNN}`，从当前最大值递增
- **type**：`demo`（代码模式）/ `skill-design`（设计概念）/ `note`（文档补充）
- **priority**：根据通用性和复杂度判定 `high` / `medium` / `low`
- **sourceNote**：指向发现该模式的研究笔记路径

---

## Phase 10: 问答 (answer) — 补充研究笔记中看不懂的地方

当用户使用 `/repo-study answer` 时：

> **核心理念**：因为看不懂，所以才有这个文件。用户边看笔记边记录困惑，AI 读取后补充对应笔记内容。

### Step 10.0: 前置检查

1. 检查当前目录是否为有效 study 项目（目录名 `*-study` + `.study-meta.json`）
2. 检查 `Question.md` 是否存在于项目根目录
3. 若 `Question.md` 不存在，提示"当前项目尚未生成 Question.md"
4. **检查历史批次文件**：扫描目录中是否有 `Question-*.md` 临时文件，如果有 `status: pending` 的未处理批次，提示用户：
   - "发现未处理的历史批次 Question-{N}.md，是否先处理？"
   - 用户选择：先处理历史 / 忽略，继续处理 Question.md

### Step 10.1: 读取 Question.md

1. 读取 `Question.md` 全文
2. 提取一级标题（`# Question`）以下的所有内容，分为两部分：
   - **(A) 顶部自由内容**：`# Question` 之后、第一个 `## OBA-xxx` 之前的所有非空内容（整体建议、反馈、优化想法等）
   - **(B) article_id sections**：所有 `## OBA-xxx` section 及其下用户内容
3. 若 (A) 和 (B) 均为空，提示"没有待处理的问题"并退出
4. **(A) 类内容的处理方式**：整体建议/反馈类内容直接在主会话处理（如文件移动、结构调整、skill 优化等），不需要启动 subagent

### Step 10.2: 展示问题概况

**如果存在 (A) 顶部自由内容**，优先展示：

| # | 类型 | 内容摘要 |
|---|------|---------|
| * | 整体建议 | {前 80 字} |

**然后展示 (B) article_id sections**：

| # | Article ID | 对应笔记 | 内容摘要 |
|---|-----------|---------|---------|
| 1 | OBA-xxx | explorer/01-xxx.md | {前 50 字} |
| 2 | OBA-yyy | notes/xxx.md | {前 50 字} |

> 📝 **对应笔记查找**：在 `explorer/` 和 `notes/` 中搜索含该 `article_id` 的文件。

### Step 10.3: 用户选择

使用 AskUserQuestion 询问：
1. 全部处理（N 个 section）
2. 选择部分处理
3. 取消

### Step 10.3b: 立即拆分（避免编辑冲突）

> **核心目的**：用户确认处理范围后，**立即**将待处理内容提取到临时文件，同时**立即**清理 Question.md。这样 Question.md 马上可以被用户继续编辑，subagent 慢慢处理临时文件即可。

用户选择完成后、启动 subagent **之前**，立即执行以下操作：

**1. 生成临时批次文件**：
- 文件名：`Question-{N}.md`（N 从 1 递增，扫描目录中已有 `Question-*.md` 取最大 N+1）
- 位置：项目根目录（与 Question.md 同级）
- 内容：将待处理的顶部自由内容 + 待处理的 article_id sections **原样复制**到临时文件

```markdown
---
title: "Question - 待处理批次 {N}"
type: question-batch
source: Question.md
created_at: "{YYYY-MM-DD}"
status: pending
sections:
  - {OBA-xxx}
  - {OBA-yyy}
---

# 待处理问题（批次 {N}）

{待处理的顶部自由内容，原样复制}

## {OBA-xxx}
{原始 section 内容}

## {OBA-yyy}
{原始 section 内容}
```

**2. 立即清理 Question.md**（此步骤完成后用户即可安全编辑）：
- 删除顶部自由内容中已被提取的部分（`# Question` 说明行之后、第一个 `## OBA-xxx` 之前已选处理的内容）
- 删除已选处理的 article_id sections（整个 `## {article_id}` + 其下所有内容直到下一个 `## OBA-xxx` 或文件末尾）
- 未选择的 sections 保持不动
- 更新 frontmatter 的 `updated_at`

**3. 输出提示**：告知用户 `已从 Question.md 中提取 {N} 个 section 到 Question-{M}.md，原文件已清理，可继续编辑`

### Step 10.4: AI 拆解（Multi Teams 并行）

> **注意**：此步骤基于 Step 10.3b 生成的临时批次文件（`Question-{N}.md`），不再直接读取 Question.md。

**对于 (A) 顶部自由内容**：直接在主会话中分析处理（从临时批次文件读取），不启动 teammate。根据内容类型决定处理方式：
- 文件移动/重命名 → 直接执行
- 目录结构调整 → 直接执行
- repo-study skill 改进建议 → 记录到 jacky-skills 项目的改进 backlog 或直接修改 skill
- 其他反馈 → 讨论后执行

**对于 (B) article_id sections**：使用 **Multi Teams 模式并行处理**，每个 section 分配一个独立 teammate：

#### Step 10.4a: 创建团队和任务

1. **TeamCreate**：创建团队 `answer-{N}`（N 为批次编号）
2. **TaskCreate**：为每个待处理的 article_id section 创建独立任务，描述中包含：
   - section 的 article_id
   - 临时批次文件路径（`Question-{N}.md`）
   - 对应笔记的查找方式（通过 article_id 在 explorer/ 和 notes/ 中搜索 frontmatter）
   - 源码路径
   - 期望输出格式

#### Step 10.4b: 并行派发 teammates

为每个 section spawn 一个 **general-purpose** 类型 teammate（带 `team_name` 和唯一 `name`，如 `answer-1-OBA-xxx`）：

**teammate prompt 模板**：

```
你是代码分析和知识补充专家。

你被分配了一个具体的研究问题，请完成以下任务：

1. 读取批次文件 {Question-{N}.md} 中你负责的 section: {article_id}
2. 通过 article_id 在 explorer/ 和 notes/ 中搜索 frontmatter，找到对应的研究笔记
3. 读取该笔记全文，理解现有内容结构
4. 理解用户写的内容（可能是问题、困惑、"看不懂"、需要补充示例等）
5. 分析源码 {源码路径}，找到答案或补充材料
6. 提出具体补充方案

**源码路径**: {项目目录}/{repo-name}/
**研究笔记路径**: {项目目录}/explorer/ 和 {项目目录}/notes/
**批次文件路径**: {Question-{N}.md}
**你的 section**: {article_id}

**输出格式**：
- **对应笔记**: {找到的笔记路径}
- **用户诉求**: {对用户内容的理解，1-2 句}
- **补充内容**: {可直接写入笔记的 Markdown 内容}
- **插入位置**: {在笔记中的哪个 section 之后插入，如"## 三、xxx 之后"}
```

每个 teammate：
- 通过 TaskUpdate 将任务标记为 `in_progress`
- 独立读取批次文件、研究笔记、源码
- 生成补充方案并通过 SendMessage 返回给 team lead
- 通过 TaskUpdate 将任务标记为 `completed`

#### Step 10.4c: 收集结果

主会话（team lead）通过 TaskList 监控进度，收集各 teammate 返回的补充方案。

### Step 10.5: 执行补充

主会话（team lead）收到所有 teammate 的分析结果后：

1. **关闭团队**：`SendMessage` shutdown 所有 teammates，然后 `TeamDelete` 清理团队资源
2. 对每个 section 的结果：
   - 找到对应的研究笔记文件
   - 将补充内容插入到指定位置
   - 保留原有内容，只做追加/补充
3. 展示补充摘要给用户确认

### Step 10.6: 标记批次完成

> **注意**：Question.md 的清理已在 Step 10.3b 中完成，此步骤只需更新临时批次文件状态。

用户确认所有内容（顶部自由内容 + article_id sections）已处理后：

1. 更新临时批次文件（`Question-{N}.md`）的 frontmatter：`status: pending` → `status: done`
2. **自动删除已完成的批次文件**（`Question-{N}.md`），避免目录残留
3. 如果所有 section 均已处理且 Question.md 只剩空壳（frontmatter + 标题 + 说明），无需额外操作（Step 10.3b 已处理）

### Step 10.7: 输出摘要

```
✅ 已处理 {N} 个 section，补充了 {M} 篇笔记

| Article | 笔记 | 补充内容 |
|---------|------|---------|
| OBA-xxx | explorer/01-xxx.md | 补充了 sqlite3 使用场景说明 |
| OBA-yyy | notes/xxx.md | 添加了 B 站视频测试示例 |

📁 批次文件: Question-{K}.md（status: done，可手动删除）
```

<!-- ========== 命令速查 ========== -->
<commands>

| 命令 | 说明 |
|------|------|
| `/repo-study` | 显示帮助信息（命令速查 + 用法示例） |
| `/repo-study <url> <问题>` | 研究 GitHub 仓库的特定问题（自动判断 Survey/Incremental 模式） |
| `/repo-study list` | 列出 GitHub 项目目录下所有 xxx-study 项目 |
| `/repo-study status` | 检查当前目录状态（topics、进度、skill 封装状态、当前模式） |
| `/repo-study update` | 强制更新源码到最新版本 |
| `/repo-study continue` | 恢复上次中断的交互学习 |
| `/repo-study sync` | 同步所有 study 项目到 Obsidian（article_id 分配 + symlink + 索引） |
| `/repo-study translate` | 使用 subagent 并行翻译文档到 `*.zh.md`（不改原文） |
| `/repo-study distill` | 将研究发现转化为独立 demo 工程或设计文档 |
| `/repo-study answer` | 回答 Question.md 中的研究问题，回答后自动归档 |

**路由规则**：空值/help → 帮助信息；子命令关键词 → 对应 Phase；含 URL → 研究模式；其他 → 在当前项目增量问答。

</commands>

<!-- ========== 四种场景速查 ========== -->
<scenarios>

```
/repo-study 场景速查：

入口:   route      → 空值/help→帮助 | 子命令→对应Phase | URL→研究 | 其他→增量问答
场景 0: list      → 列出所有 *-study 项目
场景 1-3: detect  → create / update / skip（自动判断）
场景 3.5: mode    → Survey（首次，产出→explorer/）/ Incremental（增量，产出→notes/）
场景 4: style     → yolo（快速研究）/ interactive（交互教学）——仅 Survey 模式
场景 5: research  → Survey→explorer/ | Incremental→notes/
场景 5.5: auto-sync → 研究完成后自动检测 Obsidian → 询问是否同步（仅当前项目）
场景 5c: 增量问答  → 针对性 subagent → notes/{topic}.md → auto-sync
场景 5d: 实操验证  → 逐个命令验证 → practices/{topic}-practice.md → auto-sync
场景 6: output    → 指南 / 教程 / 模板 / Cheat Sheet / 小白指南 / 技术展示文章 / Skill 映射 / 实操手册 / 全部
场景 7: continue  → 恢复交互学习
场景 8: sync      → 同步到 Obsidian（article_id + symlink + 索引）
场景 8b: translate → 并行 subagent 翻译 *.md → *.zh.md
场景 9: distill   → backlog → demo 工程 / skill 设计文档
场景 10: answer   → 读取 Question.md → Multi Teams 并行回答（每个 section 一个 teammate）→ 补充笔记 → 归档已解决 + TeamDelete

安全保障：explorer/、notes/ 和 practices/ 永不删除 | 版本检查：gh api commit SHA
```

</scenarios>

<!-- ========== 成功标准 ========== -->
<success_criteria>
- [ ] 正确解析仓库 URL，项目路径从 CLAUDE.md 读取
- [ ] 检测 study 标识（目录名 + .study-meta.json），使用 gh api 检查远程版本
- [ ] 项目创建时包含 explorer/、notes/ 和 practices/ 三个目录
- [ ] 项目创建/更新时，explorer/、notes/ 和 practices/ 目录永不删除
- [ ] 双模式检测：根据 surveyState 自动判断 Survey/Incremental 模式
- [ ] Survey 模式：产出成体系笔记到 explorer/，文件名带 2 位索引前缀（00- 环境准备 + 01- 正式内容），完成后设置 surveyState = "completed"
- [ ] Incremental 模式：产出零散笔记到 notes/，针对用户问题分析
- [ ] 文档资源扫描：检测 docs/、README.md 等文档并分类
- [ ] Yolo 模式：文档感知 subagent → 代码分析 subagent → Capability Discovery subagent（穷举可操作能力）→ 合并输出到 explorer/（带编号）+ 自动生成 Cheat Sheet
- [ ] 交互模式：subagent 调研 → 概念拆解 → 逐步讲解 → 实时归档到 explorer/（带编号）
- [ ] 首次研究强制生成导读指南 explorer/NN-{repo-name}-guide.md（带编号）
- [ ] 工具/CLI/库项目首次研究时生成环境准备章节 explorer/00-{repo-name}-environment-setup.md
- [ ] 产出路径规则：环境准备→explorer/00-（固定），成体系→explorer/01+（带编号），速查卡片→explorer/cheatsheet/（不带编号），零散→notes/（不带编号），实操手册→practices/（不带编号，按主题命名）
- [ ] 教程两阶段分离：T1 配置引导（人工）+ T2 逐章实测（subagent）
- [ ] 技术展示文章：素材收集 → subagent 生成 → 质量检查 → 沉淀到 notes/
- [ ] Cheat Sheet 专属 subagent（Phase 6d）：识别维度 → subagent 提炼 → 沉淀到 explorer/cheatsheet/ → 更新索引（YOLO 模式下与 Capability Discovery 合并执行）
- [ ] 翻译：*.md → *.zh.md，不修改源文件，按 group 并行
- [ ] sync：article_id 分配 + symlink（覆盖 explorer/、notes/、practices/ 和 Question.md）+ 索引生成
- [ ] distill：backlog → 独立可运行的 demo 工程
- [ ] Question.md：项目创建时自动生成（含 AI 预设问题），sync 时通过 symlink 同步到 Obsidian
- [ ] answer：读取 Question.md 的顶部自由内容（整体建议）和 article_id section → 顶部内容主会话直接处理 / article_id Multi Teams 并行拆解补充（每个 section 一个 teammate）→ 清理已处理内容 + shutdown teammates + TeamDelete
- [ ] Skill 项目检测：检测 SKILL.md 存在时标记为 skill-type，提取 skill 名称和脚本列表
- [ ] skill-type 项目：自动生成 skill→script 映射分析 + 脚本验收测试
- [ ] 自动同步检测（Phase 5.5）：研究完成后检测 OBSIDIAN_REPO 配置，路径有效时自动询问是否同步到 Obsidian（仅当前项目），支持跳过和本次会话不再询问
- [ ] 实操手册（Phase 6e）：识别命令范围 → 逐个实测验证 → 写入 practices/{topic}-practice.md（含 article_id）→ 更新索引 → 同步到 Obsidian
- [ ] practices/ 目录：不在 explorer/ 和 notes/ 中，按主题命名（{topic}-practice.md），每步必须有真实输入输出
</success_criteria>

<!-- ========== 参考文档 ========== -->
<references>

| 文件 | 用途 |
|------|------|
| `references/state-templates.md` | **状态模板与检测逻辑**（.study-meta.json v2、status 脚本、版本检查命令） |
| `references/interactive-mode-guide.md` | **交互模式详细指南**（实时归档、思维导图、知识树结构、会话追踪） |
| `references/yolo-mode-guide.md` | **Yolo 模式详细指南**（subagent prompt 模板、输出模板、笔记沉淀、翻译提示） |
| `references/translate-mode-guide.md` | **翻译模式详细指南**（任务分组、subagent prompt、质量规则、失败重试） |
| `references/guide-template.md` | **导读指南完整模板**（产品认知、架构图、文件地图、设计决策等完整结构） |
| `references/tutorial-workflow.md` | **教程两阶段工作流**（T1 配置引导 + T2 逐章实测 + 文件结构模板） |
| `references/anti-patterns.md` | **反模式清单**（6 个常见错误及正确做法） |
| `references/article-mode-guide.md` | **技术展示文章指南**（6 段式叙事模板、subagent prompt、质量检查清单、风格要素） |
| `references/quick-reference.md` | **快速参考**（使用示例、模式说明、常用命令速查） |
| `references/question-template.md` | **Question.md 模板与 Answer 流程**（文件格式、AI 预设问题生成、Phase 10 问答详细设计） |

</references>

---

