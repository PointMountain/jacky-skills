---
name: web-flow-deploy
description: "web-flow 内部的部署阶段：在 build 前执行 Cloudflare Pages 就绪预检，在最终发布时部署并用 HTTP 与浏览器证据验证真实 URL。仅在 web-flow 主 Skill 明确调用时使用；支持 preflight 与 publish。不要因普通用户请求单独触发。"
---

# web-flow-deploy · 预检与发布

从 `../web-flow/workflow.yaml` 读取 preflight 或 `deploy` 契约。不要等到实现完成才发现凭证或项目条件不满足。

## 独立 memory

若本 Skill 的 `memory/index.md` 存在，只读取部署凭证、项目初始化和验活相关的 1–3 条记忆；不存在时直接继续。通过三项验证的候选只写回本 Skill 的 `memory/`。

## `preflight` 模式（build 前）

仅当结构化输入 `deployment_authorized: true` 时运行；无人值守模式不能替代该授权。

1. 检查部署 CLI 是否可执行，并验证当前登录身份。
2. 确认目标项目名与生产分支计划；查询项目是否存在。
3. 项目不存在时返回 `needs_project_create`，把创建动作留给已授权的 publish 流程。
4. 按 workflow 路径将命令、退出码和身份/项目检查结果写入 `preflight/deployment-readiness.yaml`，并登记 artifact manifest；失败立即返回阻断证据。

## `publish` 模式（G3 后）

1. 首先验证结构化输入 `deployment_authorized: true`；未授权时禁止创建项目或部署，只交付已验证 preview。
2. 读取 build 产物和 `deployment-readiness.yaml`，重新验证会漂移的登录状态。
3. 在项目缺失且本轮已授权部署时，先显式创建项目，再发布站点目录。
4. 保存生产 URL 和部署命令结果。
5. 用 HTTP 状态与真实浏览器打开结果验活，检查关键资源和控制台。
6. 验活失败时保留本地 preview，返回 `must_pass` 失败与证据；只生成 `memory_candidate`，不直接写 memory。

## 产物

- preflight：`.web-flow/runs/<run_id>/preflight/deployment-readiness.yaml`
- publish：`.web-flow/runs/<run_id>/deploy/deployment-evidence.yaml`
- publish stage result：`.web-flow/runs/<run_id>/deploy/stage-result.yaml`，包含生产 URL、结构化决策轨迹和 residual

## 交接评分

publish 后调用 `web-flow-benchmark` 的 `deploy` rubric。主观评分最多两轮；URL、资源和控制台等 `must_pass` 必须以真实证据通过。
