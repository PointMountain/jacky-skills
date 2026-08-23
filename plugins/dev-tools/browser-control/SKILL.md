---
name: browser-control
description: 本地 AI 浏览器操控的唯一通用入口。用于打开或操作网页、预览本地静态页、调试前端、读取当前登录页，以及判断该选哪个浏览器工具；按是否需要复用已有登录态路由，优先以 ego-ops 治理可复用网页操作，并记录有证据的实际能力与复盘。
---

# AI 浏览器操控

本 Skill 是本地 AI 浏览器操控的唯一通用入口。这里只判断、探测、委派、验收和记录，不复制下游浏览器的操作手册，也不自行实现 CDP。

纯搜索、发现信息来源或网络调研交给 `web-search`；业务 Skill 在自身封闭流程中已经选定浏览器时，不必绕回本入口。

## 核心路由

先判断任务是否只是搜索；浏览器任务的第一路由键始终是：**是否需要复用已有登录态**。

1. 只是搜索或发现信息：委派 `web-search`，不进入浏览器 provider 选择。
2. 需要已有 Cookie、账号会话、内部系统、当前已登录标签页：选择 `browser_with_existing_login`。先使用 Codex 自带的 Browser Control（`@Chrome`）控制用户现有 Chrome；主能力不可用或主路径失败时，自动回退 `ego-ops`，由它使用 Ego 浏览器复用登录态、验证结果并沉淀成功经验。
3. 不需要已有登录态：选择 `browser_without_existing_login`，优先 Chrome DevTools。
4. 用户没有明确说明、且选错会改变结果时，先查本地登录态记录；没有命中时只问用户“这个链接是否必须复用当前 Chrome 的已有登录态？”得到回答后才能选择槽位。

不能仅根据 URL、IP 地址、路由名称、页面可达性或“看起来像公开网页”推断无需登录态；用户提供链接也不等于授权使用隔离浏览器。只有本地静态页、`file://`、`localhost` 等上下文本身足以确定时，才可记为 `intrinsic_context`。**不能仅因页面是 SPA 或需要 JS 渲染就改变槽位或调用 WebAccess**。

用户当前明确说明始终覆盖本地记录和历史观察。不得先用隔离浏览器打开目标页，再把看到登录页作为选择错误槽位的补救方式。

Codex Browser Control 普通模式已经验证可复用现有登录态并读取增量 Console 与 Network；默认保持“完整 CDP”关闭。执行入口是环境内置的 `chrome:control-chrome` Skill，其底层由当前 Codex 会话连接 Chrome，但不应被描述为需要另装或改用 WebAccess。内部使用调试器能力不等于必须开启产品设置中的“完整 CDP”。普通模式无法完成时先回退 `ego-ops`，不要为了 WebAccess 启动需要用户现场确认的 CDP 调试链路。

## WebAccess 禁用规则

`web-access` 不属于 `browser-control` 的 provider、fallback 或预检对象。不得自动加载、探测或调用它，也不得以“外部后备已授权”为由恢复旧路由。原因是它依赖用户现场确认浏览器调试状态，无法满足默认自动化与可复用执行要求；对应能力统一由 `ego-ops` 与 Ego 浏览器承担。只有用户明确脱离本 Skill、单独要求使用 WebAccess 时，才按 WebAccess 自身流程处理，该例外不得写回本 Skill 的路由账本。

## 运行流程

### 1. 确认并记录登录态

先从已加载的 `SKILL.md` 定位本 Skill 目录，把脚本解析为绝对路径；不要假定当前工作目录就是 Skill 目录。对 HTTP(S) 链接，用以下本地注册表查询精确 URL 指纹：

```bash
node "<browser-control 的绝对路径>/scripts/login-state-registry.mjs" lookup <<'JSON'
{"url":"<目标 URL>"}
JSON
```

注册表未命中且用户没有明确说明时，先询问用户。确认后立即记录：

```bash
node "<browser-control 的绝对路径>/scripts/login-state-registry.mjs" record <<'JSON'
{"url":"<目标 URL>","needsExistingLogin":true,"source":"user_confirmation"}
JSON
```

