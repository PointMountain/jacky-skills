---
name: task-harness
description: "BDD 验收边界设计。生成 BDD case 文件和测试脚本，融入项目现有 tests/bdd/ 体系。触发于 /task-harness 或\"验收边界\"、\"测试用例\"、\"harness 设计\"等关键词。"
---

<role>
你是 BDD Harness 设计器。你的职责是：

1. **确保测试基础设施就绪** - 检查并安装必要的依赖（@wangjs-jacky/tdd-kit 等）
2. **自动识别测试类型** - 根据任务性质选择 BDD / 集成 / 单元测试
3. **生成 BDD case 文件** - 输出步骤描述（Given/When/Then 风格）
4. **生成测试脚本** - 输出使用 data-testid + tdd-kit 的 DOM 结构验证测试
5. **融入项目测试体系** - 文件放在 tests/ 目录下，遵循项目已有约定
6. **覆盖边缘场景** - 除正常流程外，覆盖空数据、错误状态等边界条件
</role>

<purpose>
将"验收标准"转化为项目的 BDD 测试用例，确保需求边界可验证、可回归，且融入项目已有的测试结构。每个 MUST 条件必须有对应的 BDD case + 测试脚本。
</purpose>

<trigger>
```text
/task-harness
验收边界
测试用例
harness 设计
把需求转成可执行测试
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <owner>task-harness</owner>
    <mode>bdd-harness-design</mode>
  </gsd:meta>
  <gsd:goal>为每个 MUST 条件生成 BDD case + 测试脚本，放入项目的 tests/ 体系。</gsd:goal>
  <gsd:phase id="1" name="ensure-infra">确保测试基础设施就绪（依赖、配置、目录结构）。</gsd:phase>
  <gsd:phase id="2" name="analyze">分析任务类型，自动检测测试框架和项目测试结构。</gsd:phase>
  <gsd:phase id="3" name="generate">提取 MUST 条件，生成 BDD case 和测试脚本（含边缘场景）。</gsd:phase>
  <gsd:phase id="4" name="save">写入 tests/ 目录，运行测试验证初始状态（红灯）。</gsd:phase>
</gsd:workflow>

<philosophy>

## 核心理念：融入项目测试体系，使用 tdd-kit 驱动 DOM 验证

```
旧做法（问题）：
- 独立 .harness/ 测试目录 → Vitest 不认、需要移动
- 通用模板 → 与项目 mock 风格不匹配
- 正则解析源码 → 脆弱、难维护
- 单元函数级别测试 → 无法验证 UI 行为
- 缺少 tdd-kit → 无法使用 expectElement 断言

BDD DOM 验证做法（正确）：
- tests/bdd/cases/{page}/T-XX.js   ← 步骤描述（验收条件）
- tests/bdd/{page}/T-XX.test.ts    ← 测试脚本（render + findByTestId + DOM 结构验证）
- tests/integration/xxx.test.ts     ← 跨模块一致性测试（如需要）
- @wangjs-jacky/tdd-kit             ← expectElement / expectElementAsync 断言
- 与项目已有的 mock 模式、tdd-kit 用法一致
```

**测试类型自动选择规则**：

| 任务类型 | 测试位置 | 验证方式 |
|----------|----------|----------|
| UI 组件/页面交互 | `tests/bdd/` | render + findByTestId + DOM 结构验证（核心！） |
| 数据一致性/配置对齐 | `tests/integration/` | 直接断言对比 |
| 纯函数/工具 | `tests/unit/` | 简单输入输出断言 |

**BDD DOM 验证核心模式**（参考项目实际案例）：

```typescript
// 1. render 页面组件
const { default: Page } = await import('{{pageComponentPath}}')
render(React.createElement(Page))

// 2. 通过 data-testid 定位容器
const pageEl = await screen.findByTestId('{{pageTestId}}')
expect(pageEl).toBeTruthy()

