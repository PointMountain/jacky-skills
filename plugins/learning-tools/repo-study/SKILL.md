---
name: repo-study
description: "研究 GitHub 仓库的特定技术实现。触发词：调研下、研究下、学习下、看看 xxx 仓库、分析开源项目、repo-study"
argument-hint: '[子命令 | URL [问题]]  子命令: list|status|update|sync|translate|distill|answer|continue'
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

### 双模式：Survey + Incremental

项目研究分为两种模式，产出分别放在不同文件夹：

| 模式 | 触发条件 | 产出目录 | 内容特征 |
|------|----------|----------|----------|
| **Survey**（系统调研） | 首次研究，`surveyState != "completed"` | `explorer/` | 成体系、有阅读路径、笔记间有因果链 |
| **Incremental**（增量问答） | survey 完成后，用户针对特定话题提问 | `notes/` | 零散、不成体系、随问随记 |

- `explorer/` 中的成体系笔记最终目标是打磨成可发布的教程
- `notes/` 中的零散笔记是知识积累，供参考但不形成叙事链路

### explorer 文件编号规则

**`explorer/` 目录下的笔记文件必须带 2 位索引前缀**，按阅读顺序编号：

```
explorer/
├── 00-xxx-environment-setup.md       ← 环境准备（安装、配置、前置依赖）
├── 01-xxx-how-to-use-guide.md        ← 第一篇（入口：快速上手）
├── 02-xxx-guide.md                   ← 第二篇（导读 / 架构概览）
├── 03-architecture-deep-dive.md      ← 第三篇（核心深入）
├── ...
└── README.md                         ← 索引文件，不需要编号
```

**规则**：
1. 格式：`{NN}-{原始文件名}.md`，NN 为两位数字（00, 01, 02, 03...）
2. **`00-` 固定保留给环境准备章节**（安装、配置、账号、网络等前置条件）。如果项目无需环境准备（纯代码分析），可跳过 00- 直接从 01- 开始
3. 编号反映阅读顺序：环境准备(00) → 先跑通(01) → 全景认知(02) → 核心链路(03+) → 辅助组件 → 设计思想
4. 新增文件时：扫描 `explorer/` 中已有的编号文件，取最大编号 +1（00- 位置仅用于环境准备，不参与自动递增）
5. `README.md` 和非 `.md` 文件不需要编号
6. `notes/` 目录不使用编号（零散笔记，无固定阅读顺序）

### 笔记质量评价体系

**核心原则：价值 = 认知落差**

知识点的价值不取决于技术通用性，而取决于「知道之前」和「知道之后」的理解差距。落差越大，越值得写。

| 层级 | 识别信号 | 典型表现 |
|------|---------|---------|
| **认知颠覆** | 范式转变、跨领域迁移 | "我完全没想到还能这样做" |
| **模式提炼** | 反复出现的结构、通用解法 | "原来这个就是 XXX 模式" |
| **工具积木** | 具体代码片段、配置模板 | "拿来就能用" |

### 笔记叙事原则

1. **问题驱动螺旋** — 每篇笔记存在是因为上一篇留下了问题，不是"接下来讲 X"
   ```
   遗留问题 → 尝试解决 → 新问题浮现 → 下一篇笔记
   ```

2. **对比驱动** — 痛点展示 → 方案揭示 → 原理解释 → 举一反三。不要先给答案。

3. **实操优先** — 小白如果不知道怎么用，就不会去思考原理。阅读顺序：环境准备(00) → 先用起来(01) → 再理解为什么(02+) → 最后深入细节

4. **每篇笔记声明定位** — 给谁看？解决什么问题？与相邻笔记的因果关系是什么？

### 写作原则
- 假设读者是零基础，不跳过基础概念
- 使用步骤化表达，每个步骤只做一件事
- 提供完整示例，代码片段要完整可运行

### article_id 强制规则

**每篇研究笔记的 frontmatter 必须包含唯一的 `article_id`**：