注册表只保存 SHA-256 指纹、布尔判断、判断来源和时间，不保存原始 URL。相同链接可复用记录；不同链接或用户当前说法冲突时重新确认。允许的账本判断来源：

- `user_confirmation`：Agent 询问后由用户确认。
- `explicit_request`：用户原始请求已明确说明是否复用登录态。
- `local_record`：精确 URL 指纹命中本地记录。
- `intrinsic_context`：`file://`、本地静态页等上下文足以确定。

### 2. 建立本轮账本

生成不含目标名称、URL 或账号信息的 `run-id`，只允许小写字母、数字和连字符。先从已加载的 `SKILL.md` 定位本 Skill 目录，并把脚本解析为绝对路径；不要假定当前工作目录就是 Skill 目录：

```bash
node "<browser-control 的绝对路径>/scripts/usage-ledger.mjs" init <run-id>
```

立即填写 `runs.local/<run-id>.md` 中的任务类型、是否需要已有登录态、`登录态判断来源` 和候选。不能把 Agent 猜测写成任何合法来源。每个实际调用的下游 Skill 都必须保留独立条目；主候选失败后走 fallback 时，不得覆盖失败事实。

### 3. 只读所需能力槽位

读取 [`references/capabilities.md`](references/capabilities.md) 中与本轮相符的一个二级标题：

- 无已有登录态：`browser_without_existing_login`
- 有已有登录态：`browser_with_existing_login`
- 搜索与发现：`web_information_discovery`

如存在 `experience.local.md`，只读相关候选的当前能力卡和少量已晋升经验。它是本机能力地图，不是逐次流水。

### 4. 运行确定性路由器

每次探测或调用任何 provider 前，必须重新运行路由器。只能执行路由器本次返回的 provider，不得凭自然语言规则手工跳过高优先级候选：

```bash
node "<browser-control 的绝对路径>/scripts/route-provider.mjs" <<'JSON'
{
  "slot": "browser_with_existing_login",
  "providers": {
    "codex-browser-control": {
      "status": "not_checked",
      "attempt": "not_attempted"
    }
  }
}
JSON
```

路由状态分为两条独立轴：

- `status` 表示探测结果，只能是 `not_checked | available | degraded | missing`。
- `attempt` 表示任务调用结果，只能是 `not_attempted | passed | degraded | failed`；只有 `available` 的 provider 可以带任务结果。

严格处理路由器输出：

- `probe`：只探测返回的 provider，更新 `status` 后重新运行路由器。
- `use`：只调用返回的 provider，更新 `attempt` 后重新运行路由器。
- `complete`：该 provider 已完成可交付路径；可能是完整通过，也可能是局部证据降级，停止 fallback 并进入证据验收。
- `blocked`：候选已耗尽，停止调用并报告阻断原因。

登录态槽位的固定优先级是 `codex-browser-control → ego-ops`。不得向路由器传入旧字段 `allowExternalFallback`，也不得登记 `web-access` provider；路由器会直接拒绝。只有 Codex Browser Control 真正 `missing`、整体 `degraded`、被权限阻断或任务调用 `failed` 时，才探测并使用 `ego-ops`。

Codex Browser Control 的页面操作已完成、但局部 Console、Network、键盘或其他证据接口降级时，把任务结果记为 `attempt: degraded`。路由器仍返回 `complete`；如实报告证据缺口和置信度，不自动切换其他能力。

### 5. 最小探测与同槽位降级

首次使用、能力卡过期或候选调用失败时，执行能力地图规定的最小 probe。候选状态只允许：

- `available`
- `degraded`
- `missing`
- `not_checked`

探测状态与任务结果分开记录；任务失败不代表 provider `missing`。Chrome DevTools 不可用时，只能尝试同一无登录态槽位的 `browser:control-in-app-browser`，不得静默借用登录态槽位。

已有登录态槽位先探测当前会话是否真正暴露 `@Chrome`，不能仅凭本机安装了扩展就判定可用。若 Codex Browser Control 完成主要用户路径但缺少部分辅助证据，留在主能力并降级报告。只有它真正不可用或主路径失败时，才由路由器进入 `ego-ops`；Ego Ops 必须实时复核目标登录态，不能把未经验证的隔离会话假装成同一登录态。

