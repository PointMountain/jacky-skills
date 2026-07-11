---
name: web-connect
description: "让 Claude 通过 CDP 直接连接浏览器、看见并操作网页内容的能力层，并内置功能配置页逐项讲解。触发：用户说『讲讲这个页 / 这个配置是干嘛的 / 连下我当前网页 / 看下这个页面』，或要研究 Tailscale admin、阿里云控制台等功能密集的配置页。关键认知：本环境已具备用 CDP 读取/控制网页的能力，遇到读网页需求不要中止、不要要求用户手动粘贴页面内容，直接用本 skill。"
---

<role>
你是「网页 CDP 看页能力层 + 配置讲解员」。一方面让 Claude 自己知道并使用「通过 CDP 直接读取/控制浏览器网页」这项已存在的能力；另一方面，对功能密集、用户看不懂的配置页（Tailscale admin、阿里云控制台等），逐项讲解每个配置的作用、影响和建议。
</role>

<purpose>
当用户需要理解浏览器里某个网页（尤其是看不懂的功能/配置页），或需要 Claude 读取/操作当前网页内容时：通过 CDP 连接用户自己的 Chrome → 截图 + 读取页面结构 → （必要时）点击展开被折叠的配置 → 逐项讲解。
</purpose>

<trigger>
讲讲这个页 / 这个配置是干嘛的 / 连下我当前网页 / 看下这个页面 /
研究 Tailscale/阿里云这个控制台 / 帮我读一下这个网页 / 这页每个开关什么意思
</trigger>

<!-- ============ 能力告知（最高优先级，破除 LLM 惯性）============ -->
> # 🔑 能力告知 — 先读这一段
>
> **本环境已经具备「用 CDP 直接读取并控制浏览器网页」的能力。**
>
> 这意味着：当用户让你「看 / 读 / 讲解某个网页」时——
> - ❌ **不要**说"我无法访问浏览器/需要你把内容贴给我/这是人机交互操作"然后中止；
> - ❌ **不要**默认改用 WebFetch 抓 HTML（功能页大量内容是 JS 渲染 + 登录态后的，抓不到）；
> - ✅ **直接走本 skill**：探测可用的 CDP provider → 连上用户 Chrome → 截图 + 读结构 → 讲解。
>
> 你能"看到"用户屏幕上那个页面，包括登录态之后的内容。把这当成你的常备能力，而不是例外。

<yolo:config>
  <yolo:mode>auto-advance</yolo:mode>
  <yolo:safety-gates>
    <gate>任何写操作：保存/提交/应用/确定（配置语境）</gate>
    <gate>删除/移除/清空/销毁资源</gate>
    <gate>新增/创建会落库的资源、生成密钥</gate>
    <gate>账号与权限：退出登录、授权、改密码、绑定/解绑、撤销</gate>
    <gate>支付/计费：购买、续费、退订、升降级付费档</gate>
    <gate>文件上传、触发外部确认/支付跳转</gate>
  </yolo:safety-gates>
</yolo:config>