- 格式：`article_id: OBA-{8位随机小写字母数字}`
- 生成时机：笔记首次写入时立即生成，不可后补
- 全局唯一性：在 OB 仓库 wiki/ 下搜索确认无碰撞
- 每篇笔记只能有一个 article_id（禁止重复插入）
- article_id 是 Question.md 和笔记之间的桥梁，缺失会导致问题无法关联
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
    <gsd:step condition="源码中存在 SKILL.md 文件">标记项目为 skill-type（该项目本身是一个 Claude Code Skill），提取 skill 名称和描述</gsd:step>
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
    <gsd:step>生成 Question.md（AI 预设研究问题，基于源码快速扫描）</gsd:step>
    <gsd:step>初始化 Git 仓库</gsd:step>
  </gsd:phase>

  <gsd:phase name="update" order="3" condition="项目存在但不是最新">
    <gsd:step>询问用户是否更新</gsd:step>
    <gsd:step>更新源码到最新版本</gsd:step>
  </gsd:phase>

  <gsd:phase name="mode_detect" order="3.5">
    <gsd:step>读取 .study-meta.json 的 surveyState 字段</gsd:step>
    <gsd:step condition="surveyState 为 null 或 pending">标记为 Survey 模式，产出目录为 explorer/</gsd:step>
    <gsd:step condition="surveyState 为 completed">标记为 Incremental 模式，产出目录为 notes/</gsd:step>
    <gsd:step condition="surveyState 为 in-progress">询问用户：继续 survey / 切到 incremental</gsd:step>
    <gsd:checkpoint>根据 surveyState 决定进入 Survey 分支或 Incremental 分支</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="mode_select" order="4" condition="Survey 模式">
    <gsd:step>询问用户选择研究模式</gsd:step>
    <gsd:step>yolo 模式：直接输出完整研究发现</gsd:step>
    <gsd:step>交互模式：渐进式教学，分步骤讲解</gsd:step>
    <gsd:checkpoint>根据用户选择进入对应分支</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="research_yolo" order="5" condition="选择 yolo 模式（Survey）">
    <gsd:step>切换到项目目录</gsd:step>
    <gsd:step>若源码存在文档资源（docs/、README.md 等），先启动文档感知 subagent 扫描并提取产品认知和用户指南信息</gsd:step>
    <gsd:step>启动代码分析 subagent（蓝色标识，Explore 类型）执行代码分析</gsd:step>
    <gsd:step condition="项目为 skill-type">启动 skill 映射 subagent：分析 SKILL.md 各 section 与脚本的对应关系，验证每个脚本可独立运行</gsd:step>
    <gsd:step condition="多独立课题">并行启动多个 subagent 研究不同课题</gsd:step>
    <gsd:step>主会话合并文档感知 + 代码分析结果，按"产品认知 → 核心概念(含Why) → 代码原理"层次输出完整研究发现</gsd:step>
    <gsd:step>沉淀笔记到 explorer/（文件名必须带 2 位索引前缀，如 01-xxx.md）并设置 surveyState = "completed"</gsd:step>
    <gsd:step condition="项目需要环境准备且 explorer/ 中不存在 00-*">强制生成环境准备章节 explorer/00-{repo-name}-environment-setup.md（安装、配置、前置依赖）</gsd:step>
    <gsd:step condition="首次研究且 explorer/ 中不存在 *-guide.md">强制生成仓库导读指南 explorer/NN-{repo-name}-guide.md（带编号）</gsd:step>
    <gsd:step condition="用户使用中文提问">提示翻译功能</gsd:step>
    <gsd:step>执行 Phase 5.5 自动同步检测</gsd:step>
  </gsd:phase>

  <gsd:phase name="research_interactive" order="5b" condition="选择交互模式（Survey）">
    <gsd:step>调研阶段：若源码存在文档资源，先启动文档感知 subagent 扫描产品认知信息</gsd:step>
    <gsd:step>启动代码分析 subagent（蓝色标识）静默分析代码</gsd:step>
    <gsd:step>主会话合并文档感知 + 代码分析结果，创建会话状态和概念列表</gsd:step>
    <gsd:step>概念列表按"产品认知 → 核心概念(含Why) → 代码原理"层次排列</gsd:step>
    <gsd:step>概念拆解：将研究发现拆分为多个小概念</gsd:step>
    <gsd:step>逐步讲解：每次只讲一个概念</gsd:step>
    <gsd:step>实时归档：讲解后立即写入 explorer/（文件名带 2 位索引前缀）并更新会话状态</gsd:step>
    <gsd:step>理解确认：询问用户下一步选择</gsd:step>
    <gsd:step condition="需要更多解释">补充解释和示例</gsd:step>
    <gsd:step condition="继续">进入下一个概念</gsd:step>
    <gsd:step condition="暂停">保存进度到会话状态文件</gsd:step>
    <gsd:step>总结确认：所有概念讲解完毕后询问是否需要完整笔记</gsd:step>
    <gsd:step condition="需要">沉淀完整笔记到 explorer/（文件名带 2 位索引前缀）并设置 surveyState = "completed"</gsd:step>
    <gsd:step condition="项目需要环境准备且 explorer/ 中不存在 00-*">强制生成环境准备章节 explorer/00-{repo-name}-environment-setup.md（安装、配置、前置依赖）</gsd:step>
    <gsd:step condition="首次研究且 explorer/ 中不存在 *-guide.md">强制生成仓库导读指南 explorer/NN-{repo-name}-guide.md（带编号）</gsd:step>
    <gsd:step>执行 Phase 5.5 自动同步检测</gsd:step>
  </gsd:phase>

  <gsd:phase name="research_incremental" order="5c" condition="Incremental 模式">
    <gsd:step>解析用户的增量问题</gsd:step>
    <gsd:step>启动针对性 subagent（只分析相关代码区域）</gsd:step>
    <gsd:step>写入 notes/{topic-slug}.md</gsd:step>
    <gsd:step>更新 .study-meta.json 的 topics[]（location: "notes"）</gsd:step>
    <gsd:step>执行 Phase 5.5 自动同步检测</gsd:step>
  </gsd:phase>

  <gsd:phase name="continue" order="7" condition="用户使用 /repo-study continue">
    <gsd:step>检查会话状态：读取 .study-session.json</gsd:step>
    <gsd:step>显示进度：展示上次进度和待讲解概念</gsd:step>
    <gsd:step>继续学习：从下一个待讲解概念继续交互学习</gsd:step>
  </gsd:phase>

  <gsd:phase name="sync" order="8" condition="用户使用 /repo-study sync">
    <gsd:step>读取 CLAUDE.md 中的 GitHub 项目目录和 Obsidian 仓库路径</gsd:step>
    <gsd:step>扫描所有 *-study 项目的 explorer/ 和 notes/ 目录</gsd:step>
    <gsd:step>为缺少 article_id 的笔记自动分配 OBA-xxx（全局唯一、8位随机小写字母数字）</gsd:step>
    <gsd:step>为每个有笔记的项目在 OB 的 wiki/open-source/ 下创建 symlink（覆盖 explorer/ 和 notes/）</gsd:step>
    <gsd:step>生成/更新每个项目的 index.md 概述页（含笔记列表和 article_id）</gsd:step>
    <gsd:step>更新 open-source/index.md 总索引</gsd:step>
  </gsd:phase>

  <gsd:phase name="translate" order="8b" condition="用户使用 /repo-study translate">
    <gsd:step>运行 scripts/repo-study-translate.sh 生成翻译任务清单（source → source.zh.md）</gsd:step>
    <gsd:step>按 group 字段将任务分组，默认每组 20 个文件</gsd:step>
    <gsd:step>并行启动 subagent（每组一个）执行翻译，直接写入目标 *.zh.md 文件</gsd:step>
    <gsd:step>subagent 必须保留 frontmatter、标题层级、代码块、链接与表格结构</gsd:step>
    <gsd:step>默认跳过已存在的 *.zh.md（可通过 --force 重新翻译）</gsd:step>
    <gsd:step>严格禁止修改源文件 *.md，仅允许新增/覆盖 *.zh.md</gsd:step>
    <gsd:step>主会话汇总 subagent 执行结果并输出成功/失败清单</gsd:step>
  </gsd:phase>

  <gsd:phase name="distill" order="9" condition="user uses /repo-study distill">
    <gsd:step>Read .study-meta.json backlog[] array</gsd:step>
    <gsd:step>Prioritize pending items by priority field (high/medium/low)</gsd:step>
    <gsd:step>For each item, show: id, title, type, priority, sourceNote</gsd:step>
    <gsd:step>User selects item to distill (or accepts suggestion)</gsd:step>
    <gsd:step condition="type=demo">Create demo folder under demos/ with package.json, index.mjs, README.md</gsd:step>
    <gsd:step condition="type=skill-design">Generate skill design note under notes/（增量笔记）</gsd:step>
    <gsd:step>Update backlog item status to in-progress then done</gsd:step>
    <gsd:step>Add demo artifact to parent topic's artifacts[]</gsd:step>
    <gsd:step>Verify demo runs independently (cd demos/xxx && npm install && node index.mjs)</gsd:step>
  </gsd:phase>

  <gsd:phase name="output" order="6">
    <gsd:step>询问用户下一步：继续研究 / 生成实操指南 / 生成教程 / 生成 Skill 模板 / 生成 Cheat Sheet / 生成小白指南 / 生成技术展示文章 / 生成 Skill 映射 / 全部生成</gsd:step>
    <gsd:step condition="选择指南或全部">生成 explorer/NN-{主题}-guide.md（小白可执行的实操指南，成体系，带编号）</gsd:step>
    <gsd:step condition="选择教程或全部">进入 Phase 6b（教程两阶段工作流，产出到 explorer/）</gsd:step>
    <gsd:step condition="选择模板或全部">生成 notes/{主题}-skill.md（可复用的 Skill 模板，零散笔记）</gsd:step>
    <gsd:step condition="选择 Cheat Sheet 或全部">进入 Phase 6d（Cheat Sheet 专属 subagent，产出到 explorer/cheatsheet/）</gsd:step>
    <gsd:step condition="选择小白指南或全部">生成 explorer/NN-{repo-name}-beginner-guide.md（零基础完全指南，成体系，带编号）</gsd:step>
    <gsd:step condition="选择 skill 映射或全部">生成 notes/{repo-name}-skill-to-script-mapping.md（skill→script 映射，零散笔记）</gsd:step>
    <gsd:step>更新研究日志 notes/RESEARCH-LOG.md</gsd:step>
  </gsd:phase>

  <gsd:phase name="tutorial" order="6b" condition="用户选择生成教程">
    <gsd:meta>
      <name>tutorial-two-phase</name>
      <description>教程两阶段工作流：配置引导（人工）+ 逐章实测（sub-agent 自动化）</description>
      <requires>Agent (subagent), Bash</requires>
    </gsd:meta>

    <gsd:phase name="tutorial_phase1" order="1">
      <gsd:step>生成 Phase 1 环境配置引导：安装、Chrome 扩展、登录、网络确认</gsd:step>
      <gsd:step>每步包含：操作说明 → 验证命令 → 完成标志 → 常见问题</gsd:step>
      <gsd:step>需要人工操作的步骤用 ⚠️ 标记</gsd:step>
      <gsd:step>底部放检查清单，全部通过才能进入 Phase 2</gsd:step>
      <gsd:step>引导用户逐步完成配置，每步验证后再进入下一步</gsd:step>
      <gsd:checkpoint>Phase 1 检查清单全部通过后，才能进入 Phase 2</gsd:checkpoint>
    </gsd:phase>

    <gsd:phase name="tutorial_phase2" order="2" condition="Phase 1 检查清单全部通过">
      <gsd:step>将教程拆分为独立章节（按认证模式或功能模块划分）</gsd:step>
      <gsd:step>每章标注：状态（待实测）、认证模式（public/cookie/browser）、前置条件</gsd:step>
      <gsd:step>所有命令的输出使用占位符标记，不写"预期输出"</gsd:step>
      <gsd:step>派 sub-agent 逐章测试（每章一个 agent，3 章一组并行）</gsd:step>
      <gsd:step>每个 sub-agent 返回格式化测试报告：命令 → 实际输出 → 状态</gsd:step>
      <gsd:step>主 agent 收集报告，替换占位符为实测数据</gsd:step>
      <gsd:step>标注已知问题和替代方案</gsd:step>
    </gsd:phase>
  </gsd:phase>

  <gsd:phase name="article" order="6c" condition="用户选择生成技术展示文章">
    <gsd:meta>
      <name>article-showcase</name>
      <description>生成面向掘金/知乎等技术社区的技术展示文章，以研究者第三人称视角呈现设计洞察</description>
      <requires>Agent (subagent), Read, Write</requires>
    </gsd:meta>

    <gsd:phase name="article_collect" order="1">
      <gsd:step>读取 explorer/ 和 notes/ 下所有已有研究笔记作为素材</gsd:step>
      <gsd:step>读取源码中的 README、SKILL.md 等项目自述文档</gsd:step>
      <gsd:step>识别项目的认知颠覆点和设计哲学</gsd:step>
      <gsd:step>汇总素材清单（研究笔记 + 项目文档 + 核心洞察）</gsd:step>
    </gsd:phase>

    <gsd:phase name="article_generate" order="2">
      <gsd:step>启动文章生成 subagent（Explore 类型），使用 article-mode-guide.md 的 prompt 模板</gsd:step>
      <gsd:step>subagent 输入：研究笔记摘要 + 项目文档 + 文章叙事模板</gsd:step>
      <gsd:step>subagent 输出：完整技术展示文章（3000-5000 字 Markdown）</gsd:step>
    </gsd:phase>

    <gsd:phase name="article_check" order="3">
      <gsd:step>对照 article-mode-guide.md §4 质量检查清单验证文章</gsd:step>
      <gsd:step>确认叙事弧线完整（6 段式）</gsd:step>
      <gsd:step>确认技术深度分层（入门 → 进阶 → 深入）</gsd:step>
      <gsd:step>确认有研究者洞察（非纯客观转述）</gsd:step>
    </gsd:phase>

    <gsd:phase name="article_save" order="4">
      <gsd:step>写入 notes/{repo-name}-article.md（文章为非教程性质，放入 notes/）</gsd:step>
      <gsd:step>更新 .study-meta.json topics[] 进度</gsd:step>
      <gsd:step>在文章 frontmatter 中标注素材来源笔记</gsd:step>
    </gsd:phase>
  </gsd:phase>

  <gsd:phase name="cheatsheet" order="6d" condition="用户选择生成 Cheat Sheet">
    <gsd:meta>
      <name>cheatsheet-generation</name>
      <description>Cheat Sheet 专属 subagent：从研究笔记中提炼速查卡片，产出到 explorer/cheatsheet/</description>
      <requires>Agent (subagent), Read, Write</requires>
    </gsd:meta>

    <gsd:phase name="cheatsheet_scan" order="1">
      <gsd:step>扫描 explorer/ 和 notes/ 下所有研究笔记，识别可提炼为速查卡的知识维度</gsd:step>
      <gsd:step>常见维度：命令/API 速查、配置模板、触发词/关键词、数据结构、操作流程</gsd:step>
      <gsd:step>为每个维度生成一份 Cheat Sheet（如项目有多个维度则生成多份）</gsd:step>
    </gsd:phase>

    <gsd:phase name="cheatsheet_generate" order="2">
      <gsd:step>启动 Cheat Sheet 专属 subagent（Explore 类型）</gsd:step>
      <gsd:step>subagent 读取所有研究笔记，按维度提炼速查内容</gsd:step>
      <gsd:step>每份 Cheat Sheet 格式：标题 + 一句话说明 + 分维度表格 + 示例</gsd:step>
    </gsd:phase>

    <gsd:phase name="cheatsheet_save" order="3">
      <gsd:step>创建 explorer/cheatsheet/ 目录（如不存在）</gsd:step>
      <gsd:step>写入 explorer/cheatsheet/{topic}-cheat-sheet.md（每维度一份）</gsd:step>
      <gsd:step>更新 .study-meta.json 的 topics[]（location: "explorer"，子目录 "cheatsheet"）</gsd:step>
      <gsd:step>更新 CLAUDE.md 笔记索引和 explorer/README.md 阅读路径</gsd:step>
    </gsd:phase>
  </gsd:phase>

  <gsd:phase name="answer" order="10" condition="用户使用 /repo-study answer">
    <gsd:meta>
      <name>question-answer</name>
      <description>读取 Question.md 中用户记录的看不懂的地方，启动 subagent 拆解并补充对应笔记内容</description>
      <requires>Agent (subagent), Read, Edit, Write</requires>
    </gsd:meta>
    <gsd:step>读取项目根目录的 Question.md</gsd:step>
    <gsd:step>提取一级标题以下的所有内容，分为两部分：(A) 顶部自由内容（非 article_id section）(B) ## {article_id} section 及其下用户内容</gsd:step>
    <gsd:step condition="A 和 B 均为空">提示"没有待处理的问题"并退出</gsd:step>
    <gsd:step condition="A 不为空">将顶部自由内容作为整体建议/反馈处理（可能是文件移动、流程优化、结构调整等）</gsd:step>
    <gsd:step>展示 section 概况表格（序号 / article_id / 对应笔记 / 内容摘要）</gsd:step>
    <gsd:step>用户选择：全部处理 / 选择部分处理 / 取消</gsd:step>
    <gsd:step condition="选择了 section">启动 Explore 类型 subagent，传入 Question.md 全文 + 笔记路径 + 源码路径，让 AI 拆解并生成补充内容</gsd:step>
    <gsd:step>将补充内容插入到对应研究笔记的指定位置</gsd:step>
    <gsd:step>用户确认后清理 Question.md：删除已处理的 section</gsd:step>
    <gsd:step>输出摘要：处理了 N 个 section，补充了 M 篇笔记</gsd:step>
  </gsd:phase>
