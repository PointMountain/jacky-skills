---
name: repo-study
description: "研究 GitHub 仓库的特定技术实现。触发词：调研下、研究下、学习下、看看 xxx 仓库、分析开源项目、repo-study"
argument-hint: '[URL或仓库路径] [研究问题]'
---

<role>
你是一个 GitHub 仓库研究助手。帮助用户快速研究开源项目的特定技术实现，自动管理学习环境，沉淀研究笔记。
</role>

<purpose>
让用户能够用自然语言提问："调研下 xxx 仓库在某个领域是如何实现的"，自动处理项目创建、更新、研究全过程。
</purpose>

<philosophy>
**核心理念：问题驱动，即问即研，以分享角度记录。**

- 用户只关心问题，不关心项目创建细节
- 自动检测项目状态（新建/更新/直接研究）
- 研究结果自动沉淀到笔记
- 研究状态按"主题（topic）"持续归纳，不使用一次性完成态
- 支持同一主题下多问题、多轮产出按需追加
- 研究过程使用 Agent（subagent）执行，主会话负责项目管理和用户交互
- subagent 默认使用蓝色标识（研究任务），支持并行研究多个独立课题
- **写作原则：让完全不懂的人也能看懂**
  - 假设读者是零基础，不跳过基础概念
  - 使用步骤化表达，每个步骤只做一件事
  - 提供完整示例，代码片段要完整可运行
</philosophy>

<trigger>
```
调研下 git@github.com:chris-hendrix/claudehub.git 在 Agent 通信方面是如何实现的
研究下 https://github.com/daymade/claude-code-skills 的 skill 设计模式
看看 get-shit-done 这个项目的 GSD workflow 是怎么设计的
学习下 claudehub 的 prompt engineering 技巧
```
</trigger>

