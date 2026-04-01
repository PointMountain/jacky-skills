# 完整示例与阶段详解

> 本文件包含完整的任务工作流示例和每个阶段的详细说明。

## 完整示例（yolo 模式 - GitHub Hot 榜）

```
用户: /task-workflow yolo 开发 GitHub 热榜页面

AI: 启动任务工作流（yolo 模式）

## INIT
- 任务 ID: wf-2026-04-01-001
- 目录: .harness/tasks/github-hot-repos/ 已创建
- 复杂度评估: complex（影响 14+ 文件）
- 推荐模式: standard → 用户选择 yolo

## BRAINSTORM（AI 自动决策）
扫描已有实现:
- 数据源: wangjs-jacky/github-hot-repos (trending.json, 545 条)
- 设计稿: github-hot-repos.pen (4 个 frame)

方案选择: Vite + React + TypeScript 单页应用

## HARNESS（AI 自动生成 BDD 测试）
检测项目测试结构:
- vitest.config.ts: globals=true, jsdom
- @wangjs-jacky/tdd-kit: 缺失 → 安装
- 测试目录: 不存在 → 创建 tests/bdd/ 结构

生成 BDD case + 测试脚本:
- T-GH1: 仓库列表渲染 → tests/bdd/hot/T-GH1.test.ts
- T-GH2: 搜索筛选功能 → tests/bdd/hot/T-GH2.test.ts
- T-GH3: 语言标签筛选 → tests/bdd/hot/T-GH3.test.ts
- T-GH4: 排序切换 → tests/bdd/hot/T-GH4.test.ts
- T-GH5: 详情弹窗 → tests/bdd/hot/T-GH5.test.ts
- T-GH6: 主题切换 → tests/bdd/hot/T-GH6.test.ts
- T-GH7: 空数据/错误状态 → tests/bdd/hot/T-GH7.test.ts

产物:
- .harness/tasks/github-hot-repos/harness/harness.md
- tests/bdd/cases/hot/T-GH1.js ~ T-GH7.js
- tests/bdd/hot/T-GH1.test.ts ~ T-GH7.test.ts

## PLAN（AI 自动生成）
生成 PLAN.md（每个任务包含 harness_ref）:
- T1: 项目初始化 (harness_ref: 基础设施)
- T2: 数据层 (harness_ref: T-GH1)
- T3: 搜索功能 (harness_ref: T-GH2)
- T4: 标签筛选 (harness_ref: T-GH3)
- T5: 排序功能 (harness_ref: T-GH4)
- T6: 详情弹窗 (harness_ref: T-GH5)
- T7: 主题切换 (harness_ref: T-GH6)
- T8: 错误处理 (harness_ref: T-GH7)

## EXECUTE（TDD 红绿循环）
T1: 项目初始化 → 完成
T2: 数据层 → Red(T-GH1 失败) → Green(实现 types.ts + useRepos.ts) → 通过
T3: 搜索功能 → Red(T-GH2 失败) → Green(实现搜索逻辑) → 通过
...
偏差记录: 写入 execute/deviations.md

## REVIEW（自动复盘）
生成复盘报告: review/review.md
- MUST 条件覆盖率: 7/7 PASS
- 偏差数: 0
- 改进建议: 无

最终产物:
.harness/tasks/github-hot-repos/
├── workflow.json
├── harness/harness.md
├── plan/PLAN.md
├── execute/deviations.md
└── review/review.md

tests/bdd/
├── cases/hot/T-GH1.js ~ T-GH7.js
└── hot/T-GH1.test.ts ~ T-GH7.test.ts
```

---

## 阶段详解

### INIT 阶段

**检查清单**：
- [ ] 生成 `task-slug`
- [ ] 创建 `.harness/tasks/{task-slug}/` 目录
- [ ] 生成 `workflow.json`（含 stageTimeline）
- [ ] 生成 `current.json`
- [ ] 评估复杂度

**workflow.json 模板**：

```json
{
  "taskId": "wf-2026-04-01-001",
  "name": "<任务名称>",
  "taskSlug": "<任务名称规范化后的slug>",
  "status": "in_progress",
  "currentStage": "INIT",
  "complexity": {
    "level": "medium",
    "affectedFileCount": 6,
    "recommendation": "standard"
  },
  "createdAt": "2026-04-01T10:00:00Z",
  "updatedAt": "2026-04-01T10:00:00Z",
  "stageTimeline": {
    "INIT": {
      "enteredAt": "2026-04-01T10:00:00Z",
      "exitedAt": null
    }
  },
  "deviations": 0,
  "harnessTests": [],
  "dependencies": ["task-memory", "task-harness"]
}
```

**目录创建命令**：
```bash
mkdir -p .harness/tasks/{task-slug}/{brainstorm,harness,plan,execute,review}
```

---

### BRAINSTORM 阶段

**引导问题**：

```
1. 这个任务要解决什么问题？
2. 有哪些可能的实现方式？
3. 每种方式的优缺点是什么？
4. 有什么技术限制或约束？
5. 预期的交付物是什么？
```

**产物模板**：

