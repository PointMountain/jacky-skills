# 可复验学习闭环

> 让每次教程实践留下可复用事实，同时避免自报工具、空壳档案和无边界记忆增长。

闭环顺序固定为：memory selection → runtime capabilities → decision trace → usage events → `skill-usage-manifest` → `usage-ledger` → `retrospective` → `state=frozen` → candidate → gated promotion。

## 这不是思维链

它不是 CoT（思维链）存档。只记录外部可观察、可复验的信息：读取了什么内容、调用了哪个 Skill 或工具、得到什么受信回执、采用哪个公开决策、产物及其 hash、Review 指出的事实和最终行动。不要记录隐藏推理、自由联想或为了显得完整而补写的解释。

## Workflow 1.1.0 sidecars

所有路径均相对于私有 run 根目录 `.learning/runs/<run-id>/`。`required` 表示完成态 full validation 必须存在；optional 工件只在相应事件真实发生时创建。

| 相对路径 | 阶段 | 触发 | 必需性 | 机器事实 |
|---|---|---|---|---|
| `memory-selection.json` | `preflight` | `after_preflight` | `required` | 本轮查询、采用/拒绝结果及不可变选择快照 |
| `runtime-capabilities.json` | `preflight` | `after_probe` | `required` | 本轮真实 probe 状态，不继承历史安装状态 |
| `decision-trace.json` | `all` | `on_decision` | `required` | observation 到 validation/error/root cause 的可审计事实链 |
| `usage-events/*.json` | `all` | `after_usage_or_coverage` | `required` | 实际 content/Skill/tool 使用，或明确的能力覆盖状态 |
| `skill-usage-manifest.json` | `finalize` | `on_finalize` | `required` | 从已验证 usage event 投影出的 Skills 使用清单 |
| `usage-ledger.json` | `finalize` | `on_finalize` | `required` | 所有验证通过的 content/Skill/tool event 内容寻址索引 |
| `retrospective.json` | `finalize` | `on_finalize` | `required` | 仅汇总当前 run 已冻结证据的复盘与候选 finding |
| `feedback-candidates/*.json` | `post_run` | `on_feedback` | `optional` | Review 或用户反馈形成的追加式候选 |
| `promotion-receipts/*.json` | `post_run` | `on_promotion` | `optional` | 重新核验证据后的晋升回执 |

## Phase 0 memory selection

Phase 0 先读取长期层 root index；存在相关项时最多读取一张主题 map（跨域最多两张）和 1–3 条原子 memory。`preflight` 完成后始终写 `memory-selection.json`：无命中也写空 selection，以证明检索发生但没有采用旧经验；无真实长期 memory 时不要创建空 `local/`、index、map 或 memory。

```json
{
  "schema_version": "1.0.0",
  "workflow_version": "1.1.0",
  "run_id": "tutorial-run",
  "query": {
    "task_intents": ["learn_tutorial"],
    "mechanisms": [],
    "capability_ids": [],
    "conflicting_evidence_refs": []
  },
  "selected": [],
  "rejected": [],
  "selection_snapshot": {
    "selected": [],
    "rejected": []
  },
  "selection_snapshot_sha256": "<sha256-of-canonical-selection-snapshot>",
  "created_at": "<rfc3339>"
}
```

| 规则 | 结构约束 |
|---|---|
| `empty_memory` | `empty_selection_required`, `no_empty_local` |

有命中时，`selected[]` 与 `rejected[]` 都保存 stable memory ID、revision、采用/拒绝原因和当时快照 hash；被采用条目还保存原子 memory snapshot。当前证据冲突时拒绝旧 memory 并形成候选。`selection_snapshot_sha256` 由确定性 helper 对 canonical snapshot 重算，不接受模型自报。

## Sidecar 最小结构

字段名是机器契约。通配路径中的每个 JSON 都是独立不可变事件；所有 sidecar 携带所属 run 与 workflow 版本。

