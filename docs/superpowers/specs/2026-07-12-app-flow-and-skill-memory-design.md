# App Flow 与可记忆 Skills 设计

**日期：** 2026-07-12  
**状态：** 待书面审阅  
**范围：** `labs/app-flow`、`happy-app-experience` 与通用本地 Memory 协议

## 1. 背景

目标体验是：用户用自然语言描述一个 App，补充大致模块和截图后，Agent 可以持续工作数小时，自主选择技术栈、设计与验证方式，并按用户当次要求交付源码、安装包、预览、OTA 或 GitHub Release。

现有 `labs/web-flow` 已验证了子 Skill、独立 Memory 和渐进加载的价值，但它把 research、wireframe、prototype、design、build、deploy 固定为阶段，并要求每阶段产生结构化交接文件。主入口虽然薄，底层仍是一条厚流水线；同一上下文里的很多文件只是在重复传递模型已经知道的内容。

本设计把控制权重新交给模型：Workflow 只守住不变量，具体路径由 Agent 根据目标、代码现场、能力和按需加载的经验决定。

## 2. 设计原则

### 2.1 薄 Workflow

`app-flow` 只负责：

- 明确当前目标和什么算完成；
- 识别不可逆操作与用户授权；
- 选择当前最有价值的下一步；
- 按需激活能力 Skill 或经验包 Skill；
- 用事实验证结果；
- 在完成、阻塞或需要用户决策时停止。

它不固定：

- React Native、Expo、Flutter、原生或其他技术栈；
- research、spec、prototype、build、review、release 等阶段；
- APK、IPA、网页、源码、OTA 或 GitHub Release 等交付类型；
- 每一轮必须生成的中间文件；
- 必须使用的具体 Skill 名称或评测器。

用户当次请求和现场事实决定这些选择。

### 2.2 Skill 是可插拔能力或经验源

系统区分三种角色：

```text
薄 Flow Skill
  负责目标、权限、验证和停止
        ↓ 按需选择
能力 Skill
  负责设计、编码、测试、打包、发布等具体行动
        ↓ 按需参考
经验包 Skill
  提供某项目、团队或领域的已验证事实、取舍和失败经验
```

`app-flow` 不硬编码 `happy-app-experience`。当用户说“参考 Happy 的经验”，或当前任务与其 description 高度匹配时，Agent 才加载它。没有安装或不相关时，流程正常继续。

能力发现只依赖宿主已经暴露的 Skill metadata 目录，接口是 `name`、`description` 和可读入口，而不是 `app-flow` 内的一份固定清单。每次只围绕“下一项行动”查询：

- 没有匹配项时，使用模型与现有工具继续，或在确实缺少能力时报告阻塞；
- 只有一个可读匹配项时加载它；
- 有多个匹配项时按意图具体度、现场适配度、证据质量和加载成本排序，只加载完成当前行动所需的最小集合；
- 入口缺失或不可读时跳过该候选并保留诊断，不让整个 Flow 失败；
- 不得为了方便而把候选名称回写成固定阶段或硬编码 Skill 列表。

宿主可以用不同方式提供目录；本协议只约束选择语义，不绑定某个 CLI 或 API。

### 2.3 渐进式披露是主要架构

薄不是内容少，而是每层入口小。加载链路分两级：

```text
用户意图
→ Skill metadata 选择相关 Skill
→ SKILL.md 地图
→ 当前 Repo / WorkTree / Feature / Run 的局部索引
→ 1–3 条相关 Memory 或 reference
→ 必要时读取原始证据和源码
```

磁盘上可以保存大量内容；上下文只接收会影响当前决策的小子集。

默认一次局部检索最多加载一个根入口、一个作用域 map，以及 3 条 Memory/reference，正文合计不超过 32 KiB。只有当前决策明确需要原始证据时才继续展开，并记录展开原因；文件总数增长不改变入口读取上限。

### 2.4 文件只服务持久化和真实边界

以下情况才落盘：

- 跨会话、压缩或进程中断后需要恢复；
- 未来可能复用、需要渐进检索；
- 用户真正需要的项目代码和交付物；
- 测试、日志、截图、Release 等可复核证据；
- 工具只能通过文件传递的大型内容。

同一上下文里的 Skill 交接直接传递，不创建 `stage-result.md`、artifact manifest 或等价中转文件。

