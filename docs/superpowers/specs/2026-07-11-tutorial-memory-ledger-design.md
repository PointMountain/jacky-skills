# Tutorial to HyperFrames：V2 学习闭环设计

> 让 Skill 像真实学习者一样完成“提取 → 生成 → 观看 → 修正 → 复盘 → 沉淀”，同时保持主入口薄、运行事实可验证、长期记忆有门槛。

## 一、上位哲学

本设计参考用户当前最新的《自进化 Skill 设计哲学 V2》，只吸收其原则，不提交或改写主工作树中的未跟踪哲学文档。

一句话定义：

> **复盘还原一次运行的事实，评分发现当前产物的问题，memory 只保留会改变未来决策的已验证经验；主 Skill 只做导航与调度。**

遵守九条原则：

1. 从真实人类 SOP 反推阶段，而不是先画组件图；
2. 观察、行动、验证同等重要；
3. `SKILL.md` 是地图，不是百科全书；
4. 当前运行保存结构化决策轨迹，不保存内部思维过程；
5. 两轮评审只修一个 `top_fix`，不无限收敛；
6. 候选能力不等于实际使用，使用清单必须绑定结果与证据；
7. 低分、审美意见和一次失败不是长期 memory；
8. 没有真实内容就不预建空 memory、map 或目录；
9. 当前证据优先于旧经验，冲突时更新旧记忆状态。

## 二、真实人类 SOP

完整提取过程单独放在 `references/extraction-protocol.md`，按 SOP 卡记录触发、输入、观察、证据、判断、行动、产物、验收、异常和候选。

核心链路：

```text
来源授权与媒体识别
→ 音轨/字幕提取与 cue 复核
→ 全片粗抽帧
→ 关键段密集抽帧与小主体放大
→ 屏幕代码取证
→ tutorial_fact / visual_observation / code_fact / inference 分层
→ method / motion handoff
→ Demo 生成、机械验收、R1、单点修正、R2
→ 任务事实复盘与候选分流
```

字幕只能证明口播；运动关系必须查看真实帧。屏幕代码事实与实现推断必须分开。提取的原视频、完整字幕、私人素材和真实路径始终留在被忽略的 run 中。

## 三、薄工作流与职责边界

### 3.1 `SKILL.md` 只保留

- 触发边界与自动/协作模式；
- 全局不变量；
- 现有 12 阶段路由；
- must-pass、两轮停止与 blocked 条件；
- “何时读取哪个 reference”的语义入口；
- 结束时必须复盘和候选分流。

具体命令、字段、提取方法、评分细节和记忆规则移入一层 references。

### 3.2 稳定能力与运行状态分开

`capabilities.json` 是稳定能力槽位注册表，只记录候选、优先级、探测和 fallback，不声称当前机器一定可用。

本轮探测写入私有 `runtime-capabilities.json`：

```json
{
  "checked_at": "<timestamp>",
  "capabilities": {
    "local_transcription": {
      "status": "available",
      "selected": "audio-to-subtitle",
      "evidence_refs": ["transcript.json"],
      "fallback": null
    }
  }
}
```

阶段依赖 capability ID，不把某个工具名写死为唯一答案。

## 四、运行事实工件

复杂 workflow `1.1.0` 在原 12 阶段之外增加终止态 sidecar，不新增 `reflect` 阶段，也不重新渲染已冻结 final MP4。

### 4.1 `memory-selection.json`

Phase 0 只读取 root index；存在相关记忆时最多读取一张主题 map（跨域最多两张）和 1–3 条原子 memory。无命中也记录空选择，但不创建空长期 memory 目录。

selection 保存采用/拒绝原因和当时的原子 memory 快照/hash，使长期条目更新后仍能理解本轮用了什么。当前证据冲突时拒绝旧 memory，并形成候选。

### 4.2 `decision-trace.json`

只记录可审计事实链：

```text
observation → evidence → decision → action → validation
→ error → root_cause → next_rule
```

至少覆盖 extraction、plan_demo、R1→revise 三个真实判断点。没有证据的 root cause 必须为 `null`。

### 4.3 `skill-usage-manifest.json`

Skills 清单从 usage ledger 独立出来，每条至少包含：

