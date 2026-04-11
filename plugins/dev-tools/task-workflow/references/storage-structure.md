# 存储结构与工具集成

> 本文件包含目录结构、task-slug 规则、工具集成说明、最佳实践和反模式。

## 目录结构

```
.harness/
├── current.json                         # 活跃任务指针（含 executeCheckpoint）
└── tasks/
    └── {task-slug}/                     # 每个任务独立目录
        ├── workflow.json                # 工作流状态（含 stageTimeline + executeProgress）
        ├── brainstorm/                  # BRAINSTORM 阶段产物（quick 模式跳过）
        │   ├── mindmap.md               # 设计脑图
        │   ├── options.md               # 方案对比
        │   └── decision.md              # 最终决策
        ├── harness/                     # HARNESS 阶段产物（必须存在）
        │   └── harness.md               # 验收标准
        ├── plan/                        # PLAN 阶段产物
        │   └── PLAN.md                  # 任务列表（含 harness_ref）
        ├── execute/                     # EXECUTE 阶段产物
        │   ├── progress.md              # 逐任务进度追踪（每个 task 完成后更新）
        │   └── deviations.md            # 执行偏差记录
        └── review/                      # REVIEW 阶段产物
            └── review.md                # 复盘报告

tests/                                   # 测试文件放在项目 tests/ 目录下
├── bdd/
│   ├── cases/{page}/                    # BDD 步骤描述
│   │   └── T-{prefix}{N}.js
│   └── {page}/                          # BDD 测试脚本
│       └── T-{prefix}{N}.test.ts
├── integration/                         # 集成测试
└── unit/                                # 单元测试
```

### workflow.json 模板

```json
{
  "taskId": "wf-2026-03-22-001",
  "name": "<任务名称>",
  "taskSlug": "<task-slug>",
  "status": "in_progress",
  "currentStage": "INIT",
  "complexity": {
    "level": "medium",
    "affectedFileCount": 6,
    "recommendation": "standard"
  },
  "createdAt": "2026-03-22T10:00:00Z",
  "updatedAt": "2026-03-22T10:00:00Z",
  "stageTimeline": {
    "INIT": {
      "enteredAt": "2026-03-22T10:00:00Z",
      "exitedAt": null
    }
  },
  "deviations": 0,
  "harnessTests": [
    {
      "testCaseId": "T-GH1",
      "mustCondition": "{{对应的 MUST 条件}}",
      "testFile": "tests/bdd/hot/T-GH1.test.ts",
      "caseFile": "tests/bdd/cases/hot/T-GH1.js"
    }
  ],
  "executeProgress": {
    "totalTasks": 0,
    "completedTasks": 0,
    "currentTaskId": null,
    "taskStatus": {}
  },
  "dependencies": ["task-memory", "task-harness"]
}
```

### current.json 模板

```json
{
  "activeTaskSlug": "<task-slug>",
  "currentStage": "INIT",
  "executeCheckpoint": {
    "currentTaskId": null,
    "completedTaskIds": [],
    "lastUpdatedAt": null
  },
  "updatedAt": "2026-03-22T10:00:00Z"
}
```

> `executeCheckpoint` 在 EXECUTE 阶段每个 task 完成后更新，用于断点恢复。

### progress.md 模板

EXECUTE 阶段自动生成，每完成一个 task 追加更新：

```markdown
# Execute Progress

- [x] T1: 项目初始化 (completed 2026-04-11T10:00:00Z)
- [x] T2: 数据层 (completed 2026-04-11T10:10:00Z)
- [ ] T3: 搜索功能 (in_progress)
- [ ] T4: 标签筛选
```

> **恢复时**：读取 progress.md 确认哪些 task 已完成，从下一个未完成的 task 继续。

---

## task-slug 规则

`task-slug` 用于目录命名，规则如下：
- 全部转小写
- 非字母数字字符转为 `-`
- 合并连续 `-`
- 去除首尾 `-`
- 若结果为空，回退到 `task-<timestamp>`

生成命令：
```bash
TASK_SLUG="$(printf '%s' "$TASK_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/-\{2,\}/-/g; s/^-//; s/-$//')"
```

---

## 工具集成

### 与 superpowers 的集成

| superpowers skill | 阶段 | 用途 |
|-------------------|------|------|
| `brainstorming` | BRAINSTORM | 创意发散 |
| `writing-plans` | PLAN | 编写执行计划 |
| `executing-plans` | EXECUTE | 执行计划 |

### 与 task-memory 的集成

| task-memory 命令 | 阶段 | 用途 |
|------------------|------|------|
| `start` | INIT | 记录初始意图 |
| `record` | EXECUTE | 记录偏差 |
| `end` | REVIEW | 生成复盘 |

### 与 task-harness 的集成

| task-harness 命令 | 阶段 | 用途 |
|-------------------|------|------|
| `/task-harness` | HARNESS | 定义验收边界 + 生成 BDD 测试 |

**集成流程**：

```
1. task-workflow HARNESS 阶段 → 调用 /task-harness
2. task-harness → 检测项目测试结构
3. task-harness → 生成 BDD case + 测试脚本（写入 tests/）
4. task-harness → 生成验收标准（写入 .harness/harness.md）
5. task-workflow → 读取测试用例列表，写入 workflow.json 的 harnessTests
6. PLAN 阶段 → 每个 task 关联 harness_ref
7. EXECUTE 阶段 → 按 harness_ref 运行 TDD 红绿循环
```

