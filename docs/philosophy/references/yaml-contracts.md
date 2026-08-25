# YAML 最小契约

> YAML 负责机器可读的事实与交接；Markdown 负责语义解释、判断边界和阅读路径。

## 使用边界

适合 YAML 的内容：阶段 ID、输入输出、下一步、评分键、阈值、硬校验、运行状态和决策轨迹字段。

不适合 YAML 的内容：为什么进入某张知识地图、复杂根因解释、人类心智模型和长篇操作指南。

不要从 metadata 自动生成语义地图。机器可以校验链接与字段，不能替代语义策展。

## `workflow.yaml`

`workflow.yaml` 是例外，不是复杂任务的默认答案。开放任务默认由 Agent 维护运行时计划；需要让人阅读、协作或长期说明时，优先使用 Markdown 表达意图与边界。

只有以下三项同时满足时，才考虑把工作流写成 `workflow.yaml`：

1. 这套真实 SOP 已经过反复运行和验证，阶段与交接边界足够稳定；
2. 存在确定性机器解析、跨进程交换或 schema 校验需求；
3. Markdown 已不足以可靠承载这种机器契约。

如果缺少其中任何一项，就不应为了形式整齐而创建 `workflow.yaml`。即使满足例外条件，YAML 也只保留必要的机器事实；阶段细节留在对应 Skill 或 reference，解释与判断边界继续留在 Markdown，避免多处重复。

`SKILL.md` frontmatter、`agents/openai.yaml` 等平台协议强制要求的 YAML 不属于 `workflow.yaml` 的选择判断，继续按外部协议使用。

## 阶段结果与决策轨迹

```yaml
run_id: example-run
stage: prototype
status: completed
artifacts:
  - path: artifacts/prototype.html
decision_trace:
  observations:
    - "首屏没有明确主行动"
  evidence:
    - "reference:hero-screenshot"
  decision: "保留单一主行动，次要入口降级"
  actions:
    - "重排首屏信息层级"
  validation:
    - "桌面和移动预览均可识别主行动"
  errors: []
  root_cause: null
  next_rule: null
next: design
```

这是一条可审计事实链，不包含私密或冗长的原始思维过程。

## 评分结果

```yaml
stage: prototype
round: 1
reviewer: independent-agent
must_pass:
  - key: artifact_viewable
    passed: true
    evidence: "prototype opened successfully"
scores:
  - key: information_hierarchy
    score: 3
    weight: 2
    evidence: "主行动清楚，次要信息仍偏抢眼"
weighted_score: 3.4
threshold: 3.5
top_fix: "降低次要入口的视觉权重"
decision: revise_once
memory_candidate: null
```

## 字段纪律

- 使用稳定、简短的英文 key，说明文字可以使用任务语言；
- `evidence` 指向可复核事实，不写“感觉不错”；
- `status`、`decision` 使用有限枚举，避免同义词漂移；
- 可选字段用 `null` 或省略，不能伪造占位内容；
- YAML 不保存 token、私有绝对路径或长期有效的环境状态；
- 会漂移的运行状态写入被忽略的 `*.local.yaml` 或本轮运行目录。

## 最小原则

YAML 的价值是减少阶段间歧义，不是重建工作流引擎。没有多个阶段或机器交接需求时，轻量 Skill 不需要创建 `workflow.yaml`。