</gsd:workflow>

<!-- ========== 执行流程 ========== -->
<process>

## 入口路由 (route)

解析用户输入的 args，决定进入哪个 Phase：

**子命令检测优先级：** 先检查 args 是否匹配已知子命令，再按 URL/问题解析。

| args 匹配 | 进入 Phase | 说明 |
|------------|-----------|------|
| 空值 / `help` / `--help` | **显示帮助** | 输出命令速查表 |
| `list` | Phase 0 | 列出所有 study 项目 |
| `status` | Phase 1 | 检测当前项目状态并输出 |
| `update` | Phase 1 → Phase 3 | 强制更新源码 |
| `sync` | Phase 8 | 同步到 Obsidian |
| `translate` | Phase 8b | 并行翻译文档 |
| `distill` | Phase 9 | 蒸馏为 demo/设计文档 |
| `answer` | Phase 10 | 回答 Question.md 中的问题 |
| `continue` | Phase 7 | 恢复交互学习 |
| 含 URL 或仓库名 | Phase 1 → 自动流转 | 研究模式（默认） |

### 空值 / help 时的输出格式

当用户输入 `/repo-study` 不带参数，或带 `help`/`--help` 时，输出以下提示：

```
📖 repo-study — GitHub 仓库研究助手

用法: /repo-study <子命令> 或 /repo-study <仓库URL> [研究问题]

子命令:
  list      列出所有 *-study 项目
  status    查看当前项目状态（进度、模式、版本）
  update    更新当前项目源码到最新版本
  sync      同步所有 study 笔记到 Obsidian
  translate 并行翻译文档（*.md → *.zh.md）
  distill   将研究发现蒸馏为独立 demo 或设计文档
  answer    回答 Question.md 中的研究问题
  continue  恢复上次中断的交互学习

研究模式:
  /repo-study <URL> <问题>     首次研究 → Survey 模式（产出 explorer/）
                               后续提问 → Incremental 模式（产出 notes/）

示例:
  /repo-study https://github.com/user/repo 它的缓存策略是怎么实现的
  /repo-study list
  /repo-study sync
```

