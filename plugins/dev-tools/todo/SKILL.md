---
name: todo
description: "通过 Node CLI 管理结构化 Markdown 任务：默认全局，可显式使用项目级；支持无人值守 Durable 准备度、最终产物验收契约、上下文章节、统计、索引、完整性检查和本地 Web 看板。"
---

# Todo

Todo 是自然语言适配层。任务数据保存在 `.agent-tasks/tasks/*.md`，确定性读写全部交给本 Skill 自带的 Node CLI。

## 第一性原则：状态服务于用户的时间主权

Todo 的目标不是让任务机械地穿过一组状态，而是帮助用户从持续盯守、重复确认和不可预期的等待中释放出来，同时保留对成本、进度和启动时机的掌控。

执行任何状态变更前，先以终为始地确认：

1. 用户最终想获得的结果和工作状态是什么，而不只是当前说出的流程动作。
2. 当前状态能为用户减少什么负担，提供什么新的确定性。
3. 接下来是否存在昂贵的时间、注意力、额度或外部副作用；用户是否已经看见并接受。
4. 是否存在更便宜、更快、同样能推进最终目标的路径。
5. 当前动作是在推进用户的终局，还是只是在完成 Skill 自己的流程。

决策优先级固定为：

```text
用户终局 → 时间与注意力 → 成本与风险透明 → 用户掌控点 → 最小流程 → 工具
```

流程、状态和工具都只是手段。一旦它们与用户希望“减少等待、释放注意力、把控整体进度”的核心诉求冲突，必须调整手段，不能以“已经严格执行流程”为完成依据。

## 硬约束

1. **禁止直接编辑任务文件、YAML、`index.md` 或归档目录。**
2. 新增、修改、查询、移动、归档和正文更新都必须调用 CLI。
3. 未明确指定范围时始终使用全局 `~/.agent-tasks/`，即使当前位于 Git 仓库。
4. 只有用户明确说“当前项目”或提供项目路径时才使用项目级目录。
5. 用户只要求记录、查看或修改任务时，不得执行任务本身。
6. `list` 只查询，不调研、不实现、不创建额外上下文文件。
7. `index.md` 是生成视图，`tasks/*.md` 是唯一数据源。

## CLI 调用

Skill 内调用：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" <command> [options]
```

如果宿主没有注入 `CLAUDE_SKILL_DIR`，使用当前 `SKILL.md` 所在目录的绝对路径。不要假设系统已经存在全局 `todo` 命令。

人工安装全局命令、依赖检查和 Web 启动方法见 [`references/setup-guide.md`](references/setup-guide.md)。

## 作用域

| 用户表达 | CLI 参数 | 存储位置 |
|---|---|---|
| “添加待办”“全局待办”或未说明 | 无 | `~/.agent-tasks/` |
| “当前项目待办” | `--current-project` | `{当前 git-root}/.agent-tasks/` |
| “某项目待办”并提供路径 | `--project <path>` | `{指定 git-root}/.agent-tasks/` |

明确项目无法解析时报告错误，不静默写入全局。

## 意图映射

### 新增任务

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" add "<标题>" \
  --status idea \
  --json
```

添加当前项目任务时追加 `--current-project`。添加指定项目任务时追加 `--project <git-root>`。

创建后向用户返回：

- `task_id`
- 标题和状态
- 实际文件路径

### 查询任务

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" list
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" list --status canDurable
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" show <TSK-ID>
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" stats --format yaml
```

### 修改 YAML

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" set <TSK-ID> \
  --project-name "<项目名>" \
  --workspace "<路径>"
```

Reference 使用逗号分隔：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" set <TSK-ID> \
  --references "references/设计.md,OBA-w8s3k7p2"
```

### 修改 Markdown 章节

Skill 更新上下文时使用标准输入，避免 shell 引号破坏正文：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section set <TSK-ID> "目标"
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section append <TSK-ID> "关键决定"
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section show <TSK-ID> "当前进度"
```

将正文通过标准输入传入。`set` 替换指定二级章节，`append` 保留旧内容后追加；两者不得影响其他章节。

### 修改状态

常规状态流：

```text
idea → shaping → canDurable → doing → done
                            ↘ waitingHuman ↗
```

`waitingHuman` 是例外分支，不是每个阶段后的默认步骤。状态可以按真实进展前后调整，不强制线性迁移。

| 状态 | 含义 |
|---|---|
| `idea` | 只有想法，尚未明确执行目标 |
| `shaping` | 正在补齐目标、最终产物或权限边界 |
| `canDurable` | 已满足无人值守执行条件，但尚未启动 |
| `doing` | 正在持续执行；中间文档、报告、决策与普通失败不改变此状态；已获得的 Durable 标记继续保留 |
| `waitingHuman` | 最终可回归产物已经就绪，或遇到必须由用户提供新权限/关键输入的真实阻塞；Durable 标记继续保留 |
| `done` | 自动验收已通过，并且不需要额外人工回归；或最终人工回归已确认；Durable 标记作为历史能力证据保留 |

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" status <TSK-ID> shaping
```

进入 `canDurable` 必须记录判断依据：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" status <TSK-ID> canDurable \
  --basis human-confirmed
```