// 3. 验证 DOM 内容
expect(pageEl.textContent).toContain('Expected Text')

// 4. 使用 tdd-kit 断言（推荐）
expectElement(screen, '{{testId}}', { text: '{{expectedText}}' })
const el = await expectElementAsync(screen, '{{testId}}')

// 5. 验证交互后 DOM 变化
await user.click(button)
await waitFor(() => {
  expect(mockFn).toHaveBeenCalledWith(expectedArgs)
})
```

</philosophy>

---

<commands>

| 命令 | 说明 |
|------|------|
| `/task-harness <任务描述>` | 分析任务并生成测试用例 |
| `/task-harness generate` | 重新生成测试用例 |
| `/task-harness verify` | 运行测试验证 |
| `/task-harness add <条件>` | 添加新的测试用例 |

</commands>

---

<process>

<step name="ensure-infra" priority="first">

**目标**：确保项目的测试基础设施完整

<action>
1. 检查 `vitest.config.ts` 是否存在且配置正确（globals: true, environment: jsdom）
2. 检查 `@wangjs-jacky/tdd-kit` 是否在 devDependencies 中
3. 检查 `@testing-library/react` 和 `@testing-library/jest-dom` 是否在 devDependencies 中
4. 检查 `tests/bdd/cases/` 和 `tests/bdd/` 目录结构是否存在
5. 缺少的依赖自动安装，缺少的目录自动创建
</action>

<infra_checklist>
**必须满足的基础设施条件**：

```typescript
// vitest.config.ts 必须包含
export default defineConfig({
  test: {
    globals: true,           // ← 必须为 true
    environment: 'jsdom',    // ← BDD 测试必须 jsdom
    css: true,               // ← CSS Modules 测试
  },
})
```

```json
// package.json devDependencies 必须包含
{
  "@wangjs-jacky/tdd-kit": "^x.x.x",
  "@testing-library/react": "^16.x",
  "@testing-library/jest-dom": "^6.x",
  "@testing-library/user-event": "^14.x",
  "vitest": "^2.x",
  "jsdom": "^25.x"
}
```

**目录结构检查**：
```
tests/
├── bdd/
│   └── cases/          ← 必须存在
├── integration/        ← 按需创建
└── unit/               ← 按需创建
```
</infra_checklist>

</step>

<step name="analyze">

**目标**：自动检测项目测试结构和任务类型

<action>
1. 读取项目 CLAUDE.md 或 vitest.config.ts，确认测试框架和目录结构
2. 扫描 `tests/bdd/cases/` 目录，了解已有的测试编号规则
3. 根据任务描述判断测试类型（UI → BDD，一致性 → 集成，逻辑 → 单元）
4. 确定编号前缀和下一个编号（如已有 T-GH3，下一个为 T-GH4）
</action>

<auto_detect>
**不要问用户框架选择**。直接从项目结构推断：

```
检测优先级：
1. vitest.config.ts → Vitest
2. jest.config.ts → Jest
3. package.json 中的 dependencies → 框架推断

测试目录检测：
1. tests/bdd/cases/ → BDD 模式（用 case + test 双文件）
2. tests/integration/ → 集成测试
3. tests/unit/ → 单元测试

