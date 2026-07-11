# Browser Control 薄路由 Skill 设计

> 在 DevTools Plugin 中新增浏览器操控唯一入口，并用可审计的运行事实持续校准下游 Skill 的真实能力。

## 背景

当前仓库已经存在多种浏览器相关能力：Chrome DevTools、Codex 内置浏览器、WebAccess、`web-connect`、`web-search` 和若干自动化工具。它们分别解决不同问题，但缺少一个稳定、统一的用户入口，容易出现以下偏差：

- 没有登录态要求时仍启动更重的 WebAccess 链路；
- 需要复用现有 Cookie 或内部系统登录态时误用隔离浏览器；
- 同一能力在多个 Skill 中重复描述，更新后发生漂移；
- 只统计 Skill 是否被调用，没有记录它实际承担了什么能力、结果是否通过以及证据是什么；
- 把当前可用性、逐次运行流水和长期经验全部塞入 `experience.local.md`。

本设计遵循仓库的 [Skills 设计哲学](../../philosophy/README.md)：`SKILL.md` 是地图，外部能力按槽位探测，运行事实与长期经验分离，只有经过证据验证的结论才能晋升为稳定规则。

## 目标

1. 在 `plugins/dev-tools/` 新增 `browser-control`，作为用户发起本地 AI 浏览器操控任务的唯一决策入口。
2. 固化第一路由键：是否需要复用已有登录态。
3. 无登录态任务默认使用 Chrome DevTools；需要已有登录态、Cookie 或内部系统会话时才使用 WebAccess。
4. 保持入口足够薄：只做判断、探测、委派、验收和记录，不复制下游工具说明或重新实现 CDP。
5. 每次真实使用都记录所需能力、实际选择、结果、证据、摩擦和降级，不把“调用次数”误当能力证明。
6. 让运行证据能够逐步校准本机状态，并在满足晋升门槛后形成可复用经验或稳定注册表调整。

## 非目标

- 不新建浏览器自动化服务器、CDP Proxy 或通用工作流引擎。
- 不复制 Chrome DevTools、WebAccess 或 `web-connect` 的完整命令手册。
- 不用本 Skill 取代 `web-search` 的搜索与信息发现职责。
- 不因为一次成功或失败自动重排候选、修改稳定规则或重写下游 Skill。
- 不把所有仓库内的专用浏览器调用一次性迁移；本轮只收口通用用户入口和直接冲突的路由描述。
- 不提交登录态、Cookie、账号、内部 URL、私有页面内容或其他敏感运行事实。

## 复盘与本地经验的通用边界

每个 Skill 都应该在完成前回答一组最小复盘问题：目标是否达成、证据是什么、实际用了哪些能力、发生了什么摩擦、是否产生下次规则候选。这是执行质量要求，不等于每个 Skill 都必须长期保存一套运行系统。

是否持久化按真实需要分级：

- 一次性、无本机状态的简单 Skill：在 `SKILL.md` 中保留完成检查即可，不强制创建空的 `experience.local.md`；
- 会反复运行、受本机环境影响的 Skill：使用 `experience.local.md` 保存经过验证的本机事实和经验；
- 像 `browser-control` 这样还要求记录每次下游能力表现的路由 Skill：在 `experience.local.md` 之外增加逐次 Markdown 复盘，避免经验文件退化为流水账。

因此，`experience.local.md` 不需要被废弃，而是升级为“本机能力地图 + 经晋升经验”的入口；逐次事实留在 `runs.local/`，共享稳定规则回流 `SKILL.md` 或 reference。

## 核心路由

### 第一判断：是否需要已有登录态

```text
用户浏览器任务
  |
  |-- 只是搜索、发现信息来源？
  |      `-- 委派 web-search，退出浏览器路由
  |
  |-- 需要复用已有 Cookie、账号会话、当前登录页或内部系统？
  |      `-- WebAccess
  |
  `-- 不需要已有登录态
         `-- Chrome DevTools
```

硬规则：