合法依据：

- `poc-passed`
- `human-confirmed`
- `ai-assessed`

`durable_basis` 是任务的长程能力标记，不是临时状态附属字段。任务从 `canDurable` 进入 `doing`、`waitingHuman` 或 `done` 时必须保留；只有退回 `idea` / `shaping` 才自动移除。

### Durable 准备与执行授权

状态服务于用户安排时间，不能由 Agent 把“准备好”擅自解释成“立刻开工”：

| 用户意图 | 应做什么 | 最终状态 |
|---|---|---|
| “进入 Durable 状态”“把它变成可 Durable”“准备成 Durable” | 补齐目标、权限、最终验收与执行预估；达到条件后停止 | `canDurable` |
| “开始 Durable”“执行这个 Durable”“今晚跑起来” | 在已经满足 Durable 条件后启动长程执行 | `doing` |
| 同时明确要求“准备好并立即执行” | 先完成准备度检查，再开始执行 | `doing` |

硬约束：

1. **进入 `canDurable` 后默认停止。** 不得紧接着自动改为 `doing`，也不得开始实现、POC 或浏览器回归。
2. **执行必须单独获得授权。** 用户提供账号、凭据、生产环境权限或技术方案，只解决执行条件，不等于授权立即启动。
3. **进入 `canDurable` 前给出执行预估。** 在任务正文记录 `## Durable 执行预估`，至少包含预计耗时范围、主要阶段、最大不确定性和可能需要人工处理的最终节点。
4. **状态反馈必须说清是否已启动。** 例如：“已进入 `canDurable`，尚未执行；预计无人值守运行 8–12 小时。”

## Durable 判断

`canDurable` 表示任务已经适合用户离线、夜间或不值守时持续执行。判断重点不是“文档写得是否足够多”，而是：

1. 最终目标和范围已经稳定。
2. 用户最终要回归的产物类型、入口和验收动作已经提前约定。
3. Agent 具备独立完成任务所需的环境、能力和权限。
4. 普通实现选择存在安全默认值，失败时存在重试或回退路径。
5. 当前没有已知的高风险授权、关键凭据或产品方向选择阻塞执行。

满足以上条件即可进入 `canDurable`：

1. 用户已认可最终验收契约：使用 `human-confirmed`。
2. 可执行 POC 已证明关键路径：使用 `poc-passed`。
3. 用户不在场，但最终产物、权限和回退路径都明确：使用 `ai-assessed`。
4. 只有缺失信息会明显改变最终结果或导致任务根本无法启动时，才保持 `shaping`。

POC 只用于消除真正影响长程执行的技术不确定性，不得把“邀请用户参与 POC”变成 Durable 的固定前置步骤。

## POC 时间成本与确认门

POC 是 `shaping` 内的可选验证活动，不是进入 Durable 的默认动作。POC 可能消耗大量时间、调用额度并产生真实环境副作用，因此不得由 Agent 自行启动。

启动 POC 前必须先向用户展示一份简短确认信息：

1. **为什么需要**：它要消除哪一个阻止进入 `canDurable` 的关键不确定性。
2. **预计耗时**：给出区间，并标明主要耗时来自哪里。
3. **验证边界**：本次会做什么、明确不做什么，以及停止条件。
4. **环境与副作用**：是否登录真实账号、创建数据、发送消息、占用远端设备或修改外部状态。
5. **替代路径**：说明跳过 POC 后能否用 `human-confirmed` 或 `ai-assessed` 进入 `canDurable`，以及可靠性差异。

随后必须得到用户对本次 POC 的明确确认，例如“开始 POC”或“按这个时间预算执行”。以下内容都不构成 POC 授权：

- 用户只说希望任务进入 Durable；
- 用户提供了凭据或生产账号；
- 用户同意最终目标或验收标准；
- Agent 判断 POC 更稳妥。

POC 执行规则：

1. 未确认时保持 `shaping`，只完善任务上下文，不执行 POC。
2. 选择能消除关键不确定性的最小闭环，先使用便宜、只读、可逆的证据。
3. 到达预估上限、验证范围扩大或出现新的外部副作用时，停止并重新给出预估，不能静默延长。
4. POC 通过后可以使用 `poc-passed` 进入 `canDurable`，但仍然停止；只有用户另行要求启动，才进入 `doing`。
5. 在任务正文使用 `## POC 计划` 和 `## POC 结果` 记录预算、停止条件与结论，避免后续 Agent 重复昂贵验证。