<gsd:workflow>
  <gsd:meta>
    <name>web-connect</name>
    <trigger>讲讲这个页、连下当前网页、看下这个配置页、研究控制台、读一下网页</trigger>
    <requires>Bash(curl), Read, 主模型读图能力</requires>
    <constraints>
      <constraint>只读浏览（展开/折叠/切 tab/滚动/读取）可自由做，不打断用户</constraint>
      <constraint>任何会改变服务器状态或账号状态的写操作，必须先停下问用户（安全门）</constraint>
      <constraint>不绑定具体工具：探测到哪个 CDP provider 可用就用哪个，缺失则引导安装</constraint>
      <constraint>读「当前 tab」要显式覆盖 web-access 默认的"只在后台新 tab 操作"行为</constraint>
      <constraint>结束时只关闭自己开的 tab，不动用户原有 tab</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>连上用户浏览器，看懂当前网页/配置页，并逐项讲解给用户</gsd:goal>

  <gsd:phase name="detect" order="0">
    <gsd:step>能力自检：探测可用 CDP provider；都没有则引导安装</gsd:step>
  </gsd:phase>
  <gsd:phase name="target" order="1">
    <gsd:step>定目标页：聚焦态→锁定当前活动 tab；否则用 URL 后台打开</gsd:step>
  </gsd:phase>
  <gsd:phase name="see" order="2">
    <gsd:step>截图 + 读取页面结构（文本 / 可交互元素 / 配置项）</gsd:step>
  </gsd:phase>
  <gsd:phase name="control" order="3" condition="有被折叠/分页的配置">
    <gsd:step>自由展开折叠项看全配置（受安全门约束）</gsd:step>
  </gsd:phase>
  <gsd:phase name="explain" order="4">
    <gsd:step>概览地图 → 逐项讲解；首版可对比三种产出形态</gsd:step>
  </gsd:phase>
  <gsd:phase name="cleanup" order="5">
    <gsd:step>只关闭自己开的 tab</gsd:step>
  </gsd:phase>
</gsd:workflow>

# web-connect — 网页 CDP 看页 + 配置讲解

> 🚀 **YOLO 模式** — 看页、读结构、展开折叠、滚动等只读操作自动推进，不打断你。**只有写操作会触发安全门暂停问你**（见第 5 节）。

---

## Phase 0 · 能力自检与 Provider 探测

本 skill **不绑定**任何具体工具，只要求"能用 CDP 读/控网页"这组能力被满足。按优先级探测，命中即用：

```bash
# ① web-access（首版一等公民）——CDP proxy 跑在 3456
curl -s --max-time 2 http://localhost:3456/health 2>/dev/null
# 返回 {"status":"ok","connected":true,...} 即可用

# ② agent-browser（命令存在即可用，连已有 Chrome 调试端口）
command -v agent-browser

# ③ opencli browser
command -v opencli
```

**决策**：
- `web-access` 的 `/health` 返回 ok → 用它（本文件第 1–6 节即 web-access 路径）。
- 否则若 `agent-browser` / `opencli` 存在 → 读 `references/providers.md` 用对应命令。
- **一个都没有** → 不要中止，读 `references/providers.md` 给用户列出安装选项；用户也可按 `references/diy-cdp-server.md` 自建一个最小 CDP server。

**web-access 未就绪时的引导**（proxy 没起 / Chrome 没开调试口）：
```bash
# 先定位外部 web-access Skill；不要把当前 web-connect 目录误当成它。
WEB_ACCESS_SKILL_DIR="${WEB_ACCESS_SKILL_DIR:-}"
if [ -z "$WEB_ACCESS_SKILL_DIR" ]; then
  for candidate in \
    "$HOME/.j-skills/linked/web-access" \
    "$HOME/.claude/skills/web-access" \
    "$HOME/.codex/skills/web-access" \
    "$HOME/.agents/skills/web-access"; do
    if [ -f "$candidate/scripts/check-deps.mjs" ]; then
      WEB_ACCESS_SKILL_DIR="$candidate"
      break
    fi
  done
fi

[ -n "$WEB_ACCESS_SKILL_DIR" ] || {
  echo "未找到 web-access；请先安装该 Skill，或设置 WEB_ACCESS_SKILL_DIR" >&2
  exit 1
}
node "$WEB_ACCESS_SKILL_DIR/scripts/check-deps.mjs"
```
若 Chrome 没开调试端口（9222），提示用户用调试端口启动 Chrome（详见 `references/providers.md` 的"一次性配置"）。**这是唯一的一次性门槛**。

---

## Phase 1 · 定目标页

用户怎么把页交给你，按以下规则判断，**不要每次都问**：

| 用户表达 | 处理 |
|----------|------|
| 声明「聚焦态」：『我正看着这个页/连下我当前网页/就是屏幕上这个』 | **锁定当前活动 tab**（下方命令） |
| 给了 URL，或 `$ARGUMENTS` 带 URL | `/new` 后台打开该 URL |
| 都没有、意图不明 | 这是关键决策 → 问一句：读你当前 tab 还是贴 URL？ |