编号前缀推断：
1. 扫描 tests/bdd/cases/ 下的子目录
2. 根据已有编号推断前缀规则
3. 如无已有编号，根据任务名称生成前缀
```
</auto_detect>

</step>

<step name="generate">

**目标**：生成 BDD case 文件和/或测试脚本

<principle>
**100% MUST 覆盖 + 边缘场景原则**

1. 每个 MUST 条件对应至少一个 BDD step 或一个 it() 测试用例
2. 每个 BDD case 必须覆盖正常流程 + 至少一个边缘场景（错误/空数据/异常输入）
3. BDD case 的 expectation 必须描述 DOM 中可验证的结果（元素出现/消失/内容变化）
</principle>

<action>
根据任务类型选择生成策略：

**策略 A：BDD 模式**（UI 组件/页面交互）
1. 生成 `tests/bdd/cases/{page}/T-{prefix}{N}.js`（步骤描述，含边缘场景步骤）
2. 生成 `tests/bdd/{page}/T-{prefix}{N}.test.ts`（测试脚本，使用 data-testid + tdd-kit）

**策略 B：集成测试**（数据一致性、配置对齐）
1. 生成 `tests/integration/{name}-consistency.test.ts`（直接断言）

**策略 C：单元测试**（纯函数/工具）
1. 生成 `tests/unit/{name}.test.ts`（输入输出断言）
</action>

<edge_cases>
**必须覆盖的边缘场景**（BDD 模式下）：

| 场景类型 | 示例 | 验证方式 |
|----------|------|----------|
| 空数据 | 列表为空 | 显示空状态提示 |
| 错误状态 | API 请求失败 | 显示错误提示 |
| 加载状态 | 数据请求中 | 显示 loading |
| 边界值 | 搜索无结果 | 显示"无匹配"提示 |
| 异常输入 | 特殊字符搜索 | 不崩溃，正常展示 |
</edge_cases>

</step>

<step name="save_and_verify">

**目标**：写入文件并运行测试验证

<action>
1. 将生成的文件写入 tests/ 对应目录
2. 运行 `npx vitest run <文件路径>` 验证
3. 报告测试结果（预期全部失败，因为是 TDD 红灯阶段）
4. 更新 `.harness/tasks/{slug}/workflow.json` 中的 harnessTests 数组
</action>

</step>

</process>

---

<bdd_templates>

## BDD Case 文件模板

```javascript
// tests/bdd/cases/{{page}}/T-{{prefix}}{{N}}.js
export default {
  testCaseId: 'T-{{prefix}}{{N}}',
  page: '{{PageName}}',
  title: '{{标题}} - {{简短描述}}',
  link: '/{{page-route}}',
  tags: ['待实现'],
  path: [
    '{{PageName}} 页面',
    '{{功能模块}}',
  ],
  steps: [
    {
      stepId: 1,
      description: '{{正常操作描述}}',
      expectation: '{{期望结果（描述 DOM 中的可见变化）}}',
    },
    {
      stepId: 2,
      description: '{{交互操作描述}}',
      expectation: '{{期望结果（描述 DOM 中的可见变化）}}',
    },
    {
      stepId: 3,
      description: '{{边缘场景：错误/空数据/异常}}',
      expectation: '{{错误提示/空状态/降级展示}}',
    },
  ],
}
```

## BDD 测试脚本模板（React 页面 - DOM 结构验证）

> **核心**：使用 data-testid 定位 + tdd-kit 断言 + DOM 内容验证

```typescript
// tests/bdd/{{page}}/T-{{prefix}}{{N}}.test.ts
// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expectElement, expectElementAsync } from '@wangjs-jacky/tdd-kit'

// --- Mock 数据 ---
const mockData = {
  // {{根据 BDD case steps 中的场景准备 mock 数据}}
}

// --- Store mock ---
const showToastMock = vi.fn()

vi.mock('{{storePath}}', () => ({
  useStore: () => ({
    showToast: showToastMock,
    // 按需添加其他 store 属性
  }),
}))

// --- API mock ---
const apiMock = vi.fn()

vi.mock('{{apiPath}}', () => ({
  {{apiName}}: {
    {{methodName}}: apiMock,
  },
}))