<!-- ========== GSD Workflow XML 结构 ========== -->
<gsd:workflow>
  <gsd:meta>
    <name>repo-study</name>
    <trigger>调研下、研究下、学习下、看看 xxx 仓库、分析开源项目、repo-study</trigger>
    <requires>git, gh, Agent (subagent), Claude Code tools (Glob, Grep, Read, Write, Edit)</requires>
  </gsd:meta>

  <gsd:goal>让用户用自然语言提问，自动完成项目初始化/更新/研究全过程，并按主题沉淀可复用研究资产</gsd:goal>

  <gsd:phase name="list" order="0" condition="用户使用 /repo-study list">
    <gsd:step>读取 CLAUDE.md 中的 GitHub 项目目录配置</gsd:step>
    <gsd:step>扫描该目录下所有 *-study 子目录</gsd:step>
    <gsd:step>读取每个项目的 .study-meta.json（如存在）</gsd:step>
    <gsd:step>输出项目列表表格</gsd:step>
  </gsd:phase>

  <gsd:phase name="detect" order="1">
    <gsd:step>解析仓库 URL 和研究问题</gsd:step>
    <gsd:step>仅在当前目录检测 study 标识（目录名和 .study-meta.json）</gsd:step>
    <gsd:step>判断当前项目是否由 repo-study 创建（v2）</gsd:step>
    <gsd:step>扫描源码中的文档资源：docs/ 目录、README.md、CONTRIBUTING.md、*.md 指南文件</gsd:step>
    <gsd:step>若存在有效项目，强制检查 GitHub 远程版本是否最新</gsd:step>
    <gsd:step condition="本地版本落后">先提示用户是否更新，再决定 update / research 分支</gsd:step>
    <gsd:step>执行 status 脚本汇总课题、进度、skill 封装状态</gsd:step>
    <gsd:checkpoint>根据检测结果选择分支：create / update / research</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="create" order="2" condition="项目不存在">
    <gsd:step>创建项目目录结构</gsd:step>
    <gsd:step>克隆源码（single-branch + depth 1）</gsd:step>
    <gsd:step>删除源码的 .git 目录</gsd:step>
    <gsd:step>生成 CLAUDE.md 和元数据</gsd:step>
    <gsd:step>初始化 Git 仓库</gsd:step>
  </gsd:phase>

  <gsd:phase name="update" order="3" condition="项目存在但不是最新">
    <gsd:step>询问用户是否更新</gsd:step>
    <gsd:step>更新源码到最新版本</gsd:step>
  </gsd:phase>

  <gsd:phase name="mode_select" order="4">
    <gsd:step>询问用户选择研究模式</gsd:step>
    <gsd:step>yolo 模式：直接输出完整研究发现</gsd:step>
    <gsd:step>交互模式：渐进式教学，分步骤讲解</gsd:step>
    <gsd:checkpoint>根据用户选择进入对应分支</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="research_yolo" order="5" condition="选择 yolo 模式">
    <gsd:step>切换到项目目录</gsd:step>
    <gsd:step>若源码存在文档资源（docs/、README.md 等），先启动文档感知 subagent 扫描并提取产品认知和用户指南信息</gsd:step>
    <gsd:step>启动代码分析 subagent（蓝色标识，Explore 类型）执行代码分析</gsd:step>
    <gsd:step condition="多独立课题">并行启动多个 subagent 研究不同课题</gsd:step>
    <gsd:step>主会话合并文档感知 + 代码分析结果，按"产品认知 → 核心概念(含Why) → 代码原理"层次输出完整研究发现</gsd:step>
    <gsd:step>沉淀笔记到 notes/</gsd:step>
    <gsd:step condition="首次研究且 notes/ 中不存在 *-guide.md">强制生成仓库导读指南 notes/{repo-name}-guide.md</gsd:step>
    <gsd:step condition="用户使用中文提问">提示翻译功能</gsd:step>
  </gsd:phase>

  <gsd:phase name="research_interactive" order="5b" condition="选择交互模式">
    <gsd:step>调研阶段：若源码存在文档资源，先启动文档感知 subagent 扫描产品认知信息</gsd:step>
    <gsd:step>启动代码分析 subagent（蓝色标识）静默分析代码</gsd:step>
    <gsd:step>主会话合并文档感知 + 代码分析结果，创建会话状态和概念列表</gsd:step>
    <gsd:step>概念列表按"产品认知 → 核心概念(含Why) → 代码原理"层次排列</gsd:step>
    <gsd:step>概念拆解：将研究发现拆分为多个小概念</gsd:step>
    <gsd:step>逐步讲解：每次只讲一个概念</gsd:step>
    <gsd:step>实时归档：讲解后立即写入文件并更新会话状态</gsd:step>
    <gsd:step>理解确认：询问用户下一步选择</gsd:step>
    <gsd:step condition="需要更多解释">补充解释和示例</gsd:step>
    <gsd:step condition="继续">进入下一个概念</gsd:step>
    <gsd:step condition="暂停">保存进度到会话状态文件</gsd:step>
    <gsd:step>总结确认：所有概念讲解完毕后询问是否需要完整笔记</gsd:step>
    <gsd:step condition="需要">沉淀完整笔记到 notes/</gsd:step>
    <gsd:step condition="首次研究且 notes/ 中不存在 *-guide.md">强制生成仓库导读指南 notes/{repo-name}-guide.md</gsd:step>
  </gsd:phase>

  <gsd:phase name="continue" order="7" condition="用户使用 /repo-study continue">
    <gsd:step>检查会话状态：读取 .study-session.json</gsd:step>
    <gsd:step>显示进度：展示上次进度和待讲解概念</gsd:step>
    <gsd:step>继续学习：从下一个待讲解概念继续交互学习</gsd:step>
  </gsd:phase>

  <gsd:phase name="sync" order="8" condition="用户使用 /repo-study sync">
    <gsd:step>读取 CLAUDE.md 中的 GitHub 项目目录和 Obsidian 仓库路径</gsd:step>
    <gsd:step>扫描所有 *-study 项目的 notes 目录</gsd:step>
    <gsd:step>为缺少 article_id 的笔记自动分配 OBA-xxx（全局唯一、8位随机小写字母数字）</gsd:step>
    <gsd:step>为每个有笔记的项目在 OB 的 wiki/open-source/ 下创建 symlink</gsd:step>
    <gsd:step>生成/更新每个项目的 index.md 概述页（含笔记列表和 article_id）</gsd:step>
    <gsd:step>更新 open-source/index.md 总索引</gsd:step>
  </gsd:phase>

  <gsd:phase name="output" order="6">
    <gsd:step>询问用户下一步：继续研究 / 生成实操指南 / 生成 Skill 模板 / 生成 Cheat Sheet / 生成小白指南 / 全部生成</gsd:step>
    <gsd:step condition="选择指南或全部">生成 {主题}-guide.md（小白可执行的实操指南）</gsd:step>
    <gsd:step condition="选择模板或全部">生成 {主题}-skill.md（可复用的 Skill 模板）</gsd:step>
    <gsd:step condition="选择 Cheat Sheet 或全部">生成 {repo-name}-cheat-sheet.md（速查卡：命令速查 + Before/After 对比 + 决策树）</gsd:step>
    <gsd:step condition="选择小白指南或全部">生成 {repo-name}-beginner-guide.md（零基础完全指南：通俗类比 + 手把手教程）</gsd:step>
    <gsd:step>更新研究日志 RESEARCH-LOG.md</gsd:step>
  </gsd:phase>
