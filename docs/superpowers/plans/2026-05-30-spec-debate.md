# spec-debate Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个 Claude Code Skill，让 Claude 与 Codex 对单份 spec 文档做匿名对抗辩论，由独立裁判合成终稿。

**Architecture:** Markdown 形态 skill。`SKILL.md` 是编排器剧本（Claude Code 主循环按它执行：调度子 agent / Codex task、匿名化转译、收敛判定、写日志、调度裁判）。长提示词与 JSON schema 抽到 `references/`，由编排器按需读取并注入到各子 agent / Codex 的提示中。验证靠对固定样例 spec 实跑全流程（dry-run）。

**Tech Stack:** Claude Code Skill（SKILL.md frontmatter + 流程说明）、Agent 工具（起 Claude 辩手/裁判子 agent）、codex-companion.mjs（驱动 Codex）、bash（路径发现、JSON 抽取、增量写日志）。

---

## File Structure

```
jacky-skills/skills/spec-debate/
├── SKILL.md                       # 编排剧本：触发、4 阶段流程、收敛/异常逻辑
├── references/
│   ├── reviewer-prompt.md         # 阶段1 独立评审提示词 + JSON 契约
│   ├── cross-review-prompt.md     # 阶段2-3 交叉评审/反驳提示词
│   ├── judge-prompt.md            # 阶段4 裁判合成提示词
│   └── json-contract.md           # finding / envelope schema 单一事实源
└── samples/
    └── sample-spec.md             # dry-run 用的样例 spec
```

职责边界：
- **SKILL.md** 只放编排控制流（顺序、循环、判定、文件落点），不内联长提示词正文。
- **references/*.md** 各放一类提示词全文，互不重叠；`json-contract.md` 是 JSON 结构的唯一定义，其余文件引用它而不重复。
- **samples/sample-spec.md** 是一份故意留有缺陷（缺边界、有歧义、轻微过度设计）的样例 spec，供验证用。

---

### Task 1: 脚手架 + json-contract 单一事实源

**Files:**
- Create: `jacky-skills/skills/spec-debate/references/json-contract.md`

- [ ] **Step 1: 写 JSON 契约**

`references/json-contract.md` 内容（finding + envelope 的唯一定义，供其余提示词引用）：

````markdown
# JSON 契约（spec-debate 唯一事实源）

## 单条意见 finding
```json
{ "id":"F1", "location":"§章节/行/需求点", "category":"需求覆盖|边界遗漏|内部矛盾|可实现性|过度设计|歧义",
  "severity":"blocker|major|minor", "claim":"问题陈述", "argument":"论据", "suggestion":"改法" }
```

## 六类 category
| category | 含义 |
|----------|------|
| 需求覆盖 | 漏掉应覆盖的需求/场景 |
| 边界遗漏 | 边界条件/异常路径/空态未考虑 |
| 内部矛盾 | spec 内部前后冲突 |
| 可实现性 | 技术难落地/成本被低估 |
| 过度设计 | 引入 YAGNI 复杂度 |
| 歧义 | 表述模糊可多解 |

## 每轮信封 envelope
```json
{ "findings":[ /* finding[] */ ], "converged": false, "remaining_disputes":["F1","F3"] }
```
- `converged`：本方是否认为已无新观点
- `remaining_disputes`：本方认为仍未解决的 finding id

## 输出纪律
只输出一个 JSON 对象，不要任何解释文字、不要 markdown 代码围栏外的内容。
````

- [ ] **Step 2: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add skills/spec-debate/references/json-contract.md
git commit -m "feat(spec-debate): JSON 契约单一事实源"
```

---

### Task 2: 三个提示词模板

**Files:**
- Create: `jacky-skills/skills/spec-debate/references/reviewer-prompt.md`
- Create: `jacky-skills/skills/spec-debate/references/cross-review-prompt.md`
- Create: `jacky-skills/skills/spec-debate/references/judge-prompt.md`

- [ ] **Step 1: 写独立评审提示词** `reviewer-prompt.md`

