# WebFlow V3：Markdown 导航 + 最小 JS 运行契约

> 状态：待独立复审。本文定义 WebFlow V3 的目标形态；它替代 V2 以 YAML 描述工作流、rubric 和交接结果的做法。

## 背景

WebFlow V2 的优点是主 Skill 很薄、阶段职责清楚、外部能力按需探测、评分循环有限、部署需要单独授权。但它同时存在四个根问题：

1. `workflow.yaml`、阶段 Skill 和模板同时描述流程，事实源并不真正唯一；
2. 网站源码落在被忽略的 `.web-flow/runs/` 内，无法成为可维护项目；
3. gate、恢复、评分结果和终态只靠自然语言约定，没有可验证状态；
4. YAML 被用于人类说明、Agent 导航和机器状态三个不同职责，阅读与维护成本高。

用户的项目偏好已经明确：知识、SOP、导航和判断规则优先使用 Markdown；需要确定性处理时优先使用 JavaScript/Node.js；只有真正的机器状态才使用 JSON/JSONL。V3 以此为基本约束。

## 方案选择

### 方案 A：继续维护 YAML 工作流

保留 `workflow.yaml`、`external-skills.yaml`、`rubrics.yaml` 和阶段 YAML 产物，只补 schema 与校验器。

优点是改动小；缺点是把本应阅读和讨论的工作流固化为配置协议，继续制造 Markdown、YAML 和 Skill 文本之间的同步问题。否决。

### 方案 B：Markdown 导航 + JSON 状态 + JS 硬约束（采用）

- Markdown 负责工作流、阶段 SOP、rubric、评审、gate 说明、复盘和使用记录；
- JSON/JSONL 只负责恢复执行所需的当前状态、事件和 artifact 身份；
- 一个小型 Node.js 工具负责初始化、计算 hash、登记 artifact、追加事件和验证状态；
- 各生产 Skill 仍由 Agent 执行，不建设通用工作流引擎。

该方案与 Skill 的渐进式披露模型一致，也能对路径、状态迁移、artifact 版本和终态做确定性校验。

### 方案 C：恢复旧 Launcher/Workflow/critic 引擎

重新建设完整编排器、schema 注册中心、多 Agent runner 和自动修复循环。

它能实现最强自动化，但会重新引入高维护成本和抽象先行。V3 不采用。

## 设计原则

1. **Markdown 是地图**：Agent 通过语义明确的链接按需读取当前阶段，不通过 YAML 找路。
2. **机器状态才结构化**：只有恢复、hash、合法迁移和终态判定需要 JSON/JSONL。
3. **源码属于项目**：可维护源码始终写入目标项目的 `sourceDir`，`.web-flow/` 只保存运行证据。
4. **Agent 做判断，JS 守边界**：视觉、内容和设计判断留给 Agent；路径、状态、版本与 hash 交给 Node.js。
5. **一次只修一个重点**：独立评审最多两轮主观评分；事实门失败必须修复，不能被平均分掩盖。
6. **不恢复旧引擎**：V3 是最小可运行契约，不是工作流平台。

## 目标

- 一句话意图可以走 fast、full 或 adaptive 路径，产出真实可维护的网站源码；
- attended 与 unattended 都有明确 gate 语义和恢复点；
- factual claim 可追溯，同时允许明确标记的创意文案和占位内容；
- 每次评审都绑定具体 artifact 版本，不出现“分数对应旧页面”；
- 部署未授权或失败时仍能交付经过验证的本地 preview；
- 任务结束前留下 Skill 使用记录、复盘和可验证终态；
- 活跃 WebFlow 包不再依赖独立 YAML 工作流或 YAML 结果模板。

## 非目标

- 不实现可视化 DAG 编辑器、队列、远程 worker 或通用工作流 DSL；
- 不恢复旧 archive 中的 Launcher、critic、中心 memory 或大而全 schema；
- 不在本轮迁移 ignored memory，也不清理用户机器上的历史断链；
- 不把 labs 自动纳入仓库现有 Python 审计或 `install.sh`；V3 提供自己的 Node.js 自检与显式链接说明；
- 不强制所有目标站点使用同一框架、设计风格或部署提供商；
- 不在 build 阶段做多 Agent 并行写同一源码树。

## 活跃文件结构