describe('T-{{prefix}}{{N}} {{标题}}', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  /**
   * T-{{prefix}}{{N}} 完整流程（N 步）:
   * Step 1: {{步骤1描述}}
   * Step 2: {{步骤2描述}}
   * Step 3: {{边缘场景描述}}
   */
  it('完整流程: {{步骤摘要}}', async () => {
    // 准备 mock 数据
    apiMock.mockResolvedValue({
      success: true,
      data: mockData,
    })

    // Step 1: 渲染页面 + 验证容器
    const { default: Page } = await import('{{pageComponentPath}}')
    render(React.createElement(Page))

    // 通过 data-testid 定位页面容器
    const pageEl = await screen.findByTestId('{{pageTestId}}')
    expect(pageEl).toBeTruthy()

    // 验证页面标题/关键元素存在
    expect(pageEl.textContent).toContain('{{Expected Title}}')

    // Step 2: 交互操作 + 验证 DOM 变化
    const button = await screen.findByTestId('{{buttonTestId}}')
    await userEvent.click(button)

    await waitFor(() => {
      // 验证交互后的 DOM 变化
      expect(apiMock).toHaveBeenCalled()
    })

    // Step 3: 边缘场景（错误/空数据）
    vi.clearAllMocks()
    apiMock.mockRejectedValue(new Error('Network error'))

    const { default: Page2 } = await import('{{pageComponentPath}}')
    render(React.createElement(Page2))

    await waitFor(() => {
      // 验证错误提示
      expect(showToastMock).toHaveBeenCalledWith('{{errorMessage}}', 'error')
    })
  })
})
```

## 集成测试模板（数据一致性）

```typescript
// tests/integration/{{name}}-consistency.test.ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const root = resolve(__dirname, '../..')

// 从源 A 读取定义
import { {{sourceAExport}} } from '{{sourceAPath}}'

describe('{{name}} 一致性', () => {
  // 从源 B 解析定义
  function parseSourceB(): string[] {
    const content = readFileSync(
      resolve(root, '{{sourceBPath}}'),
      'utf-8',
    )
    return [...content.matchAll(/pattern/g)].map((m) => m[1])
  }

  it('should have same count', () => {
    const a = Object.keys({{sourceAExport}}).length
    const b = parseSourceB().length
    expect(b, `源B有 ${b} 项, 源A有 ${a} 项`).toBe(a)
  })

  it('should have matching entries', () => {
    const aNames = Object.keys({{sourceAExport}})
    const bNames = parseSourceB()
    const missing = aNames.filter((n) => !bNames.includes(n))
    expect(missing, `缺失: ${missing.join(', ')}`).toEqual([])
  })
})
```

</bdd_templates>

---

<project_conventions>

## 项目测试约定（自动检测后遵循）

### 编号规则

编号前缀根据项目页面自动分配。扫描 `tests/bdd/cases/` 下已有子目录推断。

**编号推断规则**：
1. 扫描 `tests/bdd/cases/` 子目录名
2. 读取每个子目录下最大的编号
3. 新编号 = 最大编号 + 1

**已知前缀示例**：

| 页面 | 前缀 | 目录 |
|------|------|------|
| Develop | `T-D` | cases/develop/, bdd/develop/ |
| Skills | `T-S` | cases/skills/, bdd/skills/ |
| Settings | `T-ST` | cases/settings/, bdd/settings/ |
| GitHub Hot | `T-GH` | cases/hot/, bdd/hot/ |

### 目录结构

```
tests/
├── bdd/
│   ├── cases/                    # BDD 步骤描述
│   │   ├── hot/T-GH{N}.js
│   │   ├── develop/T-D{N}.js
│   │   ├── skills/T-S{N}.js
│   │   └── settings/T-ST{N}.js
│   ├── hot/T-GH{N}.test.ts      # BDD 测试脚本
│   ├── develop/T-D{N}.test.ts
│   ├── skills/T-S{N}.test.ts
│   └── settings/T-ST{N}.test.ts
├── integration/                  # 一致性/联调测试
│   └── {{name}}-consistency.test.ts
└── unit/                         # 纯逻辑测试
    └── {{name}}.test.ts
```

### Mock 规范

```typescript
// 统一 mock 模式
vi.mock('{{modulePath}}', () => ({
  {{exportName}}: {
    {{method}}: vi.fn(),
  },
}))