```markdown
# 独立评审提示词（阶段1）

你是一名严格的 spec 文档评审者。下面给你一份 spec，请按六类维度（需求覆盖/边界遗漏/内部矛盾/可实现性/过度设计/歧义）找出问题。

要求：
- 每条问题严格按 finding 结构输出（见 JSON 契约）。
- 只报真问题，不凑数；宁缺毋滥。
- 你不知道也不需要知道是否有其他评审者。
- 严格只输出 envelope JSON（findings + converged + remaining_disputes）。首轮 converged 填 false，remaining_disputes 填你所有 finding 的 id。

【SPEC 开始】
{{SPEC_CONTENT}}
【SPEC 结束】
```

- [ ] **Step 2: 写交叉评审/反驳提示词** `cross-review-prompt.md`

```markdown
# 交叉评审 / 反驳提示词（阶段2-3）

你是评审{{SELF_LABEL}}。这是你上一轮的意见，以及另一位评审者（评审{{OTHER_LABEL}}）的意见（来源已匿名，按论据本身判断，不要揣测对方身份）。

请：
1. 对评审{{OTHER_LABEL}}的每条意见表态：认同 / 反驳（给理由）。
2. 如有新发现可补充 finding。
3. 重新评估你的立场：若已无新观点且认可当前共识，converged 填 true、remaining_disputes 填仍未解决的 id（可为空）。

严格只输出 envelope JSON。

【原 SPEC】
{{SPEC_CONTENT}}

【你上一轮意见】
{{SELF_PREV}}

【评审{{OTHER_LABEL}}意见（匿名）】
{{OTHER_PREV}}
```

- [ ] **Step 3: 写裁判提示词** `judge-prompt.md`

```markdown
# 裁判合成提示词（阶段4）

你是独立第三方裁判，此前未参与辩论。下面是原 spec 与一场匿名对抗辩论的完整日志（双方身份已隐去，只看论据 merit）。

请：
1. 逐条裁决每个 finding：采纳 / 驳回，并给一句话理由。
2. 把所有"采纳"的意见落实到 spec，重写出改进后的终稿。
3. 终稿末尾附「采纳/驳回理由表」：| finding id | 裁决 | 理由 |。

输出格式：先输出完整的 spec.final.md 正文（markdown），再输出理由表。不要输出辩论复盘之外的寒暄。

【原 SPEC】
{{SPEC_CONTENT}}

【匿名辩论日志】
{{DEBATE_LOG}}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add skills/spec-debate/references/reviewer-prompt.md skills/spec-debate/references/cross-review-prompt.md skills/spec-debate/references/judge-prompt.md
git commit -m "feat(spec-debate): 三个提示词模板"
```

---

### Task 3: SKILL.md 编排剧本

**Files:**
- Create: `jacky-skills/skills/spec-debate/SKILL.md`

- [ ] **Step 1: 写 SKILL.md**

frontmatter + 完整编排流程。关键内容：
- frontmatter：`name: spec-debate`，`description` 含触发词（辩论 spec、spec-debate、对抗评审 spec、让 Claude 和 Codex 辩论文档）。
- **前置检查**：校验入参是 `.md` 路径且存在；否则报用法 `/spec-debate <spec路径.md>` 并退出。
- **Codex 发现**：glob `~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs` 取最新版本；缺失则回退 `~/.claude/plugins/marketplaces/openai-codex/.../codex-companion.mjs`；都没有 → 提示 `/codex:setup`，询问是否降级为「仅 Claude 双 agent」。
- **产物目录**：`<spec同级>/<spec名去后缀>.debate/`，建目录。
- **阶段1 独立评审**：读 `references/reviewer-prompt.md`，把 `{{SPEC_CONTENT}}` 注入。**并行**：一个 Claude 子 agent（Agent 工具，general-purpose）当辩手甲；同时 `node <companion> task --background "<prompt>"` 起 Codex 当辩手乙，记 job-id，随后 `result <job-id> --json` 取回。两方各得 round-1 envelope JSON。每轮取回后**立即增量写** `debate-log.md`。
- **JSON 抽取兜底**：从返回文本中提取 ```json``` 块或最外层 `{...}`；解析失败则对该方重请求一次；再失败记 warning、该方该轮按空 findings 处理。
- **阶段2-3 交叉评审循环（≤3 轮）**：编排器把双方角色映射为中性「评审甲/评审乙」（绝不向任一方或日志泄漏 Claude/Codex/GPT 身份）。用 `cross-review-prompt.md` 注入 `{{SELF_LABEL}}/{{OTHER_LABEL}}/{{SPEC_CONTENT}}/{{SELF_PREV}}/{{OTHER_PREV}}`，并行让双方产出新 envelope。**收敛判定**：`甲.converged && 乙.converged && 甲.remaining_disputes==[] && 乙.remaining_disputes==[]` → 停；否则 round<3 继续。**空轮保护**：若某轮双方都空/非法 findings，不判收敛，记失败轮并报告。
- **阶段4 合成**：起 fresh Claude 裁判子 agent，用 `judge-prompt.md` 注入原 spec + 完整匿名 `debate-log.md`；产出写入 `<...>.debate/spec.final.md`（含末尾采纳/驳回理由表）。
- **降级路径**：Codex 不可用且用户选降级 → 辩手乙也用一个 Claude 子 agent（不同 system 提示，扮演挑刺角色），其余流程不变，日志标注「降级：双 Claude」。
- **收尾**：打印产物路径，提示「原 spec 未改动，终稿在 spec.final.md，由你决定是否替换」。

