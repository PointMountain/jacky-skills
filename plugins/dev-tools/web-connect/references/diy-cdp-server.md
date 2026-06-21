# 自建最小 CDP server

当环境里没有任何现成 provider（web-access / agent-browser / opencli 都没有），可以自己写一个最小 CDP server 满足 web-connect 的能力契约。**核心思路：Chrome 用调试端口启动 → 通过 CDP 控制它。** 不需要从零实现，借一个库即可。

---

## 一、前提：Chrome 开调试端口

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
# Linux
google-chrome --remote-debugging-port=9222
```
连已运行的日常 Chrome → 用 `chrome://inspect/#remote-debugging` 勾选 Allow。带调试端口启动即天然复用登录态。

---

## 二、最小实现（chrome-remote-interface）

```bash
npm i -g chrome-remote-interface
```

```js
// mini-cdp.mjs —— 满足契约的最小子集：list-tabs / screenshot / eval / click
import CDP from 'chrome-remote-interface';
import { writeFileSync } from 'node:fs';

const PORT = 9222;

// list-tabs：列出所有 page，自己判定当前活动 tab
export async function tabs() {
  const list = await CDP.List({ port: PORT });
  return list.filter(t => t.type === 'page').map(t => ({ id: t.id, title: t.title, url: t.url }));
}

async function withTab(id, fn) {
  const client = await CDP({ port: PORT, target: id });
  try { return await fn(client); } finally { await client.close(); }
}

// eval：跑任意 JS，返回可序列化值（read-text / read-dom / list-interactives 都靠它）
export const evalJs = (id, expr) => withTab(id, async ({ Runtime }) => {
  const { result } = await Runtime.evaluate({ expression: expr, returnByValue: true, awaitPromise: true });
  return result.value;
});

// focus-tab：当前活动 tab = visibilityState 为 visible 的那个
export async function activeTab() {
  for (const t of await tabs()) {
    if (await evalJs(t.id, 'document.visibilityState') === 'visible') return t;
  }
  return null;
}

// screenshot
export const shot = (id, file) => withTab(id, async ({ Page }) => {
  await Page.enable();
  const { data } = await Page.captureScreenshot({ format: 'png' });
  writeFileSync(file, Buffer.from(data, 'base64'));
  return file;
});

// click：CSS 选择器，只用于只读展开/折叠（写操作交回上层走安全门）
export const click = (id, sel) => evalJs(id,
  `(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return false;e.scrollIntoView({block:'center'});e.click();return true;})()`);
```

把这些函数包成 CLI 或 HTTP 端点都行。**最少实现 `tabs / activeTab / eval / screenshot / click` 五个就够 web-connect 跑通**——读结构和提取交互元素全部走 `evalJs` 手写 JS。

---

## 三、对照能力契约自检

| 契约能力 | 上面对应 |
|----------|----------|
| list-tabs | `tabs()` |
| focus-tab | `activeTab()`（visibility 判定）|
| screenshot | `shot()` |
| read-text/dom / list-interactives | `evalJs()` + 手写 JS |
| eval | `evalJs()` |
| click | `click()` |
| navigate/new/close | 用 `CDP.New` / `Page.navigate` / `CDP.Close` 补 |

补 navigate/close 也是几行：`await CDP.New({port,url})`、`await CDP.Close({port,id})`、`Page.navigate({url})`。

---

## 四、提醒
- 返回值必须可序列化（同 web-access：DOM 节点取属性，批量数据 `JSON.stringify`）。
- 写操作（保存/删除/提交）**不要**在这里偷偷实现成自动执行——web-connect 的安全门在上层，DIY server 只提供"只读浏览 + 展开"的能力即可。
