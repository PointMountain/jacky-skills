---
name: web-flow-research
description: "web-flow 内部的调研阶段：观察参考站和已有资料，把页面内容逐条绑定来源，产出内容规格、参考证据和素材需求。仅在 web-flow 主 Skill 明确调用时使用；当前阶段为 research。不要因普通用户请求单独触发。"
---

# web-flow-research · 源接地调研

从 `../web-flow/workflow.yaml` 读取 `research` 输入输出，不负责原型设计。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只读取参考采集、来源可信度和外部观察工具相关的 1–3 条记忆；不存在时直接继续。通过三项验证的候选只写回本 Skill 的 `memory/`，不进入中心 memory。

## 真实 SOP

1. **确认目标**：从用户意图提取受众、页面目标、主行动和不可编造的边界。
2. **观察参考**：通过本轮能力状态确保 `reference_observation` 可用；只在首次使用时探测并缓存，失败或证据失效才刷新。保存页面结构、截图或源码等可复核证据；不可用时走 fallback。
3. **建立来源表**：每条标题、功能、数据和卖点都绑定截图、代码、文档或用户原话；没有来源的内容标记缺口，不自行补写。
4. **提炼内容规格**：输出页面信息架构候选、内容优先级、主行动、必要状态和素材需求。
5. **复核完整性**：对照参考证据检查是否遗漏关键板块，并区分“事实内容”和“后续设计判断”。

## 产物

写入 `.web-flow/runs/<run_id>/research/`：

- `content-spec.yaml`
- `reference-evidence.yaml`
- `asset-requirements.yaml`
- `stage-result.yaml`，包含结构化决策轨迹和 `next: wireframe`

决策轨迹只记录观察、证据、决定、行动和验证，不写冗长原始推理。

## 交接评分

调用 `web-flow-benchmark` 的 `research` rubric。每轮只处理 `top_fix`，最多两轮；低分只生成候选，不直接写 memory。
