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
