# DOM 快照提取器

> 来源：Monkey `sidepanel.js:307-364`
> 核心价值：让 AI 看到真实页面结构，避免编造选择器

---

## 设计思路

在目标页面注入一个函数，提取四类元素的结构信息，生成紧凑的文本摘要给 AI：

1. **交互元素**（input/button/select）→ AI 生成选择器的关键信息
2. **ID 元素** → 精准选择器的最佳依据
3. **标题/地标** → 页面结构概览
4. **页面正文** → 理解页面语义内容

---

## 轻量选择器提取器

> 这个函数会被 `chrome.scripting.executeScript` 注入到目标页面执行，所以必须是纯 JS，不能引用外部模块。

```typescript
// lib/dom/extractor.ts

interface DOMSnapshot {
  title: string
  url: string
  metaDesc: string
  interactive: string[]  // input, button, select, textarea 等
  landmarks: string[]    // h1-h3, nav, main, header, footer
  links: string[]        // a[href]
  ids: string[]          // 所有有 id 的元素
}

export function domExtractor(): DOMSnapshot {
  const MAX = 60

  function attr(el: Element, ...names: string[]): string {
    for (const n of names) {
      const v = el.getAttribute(n)
      if (v) return `${n}="${v.slice(0, 80)}"`
    }
    return ''
  }

  function describe(el: Element): string {
    const tag = el.tagName.toLowerCase()
    const id = el.id ? `#${el.id}` : ''
    const cls = el.className && typeof el.className === 'string'
      ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
      : ''
    const extra = attr(el, 'name', 'type', 'placeholder', 'href', 'aria-label')
    const text = el.textContent?.trim().slice(0, 40) || ''
    return `<${tag}${id}${cls} ${extra}>${text ? `"${text}"` : ''}</${tag}>`
  }

  const results: DOMSnapshot = {
    title: document.title,
    url: location.href,
    metaDesc: document.querySelector('meta[name="description"]')
      ?.getAttribute('content')?.slice(0, 120) || '',
    interactive: [],
    landmarks: [],
    links: [],
    ids: [],
  }

  // 交互元素
  document.querySelectorAll(
    'input, button, select, textarea, [role="button"], [onclick]'
  ).forEach(el => {
    if (results.interactive.length < MAX) results.interactive.push(describe(el))
  })

  // 标题和地标
  document.querySelectorAll('h1,h2,h3,nav,main,header,footer,form')
    .forEach(el => {
      if (results.landmarks.length < 20) results.landmarks.push(describe(el))
    })

  // 链接
  document.querySelectorAll('a[href]')
    .forEach(el => {
      if (results.links.length < 20) results.links.push(describe(el))
    })

  // ID 元素
  document.querySelectorAll('[id]')
    .forEach(el => {
      if (results.ids.length < MAX) results.ids.push(`#${el.id}(${el.tagName.toLowerCase()})`)
    })

  return results
}
```

---

## 增强版页面快照（Turndown + Readability）

整合 Turndown 和 Readability，同时提供选择器信息和页面正文内容：

```typescript
// lib/dom/snapshot.ts
import TurndownService from 'turndown'
import { Readability } from '@mozilla/readability'

export function getPageSnapshot(): {
  selectorInfo: ReturnType<typeof domExtractor>
  pageContent: string   // Markdown 格式的页面正文
} {
  // 1. 轻量选择器信息（给 AI 写选择器用）
  const selectorInfo = domExtractor()

  // 2. 页面正文内容（给 AI 理解页面语义用）
  const clone = document.cloneNode(true) as Document
  const reader = new Readability(clone)
  const article = reader.parse()
  const td = new TurndownService()
  const pageContent = article
    ? td.turndown(article.content)
    : ''

  return { selectorInfo, pageContent }
}
```

---

## Content Script 配置

```typescript
// src/contents/dom-snapshot.ts
import type { PlasmoCSConfig } from 'plasmo'

export const config: PlasmoCSConfig = {
  matches: ['<all_urls>'],
  run_at: 'document_end',
}

// 监听来自 SidePanel 的快照请求
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'GET_SNAPSHOT') {
    const snapshot = getPageSnapshot()
    sendResponse(snapshot)
  }
  return true
})
```