```text
labs/web-flow/
├── README.md
├── web-flow/
│   ├── SKILL.md
│   ├── references/
│   │   ├── workflow.md
│   │   ├── runtime-state.md
│   │   └── external-capabilities.md
│   ├── scripts/
│   │   ├── web-flow-runtime.mjs
│   │   └── lib/
│   │       └── run-contract.mjs
│   └── tests/
│       └── web-flow-runtime.test.mjs
├── web-flow-research/SKILL.md
├── web-flow-prototype/SKILL.md
├── web-flow-design/SKILL.md
├── web-flow-build/SKILL.md
├── web-flow-deploy/
│   ├── SKILL.md
│   └── references/
│       └── cloudflare-pages.md
└── web-flow-benchmark/
    ├── SKILL.md
    └── references/
        ├── rubrics.md
        └── review-template.md
```

除标准 `SKILL.md` frontmatter 和平台强制元数据外，活跃 WebFlow 包不再新增 YAML。删除：

- `web-flow/workflow.yaml`
- `web-flow/external-skills.yaml`
- `web-flow-benchmark/rubrics.yaml`
- `web-flow-benchmark/score-result.template.yaml`

## 导航模型

`web-flow/SKILL.md` 只保留：触发边界、核心不变量、入口步骤和按需阅读链接。它不复制完整阶段 SOP。

导航规则：

1. 启动任务时读取 `references/workflow.md` 和 `references/runtime-state.md`；
2. 只有第一次需要外部能力时读取 `references/external-capabilities.md`；
3. 到达某阶段才读取对应生产 Skill；
4. 需要评分时只读取 benchmark Skill 和 `references/rubrics.md` 中当前阶段小节；
5. 只有选定某部署提供商时才读取对应 provider reference。

Markdown 链接必须写明“什么时候读、为什么读”，不能只列文件名。

## 输入与运行初始化

Agent 从用户自然语言和当前工作区解析以下事实，并在创建 run 前向用户确认任何高风险歧义：

| 字段 | 含义 |
|------|------|
| `intent` | 本轮要交付的网站与成功条件 |
| `projectRoot` | 目标项目根；机器状态中固定写 `.` |
| `sourceDir` | 相对项目根的可维护源码目录 |
| `sourceMode` | `create` 或 `update` |
| `interactionMode` | `attended` 或 `unattended` |
| `requestedProfile` | `fast`、`full` 或 `adaptive` |
| `deployment.requested` | 用户是否要求真实 URL |
| `deployment.authorized` | 用户是否明确授权产生外部部署副作用 |
| `references` | 用户提供的 URL、截图、文件或文字要求 |

`unattended` 不等于 `deployment.authorized`。部署授权必须单独、明确记录。

Node 工具的 `init` 命令创建：

```text
<projectRoot>/.web-flow/runs/<runId>/
├── run.json
├── events.jsonl
└── artifacts.jsonl
```

`runId` 使用 UTC 时间和随机短后缀生成；初始化后不得改名。`.web-flow/` 必须加入目标项目 `.gitignore`，但 `sourceDir` 不得位于 `.web-flow/` 内。

## 源码安全边界

所有路径先转成相对 `projectRoot` 的 POSIX 路径。机器文件中禁止保存绝对路径、`..` 跳转、凭证、认证头和私有 URL。

### create 模式

- `sourceDir` 可以不存在或为空；
- 若目录非空，立即阻断，除非用户明确改为 `update`；
- 不通过清空目录来“修复”冲突。

### update 模式

- 修改前检查版本控制状态并在 `preexisting-state.md` 记录已有改动；
- 只修改为当前目标列出的文件；不覆盖、删除或格式化无关用户内容；
- 与已有改动冲突时阻断并请求方向，不自动重置。

### 通用约束

- 解析现有父目录和符号链接后，目标必须仍位于 `projectRoot` 内；
- `sourceDir` 不得等于项目根，除非用户明确要求在已有项目根更新；
- build 直接在 `sourceDir` 中工作，运行目录只保存证据、review 和 artifact 索引；
- V3 不承诺跨框架的“原子替换”，因此用预检、最小改动和版本控制边界保护用户文件。

## 内容来源规则

“每条内容都有来源”只适用于事实性内容，不能把创意写作变成伪引用。`research/content-spec.md` 中每条主要内容必须标记为以下一种：

| 类型 | 规则 |
|------|------|
| `factual` | 必须链接到用户资料、网页、源码或可复核证据 |
| `user_statement` | 来源是本轮用户原话或明确选择 |
| `creative_copy` | 可以无外部来源，但不得包含未经验证的数字、资质或功能承诺 |
| `placeholder` | 必须显式标记，不能伪装成已确认内容 |
| `decision_needed` | 保持缺口；进入依赖该事实的阶段前必须解决 |

调研产物全部使用 Markdown：

