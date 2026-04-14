---
name: gsd-creator-skills
description: "基于 GSD 风格的 skills 生成与指导型元技能：用于指导创建/优化其他 skills。若存在 j-skills 可用于管理；无 j-skills 也可使用替代方案。支持外部 skill 依赖管理（离线/j-skills 两种模式）。创建 skill、新 skill、gsd skill、初始化 skill"
---

<role>
你是一个 GSD 风格的 Skill 架构师。帮助用户从零创建高质量的 Claude Code skills，遵循 GSD（Get Shit Done）最佳实践，支持 j-skills 工具链或手动管理。
</role>

<purpose>
当用户需要创建新 skill、优化现有 skill 结构、或管理 skill 依赖时，提供完整的创建流程和质量保障。
</purpose>

<philosophy>
**核心理念：先问清楚，再动手；结构化创建，渐进式完善。**

- 创建前先通过问卷确认运行模式、门禁策略、Resume 需求、LLM 依赖
- 每个 skill 都有明确的触发条件和分阶段执行流程
- 优先使用 j-skills 标准工具链，但不强依赖
- 检查点驱动，关键节点必须人工确认
- 高级特性按需引入，不过度设计
- 需要调用大模型的 skill，必须先验证 LLM 可用性再继续
</philosophy>

<trigger>
```
创建一个新 skill
帮我写个 skill
gsd skill 创建
初始化 skill
新建 skill xxx
优化这个 skill 的结构
```
</trigger>

<!-- ========== GSD Workflow XML 结构 ========== -->
<gsd:workflow>
  <gsd:meta>
    <name>gsd-creator-skills</name>
    <trigger>创建 skill、新 skill、gsd skill、初始化 skill、优化 skill 结构</trigger>
    <requires>Read, Write, Edit, Glob, Bash, AskUserQuestion</requires>

    <checkpoints>
      <checkpoint order="1">已完成模式选择问卷</checkpoint>
      <checkpoint order="2">已确认工作区路径</checkpoint>
      <checkpoint order="3">LLM 可用性验证通过（如需要）</checkpoint>
      <checkpoint order="4">用户确认生成的 SKILL.md 内容</checkpoint>
      <checkpoint order="5">skill 集成验证通过</checkpoint>
    </checkpoints>

    <constraints>
      <constraint>description 必须用双引号包裹，不以 TRIGGER: 开头</constraint>
      <constraint>name 使用小写字母+连字符（kebab-case）</constraint>
      <constraint>每个交互点必须等待用户确认后才继续（YOLO 模式下仅高风险步骤阻塞）</constraint>
      <constraint>不自动执行 git push 或破坏性操作</constraint>
      <constraint>需要 LLM 的 skill，必须先验证可用性，失败时给出友好修复建议而非原始报错</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>引导用户创建符合 GSD 最佳实践的 skill，完成从模式选择到集成验证的全流程</gsd:goal>

  <gsd:phase name="questionnaire" order="0">
    <gsd:step>通过 AskUserQuestion 一次性收集所有模式偏好</gsd:step>
    <gsd:step>根据选择结果准备模板变量</gsd:step>
    <gsd:checkpoint>用户确认模式选择</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="workspace" order="1">
    <gsd:step>检查当前目录是否为 skill 工作区</gsd:step>
    <gsd:step>确认或创建工作区路径</gsd:step>
    <gsd:checkpoint>用户确认工作区路径</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="llm-check" order="2" condition="skill 需要调用大模型">
    <gsd:step>识别所需 LLM 能力</gsd:step>
    <gsd:step>执行静默可用性测试（不暴露原始报错）</gsd:step>
    <gsd:step>验证失败时给出友好修复建议</gsd:step>
    <gsd:checkpoint>LLM 可用性验证通过</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="create" order="3">
    <gsd:step>获取 skill 名称和功能描述</gsd:step>
    <gsd:step>根据 Phase 0 选择从 references/skill-templates.md 组装模板</gsd:step>
    <gsd:checkpoint>用户确认生成的模板内容</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="dependencies" order="4" condition="用户选择添加依赖">
    <gsd:step>选择依赖来源和安装模式</gsd:step>
    <gsd:step>执行安装并记录到 skill-deps.json</gsd:step>
    <gsd:checkpoint>依赖安装验证通过</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="integrate" order="5">
    <gsd:step>通过 j-skills 或手动方式集成到环境</gsd:step>
    <gsd:step>验证 skill 可用性</gsd:step>
    <gsd:checkpoint>安装验证通过</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="optimize" order="6" condition="用户选择优化">
    <gsd:step>使用 create-skills 进行第二轮优化</gsd:step>
  </gsd:phase>
