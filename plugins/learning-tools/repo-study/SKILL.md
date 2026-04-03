---
name: repo-study
description: "研究 GitHub 仓库的特定技术实现。触发词：调研下、研究下、学习下、看看 xxx 仓库、分析开源项目、repo-study"
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

  <gsd:phase name="detect" order="1">
    <gsd:step>解析仓库 URL 和研究问题</gsd:step>
    <gsd:step>仅在当前目录检测 study 标识（目录名和 .study-meta.json）</gsd:step>
    <gsd:step>判断当前项目是否由 repo-study 创建（v2）</gsd:step>
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
    <gsd:step>启动 subagent（蓝色标识，Explore 类型）执行代码分析</gsd:step>
    <gsd:step condition="多独立课题">并行启动多个 subagent 研究不同课题</gsd:step>
    <gsd:step>主会话接收 subagent 结果，输出完整研究发现</gsd:step>
    <gsd:step>沉淀笔记到 notes/</gsd:step>
    <gsd:step condition="用户使用中文提问">提示翻译功能</gsd:step>
  </gsd:phase>

  <gsd:phase name="research_interactive" order="5b" condition="选择交互模式">
    <gsd:step>调研阶段：启动 subagent（蓝色标识）静默分析代码</gsd:step>
    <gsd:step>主会话接收 subagent 结果，创建会话状态和概念列表</gsd:step>
    <gsd:step>概念拆解：将研究发现拆分为多个小概念</gsd:step>
    <gsd:step>逐步讲解：每次只讲一个概念</gsd:step>
    <gsd:step>实时归档：讲解后立即写入文件并更新会话状态</gsd:step>
    <gsd:step>理解确认：询问用户下一步选择</gsd:step>
    <gsd:step condition="需要更多解释">补充解释和示例</gsd:step>
    <gsd:step condition="继续">进入下一个概念</gsd:step>
    <gsd:step condition="暂停">保存进度到会话状态文件</gsd:step>
    <gsd:step>总结确认：所有概念讲解完毕后询问是否需要完整笔记</gsd:step>
    <gsd:step condition="需要">沉淀完整笔记到 notes/</gsd:step>
  </gsd:phase>

  <gsd:phase name="continue" order="7" condition="用户使用 /repo-study continue">
    <gsd:step>检查会话状态：读取 .study-session.json</gsd:step>
    <gsd:step>显示进度：展示上次进度和待讲解概念</gsd:step>
    <gsd:step>继续学习：从下一个待讲解概念继续交互学习</gsd:step>
  </gsd:phase>

  <gsd:phase name="output" order="6">
    <gsd:step>询问用户下一步：继续研究 / 生成实操指南 / 生成 Skill 模板 / 全部生成</gsd:step>
    <gsd:step condition="选择指南或全部">生成 {主题}-guide.md（小白可执行的实操指南）</gsd:step>
    <gsd:step condition="选择模板或全部">生成 {主题}-skill.md（可复用的 Skill 模板）</gsd:step>
    <gsd:step>更新研究日志 RESEARCH-LOG.md</gsd:step>
  </gsd:phase>
</gsd:workflow>

<!-- ========== 执行流程 ========== -->
<process>

## Phase 1: 检测 (detect)

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

1. 创建 `{repo-name}-study` 目录
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

1. 启动 subagent（蓝色标识，Explore 类型）执行代码分析
2. 多独立课题时可并行启动多个 subagent
3. 主会话接收 subagent 结果，输出完整研究发现
4. 沉淀笔记到 `notes/` 并更新 `.study-meta.json` 的 `topics[]`
5. 中文提问时提示翻译功能

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
> 4. 全部生成

最后更新研究日志 `notes/RESEARCH-LOG.md` 并同步 `topics[].progress`。

</process>

<!-- ========== 命令速查 ========== -->
<commands>

| 命令 | 说明 |
|------|------|
| `/repo-study <url> <问题>` | 研究 GitHub 仓库的特定问题 |
| `/repo-study update` | 强制更新源码到最新版本 |
| `/repo-study status` | 检查当前目录状态（topics、进度、skill 封装状态） |
| `/repo-study translate` | 翻译所有文档 |
| `/repo-study continue` | 恢复上次中断的交互学习 |

</commands>

<!-- ========== 四种场景速查 ========== -->
<scenarios>

```
┌─────────────────────────────────────────────────────────────────┐
│                   repo-study 四种场景                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
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
│  │     └─ 全部生成 → 同时生成指南和模板                     │    │
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
- [ ] 仅在当前目录识别 study 状态（不递归）
- [ ] 标识当前项目是否由 repo-study 创建（v2）
- [ ] 使用 `gh api` 检查远程 commit SHA
- [ ] 若本地版本落后，提示用户是否更新
- [ ] 创建项目时生成完整文件结构（含 status 脚本）
- [ ] 更新时保留 notes/ 目录
- [ ] 询问用户选择研究模式（Yolo/交互）
- [ ] Yolo 模式：启动 subagent（蓝色标识，Explore 类型）执行代码分析
- [ ] Yolo 模式（多课题）：并行启动多个 subagent 研究独立课题
- [ ] 交互模式：启动 subagent 静默调研，主会话分步骤教学
- [ ] 交互模式：创建 .study-session.json，实时归档和思维导图
- [ ] `/repo-study continue` 可恢复上次中断的交互学习
- [ ] 沉淀笔记到 notes/ 目录，按主题写入 topics[]
- [ ] 研究完成后询问用户下一步选择（指南/模板/全部）
- [ ] 中文提问时提示翻译功能
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
| Phase 6 | 🔄 产出选择 | Decision | 继续研究/指南/模板/全部 |
| Phase 7 | 🔄 恢复确认 | Decision | 继续/重新开始 |
