# WebFlow Rubrics

> 六个阶段共用 0–5 分制、阈值 3.5、最多两轮主观评审。must-pass 是事实门，不能被加权分数抵消。

## 通用锚点

| 分数 | 锚点 |
| --- | --- |
| 0 | 缺失、不可用或没有证据 |
| 3 | 基本可用，但存在一个明确且可修的主要缺口 |
| 5 | 证据充分，完整满足本阶段目标 |

中间分数只在证据确实落于两个锚点之间时使用。weighted score 为 `sum(score × 权重) / sum(权重)`，保留两位小数。

## research

阈值：3.5。

Must-pass：

- `content_spec_exists`：内容规格存在、可读，并绑定当前 artifact revision 与实时 hash。
- `sources_resolvable`：关键事实声明能追溯到用户原话、项目源码、已有文档、参考网页或截图/录屏；gap 没有伪装成事实。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 内容完整度 | 2 | 目标内容缺失 | 核心 section 齐全但有一个明显缺口 | 页面目标、状态、行动与 gap 完整 |
| 源接地 | 2 | 事实无来源 | 多数事实可追溯但有一处弱绑定 | 所有关键事实逐项绑定可复核证据 |
| 任务理解 | 1 | 受众和目标错误 | 主任务正确但优先级不够清楚 | 受众、主行动和优先级清晰一致 |

## wireframe

阈值：3.5。

Must-pass：

- `wireframe_viewable`：当前 HTML artifact 可真实打开，文件字节与实时 hash 一致。
- `content_traceable`：草图关键内容可追溯到已登记内容规格。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 信息架构 | 2 | 无可用阅读路径 | 主路径成立但有一个排序缺口 | 首屏重点、内容顺序和节奏支持用户任务 |
| 任务清晰度 | 2 | 主行动不可识别 | 主行动可见但关键状态不足 | 主行动与关键状态均清楚 |
| 响应式结构 | 1 | 移动内容不可用 | 桌面/移动基本成立但一处拥挤 | 桌面与移动变化均有明确依据 |

## prototype

阈值：3.5。

Must-pass：

- `wireframe_approved`：输入是 G1 决策绑定的当前 wireframe。
- `prototype_viewable`：prototype 在桌面与移动 browser 视图都可真实查看，artifact 实时 hash 未漂移。
- `content_traceable`：关键内容可追溯到内容规格和 wireframe。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 信息架构 | 2 | 视觉破坏阅读路径 | 主路径成立但节奏有一处缺口 | 视觉层级强化既定阅读路径 |
| 任务清晰度 | 2 | 主行动被装饰淹没 | 主行动可用但反馈不足 | 主行动和关键状态清晰可观察 |
| 视觉方向 | 1 | 无一致主张 | 方向基本一致但辨识度一般 | 形成一致、具体且可实施的视觉主张 |
| 响应式意图 | 1 | 只考虑单一尺寸 | 桌面/移动可看但变化粗糙 | 两类视图都保留层级和操作意图 |

## design

阈值：3.5。

Must-pass：

- `tokens_parseable`：design tokens CSS 存在、语法可读，并绑定实时 hash。
- `layout_contract_exists`：sections、slots、断点、状态与动效契约存在。
- `approved_input_bound`：fast 使用 G1 wireframe，full 使用 G2 prototype，引用未漂移。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 视觉一致性 | 2 | 值互相冲突 | 主系统成立但有一处例外未解释 | 色彩、字体、间距和效果来自统一系统 |
| 层级清晰 | 1 | tokens 破坏主次 | 大体保留原型层级 | tokens 与布局稳定复现原型主次 |
| 实现清晰度 | 2 | 关键决定仍需猜测 | 可实现但有一个模糊接口 | 实现者无需重做关键设计决定 |

## build

阈值：3.5。

Must-pass：

- `preview_http_success`：当前 build 启动后 HTTP 请求成功。
- `critical_resources_load`：关键脚本、样式和媒体资源没有致命加载失败。
- `desktop_mobile_visible`：桌面与移动 browser 视图的关键内容可见、可操作。
- `console_blockers_absent`：console 没有阻断使用的错误。
- `source_verified`：update 的 allowlist 与 baseline 验证通过，sourceDir 实时 hash 与 preview artifact 绑定一致。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 原型还原度 | 2 | 与批准输入无关 | 主要结构一致但有一处明显偏差 | 信息、布局和视觉方向均忠实 |
| 动效质量 | 2 | 动效阻断使用 | 基本顺畅但一处反馈含混 | 动效有意义、流畅并支持 reduced motion |
| 实现质量 | 1 | 结构脆弱或互相污染 | 基本清晰但有一个维护缺口 | 结构清晰且 section 边界稳定 |
| 响应式质量 | 2 | 某视图不可用 | 桌面/移动可用但有一处明显妥协 | 两类视图都清晰、可读、可操作 |

## deploy

阈值：3.5。

Must-pass：

- `production_http_success`：公开 HTTPS URL 的 HTTP 状态成功。
- `production_browser_opens`：生产页面能在真实 browser 打开。
- `critical_errors_absent`：console 无阻断错误，关键资源无失败。
- `build_hash_matches`：部署证据绑定的 build hash 与当前 G3 artifact 实时 hash 一致。

| 维度 | 权重 | 0 分 | 3 分 | 5 分 |
| --- | ---: | --- | --- | --- |
| 交付清晰度 | 1 | URL 或证据缺失 | 可交付但 residual 不够明确 | URL、版本、证据与 residual 完整清楚 |
| 线上一致性 | 2 | 与批准 preview 不一致 | 主体一致但有一处环境偏差 | 线上页面与已批准 preview 完整一致 |
