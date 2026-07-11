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

- 主候选：`web-access:web-access`（WebAccess），通过 CDP 复用用户现有浏览器会话。
- 专用适配：讲解当前 tab、当前页或功能密集的配置页时，可经 `dev-tools:web-connect` 组织目标页锁定、结构读取和配置讲解；实际浏览器能力仍由 WebAccess 提供。
- 最小 probe：先检查 WebAccess 健康状态和现有浏览器连接；只有用户明确要求当前页时才以只读方式定位当前 tab。
- 输入契约：登录态需求、非敏感目标描述、意图、允许动作和所需证据类型；不得把 Cookie 或凭据写入输入记录。
- 输出契约：实际链路、页面状态、动作结果、失败原因和脱敏证据引用。经适配层时分别记录 `web-connect` 与 WebAccess。
- fallback：只能使用能明确复用同一已有会话的候选；没有经过验证的同槽位候选时报告阻断，不得改用隔离浏览器假装完成。
- 验收：取得只有目标会话下才成立的页面状态或用户确认，同时不得记录内部 URL、页面正文或身份信息。

## web_information_discovery

适用：用户目标是搜索、调研、发现来源或比较公开信息，而不是操作一个浏览器页面。

- 委派：`dev-tools:web-search`。
- 最小 probe：无浏览器 provider probe；由 `web-search` 按自身搜索降级链检查工具。
- 输入契约：查询目标、时间或来源约束、期望输出。
- 输出契约：来源与结论，或需要升级为真实浏览器任务的明确原因。
- fallback：当搜索流程确实需要浏览器交互时，重新委派 `browser-control`，由它依据是否需要已有登录态选择槽位；`web-search` 不自行比较 CDP provider。
- 验收：搜索结论有来源支撑；如升级浏览器，浏览器证据记录在新的 browser-control 运行账本中。
