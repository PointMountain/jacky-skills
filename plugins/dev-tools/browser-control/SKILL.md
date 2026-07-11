---
name: browser-control
description: 本地 AI 浏览器操控的唯一通用入口。用于打开或操作网页、预览本地静态页、调试前端、读取当前登录页，以及判断该选哪个浏览器工具；按是否需要复用已有登录态路由，并记录有证据的实际能力与复盘。
---

# AI 浏览器操控

本 Skill 是本地 AI 浏览器操控的唯一通用入口。这里只判断、探测、委派、验收和记录，不复制下游浏览器的操作手册，也不自行实现 CDP。

纯搜索、发现信息来源或网络调研交给 `web-search`；业务 Skill 在自身封闭流程中已经选定浏览器时，不必绕回本入口。

## 核心路由

先判断任务是否只是搜索；浏览器任务的第一路由键始终是：**是否需要复用已有登录态**。

1. 只是搜索或发现信息：委派 `web-search`，不进入浏览器 provider 选择。
2. 需要已有 Cookie、账号会话、内部系统、当前已登录标签页：选择 `browser_with_existing_login`，使用 WebAccess。
3. 不需要已有登录态：选择 `browser_without_existing_login`，优先 Chrome DevTools。
4. 无法判断且选错会改变结果时，只问用户“是否必须复用当前浏览器的已有登录态”。

本地静态页、`file://`、`localhost`、公开网页、截图、DOM、控制台、网络和性能调试通常都不需要已有登录态。**不能仅因页面是 SPA 或需要 JS 渲染就选择 WebAccess**。

## 运行流程

### 1. 建立本轮账本

生成不含目标名称、URL 或账号信息的 `run-id`，只允许小写字母、数字和连字符。先从已加载的 `SKILL.md` 定位本 Skill 目录，并把脚本解析为绝对路径；不要假定当前工作目录就是 Skill 目录：

```bash
node "<browser-control 的绝对路径>/scripts/usage-ledger.mjs" init <run-id>
```

立即填写 `runs.local/<run-id>.md` 中的任务类型、登录态判断和候选。每个实际调用的下游 Skill 都必须保留独立条目；主候选失败后走 fallback 时，不得覆盖失败事实。

### 2. 只读所需能力槽位

读取 [`references/capabilities.md`](references/capabilities.md) 中与本轮相符的一个二级标题：

- 无已有登录态：`browser_without_existing_login`
- 有已有登录态：`browser_with_existing_login`
- 搜索与发现：`web_information_discovery`

如存在 `experience.local.md`，只读相关候选的当前能力卡和少量已晋升经验。它是本机能力地图，不是逐次流水。

### 3. 最小探测与同槽位降级

首次使用、能力卡过期或候选调用失败时，执行能力地图规定的最小 probe。候选状态只允许：

- `available`
- `degraded`
- `missing`
- `not_checked`

探测状态与任务结果分开记录；任务失败不代表 provider `missing`。Chrome DevTools 不可用时，只能尝试同一无登录态槽位的 `browser:control-in-app-browser`，不得静默升级到 WebAccess。

### 4. 委派并用证据验收

按能力地图加载实际候选，不预读所有下游 Skill。登录态下的普通控制直接使用 WebAccess；讲解当前 tab 或功能密集的配置页时，可调用 `web-connect` 作为适配层，由它执行 WebAccess 链路。

不能把下游的“成功”文本当成唯一证据。按槽位输出契约验证可观察结果，并在“证据”章节登记：

- 证据类型只能是 `artifact | test | observation | user_confirmation`。
- 引用只能是本轮证据 ID、`run://` 引用或 `runs.local/` 内相对引用。
- “证明”写可证伪的短结论，不复制页面正文。

### 5. 校验、复盘与归档

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
- [ ] 每个被考虑的候选都有独立探测状态，所有实际下游链与 fallback 均已保留。
- [ ] 结果有可观察证据，不依赖自报成功。
- [ ] 写操作已过安全门，账本不含敏感内容。
- [ ] `validate` 与 `finalize` 已成功，本轮复盘说明是否值得晋升经验。