## 无人值守执行与人工等待阈值

### 硬约束

1. **中间文档不设人工门。** 需求文档、研究报告、设计稿说明、决策矩阵、阶段总结、日志和其他辅助材料完成后，保存为 Reference 并继续执行。
2. **阶段结束不等于暂停。** 只要下一阶段仍在既定目标、权限和验收契约内，保持 `doing` 并自动继续。
3. **普通问题不等待。** 可逆实现选择、低风险分歧、依赖故障、测试失败和工具切换由 Agent 诊断、记录、重试或采用安全替代方案。
4. **文档类任务默认自动完成。** 若用户明确要求的最终产物就是文档，完成结构、链接、事实与格式检查后直接 `done`，提供可点击文件；除非用户明确要求逐段审阅，否则不进入 `waitingHuman`。
5. **不得为了流程完整而制造人工检查点。** “请确认继续下一阶段”“请阅读长报告后验收”不属于有效阻塞。

### 只有以下情况可以进入 `waitingHuman`

1. 全部实现与自动验证已经完成，最终产物必须由人体验才能判断，而且已提供可直接回归的入口。
2. 继续执行需要用户授予新的高风险权限、提供缺失凭据，或选择会明显改变最终产品结果的方向。
3. 已耗尽安全的诊断、重试和替代路径，外部状态不变化就无法继续。

如果只是希望用户“有空看看”，不进入 `waitingHuman`；保持 `doing` 继续工作，或在自动完成后设为 `done`。

## 最终验收契约

Durable 任务在开始前应在正文记录 `## 最终验收`，至少说明：

- 最终产物是什么；
- 用户从哪里进入；
- 用户需要执行的最短回归动作；
- Agent 会先完成哪些自动验证；
- 哪些情况才算失败。

按产物类型选择回归入口：

- **网页/应用**：部署可点击 URL；无法部署时提供一条启动命令、固定本地 URL 和 3–5 步回归路径。
- **E2E**：保存真实点击步骤、自动化结果、录屏视频和视频报告；用户主要看视频回归，不要求重跑整套过程。
- **Skill**：提供可直接复制的触发提示词、预期行为和最小测试输入；用户通过实际调用 Skill 验收。
- **CLI/API**：提供可复制命令或请求、预期输出和机器可读测试结果。
- **文档/研究**：提供可点击最终文件和自动检查结果，任务直接完成，不把阅读长文设为等待门。

完整模板和例子见 [`references/durable-acceptance.md`](references/durable-acceptance.md)。

## 执行记录

Durable 执行期间在任务正文持续维护 `## 执行记录`，只记录可复用的工作证据，不暴露隐藏推理：

1. 使用了哪些 Skills/工具，以及它们承担什么工作。
2. 关键决策、假设和选择理由。
3. 遇到的问题、诊断证据、重试与解决办法。
4. 自动测试、构建、浏览器回归、录屏等验证结果。
5. 下次可以怎样减少调用、并行处理、复用缓存或提前发现失败。

记录的目的，是让后续 Agent 能恢复任务并审计效率；它不能成为要求用户阅读的中间验收物。

## 移动、归档与检查

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" move <TSK-ID> \
  --to-current-project

node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" delete <TSK-ID> --yes
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" index
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" doctor
```

`delete` 实际移动到 `archive/`，不永久删除。

## Web 看板

当用户要求打开或启动 Todo 看板时：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" web
```

项目级看板显式追加作用域参数。Web 只监听 `127.0.0.1`，与 CLI 读取同一份 Markdown 数据。

## 渐进式资料

- 需要完整命令参数时读 [`references/commands.md`](references/commands.md)。
- 需要任务 YAML、正文和目录格式时读 [`references/file-format.md`](references/file-format.md)。
- 需要安装、依赖或 Web 启动排查时读 [`references/setup-guide.md`](references/setup-guide.md)。
- 需要产品范围和验收条件时读 [`references/poc-spec.md`](references/poc-spec.md)。
- 需要判断人工等待阈值或设计最终回归入口时读 [`references/durable-acceptance.md`](references/durable-acceptance.md)。

## 错误处理

1. CLI 返回非零退出码时报告真实错误，不绕过 CLI 直接改文件。
2. Task ID 必须是 `TSK-xxxxxxxx`；标题不能代替 ID。
3. `canDurable` 缺少合法依据时不得强行写入。
4. `doctor` 报告非法 YAML、重复 ID、文件名不一致或 Reference 失效时，先修复数据再继续。
5. 旧格式只通过 `migrate` 尽力转换；迁移失败不阻塞新系统使用。
6. `waitingHuman` 不得用于中间文档验收或例行阶段确认；不满足人工等待阈值时改回 `doing` 或 `done`。
