# Harness 模板库

> 此文件包含各类任务的 Harness 模板，供主 SKILL.md 引用。
> 模板融入项目的 tests/ 体系，使用 @wangjs-jacky/tdd-kit 进行 DOM 验证。

---

## vitest.config.ts 模板

> 如果项目中不存在此文件，必须创建。

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,            // 必须为 true
    environment: 'jsdom',     // BDD 测试必须 jsdom
    css: true,                // CSS Modules 测试支持
    setupFiles: './src/test-setup.ts',  // 按需
    coverage: {
      provider: 'v8',         // 覆盖率提供程序
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.*', 'src/**/*.d.ts'],
    },
  },
})
```

---

## test-setup.ts 模板

> 如果使用 setupFiles，创建此文件。

```typescript
import '@testing-library/jest-dom/vitest'
```

---

## BDD Case 模板（UI 组件/页面）

### 模板文件：`tests/bdd/cases/{page}/T-{prefix}{N}.js`

```javascript
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
      expectation: '{{期望结果}}',
    },
    {
      stepId: 3,
      description: '{{边缘场景：错误/空数据/异常输入}}',
      expectation: '{{错误提示/空状态/降级展示}}',
    },
  ],
}
```

### 测试脚本：`tests/bdd/{page}/T-{prefix}{N}.test.ts`

> **核心验证模式**：render + data-testid + tdd-kit + DOM 内容验证

```typescript
// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expectElement, expectElementAsync } from '@wangjs-jacky/tdd-kit'

// --- Mock 数据（定义在 BDD case 的 steps 对应位置） ---
const mockData = {
  success: true,
  data: {{mockData}},
}

// --- Store mock ---
const showToastMock = vi.fn()

vi.mock('{{storePath}}', () => ({
  useStore: () => ({
    showToast: showToastMock,
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
    apiMock.mockResolvedValue(mockData)

    // Step 1: 渲染页面 + 验证容器
    const { default: Page } = await import('{{pageComponentPath}}')
    render(React.createElement(Page))

    // 通过 data-testid 定位页面容器
    const pageEl = await screen.findByTestId('{{pageTestId}}')
    expect(pageEl).toBeTruthy()

    // 验证关键内容
    expect(pageEl.textContent).toContain('{{Expected Title}}')

    // 使用 tdd-kit 验证（推荐）
    expectElement(screen, '{{testId}}', { text: '{{expectedText}}' })

    // Step 2: 交互操作
    const button = await screen.findByTestId('{{buttonTestId}}')
    await userEvent.click(button)

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith({{expectedArgs}})
    })

    // Step 3: 边缘场景
    vi.clearAllMocks()
    apiMock.mockRejectedValue(new Error('Network error'))

    const { default: Page2 } = await import('{{pageComponentPath}}')
    render(React.createElement(Page2))

    await waitFor(() => {
      expect(showToastMock).toHaveBeenCalledWith('{{errorMessage}}', 'error')
    })
  })
})
```

---

## 集成测试模板（数据一致性/配置对齐）

### 文件：`tests/integration/{name}-consistency.test.ts`

```typescript
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const root = resolve(__dirname, '../..')

describe('{{name}} 一致性', () => {
  it('should have same count', () => {
    const sourceA = getFromSourceA()
    const sourceB = getFromSourceB()
    expect(sourceB.length).toBe(sourceA.length)
  })

  it('should have matching entries', () => {
    const aNames = getFromSourceA()
    const bNames = getFromSourceB()
    const missing = aNames.filter((n) => !bNames.includes(n))
    expect(missing, `缺失: ${missing.join(', ')}`).toEqual([])
  })
})
```

---

## 单元测试模板（纯函数/工具）

### 文件：`tests/unit/{name}.test.ts`

```typescript
import { describe, it, expect } from 'vitest'
import { {{functionName}} } from '{{modulePath}}'

describe('{{functionName}}', () => {
  it('should handle normal input', () => {
    const result = {{functionName}}({{validInput}})
    expect(result).toEqual({{expectedOutput}})
  })

  it('should handle edge case: empty input', () => {
    const result = {{functionName}}([])
    expect(result).toEqual([])
  })

  it('should throw for invalid input', () => {
    expect(() => {{functionName}}(null)).toThrow()
  })
})
```

---

## data-testid 命名约定

> 组件中必须添加 data-testid 属性以支持 BDD 测试。

```typescript
// 页面级容器
<div data-testid="{{page-name}}-page">

