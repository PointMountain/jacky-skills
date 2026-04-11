# 阶段跳转规则与门控协议

> 本文件包含阶段门控协议、跳转规则、模式说明和门控格式模板。

## 阶段门控协议

**核心理念**：每个阶段完成后，必须用户明确 approve 才能进入下一阶段。

### 门控机制流程

```
    ┌──────────────┐
    │  阶段完成     │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ 展示产物      │
    │ + 总结       │
    └──────┬───────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │ AskUserQuestion 门控确认          │
    │ 问题: 是否 approve?              │
    │ 选项: approve / 其他             │
    └────────────┬───────────────────┘
                   │
         ┌─────────┴─────────┐
         │                     │
         ▼                     ▼
    ┌──────────┐         ┌──────────┐
    │ approve  │         │ 其他选项  │
    └────┬─────┘         └────┬─────┘
         │                     │
         │                     ▼
         │              ┌──────────────┐
         │              │ 调整/补充    │
         │              └──────┬───────┘
         │                     │
         │                     ▼
         │              ┌──────────────┐
         │              │ 重新询问     │
         │              └──────────────┘
         │
         ▼
    进入下一阶段
```

---

## 各阶段门控要求

| 阶段 | 门控类型 | 产物要求 | resume-signal |
|------|----------|----------|---------------|
| INIT | - | workflow.json 已创建 | 自动进入 |
| BRAINSTORM | `checkpoint:decision` | decision.md 已创建 | `approve \| continue \| adjust` |
| HARNESS | `checkpoint:decision` | harness.md 已创建 + BDD case + 测试脚本已生成 | `approve \| adjust \| add` |
| PLAN | `checkpoint:decision` | PLAN.md 已创建（含 harness_ref） | `approve \| adjust \| add` |
| EXECUTE | `checkpoint:decision` | 所有任务代码已编写 + 偏差已记录 | `approve \| adjust \| add` |
| REVIEW | - | review.md 复盘报告已生成 | 自动完成 |

**HARNESS 阶段产出验证清单**：
- [ ] `harness.md` 包含 MUST/SHOULD 条件
- [ ] 每个 MUST 条件有对应的 BDD case 文件
- [ ] 每个 BDD case 有对应的测试脚本
- [ ] 测试脚本可运行（红灯状态）
- [ ] 如果项目缺少 `@wangjs-jacky/tdd-kit`，已在 HARNESS 阶段安装

---

## 标准门控格式

```xml
<stage_gate type="checkpoint:decision" gate="blocking">

阶段门控：{当前阶段} -> {下一阶段}

<decision>{需要确认的问题}</decision>

<context>{为什么需要确认}</context>

<options>
<option id="approve">
  <name>approve - {描述}</name>
  <pros>{优点}</pros>
  <cons>{权衡}</cons>
</option>
<option id="alt">
  <name>{其他选项}</name>
  <pros>{优点}</pros>
  <cons>{权衡}</cons>
</option>
</options>

<resume-signal>Type: approve | alt</resume-signal>

</stage_gate>
```

---

## 用户响应处理

| 响应类型 | 处理方式 |
|----------|----------|
| `approve` / `yes` / `y` / `ok` | 进入下一阶段 |
| 空响应（直接回车） | 视为批准 |
| 其他内容 | 按选项 ID 匹配，或视为问题描述 |

---

## 阶段跳转规则

| 从 | 到 | 允许 | 条件 | 门控确认 |
|----|----|----|------|----------|
| INIT | BRAINSTORM | 是 | workflow.json 已创建 | 不需要 |
| INIT | HARNESS | 是 | quick 模式 + workflow.json 已创建 | 不需要 |
| BRAINSTORM | HARNESS | 是 | decision.md 已创建 | **必须** |
| HARNESS | PLAN | 是 | harness.md + BDD case + 测试脚本已创建 | **必须** |
| PLAN | EXECUTE | 是 | PLAN.md 已创建（含 harness_ref） | **必须** |
| EXECUTE | REVIEW | 是 | 所有任务完成 + 偏差已记录 | 不需要（自动进入） |
| 任意 | 之前的阶段 | 是 | 支持回退修改 | 不需要 |

---

## 使用 goto 命令

```
/task-workflow goto HARNESS    # 回到验收定义阶段
/task-workflow goto EXECUTE    # 直接进入执行
```

**注意**：跳过阶段可能导致产物缺失，AI 会提示需要补充的内容。

---

## Quick 模式

`/task-workflow quick <任务描述>` 跳过 BRAINSTORM 阶段：

```
INIT -> HARNESS -> PLAN -> EXECUTE -> REVIEW
        ^
     BRAINSTORM 跳过，HARNESS 必须执行
```

**适用场景**：
- 任务目标非常明确
- 已经有清晰的设计方案
- 需要快速启动执行

