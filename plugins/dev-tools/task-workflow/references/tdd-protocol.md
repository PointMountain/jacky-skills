# TDD 验证协议

> 本文件包含 TDD 哲学、Verify Loop 流程、失败分析模板和最佳实践。

## TDD 核心理念：红灯-绿灯-重构

**测试先行原则**：
1. **红灯**：先写失败的测试（验证需求理解正确）
2. **绿灯**：写最小代码让测试通过（不过度设计）
3. **重构**：优化代码结构（保持测试通过）

**HARNESS 作为验证标准**：
- HARNESS 定义了"什么是对的"
- 测试用例来源于 HARNESS 的 MUST 条件
- 只有测试通过才算任务完成
- **PLAN 中每个任务通过 `harness_ref` 关联到具体的 BDD 测试**

---

## TDD 与 BDD 的关联

```
HARNESS (MUST 条件)
    ↓ 1:1 映射
BDD Case (步骤描述: Given/When/Then)
    ↓ 1:1 映射
测试脚本 (可执行 Vitest 代码)
    ↓ 被引用
PLAN 任务 (harness_ref 字段)
    ↓ 被验证
EXECUTE (红→绿循环)
```

**关键约定**：
- 每个 MUST 条件 → 至少一个 BDD case
- 每个 BDD case → 对应一个测试文件
- PLAN 中每个 task → `harness_ref` 引用对应的 BDD case 编号
- EXECUTE 中每个 task → 先运行对应的 BDD 测试确认红灯，再实现代码到绿灯

---

## Verify Loop 流程图

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    TDD-Driven Verify Loop 流程                             │
└───────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────┐
                          │ 读取 HARNESS     │
                          │ 提取 MUST 条件   │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ 读取 PLAN        │
                          │ 获取 harness_ref │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ 编写 BDD 测试    │
                          │ (基于 harness_ref│
                          │  关联的 case)    │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ 实现代码          │
                          └────────┬────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │ 运行 BDD 测试              │◄─────────────────┐
                    │ npx vitest run <test>     │                  │
                    └──────────┬───────────────┘                  │
                               │                                  │
                  ┌────────────┴────────────┐                    │
                  │                         │                    │
                  ▼                         ▼                    │
            ┌──────────┐             ┌──────────┐               │
            │ 全部通过  │             │ 有失败    │               │
            └────┬─────┘             └────┬─────┘               │
                 │                        │                      │
                 │                        ▼                      │
                 │                 ┌──────────────┐             │
                 │                 │ 重试次数 < 5? │             │
                 │                 └──────┬───────┘             │
                 │                        │                      │
                 │              ┌────────┴────────┐             │
                 │              │ YES             │ NO           │
                 │              ▼                 ▼             │
                 │      ┌──────────────┐   ┌──────────────┐     │
                 │      │ 分析失败原因  │   │ 暂停询问用户  │     │
                 │      └──────┬───────┘   └──────────────┘     │
                 │             │                                │
                 │             ▼                                │
                 │      ┌──────────────┐                        │
                 │      │ 修复代码      │                        │
                 │      └──────┬───────┘                        │
                 │             │                                │
                 │             └────────────────────────────────┘
                 │
                 ▼
          记录偏差 → 进入下一任务 / REVIEW
```

---

## TDD 执行流程

```
FOR each task in PLAN:

  1. 准备阶段
     - 读取 PLAN 中的 harness_ref
     - 确认对应的 BDD case 和测试文件已存在
     - 确认测试框架配置（vitest.config.ts）

  2. 红灯阶段（Red）
     - 基于 BDD case 编写测试用例（覆盖所有 MUST 条件）
     - 运行测试 -> 确认失败
     - 记录期望行为

  3. 绿灯阶段（Green）
     - 实现最小代码（仅满足测试）
     - 不过度设计
     - 不过早优化

  4. 循环验证（Loop）
     retry_count = 0
     WHILE (测试未通过 AND retry_count < 5):
        a. 运行测试: npx vitest run <对应测试文件>
        b. IF 失败:
           - 分析失败原因（见下方模板）
           - 修复代码（最小修改）
           - 记录偏差到 execute/deviations.md
           - retry_count++
        c. IF 通过:
           - BREAK

  5. 异常处理
     IF retry_count >= 5:
        - 暂停执行
        - 使用 AskUserQuestion 询问用户：
          a. 重新设计 HARNESS
          b. 重新制定 PLAN
          c. 手动介入修复
        - 等待用户决策

  6. 完成标记
     - Task 完成
     - 更新 workflow.json 中对应的 harnessTests 状态
     - 进入下一个 task
