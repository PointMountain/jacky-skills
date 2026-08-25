# Benchmark Skill 命名统一设计

## 目标

将核心职责为量化评分、打分或基准评测的 Skill 统一命名为 `xxx-benchmark`，让名称直接表达同一类职责。

## 命名边界

- 核心职责是按维度评分、产出分数或基准报告：必须使用 `-benchmark` 后缀。
- 仅在业务流程中附带健康分、置信度或 `score.json` 字段：不因内部评分概念改名。
- Skill 目录名、frontmatter `name`、触发命令和跨 Skill 调用名必须一致。
- `score`、`rating`、`rubric` 等仍可作为业务字段、产物名或流程术语。

## 本次迁移

| 原名称 | 新名称 |
|---|---|
| `harness-evaluator` | `harness-benchmark` |
| `ob-rate` | `ob-benchmark` |
| `web-flow-review` | `web-flow-benchmark` |
| `tw-scorer` | `tw-benchmark` |
| `agent-pipeline-score` | `agent-pipeline-benchmark` |

前两个是正式 Plugin Skill，第三个是实验性内部 Skill，后两个位于历史归档。旧 `plugins/knowledge-base/skills/harness-benchmark` 已在当前工作树中删除，本次不恢复。

## 一致性要求

正式 Plugin 的目录重命名要同步更新 `plugin.json`、根 Marketplace 版本和 README；实验性与归档 Skill 要更新其编排器、调用方和说明文档。仓库测试应固定这五个迁移结果，并由统一审计继续验证目录名与 frontmatter 一致。