> **注意**：如果 args 不匹配任何子命令也不含 URL，则当作研究问题处理（在当前 study 项目中执行增量问答）。

---

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

在检测项目状态后，**扫描源码中的文档资源**（`docs/`、`README.md`、`CONTRIBUTING.md`、根目录 `*.md`），识别文档站类型（VitePress / Docsify / Docusaurus），并将结果传递给后续 Phase 用于产品认知建立和导读指南生成。

### Step 1.2b: Skill 项目检测

在文档资源扫描后，**检测源码中是否包含 SKILL.md 文件**：
1. 检查 `{源码目录}/SKILL.md` 是否存在
2. 若存在，标记项目为 `skill-type`
3. 从 SKILL.md 的 frontmatter 提取 `name` 和 `description`
4. 列出 SKILL.md 中引用的所有脚本路径（如 `scripts/` 目录下的文件）
5. 将 skill-type 标记传递给后续 Phase 用于针对性分析

### Step 1.3: 运行 status 脚本

```bash
scripts/repo-study-status.sh --json --check-remote
```

> 注意：该脚本现在位于 skill 自身目录中，无需在每个 study 项目中生成副本。

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
4. 创建 `explorer/` 和 `notes/` 目录
5. 生成 `CLAUDE.md`、`.study-meta.json`（v2，含 `surveyState: "pending"`）
6. **生成 `Question.md`** — 启动快速 subagent 扫描源码，生成 5-8 个 AI 预设研究问题（格式见 `references/question-template.md`）
7. 初始化 Git 仓库并首次提交

