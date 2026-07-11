# YOLO 研究执行步骤

> 用户选择 Survey + YOLO 模式时读取。通用原则和完整 prompt 仍见 yolo-mode-guide.md。

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

### Step 5a.3b: Capability Discovery（能力发现） — YOLO 模式强制步骤

> 🎯 **目标**：穷举项目所有可操作能力，生成对应的 Cheat Sheet。此步骤确保研究不仅覆盖架构理解，还覆盖全部可实操的内容。

**触发条件**：YOLO 模式下的所有项目（不可跳过）。

**启动 Capability Discovery subagent**（Explore 类型）：

**扫描范围**（根据项目类型自适应）：

| 项目类型 | 扫描目标 | 示例 |
|----------|----------|------|
| CLI 工具 | 所有命令、子命令、参数、选项 | `clis/` 目录、`cli()` 注册、`commander/yargs` 定义 |
| REST API | 所有端点、方法、参数、响应 | `routes/`、`@Controller`、OpenAPI spec |
| 库/SDK | 所有公开 API、类、函数、配置项 | `export` 列表、`index.ts`、类型定义 |
| 插件系统 | 所有插件钩子、扩展点、生命周期 | `plugin/`、`hook`、`middleware` |
| 框架 | 所有配置项、中间件、组件、指令 | `config/`、`directive/`、`component/` |
| 浏览器扩展 | 所有浏览器 API 调用、content script、popup | `manifest.json`、`background.ts`、`content.ts` |
| 配置驱动 | 所有配置项、环境变量、选项 | `.env.example`、`config/`、`settings/` |

**扫描方法**：
1. **文件结构扫描**：Glob 搜索注册文件、路由文件、命令定义文件
2. **模式匹配**：Grep 搜索常见的注册模式（`cli(`、`command(`、`router.`、`app.get`、`export`、`register`）
3. **Manifest/Config 读取**：读取 `package.json`（bin 字段）、`manifest.json`、CLI manifest 等
4. **文档交叉验证**：对比 `docs/` 和 `README.md` 中列出的功能与源码中的实际实现

**Cheat Sheet 生成规则**：
1. **按维度分文件**：每个有意义的维度生成一份独立 Cheat Sheet（如"命令速查"、"API 速查"、"配置速查"）
2. **文件命名**：`explorer/cheatsheet/{topic}-cheat-sheet.md`（不带编号）
3. **每份 Cheat Sheet 必须包含**：标题 + 一句话说明 + 分维度表格 + 使用示例 + article_id
4. **表格格式**：命令/操作 | 干什么 | 关键参数 | 示例
5. **对于大型项目**（命令/API 数量 > 50），额外生成一份**总览 Cheat Sheet**（`explorer/cheatsheet/all-{dimension}-cheat-sheet.md`），按分类组织所有内容

> 📝 **详细 subagent prompt 模板** → `references/yolo-mode-guide.md` §6

### Step 5a.4: 沉淀与指南

1. 沉淀笔记到 `explorer/`（**文件名必须带 2 位索引前缀**，如 `01-xxx.md`、`02-xxx.md`）并更新 `.study-meta.json` 的 `topics[]`（location: "explorer"）
   - **每篇笔记写入时立即生成 `article_id` 并写入 frontmatter**（格式：`OBA-{8位随机小写字母数字}`，全局唯一性校验）
   - **更新 Question.md**：对本次新建的每篇笔记，检查其 `article_id` 是否已在 Question.md 中有对应 section，若没有则在末尾追加（格式见 `references/question-template.md`）
2. **环境准备章节（可选）**：如果项目需要安装、配置等前置步骤，生成 `explorer/00-{repo-name}-environment-setup.md`（纯代码分析项目可跳过）
3. 设置 `surveyState = "completed"`
4. **首次研究强制生成导读指南**：检查 `explorer/` 中是否已有 `*-guide.md`，若不存在则生成（带编号前缀）
5. **自动 Capability Discovery + Cheat Sheet 生成**：启动 Capability Discovery subagent，扫描项目所有可操作能力（命令/API/配置/端点/插件钩子等），自动生成对应 Cheat Sheet 到 `explorer/cheatsheet/`。此项为 YOLO 模式强制步骤，不可跳过（详见 references/yolo-mode-guide.md §6）
6. 中文提问时提示翻译功能

> 📝 **导读指南完整模板** → `references/guide-template.md`
> 📝 **subagent prompt 模板、输出模板** → `references/yolo-mode-guide.md` §1-3
>
> ⚠️ **强制规则**：每个项目首次研究时必须生成导读指南，不可跳过。指南是 explorer/ 的入口文档。
> ⚠️ **00- 规则**：如果项目是工具/CLI/库（需要安装和环境配置），必须生成 `00-` 环境准备章节。纯代码分析项目可跳过。

---


