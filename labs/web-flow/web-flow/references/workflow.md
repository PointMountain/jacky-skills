# WebFlow 工作流导航

> 本文解释人类如何选择路径与找到阶段契约。合法状态、事件字段和终态矩阵以 [JS 运行时合约](runtime-state.md)为准。

## 一、先确认输入

每个 run 至少需要产品意图和项目根目录，并明确以下选择：

| 维度 | 选项 | 说明 |
| --- | --- | --- |
| 源码模式 | `create` / `update` | create 写入新的 sourceDir；update 只允许修改已确认的路径 |
| 执行模式 | `attended` / `unattended` | attended 在视觉门等待用户；unattended 依据独立评审自动决策 |
| profile | `fast` / `full` / `adaptive` | 决定是否制作高保真 prototype；G1 后不可再改 |
| 部署请求 | `true` / `false` | 只表示目标；真实发布仍需 G3 后的用户授权 |

`sourceDir` 必须是项目内相对路径。create 模式要求目标为空或不存在；update 模式要求目录已存在且属于 Git 项目。

## 二、选择 profile

### fast

`research → wireframe → G1 → design → build → G3 → 可选 deploy`

适合结构清楚、视觉方向已知、验证成本较低的页面。G2 记为 not applicable，不能伪造 prototype 通过记录。

### full

`research → wireframe → G1 → prototype → G2 → design → build → G3 → 可选 deploy`

适合参考站仿做、复杂品牌表达、关键动效或交互需要先验证的任务。

### adaptive

先按研究证据决定 fast 或 full，并在 G1 决策时锁定。锁定后不能为赶进度临时插入或移除 prototype。

## 三、阶段与工件

| 阶段 | 负责 Skill | 核心工件 |
| --- | --- | --- |
| research | [web-flow-research](../../web-flow-research/SKILL.md) | `research/content-spec.md`、`reference-evidence.md`、`asset-requirements.md`、`stage-result.md` |
| wireframe | [web-flow-prototype](../../web-flow-prototype/SKILL.md) | `wireframe/wireframe.html`、`stage-result.md` |
| prototype | [web-flow-prototype](../../web-flow-prototype/SKILL.md) | `prototype/prototype.html`、`stage-result.md` |
| design | [web-flow-design](../../web-flow-design/SKILL.md) | `design/design-tokens.css`、`layout-contract.md`、`stage-result.md` |
| build | [web-flow-build](../../web-flow-build/SKILL.md) | sourceDir、`build/preview-evidence.md`、`stage-result.md` |
| deploy | [web-flow-deploy](../../web-flow-deploy/SKILL.md) | `preflight/deployment-readiness.md`、`deploy/deployment-evidence.md`、`stage-result.md` |

阶段结束后先登记 artifact revision，再调用 [web-flow-benchmark](../../web-flow-benchmark/SKILL.md)。评审文档、rubric、artifact revision 和 hash 必须同时绑定，之后才能做 gate 决策或进入下一阶段。

## 四、三个视觉门

- G1：确认信息架构和阅读路径；同时锁定 profile。
- G2：只属于 full profile，确认高保真视觉与关键交互。
- G3：确认真实 sourceDir 构建出的桌面与移动预览。

用户选择 revise 时回到产物所属阶段，并产生新的 artifact revision、review round 和 gate decision；不得覆盖旧证据。用户选择 reject 时进入 cancelled；暂时不决定则进入 deferred/blocked，等待明确恢复。

## 五、部署和终态

部署请求不等于部署授权。只有 G3 已批准后，用户才能追加授权；发布前必须重新验证 preflight。未请求或未授权部署时，交付已批准 preview 即可成功结束。

终态只有 `success`、`partial`、`failed`、`cancelled`。任何终态都通过运行时 `finalize` 产生，并在提交后再次验证。完整命令与恢复方式见[运行时状态](runtime-state.md)。