- `research/content-spec.md`
- `research/reference-evidence.md`
- `research/asset-requirements.md`
- `research/stage-result.md`

## 执行档位

### fast

```text
research → wireframe → G1 → design → build → G3 → optional deploy
```

- `prototype` 标记为 `skipped`；G2 标记为 `not_applicable`；
- design 的视觉事实源是已批准 wireframe 加明确的视觉方向；
- 适合结构简单、参考依赖低、用户优先速度的页面。

### full

```text
research → wireframe → G1 → prototype → G2 → design → build → G3 → optional deploy
```

- design 的视觉事实源是已批准 prototype；
- 适合高相似度复刻、复杂视觉状态、关键素材依赖或需要先验证交互方向的页面。

### adaptive

初始化时暂不决定最终路径。G1 后根据参考依赖、视觉复杂度、素材风险和用户时间偏好解析为 fast 或 full，并在进入 design 前锁定。

锁定后不允许在同一 run 中临时补插 prototype。若设计目标发生实质变化，结束当前 run 为 `partial`，新建 run，并显式登记可复用的旧 artifact；这避免“补插后哪些阶段需要重跑”的隐式分支。

## 阶段与产物

| 阶段 | 生产 Skill | 关键产物 | 后续门 |
|------|------------|----------|--------|
| research | `web-flow-research` | 内容规格、证据、素材需求 | 无 |
| wireframe | `web-flow-prototype` 的 wireframe 模式 | 可打开低保真 HTML、stage result | G1 |
| prototype | `web-flow-prototype` 的 prototype 模式 | 可打开视觉/交互 HTML、stage result | G2 |
| design | `web-flow-design` | `design-tokens.css`、`layout-contract.md` | 无 |
| build | `web-flow-build` | `sourceDir` 源码、preview evidence、stage result | G3 |
| deploy | `web-flow-deploy` | deployment evidence、真实 URL | 无 |

每个生产阶段完成前都调用 benchmark。benchmark 不是 DAG 中的生产阶段，而是绑定当前 artifact revision 的独立 review。

## 最小运行状态

`run.json` 是可恢复的当前快照，`events.jsonl` 是不可回写的状态迁移历史，`artifacts.jsonl` 是不可回写的 artifact revision 历史。详细字段与合法迁移写入 `references/runtime-state.md`，实现由 JS 常量维护，不再另建 schema YAML。

`run.json` 至少包含：

```json
{
  "schemaVersion": 3,
  "runId": "20260711T120000Z-a1b2",
  "intent": "制作产品落地页",
  "projectRoot": ".",
  "source": { "mode": "create", "dir": "site" },
  "interactionMode": "attended",
  "profile": { "requested": "adaptive", "resolved": null, "lockedAt": null },
  "deployment": { "requested": false, "authorized": false, "provider": null },
  "status": "running",
  "currentStage": "research",
  "stages": {},
  "gates": {},
  "resume": { "stage": "research", "action": "start" },
  "updatedAt": "2026-07-11T12:00:00.000Z"
}
```

阶段状态：

```text
not_started → running
not_started → skipped
running → awaiting_gate | completed | blocked | failed | cancelled
awaiting_gate → running | completed | blocked | cancelled
blocked → running | failed | cancelled
```

`completed`、`skipped`、`failed` 和 `cancelled` 对该阶段是终态；若需要重做已完成阶段，必须登记新的 artifact revision 和 `stage_reopened` 事件，不能静默覆盖历史。

run 状态：

- `running`：仍在正常执行；
- `blocked`：可恢复，`resume` 必须指出阶段与所需动作；
- `success`：本轮已完成用户实际授权范围；
- `partial`：已有可交付 preview，但请求的部署或实质变更未完成；
- `failed`：没有可交付结果且无法继续；
- `cancelled`：用户拒绝或明确终止。

只有 `blocked` 可以恢复为 `running`。其余四个结束状态不可原地重开；继续工作需要新 run。

## Artifact 身份

每个 artifact revision 在 `artifacts.jsonl` 中追加一行：

```json
{"artifactId":"build.preview","revision":2,"kind":"directory","path":"site","sha256":"...","producer":"build","createdAt":"...","supersedes":"build.preview@1"}
```

规则：

- 路径一律相对项目根；
- 文件 hash 为原始字节的 SHA-256；
- 目录 hash 先按 POSIX 相对路径排序，计算每个文件 SHA-256，再对规范化清单计算 SHA-256；
- 目录 hash 排除 `.git/`、`.web-flow/`、`node_modules/` 和框架缓存目录；
- review、gate 和 deploy evidence 必须引用完整 `artifactId@revision` 与 hash；
- 修改产物必须新增 revision，不得改写旧 artifact 记录。