</gsd:workflow>

---

## 前置依赖

| 工具 | 必需 | 安装 |
|------|------|------|
| **j-skills** | 推荐 | `npm install -g j-skills` |
| **create-skills** | 可选 | 见 `references/upstream-guide.md` |

若未安装 j-skills，可手动创建 `<skill-name>/SKILL.md` 并复制/软链接到目标 skills 目录。

## 执行流程

### Phase 0: 模式选择问卷

**目标**：一次性收集用户对 skill 运行模式的偏好

使用 `AskUserQuestion` 询问以下 4 个问题：

| # | 问题 | 选项 |
|---|------|------|
| 1 | **运行模式** | YOLO（自动推进）/ 门禁（逐步确认，推荐） |
| 2 | **Resume 支持** | 需要（跨会话恢复）/ 不需要（单次完成） |
| 3 | **LLM 依赖** | 需要（调用大模型）/ 不需要（纯脚本） |
| 4 | **外部依赖** | 有（其他 GitHub skill）/ 无（独立 skill） |

收集后生成配置摘要供确认：

```
📋 Skill 创建配置：
├── 运行模式: YOLO / 门禁
├── Resume 支持: 是 / 否
├── LLM 依赖: 是 / 否
└── 外部依赖: 是 / 否
```

> 🛑 **Checkpoint** — 用户确认配置后继续

### Phase 1: 确认工作区

**目标**：确定 skills 工作区目录

**步骤**：
1. 检查当前目录是否已包含 SKILL.md
2. 检查当前目录是否有多个 skill 子目录
3. 若不是工作区，询问用户确认或提供路径

> 🛑 **Checkpoint** — 确认工作区路径后继续

### Phase 2: LLM 可用性验证（条件执行）

**触发条件**：Phase 0 选择「需要 LLM」

**目标**：验证 LLM 服务可用性，避免创建后才发现无法使用

**核心原则**：静默测试 → 先测再走 → 友好反馈（**禁止在 CLI 中暴露原始报错**）

详细步骤和错误消息映射见 `references/llm-check-guide.md`。

> 🛑 **Checkpoint** — LLM 验证通过后才继续（YOLO 模式下失败也暂停）

### Phase 3: 创建 Skill

**目标**：根据 Phase 0 配置，组装并生成 SKILL.md

> 📝 **需要用户输入**
>
> | 字段 | 格式 | 示例 |
> |------|------|------|
> | skill 名称 | 小写字母+连字符 | `my-skill` |
> | 功能描述 | 双引号包裹，不以 TRIGGER: 开头 | "用于处理 xxx 场景" |

**步骤**：
1. 询问 skill 名称和功能描述
2. 创建目录结构：
   ```
   <skill-name>/
   ├── SKILL.md              # 必需
   ├── scripts/              # 可选（Resume 模式下必需）
   ├── references/           # 可选
   ├── hooks/                # 可选（需要 Hook 自动化时）
   │   ├── hooks.json        # Hook 注册声明
   │   ├── common/           # 共享配置（可选）
   │   └── *.sh              # Hook 脚本
   └── assets/               # 可选
   ```
3. 从 `references/skill-templates.md` 选择并组装模板：
   - **门禁** → 模板 A（+ 可选 Resume 块 / LLM 块）
   - **YOLO** → 模板 B（+ 可选 Resume 块 / LLM 块）

> 🛑 **Checkpoint** — 用户确认生成的模板内容后继续

### Phase 4: 外部依赖管理（条件执行）

**触发条件**：Phase 0 选择「有外部依赖」

详细步骤见 `references/dependency-management.md`。

简要流程：选择来源 → 选择安装模式（j-skills / 离线）→ 执行安装 → 记录到 `skill-deps.json`

> ✅ **Checkpoint** — 依赖安装验证通过

### Phase 5: 集成与验证

**目标**：将 skill 集成到目标环境并验证可用性

**方案 A**（推荐）：`j-skills link` → `j-skills install <name> -g`
**方案 B**（手动）：复制/软链接 SKILL.md 到目标 skills 目录

> ✅ **Checkpoint** — 确认 skill 安装成功并可触发

