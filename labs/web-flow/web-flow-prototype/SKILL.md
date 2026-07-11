---
name: web-flow-prototype
description: "web-flow 内部的原型设计阶段：以 wireframe 和 prototype 两种模式，把源接地内容转成低保真草图与可观察的视觉或交互原型；运行时按需复用外部能力，缺失时降级为 HTML/CSS。仅在 web-flow 主 Skill 明确调用时使用。不要因普通用户请求单独触发。"
---

# web-flow-prototype · 草图与视觉原型

> 原型不是“让图片模型出一张图”。它复现人真实的设计过程：先排结构并评审 G1，再做视觉原型并评审 G2。

从 `../web-flow/workflow.yaml` 读取当前 mode、输入、具体输出路径和统一 stage-result 契约。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只沿当前 mode 和外部原型工具相关入口读取 1–3 条记忆；不存在时直接继续。通过三项验证的候选只写回本 Skill 的 `memory/`。

## `wireframe` 模式（G1）

1. 从 `content_spec` 和 `reference_evidence` 确认受众、主任务、主行动与必须出现的信息。
2. 按用户完成任务的顺序建立信息架构，明确首屏重点与页面节奏。
3. 生成可真实打开的低保真 HTML 草图，检查信息层级、阅读路径和桌面/移动布局。
4. 写 `wireframe/stage-result.yaml`，调用 `web-flow-benchmark` 的 `wireframe` rubric。
5. attended 模式给用户看 G1；unattended 模式必须在进入 prototype 前完成独立评分和至多一次 `top_fix`。

## `prototype` 模式（G2）

1. 读取已评审 wireframe 与 `asset_requirements`，区分必须验证的关键素材和可用占位符表达的非关键素材。
2. 对 `prototype_design` 及必要的 `visual_asset_generation` 执行“本轮首次使用才探测”；已有有效状态直接复用，失败或证据失效才刷新。
3. 使用第一个满足输入输出的候选；全部不可用时降级为本地 HTML/CSS，不静默跳过原型。
4. 形成可打开的视觉或交互原型，保留与内容证据、草图和关键素材需求的对应关系。
5. 真实观察桌面与移动视图，检查主行动、层级、可读性和关键状态。
6. 写 `prototype/stage-result.yaml`，调用 `web-flow-benchmark` 的 `prototype` rubric。
7. attended 模式给用户看 G2；unattended 模式使用独立评分结果进入 design。

本 Skill 只选择与编排，不复制外部 Skill 的完整说明，也不把供应者写死为永久依赖。

## 决策轨迹

每个 mode 都按 `workflow.yaml` 写 `observations/evidence/decision/actions/validation/errors/root_cause/next_rule`，并把工件登记进 `artifact-manifest.yaml`。只写可审计事实，不写冗长原始推理。