</gsd:workflow>

<!-- ========== 执行流程 ========== -->
<process>

## Phase 0: 列表 (list) — 可选

当用户使用 `/repo-study list` 时：

1. 读取 CLAUDE.md 中的 `GitHub 项目目录` 配置（如 `/Users/jiashengwang/jacky-github`）
2. 扫描该目录下所有匹配 `*-study` 的子目录
3. 对每个 study 目录，尝试读取 `.study-meta.json` 获取元数据
4. 输出表格：

| 项目名 | 来源仓库 | Topics 数 | 最后更新 |
|--------|----------|-----------|----------|
| xxx-study | owner/repo | N | YYYY-MM-DD |

5. 对于没有 `.study-meta.json` 的目录，标记为"手动创建"

---

## Phase 1: 检测 (detect)

### Step 1.0: 读取路径配置

读取当前会话加载的 CLAUDE.md 配置（已自动加载），获取：
- **GitHub 项目目录**: 从 CLAUDE.md 中读取 `GitHub 项目目录` 配置值
- 此目录作为所有 study 项目的**父目录**
- 如果配置不存在，使用当前工作目录作为父目录

> 注意：不要硬编码路径，始终从 CLAUDE.md 配置中读取。

### Step 1.1: 解析用户输入

从用户输入中提取仓库 URL、仓库名、研究问题、目标目录。

**URL 解析规则：**
```
git@github.com:user/repo.git → 仓库名: repo, owner: user
https://github.com/user/repo → 仓库名: repo, owner: user
```

### Step 1.2: 检测当前目录状态（仅当前目录）

**核心逻辑（不扫描子目录，不递归）：**
1. 检查当前目录名是否匹配 `*-study`
2. 检查当前目录是否存在 `.study-meta.json`
3. 识别项目来源（repo-study-managed / non-repo-study）
4. 如果是有效 study 项目，必须比对本地和远程 commit SHA
5. 若本地落后远程，先提示用户是否更新

> 📝 **详细检测流程和命令** → `references/state-templates.md`

### Step 1.2a: 文档资源扫描

在检测项目状态后，**扫描源码中的文档资源**，为后续研究提供上下文：

```bash
# 检测文档目录结构
ls {repo-name}/docs/ 2>/dev/null
cat {repo-name}/README.md | head -100
```

**扫描范围**：
| 路径 | 说明 |
|------|------|
| `{repo}/docs/` | 官方文档目录（VitePress、Docusaurus 等） |
| `{repo}/README.md` | 项目自述文件 |
| `{repo}/CONTRIBUTING.md` | 贡献指南 |
| `{repo}/*.md` | 根目录下的指南文件 |

**文档分类**：如果发现文档目录，识别其类型和内容组织方式：
- `docs/.vitepress/config.mts` → VitePress 文档站
- `docs/sidebar.*` 或 `docs/_sidebar.md` → Docsify 文档站
- `docs/docusaurus.config.*` → Docusaurus 文档站

**将扫描结果传递给后续 Phase**，用于：
1. 生成导读指南时引用已有文档
2. subagent 研究时先读文档建立产品认知
3. 笔记中标注"项目已有文档可参考"

### Step 1.3: 运行 status 脚本

```bash
scripts/repo-study-status.sh --json --check-remote
```

脚本输出包含：项目来源、topics 列表、进度统计、skill 封装状态、远程版本状态。

> 📝 **脚本输出格式** → `references/state-templates.md` §5

### Step 1.4: 版本落后时的用户提示

