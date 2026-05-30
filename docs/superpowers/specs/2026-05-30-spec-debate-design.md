# spec-debate Skill 设计文档

> 让 Claude 与 Codex 对一份 spec 文档做**匿名对抗辩论**，由独立第三方裁判合成终稿。

- **状态**：设计已确认，待实现
- **日期**：2026-05-30
- **形态**：Claude Code Skill（落于 `jacky-skills/skills/spec-debate/`）
- **设计来源**：选型器交互确认（四阶段对抗评审 + 辩论加独立合成 + 第三方独立裁判 + 自适应停机 + 匿名化 + 结构化 JSON 契约）

---

## 一、目标与动机

### 解决什么问题

单个模型生成的 spec 文档容易有盲区：需求覆盖不全、边界遗漏、内部自相矛盾、过度设计。让**两个异构模型（Claude 与 GPT/Codex）相互对抗评审**，能用差异化视角暴露单模型自我点头时发现不了的问题，最终合成一份更扎实的 spec。

### 为什么是「辩论」而非「共识投票」

spec 是设计权衡，往往没有唯一正确答案。纯共识投票会把分歧抹平成平庸；辩论 + 独立合成则**保留分歧的张力**，由裁判择优，能产出更高质量的终稿。

### 异构的价值

辩论双方必须来自不同厂商（Claude vs GPT），否则会迅速趋同。匿名化进一步防止某一方因为"知道这是对手说的"而产生迎合或对抗偏见（anchoring）。

---

## 二、触发与接口

- **触发**：`/spec-debate <spec路径.md>` 或自然语言「辩论这份 spec」
- **输入**：单个 spec markdown 文件的路径（一次辩一份）
- **前置依赖**：
  - 本地已装 Codex CLI（`codex` 在 PATH；通过 `codex-companion.mjs` 驱动）
  - Claude Code 的 Agent 工具可用（用于起 Claude 侧辩手与裁判子 agent）

---

## 三、角色分配（4 实体）

| 角色 | 实体 | 职责 | 关键约束 |
|------|------|------|----------|
| **编排器** | Claude Code 主循环 | 调度轮次、匿名化转译、写日志、收敛判定 | **中立，绝不下场辩论** |
| **辩手甲** | fresh Claude 子 agent（Agent 工具） | 评审 spec、交叉批评、反驳 | 不知道对手是谁 |
| **辩手乙** | `codex-companion.mjs task --background` | 同上，GPT 侧视角 | 不知道对手是谁 |
| **裁判** | fresh Claude 子 agent | 读原 spec + 匿名辩论日志，合成终稿 | 零辩论记忆，独立产出 |

> 编排器与裁判都是 Claude，但**裁判是 fresh 子 agent、不带编排上下文**，保证"第三方独立裁判"的独立性。

### Codex 驱动机制

通过 codex 插件自带的 companion 脚本非交互驱动：

```bash
node "<codex-plugin>/scripts/codex-companion.mjs" task --background "<prompt>"
# → 返回 job-id
node "<codex-plugin>/scripts/codex-companion.mjs" result <job-id> --json
# → 取回 stdout
```

`<codex-plugin>` 在实现时动态定位：glob `~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs`，按版本号取最新；若 cache 路径缺失，回退到 `~/.claude/plugins/marketplaces/openai-codex/...` 下的同名脚本。两处都找不到 → 视为 Codex 未就绪（见 §7）。

---

## 四、结构化 JSON 契约

### 单条意见（finding）

```json
{
  "id": "F1",
  "location": "§3.2 / 某行 / 某需求点",
  "category": "需求覆盖|边界遗漏|内部矛盾|可实现性|过度设计|歧义",
  "severity": "blocker|major|minor",
  "claim": "问题陈述（一句话说清是什么问题）",
  "argument": "论据（为什么这是问题）",
  "suggestion": "改法（具体怎么改）"
}
```

**六类维度（spec 专用，固定）**：

| category | 含义 |
|----------|------|
| 需求覆盖 | 漏掉了应覆盖的需求 / 场景 |
| 边界遗漏 | 边界条件、异常路径、空态未考虑 |
| 内部矛盾 | spec 内部前后冲突 |
| 可实现性 | 技术上难落地 / 成本被低估 |
| 过度设计 | 引入了 YAGNI 的复杂度 |
| 歧义 | 表述模糊、可多种解读 |

### 每轮信封（envelope）

```json
{
  "findings": [ /* finding[] */ ],
  "converged": false,
  "remaining_disputes": ["F1", "F3"]
}
```

- `converged`：本方是否认为已无新观点可提
- `remaining_disputes`：本方认为仍未解决的 finding id 列表

### 解析与兜底

- Codex 易把 JSON 裹进散文 → 提示词强约束「只输出 JSON，不要任何解释文字」+ 正则抽取 ```json``` 块或最外层 `{...}` 兜底。
- 解析失败 → 对该方**重请求一次**；再失败则在 log 记 warning，把该轮该方视为空 findings 跳过（不中断整体流程）。
- **空 findings 不等于收敛**：若某轮**双方都**返回空/非法 findings，不得据此判定收敛提前停机——记为失败轮，编排器报告并按 §7 处理（重试该轮或询问用户），避免"空辩论"被误当成"已达成一致"。

