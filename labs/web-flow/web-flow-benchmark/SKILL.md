---
name: web-flow-benchmark
description: "web-flow 内部的独立多维评测阶段：按当前 stage rubric 先验 must-pass，再对主观质量评分，每轮只给一个 top_fix，最多两轮并输出结构化 YAML。仅在 web-flow 主 Skill 明确调用时使用。不要因普通用户请求单独触发。"
---

# web-flow-benchmark · 有限评测

> 评分负责发现问题，不负责制造无限循环；memory 只接收经过根因验证的错误，不接收所有低分。

## 输入

- `stage`、`round`（1 或 2）
- 本阶段真实产物
- 内容、原型或设计参考
- 可复核的测试、浏览器或命令证据

只读取 `rubrics.yaml` 中当前 stage；不要加载其他阶段细节。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只读取 rubric、硬校验、加权计算和停止规则相关的 1–3 条记忆。benchmark 自身发生且通过三项验证的错误写回自己的 `memory/`；产物阶段的错误候选必须交回对应阶段 Skill。

## 独立性

评分必须交给没有参与本阶段生成的独立 AI，或至少使用干净上下文。评测 Agent 不能用生成者的自我说明代替产物证据。

## 一次评分

1. 读取当前 rubric 的 `must_pass`、维度、权重、阈值和 0/3/5 锚点。
2. 先逐项验证 `must_pass`，为每项写 `passed` 和 evidence。事实门修复后的重新验证不占用主观评分两轮。
3. 任一 `must_pass` 失败：`decision: blocked`，指出一个最先要恢复的事实条件；不计算“平均后通过”。
4. 硬校验全过后，对每个主观维度打 0–5 分并给证据；加权均分公式为 `sum(score × weight) / sum(weight)`，保留两位小数。
5. 只选择一个对结果影响最大且当前可改的 `top_fix`。
6. 按 `score-result.template.yaml` 输出 YAML；`decision` 只能是 `pass/revise_once/proceed_with_residual/blocked`，不输出另一套 Markdown 打分卡。

## 两轮规则

```text
round 1 达阈值 → pass
round 1 未达阈值 → revise_once，只修 top_fix
round 2 → 停止主观评审循环
  达阈值 → pass
  未达阈值 → proceed_with_residual，不要求收敛
任意轮 must_pass 失败 → blocked，修复事实条件后重新验证
```

第二轮后的 residual 要保留，但不能自动写进 memory。

## memory candidate

只有发现可能跨次复现的真实错误时才附候选，并分别回答：

- `actual_error`：是否真的发生，而非审美偏好？
- `root_cause_verified`：根因是否有代码、测试、命令、数据或用户确认？
- `likely_to_recur`：同类任务未来是否可能再发生？

三项同时为 true 才能交回发生错误的阶段 Skill，由该 Skill 在自己的 `memory/` 中查重并写入；benchmark 自己不保存其他阶段的 memory。

## 边界

- 不引入 rubric 之外的“更漂亮”要求；
- 不在一轮同时要求修多个问题；
- 不用高分掩盖链接打不开、产物不存在等事实失败；
- 不保存评测 Agent 的冗长原始推理，只保存分数、证据、决定和候选。
