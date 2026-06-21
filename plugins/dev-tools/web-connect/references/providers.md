# Provider 接入参考

web-connect 是**能力层**，不绑定具体工具。本文件定义"能用 CDP 读/控网页"的**能力契约**，并给出各 provider 的精确接入命令。SKILL.md 主流程默认走 web-access；用别的 provider 或需要一次性配置/安装引导时读这里。

---

## 一、能力契约

任何 provider 满足下表即可接入（标 ★ 为强烈推荐，缺失会明显降低体验）：

| 能力 | 说明 | web-access | agent-browser | opencli |
|------|------|:----------:|:-------------:|:-------:|
| health/connect | 确认能连上 CDP | ✅ `/health` | ✅ `--cdp` | ✅ daemon |
| list-tabs | 列出已打开 tab | ✅ `/targets` | ✅ | ✅ |
| focus-tab ★ | 判定/锁定当前活动 tab | ⚠️ 需 eval 判定 | ⚠️ | ⚠️ |
| navigate/new | 打开 URL | ✅ `/new` `/navigate` | ✅ `open` | ✅ `open` |
| screenshot | 截图到文件 | ✅ `/screenshot` | ✅ `screenshot` | ✅ `screenshot` |
| read-text/dom ★ | 读文本/DOM | ✅ `/eval` | ✅ `get text/html` | ✅ `extract` |
| list-interactives ★ | 提取可交互元素 | ⚠️ 手写 eval | ✅ `snapshot -i` | ✅ `state` |
| eval ★ | 跑任意 JS | ✅ `/eval` | ⚠️ 有限 | ⚠️ 有限 |
| click | 点击/展开 | ✅ `/click` `/clickAt` | ✅ | ✅ `click` |
| scroll | 滚动触发懒加载 | ✅ `/scroll` | ✅ | ✅ |
| close | 关自己的 tab | ✅ `/close` | ✅ | ✅ `close` |

---

## 二、Provider 1：web-access（首版一等公民）

来源：GitHub `eze-is/web-access`（v2.5.x）。底层是一个 `cdp-proxy` Node 进程，把 Chrome 的 CDP 暴露成 `http://localhost:3456` 的 HTTP API，**直连用户日常 Chrome，天然复用登录态**。

### 2.1 一次性配置（唯一门槛）

```bash
# ① 让 Chrome 开调试端口（二选一）
#   a) 命令行启动（macOS）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
#   b) 已运行的 Chrome：地址栏打开 chrome://inspect/#remote-debugging，勾选 Allow，按需重启

# ② 起 cdp-proxy（脚本路径按实际安装位置，存在哪个用哪个）
node "${CLAUDE_SKILL_DIR}/scripts/check-deps.mjs"            # skill 框架管理时
node ~/.claude/skills/web-access/scripts/check-deps.mjs       # 装到用户目录时
```
- proxy 监听 `3456`（可用环境变量 `CDP_PROXY_PORT` 改）；Chrome 端口经 `DevToolsActivePort` 文件自动发现，回退扫描 `9222/9229/9333`。
- 需 **Node ≥ 22**（原生 WebSocket）；低于 22 需 `npm i -g ws`。
- 停止：`pkill -f cdp-proxy.mjs`；端口占用排查：`lsof -i :3456`。

### 2.2 端点速查表

| 端点 | 方法 | 参数 / body | 返回 |
|------|------|-------------|------|
| `/health` | GET | — | `{status,connected,sessions,chromePort}` |
| `/targets` | GET | — | `[{targetId,title,url,type}]`（**无 active 字段**）|
| `/new` | GET | `?url=` | `{targetId}` |
| `/navigate` | GET | `?target=&url=` | `{frameId,loaderId}` |
| `/back` | GET | `?target=` | `{ok}` |
| `/info` | GET | `?target=` | `{title,url,ready}` |
| `/eval` | POST | `?target=` + body=JS | `{value}` / `{error}` |
| `/click` | POST | `?target=` + body=CSS选择器 | `{clicked,tag,text}` |
| `/clickAt` | POST | `?target=` + body=CSS选择器 | `{clicked,x,y,tag,text}`（真实鼠标手势）|
| `/setFiles` | POST | `?target=` + body=`{selector,files[]}` | `{success,files}` |
| `/scroll` | GET | `?target=&y=&direction=down\|up\|top\|bottom` | `{value}` |
| `/screenshot` | GET | `?target=&file=&format=png\|jpeg` | `{saved}` 或二进制 |
| `/close` | GET | `?target=` | `{success}` |

### 2.3 关键注意
- **eval 返回值必须可序列化**：DOM 节点不能直接返回，要取属性；批量数据用 `JSON.stringify()` 包裹。eval 超时 30s，`/new`·`/navigate` 自动等加载（15s）。
- **当前活动 tab 判定**：`/targets` 无 active 字段 → 遍历对每个 tab `/eval document.visibilityState`，取 `"visible"` 者；兜底 `document.hasFocus()`。
- **`/click`（JS 点击，isTrusted=false）** 适合展开/折叠/普通交互；**`/clickAt`（真实鼠标）** 用于需要用户手势或触发文件对话框的场景。
- iframe / Shadow DOM 的 CSS 选择器不能直接穿透，用 eval 递归遍历或 `contentDocument` / `shadowRoot`。
- 风险提示（web-access 官方）：部分站点对自动化检测严格，存在账号风险；已内置端口探测拦截，但密集 `/new` 仍可能触发反爬。

---

## 三、Provider 2：agent-browser

命令最简洁，自动给元素 ref（`@e1`）。连已有 Chrome：

```bash
agent-browser --cdp 9222 screenshot /tmp/page.png   # 截图
agent-browser --cdp 9222 snapshot -i --json         # 交互元素树（含 role/label）
agent-browser --cdp 9222 get text body              # 整页文本
agent-browser --cdp 9222 get html @e5               # 某元素 HTML
# 连接方式：--cdp 9222 / connect 9222 / --auto-connect（自动扫描调试端口）
```
安装：`npm i -g agent-browser`（v0.26+）。优势：`snapshot -i` 免手写 JS；劣势：默认起独立浏览器，连日常 Chrome 需带 `--cdp`。

---

## 四、Provider 3：opencli browser

```bash
opencli browser mywork open https://admin.example.com   # 开会话（自动起 daemon）
opencli browser mywork state                            # 页面状态 + 可交互元素 ref 列表
opencli browser mywork click 12                         # 点第 12 个元素
opencli browser mywork extract                          # 导出页面 Markdown
opencli browser mywork screenshot /tmp/shot.png
opencli browser mywork close
```
已装 OpenCLI 时的便捷选择，命令式、ref 自动生成。

---

## 五、一个 provider 都没有时

**不要中止**，给用户列出选项：

1. **web-access**（推荐，最贴合"看当前页"）：安装 `eze-is/web-access` 到 `~/.claude/skills/`，需 Node ≥ 22。
2. **agent-browser**：`npm i -g agent-browser`，命令最简单。
3. **opencli**：已装 OpenCLI 即可用 `opencli browser`。
4. **自建**：按 `references/diy-cdp-server.md` 写一个最小 CDP server，满足第一节能力契约即可。

让用户选其一，装好后回到 SKILL.md Phase 0 重新探测。