```

---

## 测试运行命令

```bash
# 运行单个 BDD 测试
npx vitest run tests/bdd/{page}/T-{prefix}{N}.test.ts

# 运行页面下所有 BDD 测试
npx vitest run tests/bdd/{page}/

# 运行所有测试
npx vitest run

# 带覆盖率
npx vitest run --coverage
```

---

## 失败分析模板

```markdown
## 测试失败分析

### 基本信息
- **Task ID**: T2
- **BDD Case**: T-GH3（{{case 标题}}）
- **测试文件**: tests/bdd/hot/T-GH3.test.ts
- **重试次数**: 2/5
- **失败时间**: {{时间戳}}

### 失败的测试用例
```bash
# 运行命令
npx vitest run tests/bdd/hot/T-GH3.test.ts

# 失败输出
FAIL: should increment count when + clicked
  Expected: count = 1
  Received: count = 0
```

### 根因分析
**直接原因**：
- 事件监听器未正确绑定（用例 1）

**根本原因**：
- HARNESS 明确要求"最大值 100"，但实现时遗漏

### 修复方案
```diff
// src/counter.js
- document.getElementById('increment-btn')
+ document.getElementById('increment')

+ if (this.count < 100) {
+   this.count++;
+ }
```

### HARNESS 关联
- [ ] MUST: 点击 + 按钮，计数增加 -> 失败
- [ ] MUST: 最大值不超过 100 -> 失败
- [ ] SHOULD: 显示当前计数 -> 未测试

### 偏差记录
- 记录到 execute/deviations.md (DEV-{{N}})

### 重测计划
1. 修复代码（见上方 diff）
2. 运行测试: `npx vitest run tests/bdd/hot/T-GH3.test.ts`
3. 预期结果：所有 MUST 条件通过
```

---

## TDD 最佳实践

### 1. 测试先行（Test First）
```
错误：先写代码，后补测试
正确：先写测试，再写代码
```

### 2. 最小实现（Minimal Implementation）
```
错误：一次性实现完整功能 + 额外特性
正确：只写让测试通过的最少代码
```

### 3. 单一职责（Single Responsibility）
```
错误：一个测试用例验证多个条件
正确：一个测试用例只验证一个 HARNESS MUST 条件
```

### 4. 快速反馈（Fast Feedback）
```
错误：写完所有代码才运行测试
正确：每完成一个功能点就运行测试
```

### 5. 重构时机（Refactoring Timing）
```
错误：测试失败时重构
正确：测试通过后才重构（保持绿灯）
```

### HARNESS 映射规则

| HARNESS 条件类型 | 测试策略 |
|-----------------|---------|
| MUST 条件 | 必须有对应 BDD case + 测试脚本，失败则任务失败 |
| SHOULD 条件 | 建议有测试用例，失败可接受 |
| EDGE 条件 | 边缘场景测试（空数据、异常输入等），提升健壮性 |

### 测试类型选择

| 任务类型 | 测试位置 | 验证方式 |
|----------|----------|----------|
| UI 组件/页面交互 | `tests/bdd/` | render + findByTestId + DOM 结构验证 |
| 数据一致性/配置对齐 | `tests/integration/` | 直接断言对比 |
| 纯函数/工具 | `tests/unit/` | 输入输出断言 |

---

## Prompt 链记录

记录每次用户输入，形成 Prompt 思维链：

```
用户输入 1 (初始 Prompt)
    | AI 执行
用户输入 2 (修正/补充)  <- 记录：为什么需要修正？
    | AI 执行
用户输入 3 (Bug 修复)   <- 记录：原始设计遗漏了什么？
    | AI 执行
   完成
```

**记录时机**：
| 触发条件 | 记录内容 |
|----------|----------|
| 用户给出修正指令 | 原始 Prompt 缺失了什么信息 |
| 代码执行失败 | 用户的补充说明 |
| 用户补充需求 | 是范围蔓延还是原始需求不完整 |
| 里程碑完成 | 保存当前进展 |
| 测试失败 | 记录失败原因和修复策略到 deviations.md |
