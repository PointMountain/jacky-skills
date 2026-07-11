---
name: web-flow-design
description: "web-flow 内部的设计系统阶段：消费已确认原型，提炼 design tokens 和布局契约，保证后续并行实现共享同一视觉与结构事实源。仅在 web-flow 主 Skill 明确调用时使用；当前阶段为 design。不要因普通用户请求单独触发。"
---

# web-flow-design · 设计系统

从 `../web-flow/workflow.yaml` 读取 `design` 契约。视觉方向以已选择的 prototype 为事实源，不在本阶段重新发明原型。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只读取设计一致性、布局契约和当前外部设计工具相关的 1–3 条记忆；不存在时直接继续。通过三项验证的候选只写回本 Skill 的 `memory/`。

## 真实 SOP

1. **观察原型**：识别层级、节奏、关键状态和桌面/移动差异，记录证据。
2. **提炼 tokens**：定义颜色、字体、间距、圆角、边框、阴影和动效节奏；每个值能追溯到原型或明确决策。
3. **建立布局契约**：定义 sections 顺序、slot、容器、断点和关键组件状态，作为并行实现的共同输入。
4. **检查一致性**：用少量代表性 section 验证 tokens 与布局能复现原型，不把工具默认样式当设计决策。

## 产物

写入 `.web-flow/runs/<run_id>/design/`：

- `design-tokens.yaml`
- `layout-contract.yaml`
- `stage-result.yaml`，包含结构化决策轨迹和 `next: build`

## 交接评分

调用 `web-flow-benchmark` 的 `design` rubric。每轮只处理 `top_fix`，最多两轮；`must_pass` 未通过时保持阻断。