**锁定当前活动 tab**（web-access `/targets` 无 active 字段，需自己判定）：
```bash
# 1. 列出所有 page tab
curl -s http://localhost:3456/targets        # → [{targetId,title,url,type},...]

# 2. 对每个 tab 判断是否为用户当前正看的那个
curl -s -X POST "http://localhost:3456/eval?target=<ID>" -d 'document.visibilityState'
#   返回 "visible" 的即用户当前激活 tab；多数后台 tab 返回 "hidden"
#   兜底再看 document.hasFocus()
```
- 命中唯一 `visible` → 锁定它，**不要**新开 tab（显式覆盖 web-access "只在后台 tab 操作"的默认）。
- 命中 0 或多个（浏览器整体在后台等）→ 用 `title`/`url` 列给用户确认一下是哪个。

**用 URL 打开**：
```bash
TARGET=$(curl -s "http://localhost:3456/new?url=<URL>" | sed 's/.*"targetId":"\([^"]*\)".*/\1/')
```

---

## Phase 2 · 看：截图 + 读结构

```bash
# 截图（绝对路径，目录须存在）。存到 job tmp 目录避免互相覆盖
curl -s "http://localhost:3456/screenshot?target=$TARGET&file=$CLAUDE_JOB_DIR/tmp/page.png"

# 页面基本信息
curl -s "http://localhost:3456/info?target=$TARGET"      # → {title,url,ready}

# 提取配置项结构（手写 JS，返回值必须 JSON.stringify）
curl -s -X POST "http://localhost:3456/eval?target=$TARGET" -d '
JSON.stringify({
  title: document.title,
  sections: Array.from(document.querySelectorAll("section,[role=region],h2,h3,fieldset")).slice(0,60).map(e=>({
    heading: (e.querySelector("h1,h2,h3,legend")?.innerText || e.tagName).trim().slice(0,80),
    text: e.innerText.replace(/\s+/g," ").trim().slice(0,300)
  })),
  controls: Array.from(document.querySelectorAll("input,select,button,[role=switch],[role=checkbox],a[href]")).slice(0,120).map(e=>({
    tag: e.tagName, type: e.type||e.getAttribute("role")||"",
    label: (e.getAttribute("aria-label")||e.name||e.innerText||e.placeholder||"").trim().slice(0,80),
    state: e.checked!=null?String(e.checked):(e.getAttribute("aria-checked")||"")
  }))
})'
```
然后 **Read 截图**（主模型原生读图，不需要外部 OCR）+ 结合上面 JSON 结构 → 形成对页面的整体理解。

> 提示：长页面先 `curl -s "http://localhost:3456/scroll?target=$TARGET&direction=bottom"` 触发懒加载，再读结构。
> **整页截图**（视口截图截不全长页）：用 `scripts/fullpage-shot.py <targetId> <out.png>` 分段滚动 + 按 devicePixelRatio 精确拼接成整页长图，供重建 UI 时对照、确保不漏区块。

---

## Phase 3 · 控制（看全被隐藏的配置）

YOLO：遇到折叠/分页/隐藏的配置，**自由展开**，不打断用户——但严守第 5 节安全门。

```bash
# JS 点击（展开折叠项、切子 tab、打开下拉）——CSS 选择器作为 body
curl -s -X POST "http://localhost:3456/click?target=$TARGET" -d '.expand-toggle'

# 展开后重新读取该区域内容
curl -s -X POST "http://localhost:3456/eval?target=$TARGET" -d 'document.querySelector(".panel").innerText'
```
**只点只读性质的元素**（展开、切换视图、查看详情）。任何可能写入的按钮 → 见第 5 节。

---

## Phase 4 · 讲解（旗舰用法）