> ⚠️ **Checkpoint - Human-Verify** — 确保文件结构完整后初始化 Git 仓库。
> 📝 **元数据结构** → `references/state-templates.md` §4
> 📝 **Question.md 模板** → `references/question-template.md`

---

## Phase 3: 更新 (update) — 仅当项目不是最新时

1. 临时克隆最新代码到 `temp_clone`
2. 只更新源码目录，**保留 explorer/ 和 notes/ 目录**（永不删除）
3. 更新 `.study-meta.json` 中的 commit SHA
4. 删除临时目录

> ⚠️ **安全检查**: 更新前确认 explorer/ 和 notes/ 目录不会被删除。

---

## Phase 3.5: 模式检测 (mode_detect) — 自动判断

读取 `.study-meta.json` 的 `surveyState` 字段，决定进入哪种模式：

| surveyState | 模式 | 产出目录 | 说明 |
|-------------|------|----------|------|
| `null` / `pending` | **Survey** | `explorer/` | 首次系统调研，生成成体系笔记 |
| `completed` | **Incremental** | `notes/` | 已有调研基础，按需回答特定问题 |
| `in-progress` | **询问用户** | — | 之前的调研未完成，确认是继续还是切换 |

> **向后兼容**：对缺少 `surveyState` 字段的存量项目，如果 `explorer/` 或 `notes/` 中已有笔记，自动补充为 `"completed"`。

**分支逻辑**：
- Survey 模式 → 继续进入 Phase 4（选择 yolo/交互）
- Incremental 模式 → 直接进入 Phase 5c（增量问答）

---

## Phase 4: 模式选择 (mode_select) — 仅 Survey 模式

> ⚠️ **Checkpoint - Decision**
>
> 询问用户选择研究模式：
> 1. **Yolo 模式**（快速）— 直接输出完整研究发现
> 2. **交互模式**（教学）— 分步骤渐进式教学，每步确认理解

---

## Phase 5a: 研究 — Yolo 模式

> 📖 **详细文档** → `references/yolo-mode-guide.md`

### Step 5a.1: 文档感知（如果项目有文档）

若 Phase 1 检测到项目有文档资源（docs/、README 等），先启动**文档感知 subagent**（Explore 类型），提取产品形态、安装方式、核心组件、文档结构和用户指南摘要。