// 功能模块
<div data-testid="{{page-name}}-{{feature}}">

// 交互元素
<button data-testid="{{page-name}}-{{action}}-{{target}}">

// 列表项
<div data-testid="{{page-name}}-{{item-type}}-{{id}}">
```

---

## 编号规则速查

| 页面 | 前缀 | 目录 | 示例 |
|------|------|------|------|
| GitHub Hot | `T-GH` | cases/hot/, bdd/hot/ | T-GH1, T-GH2 |
| Develop | `T-D` | cases/develop/, bdd/develop/ | T-D1, T-D2 |
| Skills | `T-S` | cases/skills/, bdd/skills/ | T-S1, T-S2 |
| Settings | `T-ST` | cases/settings/, bdd/settings/ | T-ST1, T-ST2 |
| 集成测试 | 无编号 | tests/integration/ | - |
| 单元测试 | 无编号 | tests/unit/ | - |

---

## 边缘场景覆盖清单

每个 BDD case 应覆盖以下场景中的至少一项：

| 场景 | 验证要点 | 示例 |
|------|----------|------|
| 空数据 | 显示空状态提示 | 列表为空 → "暂无数据" |
| API 错误 | 显示错误提示 | fetch 失败 → Toast error |
| 加载中 | 显示 loading 状态 | 请求中 → spinner |
| 无匹配 | 显示无结果提示 | 搜索无结果 → "无匹配项" |
| 边界值 | 正确处理极端数据 | 0 条 / 1000 条数据 |
| 特殊字符 | 不崩溃 | 搜索 `<script>` |

---

## 分步模式测试脚本模板

> **适用场景**：BDD case 中每个 step 独立验证，步骤之间无强状态依赖。
> 步骤数 > 4 或步骤相互独立时推荐使用。

```typescript
// tests/bdd/{{page}}/T-{{prefix}}{{N}}.test.ts
// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expectElement } from '@wangjs-jacky/tdd-kit'

// --- Mock 数据 ---
const normalMockData = {
  success: true,
  data: {{normalData}},
}

const emptyMockData = {
  success: true,
  data: [],
}

// --- Mock 配置 ---
let mockData = normalMockData

vi.mock('{{storePath}}', () => ({
  useStore: () => ({
    showToast: vi.fn(),
  }),
}))

vi.mock('{{apiPath}}', () => ({
  {{apiName}}: {
    {{methodName}}: (...args) => Promise.resolve(mockData),
  },
}))

describe('T-{{prefix}}{{N}} {{标题}}', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockData = normalMockData
  })

  it('Step 1: {{步骤1描述 - 通常是页面渲染/数据加载}}', async () => {
    const { default: Page } = await import('{{pageComponentPath}}')
    render(React.createElement(Page))

    // 验证页面容器渲染
    const pageEl = await screen.findByTestId('{{pageTestId}}')
    expect(pageEl).toBeTruthy()

    // 验证关键内容
    expectElement(screen, '{{testId}}', { text: '{{expectedText}}' })
  })

  it('Step 2: {{步骤2描述 - 通常是交互操作}}', async () => {
    const { default: Page } = await import('{{pageComponentPath}}')
    render(React.createElement(Page))

    // 执行交互
    const button = await screen.findByTestId('{{buttonTestId}}')
    await userEvent.click(button)

    // 验证交互结果
    await waitFor(() => {
      const resultEl = screen.getByTestId('{{resultTestId}}')
      expect(resultEl.textContent).toContain('{{expectedResult}}')
    })
  })

  it('Step 3: 边缘场景 - {{边缘描述}}', async () => {
    mockData = emptyMockData

    const { default: Page } = await import('{{pageComponentPath}}')
    render(React.createElement(Page))

    // 验证空状态
    const emptyState = await screen.findByTestId('{{emptyTestId}}')
    expect(emptyState).toBeTruthy()
    expect(emptyState.textContent).toContain('{{emptyMessage}}')
  })
})
```

---

## 非页面组件测试模板

> **适用场景**：测试 Sidebar、Header、Modal 等独立组件，非完整页面。
> 组件通常需要 props 传入，而非路由加载。

```typescript
// tests/bdd/{{componentDir}}/T-{{prefix}}{{N}}.test.ts
// @vitest-environment jsdom
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expectElement } from '@wangjs-jacky/tdd-kit'

