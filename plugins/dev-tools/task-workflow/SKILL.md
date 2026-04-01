---
name: task-workflow
description: "任务工作流编排工具。整合 task-memory、superpowers、task-harness 形成完整的任务执行流程。触发于 /task-workflow 或\"工作流编排\"、\"任务流程\"等关键词。"
---

# Task Workflow - 任务工作流编排

将复杂任务拆分为可门控的阶段流程：INIT → BRAINSTORM → HARNESS → PLAN → EXECUTE → REVIEW。

## 模式

| 命令 | 说明 |
|------|------|
| `/task-workflow <描述>` | 标准模式 |
| `/task-workflow quick <描述>` | 跳过 BRAINSTORM |
| `/task-workflow yolo <描述>` | 全自动，无门控确认，失败中止（**HARNESS 阶段不可跳过**） |
| `/task-workflow status` | 查看当前状态 |
| `/task-workflow end` | 结束工作流，生成复盘 |

## 复杂度评估（INIT 阶段自动判定）

| 复杂度 | 条件 | 推荐模式 | 门控策略 |
|--------|------|----------|----------|
| 简单 | 影响文件 ≤ 3，无跨模块依赖 | quick | 自动通过 BRAINSTORM，HARNESS 必须执行 |
| 中等 | 影响文件 4-8，有模块间依赖 | standard | HARNESS + PLAN 需确认 |
| 复杂 | 影响文件 > 8，跨系统/架构级变更 | standard | BRAINSTORM + HARNESS + PLAN 需确认 |

> 用户可覆盖推荐模式。yolo 模式仅跳过门控确认，**不跳过任何阶段本身的执行**。

## 工作流阶段

```
INIT → BRAINSTORM → HARNESS → PLAN → EXECUTE → REVIEW
        (quick跳过)                (含验证)    (含复盘)
```

### INIT

1. 生成 task-slug，创建 `.harness/tasks/{slug}/` 目录
2. 检索已有实现（Grep/Glob 扫描相关代码）
3. 评估任务复杂度，向用户展示推荐模式
4. 如 task-memory 可用，启动监听记录初始意图
5. 写入 `workflow.json`

**自适应门控**：简单任务自动进入 HARNESS；中等/复杂任务进入 BRAINSTORM（如果 quick 模式则进入 HARNESS）。

### BRAINSTORM（quick 模式跳过）

调用 superpowers:brainstorming 进行创意发散，生成方案对比，记录最终决策。

**门控**：中等任务自动通过；复杂任务需用户确认。

### HARNESS（**所有模式必须执行，不可跳过**）

基于 brainstorm 结果（或 INIT 检索结果，如果是 quick 模式），定义验收边界和测试用例。

> **强制规则**：yolo 模式仅自动通过门控确认，但 HARNESS 阶段的**执行和分析过程不可省略**。

**如果 task-harness 可用，调用 `/task-harness` 辅助生成。**

**HARNESS 阶段必须产出以下文件**：

| 产物 | 位置 | 说明 |
|------|------|------|
| `harness.md` | `.harness/tasks/{slug}/harness/` | 验收标准（MUST/SHOULD/MAY） |
| BDD case 文件 | `tests/bdd/cases/{page}/T-{prefix}{N}.js` | 步骤描述 |
| 测试脚本 | `tests/bdd/{page}/T-{prefix}{N}.test.ts` | 可执行测试代码 |

**门控**：中等/复杂任务需用户确认验收标准。yolo 模式自动确认。

### PLAN

基于 HARNESS 验收标准 + INIT 检索的已有实现，生成 PLAN.md。必须包含：

- **受影响文件清单**（create/modify/delete）
- **任务依赖关系**
- **风险与回归点**
- **失败模式**（每个关键任务的回退方案）
- **harness_ref**：每个任务必须关联到对应的 HARNESS MUST 条件和 BDD 测试用例

**PLAN.md 任务模板**（每个任务必须包含 `harness_ref`）：

```xml
<task type="auto" id="T1">
  <name>{{任务名称}}</name>
  <files>{{涉及的文件}}</files>
  <action>{{具体行动}}</action>
  <verify>{{验证命令}}</verify>
  <harness_ref>
    - MUST: {{对应的 MUST 条件}}
    - BDD: {{对应的 BDD case 编号，如 T-GH1}}
    - Test: {{对应的测试文件路径}}
  </harness_ref>
</task>
```

**门控**：所有复杂度都需要用户确认执行计划。yolo 模式自动确认。

### EXECUTE（含 TDD 红绿循环验证）

逐个执行 PLAN.md 中的任务，严格按 **TDD 红→绿** 顺序：

1. **Red**：基于 PLAN 中 `harness_ref` 关联的 BDD 测试用例，写失败测试，运行确认失败
2. **Green**：写最小实现代码，测试通过
3. **记录执行偏差**：每个偏差记录到 `.harness/tasks/{slug}/execute/deviations.md`
4. **红绿循环检查点**：每完成一个任务，运行对应的 BDD 测试确认通过

验证失败时循环修复（最多 5 次），超过上限暂停询问用户。

**偏差记录格式**：

```markdown
## 偏差记录

### DEV-001: {{偏差标题}}
- **发生时间**: {{时间戳}}
- **关联任务**: T{{N}}
- **偏差类型**: 设计偏差 / 实现偏差 / 环境偏差
- **描述**: {{偏差描述}}
- **根因**: {{根因分析}}
- **影响范围**: {{影响哪些文件/模块}}
- **处理方式**: {{如何解决}}
```