- 本地静态页、`file://`、`localhost`、公开网页、前端调试、截图、DOM 检查、控制台、网络与性能分析，默认进入无登录态能力槽位。
- 内部系统、当前已登录标签页、必须依赖现有 Cookie 的页面，进入登录态能力槽位。
- “页面是 SPA”或“需要 JS 渲染”本身不构成使用 WebAccess 的理由；只要不需要已有登录态，仍优先 Chrome DevTools。
- 不允许因为 Chrome DevTools 暂时不可用而静默升级到 WebAccess。应先走同槽位的无登录态 fallback；所有合理候选都不可用时再报告阻断。
- 登录态需求无法从用户表达和目标事实判断、且选错会改变结果时，只询问这一项关键问题。

### 能力槽位

稳定注册表至少定义三个边界：

1. `browser_without_existing_login`
   - 主候选：Chrome DevTools MCP。
   - 等价环境候选：Codex in-app Browser。
   - 适用：静态页、本地预览、公开页面、前端调试和无需既有会话的交互。
2. `browser_with_existing_login`
   - 主候选：WebAccess。
   - `web-connect` 作为当前标签页和复杂配置页讲解的专用适配层，不再承担通用入口职责。
3. `web_information_discovery`
   - 委派：`web-search`。
   - 只声明边界，不把搜索流程复制进本 Skill。

候选按能力槽位注册，而不是把完整流程绑定到工具名。将来出现更合适的同类能力时，可以通过验证后启用、替换或重排候选，而不改变用户入口。

## 唯一入口边界

`browser-control` 的 frontmatter 描述覆盖通用浏览器操控、打开页面、静态页预览、网页调试、当前登录页和“该选哪个浏览器工具”等请求。

为避免触发竞争：

- 收紧 `web-connect` 的 description，把它标记为 `browser-control` 的登录态/当前页/配置讲解执行层；普通浏览器请求不得直接触发。
- `web-search` 保持网络信息发现唯一入口；它需要升级到真实浏览器时，应委派 `browser-control` 决定无登录态或登录态能力，而不是自行把 JS 页面等同于 WebAccess。
- 其他业务 Skill 在自己的封闭流程中可以继续使用已选定的浏览器能力；“唯一入口”约束的是通用用户意图和提供者选择，不要求本轮重写所有专用实现。

## 文件结构

```text
plugins/dev-tools/browser-control/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── capabilities.md
├── scripts/
│   └── usage-ledger.mjs
├── tests/
│   └── usage-ledger.test.mjs
└── .gitignore
```

运行时按需创建并全部忽略：

```text
plugins/dev-tools/browser-control/
├── runs.local/
│   └── <run-id>.md
└── experience.local.md
```

不提前创建空运行目录或空经验文件。首次真实使用时，脚本创建本轮 Markdown 复盘；首次完成有效探测后，再用真实状态初始化 `experience.local.md`，不生成只有标题的空模板。

## Markdown-first 三层事实模型

中间状态、逐次复盘和本机经验统一使用 Markdown。原因不是排斥结构化数据，而是浏览器能力会不断增加字段、限制和解释；Markdown 更适合 AI 按文章语义读取，也允许未来新增段落而不先迁移固定 schema。

Node 校验器只约束必需标题、核心枚举、安全边界和路径，不拒绝额外标题或单行项目。运行复盘使用“标题 + 短项目列表”，不接收任意长文、代码块或原始页面片段。这样既保留最低契约，又不会让字段扩展被固定机器 schema 卡住。

### 1. 稳定能力注册表

`references/capabilities.md` 进入版本控制，只描述：

- 能力槽位及适用条件；
- 有序候选与别名；
- 最小探测方式；
- 输入输出契约；
- 合法 fallback；
- 禁止跨槽位降级的规则。

它不声明候选当前一定可用，也不保存本机登录状态。

每个能力槽位用独立二级标题，候选、探测、输入输出和 fallback 使用短表格或项目列表。新增候选或字段时可以直接添加段落，不需要迁移运行记录。

### 2. 每次实际使用与复盘

`runs.local/<run-id>.md` 每次真实路由后保存一篇独立复盘。一次路由可能经过适配层、实际提供者和 fallback，因此必须逐项记录每个真实调用的下游 Skill，而不是只保存最终工具名。