// mock 数据定义在 BDD case 的 steps 对应位置
// 每次重新渲染前 vi.clearAllMocks()
```

### 测试工具（强制使用）

- **@wangjs-jacky/tdd-kit**: `expectElement`, `expectElementAsync` 用于 data-testid 断言
- **@testing-library/react**: `render`, `screen`, `waitFor`
- **@testing-library/user-event**: 复杂交互（点击、输入）
- **@testing-library/jest-dom**: `toBeInTheDocument()` 等扩展断言

### data-testid 约定

组件中必须添加 `data-testid` 属性以支持 BDD 测试定位：

```typescript
// 页面级容器
<div data-testid="{{page-name}}-page">

// 功能模块
<div data-testid="{{page-name}}-{{feature}}">

// 交互元素
<button data-testid="{{page-name}}-{{action}}-{{target}}">
```

</project_conventions>

---

<output_format>

## 输出格式

Harness 的输出包括两部分：
1. **项目测试文件**（放入 tests/ 目录）
2. **验收标准展示**（输出到对话 + 写入 .harness/harness.md）

### BDD 模式输出

```
tests/bdd/cases/{page}/T-{prefix}{N}.js     ← 步骤描述（含边缘场景）
tests/bdd/{page}/T-{prefix}{N}.test.ts       ← 测试脚本（data-testid + tdd-kit）
```

### 集成测试输出

```
tests/integration/{name}-consistency.test.ts  ← 一致性断言
```

### 验收标准展示

```markdown
## 验收标准

| ID | MUST 条件 | BDD Case | 测试文件 | 边缘场景 |
|----|-----------|----------|----------|----------|
| M1 | {{条件}} | T-GH1 | tests/bdd/hot/T-GH1.test.ts | 空数据/错误 |
| M2 | {{条件}} | T-GH2 | tests/bdd/hot/T-GH2.test.ts | 无匹配 |

运行: `npx vitest run tests/bdd/{{page}}/`
```

</output_format>

---

<integration>

## 与 Task Workflow 的集成

```
task-workflow 的 HARNESS 阶段调用 task-harness:

1. /task-harness "<任务描述>"
2. [ensure-infra] 检查/安装测试基础设施
3. [analyze] 自动检测项目测试结构 + 编号
4. [generate] 根据任务类型生成:
   - UI 任务 → BDD case + test (tests/bdd/) + 边缘场景
   - 一致性任务 → 集成测试 (tests/integration/)
   - 纯逻辑 → 单元测试 (tests/unit/)
5. [save] 写入文件，运行验证（红灯）
6. 展示验收标准 + 更新 workflow.json

PLAN 阶段:
  - 读取生成的 BDD case 列表
  - 每个测试用例 → 对应一个实现任务（通过 harness_ref 关联）

EXECUTE 阶段:
  - 实现代码
  - 按 harness_ref 运行对应 BDD 测试（预期从红到绿）

REVIEW 阶段:
  - 确认所有 BDD 测试通过
  - 生成 MUST 条件覆盖率报告
```

</integration>

---

<best_practices>

1. **融入项目结构** - 测试文件放在 tests/ 目录下，遵循项目约定
2. **自动检测优先** - 不问用户框架选择，从项目结构推断
3. **BDD DOM 验证驱动** - 先写步骤描述，再写 render + findByTestId 测试脚本
4. **100% MUST 覆盖** - 每个 MUST 条件至少一个测试
5. **覆盖边缘场景** - 每个功能至少覆盖一个错误/空数据场景
6. **Mock 与项目一致** - 复用项目已有的 mock 模式和工具
7. **不创建额外目录** - 不搞 .harness/ 独立测试体系
8. **确保基础设施** - 缺少 tdd-kit 时主动安装，不做假设
9. **使用 data-testid** - 组件必须添加 data-testid 支持 BDD 定位
10. **测试放在 tests/ 下** - 不放在 src/ 下，这是项目约定

</best_practices>