// 导入组件（非动态 import，因为组件不需要路由）
import { {{ComponentName}} } from '{{componentPath}}'

// --- Mock 依赖 ---
const onClickMock = vi.fn()

vi.mock('{{dependencyPath}}', () => ({
  {{dependencyExport}}: vi.fn(),
}))

describe('T-{{prefix}}{{N}} {{标题}}', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('正常渲染: {{组件正常状态描述}}', () => {
    render(
      React.createElement({{ComponentName}}, {
        {{prop1}}: '{{value1}}',
        {{prop2}}: {{value2}},
        on{{Event}}: onClickMock,
      })
    )

    const componentEl = screen.getByTestId('{{componentTestId}}')
    expect(componentEl).toBeTruthy()
    expect(componentEl.textContent).toContain('{{expectedContent}}')
  })

  it('交互: {{交互描述}}', async () => {
    render(
      React.createElement({{ComponentName}}, {
        {{prop1}}: '{{value1}}',
        on{{Event}}: onClickMock,
      })
    )

    const trigger = await screen.findByTestId('{{triggerTestId}}')
    await userEvent.click(trigger)

    expect(onClickMock).toHaveBeenCalledWith({{expectedArgs}})
  })

  it('边缘场景: {{边缘描述}}', () => {
    // 测试空 props / 异常 props
    render(
      React.createElement({{ComponentName}}, {
        {{prop1}}: undefined,
        {{prop2}}: null,
      })
    )

    const componentEl = screen.getByTestId('{{componentTestId}}')
    expect(componentEl).toBeTruthy()
    // 验证降级展示
  })
})
```

---

## Mock 模式速查表

> 快速选择合适的 mock 策略。

### 模式 1：简单 Mock（固定返回值）

**场景**：mock 返回值在整个测试文件中不变。

```typescript
const apiMock = vi.fn()

vi.mock('{{apiPath}}', () => ({
  {{apiName}}: { {{methodName}}: apiMock },
}))

// 使用
beforeEach(() => {
  apiMock.mockResolvedValue({ success: true, data: mockData })
})
```

### 模式 2：动态 Mock（getter 函数）

**场景**：不同 it() 需要不同的 mock 返回值。

```typescript
let mockData = { success: true, data: defaultData }

vi.mock('{{apiPath}}', () => ({
  {{apiName}}: {
    {{methodName}}: (...args) => Promise.resolve(mockData),
  },
}))

// 在各 it() 中修改
it('正常流程', () => {
  mockData = { success: true, data: normalData }
})

it('空数据', () => {
  mockData = { success: true, data: [] }
})

it('错误', () => {
  mockData = { success: false, error: 'Something went wrong' }
})
```

### 模式 3：子树查找 Mock（within 限定范围）

**场景**：页面有多个相同结构的元素（列表项、卡片），需要在特定容器内查找。

```typescript
import { within } from '@testing-library/react'

it('列表中的特定项', async () => {
  render(React.createElement(Page))

  // 找到列表容器
  const list = await screen.findByTestId('{{listTestId}}')

  // 在列表内查找特定项
  const items = within(list).getAllByTestId('{{itemTestId}}')
  expect(items.length).toBe({{expectedCount}})

  // 在特定项内查找元素
  const firstItem = items[0]
  const title = within(firstItem).getByText('{{expectedTitle}}')
  expect(title).toBeTruthy()
})

// 结合 tdd-kit
it('结合 expectElement 验证', async () => {
  render(React.createElement(Page))

  const card = await screen.findByTestId('{{cardTestId}}')
  const button = within(card).getByRole('button', { name: '{{buttonName}}' })

  await userEvent.click(button)

  // 验证卡片内部变化
  await waitFor(() => {
    expect(within(card).getByText('{{newContent}}')).toBeTruthy()
  })
})
```

### 速查表

| 场景 | 推荐模式 | 关键 API |
|------|----------|----------|
| API 固定返回 | 简单 Mock | `vi.fn()` + `mockResolvedValue` |
| 不同测试不同返回 | 动态 Mock | `let mockData` + getter 函数 |
| 列表/卡片内查找 | 子树查找 | `within(container).getByXxx()` |
| 路由/图标等非业务依赖 | 组件 Mock | `vi.mock('react-router-dom')` |
| Store/全局状态 | 简单 Mock | `vi.mock('{{store}}', () => ({...}))` |