> 详细 TDD 验证协议见 `references/tdd-protocol.md`

**门控**：yolo 模式自动通过；其他模式完成后确认。

### REVIEW（含正式复盘报告）

保存最终状态，生成**正式复盘报告**。复盘报告写入 `.harness/tasks/{slug}/review/review.md`。

**复盘报告模板**：

```markdown
# 复盘报告：{{任务名称}}

## 基本信息
- **任务 ID**: {{taskId}}
- **模式**: standard / quick / yolo
- **复杂度**: simple / medium / complex
- **开始时间**: {{createdAt}}
- **结束时间**: {{completedAt}}

## 完成情况

### MUST 条件覆盖率
| MUST 条件 | 状态 | 对应测试 |
|-----------|------|----------|
| {{条件}} | PASS/FAIL | T-{{prefix}}{{N}} |

### 测试执行结果
- 总测试数: {{total}}
- 通过: {{passed}}
- 失败: {{failed}}
- 跳过: {{skipped}}

## 偏差分析
| 编号 | 偏差描述 | 根因 | 处理方式 |
|------|----------|------|----------|
| DEV-001 | {{描述}} | {{根因}} | {{处理}} |

## 改进建议
1. {{建议 1}}
2. {{建议 2}}

## 经验沉淀
- {{可复用的经验/模式}}
```

```
任务记录已保存到: .harness/tasks/{task-slug}/
复盘报告: .harness/tasks/{task-slug}/review/review.md
```

## 恢复机制

检测到 `.harness/current.json` 且 status ≠ completed 时，展示断点摘要并询问恢复策略（continue / restart-stage / abort）。

## 存储结构

```
.harness/
├── current.json                    # 当前活跃任务指针
└── tasks/{slug}/
    ├── workflow.json               # 工作流状态（含 stageTimeline）
    ├── brainstorm/                 # BRAINSTORM 阶段产物（quick 模式跳过）
    │   ├── mindmap.md
    │   ├── options.md
    │   └── decision.md
    ├── harness/                    # HARNESS 阶段产物（必须存在）
    │   └── harness.md              # 验收标准
    ├── plan/
    │   └── PLAN.md                 # 执行计划（含 harness_ref）
    ├── execute/
    │   └── deviations.md           # 执行偏差记录
    └── review/
        └── review.md               # 复盘报告

tests/                              # 测试文件放在项目 tests/ 目录下
├── bdd/
│   ├── cases/{page}/               # BDD 步骤描述
│   │   └── T-{prefix}{N}.js
│   └── {page}/                     # BDD 测试脚本
│       └── T-{prefix}{N}.test.ts
├── integration/                    # 集成测试
└── unit/                           # 单元测试
```

## YOLO 模式语义澄清

> **关键区分**：yolo 跳过的是**门控确认**（用户审批），不是**阶段执行**。

| 行为 | yolo 是否执行 | 说明 |
|------|---------------|------|
| BRAINSTORM 分析 | 是 | 自动选择最佳方案 |
| HARNESS 分析 + 生成测试 | **是（强制）** | 自动选择框架 + 生成用例 |
| PLAN 生成 | 是 | 自动生成计划 |
| 门控确认 | 否 | 自动 approve |
| HARNESS 产出文件 | **是（强制）** | BDD case + 测试脚本必须生成 |

## 项目测试约定（HARNESS 阶段自动遵循）

以下约定在 HARNESS 阶段通过 task-harness 自动检测并遵循。如果项目缺少这些配置，HARNESS 阶段应主动创建。

### 必要的测试配置

| 配置项 | 位置 | 说明 |
|--------|------|------|
| `vitest.config.ts` | 项目根目录 | `globals: true`, `environment: 'jsdom'` |
| `@wangjs-jacky/tdd-kit` | `devDependencies` | 提供 `expectElement` / `expectElementAsync` |
| `@testing-library/react` | `devDependencies` | BDD 测试必需 |
| `CLAUDE.md` 测试约定 | 项目根目录 | 声明测试目录结构和编号规则 |

### 测试编号规则

根据项目页面自动分配前缀。扫描已有 `tests/bdd/cases/` 目录确定下一个编号。

| 页面 | 前缀 | 示例 |
|------|------|------|
| 根据项目实际页面确定 | 动态 | T-GH1, T-GH2（GitHub Hot 榜） |

## 推荐 Skill（非强制）

| Skill | 用途 | 何时有用 |
|-------|------|----------|
| task-memory | 对话监听与偏差记录 | 复杂任务需要跨会话记忆 |
| task-harness | 验收边界定义 + BDD 测试生成 | 需要严格的验收标准和自动化测试 |

不可用时静默降级，不阻塞流程。但如果 task-harness 不可用，HARNESS 阶段仍需手动产出 `harness.md` 和测试用例。

## References

详细参考文档位于 `references/` 目录：

| 文件 | 内容 |
|------|------|
| `references/tdd-protocol.md` | TDD 哲学、Verify Loop 流程图、失败分析模板 |
| `references/stage-transitions.md` | 阶段跳转规则、门控协议 |
| `references/storage-structure.md` | 目录结构、task-slug 规则、模板 |
| `references/examples.md` | 完整示例 |