| 相对路径 | 必需字段 |
|---|---|
| `memory-selection.json` | schema_version, workflow_version, run_id, query, selected[], rejected[], selection_snapshot, selection_snapshot_sha256, created_at |
| `runtime-capabilities.json` | schema_version, workflow_version, run_id, registry_version, registry_sha256, probed_at, capabilities{} |
| `decision-trace.json` | schema_version, workflow_version, run_id, decisions[] |
| `usage-events/*.json` | schema_version, workflow_version, run_id, event_id, kind, stage, capability_id, actual_id, purpose, result, capture_state, evidence_refs[], recorded_at |
| `skill-usage-manifest.json` | schema_version, workflow_version, run_id, entries[] |
| `usage-ledger.json` | schema_version, workflow_version, run_id, event_refs[], manifest |
| `retrospective.json` | schema_version, workflow_version, run_id, objective, result, skills_manifest_ref, evidence[], findings[] |
| `feedback-candidates/*.json` | schema_version, workflow_version, run_id, candidate_id, final_hash, r2_hash, evidence_refs[], applies_to[], destination, received_at, source, claim, next_validation |
| `promotion-receipts/*.json` | schema_version, workflow_version, run_id, promotion_id, candidate_id, destination, evidence_refs[], source_candidate, promoted_revision, created_at |

Manifest entry 至少包含 capability、phase、checked candidates、selected、source、revision、mode、inputs、outputs、result、evidence refs、friction 和 adjustment candidate。`result=passed` 必须能回到真实产物、测试或日志；证据不足只能降级。

所有 path 都是相对 run 根目录的规范化路径，不允许绝对路径或 `..`。所有 sha256 都是对应文件实际字节的小写 64 位 SHA-256。

## run.json extension 与校验

新 run 只使用下面这一种初始化形态；不要再写 `version` 字段或数组型 `sidecars`：

```json
{
  "workflow_version": "1.1.0",
  "extensions": {
    "learning_loop": {
      "required": true,
      "state": "collecting",
      "contract_version": "1.0.0",
      "selection": null,
      "sidecars": {}
    }
  }
}
```

`preflight` 后 `selection` 指向 `memory-selection.json` 的 descriptor。后续 `sidecars` 是“run 相对路径 → descriptor”的 object；key 必须等于 descriptor.path。完成态示例：

```json
{
  "workflow_version": "1.1.0",
  "extensions": {
    "learning_loop": {
      "required": true,
      "state": "frozen",
      "contract_version": "1.0.0",
      "selection": {
        "path": "memory-selection.json",
        "sha256": "<sha256-of-selection-bytes>"
      },
      "sidecars": {
        "runtime-capabilities.json": {
          "path": "runtime-capabilities.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        },
        "decision-trace.json": {
          "path": "decision-trace.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        },
        "usage-events/event-0001.json": {
          "path": "usage-events/event-0001.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        },
        "skill-usage-manifest.json": {
          "path": "skill-usage-manifest.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        },
        "usage-ledger.json": {
          "path": "usage-ledger.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        },
        "retrospective.json": {
          "path": "retrospective.json",
          "sha256": "<sha256-of-sidecar-bytes>"
        }
      }
    }
  }
}
```

Validator 必须确认 selection/sidecar 文件真实存在且为普通文件，按 allowlist 拒绝越界路径，读取实际字节重算 SHA-256，并交叉核对 run ID、workflow/contract 版本、event/evidence/manifest/ledger 引用和 coverage。Extension 错误只使 learning validation 失败，不触发原 12 阶段 invalidation。

## Usage event kind 分支

每个 usage event 共有 `kind`、`stage`、`capability_id`、`actual_id`、`purpose`、`result`、`capture_state`、`evidence_refs`。分支契约如下：

| kind | 特有字段 | receipt 策略 |
|---|---|---|
| `content` | `content_ref`, `content_sha256` | `forbidden` |
| `skill` | `version`, `execution_receipt.path`, `execution_receipt.sha256` | `required_when_captured` |
| `tool` | `version`, `execution_receipt.path`, `execution_receipt.sha256` | `required_when_captured` |

`content` 记录本轮实际读取的 source/artifact，只绑定真实 run-relative ref 和脚本重算的内容 hash，不要求工具 receipt。`skill`/`tool` 在 `captured` 时绑定可得版本与受信 execution receipt；版本不可得时保留 `null`，不能从当前环境猜测历史版本。