**不适用场景**：
- 需求模糊，需要探索
- 复杂任务，有多种方案
- 第一次处理此类任务

---

## YOLO 模式

`/task-workflow yolo <任务描述>` **全自动执行（无需门控确认），但所有阶段必须执行**

```
INIT -> BRAINSTORM -> HARNESS -> PLAN -> EXECUTE -> REVIEW
                          ↑
                     必须执行（仅跳过确认）
```

### YOLO 模式语义澄清

> **核心区分**：yolo 跳过的是"门控确认"（用户审批），不是"阶段执行"。

| 阶段 | 是否执行 | 是否需确认 | 说明 |
|------|----------|------------|------|
| INIT | 是 | 否 | 正常执行 |
| BRAINSTORM | 是 | 否 | AI 自动选择最佳方案 |
| HARNESS | **是（强制）** | 否 | AI 自动生成 BDD case + 测试脚本 |
| PLAN | 是 | 否 | AI 自动生成计划（含 harness_ref） |
| EXECUTE | 是 | 否 | AI 自动实现 + 自动修复循环 |
| REVIEW | 是 | 否 | AI 自动生成复盘报告 |

### AI 自动决策

| 阶段 | AI 决策内容 |
|------|------------|
| BRAINSTORM | 自动选择最佳方案 |
| HARNESS | 自动检测框架 + 生成 BDD case + 测试脚本 |
| PLAN | 自动生成执行计划（每个 task 含 harness_ref） |
| EXECUTE | 自动实现 + 记录偏差 + 自动修复循环 |

### 模式对比

| 模式 | BRAINSTORM | HARNESS 执行 | 门控确认 | 适用场景 |
|------|-----------|-------------|----------|----------|
| 标准 | 执行 | 执行 | 每阶段确认 | 复杂任务、首次任务 |
| quick | **跳过** | 执行 | HARNESS + PLAN 确认 | 目标明确 |
| yolo | 执行 | **执行（强制）** | 全部自动 | 简单任务、演示 |

**YOLO 模式 auto_advance 行为**：
- `checkpoint:decision` -> 自动选择第一个选项
- 产物文件照常生成（harness.md、BDD case、测试脚本、deviations.md、review.md）

---

## 恢复机制

当检测到 `.harness/current.json` 且 `status ≠ completed` 时，按以下流程恢复：

### 恢复流程

```
1. 读取 current.json → 获取 activeTaskSlug + currentStage
2. IF currentStage === "EXECUTE":
     a. 读取 execute/progress.md → 获取已完成 task 列表
     b. 读取 workflow.json 的 executeProgress → 获取 currentTaskId
     c. 读取 PLAN.md → 获取当前 task 的详细信息
     d. 展示断点摘要：
        - 已完成：T1(项目初始化) T2(数据层) T3(搜索功能)
        - 当前：T4(标签筛选)
        - 剩余：T5 T6 T7 T8
     e. 询问用户恢复策略：
        - continue: 从 T4 继续
        - ralph: 切换到 ralph-loop 模式从 T4 继续
        - restart-stage: 重新执行整个 EXECUTE 阶段
        - abort: 终止工作流
3. ELSE:
     正常阶段恢复（展示断点摘要 + 询问策略）
```

### 断点摘要格式

```
## 工作流恢复：{任务名称}

**当前阶段**: EXECUTE (T4/8)
**已耗时**: {{从 createdAt 到现在}}

### 执行进度
- [x] T1: 项目初始化 ✓
- [x] T2: 数据层 ✓
- [x] T3: 搜索功能 ✓
- [ ] T4: 标签筛选 ← 从这里继续
- [ ] T5: 排序功能
- [ ] T6: 详情弹窗
- [ ] T7: 主题切换
- [ ] T8: 错误处理

### 偏差记录
- DEV-001: {{偏差描述}} (已处理)

恢复策略：continue / ralph / restart-stage / abort
```

### Context 接近极限时的处理

在 EXECUTE 阶段开头，如果检测到：
- 任务数 > 5
- 或用户之前已恢复过一次

则主动提示：

```
⚠️ EXECUTE 阶段任务较多（{N} 个），context 可能在执行中途耗尽。

建议：
1. 回复 "ralph" → 启用 ralph-loop 循环模式（每轮处理一个 task，自动续跑）
2. 继续当前会话 → 每个 task 完成后会自动 checkpoint，context 耗尽时可恢复
```

---

| 回退到 | 保留产物 | 需重做产物 |
|--------|----------|------------|
| BRAINSTORM | workflow.json | harness/, plan/, execute/, review/ |
| HARNESS | workflow.json, brainstorm/ | plan/, execute/, review/ |
| PLAN | workflow.json, brainstorm/, harness/ | execute/, review/ |
| EXECUTE | 全部 | review/ |
