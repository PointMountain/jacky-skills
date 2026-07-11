# Self-Evolving Skill V2 Implementation Plan

> **For agentic workers:** REQUIRED: Use `subagent-driven-development` to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 保留 V1 `experience.local.md` 规范，同时建立以真实人类 SOP、渐进式加载、结构化决策轨迹、两轮评分和错误记忆为核心的 V2 通用设计哲学，并让 `web-forge` 成为首个完整实例。

**Architecture:** V2 主文档只保存不变量和导航，细节进入一层 references。`web-forge` 用 `workflow.yaml` 作为阶段事实源，以薄总调度路由 research → prototype → design → build → deploy；score 与 memory 横切各阶段，外部 Skill 每次运行先探测再选择。

**Tech Stack:** Markdown、YAML、Agent Skills、`j-skills`。

**工作区约束:** 当前 `main` 包含大量用户未提交改动，而且待优化的 `web-forge-*` 本身尚未跟踪。只修改下列明确文件；不暂存、不提交、不移动任何无关文件。

---

## Chunk 1: V2 权威文档

### Task 1: 建立薄总纲与渐进式 references

**Files:**
- Create: `docs/自进化-skill-设计哲学-v2.md`
- Create: `docs/self-evolving-skill-v2/human-sop.md`
- Create: `docs/self-evolving-skill-v2/progressive-loading.md`
- Create: `docs/self-evolving-skill-v2/yaml-contracts.md`
- Create: `docs/self-evolving-skill-v2/memory-and-scoring.md`
- Create: `docs/self-evolving-skill-v2/external-skills.md`
- Modify: `docs/自进化-skill-协议规范.md`
- Modify: `docs/抖音口播稿-会自我进化的skill.md`
- Modify: `docs/自进化skill-主张.html`

- [x] **Step 1:** 写 V2 总纲，只保留定位、第一性原理、三级接入、两条闭环和 references 路由。
- [x] **Step 1.1:** 写死三级最低契约：所有 Skill 默认具备自进化基因；轻量至少有观察/验证/候选，中量再加记忆，复杂工作流才启用完整 map/YAML/score；没有真实内容时禁止预建空结构。
- [x] **Step 2:** 在 references 中分别定义人类 SOP 反推、双层渐进加载、YAML 契约、错误记忆与两轮评分、外部 Skill 探测与降级。
- [x] **Step 3:** 明确“决策轨迹”只记录 `观察 → 证据 → 决定 → 行动 → 验证 → 错误 → 根因 → 下次规则`，不保存冗长原始推理。
- [x] **Step 4:** 给三份 V1/衍生文档增加状态说明：V1 保留，V2 为当前主规范。
- [x] **Step 5:** 检查所有相对链接可达，主总纲不复制 references 细节。

## Chunk 2: `web-forge` V2 实例

### Task 2: 建立 YAML 工作流与外部能力状态协议

**Files:**
- Create: `skills/web-forge/workflow.yaml`
- Create: `skills/web-forge/external-skills.yaml`
- Modify: `skills/web-forge/SKILL.md`
- Modify: `skills/web-forge/.gitignore`
- Modify: `README.md`

- [x] **Step 1:** 让 `workflow.yaml` 成为阶段、输入输出、评分键、视觉门和下一步的唯一事实源。
- [x] **Step 2:** 让 `external-skills.yaml` 定义能力候选、运行时探测、状态文件和降级路径，不提交易漂移的“已安装”结论。
- [x] **Step 3:** 将总 `SKILL.md` 压缩为模式判断、地图读取、按阶段调度和横切规则，删除重复评分维度。
- [x] **Step 4:** 在根 README 的独立 Skill 清单中加入 `web-forge-prototype`；不重新创建已被移除的 `skills/web-forge/README.md`，不改动 README 其他内容。
- [x] **Step 5:** 修改前保存 `README.md` 的限定路径基线 diff；只做定点 patch，验证时比较本轮新增 delta，避免覆盖用户已有改动。

### Task 3: 补齐真实原型设计阶段并校准相邻阶段

**Files:**
- Create: `skills/web-forge-prototype/SKILL.md`
- Modify: `skills/web-forge-research/SKILL.md`
- Modify: `skills/web-forge-design/SKILL.md`
- Modify: `skills/web-forge-build/SKILL.md`
- Modify: `skills/web-forge-deploy/SKILL.md`

- [x] **Step 1:** 使用官方 `skill-creator/scripts/init_skill.py` 初始化 `web-forge-prototype`，删除无用示例资源。
- [x] **Step 2:** 将原型阶段写成人类 SOP：观察参考与内容目标 → 信息架构 → 低保真草图 → 可交互/可视原型 → 观察验证 → 选择与记录。
- [x] **Step 3:** 原型 Skill 只做编排：运行时探测现有外部 Skill，优先复用，全部不可用时降级为 HTML 原型。
- [x] **Step 4:** research 只产证据化内容规格；design 消费已选原型并产 tokens/layout；build 产真实预览；deploy 同时支持前置预检与最终上线。

### Task 4: 修正评分与记忆闭环

**Files:**
- Create: `skills/web-forge-score/score-result.template.yaml`
- Modify: `skills/web-forge-score/SKILL.md`
- Modify: `skills/web-forge-score/rubrics.yaml`
- Create: `skills/web-forge-memory/.gitignore`
- Modify: `skills/web-forge-memory/SKILL.md`
- Modify: `skills/web-forge-memory/references/starter-kit.md`

- [x] **Step 1:** 评分输出改为 YAML：阶段、轮次、硬校验、维度分、加权分、`top_fix`、decision、`memory_candidate`。
- [x] **Step 2:** 每个阶段交接均由独立 AI 做多维评分；每轮只修 `top_fix`，最多两轮。第二轮后主观项不要求收敛并继续推进；事实性 `must_pass` 不参与平均分，也不能因轮次用完而伪装成成功。
- [x] **Step 3:** 低分先生成候选；只有真实错误、根因已验证、未来可复现同时成立才写 memory。
- [x] **Step 4:** 开局只读根 index 路由，到阶段入口再读相关 map 和 1–3 条记忆，避免重复全读。
- [x] **Step 5:** 真正忽略 `local/` 与私有配置；保留现有本地记忆，不删除、不重写。

## Chunk 3: 验证与安装

### Task 5: 结构、契约与注册验证

**Files:**
- Verify all files from Tasks 1–4

- [x] **Step 1:** 用 YAML 解析器读取全部新改 YAML 和 Markdown frontmatter，预期零解析错误。
- [x] **Step 2:** 检查 V2 文档和 Skill 内所有相对链接，预期零断链。
- [x] **Step 3:** 检查 `workflow.yaml` stages 与 `rubrics.yaml` stage keys 一致。
- [x] **Step 4:** 检查新跟踪内容不包含真实 token、私有绝对路径或本机专用代理值。
- [x] **Step 5:** 运行官方 `quick_validate.py` 验证 `web-forge-prototype`。
- [x] **Step 6:** 用 `j-skills link` 与 `j-skills install -g --env claude-code,codex` 注册新 Skill，再从列表验证。
- [x] **Step 7:** 仅对本计划列出的路径运行 `git diff --check` 并复核相对基线新增的 delta；不把无关脏改动算入结果，不提交工作区。
