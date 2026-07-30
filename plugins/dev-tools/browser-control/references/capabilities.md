# Browser Control 能力地图

本文件只定义稳定槽位、候选顺序、最小探测和验收契约，不承诺候选在当前机器可用。每次只读取与本轮任务相符的一个二级标题。

## browser_without_existing_login

适用：本地静态页、`file://`、`localhost`、公开网页、截图、DOM 检查、控制台、网络与性能分析，以及不依赖用户现有 Cookie 的交互。SPA 或 JS 渲染不会改变这个槽位。

- 主候选：Chrome DevTools。
- 同槽位 fallback：`browser:control-in-app-browser`，用于 Codex 环境中等价的隔离浏览器控制。
- 禁止降级：Chrome DevTools 不可用时不得回退到 WebAccess，也不得借用已有登录态槽位。
- 最小 probe：确认候选能够创建或连接一个无需登录态的页面，并返回页面标题或结构快照；不要用真实目标页面做安装探测。
- 输入契约：非敏感目标引用、意图、允许动作和所需证据类型。
- 输出契约：实际页面状态、动作结果、失败原因和可登记的非敏感证据引用。
- fallback 条件：主候选为 `missing`、`degraded` 且无法完成所需动作，或调用失败；必须保留主候选事实，再探测同槽位候选。
- 验收：至少取得与目标一致的结构、截图、控制台/网络观察或用户确认之一；provider 自报成功不算唯一证据。

## browser_with_existing_login

适用：必须复用当前浏览器 Cookie、账号会话、内部系统权限或当前已登录页面的任务。

- 唯一默认候选：Codex Browser Control（路由 ID `codex-browser-control`，执行 Skill `chrome:control-chrome`，需要明确锁定 Chrome 时使用 `@Chrome`）。这是 Codex 自带的 Chrome 控制能力，复用用户当前 Chrome Profile、现有登录态和标签页。默认保持“完整 CDP”关闭；普通模式已验证能够执行页面交互并读取增量 Console 与 Network。
- 主候选前提：必须在当前会话中真正暴露 `@Chrome`，且目标 Chrome Profile 已安装并启用扩展。仅发现本机安装文件、桌面端插件或其他会话曾成功，不代表本轮 `available`。
- 主候选最小 probe：确认 `@Chrome` 可调用，并以只读方式取得目标登录会话才成立的页面状态。E2E 任务还要在交互前建立 Console 与 Network 基线。
- 降级解释：页面主路径可完成、但局部 Console、Network、键盘或其他证据接口降级时，Codex Browser Control 仍然完成本轮；记录证据缺口和置信度，不得自动切换 WebAccess。
- 可选外部后备：`web-access:web-access`（WebAccess），通过外部 CDP 复用用户现有浏览器会话。它不属于默认依赖；只有 Codex Browser Control 真正 `missing`、整体 `degraded`、被权限阻断或主路径调用 `failed`，并且用户明确允许外部后备后才能启用。
- fallback 最小 probe：检查 WebAccess 健康状态和现有浏览器连接；本地代理请求必须绕过终端全局网络代理。只有用户明确要求当前页时才以只读方式定位当前 tab。
- 专用适配：用户授权并切换到 WebAccess 后，讲解当前 tab、当前页或功能密集的配置页时，可经 `dev-tools:web-connect` 组织目标页锁定、结构读取和配置讲解；实际浏览器能力仍由 WebAccess 提供。
- 输入契约：登录态需求、非敏感目标描述、意图、允许动作和所需证据类型；不得把 Cookie 或凭据写入输入记录。
- 输出契约：实际链路、页面状态、动作结果、失败原因和脱敏证据引用。经适配层时分别记录 `web-connect` 与 WebAccess；不得把扩展内部使用调试器能力误写成已开启“完整 CDP”。
- 禁止降级：只能使用能明确复用同一已有会话的候选；没有经过验证的同槽位候选时报告阻断，不得改用隔离浏览器假装完成。
- 普通交互验收：取得只有目标会话下才成立的页面状态或用户确认，同时不得记录内部 URL、页面正文或身份信息。
- E2E 验收：操作前记录 Console 与 Network 基线；操作后分别报告页面状态、新增 Console、新增 Network 和失败 XHR/Fetch。新增 Console error 或失败 XHR/Fetch 默认使 E2E 失败，既有 warning 只记入基线。

## web_information_discovery

适用：用户目标是搜索、调研、发现来源或比较公开信息，而不是操作一个浏览器页面。

- 委派：`dev-tools:web-search`。
- 最小 probe：无浏览器 provider probe；由 `web-search` 按自身搜索降级链检查工具。
- 输入契约：查询目标、时间或来源约束、期望输出。
- 输出契约：来源与结论，或需要升级为真实浏览器任务的明确原因。
- fallback：当搜索流程确实需要浏览器交互时，重新委派 `browser-control`，由它依据是否需要已有登录态选择槽位；`web-search` 不自行比较 CDP provider。
- 验收：搜索结论有来源支撑；如升级浏览器，浏览器证据记录在新的 browser-control 运行账本中。