## 3. App Flow 运行模型

运行循环保持为自然语言约束，而不是固定阶段图：

```text
读取目标、现场和当前证据
→ 判断下一项最有价值的行动
→ 加载完成该行动所需的 Skill 与局部 Memory
→ 行动
→ 验证结果是否推进目标
→ 必要时更新局部 Memory 或恢复点
→ 完成则交付；有价值的下一步仍存在则继续；缺授权或关键信息则阻塞
```

### 3.1 任务身份与唯一恢复点

一次 `app-flow` 激活会形成一个 `run-id` 和一个稳定 `task-key`。`task-key` 由 Repo 命名空间加显式 Goal/Task/Feature ID 组成；没有显式 ID 时才使用规范化 WorkTree 或分支标识。

跨 Skill 的任务级恢复点只由最外层 `app-flow` 实例拥有。能力 Skill 和经验包可以保存自己的局部 Memory 与证据，但不能各自宣称“整个任务最新状态”。子 Agent 把状态返回给 Flow owner，由 owner 统一写恢复点。

最新恢复点通过一个固定大小的指针发现：

```text
app-flow/local/maps/resume/<repo-key>/<task-key>.md
  → app-flow/local/runs/<run-id>/checkpoints/<checkpoint-id>.md
```

Checkpoint 是不可变文件；指针最后以临时文件加原子 rename 更新。恢复时只读该指针和它指向的 checkpoint，校验 Repo、WorkTree、目标摘要与证据路径后继续，不递归扫描所有 Skill 的 `local/`。指针损坏或证据失效时降级为读取当前现场并新建恢复点，而不是猜测旧状态。

### 3.2 完成条件

完成条件从用户目标动态形成。例如：

- “做一个可安装的 Android 日记 App，并发布 GitHub Release”要求可下载 Release URL、安装资产和验证证据；
- “先做一个能看的原型”不应自动升级为生产发布；
- “参考 Happy”表示读取经验，不表示必须复制 Happy 的技术栈。

### 3.3 权限边界

删除、付费、生产发布、推送、创建 Release、修改远端数据等外部副作用只在用户已明确授权的范围内执行。无人值守或长时间运行不自动扩大授权。

### 3.4 失败、预算与停止

- 激活时建立 execution envelope：优先采用用户给出的时间、费用和资源限制；否则采用宿主可见的剩余资源，并预留验证与交付所需空间；
- “实质进展”必须至少产生一项可核验变化：验收条件被满足、相关测试/检查通过、根因范围缩小、阻塞被解除，或新增了能改变下一步的证据；
- 同一失败签名连续两次出现且没有新增证据时，不再原样重试，必须先诊断或换假设；
- 每个行动都要有假设、预期证据和成本上界；不存在尚未尝试且在 envelope 内可行的行动时，进入阻塞而不是无限换方案；
- 缺少授权、关键输入或外部状态时进入阻塞；剩余资源不足以同时完成下一步和最低验证时，也写恢复点后停止；
- 历史 Memory 与当前证据冲突时以当前证据为准，并更新旧记忆状态；
- 上下文即将切换、等待外部状态或任务被中断时，写一个紧凑恢复点；
- 恢复点只保留目标、已验证事实、当前输出指针、阻塞和下一步，不复制完整上下文。

## 4. Happy App Experience

### 4.1 定位

`happy-app-experience` 是可插拔经验包，不是另一个 App Workflow。它回答：Happy 在真实开发中如何选择、哪里踩过坑、哪些证据证明某种做法有效、什么边界下不应照搬。

现有 `happy-ops` 继续负责自托管中继、daemon、OTA 运行态和本机运维。两者边界为：

- `happy-ops`：维护和排障 Happy/Paws 运行系统；
- `happy-app-experience`：为其他 App 开发任务提供可迁移的产品与工程经验。

### 4.2 经验来源

Happy 仓库的源码、`docs/`、package 指令、测试和发布记录是真实事实源。经验包保存导航、脱敏后的取舍和已验证结论，不复制整个仓库。