> ⚠️ **Checkpoint - Decision**
>
> 当 `remoteCheck.status == "outdated"` 时，必须提示用户选择更新或继续使用当前版本。

---

## Phase 2: 创建 (create) — 仅当项目不存在时

1. 在 GitHub 项目目录下创建 `{repo-name}-study` 目录（路径从 CLAUDE.md 读取）
2. 浅克隆源码：`git clone --single-branch --depth 1 "$REPO_URL" "$REPO_NAME"`
3. 删除 `.git` 目录
4. 生成 `CLAUDE.md`、`.study-meta.json`（v2）、`scripts/repo-study-status.sh`
5. 初始化 Git 仓库并首次提交

> ⚠️ **Checkpoint - Human-Verify** — 确保文件结构完整后初始化 Git 仓库。

> 📝 **元数据结构** → `references/state-templates.md` §4

---

## Phase 3: 更新 (update) — 仅当项目不是最新时

1. 临时克隆最新代码到 `temp_clone`
2. 只更新源码目录，**保留 notes/ 目录**（永不删除）
3. 更新 `.study-meta.json` 中的 commit SHA
4. 删除临时目录

> ⚠️ **安全检查**: 更新前确认 notes/ 目录不会被删除。

---

## Phase 4: 模式选择 (mode_select)

> ⚠️ **Checkpoint - Decision**
>
> 询问用户选择研究模式：
> 1. **Yolo 模式**（快速）— 直接输出完整研究发现
> 2. **交互模式**（教学）— 分步骤渐进式教学，每步确认理解

---

## Phase 5a: 研究 — Yolo 模式

> 📖 **详细文档** → `references/yolo-mode-guide.md`

### Step 5a.1: 文档感知（如果项目有文档）

若 Phase 1 检测到项目有文档资源（docs/、README 等），先启动**文档感知 subagent**：

```
Agent({
  description: "文档感知分析",
  subagent_type: "Explore",
  prompt: "扫描 {repo-name}/docs/ 和 README.md，提取以下信息：
    1. 产品形态（npm 包？CLI 工具？Web 应用？浏览器插件？）
    2. 安装方式和基本使用命令
    3. 核心组件及其作用
    4. 文档覆盖的主题和结构
    5. 关键的用户指南内容摘要"
})
```

### Step 5a.2: 代码分析

启动 subagent（蓝色标识，Explore 类型）执行代码分析。

### Step 5a.3: 结果合并与输出

主会话按以下层次合并输出：
1. **产品认知**（来自文档感知 subagent）
2. **核心概念 + 前因后果**（来自文档 + 代码综合分析）
3. **代码原理**（来自代码分析 subagent）

### Step 5a.4: 沉淀与指南

1. 沉淀笔记到 `notes/` 并更新 `.study-meta.json` 的 `topics[]`
2. **首次研究强制生成导读指南**：检查 `notes/` 中是否已有 `*-guide.md`，若不存在则生成
3. **可选 Cheat Sheet 生成**：如果项目是工具/库/CLI（有明确安装和使用命令），在首次研究时提示用户是否生成 Cheat Sheet
4. 中文提问时提示翻译功能

**导读指南模板**（蒸馏自 understand-onboard，1200-2000 字）：