## G1、G2、G3

| gate | 展示内容 | 通过后 |
|------|----------|--------|
| G1 | 低保真 wireframe、信息架构、桌面/移动视图 | 解析并锁定 profile |
| G2 | full 路径的视觉或交互 prototype | 进入 design |
| G3 | 来自 `sourceDir` 的真实 preview 与验证证据 | 可按授权进入 deploy |

attended 决定：

- `approved`：绑定当前 artifact revision，阶段完成；
- `revise`：当前阶段回到 `running`，产出新 revision 后重新 review 和 gate；
- `rejected`：run 进入 `cancelled`；
- `deferred`：run 进入 `blocked`，保存明确 resume action。

unattended 决定：

- 最新独立 review 的 must-pass 全部通过，且 decision 为 `pass` 或 `proceed_with_residual`，才可写 `auto_approved`；
- review 为 `blocked` 时 gate 不能自动放行；
- fast 路径的 G2 必须写 `not_applicable`，不能伪造 approval。

gate 详情写 Markdown 到 `gates/G1.md` 等文件；可恢复的当前决定与 artifact ref 同步写入 `run.json`，不可变历史追加到 `events.jsonl`。

## 独立 Benchmark

`web-flow-benchmark/references/rubrics.md` 是评分规则的唯一可读事实源，按阶段分节。每节包含：

- 必须通过的事实项及所需证据；
- 0–5 分维度、权重和 0/3/5 锚点；
- 阶段阈值；
- 不得引入的额外审美要求。

评审必须由未参与当前 artifact 生成的独立 Agent 完成；若运行环境只能使用干净上下文而无法创建独立 Agent，review 中必须记录这个限制，不能写成完全独立。

review 使用 `references/review-template.md` 的 Markdown 结构，保存到：

```text
reviews/<stage>-round-1.md
reviews/<stage>-round-2.md
reviews/<stage>-must-pass-recheck-<n>.md
```

每份 review 必须记录 evaluator、rubric revision、时间、artifact ref/hash、逐项 must-pass 证据、各维度分数、加权结果、唯一 `top_fix`、decision 和 residual。

两轮规则：

```text
must-pass 失败 → blocked；修复事实后可反复 recheck，不占主观轮次
round 1 达阈值 → pass
round 1 未达阈值 → revise_once，只修 top_fix
round 2 达阈值 → pass
round 2 未达阈值 → proceed_with_residual，停止主观循环
```

`run.json` 只保存最新 review 的 artifact ref、decision、must-pass 结果和分数，完整理由留在 Markdown。JS 验证器检查允许值、轮次上限、artifact 绑定和 gate 条件，不尝试解释主观文本。

## 外部能力

V3 不维护静态候选 YAML 注册表。`references/external-capabilities.md` 定义语义 capability slot：

- `reference_observation`
- `prototype_design`
- `visual_asset_generation`
- `browser_verification`
- `deployment_provider`

第一次真正需要某 slot 时，Agent 从当前可用 Skill catalog 中按输入输出和边界选择候选，只探测首选；失败后再尝试下一个或文档中的本地 fallback。不得开局扫描所有能力，也不得把某个第三方工具写成永久依赖。

本轮实际选择、探测证据、输入输出、结果、fallback 和摩擦记录到 `skill-usage.md`。这是运行叙事，不是恢复状态，因此使用 Markdown，不再创建 `external-status.yaml`。

## 部署

`web-flow-deploy` 改为提供商无关入口。只有选定 Cloudflare Pages 时才按需读取 `references/cloudflare-pages.md`；未来新增 provider 也使用独立 Markdown reference。

规则：

1. `deployment.requested=false`：不做 preflight；G3 后 preview 验证通过即可 `success`；
2. `requested=true` 且 `authorized=false`：禁止外部写操作；交付 preview 后为 `partial`；
3. `requested=true` 且 `authorized=true`：开局可做一次早期 preflight 发现凭证/项目问题；
4. publish 前必须重新执行全部易漂移检查，早期 readiness 不能作为永久通行证；
5. publish 必须绑定当前 build artifact hash，保存命令退出码、URL、HTTP 结果、浏览器证据和控制台结果；
6. 部署失败不能破坏本地源码和 preview，run 以 `partial` 结束并保留恢复建议；
7. URL、关键资源或控制台事实门失败时不能标记 deploy 成功。

早期检查写 `preflight/deployment-readiness.md`；最终发布写 `deploy/deployment-evidence.md`。二者都不得包含 token 或认证头。

## 终态与复盘

