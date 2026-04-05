# world:MAIN 脚本注入

> 来源：Monkey `sidepanel.js:603-619` + `service-worker.js:119-131`
> 核心价值：绕过 CSP，在页面主世界执行代码

---

## 背景知识

Chrome 扩展有两种执行世界：

| 世界 | 作用域 | CSP 限制 | 适用场景 |
|------|--------|---------|---------|
| `ISOLATED`（默认） | 扩展隔离世界 | 不受页面 CSP 限制 | 访问扩展 API |
| `MAIN` | 页面主世界 | 不受页面 CSP 限制 | 访问页面 JS 上下文 |

关键点：**两个世界都不受页面 CSP 限制**，但只有 `MAIN` 世界能访问页面的全局 JS 变量和 DOM 状态。

---

## 核心函数

```typescript
// lib/injection/script-runner.ts

/**
 * 在目标页面的主世界中执行 JS 代码
 * - world: 'MAIN' 绕过页面 CSP 限制
 * - (0, eval)(src) 间接 eval 让代码在全局作用域运行
 */
export async function executeInPage(tabId: number, code: string): Promise<void> {
  await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func: (src: string) => (0, eval)(src),
    args: [code],
  })
}

/**
 * 在目标页面执行一个函数并获取返回值
 * 用于提取 DOM 快照等场景
 */
export async function executeAndReturn<T>(
  tabId: number,
  func: () => T
): Promise<T | null> {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func,
  })
  return (result?.result as T) ?? null
}
```

---

## 使用示例

### 提取 DOM 快照

```typescript
const snapshot = await executeAndReturn<DOMSnapshot>(tabId, domExtractor)
```

### 执行 AI 生成的脚本

```typescript
await executeInPage(tabId, generatedScriptCode)
```

---

## 为什么用间接 eval

```typescript
// ✗ 直接 eval — 代码在闭包作用域运行
func: (src: string) => eval(src)
// 页面代码中的 function 声明不会成为全局函数

// ✓ 间接 eval — 代码在全局作用域运行
func: (src: string) => (0, eval)(src)
// (0, eval) 是间接调用，等价于全局 eval
// function 声明会成为全局函数，var 声明会成为全局变量
```

---

## 权限声明

需要在 `manifest.json` 中声明 `scripting` 权限：

```json
{
  "permissions": ["scripting", "activeTab"]
}
```

Plasmo 框架会自动处理 manifest 生成，只需在代码中使用即可。
