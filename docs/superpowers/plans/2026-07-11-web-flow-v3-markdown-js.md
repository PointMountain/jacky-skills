# WebFlow V3 Markdown-first / JS-first Implementation Plan

> **For agentic workers:** REQUIRED: Use `superpowers:subagent-driven-development`（有独立 reviewer 时）或 `superpowers:executing-plans` 执行。每项实现先写失败测试，再做最小修改。当前工作树含用户既有改动：不创建 worktree、不 commit、不 push，只触碰本计划列出的 WebFlow、规格/计划与合约测试文件。

**Goal:** 将 WebFlow V2 从 YAML 驱动的提示词协议更新为 Markdown 导航、事件权威的 JSON/JSONL 状态和 Node.js 硬约束，使源码进入真实项目目录，gate、artifact、review、部署与终态均可恢复、校验和审计。

**Architecture:** `events.jsonl` 是状态迁移唯一权威，`run.json` 是可重建投影，`artifacts.jsonl` 是不可覆盖的 artifact ledger。生产 Skill 仍由 Agent 按 Markdown SOP 执行；Node.js 只实现有限状态合同。纯 reducer、运行存储、artifact/path 与 validator 分文件，CLI 只做参数路由。

**Tech Stack:** Markdown、JSON/JSONL、Node.js 24 ESM、Node 标准库、`node:test`。仅为兼容被删除的 V2 YAML，最小修改一项现有 Python `unittest`；不新增 Python 实现。

**Spec:** `docs/superpowers/specs/2026-07-11-web-flow-v3-design.md`

**JS file budgets:** `state-contract.mjs` ≤ 375 行；`runtime-store.mjs` ≤ 325 行；`artifact-store.mjs`、`artifact-ledger.mjs`、`source-safety.mjs` 各 ≤ 300 行；`workflow-contract.mjs`、`review-contract.mjs`、`review-store.mjs`、`gate-contract.mjs`、`gate-store.mjs`、`deployment-contract.mjs`、`deployment-store.mjs` 各 ≤ 350 行；`validators.mjs` ≤ 350 行；CLI ≤ 250 行。逼近预算时按职责拆函数，不把业务判断塞进 CLI。

---

## Chunk 1：最小 Node 运行合同

### Task 1：初始化与纯事件 reducer

**Files:**
- Create: `labs/web-flow/web-flow/tests/state-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/state-contract.mjs`

- [x] 写 `initialization` 失败测试：安全 run id、首个 typed event 为 `run_initialized`、sequence=1、`beforeStateHash=null`、投影 `eventSequence=1`。
- [x] 写 `replay` 失败测试：仅靠首事件重建相同投影；`stateHash` 对排除自身后的规范 JSON 计算；未知 event type 与跳号被拒绝。
- [x] 运行 `node --test --test-name-pattern='initialization|replay' labs/web-flow/web-flow/tests/state-contract.test.mjs`；预期 `ERR_MODULE_NOT_FOUND`。
- [x] 实现常量、规范 JSON、state hash、初始投影、typed reducer 与纯 `replayEvents()`；不做文件 I/O。
- [x] 重跑同一命令；预期所选测试全部通过、退出码 0。

### Task 2：运行存储、reconcile 与 `.gitignore`