- [ ] **Step 2: 校验 frontmatter 合法**

Run: `head -10 /Users/jiashengwang/jacky-github/jacky-skills/skills/spec-debate/SKILL.md`
Expected: 合法 YAML frontmatter，含 name + description。

- [ ] **Step 3: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add skills/spec-debate/SKILL.md
git commit -m "feat(spec-debate): SKILL.md 编排剧本"
```

---

### Task 4: 样例 spec（dry-run 用）

**Files:**
- Create: `jacky-skills/skills/spec-debate/samples/sample-spec.md`

- [ ] **Step 1: 写一份故意有缺陷的样例 spec**

一份小功能 spec（如"一个把剪贴板文本转为 slug 的 CLI"），故意埋：① 一个边界遗漏（未说空输入怎么办）② 一个歧义（"特殊字符"未定义范围）③ 一处轻微过度设计（无谓的插件系统）。用于验证辩论能否捞出这些。

- [ ] **Step 2: Commit**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add skills/spec-debate/samples/sample-spec.md
git commit -m "test(spec-debate): dry-run 样例 spec"
```

---

### Task 5: Dry-run 验证

**Files:** 无新文件（执行验证）

- [ ] **Step 1: 链接/安装 skill 到本地**

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
j-skills link spec-debate 2>&1 | tail -3
```

- [ ] **Step 2: 对样例 spec 实跑全流程**

按 SKILL.md 编排，对 `skills/spec-debate/samples/sample-spec.md` 跑一遍。

- [ ] **Step 3: 逐项核查（来自 spec §8）**

1. `sample-spec.debate/` 下 `debate-log.md` + `spec.final.md` 都生成；log 每轮 JSON 合法。
2. 辩论在 ≤3 轮内停（无死循环）。
3. 日志无 Claude/Codex/GPT 身份泄漏给对方或裁判。
4. `spec.final.md` 纳入了被采纳 finding，理由表每条 finding 都有裁决。
5. 三个埋入缺陷（边界/歧义/过度设计）至少被捞出 2 个。
6. 降级路径：临时令 Codex 不可用，确认提示并能以仅 Claude 模式跑通。

- [ ] **Step 4: 记录验证结果**

把 dry-run 结论追加到 `skills/spec-debate/SKILL.md` 末尾的「验证记录」小节（或 samples 旁的 NOTES）。Commit。

```bash
cd /Users/jiashengwang/jacky-github/jacky-skills
git add -A
git commit -m "test(spec-debate): dry-run 验证通过记录"
```

---

## Self-Review

- **Spec coverage**：§2 触发→Task3 前置检查；§3 角色/Codex 驱动→Task3 发现+调度；§4 JSON 契约→Task1+提示词；§5 四阶段流程→Task3；§6 产物落点→Task3；§7 异常→Task3（降级/抽取/空轮）；§8 验证→Task5；§9 YAGNI→计划未引入额外特性。全覆盖。
- **Placeholder 扫描**：提示词中的 `{{...}}` 是有意的注入占位符，由编排器在运行时替换，非计划占位；其余无 TODO/TBD。
- **类型一致**：envelope 字段（findings/converged/remaining_disputes）、finding 字段在 Task1 定义，Task2/3 引用一致；收敛判定式与 spec §5 一致。