---

## 最佳实践

1. **不要跳过 HARNESS** - 没有明确边界就无法验证完成，yolo 模式也必须执行
2. **PLAN 必须关联 HARNESS** - 每个任务通过 harness_ref 追溯到 MUST 条件
3. **及时记录偏差** - 发现偏差立即记录到 `execute/deviations.md`
4. **认真做 REVIEW** - 生成正式复盘报告到 `review/review.md`
5. **保存 workflow.json** - 便于中断后恢复，stageTimeline 提供完整阶段追溯
6. **测试放在 tests/ 目录** - 测试文件放在项目的 tests/ 目录下，不是 .harness/

---

## 反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 跳过 HARNESS | 没有验收标准，无法验证 | HARNESS 必须执行，yolo 仅跳过确认 |
| 模糊的 Harness | 无法验证完成 | 使用可量化的标准 |
| 测试放在 src/ 下 | Vitest 不认 tests/ 目录，task-harness 管理不到 | 测试放在 tests/bdd/ 下 |
| 不记录偏差 | 无法复盘改进 | 发现偏差立即记录到 deviations.md |
| PLAN 缺少 harness_ref | 任务与验收标准断裂 | 每个任务关联 BDD 编号和测试文件 |
| 不做 REVIEW | 无法沉淀经验 | 生成正式复盘报告 |
| 缺少 tdd-kit 依赖 | 无法使用 expectElement 断言 | HARNESS 阶段主动安装 |

---

## Harness 模板

```markdown
# Harness: {{任务名称}}

## 验收标准

### 必须 (MUST)
- [ ] {{可验证条件 1}}
- [ ] {{可验证条件 2}}

### 应该 (SHOULD)
- [ ] {{可验证条件 3}}

### 边缘场景 (EDGE)
- [ ] {{空数据/异常输入等边界条件}}

## BDD 测试映射

| MUST 条件 | BDD Case | 测试文件 |
|-----------|----------|----------|
| {{条件 1}} | T-{{prefix}}{{N}} | tests/bdd/{{page}}/T-{{prefix}}{{N}}.test.ts |
| {{条件 2}} | T-{{prefix}}{{N+1}} | tests/bdd/{{page}}/T-{{prefix}}{{N+1}}.test.ts |

## 失败模式

| MUST 条件 | 失败场景 | 检测方式 | 恢复策略 |
|-----------|----------|----------|----------|
| {{条件 1}} | {{什么情况下失败}} | {{如何发现}} | {{失败后怎么处理}} |
| {{条件 2}} | {{什么情况下失败}} | {{如何发现}} | {{失败后怎么处理}} |

## 验证命令
```bash
npx vitest run tests/bdd/{{page}}/
```
```

### Harness 反模式示例

```
错误: "界面要美观"        -> 无法验证
正确: "Lighthouse 分数 >= 90" -> 可验证

错误: "性能要好"          -> 模糊
正确: "首屏加载 < 2s"     -> 可量化

错误: 测试放在 src/       -> Vitest 配置不覆盖
正确: 测试放在 tests/     -> 遵循项目测试目录约定
```

---

## PLAN 模板

```xml
<plan>
<blueprint>
## 受影响文件清单
| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| {{path}} | create/modify/delete | {{说明}} |

## 代码依赖关系
- T2 依赖 T1（{{原因}}）
- T3 依赖 T1（{{原因}}）

## 风险与回归点
- 修改 {{文件/模块}} 可能影响 {{现有功能}}
- 需要回归验证：{{场景列表}}

## 失败模式
- T1 失败 → 回退方案：{{具体回退策略}}
- T3 失败 → 回退方案：{{具体回退策略}}
</blueprint>

<task type="auto" id="T1">
  <name>{{任务名称}}</name>
  <files>{{涉及的文件}}</files>
  <action>{{具体行动}}</action>
  <verify>{{验证命令}}</verify>
  <harness_ref>
    - MUST: {{对应的 MUST 条件}}
    - BDD: T-{{prefix}}{{N}}（{{BDD case 标题}}）
    - Test: tests/bdd/{{page}}/T-{{prefix}}{{N}}.test.ts
  </harness_ref>
</task>

<task type="auto" id="T2">
  <name>{{任务名称}}</name>
  <files>{{涉及的文件}}</files>
  <action>{{具体行动}}</action>
  <verify>{{验证命令}}</verify>
  <harness_ref>
    - MUST: {{对应的 MUST 条件}}
    - BDD: T-{{prefix}}{{N+1}}
    - Test: tests/bdd/{{page}}/T-{{prefix}}{{N+1}}.test.ts
  </harness_ref>
</task>

<task type="checkpoint" id="C1" gate="blocking">
  <what-built>{{已构建的内容}}</what-built>
  <how-to-verify>{{验证方式}}</how-to-verify>
  <resume-signal>{{继续信号}}</resume-signal>
</task>
</plan>
```

---

## 偏差记录模板

偏差记录写入 `.harness/tasks/{slug}/execute/deviations.md`。

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
- **harness_ref**: 对应的 MUST 条件是否受影响
```

---

## 复盘报告模板

复盘报告写入 `.harness/tasks/{slug}/review/review.md`。

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
| MUST 条件 | 状态 | 对应 BDD | 对应测试 |
|-----------|------|----------|----------|
| {{条件}} | PASS/FAIL | T-{{prefix}}{{N}} | tests/bdd/... |

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