`runtime-capabilities.json` 的 `capabilities{}` 以 capability ID 为 key。每项统一使用 `probes[]`，probe 包含 registry candidate ID、有限 `result` 和真实 evidence refs。`ordered_fallback` 按 registry 优先级记录已探测前缀并选择第一个通过或可降级候选；`all` 模式必须覆盖全部候选，`selected` 是所有通过候选的数组。`status`、`selected` 与 `fallback` 必须能由 probe 结果和 registry fallback 机械推导。

Execution receipt 本身必须是 JSON 对象，至少包含 `receipt_type=execution`、非空字符串数组 `command`、非布尔整数 `exit_code` 和带时区的 RFC3339 `executed_at`。可选 `stdout`、`stderr`、`target` 出现时必须是可重算 hash 的真实引用。`passed` 只接受 `exit_code=0`，`failed` 只接受非零；`degraded` receipt 不能支撑 manifest 的 `passed`。

## Usage coverage

| 规则 | 结构约束 |
|---|---|
| `kind_enum` | `content`, `skill`, `tool` |
| `capture_state_enum` | `captured`, `missing`, `degraded`, `not_recorded` |
| `result_enum` | `passed`, `degraded`, `failed`, `not_recorded` |
| `stage_capability` | `completed_stage`, `workflow_capability`, `event_or_coverage` |
| `silent_absence` | `finalize_fails` |
| `evidence_hash` | `record-usage`, `read_evidence_refs`, `recompute_sha256`, `reject_self_reported_hash` |

对每个已完成 stage，workflow 声明的每个适用 capability 必须有真实 event，或有 `capture_state=missing|degraded|not_recorded` 的明确 coverage event。无执行不能静默缺席；finalize 按 workflow stage/capability 矩阵发现漏记，而不是只检查已经声明的条目。

`record-usage` 自行读取 `evidence_refs`、content ref 和 execution receipt，重算真实 hash 后才写不可变 event。模型 draft 中的 hash 只可作输入提示，不能作为机器事实。

## 各阶段写入纪律

| 阶段 | usage 规则 | 额外 sidecar |
|---|---|---|
| `preflight` | `event_or_coverage` | `runtime-capabilities`, `memory-selection` |
| `ingest` | `event_or_coverage` | `decision-trace` |
| `transcript` | `event_or_coverage` | `none` |
| `learn_method` | `event_or_coverage` | `decision-trace` |
| `observe_motion` | `event_or_coverage` | `decision-trace` |
| `plan_demo` | `event_or_coverage` | `decision-trace` |
| `build` | `event_or_coverage` | `none` |
| `verify` | `event_or_coverage` | `none` |
| `review_r1` | `event_or_coverage` | `decision-trace` |
| `revise` | `event_or_coverage` | `decision-trace` |
| `review_r2` | `event_or_coverage` | `none` |
| `finalize` | `event_or_coverage` | `skill-usage-manifest`, `usage-ledger`, `retrospective`, `state=frozen` |

Decision trace 至少覆盖 extraction、`plan_demo` 和 R1→`revise` 三个真实判断点，并只写 observation → evidence → decision → action → validation → error → root_cause → next_rule 的可审计事实；没有证据的 root cause 必须为 `null`。

## Freeze 与 post-run feedback

| 时期 | 允许写入 | 禁止改写 |
|---|---|---|
| `collecting` | `memory-selection`, `runtime-capabilities`, `decision-trace`, `usage-events` | `final`, `final_hash` |
| `finalize` | `skill-usage-manifest`, `usage-ledger`, `retrospective`, `state=frozen` | `third_review`, `rerender_after_freeze` |
| `post_run` | `feedback-candidate`, `promotion-receipt` | `retrospective`, `final`, `skill-usage-manifest`, `usage-ledger` |

三个语义 draft 可以在同一次 finalize 中同批校验，但确定性落盘顺序唯一为 `skill-usage-manifest` → `usage-ledger` → `retrospective` → 原子 `state=frozen`。因此 retrospective 的 `skills_manifest_ref` 在写入时已有有效前置。Finalize 同字节重试幂等，不同字节拒绝覆盖。冻结后 post-run Review 或用户反馈绝不回写 retrospective、R2、final、manifest 或 ledger，也不触发第三轮评分或重新渲染。

## Candidate 与 promotion