```markdown
# Browser Control Run: <run-id>

## 任务

- 时间：<ISO-8601>
- 类型：static-page
- 需要已有登录态：否

## 候选探测

### chrome-devtools

- 状态：available
- 检查时间：<ISO-8601>
- 版本：未知
- 状态证据引用：E0

## 路由决定

- 能力槽位：browser_without_existing_login
- 检查候选：chrome-devtools
- 实际链路：browser-control → chrome-devtools
- 模式：primary
- 结果：passed

## 实际使用的 Skills

### chrome-devtools

- 承担能力：无登录态浏览器控制
- 来源：<plugin-or-skill-id>
- 版本：未知
- 实际动作：navigate、snapshot、console
- 输入：target、intent
- 输出：browser_result、evidence
- 结果：passed
- 证据引用：E1
- 摩擦：无

## 证据

### E0

- 类型：observation
- 引用：run://probe-snapshot
- 证明：候选能够打开目标并返回页面结构

### E1

- 类型：artifact
- 引用：run://snapshot-created
- 证明：目标已打开并取得页面结构

## 复盘

- 总体结果：success
- 有效模式：无登录态静态页由 Chrome DevTools 完成
- 已验证根因：无
- 下次规则候选：无
- 建议归宿：none
```

登录态配置讲解可能把实际链路记录为 `browser-control → web-connect → web-access:web-access`，并为 `web-connect` 和 WebAccess 分别写三级标题，说明适配职责和实际浏览器能力。fallback 同样新增独立条目，不得覆盖或丢弃主候选的失败事实。

候选探测状态与任务结果必须分开：

- 候选状态只允许 `available | degraded | missing | not_checked`；
- 每个被考虑的候选都写状态、检查时间和状态证据；未执行探测时明确写 `not_checked`；
- 任务可以在候选 `available` 时因业务步骤失败，不能据此把候选标为 `missing`；
- `finalize` 只依据“候选探测”更新当前能力卡，不能从“路由决定”或任务结果反推可用性。

记录“能力 + 结果 + 证据 + 复盘”，不重复 `skill-stats` 已经提供的调用频率统计。必需标题固定，但允许在任意章节增加新的短项目或子标题。

证据使用最小固定语义：

- “类型”只允许 `artifact | test | observation | user_confirmation`；
- “引用”只允许本轮内部的非敏感证据 ID、`run://` 引用或运行目录内相对路径；
- “证明”只写可证伪的简短结论，不复制页面正文、URL、请求头或账号信息；
- 下游 Skill 只能引用已登记的证据编号，不能另写未经登记的自由文本证据。

### 3. 本机能力地图与经晋升经验

`experience.local.md` 是本机 Markdown 入口，但不再承担逐次流水。它只维护两类会改变下一次路由的信息：

1. **当前能力地图**：每个候选最近一次经过证据验证的状态、检查时间、实际能力、版本和已知限制；
2. **经晋升经验**：已经验证、会影响下次决策的本机结论。

例如：

- 某候选在本机的稳定安装或连接约束；
- 某类登录态任务已验证的前置条件；
- 有明确根因和防错动作的重复失败；
- 经过多次证据支持的候选适用边界。

逐次调用流水和未经验证的猜测不得写入此文件。当前状态必须带 `checked_at` 和证据引用，不能只写“已安装”或“可用”。同一能力的新证据更新原卡片，不重复追加状态段落。

第一次真实运行完成且产生有效证据时，可以创建 `experience.local.md` 并写入首张能力状态卡；这不是空模板，也不代表本轮结论已经晋升为长期经验。

## 运行闭环

1. 识别用户意图，先排除纯搜索任务。
2. 判断是否需要复用已有登录态，并选定一个能力槽位。
3. 读取 `references/capabilities.md` 中该槽位，并从 `experience.local.md` 读取相关能力卡和最多少量经验。
4. 在首次使用、状态过期或现有候选失败时执行最小探测，并更新本机状态。
5. 加载并调用被选中的下游 Skill；不预读所有候选的完整说明。
6. 对照能力槽位的输出契约验证结果，不接受下游 Skill 的自报成功作为唯一证据。
7. 无论成功、降级还是失败，都完成本轮 Markdown 复盘，并调用 `usage-ledger.mjs` 校验和归档。
8. 只有出现有证据的可复用结论时，才形成经验或调整候选；不为“完整”强行沉淀。

## Node.js 复盘账本脚本

`usage-ledger.mjs` 使用 Node.js 18+、ESM 和标准库，保持 macOS、Linux 与 Windows 可运行，不引入第三方运行依赖。它提供三个最小子命令：

