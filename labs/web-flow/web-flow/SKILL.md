---
name: web-flow
description: "将一句话产品意图落地为真实、带动效、可部署的前端站点，通过 research/prototype/design/build/deploy 子 Skill 渐进执行，并在每阶段交接调用 web-flow-benchmark 做有限评测；每个子 Skill 独立维护自己的错误 memory。用于仿做网站、建设官网或落地页、产出项目代码并部署到真实 URL；不处理纯后端、纯 CLI 或非可视产物，单文件 HTML 成品应使用 crafted-web。"
---

# web-flow · 总地图

> 本文件只负责导航与调度。阶段事实以 `workflow.yaml` 为准，外部能力候选与降级以 `external-skills.yaml` 为准；不要一次性加载全部子 Skill。

## V2 不变量

1. **先观察真实 SOP**：每阶段都写清观察、证据、决定、行动和验证，不凭理想架构补步骤。
2. **渐进加载**：只加载当前阶段 Skill；到阶段入口再读取该 Skill 自己的 `memory/index.md` 和 1–3 条相关 memory，不存在时直接继续。
3. **外部能力按需探测**：能力在本轮第一次使用时才探测并缓存 `available/degraded/missing`、证据与 fallback；失败或证据失效才刷新。
4. **有限评分**：每个生产阶段由独立 AI 多维评分，每轮只修 `top_fix`，最多两轮，不追求主观收敛。
5. **事实门不放水**：`must_pass` 未通过时保持阻断，不能被平均分或轮次上限掩盖。
6. **低分不是记忆**：先生成 `memory_candidate`；真实错误、根因已验证、未来可复现三项同时成立才入库。

## 调度流程

1. **建本轮目录**：先确认目标项目根 `.gitignore` 已包含 `.web-flow/`（没有就补一条），再创建 `.web-flow/runs/<run_id>/`；所有状态只写相对路径，并脱敏 token、凭证、认证头、私有 URL 与私有绝对路径。
2. **判模式与授权**：用户明确要求无人值守时用 `unattended`；否则用 `attended`。另行记录 `deployment_authorized`，只有用户明确要求真实部署才为 true；无人值守本身不构成部署授权。
3. **只读调度记忆**：若主 Skill 自己的 `memory/index.md` 存在，只读取与调度相关的 1–3 条 memory；不扫描子 Skill 的 memory。
4. **做 preflight**：初始化本轮外部能力状态；仅在已获部署授权时调用 `web-flow-deploy` 的 `preflight` 模式。不要在开局遍历探测全部外部能力。
5. **逐阶段运行**：按 `workflow.yaml` 的 `research → wireframe → prototype → design → build → deploy`，到哪一步才加载哪个子 Skill；未获部署授权时在 G3 后交付 preview 并结束。
6. **阶段交接评测**：每阶段结束调用 `web-flow-benchmark` 对应 rubric；需要返工时只把 `top_fix` 交回原阶段一次。
7. **处理视觉门**：attended 模式在 G1 草图、G2 视觉原型、G3 真实预览停下给用户看；unattended 模式使用独立评分结果继续。
8. **沉淀错误**：候选交回发生错误的阶段 Skill，由该 Skill 在自己的 `memory/` 内验证、查重和归档；未验证项只留在本轮 residual。

## 结构化交接

每个阶段按 `workflow.yaml` 的具体 path 写工件，并同步更新本轮 `artifact-manifest.yaml` 与决策轨迹：

```text
观察 → 证据 → 决定 → 行动 → 验证 → 错误 → 根因 → 下次规则
```

这里只记录可审计事实，不保存冗长原始推理。最终交付至少包含真实预览或生产 URL、关键验证证据和仍存在的 residual。

## 按需文件

- 当前阶段与交接：`workflow.yaml`
- 外部能力选择：`external-skills.yaml`
- 评测细节：调用 `web-flow-benchmark`
- 错误记忆：由当前阶段 Skill 独立维护 `memory/`
- 历史方案：`archive/`，日常运行不读