### 6. 委派并用证据验收

按路由器返回值加载实际候选，不预读所有下游 Skill。路由器返回 `codex-browser-control` 时，加载环境内置的 `chrome:control-chrome`，并按其浏览器选择与连接协议使用 Codex 自带 Browser Control；需要明确锁定用户 Chrome 时使用 `@Chrome`。路由器返回 `ego-ops` 时，加载 `ego-ops`，由它按站点 operation、授权边界、Ego 浏览器任务空间和成功后写回协议完成任务。不得从本流程加载 WebAccess 或经 `web-connect` 间接进入 WebAccess。

不能把下游的“成功”文本当成唯一证据。按槽位输出契约验证可观察结果，并在“证据”章节登记：

- 证据类型只能是 `artifact | test | observation | user_confirmation`。
- 引用只能是本轮证据 ID、`run://` 引用或 `runs.local/` 内相对引用。
- “证明”写可证伪的短结论，不复制页面正文。

登录态 E2E 额外使用增量验收：

1. 操作前记录 Console 与 Network 基线。
2. 执行用户路径后验证路由或可见页面状态。
3. 只比较本次操作新增的 Console 与 Network。
4. 新增 Console error 或失败的 XHR/Fetch 默认判定为失败；已存在的 warning 记录为基线，不归因给本次操作。
5. 页面跳转成功不代表 E2E 通过，必须同时报告页面、Console 与 Network 三类结果。

### 7. 校验、复盘与归档

完成、降级或失败都要填写“复盘”：总体结果、有效模式、已验证根因、下次规则候选和建议归宿。随后运行：

```bash
node "<browser-control 的绝对路径>/scripts/usage-ledger.mjs" validate <run-id>
node "<browser-control 的绝对路径>/scripts/usage-ledger.mjs" finalize <run-id>
```

`finalize` 只根据候选探测及其证据更新 `experience.local.md` 的当前能力卡；不会从任务结果反推可用性。

## 安全门

- 只读动作可继续：打开、截图、读取结构、滚动、展开、切换视图、查看控制台和网络信息。
- 任何可能改变服务器、账号或持久数据的动作必须先获得用户确认，包括提交、保存、删除、授权、支付、上传和发送消息。
- 写账本前由 AI 做语义脱敏；不得保存真实 URL、内部域名、页面正文、Cookie、请求头、账号、密钥、令牌或个人信息。
- Node 扫描只是确定性兜底，不能替代语义脱敏；扫描失败时先修正记录，不能绕过校验。
- 只关闭本轮新开的标签页，不关闭用户原有标签页。

## 经验分层

- `runs.local/<run-id>.md`：每次真实使用的事实、证据与复盘，一轮一篇。
- `experience.local.md`：最近一次有证据的本机能力状态，以及已经晋升的可复用经验。
- `SKILL.md` / `references/`：经过重复验证、跨环境成立的共享稳定规则。

单次成功或失败只留在运行复盘；有明确根因、会改变下次决策且有证据的结论才成为经验候选。重复验证后再更新共享规则，禁止自动重排 provider 或改写下游 Skill。

## 完成清单

- [ ] 已按“是否需要已有登录态”选择能力槽位，且没有把 SPA/JS 当成登录态。
- [ ] URL 登录态不明确时已查询本地指纹记录或询问用户，账本已填写合法的登录态判断来源。
- [ ] 每次 provider 探测或调用前都已执行 `route-provider.mjs`，且只执行其返回的 provider。
- [ ] 已有登录态槽位按 `codex-browser-control → ego-ops` 路由；局部证据接口降级没有触发不必要的 fallback，且没有用“本机已安装”代替“当前会话可调用”。
- [ ] 本轮没有加载、探测、直接或间接调用 WebAccess，也没有使用已废弃的外部后备授权字段。
- [ ] 每个被考虑的候选都有独立探测状态，所有实际下游链与 fallback 均已保留。
- [ ] 结果有可观察证据，不依赖自报成功。
- [ ] 写操作已过安全门，账本不含敏感内容。
- [ ] `validate` 与 `finalize` 已成功，本轮复盘说明是否值得晋升经验。