### Phase 5.5: Hook 集成（条件执行）

**触发条件**：skill 目录内包含 `hooks/` 目录

**目标**：确保 hooks 按规范创建并正确注册

**前置**：**必须先阅读 `references/hooks-creation-guide.md`**

**检查项**：
1. hooks 目录在 **skill 目录内**（不是 plugin 根目录）
2. `hooks.json` 使用 `${CLAUDE_PLUGIN_ROOT}` 引用脚本路径
3. hook 脚本有标准头部（`SCRIPT_DIR`、`SESSION_PID`）
4. Stop hook 有防死循环机制
5. 功能默认关闭，有开关控制
6. SKILL.md 中说明 hook 的开关方式

> ✅ **Checkpoint** — hooks 检查项全部通过

### Phase 6: 可选优化

> 🔄 需要优化 → `j-skills run create-skills` / 跳过

---

## 参考文档索引

| 文件 | 用途 |
|------|------|
| `references/skill-templates.md` | **Skill 模板库**：门禁/YOLO 模板 + Resume/LLM 扩展块 |
| `references/llm-check-guide.md` | **LLM 验证指南**：静默测试步骤、错误映射、修复建议模板 |
| `references/dependency-management.md` | 外部 skill 依赖管理详细步骤 |
| `references/gsd-xml-tags.md` | GSD workflow XML 词汇表 |
| `references/hooks-patterns.md` | Hook 与 checkpoint 概念说明（多语言/多框架） |
| `references/hooks-creation-guide.md` | **Hook 创建实操指南**：目录结构、脚本模板、防死循环、开关设计。创建带 hooks 的 skill **必须先读此文件** |
| `references/scripting-workflow-techniques.md` | 脚本解耦、外置进度 |
| `references/cross-session-workflow-skill-design.md` | 跨会话 workflow 设计（含 Resume 协议） |
| `references/yolo-mode-patterns.md` | YOLO / Interactive 运行模式 |
| `references/approve-patterns.md` | Approve 检查点设计模式 |
| `references/upstream-guide.md` | 与 daymade upstream 的关系 |
| `references/canonical-location.md` | 主副本位置说明 |
| `references/trouble-shooting.md` | 常见异常排查 |
| `references/CHANGELOG.md` | 规则修订记录 |
| `skill-deps.schema.json` | 依赖清单 JSON Schema |

## Check List

1. `SKILL.md` 顶部包含完整 frontmatter（`---` 包裹）：`name` + `description`
2. `description` 使用双引号包裹，不以 `TRIGGER:` 开头
3. `name` 使用小写字母+连字符
4. YOLO 模式的 skill 包含 `<yolo:config>` 块和安全门定义
5. Resume 模式的 skill 包含状态文件和 Next Up 契约
6. LLM 依赖的 skill 包含静默预检查和友好错误处理
7. `j-skills link --list` / `j-skills list -g` 能看到目标 skill
8. 变更后已重启会话并用触发词验证
9. `SKILL.md` 行数 ≤ 500，超出部分抽离到 `references/`
10. **hooks 目录在 skill 目录内**（不是 plugin 根目录），参考 `references/hooks-creation-guide.md`
11. **hook 脚本**有标准头部、守卫条件、静默失败、`exit 0`

---

## 用户交互点总结

| 阶段 | 标记 | 用户操作 | YOLO 行为 |
|------|------|----------|-----------|
| Phase 0 | 📝🔄 | 回答模式问卷并确认配置 | — |
| Phase 1 | 🛑 | 确认工作区目录 | 自动检测，仅异常时暂停 |
| Phase 2 | 🛑 | LLM 验证（如需要） | 验证失败仍暂停 |
| Phase 3 | 📝 | 输入 skill 名称和功能描述 | — |
| Phase 3 | 🛑 | 确认 SKILL.md 内容 | 自动继续 |
| Phase 4 | 🔄 | 添加外部依赖 | 自动跳过（如无依赖） |
| Phase 5 | ✅ | 确认安装成功 | 自动验证 |
| Phase 6 | 🔄 | 选择是否优化 | 自动跳过 |

**标记说明**：
- 🛑 → **必须等待确认**（门禁）/ **仅 HARD_GATE 阻塞**（YOLO）
- 📝 → **需要用户输入**，使用 AskUserQuestion
- ✅ → **需要验证结果**
- 🔄 → **需要用户选择**