> 📝 **subagent prompt 模板** → `references/yolo-mode-guide.md` §1

### Step 5a.2: 代码分析

启动 subagent（蓝色标识，Explore 类型）执行代码分析。

### Step 5a.2b: Skill 映射分析（skill-type 项目）

当 Phase 1 检测到项目为 skill-type 时，启动**skill 映射 subagent**（Explore 类型）：

**分析内容**：
1. 读取 SKILL.md，提取每个能力 section（如"前置检查""CDP 操作""本地资源"等）
2. 找出每个 section 引用的脚本文件（`scripts/` 目录下的 .mjs/.sh 等）
3. 分析每个脚本的核心机制（输入→处理→输出）
4. 列出完整触发链路：SKILL.md section → 脚本 → 工作流

**验收验证**（如环境允许）：
1. 逐个运行脚本，记录输出
2. 对浏览器类脚本，测试完整的 tab 生命周期（创建→操作→关闭）
3. 汇总验收结果（通过/失败/跳过）

**输出格式**：`explorer/NN-{repo-name}-skill-to-script-mapping.md`（带编号）

### Step 5a.3: 结果合并与输出

主会话按以下层次合并输出：
1. **产品认知**（来自文档感知 subagent）
2. **核心概念 + 前因后果**（来自文档 + 代码综合分析）
3. **代码原理**（来自代码分析 subagent）

### Step 5a.4: 沉淀与指南

1. 沉淀笔记到 `explorer/`（**文件名必须带 2 位索引前缀**，如 `01-xxx.md`、`02-xxx.md`）并更新 `.study-meta.json` 的 `topics[]`（location: "explorer"）
   - **每篇笔记写入时立即生成 `article_id` 并写入 frontmatter**（格式：`OBA-{8位随机小写字母数字}`，全局唯一性校验）
   - **更新 Question.md**：对本次新建的每篇笔记，检查其 `article_id` 是否已在 Question.md 中有对应 section，若没有则在末尾追加（格式见 `references/question-template.md`）
2. **环境准备章节（可选）**：如果项目需要安装、配置等前置步骤，生成 `explorer/00-{repo-name}-environment-setup.md`（纯代码分析项目可跳过）
3. 设置 `surveyState = "completed"`
4. **首次研究强制生成导读指南**：检查 `explorer/` 中是否已有 `*-guide.md`，若不存在则生成（带编号前缀）
5. **可选 Cheat Sheet 生成**：如果项目是工具/库/CLI（有明确安装和使用命令），在首次研究时提示用户是否生成 Cheat Sheet
6. 中文提问时提示翻译功能

> 📝 **导读指南完整模板** → `references/guide-template.md`
> 📝 **subagent prompt 模板、输出模板** → `references/yolo-mode-guide.md` §1-3
>
> ⚠️ **强制规则**：每个项目首次研究时必须生成导读指南，不可跳过。指南是 explorer/ 的入口文档。
> ⚠️ **00- 规则**：如果项目是工具/CLI/库（需要安装和环境配置），必须生成 `00-` 环境准备章节。纯代码分析项目可跳过。

---

## Phase 5b: 研究 — 交互模式

> 📖 **详细文档** → `references/interactive-mode-guide.md`

核心流程：文档感知 subagent + 代码分析 subagent → 概念拆解 → 逐步讲解 → 实时归档。

- 启动 subagent 静默分析代码，主会话创建 `.study-session.json` 和概念列表
- 逐步讲解每个概念，每步后提供选项：继续/暂停/更多解释/提问
- 实时归档到 `explorer/`，支持 `/repo-study continue` 恢复中断
- 首次研究时：环境准备章节（00-，如需）+ 强制生成导读指南（模板同 Phase 5a）
- 完成后设置 `surveyState = "completed"`

> ⚠️ **Checkpoint - Human-Verify** — 调研完成后确认概念列表再开始讲解。

---

## Phase 5c: 增量问答 (incremental) — Incremental 模式

> 适用场景：survey 完成后，用户针对特定话题/文章提问。
> 产出目录：`notes/`（零散笔记，不成体系）

### Step 5c.1: 解析增量问题

从用户输入中提取具体的研究问题，确定需要分析的代码区域。

### Step 5c.2: 启动针对性 subagent

启动 subagent（蓝色标识，Explore 类型），**只分析相关代码区域**，不重复 survey 已覆盖的内容。

> 📝 **subagent prompt 模板** → `references/yolo-mode-guide.md` §4

### Step 5c.3: 写入笔记

将研究结果写入 `notes/{topic-slug}.md`，命名简洁直接（如 `skill-prompt-engineering.md`）。

**写入时立即生成 `article_id` 并写入 frontmatter**（格式：`OBA-{8位随机小写字母数字}`，全局唯一性校验）。

笔记结构：
```markdown
# {话题标题}

> 关联教程：explorer/{related-tutorial-note}.md（如有）

## 问题
// 用户原始问题

## 分析
// 针对性分析内容

## 关键发现
// 核心洞察，1-3 点
```

### Step 5c.4: 更新元数据

更新 `.study-meta.json`：
- 在 `topics[]` 中新增条目，标记 `location: "notes"`
- 更新 `lastUpdated` 时间戳

**更新 Question.md**：对本次新建的笔记，检查其 `article_id` 是否已在 Question.md 中有对应 section，若没有则在末尾追加：
```
## {article_id}
<!-- {笔记相对路径} -->












```
（8 行空白用于用户后续编辑。格式参考 `references/question-template.md`）

---

## Phase 5.5: 自动同步检测 (auto-sync) — 研究完成后自动触发