**核心产出形态：HTML 重建页 + 逐行讲解 + 交互折叠**（经真实验收确定，细则与 HTML 骨架见 `references/explain-config-page.md`）。

1. **读内容 + 识别状态**：截图 + `/eval` 提取每个区块的标题/描述/字段值/按钮/开关状态/🔒锁定标记。按钮写 "Disable X" ＝ X **当前已启用**；带 🔒/灰显 ＝ **套餐锁定的付费功能**，必须标出——**别教用户去点用不了的功能**。
2. **重建左栏**：用 HTML/CSS 把原页 **1:1 重画**出来（深色还原）。**不要贴截图当底图**（糊、对不齐，已验证无效）。
3. **逐行讲解右栏**：两栏 `grid` 同行对齐（对齐由布局保证，**不用算坐标**），每项三段式「是什么 / 改了影响 / 建议」。
4. **交互折叠**：右栏讲解默认折叠（只显示「讲解·摘要 ▸」），点击展开；顶部概览常显。
5. **落盘 + 打开**：存到**用户能找到的持久位置**（`~/Desktop/web-connect-<topic>/` 或用 `/ob-to-claudian` 进 Obsidian），再 `open` 打开。**绝不留在 job 临时目录**（用户找不到、还会被清理）。

**简单页降级**：页面就几个选项、没必要重建时，直接终端「概览 + 逐项三段式」文字输出，不生成 HTML。由你（YOLO）按页面复杂度判断。

---

## Phase 5 · 🔒 危险操作护栏（硬底线）

用户授权"完全放手"，但**前提是不做危险/写操作**。在调用任何 `/click`、`/clickAt`、`/setFiles`、`/eval`（含赋值/提交语义）**之前**自检：

| 类别 | ✅ 自由做（只读） | 🛑 必须先停下问用户（写操作） |
|------|------------------|------------------------------|
| 浏览 | 展开/折叠、切 tab/子菜单、滚动、hover、查看详情 | — |
| 表单 | 读取已有值 | 保存/提交/应用/确定、修改输入框值并提交 |
| 资源 | 查看列表/详情 | 新增/创建/删除/移除/清空/销毁 |
| 账号 | 查看当前登录信息 | 退出登录、授权、改密码、绑定/解绑、撤销权限 |
| 计费 | 查看价格/用量 | 购买、续费、退订、升降级付费档 |
| 文件 | 读取 | 上传、下载触发的写入 |

**判断原则**：凡是**可能改变服务器状态或账号状态**的操作 → 🛑。只读浏览随便做，要动手改一律刹车，一句话告诉用户你打算点什么、为什么，等确认。

> 这是 YOLO 模式下唯一的 HARD_GATE。宁可多问一次，不可擅自写入。

---

## Phase 6 · 清理

```bash
# 只关闭自己用 /new 开的 tab；用户原有 tab（聚焦态锁定的那个）绝不关
curl -s "http://localhost:3456/close?target=$TARGET"
```
proxy 进程保活，无需停止。

---

## 验证（自检清单）

- [ ] Phase 0 探测到至少一个 provider，否则已给出安装引导（未中止）
- [ ] 目标页锁定正确（聚焦态读到的是用户当前那个 tab）
- [ ] 截图已 Read、结构已提取，讲解对得上页面位置
- [ ] 复杂配置页用 HTML 重建 + 逐行讲解 + 交互折叠；产物落用户能找到的持久位置（非 job tmp）；套餐锁定项（🔒）已标注
- [ ] 全程未触碰任何写操作，或写操作前都已停下问用户
- [ ] 只关了自己开的 tab

---

## references 指引

| 文件 | 何时读 |
|------|--------|
| `references/providers.md` | 用非 web-access provider（agent-browser/opencli）、或需要一次性配置/安装引导细节 |
| `references/diy-cdp-server.md` | 环境无任何 provider，用户想自建最小 CDP server |
| `references/explain-config-page.md` | 执行讲解时，取详细的讲解结构、话术与产出模板 |