**Files:**
- Modify: `labs/web-flow/web-flow/tests/state-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Create: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [x] 写 `runtime store` 失败测试：init 创建含一条初始化事件的 `events.jsonl`、空 `artifacts.jsonl` 和匹配投影。
- [x] 写 `.gitignore` 失败测试：保留原内容、只追加一次 `.web-flow/`、重复 init 不重复该行。
- [x] 写 `reconcile` 失败测试：事件领先快照时可重建；投影手工领先/漂移时普通 transition 拒绝；重复 event id 幂等且不增加 sequence。
- [x] 运行 `node --test --test-name-pattern='runtime store|gitignore|reconcile|idempotent' labs/web-flow/web-flow/tests/state-contract.test.mjs`；预期新增测试失败。
- [x] 实现事件追加/同步、临时投影、原子替换、重放对账、init 与 reconcile；CLI 仅转发参数。
- [x] 重跑同一命令；预期通过。

### Task 3：路径、hash、artifact ledger 与 update 基线

**Files:**
- Create: `labs/web-flow/web-flow/tests/artifacts-paths.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/artifact-store.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/artifact-ledger.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/source-safety.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/state-contract.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [x] 写 `safe paths` 失败测试：拒绝绝对路径、`..`、`.web-flow` 内源码、create 非空目录、未明确允许的项目根及 artifact 内任意 symlink。
- [x] 写 `artifact hash` 失败测试：文件/目录 hash 稳定；排序为 POSIX；七个固定排除目录不改变 hash；普通文件原地变化会改变 hash。
- [x] 写 `artifact ledger` 失败测试：revision 单调、旧记录不覆盖、完全相同重复登记幂等、`supersedes` 和跨 run `reusedFrom` provenance 正确。
- [x] 写 `update baseline` 失败测试：init 把既有 dirty path/hash 写入 `preexisting-state.md` 与初始化事件；允许路径和 dirty path 冲突时阻断；新增变化越界或既有脏文件 hash 改变时失败。
- [x] 运行 `node --test labs/web-flow/web-flow/tests/artifacts-paths.test.mjs`；预期 `ERR_MODULE_NOT_FOUND` 或新增断言失败。
- [x] 实现路径/realpath 检查、固定排除表、拒绝 symlink、SHA-256、artifact append/import 与 update 基线/allowlist 校验。
- [x] 在 CLI 接入 `artifact add`、`artifact import` 和 `source plan`；项目根 update 禁止把 `.` 当通配 allowlist。
- [x] 重跑 artifact/path 测试；预期全部通过。

### Task 4：阶段、profile 与 supersession transition

**Files:**
- Modify: `labs/web-flow/web-flow/tests/state-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/workflow-contract.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/state-contract.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [x] 写 `stage transitions` 失败测试：合法/非法边、blocked 必须有 resume、completed 不可 reopen、terminal 不可原地继续。
- [x] 写 `profiles` 失败测试：fast 锁定后 prototype=`skipped`/G2=`not_applicable`；full 保留 prototype/G2；adaptive 只能 G1 后且 design 前锁定。
- [x] 写 `supersession` 失败测试：纯 guard 规定无 G3 时旧 run 只能 cancelled+`supersededBy`、有 G3 时才允许 partial；实际 terminal event 延后到 Task 7 `finalize`，新 run 复用 artifact 必须有 provenance。
- [x] 写 `deployment authorization` 失败测试：unattended 不自动授权；G3 后、finalize 前允许显式用户授权；partial 后授权被拒绝。
- [x] 运行 `node --test --test-name-pattern='stage transitions|profiles|supersession|deployment authorization' labs/web-flow/web-flow/tests/state-contract.test.mjs`；预期新增测试失败。
- [x] 实现有限 `transition <runDir> --event-file` 与 typed reducer；不提供任意 `event append`，不自动运行阶段。
- [x] 重跑同一命令；预期通过。

### Task 5：独立 review 与版本化 gate

**Files:**
- Modify: `labs/web-flow/web-flow/tests/state-contract.test.mjs`
- Modify: `labs/web-flow/web-flow/tests/artifacts-paths.test.mjs`
- Create: `labs/web-flow/web-flow/tests/review-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/review-contract.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/review-store.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/gate-contract.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/gate-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/state-contract.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/artifact-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [x] 写 `review record` 失败测试：主观 round 仅 1/2；must-pass recheck 可多次且不占 round；event 绑定 rubric/review/artifact 的 path+实时 hash；review 文档禁止覆盖。
- [x] 写 `gate decisions` 失败测试：decision 文件序号递增并把 path/hash 写入事件；覆盖旧文件或文档漂移被拒绝。
- [x] 覆盖 `approved/revise/rejected/deferred/auto_approved/not_applicable`；rejected 进入待 cancelled finalization，deferred 进入 blocked+resume。
- [x] 写 must-pass 公共前置测试：attended 与 unattended 都不能放行 failed review；`auto_approved` 只允许 unattended；主观 residual 可显式接受。
- [x] 运行 `node --test --test-name-pattern='review record|gate decisions|must-pass' labs/web-flow/web-flow/tests/state-contract.test.mjs labs/web-flow/web-flow/tests/artifacts-paths.test.mjs`；预期新增测试失败。
- [x] 实现 `review record`、`gate decide` 窄命令；每次实时重算 artifact、rubric、review/gate Markdown hash。
- [x] 实现 gate revise 的 attempt 递增与 review round 重置；不支持 completed stage reopen。
- [x] 重跑同一命令；预期通过。