> **触发时机**：Phase 5a（Yolo）、5b（交互）、5c（增量）完成后自动执行。
> **目的**：减少用户手动同步的心智负担，让笔记自动流入 Obsidian 知识库。

### Step 5.5.1: 检测 Obsidian 配置

从 CLAUDE.md 配置中检测 `OBSIDIAN_REPO` 是否存在且路径有效：

```bash
# 检查 Obsidian 仓库路径是否配置且存在
test -d "$OBSIDIAN_REPO" && echo "ob_available" || echo "ob_unavailable"
```

- 若 `OBSIDIAN_REPO` 未配置或路径不存在 → **跳过**，不提示用户
- 若路径有效 → 进入 Step 5.5.2

### Step 5.5.2: 询问用户是否同步

使用 AskUserQuestion 询问用户：

> **问题**：检测到 Obsidian 仓库已配置，是否将本次新生成/更新的笔记同步到 Obsidian？
>
> | 选项 | 说明 |
> |------|------|
> | 是，同步到 Obsidian | 执行 Phase 8 的同步流程（仅当前项目） |
> | 否，稍后手动同步 | 跳过，用户可通过 `/repo-study sync` 手动触发 |
> | 本次会话不再询问 | 标记会话状态，后续增量问答时不再提示 |

### Step 5.5.3: 执行同步（仅当前项目）

用户选择"是"时，执行 **当前项目** 的同步（不等同于 `/repo-study sync` 的全量同步）：

1. 为本次新生成/更新的笔记分配 `article_id`（`OBA-xxx`）
2. 在 Obsidian 仓库创建 symlink：
   - `wiki/open-source/{project}/explorer` → `{study项目}/explorer`
   - `wiki/open-source/{project}/notes` → `{study项目}/notes`
   - `wiki/open-source/{project}/Question.md` → `{study项目}/Question.md`（如存在）
3. 生成/更新 `wiki/open-source/{project}/index.md` 概述页
4. 更新 `wiki/open-source/index.md` 总索引
5. 输出同步结果摘要

### Step 5.5.4: 会话状态标记

用户选择"本次会话不再询问"时，在会话上下文中标记 `skip_ob_sync = true`，后续 Phase 5c 增量问答完成时不再触发自动同步提示。

> ⚠️ **注意**：此标记仅在当前 Claude Code 会话中有效，新会话会重新检测。

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
> 2. 生成实操指南 → `explorer/NN-{主题}-guide.md`（成体系，带编号）
> 3. **生成教程** → 进入 Phase 6b（教程两阶段工作流，产出到 `explorer/`，带编号）
> 4. 生成 Skill 模板 → `notes/{主题}-skill.md`（零散笔记）
> 5. **生成 Cheat Sheet** → 进入 Phase 6d（专属 subagent，产出到 `explorer/cheatsheet/`）
> 6. 生成小白指南 → `explorer/NN-{repo-name}-beginner-guide.md`（成体系，带编号）
> 7. **生成技术展示文章** → 进入 Phase 6c（产出到 `notes/`）
> 8. **生成 Skill 映射** → `notes/{repo-name}-skill-to-script-mapping.md`（零散笔记）
> 9. 全部生成

最后更新研究日志 `explorer/RESEARCH-LOG.md` 并同步 `topics[].progress`。

**产出路径规则**：
- 环境准备（安装、配置、前置依赖）→ `explorer/00-{repo-name}-environment-setup.md`（**00- 固定前缀**，工具/CLI/库项目必须生成）
- 成体系的内容（指南、教程、小白指南）→ `explorer/`（**文件名带 2 位索引前缀，从 01- 起**）
- 速查卡片（Cheat Sheet）→ `explorer/cheatsheet/`（**不带编号**，每维度一份）
- 零散/独立的内容（文章、Skill 映射）→ `notes/`（不带编号）

---

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

### Step 10.4: AI 拆解（subagent）

> **注意**：此步骤基于 Step 10.3b 生成的临时批次文件（`Question-{N}.md`），不再直接读取 Question.md。

**对于 (A) 顶部自由内容**：直接在主会话中分析处理（从临时批次文件读取），不启动 subagent。根据内容类型决定处理方式：
- 文件移动/重命名 → 直接执行
- 目录结构调整 → 直接执行
- repo-study skill 改进建议 → 记录到 jacky-skills 项目的改进 backlog 或直接修改 skill
- 其他反馈 → 讨论后执行

**对于 (B) article_id sections**：启动一个 Explore 类型 subagent，传入临时批次文件内容 + 对应笔记路径 + 源码路径：

```
你是代码分析和知识补充专家。

用户在阅读研究笔记时，遇到看不懂的地方，写在了批次文件里。请：

1. 读取以下批次文件中每个 article_id section 的内容
2. 找到对应的研究笔记（通过 article_id 在 explorer/ 和 notes/ 中搜索 frontmatter）
3. 理解用户写的内容（可能是问题、困惑、"看不懂"、需要补充示例等）
4. 分析源码，找到答案或补充材料
5. 提出具体补充方案：在原笔记的哪个位置补充什么内容

**源码路径**: {项目目录}/{repo-name}/
**研究笔记路径**: {项目目录}/explorer/ 和 {项目目录}/notes/
**批次文件内容**:
{Question-{N}.md 全文}

**输出格式**（每个 section 一组）：

### section: {article_id}
- **对应笔记**: {找到的笔记路径}
- **用户诉求**: {AI 对用户内容的理解，1-2 句}
- **补充内容**: {可直接写入笔记的 Markdown 内容}
- **插入位置**: {在笔记中的哪个 section 之后插入，如"## 三、xxx 之后"}
```

### Step 10.5: 执行补充