```json
{
  "capability": "motion_observation",
  "phase": "observe_motion",
  "candidates_checked": ["animate-prompt", "ffmpeg-frame-sampling"],
  "selected": "ffmpeg-frame-sampling",
  "source": "local-binary",
  "revision": "<version-or-hash-or-null>",
  "mode": "fallback",
  "inputs": ["local_media"],
  "outputs": ["motion-spec.json"],
  "result": "passed",
  "evidence_refs": ["motion-spec.json", "frames/transition-strip.png"],
  "friction": null,
  "adjustment_candidate": null
}
```

“被列为候选”“被调用过”“目录存在”都不等于有效。`result=passed` 必须能定位到真实产物、测试或日志；证据不足只能是 `degraded`、`failed` 或 `not_recorded`。

### 4.4 `usage-ledger.json`

记录本轮实际读取和使用的内容、底层工具与产物。它由逐次 `usage-events/*.json` 聚合，不能只在结束时凭模型总结：

- source/artifact 只用 run-relative ref、逻辑 ID 和真实 hash；
- 工具记录名称、可得版本、承担阶段、输入/输出和 execution receipt；
- 提取、抽帧、素材处理、check/render 和审阅取证都必须列出；
- 无法证明的历史使用明确写 `not_recorded`，不能用当前环境倒推；
- 不复制字幕全文、原 locator、私人路径或完整敏感 argv。

每条 usage event 包含 `kind=content|skill|tool`、stage、capability ID、实际 ID、用途、result/capture state 和 evidence refs。`record-usage` 自行读取 evidence refs 并记录真实 hash，不接受模型填 hash。每个已完成阶段在 workflow 中声明的 capability 都必须有至少一条事件，或一条明确的 `missing|degraded|not_recorded` 事件；因此 finalize 能发现漏记，而不是只验证已声明条目。

### 4.5 `retrospective.json`

复盘只汇总当前 run 已有事实，不增加第三轮评分：

```json
{
  "objective": "<目标>",
  "result": "success",
  "skills_manifest_ref": "skill-usage-manifest.json",
  "evidence": [],
  "findings": [
    {
      "type": "effective_pattern",
      "claim": "<可证伪陈述>",
      "evidence_refs": ["<真实证据>"],
      "applies_to": ["<边界>"],
      "destination_candidate": "reference",
      "status": "candidate"
    }
  ]
}
```

finding 类型：`effective_pattern`、`failure_root_cause`、`environment_fact`、`skill_friction`。归宿候选：`reference`、`local_memory`、`error_memory`、`skill_adjustment`、`backlog`。

没有 evidence refs 的 finding 只能进入 backlog。

## 五、候选分流与原子 memory

```text
通用有效模式 + 跨任务/重复验证 → Skill/reference
环境事实 + verified_at/边界 → gitignored local memory
真实错误 + 根因已验证 + 未来会复现 → 原子 error memory
重复能力摩擦/明确契约缺口 → skill_adjustment_candidate
猜测/单次低分/审美意见/residual → backlog
```

`record-feedback` 只生成候选。Reviewer 意见必须绑定 R2、测试或验证证据；用户纠正记录为 `asserted_user_instruction` candidate，不能由模型自行伪装成已确认 active 规则。当前会话中用户明确要求修改共享行为时，仍通过正常代码变更、测试和 Review 修回 Skill/reference。

post-run Review 或用户反馈不能回写已经冻结的 retrospective。`record-feedback` 把脱敏候选写入当前私有 run 的 `feedback-candidates/<candidate-id>.json`，绑定 run ID、final/R2 hash、evidence refs、适用边界和目标归宿。它不创建长期 `local/`，也不修改 final。`promote-memory --input feedback-candidates/<id>.json` 重新读取当前 run 证据；通过门槛后写原子 memory，并在私有 run 写一份 promotion receipt。用户反馈没有可复验证据时始终只保留 candidate。

长期层保持最小：

```text
local/                  # 整体 Git ignored；有真实 memory 时才创建
├── index.json          # 说明何时进入、为什么进入
├── memories/
│   └── <stable-id>.json
└── maps/               # 至少 3 条共享同一问题模型后才创建
```

一条 memory 只对应一个根因，包含现象、已验证根因、证据引用、下次规则、适用/不适用边界、状态和 verified_at。同根因更新原条；selection 已冻结当时快照。失效条目标为 `superseded` 或 `archived`。

## 六、兼容策略