```markdown
# {工具名} 使用指南

> 一句话说清楚这个工具是什么、解决什么问题

## 📌 项目概览
**核心价值**：一句话
**技术特征**：2-3 个关键特征
**代码规模**：约 X 行，Y 个源文件

## 🎮 产品认知（必读）

### 这是什么？
用 2-3 句话说清楚这个工具的产物形态：
- 是一个 npm 包？Chrome 插件？命令行工具？Web 应用？
- 用户安装后怎么使用？给出最基础的 1-2 个命令示例
- 它解决什么场景的问题？

### 核心组件
| 组件 | 形态 | 作用 |
|------|------|------|
| 如：CLI 工具 | npm 全局包 `@scope/name` | 命令行入口 |
| 如：Chrome 插件 | 浏览器扩展 | 提供浏览器控制能力 |

### 基本使用方式
1. **安装**：`npm install -g @scope/name`
2. **验证**：`xxx --version`
3. **第一个命令**：`xxx <site> <command>` + 输出示例
4. **输出格式**：`xxx <cmd> -f json/table/yaml`

## 📚 文档资源（如果项目有文档）
> ⚠️ 此项目自带完整的官方文档，以下是资源导航：

| 文档路径 | 内容 | 推荐阅读场景 |
|---------|------|------------|
| `docs/guide/getting-started.md` | 快速开始 | 第一次接触时 |
| `docs/guide/xxx.md` | xxx 指南 | 需要深入了解时 |

**文档站类型**：VitePress / Docusaurus / 纯 Markdown
**是否有多语言**：英文 / 中文

## 🔍 核心概念（含前因后果）

每个核心概念必须回答三个问题：
1. **是什么？** — 用简单语言解释
2. **为什么需要？** — 不用这个技术会怎样？痛点是什么？
3. **怎么实现的？** — 简要说明实现思路

### 概念：{概念名如 BrowserBridge}
- **是什么**：一句话解释
- **为什么需要**：不用它会怎样？对比替代方案的缺陷
- **实现思路**：核心数据流（3-5 步 ASCII 图）

## 🏗️ 系统架构

### 架构图（ASCII 图）
用 ASCII 画系统边界、核心组件、数据流向。
重点：让读者 30 秒建立全局认知。

### 核心数据流
画出最核心的一条路径（如"用户输入 → 最终输出"），3-7 步。

### 技术栈
| 层级 | 技术 | 用途 |
|------|------|------|

## 🗺️ 关键文件地图

| 优先级 | 文件路径 | 行数 | 职责 | 何时阅读 |
|--------|---------|------|------|---------|

### ⚠️ 高风险文件
| 文件 | 风险 | 说明 |
|------|------|------|

## 💡 核心设计决策

| 问题 | 方案 | 原因 | 不这样做的后果 |
|------|------|------|-------------|

## 🚀 本地搭建（5 步内）

### 前置条件
| 工具 | 要求 | 说明 |
|------|------|------|

### 安装步骤
Step 1 → Step 2 → ... → 验证

## 🐛 调试指南

### 各组件调试入口
| 组件 | 打开方式 | 说明 |
|------|---------|------|

### 常见问题排查（2-3 个典型问题）
问题 → 原因 → 排查步骤

## 🎯 适合谁用
| 角色 | 场景 |
|------|------|

## 📖 进阶阅读
→ 链接到 notes/ 下的具体笔记，按主题分类
```

> ⚠️ **强制规则**：每个项目首次研究时必须生成导读指南，不可跳过。指南是 notes/ 的入口文档。
>
> **核心原则**（蒸馏自 understand-onboard）：
> 1. **产品认知优先** — 先让读者知道"这是什么、怎么用"，再讲原理
> 2. **前因后果必需** — 每个技术概念必须解释"为什么需要"，对比不使用时的痛点
> 3. **文档资源感知** — 如果项目自带文档，必须列出并说明内容
> 4. **可视化优先** — 架构图 + 数据流图让读者快速建立全局认知
> 5. **实战导向** — 调试指南、高风险文件直接解决开发者痛点
> 6. **阅读路径清晰** — 关键文件地图标注优先级和阅读时机
> 7. **设计决策传递** — 问题-方案-原因-不这样做的后果四列表传递项目智慧

**subagent prompt 要点**：源码路径 + 研究问题 + 输出格式（让完全不懂的人也能看懂）

> 📝 **subagent prompt 模板、输出模板** → `references/yolo-mode-guide.md` §1-3

---

## Phase 5b: 研究 — 交互模式

> 📖 **详细文档** → `references/interactive-mode-guide.md`

1. 启动 subagent（蓝色标识）静默分析代码
2. 主会话根据 subagent 结果创建 `.study-session.json` 和概念列表
3. 逐步讲解每个概念（主会话执行）
4. **实时归档**：讲解后立即使用 Write 写入 `notes/{主题分类}/{概念名称}.md`
5. **实时更新**：使用 Edit 更新 `.study-session.json` 和思维导图
6. 每步后提供选项：继续/暂停/更多解释/提问
7. 支持通过 `/repo-study continue` 恢复中断
8. **首次研究强制生成导读指南**：所有概念讲解完毕后，检查 `notes/` 中是否已有 `*-guide.md`，若不存在则生成（模板同 Phase 5a）

> ⚠️ **Checkpoint - Human-Verify** — 调研完成后确认概念列表再开始讲解。

