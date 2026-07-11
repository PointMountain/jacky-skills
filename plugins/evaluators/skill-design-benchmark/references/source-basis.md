# Source Basis

> 这些 ID 解释“准则从哪里来、如何推导”。评分时只在 rubric 中引用 ID；用户追问来源时再读本文件。

## 固定快照

- `G`：[`ConardLi/garden-skills@fbd6453`](https://github.com/ConardLi/garden-skills/tree/fbd6453c984e2a150c9553efe3075e1f62338df8)
- `W`：[`eze-is/web-access@6532d4d`](https://github.com/eze-is/web-access/tree/6532d4da491fc6af2a7f3a161d7d7c69d67bca80)，由本地研究镜像 `wangjs-jacky/web-access-study@8639949` 固定

正面机制说明什么值得奖励；样本自身的缺口说明不能把“写了规则”当成“已经稳定”。

## G-BOUNDARY

- **证据**：[`beautiful-article/SKILL.md:13-21`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/beautiful-article/SKILL.md#L13-L21)
- **观察**：先区分文章、应用和越界请求，越界时停止并澄清。
- **推导**：触发稳定性来自可执行边界和明确产物，不来自流程长度。
- **边界**：职责天然单一的 Skill，一两句精确边界即可满分。

## W-EVIDENCE

- **证据**：[`SKILL.md:39-45`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L39-L45)、[`SKILL.md:210-223`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L210-L223)
- **观察**：先定义完成，把每一步结果当证据；核实类任务回到一手来源。
- **推导**：高分需要完成定义、换路信号、最终验收和停止条件，而非步骤清单。
- **边界**：Prompt 宣称闭环不证明真实遵守，仍需行为案例。

## W-TRADEOFF

- **证据**：[`SKILL.md:47-61`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L47-L61)、[`SKILL.md:81-90`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L81-L90)
- **观察**：按 URL、登录态、动态交互等信号选工具，并写明成本、信息损耗和兜底关系。
- **推导**：评适用信号、tradeoff 和换路条件，不评固定工具优先级表。
- **边界**：具体工具只适用于联网任务，不能固化成通用顺序。

## G-CONTEXT

- **证据**：[`beautiful-article/SKILL.md:105-117`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/beautiful-article/SKILL.md#L105-L117)、[`web-design-engineer/SKILL.md:483-493`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/web-design-engineer/SKILL.md#L483-L493)
- **观察**：按阶段和 anchor 标明必读/按需资料，只加载命中的 recipe。
- **推导**：主文件应是入口地图；高分来自明确加载条件和最小必要上下文。
- **边界**：小型自包含 Skill 没有 references 也不扣分；关键约束不能被藏起来。

## G-SSOT

- **证据**：[`beautiful-article/SKILL.md:52-60`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/beautiful-article/SKILL.md#L52-L60)、[`web-video-presentation/SKILL.md:51-77`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/web-video-presentation/SKILL.md#L51-L77)
- **观察**：复杂流程只保留一份 plan，并把 `narrations.ts` 定为步数和文本的唯一真相源。
- **推导**：长任务应明确 canonical state，其他产物从它派生，避免复制漂移。
- **边界**：源码声称 SSOT 不等于消费者已统一；一次性任务可判定为不需要状态。

## G-ANCHOR

- **证据**：[`web-video-presentation/SKILL.md:258-285`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/web-video-presentation/SKILL.md#L258-L285)、[`SKILL.md:304-325`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/web-video-presentation/SKILL.md#L304-L325)
- **观察**：先做完整可验收的第 1 章，暴露缺口后再顺序或并行扩展。
- **推导**：重复多、并行或返工昂贵时，应先验证代表性切片。
- **边界**：低成本单路径任务不应被强制增加样板 checkpoint。

## G-DEGRADE

- **证据**：[`gpt-image-2/SKILL.md:20-82`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/gpt-image-2/SKILL.md#L20-L82)、[`check-mode.js:20-45`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/gpt-image-2/scripts/check-mode.js#L20-L45)
- **观察**：先探测能力，再本地执行、委托宿主或只交付 Prompt；禁止假装已出图。
- **推导**：依赖可缺失时，应区分完整完成、替代交付和无法执行。
- **边界**：脚本不能自动区分所有模式，样本本身也不应拿绝对满分。

## W-PREFLIGHT

- **证据**：[`check-deps.mjs:65-83`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/check-deps.mjs#L65-L83)、[`check-deps.mjs:95-167`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/check-deps.mjs#L95-L167)
- **观察**：确定性探测、复用或启动 Proxy、等待就绪，失败时给出下一步和日志位置。
- **推导**：好的前检提供事实、能否继续、恢复路径和可观察结果，而不只是报错。
- **边界**：该脚本会启动后台进程；应只在真正需要 CDP 的路径执行。

## W-RUNTIME

- **证据**：[`cdp-proxy.mjs:113-178`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/cdp-proxy.mjs#L113-L178)、[`cdp-proxy.mjs:202-277`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/cdp-proxy.mjs#L202-L277)
- **观察**：连接复用、命令 ID 映射、超时清理和加载等待被下沉到代码。
- **推导**：确定性协议、不变量和并发清理应由脚本保证，而非让 Prompt 反复解释。
- **边界**：传输层机制不证明页面业务正确；仍需失败场景测试。

## G-QA

- **证据**：[`beautiful-article/SKILL.md:66-101`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/beautiful-article/SKILL.md#L66-L101)
- **观察**：低风险节点内联检查，关键节点独立 Reviewer；所有 fail 先修复再汇报。
- **推导**：验证强度应与风险匹配，失败必须回流到产物；Reviewer 数量不加分。
- **边界**：简单 Skill 的确定性自检可能比多 Agent 更可靠、更省上下文。

## W-SAFETY

- **证据**：[`SKILL.md:92-103`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L92-L103)、[`cdp-proxy.mjs:288-373`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/cdp-proxy.mjs#L288-L373)、[`cdp-proxy.mjs:448-475`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/cdp-proxy.mjs#L448-L475)
- **观察**：Prompt 要求隔离和清理自建 Tab，但 Proxy 仍提供任意 JS、关闭 Tab、上传本地文件等高权限接口。
- **推导**：高风险 Skill 除了写授权和清理，还应尽量在实现层强制所有权、鉴权和危险动作边界。
- **边界**：绑定 loopback 降低远程暴露；这里评价的是 Prompt 契约没有被运行时完全强制。

## W-MEMORY-GAP

- **证据**：[`SKILL.md:225-249`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/SKILL.md#L225-L249)、[`match-site.mjs:18-45`](https://github.com/eze-is/web-access/blob/6532d4da491fc6af2a7f3a161d7d7c69d67bca80/scripts/match-site.mjs#L18-L45)
- **观察**：经验按域名命中后加载；写回主要依赖 Agent，自由文本缺少去重、冲突和过期强制。
- **推导**：记忆应匹配后渐进加载；若会影响执行，高分还需结构、来源、冲突和时效治理。
- **边界**：`updated` 日期不是自动过期机制，提示“只写事实”也不是硬闭环。

## G-CI-GAP

- **证据**：[`validate-skills.yml:31-49`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/.github/workflows/validate-skills.yml#L31-L49)、[`package.json:16-24`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/package.json#L16-L24)
- **观察**：CI 验证发布结构、打包和 README 同步，但不覆盖 Skill 的真实行为。
- **推导**：结构 CI 很重要，但不能让行动型或高风险 Skill 因“有 CI”直接拿满行为分。
- **边界**：这不否定发布校验价值；纯说明型小 Skill 不需要庞大测试套件。

## G-LATEST-GAP

- **证据**：[`beautiful-article/scaffold.sh:132-146`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/beautiful-article/scripts/scaffold.sh#L132-L146)、[`web-video-presentation/scaffold.sh:91-100`](https://github.com/ConardLi/garden-skills/blob/fbd6453c984e2a150c9553efe3075e1f62338df8/skills/web-video-presentation/scripts/scaffold.sh#L91-L100)
- **观察**：新脚手架使用 `latest`，不同日期的 fresh run 可能得到不同依赖。
- **推导**：承诺可复现时，应固定关键工具版本或把升级做成显式动作。
- **边界**：追随新能力可能是有意取舍；只有与承诺冲突时才扣分。