1. `init <run-id>`：原子创建 `runs.local/<run-id>.md` 的最小 Markdown 复盘骨架；
2. `validate <run-id>`：检查必需标题、核心枚举、证据引用、安全规则和完成状态；
3. `finalize <run-id>`：验证通过后锁定本轮复盘，并用有证据的最新状态更新 `experience.local.md` 的对应能力卡。

AI 在 `init` 与 `finalize` 之间直接阅读和编辑 Markdown。校验器允许额外标题和单行项目，因此新增字段不需要升级固定 schema。

脚本不负责自动修改 `references/capabilities.md`、`SKILL.md`、经晋升经验段或下游 Skill。`finalize` 只能更新 `experience.local.md` 的“当前能力地图”；长期经验仍需通过晋升门槛。

脚本只能可靠检查结构和可识别模式，不能判断一段自然语言在语义上是否属于敏感页面正文。因此写入前由 AI 承担语义脱敏：只保留证明结论，不复制原始 DOM、页面正文、请求内容或账号信息。脚本再执行确定性防线：

- 复盘文件最大 64 KiB，只允许标题、空行和单行项目；禁止 fenced code block、原始 HTML/DOM 片段和多行粘贴；
- 普通项目值不超过 500 个字符，“证明”不超过 240 个字符；
- 拒绝 Cookie、token、Authorization、密码、JWT、请求头模式和任何 `http://`、`https://` 或带 query 的 URL；仅允许 `run://` 和运行目录内相对证据引用；
- `run_id` 只允许小写字母、数字和单连字符，长度不超过 63；写入前解析目标路径并确认它仍位于 `runs.local/` 内，禁止 `..`、斜杠、绝对路径和已有文件覆盖。

只要 AI 尚未完成语义脱敏，`finalize` 就不得执行。脚本的模式扫描是第二道防线，不对语义安全作虚假保证。

经验文件的机器维护区块使用唯一哨兵语法：

```markdown
<!-- browser-control:status:chrome-devtools:start -->
### chrome-devtools

- 状态：available
- 检查时间：<ISO-8601>
- 状态证据引用：runs.local/<run-id>.md#E0
<!-- browser-control:status:chrome-devtools:end -->
```

每个候选 ID 只能存在一对同名哨兵；禁止重复、嵌套、交叉或起止不匹配。缺失或损坏时 fail closed，不猜测修复。脚本只替换同一对哨兵之间的机器状态块，区块外字节保持不变；AI 新增的补充字段、解释和经晋升经验必须写在哨兵外。写入使用临时文件加原子重命名，失败不留下半文件。

脚本使用 `import.meta.url` 定位自身与 Skill 根目录，不依赖调用时的 CWD，也不拼接用户传入的根路径。内部路径逻辑显式覆盖 POSIX、Windows drive 与 UNC 语义，读取时接受 LF 和 CRLF，写回保持原文件换行风格。

## 经验晋升与自进化

运行记录只能产生候选，不能直接改稳定路由。

```text
真实运行事实
→ 结果与证据
→ 摩擦或有效模式候选
→ 验证根因、查重、确认适用边界
→ 分流
   |-- 本机专属事实 → experience.local.md
   |-- 通用且重复验证 → SKILL.md / reference
   |-- 候选能力稳定变化 → references/capabilities.md 变更候选
   `-- 证据不足 → 留在本轮 manifest