第一版至少种下一条真实经验：Happy 的 OTA 只用于 JavaScript 兼容改动；原生依赖、权限、Expo plugin、包 ID、更新 URL 或 runtime version 变化需要重建 App。该经验必须指向 Happy 仓库中的 `docs/getting-started.zh-CN.md`、`packages/happy-app/app.config.js` 与 `packages/happy-app/eas.json`，并写明验证日期和不应外推到非 Expo 项目的边界。另记录“OTA 是最终真机确认，不替代发布前静态检查和回归测试”的证据入口 `docs/research/2026-07-04-right-swipe-panel-retrospective.md`。

可逐步沉淀的领域包括：

- RN/Expo 选择与适用边界；
- 移动端导航、手势、状态、i18n 和响应式布局；
- Preview、真机验证、OTA、APK 与 GitHub Release 的取舍；
- PR、WorkTree、测试、发布门禁和回滚；
- 已验证的失败根因及下一次防错动作。

目录和领域只在真实内容形成问题簇后创建，不预建空分类。

## 5. 每个 Skill 的本地 Memory

### 5.1 Git 边界

每个支持自进化的 Skill 至少提交：

```text
<skill>/
├── SKILL.md
└── .gitignore
```

`.gitignore` 至少包含：

```gitignore
local/
*.local.*
```

`local/` 在第一次真实写入时创建，整体不提交。动态索引、Feature 名、运行资料和 Memory 都在忽略范围内；禁止 `git add -f`。

可分享、已脱敏并反复验证的知识才进入提交层的 `references/` 或 `SKILL.md`。

### 5.2 本地结构

```text
local/
├── INDEX.md
├── maps/
│   ├── <topic>.md
│   └── features/<feature-key>.md
├── memories/<memory-id>.md
├── runs/<run-id>/
└── archive/
```

- `INDEX.md` 只导航主题和活跃 Feature map；
- map 只列短摘要、适用边界、路径和验证时间；
- Memory 一个主题或根因一个 Markdown；
- Run 保存可选的全量资料、临时文件、证据和恢复点；
- archive 日常不读。

Memory 可以达到数 GB，因为运行时禁止递归全读；容量和上下文成本解耦。

### 5.3 Feature 路由与并发

定位顺序：

1. 显式 Feature/Task/Goal ID；
2. WorkTree 名称；
3. Git 分支名；
4. Repo ID 或规范化远程地址；
5. 通用主题。

所有 Feature 路径都必须带 Repo 命名空间，不能直接使用裸 Feature ID：

```text
maps/features/<repo-key>/<feature-key>.md
```

- `repo-key` 优先取去掉协议、凭据、查询参数和 `.git` 后的规范化远程标识，再附其 SHA-256 前 12 位；没有远程时对仓库 realpath 做哈希，索引中不暴露绝对路径；
- `feature-key` 由显式 ID、WorkTree 或分支的安全 slug 加原值哈希形成，避免大小写、斜杠和同名冲突；
- Memory 文件使用时间有序 ID 加随机后缀，只新增、不原地覆盖；修正通过 `supersedes` 指向旧记录；
- 每个 run 只有 Flow owner 或它指定的单一 memory writer 更新同一 Skill 的 map；跨 run 更新使用原子创建的 per-map lock，持锁后重新读取并按 Memory ID 合并，写唯一临时文件后 rename；
- 无法在 execution envelope 内取得锁时，保留不可变 Memory 和 `pending-index` 指针，下一次使用先做有界合并，绝不覆盖未知的新内容。

相同 Repo 下的相同 Feature key 可以让多个会话和 Agent 找到同一批资料。根索引找不到入口时按当前现场继续，不扫描全部 Memory。

### 5.4 Memory 最小读写契约

可被 map 索引的 Memory 至少包含以下短字段；格式可以是 Markdown 列表，不要求 YAML：

```text
id
scope: repo / worktree / feature / run
status: raw | observed | verified | superseded
created-at / verified-at
evidence: 相对源码路径、测试命令、日志或 URL
supersedes
sensitivity: public | redacted | local-private
```

正文只写结论或决策、适用边界、证据解释和“下次如何用”。`verified` 必须有仍可访问的证据；没有证据只能是 `raw` 或 `observed`。旧结论失效时新增记录并标记替代关系，不静默改写历史。

Token、密码、私钥、完整环境变量、个人聊天原文和未经授权的第三方私密数据永不写入 Memory；日志先脱敏，必须保留的敏感资料只记录受控位置的指针。读取时遇到缺字段、断链或损坏条目就跳过并把 map 标为待修复，继续使用当前证据，不让一条坏 Memory 阻塞任务。