| 规则 | 结构约束 |
|---|---|
| `feedback_binding` | `run_id`, `final_hash`, `r2_hash`, `evidence_refs`, `applies_to`, `destination`, `received_at`, `source`, `claim`, `next_validation` |
| `post_run_append_only` | `feedback_candidate_only`, `no_retrospective`, `no_final_mutation` |
| `promotion_revalidation` | `reread_evidence`, `recompute_hash`, `write_receipt` |

`record-feedback` 只生成私有 candidate。Reviewer 意见必须绑定 R2、测试或验证证据；用户纠正保存为 `asserted_user_instruction` candidate，不能由模型伪装成 active 规则。没有可复验证据时始终留在 candidate/backlog。

`promote-memory` 重新读取 source candidate 与当前 run 的 final/R2/evidence，逐项重算 hash，通过归宿门槛后才写原子 memory，并在 `promotion-receipts/` 写不可变 receipt。Promotion 不消费当前环境推测，不回写冻结工件。

## 候选分流

- 通用有效模式且跨任务重复验证 → `reference` candidate。
- 环境事实具备 `verified_at` 与适用边界 → Git ignored `local_memory` candidate。
- 真实错误具有已验证根因和未来复现边界 → 原子 `error_memory` candidate。
- 重复能力摩擦或明确契约缺口 → `skill_adjustment` candidate。
- 猜测、单次低分、审美意见或 residual → `backlog`。

长期 `local/` 只在首条真实 memory 晋升时原子创建。每条 memory 只对应一个根因；同根因更新原条并保留旧 selection snapshot，失效条目标记 `superseded` 或 `archived`。

## 版本边界

| workflow_version | 默认验证 | 显式模式 | extension state |
|---|---|---|---|
| `1.1.0` | `full` | `native` | `collecting_or_frozen` |
| `1.0.0` | `valid_without_v2` | `backfill` | `backfilled` |
| `unknown` | `fail_closed` | `none` | `none` |

新 run 默认 `1.1.0`。Legacy `1.0.0` 默认按冻结 workflow 和原 hash 继续有效；`--require-learning-memory` 才要求显式 backfill。`--core-only` 只跳过 learning extension，不跳过原 12 阶段、final 或 ffprobe。

## Backfill 约束

| 规则 | 结构约束 |
|---|---|
| `eligible` | `completed`, `workflow=1.0.0` |
| `sources` | `saved_artifacts`, `saved_receipts`, `scores`, `final` |
| `unknown_usage` | `not_recorded`, `no_current_environment` |
| `immutability` | `sidecars`, `run.json.extensions`, `old_files_unchanged`, `final_hash_unchanged` |
| `idempotence` | `byte_identical` |
| `long_term_memory` | `no_active_memory` |

Backfill 是显式、受限、幂等迁移：只从旧 run 当时保存的 artifact、receipt、源码 manifest、score 与 final 推导 `historical_best_effort` 工件，生成空历史 selection，并设 `state=backfilled`。未知 Skill/tool 一律写 `not_recorded`，禁止读取当前环境补造历史。

重复 backfill 必须产生同字节结果。除新增 sidecar 和 `run.json.extensions` 外，旧文件、阶段 hash 链与 final hash 保持不变；backfill 不自动创建或激活长期 memory。

## 下一轮有限检索

下一轮最多读取 1–3 条与来源类型、失败模式或目标机制直接相关的经验，并记录采用或拒绝理由。旧经验只能提出检查项，不能覆盖本轮媒体证据、真实能力探测或用户边界。

若没有相关经验，仍写空 `memory-selection.json`，随后继续正常 workflow；不要创建空长期 `local/`。若经验与本轮证据冲突，以本轮证据为准，并把冲突送入候选等待复验。

## 完成条件

一次 native `1.1.0` 学习沉淀只有在以下条件满足时才可信：

1. selection 已冻结本轮查询、采用/拒绝理由和旧 memory snapshot/hash；
2. 每个 completed stage/workflow capability 都有 event 或明确 coverage；
3. content、Skill 和 tool event 通过各自证据分支校验；
4. manifest 能回到 ledger 的真实 event，ledger 能回到实际 evidence/receipt；
5. retrospective 只引用冻结前已有事实，post-run 反馈只追加 candidate；
6. validator 已重算所有 descriptor 和交叉引用，extension state 与版本边界一致。