```markdown
# 设计脑图：<任务名>

## 核心问题
<要解决的问题>

## 方案列表

### 方案 A: <名称>
- 描述: <简述>
- 优点: <列出>
- 缺点: <列出>
- 复杂度: 低/中/高

### 方案 B: <名称>
...

## 最终选择
选择方案 X，理由：<说明>
```

---

### HARNESS 阶段

**产出验证清单**：
- [ ] `harness.md` 已创建（包含 MUST/SHOULD/EDGE 条件）
- [ ] BDD case 文件已创建（每个 MUST 至少一个）
- [ ] 测试脚本已创建（可运行，红灯状态）
- [ ] `@wangjs-jacky/tdd-kit` 已安装（如缺失）
- [ ] `vitest.config.ts` 已配置（如缺失）
- [ ] `workflow.json` 的 `harnessTests` 已更新

**验收标准分类**：

| 级别 | 含义 | 验证方式 |
|------|------|----------|
| MUST | 必须满足 | BDD 自动化测试 |
| SHOULD | 强烈建议 | 手动验证 |
| EDGE | 边缘场景 | BDD 或手动验证 |

**任务类型参考**：UI 组件 / 数据一致性 / 纯函数 / API / 配置

---

### PLAN 阶段

**任务拆分原则**：
1. **原子性** - 每个任务可独立完成
2. **可验证** - 完成后能判断是否成功
3. **粒度适中** - 不太大也不太小
4. **依赖明确** - 前后关系清晰
5. **harness_ref 完整** - 每个任务关联到 MUST 条件和 BDD case

**成功标准**：
- 所有 MUST 条件都有对应任务
- 每个任务都有 harness_ref
- 每个任务都有 verify 定义
- 任务顺序符合依赖关系

---

### EXECUTE 阶段

**TDD 红绿循环**：

```
FOR each task in PLAN:
  1. 读取 task 的 harness_ref
  2. Red: 确认对应的 BDD 测试存在且可运行（预期失败）
  3. Green: 实现最小代码使测试通过
  4. Loop: 运行测试 → 失败则修复（最多 5 次）
  5. 记录偏差到 execute/deviations.md（如有）
```

**偏差记录触发词**：

```
- "发现..."
- "不对..."
- "问题是..."
- "应该..."
- "需要修改..."
- "忘记..."
- "漏了..."
```

---

### REVIEW 阶段

**复盘问题**：

```
1. 哪些地方与预期不同？
2. 为什么会出现这些偏差？
3. 如何避免类似问题？
4. Harness 定义是否完整？
5. 下次可以改进什么？
6. MUST 条件覆盖率是多少？
```

**输出文件**：

```
.harness/tasks/{task-slug}/
├── workflow.json               # 完整工作流状态
├── brainstorm/                 # BRAINSTORM 产物
│   ├── mindmap.md
│   ├── options.md
│   └── decision.md
├── harness/
│   └── harness.md              # 验收标准
├── plan/
│   └── PLAN.md                 # 执行计划
├── execute/
│   └── deviations.md           # 偏差记录
└── review/
    └── review.md               # 复盘报告
```

---

## BDD Case 文件示例

### T-GH1.js（仓库列表渲染）

```javascript
// tests/bdd/cases/hot/T-GH1.js
export default {
  testCaseId: 'T-GH1',
  page: 'HotList',
  title: '仓库列表渲染 - 加载并展示热门仓库',
  link: '/',
  tags: ['待实现'],
  path: [
    'HotList 页面',
    '仓库列表',
  ],
  steps: [
    {
      stepId: 1,
      description: '页面加载完成',
      expectation: '显示头部区域（Logo + 搜索框 + 统计信息）',
    },
    {
      stepId: 2,
      description: '仓库数据加载成功',
      expectation: '展示 3 列卡片网格，每个卡片包含仓库名、描述、星标数等',
    },
    {
      stepId: 3,
      description: '数据加载失败',
      expectation: '显示错误提示信息',
    },
    {
      stepId: 4,
      description: '空数据状态',
      expectation: '显示空状态提示',
    },
  ],
}
```

### T-GH1.test.ts（对应测试脚本）

```typescript
// tests/bdd/hot/T-GH1.test.ts
// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { expectElement, expectElementAsync } from '@wangjs-jacky/tdd-kit'

// --- API mock ---
const fetchMock = vi.fn()
vi.mock('../../src/hooks/useRepos', () => ({
  useRepos: () => ({
    repos: fetchMock(),
    loading: false,
    error: null,
  }),
}))

describe('T-GH1 仓库列表渲染', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('完整流程: 页面加载 → 数据展示 → 错误处理', async () => {
    // Step 1: 渲染页面
    const { default: App } = await import('../../src/App')
    render(React.createElement(App))

    const pageEl = await screen.findByTestId('hot-page')
    expect(pageEl).toBeTruthy()

    // Step 2: 仓库数据加载成功
    // ... DOM 结构验证

    // Step 3: 数据加载失败
    // ... 错误提示验证

    // Step 4: 空数据状态
    // ... 空状态验证
  })
})
```