### Task 6：部署消费点合同

**Files:**
- Create: `labs/web-flow/web-flow/tests/deployment-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/deployment-contract.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/deployment-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/state-contract.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/artifact-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [ ] 写 `deploy preflight` 失败测试：未请求/未授权不能记录外部写操作；publish 必须声明晚期 preflight 已重跑。
- [ ] 写 `deploy binding` 失败测试：publish 前实时重算 build hash；deployment evidence 文档 hash 与 build ref/hash 进入事件；旧 build 或漂移证据被拒绝。
- [ ] 写 `deploy facts` 失败测试：成功必须有 HTTP、真实浏览器和 console 三项 passed；任一失败只能留下 failed deployment result，后续 run 至多 partial。
- [ ] 运行 `node --test labs/web-flow/web-flow/tests/deployment-contract.test.mjs`；预期新增测试失败。
- [ ] 实现 `deploy record --mode preflight|publish`；只登记并验证 Agent 提供的证据，不执行网络、浏览器或部署。
- [ ] 重跑 deployment 测试；预期全部通过。

### Task 7：run validator、秘密扫描与 finalize

**Files:**
- Modify: `labs/web-flow/web-flow/tests/state-contract.test.mjs`
- Modify: `labs/web-flow/web-flow/tests/artifacts-paths.test.mjs`
- Modify: `labs/web-flow/web-flow/tests/deployment-contract.test.mjs`
- Create: `labs/web-flow/web-flow/scripts/lib/validators.mjs`
- Modify: `labs/web-flow/web-flow/scripts/lib/runtime-store.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`

- [ ] 写 `sensitive scan` 失败测试：机器状态与 Markdown 中已知 token、Authorization header、用户绝对路径、localhost/私网 URL 被有限扫描拒绝；公共 URL 与相对路径允许。
- [ ] 写 `terminal matrix` 失败测试：success 需当前 G3；请求且授权 deploy 的 success 需同 build hash deployment evidence；partial 需 G3+未完成说明；failed/cancelled 不要求 preview但要求原因。
- [ ] 写 `finalize` 失败测试：缺 `skill-usage.md`/`retrospective.md`、artifact/review/gate 文档漂移、投影不一致均不得提交 terminal event。
- [ ] 写 `finalize recovery` 测试：terminal event 已落而投影未替换时 reconcile；finalize 完成后 `validate-run --require-terminal` 再验证真实终态。
- [ ] 运行 `node --test labs/web-flow/web-flow/tests/*.test.mjs`；预期新增测试失败。
- [ ] 实现有限模式 scanner、事件重放/run/artifact 文档对账、projected-terminal 预验证与 finalize 后验证。
- [ ] 接入 `validate-run`、`finalize`；重跑 Node 全测试，预期全部通过。
- [ ] 运行 `wc -l` 检查五个 JS 文件预算；超出时按既定职责拆分后再次测试。

---

## Chunk 2：Markdown 导航与阶段 Skill

### Task 8：先迁移旧 trigger 合约，再删除主 YAML

**Files:**
- Create: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Modify: `tests/test_trigger_contracts.py`
- Create: `labs/web-flow/web-flow/references/workflow.md`
- Create: `labs/web-flow/web-flow/references/runtime-state.md`
- Create: `labs/web-flow/web-flow/references/external-capabilities.md`
- Modify: `labs/web-flow/web-flow/SKILL.md`
- Modify: `labs/web-flow/web-flow/scripts/lib/validators.mjs`
- Modify: `labs/web-flow/web-flow/scripts/web-flow-runtime.mjs`
- Delete: `labs/web-flow/web-flow/workflow.yaml`
- Delete: `labs/web-flow/web-flow/external-skills.yaml`

- [ ] 先修改现有 Python 合约，使其期待主 Skill 链接 `references/workflow.md`、调用 benchmark、阶段拥有 memory 候选且无中心 memory。
- [ ] 运行 `python3 -m unittest tests.test_trigger_contracts -v`；预期因新 Markdown 尚不存在/主 Skill仍指向 YAML 而失败。
- [ ] 写 package 失败测试：必要 references、语义导航、独立 YAML 禁令、旧文件名禁令、archive/memory 排除，以及所有活跃 Markdown 的相对链接可解析。
- [ ] 运行 `node --test labs/web-flow/web-flow/tests/package-validation.test.mjs`；预期失败。
- [ ] 写 `workflow.md`、`runtime-state.md`、`external-capabilities.md`；JS 是机器事实源，Markdown 只解释与导航。
- [ ] 精简主 Skill 为触发边界、不变量、入口与“何时/为何读”的链接；删除两个主 YAML。
- [ ] 实现 `validate-package` 的 required files、broken relative link、禁 YAML/旧引用与有限敏感扫描。
- [ ] 运行 `node --test labs/web-flow/web-flow/tests/package-validation.test.mjs` 与 `python3 -m unittest tests.test_trigger_contracts -v`；预期通过。

### Task 9：迁移 research

**Files:**
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Modify: `labs/web-flow/web-flow-research/SKILL.md`

- [ ] 加失败断言：research 不引用 YAML，确切产物为 `research/content-spec.md`、`reference-evidence.md`、`asset-requirements.md`、`stage-result.md`，并包含五类内容来源。
- [ ] 运行 package test；预期 research 断言失败。
- [ ] 更新 research SOP、按需能力与 benchmark 交接；保留 internal-only 触发边界。
- [ ] 重跑 package test；预期通过。

### Task 10：迁移 prototype

**Files:**
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Modify: `labs/web-flow/web-flow-prototype/SKILL.md`

- [ ] 加失败断言：wireframe 与 full prototype 的确切 HTML/stage-result 路径、G1/G2、attempt/review 版本路径、fast 的 G2 not applicable。
- [ ] 运行 package test；预期 prototype 断言失败。
- [ ] 更新两个模式的 SOP 与 artifact/review/gate 登记步骤；重跑 package test，预期通过。

### Task 11：迁移 design

**Files:**
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Modify: `labs/web-flow/web-flow-design/SKILL.md`

- [ ] 加失败断言：fast 消费 approved wireframe、full 消费 approved prototype；确切产物为 `design/design-tokens.css`、`layout-contract.md`、`stage-result.md`。
- [ ] 运行 package test；预期 design 断言失败。
- [ ] 更新 design SOP，明确 run 内 CSS 是契约证据、实际样式由 build 写入 sourceDir；重跑测试，预期通过。

### Task 12：迁移 build 与 update 安全 SOP

**Files:**
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Modify: `labs/web-flow/web-flow-build/SKILL.md`

- [ ] 加失败断言：源码只写 `sourceDir`；确切证据为 `preexisting-state.md`、`build/preview-evidence.md`、`build/stage-result.md`；禁止并行写同一源码树。
- [ ] 加失败断言：update 在 build 前 source plan、dirty conflict 阻断、build 后 allowlist/baseline 验证。
- [ ] 运行 package test；预期 build 断言失败。
- [ ] 更新 build SOP 与 G3 流程；重跑 package test，预期通过。

### Task 13：迁移 benchmark

**Files:**
- Create: `labs/web-flow/web-flow-benchmark/references/rubrics.md`
- Create: `labs/web-flow/web-flow-benchmark/references/review-template.md`
- Modify: `labs/web-flow/web-flow-benchmark/SKILL.md`
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`
- Delete: `labs/web-flow/web-flow-benchmark/rubrics.yaml`
- Delete: `labs/web-flow/web-flow-benchmark/score-result.template.yaml`

- [ ] 加失败断言：六阶段 rubric 小节、must-pass/权重/阈值/0-3-5 锚点、review template 必需字段、版本化 review 路径，无 YAML 引用。
- [ ] 运行 package test；预期 benchmark 断言失败。
- [ ] 把现有 rubric 迁入 Markdown并补 factual claim、实时 hash、桌面/移动、HTTP/browser/console 证据。
- [ ] 写 review template；精简 benchmark Skill 为独立性、两轮/recheck、按需 rubric 与 Node 登记命令；删除两个 YAML。
- [ ] 重跑 package 与 Node 全测试；预期通过。

### Task 14：迁移 provider-neutral deploy

**Files:**
- Create: `labs/web-flow/web-flow-deploy/references/cloudflare-pages.md`
- Modify: `labs/web-flow/web-flow-deploy/SKILL.md`
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`

- [ ] 加失败断言：入口 provider-neutral；Cloudflare 命令只在 reference；确切产物为 `preflight/deployment-readiness.md`、`deploy/deployment-evidence.md`、`deploy/stage-result.md`。
- [ ] 加失败断言：G3 后 finalize 前补授权、publish 前重新 preflight、`deploy record` 绑定 build hash 与三项事实证据、失败保持 preview/partial。
- [ ] 运行 package test；预期 deploy 断言失败。
- [ ] 更新 deploy Skill 与 Cloudflare reference；重跑 package/deployment tests，预期通过。

### Task 15：更新 README 与显式分发边界

**Files:**
- Modify: `labs/web-flow/README.md`
- Modify: `labs/web-flow/web-flow/tests/package-validation.test.mjs`

- [ ] 加失败断言：README 包含七条具体 `j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/<skill>"`、labs 不进入 `install.sh`、archive 不参与运行、Node 自检命令。
- [ ] 运行 package test；预期 README 断言失败。
- [ ] 更新 README 的 V3 概念、安装/链接、Node 前置、运行证据与验证命令。
- [ ] 重跑 package test 与两个 Python 合约测试；预期通过。

---

## Chunk 3：可复制 smoke、独立 review 与完成验证

### Task 16：增加真实 CLI smoke

**Files:**
- Create: `labs/web-flow/web-flow/tests/runtime-smoke.test.mjs`

- [ ] 写一个使用 `spawnSync(process.execPath, [cli, ...])` 的 fast-profile smoke：临时 Git 项目中执行 init、artifact add、typed transition、review record、G1/G3 gate、finalize success、删除 run.json 后 reconcile。
- [ ] smoke 内断言：`.gitignore` 仅一条 `.web-flow/`；`site/` 在项目根且不在 runDir；events sequence 连续；review/gate hash 匹配；final `status=success`；reconcile 前后 `stateHash` 相同。
- [ ] 运行 `node --test labs/web-flow/web-flow/tests/runtime-smoke.test.mjs`；若暴露命令缺口，先保留失败，再最小修复对应模块。
- [ ] 重跑同一命令；预期 `1..1`、pass 1、fail 0、退出码 0。

### Task 17：独立实现 review

**Files:**
- Review: `docs/superpowers/specs/2026-07-11-web-flow-v3-design.md`
- Review: `labs/web-flow/**` 活跃文件

- [ ] 派发未参与实现的 reviewer，对照规格检查 Markdown-first/JS-first、事件权威、源码归属、update 安全、gate/review 漂移、部署和终态矩阵。
- [ ] 每个阻断问题先补精确失败测试，再做最小修复；重复 review 直到 Approved。
- [ ] 运行 `wc -l labs/web-flow/*/SKILL.md`，确认每个 Skill ≤500 行；运行 package test 确认 frontmatter 名称与目录一致。

### Task 18：分层完成验证

**Files:**
- Test: `labs/web-flow/web-flow/tests/*.test.mjs`
- Test: `tests/test_trigger_contracts.py`
- Test: `tests/test_benchmark_naming_contract.py`

- [ ] 运行 `node --test labs/web-flow/web-flow/tests/*.test.mjs`；预期全部通过。
- [ ] 运行 `node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs validate-package`；预期输出 `WebFlow package valid`、退出码 0。
- [ ] 运行 `python3 -m unittest tests.test_trigger_contracts tests.test_benchmark_naming_contract -v`；预期 5 项通过。
- [ ] 运行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`。
- [ ] 运行 `python3 scripts/audit_skills.py --scan-shared-content`。
- [ ] 运行 `bash -n install.sh` 与 `claude plugin validate --strict .`。
- [ ] 运行 `git diff --check`。
- [ ] 运行 `rg -n 'workflow\.yaml|external-skills\.yaml|rubrics\.yaml|score-result\.template\.yaml|validate_web_flow\.py' labs/web-flow --glob '!**/archive/**' --glob '!**/memory/**'`；预期无输出。
- [ ] 若全仓验证被用户既有无关改动阻断，保留现场并区分 WebFlow scoped 结果与外部失败；不修、不回滚无关文件。
- [ ] 不 commit、不 push、不清理 ignored memory、不删除机器上的历史断链。
