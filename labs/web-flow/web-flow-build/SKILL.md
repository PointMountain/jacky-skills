---
name: web-flow-build
description: "web-flow 内部的实现阶段：按内容规格、已选原型、design tokens 和布局契约分 section 构建前端与动效，组装并验证真实预览。仅在 web-flow 主 Skill 明确调用时使用；当前阶段为 build。不要因普通用户请求单独触发。"
---

# web-flow-build · 实现与真实预览

从 `../web-flow/workflow.yaml` 读取 `build` 契约，不在本阶段修改内容来源或视觉方向。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只读取并行 section、动效、响应式和集成相关的 1–3 条记忆；不存在时直接继续。通过三项验证的候选只写回本 Skill 的 `memory/`。

## 真实 SOP

1. **拆实现单元**：按 `layout-contract.yaml` 的 slot 分工；每个执行者只接收当前 section 所需内容和共享 tokens。
2. **并行构建**：section 根元素带稳定 slot，样式和脚本限定作用域，避免交叉污染。
3. **按原型实现动效**：CSS 优先，动效必须支持信息理解或状态反馈；尊重减少动态效果设置。
4. **组装真实页面**：按布局契约拼装，保留内容来源和原型对应关系。
5. **观察验证**：通过本轮能力状态确保 `browser_verification` 可用；只在首次使用时探测并缓存，失败或证据失效才刷新。真实打开桌面与移动视图，检查溢出、遮挡、交互、资源和控制台。
6. **产 G3 预览**：attended 模式给用户看真实预览；unattended 模式交独立评分。

## 产物

写入 `.web-flow/runs/<run_id>/build/`：

- 可部署站点目录
- 本地或临时 `preview`
- `stage-result.yaml`，包含结构化决策轨迹和 `next: deploy`

## 交接评分

调用 `web-flow-benchmark` 的 `build` rubric。每轮只处理 `top_fix`，最多两轮；事实性 `must_pass` 未通过时不能伪装成预览成功。