当前两个真实 run 使用 workflow `1.0.0`，每个阶段绑定当前 `workflow.json` 的原 hash。直接覆盖会使历史 run 假性失效。

因此：

- 把当前原字节冻结为 `references/workflows/1.0.0.json`；
- 新 `workflow.json` 与 `references/workflows/1.1.0.json` 使用相同字节；
- validator 先读取 run，再按 `workflow_version` 选择历史文件和真实 hash；
- 新 run 默认 `1.1.0`，extension 初始为 `collecting`；preflight 完成后要求 selection，全部核心阶段完成后要求 sidecar `frozen`；
- `--core-only` 只跳过 learning sidecar，不跳过原 12 阶段、final 或 ffprobe；
- legacy `1.0.0` 默认继续验证；`--require-learning-memory` 要求先 backfill；
- extension 失败不触发核心阶段 invalidation。

backfill 只能从当时已经保存的 artifact、receipt、源码 manifest、评分和 final 推导事实。历史 Skills/工具证据不存在时写 `not_recorded`，不得用当前版本补造。它不自动产生长期 memory；重复执行必须幂等，并证明除新增 sidecar 和 `run.json.extensions` 外旧文件/final hash 不变。

## 七、确定性 helper

新增 `record_learning.py`，使用 Python 标准库：

```text
select-memory       生成最多 1–3 条选择与快照
record-capability   写运行时能力选择/降级及证据
record-decision     追加结构化事实轨迹
record-usage        逐次记录内容、Skill、工具及真实证据引用
finalize            校验并冻结 manifest/ledger/retrospective
record-feedback     写 run 内 post-run candidate，不改 final/retrospective
promote-memory      消费 candidate，通过证据门槛后写原子 memory 与 receipt
backfill            受限回填 legacy run
lint                查结构、断链、重复 ID、隐私和孤立项
```

模型负责语义陈述，脚本负责读取实际引用、重算 hash、校验枚举/边界和原子写。无需构建通用事件数据库、向量库、常驻服务、宿主签名系统或全工具执行代理。

`validate_run.py` 在 core 验证后校验 sidecar：

- 工件真实存在且 descriptor hash 匹配；
- capability/Skill/tool 的 passed 结果有真实 evidence refs；
- ledger、manifest、decision trace、retrospective 与当前 source/build/R1/R2/final 交叉绑定；
- candidate 分流满足 evidence 与枚举；
- 私有路径、字幕全文、token、Cookie、私钥、敏感 URL/argv 被拒绝；
- workflow 1.1 完成态缺任一必需 sidecar 时失败；
- legacy 只有显式 require 时要求回填。

## 八、隐私与公开边界

- `.learning/runs/` 中的 source、transcript、frames、runtime state、decision trace、usage events、manifest、ledger、retrospective、feedback candidate/promotion receipt 和 backfill sidecar 全部私有；
- `local/`、`experience.local.md`、`runtime.local.json` 全部 Git ignored；
- 长期 memory 不复制原视频、字幕全文、私人图片、绝对路径、凭证或完整命令；
- staged audit 必须拒绝强制暂存上述私人文件；
- 分享型 Skill 的行为规则修回 Skill/reference，不写 Codex 个人 auto memory；
- 上位 V2 哲学文档当前是用户未跟踪内容，本任务只读参考，不能误纳入提交。

## 九、验收

1. `SKILL.md` 保持少于 200 行，并直接语义路由一层 references；
2. 独立 `extraction-protocol.md` 覆盖音轨/字幕/抽帧/屏幕代码/事实分层/异常回退；
3. frozen workflow 1.0 字节/hash不变，新 workflow 1.1 默认启用 sidecar；
4. 原有 60 个测试继续通过；
5. 新测试覆盖 capability 状态、decision trace、逐次 usage events/阶段覆盖、usage manifest、ledger、retrospective、post-run candidate→promotion、渐进选择、隐私与 backfill；
6. 新 run 缺必需 sidecar 默认失败，`--core-only` 通过原核心；
7. 两个真实 legacy run backfill 后通过 `--require-learning-memory --ffprobe on`，final MP4 hash 不变；
8. 无真实 memory 时不创建 `local/`；有 memory 时最多加载 1–3 条；
9. `quick_validate.py`、py_compile、全部测试和 staged privacy audit 通过；
10. 独立安全/Skill Review 通过，Codex 与 Claude Code 安装链接刷新。
