# Learn Repo 工作流契约

> 需要核对机器可读的 phase、checkpoint、工具依赖或硬约束时读取。日常执行以 SKILL.md 的执行流程为主。

<gsd:workflow>
  <gsd:meta>
    <name>learn-repo</name>
    <trigger>学习项目、理解代码、搞懂原理、继续学习、resume 学习日志</trigger>
    <requires>Read, Write, Edit, Glob, Bash, AskUserQuestion, Skill(web-search)</requires>

    <checkpoints>
      <checkpoint order="1">上下文恢复完成（已读取 overview 或确认无历史日志）</checkpoint>
      <checkpoint order="2">用户已明确确认今日话题、知识水平、学习目标</checkpoint>
      <checkpoint order="3">overview.md 创建/恢复完成，用户确认结构</checkpoint>
      <checkpoint order="4">章节讲解结束，用户明确回复"无疑问"</checkpoint>
      <checkpoint order="5">笔记写入后 overview 四个部分已全部同步</checkpoint>
    </checkpoints>

    <constraints>
      <constraint>【硬约束】禁止把任何学习笔记/产出写入被学习的原仓库，必须写到兄弟目录 {repo-name}-study/ 下</constraint>
      <constraint>学习前必须在 {repo-name}-study/ 下做源码快照（git clone --depth 1 + 删 .git），并把 commit SHA 记进 .study-meta.json，保证笔记可追溯</constraint>
      <constraint>用户未明确确认今日话题前，禁止创建任何文件或目录（含 study 目录与源码快照）</constraint>
      <constraint>章节讲解完毕必须先问"还有什么不明白的吗？"，用户确认无疑问后才能写笔记</constraint>
      <constraint>禁止讲解一结束就立即写笔记，必须经过确认环节</constraint>
      <constraint>每写一篇主题笔记，必须同步更新 overview 的全部四个部分</constraint>
      <constraint>所有文件命名使用简洁英文短横线（kebab-case）</constraint>
      <constraint>需要联网搜索时必须先调用 web-search skill，禁止直接调用 WebSearch / web-search-prime 等工具</constraint>
      <constraint>不重复创建已存在的 overview.md，应在原文件上继续追加</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>通过持续的交互式教学，把项目相关知识沉淀为结构化、可追溯、有进度的学习日志</gsd:goal>

  <gsd:phase name="resume" order="0">
    <gsd:step>Glob 查找 {GitHub 项目目录}/*-study/docs/topics/**/*-overview.md</gsd:step>
    <gsd:step>读取最近 overview，恢复学员背景、学习路线、当前进度</gsd:step>
    <gsd:checkpoint>用户确认恢复的上下文准确，或确认从零开始</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="kickoff" order="1">
    <gsd:step>询问今日话题</gsd:step>
    <gsd:step>评估用户已有知识水平</gsd:step>
    <gsd:step>明确学习目标</gsd:step>
    <gsd:checkpoint>三要素全部明确后才允许进入下一阶段</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="workspace" order="1.5">
    <gsd:step>确定被学习的仓库：默认 = cwd 所在 git 仓库；或用户给定的 URL/路径</gsd:step>
    <gsd:step>从 CLAUDE.md 读取 GitHub 项目目录，算出 study 目录 = {GitHub 项目目录}/{repo-name}-study</gsd:step>
    <gsd:step condition="study 目录不存在">创建 study 目录；git clone --depth 1 源码到 source/；删除 .git；记录 commit SHA 到 .study-meta.json</gsd:step>
    <gsd:step condition="study 目录已存在">复用；如学习同一仓库新主题，仅在 docs/topics/ 下新增，不重复 clone</gsd:step>
    <gsd:checkpoint>study 目录与源码快照就绪，.study-meta.json 已记录 repo + commit</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="overview" order="2">
    <gsd:step>创建 {study目录}/docs/topics/&lt;topic-name&gt;/&lt;date&gt;-&lt;topic&gt;-overview.md</gsd:step>
    <gsd:step>填充 6 个标准小节</gsd:step>
    <gsd:checkpoint>用户确认 overview 结构和学习路线</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="teach" order="3" loop="true">
    <gsd:step>先考：问"你觉得这是什么？"</gsd:step>
    <gsd:step>诊断：逐条点评回答（需强化 / 需纠错 / 是空白）</gsd:step>
    <gsd:step>讲解：从空白处补全，用比喻和实战驱动</gsd:step>
    <gsd:step>延伸：问一个验证型问题</gsd:step>
    <gsd:step>必要时通过 web-search skill 联网调研</gsd:step>
    <gsd:checkpoint>问"这一章还有什么不明白的吗？"必须得到明确确认</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="persist" order="4">
    <gsd:step>写入 {study目录}/docs/topics/&lt;topic&gt;/&lt;date&gt;-&lt;topic&gt;-&lt;chapter&gt;.md</gsd:step>
    <gsd:step>同步 overview：笔记目录表 / 知识全景图 / 认知纠错记录 / 下次学习建议</gsd:step>
    <gsd:checkpoint>四个部分全部同步完成，回到 Phase 3 进入下一章节</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