### 5.5 自主进化

每次 Skill 使用后都进行一次判断：

- 是否需要保存完整 Run 资料；
- 是否需要更新 Feature 状态；
- 是否出现会改变未来决策的原子经验；
- 是否已有同根因条目需要更新；
- 是否有多次成立、可脱敏并晋升到 reference 的通用规则。

允许全量保存，但“保存”“索引”“可信”“晋升”是四个不同状态。一次使用可以新增本地资料，不应直接改写稳定 `SKILL.md`。

## 6. 最小实现形态

第一版不创建 `workflow.yaml`、固定阶段 Skill、artifact manifest、评分 schema 或预设中间目录。

```text
labs/app-flow/app-flow/
├── SKILL.md
└── .gitignore

skills/happy-app-experience/
├── SKILL.md
├── .gitignore
└── references/
    ├── INDEX.md
    └── mobile-delivery.md
```

`scripts/` 和 `local/` 都在真实需要时再出现：

- 第一版随真实 Happy 经验创建最小 `references/`，不预建空主题；
- Memory 数量使人工维护索引明显出错时，才增加确定性的 Node.js 检查或重建脚本；
- 有第一条本地资料时创建 `local/`，但保持 Git ignored。

## 7. 示例

用户请求：

> 做一个日记 App，参考 Happy 的经验，Android 可安装，完成后发布 GitHub Release。

预期行为：

1. `app-flow` 从请求形成目标、授权边界和完成条件；
2. 激活 `happy-app-experience`，只读与移动栈、交付和真机验证有关的索引；
3. Agent 根据需求和当前环境决定技术栈，不因参考 Happy 就强制 Expo；
4. 按当前工作需要激活设计、实现、测试和发布能力；
5. Skill 间直接使用当前上下文，不生成阶段交接文件；
6. 长任务需要恢复时，由 `app-flow` 写唯一任务 checkpoint；各 Skill 只写自己的局部 Memory 与证据；
7. 最终以 Release URL、可安装资产和验证证据判断完成。

## 8. 验收标准

书面设计必须满足：

- Workflow 不硬编码技术栈、固定阶段或交付类型；
- Happy 经验以可插拔 Skill 提供，不耦合进 `app-flow`；
- 同一上下文不通过中间 Markdown 交接；
- 每个 Skill 独立拥有本地 Memory；
- `local/`、动态索引、maps、memories、runs 和 archive 全部 Git ignored；
- 根索引不平铺全部条目，支持按 Feature/WorkTree 渐进定位；
- 能力发现通过宿主 Skill metadata，零个、多个和不可读候选都有降级路径；
- 跨 Skill 任务只有一个可直接发现的最新恢复点；
- Repo/Feature key 可防止跨仓库同名冲突，并发更新不会静默覆盖；
- Memory 有证据、可信状态、替代关系、敏感信息与损坏降级契约；
- 允许全量本地保存，并明确保存不等于加载或可信；
- 稳定 Skill 只有在经验反复验证后才演进；
- 第一版运行时提交文件保持最小，不创建 YAML 工作流和空目录。

进入实现后还必须验证：

- `.gitignore` 能阻止本地 Memory 出现在普通 `git status`；
- 给定 Feature ID 时能只定位对应 map 和少量 Memory；
- 没有 Memory 时 Skill 可以正常运行；
- Memory 很多时，首次决策仍最多读取 1 个入口、1 个作用域 map、3 条正文且不超过 32 KiB；
- “参考 Happy”与“不参考 Happy”两种请求都能正常路由。
- 从仓库元数据能发现并读取 `app-flow`，且缺少可选能力 Skill 时仍能完成 smoke test；
- `happy-app-experience` 至少有一条带当前源码证据、验证日期和适用边界的真实经验。

## 9. 暂不处理

- Memory 的云同步、备份、加密和跨机器复制；
- 向量数据库、Embedding 或中心化 RAG；
- 自动清理数 GB 本地资料的保留策略；
- 对所有既有 Skills 批量迁移；
- 修改或删除当前 `labs/web-flow`；
- 在设计阶段发布 App、OTA 或 GitHub Release。
