# Repo Study 工作流契约

> 需要核对完整 phase 图、条件分支、checkpoint 或各模式工具依赖时读取。实际执行以 SKILL.md 路由和对应 reference 的详细步骤为准。

## 目录

- [检测、创建与更新](#repo-study-工作流契约)
- [Survey 与 Incremental 研究分支](#repo-study-工作流契约)
- [教程、文章、Cheat Sheet 与实操](#repo-study-工作流契约)
- [同步、翻译、蒸馏与 Answer](#repo-study-工作流契约)

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
    <gsd:step>启动 Capability Discovery subagent：穷举项目所有可操作能力（命令/API/配置/端点），自动生成 Cheat Sheet 到 explorer/cheatsheet/（详见 references/yolo-mode-guide.md §6）</gsd:step>
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
    <gsd:step condition="用户要求实操验证">进入 Phase 5d（实操手册生成，产出 practices/）</gsd:step>
    <gsd:step condition="普通增量问答">写入 notes/{topic-slug}.md</gsd:step>
    <gsd:step condition="普通增量问答">更新 .study-meta.json 的 topics[]（location: "notes"）</gsd:step>
    <gsd:step>执行 Phase 5.5 自动同步检测</gsd:step>
  </gsd:phase>

  <gsd:phase name="research_practice" order="5d" condition="用户要求实操验证（Incremental 模式下）">
    <gsd:step>识别需要验证的命令/操作范围（如某个站点的所有命令、某个功能的操作流程）</gsd:step>
    <gsd:step>逐个执行命令，记录真实输入和输出（每步必须跑通，失败则标注原因和替代方案）</gsd:step>
    <gsd:step>写入 practices/{topic}-practice.md（每个实操文件包含：前置条件 → 命令全景表 → 分章节实操 → 已知问题 → 速查表）</gsd:step>
    <gsd:step>写入时立即生成 article_id 并写入 frontmatter</gsd:step>
    <gsd:step>更新 .study-meta.json 的 topics[]（location: "practices"）</gsd:step>
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
    <gsd:step>询问用户下一步：继续研究 / 生成实操指南 / 生成教程 / 生成 Skill 模板 / 生成 Cheat Sheet / 生成小白指南 / 生成技术展示文章 / 生成 Skill 映射 / 生成实操手册 / 全部生成</gsd:step>
    <gsd:step condition="选择指南或全部">生成 explorer/NN-{主题}-guide.md（小白可执行的实操指南，成体系，带编号）</gsd:step>
    <gsd:step condition="选择教程或全部">进入 Phase 6b（教程两阶段工作流，产出到 explorer/）</gsd:step>
    <gsd:step condition="选择模板或全部">生成 notes/{主题}-skill.md（可复用的 Skill 模板，零散笔记）</gsd:step>
    <gsd:step condition="选择 Cheat Sheet 或全部">进入 Phase 6d（Cheat Sheet 专属 subagent，产出到 explorer/cheatsheet/）</gsd:step>
    <gsd:step condition="选择小白指南或全部">生成 explorer/NN-{repo-name}-beginner-guide.md（零基础完全指南，成体系，带编号）</gsd:step>
    <gsd:step condition="选择 skill 映射或全部">生成 notes/{repo-name}-skill-to-script-mapping.md（skill→script 映射，零散笔记）</gsd:step>
    <gsd:step condition="选择实操手册或全部">进入 Phase 6e（实操手册生成，产出到 practices/）</gsd:step>
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
      <description>Cheat Sheet 专属 subagent：从研究笔记和源码中提炼速查卡片，产出到 explorer/cheatsheet/</description>
      <requires>Agent (subagent), Read, Write</requires>
    </gsd:meta>

    <gsd:phase name="cheatsheet_scan" order="1">
      <gsd:step>扫描 explorer/ 和 notes/ 下所有研究笔记，识别可提炼为速查卡的知识维度</gsd:step>
      <gsd:step>常见维度：命令/API 速查、配置模板、触发词/关键词、数据结构、操作流程</gsd:step>
      <gsd:step>为每个维度生成一份 Cheat Sheet（如项目有多个维度则生成多份）</gsd:step>
      <gsd:step condition="YOLO 模式已完成 Capability Discovery">跳过本步骤，直接使用 Step 5a.3b 已生成的 Cheat Sheet，仅补充用户要求的额外维度</gsd:step>
    </gsd:phase>

    <gsd:phase name="cheatsheet_generate" order="2">
      <gsd:step>启动 Cheat Sheet 专属 subagent（Explore 类型）</gsd:step>
      <gsd:step>subagent 读取所有研究笔记 AND 源码中的命令/API 定义，按维度提炼速查内容</gsd:step>
      <gsd:step>每份 Cheat Sheet 格式：标题 + 一句话说明 + 分维度表格 + 示例 + article_id</gsd:step>
      <gsd:step condition="命令/API 数量 > 50">额外生成一份总览 Cheat Sheet（all-{dimension}-cheat-sheet.md），按分类组织</gsd:step>
    </gsd:phase>

    <gsd:phase name="cheatsheet_save" order="3">
      <gsd:step>创建 explorer/cheatsheet/ 目录（如不存在）</gsd:step>
      <gsd:step>写入 explorer/cheatsheet/{topic}-cheat-sheet.md（每维度一份）</gsd:step>
      <gsd:step>更新 .study-meta.json 的 topics[]（location: "explorer"，子目录 "cheatsheet"）</gsd:step>
      <gsd:step>更新 CLAUDE.md 笔记索引和 explorer/README.md 阅读路径</gsd:step>
    </gsd:phase>
  </gsd:phase>

  <gsd:phase name="practice" order="6e" condition="用户选择生成实操手册">
    <gsd:meta>
      <name>practice-generation</name>
      <description>实操手册生成：逐个命令验证，记录真实输入输出，产出到 practices/</description>
      <requires>Agent (subagent), Bash, Read, Write</requires>
    </gsd:meta>

    <gsd:phase name="practice_identify" order="1">
      <gsd:step>识别实操范围：确定要验证的命令/操作集合（如某个站点的所有命令、某个功能的完整流程）</gsd:step>
      <gsd:step>从 explorer/ 和 notes/ 中提取已有研究素材，识别相关命令和 API</gsd:step>
    </gsd:phase>

    <gsd:phase name="practice_verify" order="2">
      <gsd:step>逐个执行命令，记录真实输入和输出</gsd:step>
      <gsd:step>失败的命令标注原因和替代方案</gsd:step>
      <gsd:step>验证输出格式（yaml/table/json/csv/md）</gsd:step>
    </gsd:phase>

    <gsd:phase name="practice_save" order="3">
      <gsd:step>创建 practices/ 目录（如不存在）</gsd:step>
      <gsd:step>写入 practices/{topic}-practice.md（结构：前置条件 → 命令全景表 → 分章节实操 → 已知问题 → 速查表）</gsd:step>
      <gsd:step>写入时立即生成 article_id 并写入 frontmatter</gsd:step>
      <gsd:step>更新 .study-meta.json 的 topics[]（location: "practices"）</gsd:step>
      <gsd:step>更新 CLAUDE.md 笔记索引</gsd:step>
    </gsd:phase>
  </gsd:phase>

  <gsd:phase name="answer" order="10" condition="用户使用 /repo-study answer">
    <gsd:meta>
      <name>question-answer</name>
      <description>读取 Question.md 中用户记录的看不懂的地方，使用 Multi Teams 并行拆解并补充对应笔记内容（每个 section 一个 teammate）</description>
      <requires>TeamCreate, Agent (teammate), TaskCreate, TaskUpdate, TaskList, SendMessage, TeamDelete, Read, Edit, Write</requires>
    </gsd:meta>
    <gsd:step>读取项目根目录的 Question.md</gsd:step>
    <gsd:step>提取一级标题以下的所有内容，分为两部分：(A) 顶部自由内容（非 article_id section）(B) ## {article_id} section 及其下用户内容</gsd:step>
    <gsd:step condition="A 和 B 均为空">提示"没有待处理的问题"并退出</gsd:step>
    <gsd:step condition="A 不为空">将顶部自由内容作为整体建议/反馈处理（可能是文件移动、流程优化、结构调整等）</gsd:step>
    <gsd:step>展示 section 概况表格（序号 / article_id / 对应笔记 / 内容摘要）</gsd:step>
    <gsd:step>用户选择：全部处理 / 选择部分处理 / 取消</gsd:step>
    <gsd:step condition="选择了 section">立即拆分到临时批次文件 Question-{N}.md，清理 Question.md</gsd:step>
    <gsd:step condition="有 article_id sections">TeamCreate 创建团队 answer-{N}，为每个 section 调用 TaskCreate 创建独立任务</gsd:step>
    <gsd:step condition="有 article_id sections">并行派发 general-purpose 类型 teammates（每个 section 一个），各自读取批次文件 + 对应笔记 + 源码，独立分析并生成补充内容</gsd:step>
    <gsd:step>主会话收集各 teammate 结果，将补充内容插入到对应研究笔记的指定位置</gsd:step>
    <gsd:step>用户确认后清理批次文件，SendMessage shutdown 所有 teammates，TeamDelete 清理团队</gsd:step>
    <gsd:step>输出摘要：处理了 N 个 section，补充了 M 篇笔记</gsd:step>
  </gsd:phase>
</gsd:workflow>