主会话收到 subagent 分析结果后，对每个 section：

1. 找到对应的研究笔记文件
2. 将补充内容插入到指定位置
3. 保留原有内容，只做追加/补充
4. 展示补充摘要给用户确认

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

</process>

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
场景 6: output    → 指南 / 教程 / 模板 / Cheat Sheet / 小白指南 / 技术展示文章 / Skill 映射 / 全部
场景 7: continue  → 恢复交互学习
场景 8: sync      → 同步到 Obsidian（article_id + symlink + 索引）
场景 8b: translate → 并行 subagent 翻译 *.md → *.zh.md
场景 9: distill   → backlog → demo 工程 / skill 设计文档
场景 10: answer   → 读取 Question.md → subagent 回答 → notes/question-{NN}.md → 归档已解决

安全保障：explorer/ 和 notes/ 永不删除 | 版本检查：gh api commit SHA
```

</scenarios>

<!-- ========== 成功标准 ========== -->
<success_criteria>
- [ ] 正确解析仓库 URL，项目路径从 CLAUDE.md 读取
- [ ] 检测 study 标识（目录名 + .study-meta.json），使用 gh api 检查远程版本
- [ ] 项目创建时包含 explorer/ 和 notes/ 两个目录
- [ ] 项目创建/更新时，explorer/ 和 notes/ 目录永不删除
- [ ] 双模式检测：根据 surveyState 自动判断 Survey/Incremental 模式
- [ ] Survey 模式：产出成体系笔记到 explorer/，文件名带 2 位索引前缀（00- 环境准备 + 01- 正式内容），完成后设置 surveyState = "completed"
- [ ] Incremental 模式：产出零散笔记到 notes/，针对用户问题分析
- [ ] 文档资源扫描：检测 docs/、README.md 等文档并分类
- [ ] Yolo 模式：文档感知 subagent → 代码分析 subagent → 合并输出到 explorer/（带编号）
- [ ] 交互模式：subagent 调研 → 概念拆解 → 逐步讲解 → 实时归档到 explorer/（带编号）
- [ ] 首次研究强制生成导读指南 explorer/NN-{repo-name}-guide.md（带编号）
- [ ] 工具/CLI/库项目首次研究时生成环境准备章节 explorer/00-{repo-name}-environment-setup.md
- [ ] 产出路径规则：环境准备→explorer/00-（固定），成体系→explorer/01+（带编号），速查卡片→explorer/cheatsheet/（不带编号），零散→notes/（不带编号）
- [ ] 教程两阶段分离：T1 配置引导（人工）+ T2 逐章实测（subagent）
- [ ] 技术展示文章：素材收集 → subagent 生成 → 质量检查 → 沉淀到 notes/
- [ ] Cheat Sheet 专属 subagent（Phase 6d）：识别维度 → subagent 提炼 → 沉淀到 explorer/cheatsheet/ → 更新索引
- [ ] 翻译：*.md → *.zh.md，不修改源文件，按 group 并行
- [ ] sync：article_id 分配 + symlink（覆盖 explorer/、notes/ 和 Question.md）+ 索引生成
- [ ] distill：backlog → 独立可运行的 demo 工程
- [ ] Question.md：项目创建时自动生成（含 AI 预设问题），sync 时通过 symlink 同步到 Obsidian
- [ ] answer：读取 Question.md 的顶部自由内容（整体建议）和 article_id section → 顶部内容主会话直接处理 / article_id subagent 拆解补充 → 清理已处理内容
- [ ] Skill 项目检测：检测 SKILL.md 存在时标记为 skill-type，提取 skill 名称和脚本列表
- [ ] skill-type 项目：自动生成 skill→script 映射分析 + 脚本验收测试
- [ ] 自动同步检测（Phase 5.5）：研究完成后检测 OBSIDIAN_REPO 配置，路径有效时自动询问是否同步到 Obsidian（仅当前项目），支持跳过和本次会话不再询问
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

## ⚠️ 用户交互点总结

| 阶段 | 交互点 | 类型 | 用户操作 |
|------|--------|------|----------|
| Phase 1 | 🛑 版本落后提示 | Decision | 选择是否更新源码 |
| Phase 3.5 | 🔄 模式检测 | Auto | 根据 surveyState 自动判断 |
| Phase 3.5 | 🔄 调研中断确认 | Decision | 仅 surveyState="in-progress" 时，继续/切换 |
| Phase 2 | ✅ 文件结构验证 | Human-Verify | 确认文件结构完整（含 explorer/ 和 notes/） |
| Phase 4 | 🔄 研究风格选择 | Decision | 选择 Yolo/交互模式（仅 Survey 模式） |
| Phase 5b | ✅ 调研完成确认 | Human-Verify | 确认概念列表 |
| Phase 5b | 🔄 理解确认 | Decision | 继续/暂停/更多解释/提问 |
| Phase 5.5 | 🔄 自动同步提示 | Decision | 检测到 Obsidian 时自动询问是否同步（仅当前项目）/跳过/不再询问 |
| Phase 6 | 🔄 产出选择 | Decision | 继续研究/指南/教程/模板/Cheat Sheet/小白指南/技术展示文章/Skill 映射/全部 |
| Phase 6b-T1 | ✅ 配置完成确认 | Human-Verify | 用户完成所有配置步骤，检查清单全通过 |
| Phase 6b-T2 | 🔄 实测结果审核 | Human-Verify | 确认实测数据，处理失败的命令 |
| Phase 7 | 🔄 恢复确认 | Decision | 继续/重新开始 |
| Phase 10 | 🔄 问题选择 | Decision | 全部回答/选择部分回答/取消 |
