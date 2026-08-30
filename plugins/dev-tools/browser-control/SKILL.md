---
name: browser-control
description: 本机网页自动化的统一入口。所有网页打开、交互、提取、截图、调试和回归都交由 Ego Ops 治理，并只通过 Ego Lite 的 ego-browser 执行与验证。
---

# Browser Control

本 Skill 只负责确认授权边界、建立最小运行账本、委派 Ego Ops 并验收结果；它不再选择或调用其他浏览器 provider。

## 唯一执行链

```text
Browser Control → Ego Ops → Ego Lite（ego-browser）
```

无论任务是否需要已有登录态，都使用这一条链路。Ego Lite 的 Agent task space 会隔离 Agent 标签页，同时复用当前用户登录态；每次任务仍须在当前页面实时复核登录、权限、目标对象和成功标准。

## 已移除的路径

以下工具不属于本机网页自动化方案，不能作为 provider、fallback、预检或间接依赖加载：

- Agent Browser
- WebAccess / Web Access
- OpenCLI 的 `browser` 子命令与 `web` adapter
- Chrome DevTools、Codex Browser Control、in-app browser
- Playwright CLI（仅在用户明确要求运行项目测试时按测试工具单独处理，不用于真人网页操作）

公开信息检索仍由 `web-search` 处理；只有需要真实页面交互、浏览器状态、截图或 DOM 证据时才进入本 Skill。

## 每次运行

1. 明确目标、允许与禁止动作、风险及成功标准。只读操作可继续；提交、保存、删除、授权、上传、支付、发送消息等动作必须先得到用户确认。
2. 生成脱敏 `run-id`，初始化账本：

```bash
node "<browser-control 的绝对路径>/scripts/usage-ledger.mjs" init <run-id>
```

3. 读取 [`references/capabilities.md`](references/capabilities.md) 的唯一能力卡。每次探测或执行前运行路由器；它只能返回 `ego-ops`：

```bash
node "<browser-control 的绝对路径>/scripts/route-provider.mjs" <<'JSON'
{
  "slot": "browser_automation",
  "providers": { "ego-ops": { "status": "not_checked", "attempt": "not_attempted" } }
}
JSON
```

4. 加载 `ego-ops`。它先读取本机经验，再以 Ego Lite 创建或复用任务空间，遵循“观察 → 行动 → 验证 → 成功后写回”的循环。不得在任务中改走其他浏览器工具。
5. 用可观察证据验收：页面状态、目标动作结果、必要的截图/DOM/网络观察，或用户确认。provider 自报成功不算唯一证据。
6. 用一次 `complete` 归档脱敏事实；成功且能改变下次决策的结论，由 Ego Ops 写入其本机经验。账本不得存 URL、页面正文、Cookie、请求头、账号、密钥或个人信息。

## 收敛漂移检查

在调整 Skill、CLI、npm 全局包或链接后运行以下脚本。它检查唯一 Ego 路由、退休 Skill/命令、Ego Lite 可达性和 OpenCLI 网页命令保护；任一项失败会以非零状态退出：

```bash
node "<browser-control 的绝对路径>/scripts/verify-ego-only.mjs"
```

追加 `--json` 可供定时任务或其他 Agent 读取。

## Playwright 边界

Playwright 是项目自动化测试工具，不是本机真人浏览器控制方案。用户明确要求项目 E2E 测试时，可以在测试仓库内运行其既有 Playwright 命令；该测试流程不能借用、读取或复用 Ego Lite 的用户会话，也不能反向成为 Browser Control 的 fallback。

## 完成清单

- [ ] 已按用户授权限定动作，风险操作已确认。
- [ ] 本轮路由与实际链路均为 `browser-control → ego-ops → ego-browser`。
- [ ] Ego Lite 已实时复核页面前提并以可观察结果验证。
- [ ] 已清理或按用户要求保留 Ego Lite task space。
- [ ] 已归档脱敏运行事实；只有有证据且可复用的结论才沉淀到 Ego Ops 本机经验。