---

## 五、流程（硬上限 3 轮）

```
┌─ 阶段 1：独立评审（1 次） ────────────────────────────┐
│ 编排器并行下发 [spec + 评审提示] 给 甲、乙（互不可见）  │
│ 甲、乙 各返回 round-1 findings JSON                     │
└────────────────────────────────────────────────────────┘
            │
┌─ 阶段 2-3：交叉评审 + 反驳（循环，≤3 轮） ─────────────┐
│ 编排器抹去来源（标"评审甲/乙"），把对方上一轮 findings  │
│   交叉发给每一方                                        │
│ 每一方：对每条对方意见表态（认同/反驳）+ 可提新发现     │
│   + 填 converged / remaining_disputes                   │
│ 编排器收敛判定：                                        │
│   两方 converged==true 且 remaining_disputes 均为空     │
│     → 停，进合成                                        │
│   否则 → 下一轮（轮数 < 3 才继续；满 3 强制停）         │
└────────────────────────────────────────────────────────┘
            │
┌─ 阶段 4：合成（1 次） ─────────────────────────────────┐
│ 裁判 fresh 子 agent 读 [原 spec + 完整匿名辩论日志]     │
│ 产出：                                                  │
│   - spec.final.md（纳入被采纳意见的重写稿）             │
│   - 采纳/驳回理由表（finding → 裁决 → 理由）            │
└────────────────────────────────────────────────────────┘
```

### 匿名化规则

- 交叉评审时，编排器把"辩手甲/乙"统一映射为中性标签（评审甲 / 评审乙），**任一方都不知道对方是 Claude 还是 Codex**。
- 传给裁判的日志同样匿名（裁判只看论点 merit，不看模型身份）。

### 收敛判定（自适应停机）

由**双方自声 + 编排器确认**：

```
stop = (甲.converged AND 乙.converged
        AND 甲.remaining_disputes == []
        AND 乙.remaining_disputes == [])
       OR round == 3
```

---

## 六、产物与状态持久化

落点：原 spec 同级新建 `<spec名>.debate/` 子目录，**原 spec 文件零改动**。

| 文件 | 内容 |
|------|------|
| `<spec名>.debate/debate-log.md` | 每轮的 JSON + 可读转录，**每轮增量写入**（可中途查看、断点续看） |
| `<spec名>.debate/spec.final.md` | 合成终稿 + 末尾「采纳/驳回理由表」 |

> 用户自行决定要不要用 `spec.final.md` 替换原文，skill 不自动覆盖。

debate-log.md 增量写入也充当**状态持久化**：每轮结束即落盘，中途失败可看到已完成的轮次。

---

## 七、异常处理

| 异常 | 处理 |
|------|------|
| Codex task 失败 / 超时 | 编排器报告，询问用户：**降级为「仅 Claude 双 agent」继续**（失去异构性但流程不断）还是中止。用户已确认接受此降级兜底。 |
| 某轮某方 JSON 不合法 | 严格提取 JSON 块 + 重请求一次；再失败记 warning，该方该轮视为空 findings 跳过 |
| spec 路径不存在 / 非 markdown | 直接报错退出，提示正确用法 |
| Codex 插件路径找不到 | 报告 Codex 未就绪，提示 `/codex:setup`，并提供仅 Claude 降级选项 |

---

## 八、验证策略

编排类 skill 难写传统单测，主验证 = 拿一份**样例 spec** 跑一次完整流程（dry-run 指"对固定样例 spec 实跑全流程"，非 no-op 空跑），逐项核查：

1. 产物齐全：`debate-log.md` + `spec.final.md` 两个文件都生成，且 `debate-log.md` 每轮 JSON 合法可解析
2. 收敛能在 ≤3 轮内停（不会无限循环）
3. 匿名化生效：日志中无"Claude/Codex/GPT"等模型身份泄漏给对方或裁判
4. 终稿 `spec.final.md` 确实纳入了被采纳的 finding，且理由表完整（每条 finding 都有裁决）
5. 降级路径：模拟 Codex 不可用，确认能提示并以仅 Claude 模式跑通

---

## 九、明确不做（YAGNI）

- ❌ 不做多 spec 批量辩论（一次一份；要批量就多次调用）
- ❌ 不做 3+ 模型混战（仅 Claude vs Codex 二元对抗）
- ❌ 不做纯共识投票模式（已选辩论+合成）
- ❌ 不自动覆盖原 spec 文件
- ❌ 不做 Web UI / 可视化（选型器已是一次性产物，与本 skill 无关）

---

## 十、目录结构（实现时）

```
jacky-skills/skills/spec-debate/
├── SKILL.md              # 触发、流程编排说明、提示词模板
└── (按需) references/    # 评审提示词、裁判提示词、JSON schema 等长内容
```
