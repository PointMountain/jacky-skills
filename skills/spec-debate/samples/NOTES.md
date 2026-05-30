# Dry-run 验证记录

> 2026-05-30 对 `sample-spec.md` 实跑全流程，验证 spec-debate skill。

## 流程实况

| 轮次 | 评审甲（Claude 子 agent） | 评审乙（Codex task） | 编排器收敛判定 |
|------|--------------------------|----------------------|----------------|
| R1 独立评审 | 6 finding，converged=false | 5 finding，converged=false | 继续 |
| R2 交叉评审 | converged=true，坚持插件 RCE 维持 blocker | 全盘认同甲，但仍挂 F001/F005，converged=false | **不停**（单方收敛不触发） |
| R3 反驳收尾 | 立场稳定 converged=true | 撤回未决，converged=true | **STOP**（双方收敛，第 3 轮内自然停） |
| 合成 | — 裁判 fresh 子 agent 5 条共识全采纳 → spec.final.md | | |

## 核查结果（对应 spec §8）

1. ✅ 产物齐全：`debate-log.md` + `spec.final.md` 均生成；4 轮 envelope JSON 全部合法可解析。
2. ✅ ≤3 轮停机：第 3 轮自然收敛，未触顶强停、无死循环。
3. ✅ 匿名：交叉评审/裁判提示词中无 Claude/Codex/GPT 等身份词（grep 验证）；身份仅存在于编排器自留日志头，未传给辩手/裁判。
4. ✅ 终稿纳入被采纳 finding，采纳/驳回理由表完整（5 条共识逐条有裁决）。
5. ✅ 三个埋点全部被捞出：边界遗漏（空输入）、歧义（字符规则未闭合）、过度设计（插件机制 + 远程加载 RCE）。
6. ⚠ 降级路径（Codex 不可用 → 双 Claude）已在 SKILL.md 设计，本次 dry-run 未触发（Codex 正常），留待真实缺失时验证。

## 关键经验（已回写 SKILL.md）

- Codex 驱动：`task --background` 起任务 → `status --json` 轮询 `"status":"completed"` → `result --json` 取 **`.job.summary`** 字段（即最终回答），对其做 JSON 抽取。
- 自适应停机的价值在 R2 显现：单方收敛**不能**触发停机，否则会过早结束；必须双方 converged 且 remaining_disputes 均空。
- 异构互补明显：甲从 YAGNI/RCE 切入，乙从「插件 vs 合法 slug 内部矛盾」切入同一设计缺陷，裁判合并后论据更全。