进入 `success`、`partial`、`failed` 或 `cancelled` 前必须依次：

1. 完成 `skill-usage.md`；
2. 完成 `retrospective.md`，记录目标、实际路径、偏差、有效做法、失败、residual 和候选规则；
3. 运行 `validate-run`；
4. 追加 terminal event，再更新 `run.json` 终态；
5. 输出 preview 或 production URL、关键验证证据和 residual。

低分或主观偏好不能直接写 memory。只有真实错误、根因有证据、未来可能复现三项同时成立，才在 retrospective 中生成候选；是否晋升到可分享 Skill/reference 是后续独立维护动作。

## Node.js 运行工具

实现使用 Node.js ESM 和标准库，不安装运行时依赖。入口：

```text
node web-flow/scripts/web-flow-runtime.mjs init ...
node web-flow/scripts/web-flow-runtime.mjs artifact add ...
node web-flow/scripts/web-flow-runtime.mjs event append ...
node web-flow/scripts/web-flow-runtime.mjs validate-package
node web-flow/scripts/web-flow-runtime.mjs validate-run <runDir>
```

职责仅限：

- 安全解析项目与源码路径；
- 创建初始状态；
- 计算并登记 artifact hash/revision；
- 追加不可变事件；
- 检查 JSON/JSONL 结构、状态迁移、artifact 引用、gate/review 条件和终态必需文件；
- 检查活跃 WebFlow 文档链接、禁止的独立 YAML 文件和遗留引用。

它不选择设计风格、不写页面、不调用外部 Skill、不自动部署，也不实现通用 DAG runner。

## 测试

使用 `node:test` 覆盖：

1. package 自检能发现遗留 YAML 文件、失效相对链接和对旧文件名的引用；
2. init 生成合法 `run.json`、空 JSONL 文件和安全 run id；
3. create/update 路径规则与符号链接逃逸被拒绝；
4. 文件与目录 hash 稳定，排除目录不影响结果；
5. artifact revision 只追加、不覆盖，review 引用旧 revision 时被拒绝；
6. fast/full/adaptive 的 stage 与 gate applicability 正确；
7. 非法阶段迁移、非法 terminal 重开和缺失 resume 被拒绝；
8. unattended gate 不能绕过 blocked must-pass；
9. terminal 缺 `skill-usage.md`、`retrospective.md` 或有效 preview/deploy evidence 时失败；
10. 凭证形态和绝对路径不会进入机器状态或 Markdown 证据。

测试命令：

```bash
node --test labs/web-flow/web-flow/tests/*.test.mjs
node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs validate-package
```

现有仓库 Python 测试仍作为回归验证运行，但 V3 新逻辑不新增 Python 文件。

## 分发边界

WebFlow 仍位于 `labs/`，不进入标准 `./install.sh`。`labs/web-flow/README.md` 必须提供七个活跃 Skill 的显式 `j-skills link` 与安装说明，并说明 archive 不参与运行。

本轮不修改现有 Python 审计器来扫描 labs，以避免为了实验性模块扩大稳定基础设施；`validate-package` 是 WebFlow 自己的可重复验收入口。

## 验收标准

- 活跃 WebFlow 中只有必要的 `SKILL.md` frontmatter 使用 YAML；四个独立 YAML 文件被删除；
- 主 Skill 通过 Markdown 语义链接完成渐进导航，不再引用 `workflow.yaml` 或 `external-skills.yaml`；
- 所有阶段产物、rubric、review、gate、usage 和 retrospective 均为 Markdown/HTML/CSS；
- 网站源码写入安全的项目 `sourceDir`，不再写入 gitignored run 目录；
- JSON/JSONL 能恢复当前阶段、profile、gate、review 和 artifact 版本；
- Node 工具能拒绝非法路径、非法迁移、旧 artifact 评审和不完整终态；
- fast 路径明确跳过 prototype/G2，full 路径消费 prototype，adaptive 在 design 前锁定；
- factual claim 有证据，创意文案不会被伪装成事实；
- 部署授权与 unattended 分离，发布前重新 preflight，失败仍保留 preview；
- benchmark 独立、绑定 artifact、最多两轮主观评分且 must-pass 不放水；
- Node 测试、package 自检、现有相关 Python 回归测试和仓库通用验证全部通过；
- 不自动 commit、push、清理 ignored memory 或删除用户机器上的历史链接。

## 实施边界

本规格先改活跃 WebFlow 文档、最小 Node 运行契约、测试和 README。archive 只作为历史证据保留，不作为运行依赖；ignored memory 的归属和晋升另开任务处理。