```

调整候选必须说明 `operation`、`reason`、`evidence_refs` 和 `status: candidate`。只有经过最小探测与关键路由回归后，才能启用、停用、替换或重排稳定候选。

当前证据与历史经验冲突时，以当前证据为准，并更新旧经验状态；不保留互相矛盾的“活跃真相”。

## 安全与隐私

- 进入版本控制的文件不得包含真实账号、Cookie、token、内部 URL、私有页面内容或本机绝对路径。
- 本地运行记录同样默认脱敏，只保存足以证明能力结果的摘要或本地证据引用。
- 读取和截图不扩大用户授权；保存、提交、发布、删除、授权、支付和上传等外部写操作继续遵循下游 Skill 的确认门。
- 路由层不绕过 Chrome DevTools、WebAccess 或 `web-connect` 自身的安全规则。
- 只关闭本轮创建的页面或标签，不影响用户原有页面。

## Plugin 集成

新增 Skill 属于 DevTools Plugin 的 MINOR 变更：

- `plugins/dev-tools/.claude-plugin/plugin.json`: 添加 `./browser-control/`，版本 `2.5.2 -> 2.6.0`；
- 根 `.claude-plugin/marketplace.json`: 同步 `2.6.0`；
- 根 `README.md`: 同步版本和 Skill 清单；
- `web-connect/SKILL.md`: 收紧触发边界，并修复与当前 WebAccess API 不一致的旧导航请求；
- `web-search/SKILL.md`: 浏览器升级路径委派 `browser-control`；
- 不恢复正在删除的 Plugin 内嵌 marketplace；
- 保留当前工作树中所有无关用户改动，只做小范围补丁。

## 验证

### 结构与脚本测试

- 官方 `quick_validate.py` 通过；
- `usage-ledger.mjs` 能初始化、校验并归档 passed、degraded、failed 三种 Markdown 复盘；
- 缺少必需标题、非法枚举和明显敏感内容时拒绝归档；
- `available` 候选上的任务失败不会把能力状态改成 `missing`；`not_checked` 不会覆盖已有有效状态；
- 多下游链能分别记录适配层、实际提供者和 fallback 的职责、结果与证据；
- 任意项目中的 secret、JWT、Authorization、HTTP(S) URL、请求头模式、超长文本、代码块和原始 HTML 片段被拒绝；语义脱敏作为 finalize 前置条件明确保留；
- `../`、斜杠、绝对路径和非法 `run_id` 不能逃逸 `runs.local/`；
- 同一 run ID 不被静默覆盖；
- 复盘与能力卡更新使用原子替换，失败不留下半文件；
- 第一次完成有效探测后才创建带真实能力卡的 `experience.local.md`，不创建空模板；
- 新增额外 Markdown 标题和短项目不会导致校验失败或被脚本覆盖；
- 缺失、重复、嵌套、交叉或错配的状态哨兵全部 fail closed，哨兵外字节保持不变；
- 从非仓库 CWD 调用仍写入正确 Skill 目录；LF/CRLF 均可读取并保持原换行风格；
- 使用 `path.posix` 与 `path.win32` 覆盖 POSIX、Windows drive 和 UNC 路径样例；
- `.gitignore` 确保所有本机运行事实不会进入版本控制。

### 路由契约测试

至少覆盖：

1. 本地静态 HTML，无登录态 → Chrome DevTools；
2. 公开 SPA，无登录态 → Chrome DevTools；
3. 内部系统，需要现有登录态 → WebAccess；
4. 当前已登录标签页的配置讲解 → WebAccess / `web-connect`；
5. 只要求搜索资料 → `web-search`；
6. Chrome DevTools 不可用 → 同槽位 fallback，不能静默切 WebAccess；
7. 下游自报成功但无可复核证据 → 结果不得记为 passed。
8. `web-connect → WebAccess` 和主候选失败后的 fallback 均在“实际使用的 Skills”中保留完整链路。

### Forward Test

用最小上下文启动独立 Agent，让它使用新 Skill 分别处理上述典型请求。评估输出只看路由、证据与记录工件，不向 Agent 泄露预期答案。失败后修订 Skill 并重新验证。

### 仓库级验证

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
```

Skill 自有 Node 测试在 GitHub Actions 使用 `ubuntu-latest`、`macos-latest`、`windows-latest` 与 Node 18+ 矩阵运行；仓库其他只适用于特定平台的验证保持原有执行边界。

## 验收标准

- 通用浏览器操控请求只由 `browser-control` 做首次提供者选择。
- 登录态是稳定、明确且可测试的第一路由键。
- 无登录态任务不会因为 JS 渲染或方便而进入 WebAccess。
- 新 Skill 保持薄路由，不复制下游操作说明。
- 每次实际使用都能产生带结果和证据的 manifest；调用次数不被冒充为能力。
- 本机状态、逐次记录、长期经验和共享规则各有唯一归属。
- 任何稳定候选调整都有证据、探测、回归与回滚路径。
- DevTools Plugin manifest、根 marketplace 和 README 版本一致。
- 现有用户改动未被覆盖，仓库全量验证通过。