> 📝 **实时归档机制、思维导图结构、知识树维护** → `references/interactive-mode-guide.md`

---

## Phase 7: 恢复学习 (continue) — 可选

1. 检查 `.study-session.json` 是否存在
2. 读取并显示上次进度和待讲解概念
3. 用户确认后从下一个概念继续

---

## Phase 6: 产出选择 (output)

> ⚠️ **Checkpoint - Decision**
>
> 研究完成后询问用户：
> 1. 继续深入研究 → 返回 Phase 5
> 2. 生成实操指南 → `notes/{主题}-guide.md`
> 3. 生成 Skill 模板 → `notes/{主题}-skill.md`
> 4. 生成 Cheat Sheet → `notes/{repo-name}-cheat-sheet.md`（速查卡：命令速查 + Before/After 对比 + 决策树）
> 5. 生成小白指南 → `notes/{repo-name}-beginner-guide.md`（零基础完全指南：通俗类比 + 手把手教程）
> 6. 全部生成

最后更新研究日志 `notes/RESEARCH-LOG.md` 并同步 `topics[].progress`。

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
   - 创建 `wiki/open-source/{project}/notes` symlink → `{study项目}/notes`
   - 若 `index.md` 不存在，生成仓库概述页（含笔记列表和 article_id）
6. 重新生成 `wiki/open-source/index.md` 总索引
7. 输出同步结果摘要

> 📝 **同步脚本** → `scripts/repo-study-sync-ob.sh`（支持 `--dry-run` 和 `--project` 参数）

</process>

<!-- ========== 命令速查 ========== -->
<commands>

| 命令 | 说明 |
|------|------|
| `/repo-study <url> <问题>` | 研究 GitHub 仓库的特定问题 |
| `/repo-study list` | 列出 GitHub 项目目录下所有 xxx-study 项目 |
| `/repo-study update` | 强制更新源码到最新版本 |
| `/repo-study status` | 检查当前目录状态（topics、进度、skill 封装状态） |
| `/repo-study translate` | 翻译所有文档 |
| `/repo-study continue` | 恢复上次中断的交互学习 |
| `/repo-study sync` | 同步所有 study 项目到 Obsidian（article_id 分配 + symlink + 索引） |

</commands>

<!-- ========== 四种场景速查 ========== -->
<scenarios>

