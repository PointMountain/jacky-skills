# Skill Labs（预览版）

`labs/` 用于验证尚未稳定的新型 Skill、轻量 Workflow 和组织方式。

- 这里的内容可以试用，但不承诺稳定接口或向后兼容。
- 验证成熟后，独立 Skill 迁入 `skills/`，成组能力迁入 `plugins/`。
- 停止维护的实验迁入 `archived/`。

当前实验：

- [`web-flow`](./web-flow/)：面向网站交付的固定阶段 Workflow，依次串联调研、原型、设计、实现、评审与部署。
- [`app-flow`](./app-flow/app-flow/)：面向长任务 App 交付，不预设固定技术栈、阶段或交付形式，而是根据任务证据动态组织工作。

`web-flow` 适合沿固定交付阶段推进网站任务；`app-flow` 则为长任务 App Workflow 动态选择阶段与交付物。

## 手动预览安装

Labs 仅供手动预览安装，不进入 `./install.sh --all`。要试用 `app-flow`，请从仓库根目录执行：

```bash
j-skills link ./labs/app-flow/app-flow
j-skills install app-flow -g --env claude-code,codex
```
