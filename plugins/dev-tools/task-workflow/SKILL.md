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
| `/task-workflow yolo <描述>` | 全自动，无门控确认，失败中止 |
| `/task-workflow status` | 查看当前状态 |
| `/task-workflow end` | 结束工作流，生成复盘 |

## 复杂度评估（INIT 阶段自动判定）

| 复杂度 | 条件 | 推荐模式 | 门控策略 |
|--------|------|----------|----------|
| 简单 | 影响文件 ≤ 3，无跨模块依赖 | quick | 自动通过 BRAINSTORM/HARNESS，仅 PLAN 确认 |
| 中等 | 影响文件 4-8，有模块间依赖 | standard | HARNESS + PLAN 需确认 |
| 复杂 | 影响文件 > 8，跨系统/架构级变更 | standard | BRAINSTORM + HARNESS + PLAN 需确认 |

> 用户可覆盖推荐模式。yolo 模式跳过所有门控。

## 工作流阶段

```
INIT → BRAINSTORM → HARNESS → PLAN → EXECUTE → REVIEW
        (quick跳过)                      (含验证)
```

### INIT

1. 生成 task-slug，创建 `.harness/tasks/{slug}/` 目录
2. 检索已有实现（Grep/Glob 扫描相关代码）
3. 评估任务复杂度，向用户展示推荐模式
4. 如 task-memory 可用，启动监听记录初始意图
5. 写入 `workflow.json`

**自适应门控**：简单任务自动进入 PLAN；中等/复杂任务进入 BRAINSTORM（或 HARNESS，如果 quick 模式）。

### BRAINSTORM（quick 模式跳过）

调用 superpowers:brainstorming 进行创意发散，生成方案对比，记录最终决策。

**门控**：中等任务自动通过；复杂任务需用户确认。

### HARNESS

基于 brainstorm 结果（或 INIT 检索结果，如果是 quick 模式），定义验收边界和测试用例。

> 如果 task-harness 可用，调用 `/task-harness` 辅助生成。Harness 模板见 `references/storage-structure.md`。

**门控**：中等/复杂任务需用户确认验收标准。

### PLAN

基于 HARNESS 验收标准 + INIT 检索的已有实现，生成 PLAN.md。必须包含：

- **受影响文件清单**（create/modify/delete）
- **任务依赖关系**
- **风险与回归点**
- **失败模式**（每个关键任务的回退方案）

**门控**：所有复杂度都需要用户确认执行计划。

### EXECUTE（含验证）

逐个执行 PLAN.md 中的任务，严格按 **TDD 红→绿** 顺序：

1. **Red**：写失败测试，运行确认失败
2. **Green**：写最小实现代码，测试通过
3. 记录执行偏差（如有 task-memory）

验证失败时循环修复（最多 5 次），超过上限暂停询问用户。

> 详细 TDD 验证协议见 `references/tdd-protocol.md`

**门控**：yolo 模式自动通过；其他模式完成后确认。

### REVIEW

保存最终状态，生成复盘报告。自动完成，无需确认。

```
任务记录已保存到: .harness/tasks/{task-slug}/
```

## 恢复机制

检测到 `.harness/current.json` 且 status ≠ completed 时，展示断点摘要并询问恢复策略（continue / restart-stage / abort）。

## 存储结构

```
.harness/
├── current.json                    # 当前活跃任务指针
└── tasks/{slug}/
    ├── workflow.json               # 工作流状态
    ├── PLAN.md                     # 执行计划
    └── *.test.*                    # 测试文件
```

## 推荐 Skill（非强制）

| Skill | 用途 | 何时有用 |
|-------|------|----------|
| task-memory | 对话监听与偏差记录 | 复杂任务需要跨会话记忆 |
| task-harness | 验收边界定义 | 需要严格的验收标准 |

不可用时静默降级，不阻塞流程。

## References

详细参考文档位于 `references/` 目录：

| 文件 | 内容 |
|------|------|
| `references/tdd-protocol.md` | TDD 哲学、Verify Loop 流程图、失败分析模板 |
| `references/stage-transitions.md` | 阶段跳转规则、门控协议 |
| `references/storage-structure.md` | 目录结构、task-slug 规则、模板 |
| `references/examples.md` | 完整示例 |