```
┌─────────────────────────────────────────────────────────────────┐
│                   repo-study 五种场景                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 0: 列表                                                    │
│  用户输入：/repo-study list                                      │
│  → 读取 GitHub 项目目录，列出所有 *-study 项目                    │
│                                                                  │
│  场景 1-4: 研究流程                                              │
│  用户输入：调研下 xxx 在某领域是如何实现的                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Phase 1: 检测                                            │    │
│  │                                                          │    │
│  │  项目存在？                                              │    │
│  │     ├─ 否 → Phase 2: 创建                               │    │
│  │     └─ 是 → 检查版本                                     │    │
│  │              ├─ 不是最新 → Phase 3: 更新                 │    │
│  │              └─ 已是最新 → 跳过更新                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Phase 4: 模式选择                                        │    │
│  │                                                          │    │
│  │  选择研究模式：                                          │    │
│  │     ├─ Yolo 模式 → Phase 5a: subagent 研究 + 完整报告   │    │
│  │     └─ 交互模式 → Phase 5b: subagent 调研 + 渐进讲解    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Phase 6: 产出选择 (Yolo 模式后)                          │    │
│  │                                                          │    │
│  │  研究完成后询问：                                        │    │
│  │     ├─ 继续深入研究 → 返回 Phase 5                       │    │
│  │     ├─ 生成实操指南 → {主题}-guide.md                   │    │
│  │     ├─ 生成 Skill 模板 → {主题}-skill.md                │    │
│  │     ├─ 生成 Cheat Sheet → {repo}-cheat-sheet.md         │    │
│  │     ├─ 生成小白指南 → {repo}-beginner-guide.md          │    │
│  │     └─ 全部生成 → 同时生成以上所有文档                   │    │
│  │                                                          │    │
│  │  最后更新研究日志 RESEARCH-LOG.md                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  版本检查：使用 gh api 比对 commit SHA                           │
│  安全保障：notes/ 目录永不删除                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

</scenarios>

<!-- ========== 成功标准 ========== -->
<success_criteria>
- [ ] 正确解析仓库 URL 和研究问题
- [ ] 项目创建路径从 CLAUDE.md 的 GitHub 项目目录配置中读取（不硬编码）
- [ ] `/repo-study list` 可列出所有 xxx-study 项目
- [ ] 仅在当前目录识别 study 状态（不递归）
- [ ] 标识当前项目是否由 repo-study 创建（v2）
- [ ] **文档资源扫描**：检测 docs/、README.md 等文档资源，分类文档站类型
- [ ] 使用 `gh api` 检查远程 commit SHA
- [ ] 若本地版本落后，提示用户是否更新
- [ ] 创建项目时生成完整文件结构（含 status 脚本）
- [ ] 更新时保留 notes/ 目录
- [ ] 询问用户选择研究模式（Yolo/交互）
- [ ] Yolo 模式：若项目有文档，先启动文档感知 subagent 提取产品认知
- [ ] Yolo 模式：启动代码分析 subagent（蓝色标识，Explore 类型）
- [ ] Yolo 模式（多课题）：并行启动多个 subagent 研究独立课题
- [ ] **产品认知层次**：输出按"产品认知 → 核心概念(含Why) → 代码原理"排列
- [ ] **前因后果**：每个核心技术概念解释"为什么需要"和"不使用的后果"
- [ ] 交互模式：启动文档感知 + 代码分析 subagent 静默调研
- [ ] 交互模式：创建 .study-session.json，实时归档和思维导图
- [ ] `/repo-study continue` 可恢复上次中断的交互学习
- [ ] 沉淀笔记到 notes/ 目录，按主题写入 topics[]
- [ ] **首次研究强制生成导读指南** notes/{repo-name}-guide.md（含产品认知、文档资源、前因后果）
- [ ] **文档资源体现**：导读指南中列出项目已有文档资源（如有）
- [ ] 研究完成后询问用户下一步选择（指南/模板/Cheat Sheet/小白指南/全部）
- [ ] **Cheat Sheet 生成**：Phase 6 选择"生成 Cheat Sheet"时，生成含命令速查 + Before/After 对比 + 决策树的速查卡
- [ ] **小白指南生成**：Phase 6 选择"生成小白指南"时，生成含通俗类比 + 手把手教程的零基础完全指南
- [ ] **工具类项目提示**：Phase 5a 首次研究工具/库/CLI 项目时，提示用户是否生成 Cheat Sheet
- [ ] 中文提问时提示翻译功能
- [ ] **sync 时 article_id 分配**：为缺少 article_id 的笔记自动分配 OBA-xxx，全局唯一校验
- [ ] **sync 时 index.md 含笔记列表**：项目 index.md 列出每个笔记标题和 article_id
</success_criteria>

<!-- ========== 参考文档 ========== -->
<references>

| 文件 | 用途 |
|------|------|
| `references/state-templates.md` | **状态模板与检测逻辑**（.study-meta.json v2、status 脚本、版本检查命令） |
| `references/interactive-mode-guide.md` | **交互模式详细指南**（实时归档、思维导图、知识树结构、会话追踪） |
| `references/yolo-mode-guide.md` | **Yolo 模式详细指南**（subagent prompt 模板、输出模板、笔记沉淀、翻译提示） |
| `references/anti-patterns.md` | **反模式清单**（6 个常见错误及正确做法） |
| `references/quick-reference.md` | **快速参考**（使用示例、模式说明、常用命令速查） |

</references>

---

## ⚠️ 用户交互点总结

| 阶段 | 交互点 | 类型 | 用户操作 |
|------|--------|------|----------|
| Phase 1 | 🛑 版本落后提示 | Decision | 选择是否更新源码 |
| Phase 2 | ✅ 文件结构验证 | Human-Verify | 确认文件结构完整 |
| Phase 4 | 🔄 模式选择 | Decision | 选择 Yolo/交互模式 |
| Phase 5b | ✅ 调研完成确认 | Human-Verify | 确认概念列表 |
| Phase 5b | 🔄 理解确认 | Decision | 继续/暂停/更多解释/提问 |
| Phase 6 | 🔄 产出选择 | Decision | 继续研究/指南/模板/Cheat Sheet/小白指南/全部 |
| Phase 7 | 🔄 恢复确认 | Decision | 继续/重新开始 |
