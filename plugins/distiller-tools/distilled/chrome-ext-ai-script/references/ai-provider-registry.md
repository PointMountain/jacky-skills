# AI Provider 注册中心

> Monkey 的痛点：服务商硬编码在 options.js 里，加一个服务商要改多处代码
> 新方案：插件化注册，每个 Provider 独立一个文件

---

## 设计思路

采用 **Provider 注册中心模式**：每个服务商是独立模块，实现统一接口。新增服务商只需写一个 Provider 文件并注册，主流程代码零改动。

```
provider-registry.ts（注册中心）
    ├── registerProvider(openaiProvider)    → providers/openai.ts
    ├── registerProvider(claudeProvider)    → providers/claude.ts
    ├── registerProvider(geminiProvider)    → providers/gemini.ts
    └── registerProvider(customProvider)    → providers/custom.ts
```

---

## Provider 接口定义

```typescript
// lib/ai/provider-registry.ts

export interface AIProvider {
  id: string
  name: string
  models: string[]
  defaultModel: string
  createModel(apiKey: string, model: string, endpoint?: string): any
}
```

---

## 各服务商实现

### OpenAI

```typescript
// lib/ai/providers/openai.ts
import { createOpenAI } from '@ai-sdk/openai'

export const openaiProvider: AIProvider = {
  id: 'openai',
  name: 'OpenAI',
  models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  defaultModel: 'gpt-4o',
  createModel(apiKey, model, endpoint) {
    return createOpenAI({ apiKey, baseURL: endpoint }).languageModel(model)
  },
}
```

### Claude

```typescript
// lib/ai/providers/claude.ts
import { createAnthropic } from '@ai-sdk/anthropic'

export const claudeProvider: AIProvider = {
  id: 'claude',
  name: 'Claude',
  models: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  defaultModel: 'claude-sonnet-4-6',
  createModel(apiKey, model) {
    return createAnthropic({ apiKey }).languageModel(model)
  },
}
```

### Gemini

```typescript
// lib/ai/providers/gemini.ts
import { createGoogleGenerativeAI } from '@ai-sdk/google'

export const geminiProvider: AIProvider = {
  id: 'gemini',
  name: 'Gemini',
  models: ['gemini-2.0-flash', 'gemini-2.0-pro'],
  defaultModel: 'gemini-2.0-flash',
  createModel(apiKey, model) {
    return createGoogleGenerativeAI({ apiKey }).languageModel(model)
  },
}
```

---

## 注册中心

```typescript
// lib/ai/provider-registry.ts

const registry = new Map<string, AIProvider>()

export function registerProvider(provider: AIProvider) {
  registry.set(provider.id, provider)
}

export function getProvider(id: string): AIProvider | undefined {
  return registry.get(id)
}

export function getAllProviders(): AIProvider[] {
  return Array.from(registry.values())
}

// 初始化 — 新增服务商只需在这里加一行
registerProvider(openaiProvider)
registerProvider(claudeProvider)
registerProvider(geminiProvider)
```

---

## 连通性测试

设置面板中的"测试连接"功能：实际调用一次 AI API，判断 Key 是否有效。

```typescript
// 测试逻辑伪代码
async function testConnection(provider: AIProvider, apiKey: string, model: string) {
  try {
    const result = await generateText({
      model: provider.createModel(apiKey, model),
      prompt: 'Hello',
      maxTokens: 1,
    })
    return { success: true, latency: result.duration }
  } catch (error) {
    // 429 频率限制也算成功（说明 Key 有效）
    if (error.status === 429) {
      return { success: true, note: '频率限制，但 Key 有效' }
    }
    return { success: false, reason: error.message }
  }
}
```
