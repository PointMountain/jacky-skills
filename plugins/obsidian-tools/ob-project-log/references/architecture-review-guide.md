# 架构回顾模式（Mode 4）实现指南

> 把 Obsidian 当工作台：AI 扫码生成档案 → 用户在 Obsidian 用 callout 批注 → resolve 派 sub-agent 批量改代码。源文件在 Obsidian，项目根软链。

## 设计动机

前三种模式都是"对话 → Obsidian"的单向沉淀。**模式四是闭环**：

```
init    ──→ 代码库 ──Explore subagent──→ Obsidian 档案 + 项目软链
              │                            │
              │                            ▼
              │                     用户在 Obsidian 中
              │                     用 [!review] callout 批注
              │                            │
              │                            ▼
resolve ──→ 扫描批注 ─→ 列出确认 ─→ TeamCreate 批量派单
              │                            │
              ▼                            ▼
           改代码 ←─── 主会话 apply diff ←──┘
                  └─→ 改档案（追加澄清/推理回应）
                  └─→ 删除已 resolve 的 [!review] 块
```

## 文件布局

| 文件 | 真文件位置 | 项目根软链 | 锚点 |
|------|-----------|-----------|------|
| 架构流水线 | `$WIKI_PATH/architecture-flow.md` | `{git_root}/ARCHITECTURE.md` | `F-001/F-002/...` |
| 决策清单 | `$WIKI_PATH/decisions.md` | `{git_root}/DECISIONS.md` | `D-001/D-002/...` |

`$WIKI_PATH` 解析规则见 SKILL.md 主文档"项目路径解析"章节。

## init 子命令完整流程

### Step 1：解析项目路径

按 SKILL.md "项目路径解析"章节确定 `$WIKI_PATH` 和 `$GIT_ROOT`。

### Step 2：检测档案是否已存在

```bash
ARCH="$WIKI_PATH/architecture-flow.md"
DEC="$WIKI_PATH/decisions.md"

if [ -f "$ARCH" ] && [ -f "$DEC" ]; then
  MODE="incremental"   # 增量更新，保留 [!review] 块
else
  MODE="initial"       # 首次生成
fi
```

### Step 3：派 Explore sub-agent 扫码

使用 `Agent` 工具派 `Explore` 类型 sub-agent，prompt 模板：

```
你是项目架构分析专家。请扫描以下代码库并产出两份结构化档案。

**项目路径**: {GIT_ROOT}
**项目名**: {project-name}
**模式**: {initial | incremental}
{如果 incremental:}
**已有档案**:
- {ARCH 内容}
- {DEC 内容}
你需要保留所有 [!review] 块（这是用户批注），只刷新自动生成的部分。

### 任务一：生成 architecture-flow.md

扫描入口文件、主要脚本、CLI 命令、构建配置，识别这个项目的执行流水线。

输出格式（必须严格遵守）：

```yaml
---
article_id: OBA-{8位随机}
type: architecture-review
sub_type: flow
project: {project-name}
generated_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
---
```

# {project-name} 架构流水线

> 自动从代码扫描生成。在任意位置用 `> [!review]` callout 写下你的疑问或修改建议，
> 然后调用 `review resolve` 批量处理。

## 总览

{用 ASCII 或 Mermaid 画一张端到端流程图，展示输入→输出}

## F-001: {步骤名称}

- **职责**: 一句话说清楚这步做什么
- **输入**: 上一步给什么 / 用户提供什么
- **中间产物**: 这一步内部产生什么临时文件或状态
- **输出**: 给下一步什么
- **关键代码**:
  - `path/to/file.ts:42-78` — 主入口
  - `path/to/helper.ts:10-50` — 辅助逻辑
- **关联决策**: D-001, D-005

## F-002: ...

（按数据流顺序排列所有步骤，至少包含每个步骤的输入/输出/关键代码）

### 任务二：生成 decisions.md

扫描代码识别所有"可被替换的技术选型/方案选择"。重点找：
- 三方依赖选择（TTS 引擎、UI 框架、数据库等）
- 算法/策略选择（缓存策略、错误处理方式、并发模型）
- 协议/格式选择（数据格式、API 风格、文件结构）
- 可调参数（超时、重试次数、阈值等）

输出格式：

```yaml
---
article_id: OBA-{8位随机}
type: architecture-review
sub_type: decisions
project: {project-name}
generated_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
---
```

# {project-name} 决策清单

> 这里列出项目里所有"你能改"的决策点。如果对某个决策有意见，
> 在对应章节下用 `> [!review]` callout 写明你的想法（要换什么、为什么），
> 然后调用 `review resolve` 让 AI 批量评估并改代码。

## D-001: {决策主题}

- **当前方案**: {目前选了什么}
- **备选方案**: {合理的备选有哪些}
- **决策依据**: {从代码/注释/commit 推断的选择理由}
- **可改性**: 高 / 中 / 低（说明改造成本）
- **关联代码**: `path/to/file.ts`（具体函数或行号）
- **关联步骤**: F-002

## D-002: ...

（按重要性排序，至少 5 条；如果项目很简单可以少，但每条必须真实可决策）

### 通用约束

1. 锚点 ID（F-xxx, D-xxx）必须从 001 开始连续分配
2. 如果是 incremental 模式，已有的 F-xxx/D-xxx ID **不能修改**，新增的接续编号
3. 如果是 incremental 模式，所有 `> [!review]` callout 块必须**逐字保留**
4. 代码引用尽量带行号，行号要从源码读出来不要瞎编
5. 不嵌入大段代码，只引用路径+行号
6. 中文输出
```

### Step 4：写入 Obsidian + 验证

主会话收到 sub-agent 输出后：

1. 解析两份 markdown 内容
2. 验证 frontmatter 格式（article_id、type、sub_type 必填）
3. 验证锚点 ID 唯一且连续
4. **如果 incremental 模式**：用 grep 提取旧文件中所有 `> [!review]` 块的 (锚点ID, 块内容)，确认新内容里这些块都还在；如果丢失，从旧文件补回
5. 写入 `$WIKI_PATH/architecture-flow.md` 和 `$WIKI_PATH/decisions.md`

### Step 5：建项目根软链

```bash
GIT_ROOT=$(git rev-parse --show-toplevel)

create_symlink() {
  local target="$1"
  local link="$2"
  local name=$(basename "$link")

  if [ -L "$link" ]; then
    # 已是软链：检查目标是否一致
    actual=$(readlink "$link")
    if [ "$actual" = "$target" ]; then
      echo "  ✓ $name → 软链已存在且正确"
    else
      echo "  ⚠ $name → 软链指向了 $actual，更新为 $target"
      rm "$link"
      ln -s "$target" "$link"
    fi
  elif [ -e "$link" ]; then
    # 存在实体文件：报警跳过
    echo "  ❌ $name → 已有同名实体文件，跳过软链创建"
    echo "      请手动备份后删除 $link，再重跑 review init"
    return 1
  else
    ln -s "$target" "$link"
    echo "  ✓ $name → 已创建软链"
  fi
}

create_symlink "$WIKI_PATH/architecture-flow.md" "$GIT_ROOT/ARCHITECTURE.md"
create_symlink "$WIKI_PATH/decisions.md" "$GIT_ROOT/DECISIONS.md"
```

### Step 6：更新索引

更新 `$WIKI_PATH/index.md`，把两份新档案加入表格（type 标记为 `architecture-review`）。

更新项目 CLAUDE.md 的 `<!-- ob-index:start -->` 段，把档案行加进去：

```markdown
| ARCHITECTURE.md → architecture-flow.md | 架构流水线（步骤+决策） | 想了解项目执行流程时 |
| DECISIONS.md → decisions.md | 可决策清单 | 想知道哪些技术选型可以改时 |
```

### Step 7：输出摘要

```
🏗️  架构回顾档案已生成

📂 真文件位置：
  $WIKI_PATH/architecture-flow.md  ({N} 个步骤 F-001..F-{N})
  $WIKI_PATH/decisions.md          ({M} 个决策 D-001..D-{M})

🔗 项目根软链：
  ARCHITECTURE.md → ../jacky-obsidian/wiki/projects/{project}/architecture-flow.md
  DECISIONS.md    → ../jacky-obsidian/wiki/projects/{project}/decisions.md

下一步：在 Obsidian 中打开档案，对想要修改的步骤/决策用以下语法批注：

  > [!review] 可选标题
  > 我想把 X 改成 Y，因为...

写完后调用 `review resolve` 批量处理。
```

## resolve 子命令完整流程

### Step 1：扫描批注

读取 `architecture-flow.md` 和 `decisions.md`，用 grep 找所有 `> [!review]` 块：

```bash
# 扫描 review 块（连续的 > 开头行 + 上方最近的 ## 标题作为锚点）
extract_reviews() {
  local file="$1"
  awk '
    /^## (F-|D-)[0-9]+/ { current_anchor = $0 }
    /^> \[!review/ {
      in_review = 1
      review_start = NR
      review_type = "auto"
      if (match($0, /\[!review:([a-z]+)\]/, arr)) review_type = arr[1]
      review_content = $0 "\n"
      next
    }
    in_review && /^> / { review_content = review_content $0 "\n"; next }
    in_review && !/^> / {
      print current_anchor "|" review_type "|" review_start "|" review_content "---END---"
      in_review = 0
    }
  ' "$file"
}
```

### Step 2：列出 + 让用户勾选（**先列后改**）

```
📋 发现 {N} 条待处理批注：

[1] D-001 TTS 引擎选型 (clarify)
    "我想换成 macOS say 当 fallback，不要为了便宜牺牲稳定性"

[2] F-002 TTS 合成步骤 (auto → 待自动分类)
    "这块时序不太懂，能给个时序图吗"

[3] D-005 字幕渲染时机 (modify)
    "把 word-by-word 改成 sentence-by-sentence，太啰嗦了"

[4] D-007 ffmpeg 拼接策略 (challenge)
    "为什么不用 concat demuxer？复杂度低很多"

请输入要处理的编号（如 1,3,4 或 all）：
```

用 `AskUserQuestion` 工具收集用户选择。

### Step 3：自动分类（针对 type=auto 的）

对每条 `[!review]`（无 type 标注的），由主会话基于内容判断类型：

- 包含"看不懂"、"举个例子"、"补充"、"画个图" → `clarify`
- 包含"换成"、"改成"、"加个"、"应该是" → `modify`
- 包含"为什么不"、"为什么用"、"我觉得"、"应不应该" → `challenge`

### Step 4：TeamCreate + 批量派单

借鉴 todo skill 的 Multi Teams 模式：

```
1. TeamCreate("review-resolve-{timestamp}")

2. 对每条选中的批注，TaskCreate({
     name: "review-{anchor_id}",
     description: "{完整 prompt，见下方模板}"
   })

3. 同时 spawn N 个 general-purpose teammate（在一个 message 里并行）：
   每个 teammate 拿到独立任务

4. 主会话通过 TaskList 监控进度，接收 SendMessage
```

### teammate prompt 模板

```
你是架构回顾批注处理 agent。读取 checkpoint 后处理一条用户批注。

**项目路径**: {GIT_ROOT}
**档案文件**: {ARCH 或 DEC 完整路径}
**锚点 ID**: {F-xxx 或 D-xxx}
**批注类型**: {clarify | modify | challenge}

**锚点上下文**（从档案中提取的对应章节全文）：
{对应 F-xxx 或 D-xxx 章节内容}

**用户批注内容**：
{[!review] 块的纯文本内容}

**关联代码文件**（从锚点上下文中的"关键代码"提取）：
- {file:line}

### 你需要做什么（按 type 分支）

#### 如果 type = clarify
读关联代码，把用户问的内容补充清楚。
输出 JSON：
```json
{
  "type": "clarify",
  "doc_patch": {
    "file": "{ARCH 或 DEC 路径}",
    "anchor": "{锚点 ID}",
    "insert_after": "## {锚点 ID}: ...的最后一行 - **关联代码**: ...",
    "content": "### 补充说明\n\n{你的解释，含必要的代码引用}"
  }
}
```

#### 如果 type = modify
分析用户的修改建议是否可行。**不要直接改代码**，输出修改方案：
```json
{
  "type": "modify",
  "feasibility": "可行 | 部分可行 | 不可行",
  "reasoning": "{为什么这么判断}",
  "code_changes": [
    {
      "file": "path/to/file.ts",
      "diff": "{完整 unified diff，可被 patch 命令应用}"
    }
  ],
  "doc_patch": {
    "anchor": "{锚点 ID}",
    "update": "{档案中需要更新的字段，如 当前方案 改成什么}"
  }
}
```

#### 如果 type = challenge
读关联代码，给出推理回应（不改代码）：
```json
{
  "type": "challenge",
  "response": "{你的论证：当前方案 vs 用户提议，权衡分析}",
  "doc_patch": {
    "anchor": "{锚点 ID}",
    "insert_after": "## {锚点 ID}: ... 的最后一行",
    "content": "### 关于「{用户批注核心}」的讨论\n\n{response 内容，标注 reviewed-at 日期}"
  }
}
```

### 输出方式

完成后调用 SendMessage 把上述 JSON 发给 team lead，然后 TaskUpdate 标记 completed。

### 约束

- 代码改动必须给完整 unified diff，不能伪代码
- 文档改动 anchor 必须是字符串精确匹配（用于后续 sed 定位）
- challenge 类型必须给出至少 2 条权衡理由
- 中文输出
```

### Step 5：主会话汇总 apply

收齐所有 teammate 结果后：

#### 5a. 应用文档 patch（无需确认）

对所有 `doc_patch`：用 Read + Edit 工具按 anchor 定位后追加内容。

#### 5b. 展示代码 diff 等用户确认

```
📝 收到 {N} 条代码修改建议：

[1] D-001 TTS 引擎选型
    可行性：可行
    理由：豆包 + macOS say fallback 是合理的稳定性增强
    Diff:
    --- a/pipeline/src/synthesize.ts
    +++ b/pipeline/src/synthesize.ts
    @@ -42,6 +42,15 @@
    + try {
    +   return await doubaoTTS(text);
    + } catch (e) {
    +   console.warn('[tts] doubao failed, falling back to macOS say');
    +   return await macSayTTS(text);
    + }

[2] D-005 字幕渲染时机
    可行性：部分可行
    ...

请输入要应用的编号（如 1,2 或 all 或 none）：
```

用户确认后用 `git apply` 或 Edit 工具批量应用。

#### 5c. 清理已处理批注

成功 resolve 的 `[!review]` 块从档案中删除（用 sed 按行号区间删除）。失败/跳过的保留。

### Step 6：清理 + 输出摘要

```
1. SendMessage shutdown 所有 teammates
2. TeamDelete

输出：

✅ 已处理 {N} 条批注

文档更新：
  - architecture-flow.md  ← 补充 F-002 的时序说明
  - decisions.md          ← D-001 当前方案更新为「豆包 + macOS say fallback」
                          ← D-007 添加 challenge 推理回应

代码改动：
  - pipeline/src/synthesize.ts  (+9 -1)  D-001
  - remotion-player/src/.../SubtitleSlide.tsx  (+5 -3)  D-005

剩余未处理：
  - F-007 (challenge): 用户跳过
```

## status 子命令

仅扫描 + 列出 `[!review]`，不执行：

```
📋 当前批注状态：

architecture-flow.md (2 条)
  - F-002 [auto]: "这块时序不太懂..."
  - F-005 [clarify]: "举个例子说明..."

decisions.md (3 条)
  - D-001 [modify]: "换成 macOS say fallback..."
  - D-005 [modify]: "改成 sentence-by-sentence..."
  - D-007 [challenge]: "为什么不用 concat demuxer..."

调用 `review resolve` 批量处理。
```

## 常见情况

| 情况 | 处理 |
|------|------|
| 用户在两份档案外的地方写了 `[!review]` | 扫描时只扫这两份档案，其他位置忽略 |
| 同一锚点下多个 review 块 | 视为独立批注，分别派单 |
| review 块跨多行带空行 | 以 `^> ` 开头的连续行为一块，遇到非 `>` 行结束 |
| init 时项目无 git | 仍可生成档案到 Obsidian，软链路径用项目目录绝对路径 |
| resolve 时 teammate 失败 | 该批注保留在档案中，摘要中标注失败原因，其他正常处理 |
| 用户在 Obsidian 编辑了非 review 部分 | 下次 init 增量模式会覆盖这部分（这是设计选择：自动生成内容由 AI 维护，用户只负责 review 块） |

## 与其他模式的关系

- 与**模式二（手动沉淀）**互补：模式二记对话产生的知识（如踩坑记录），模式四记代码本身的结构和决策
- 与**模式三（浏览追问）**互补：模式三是改文档，模式四是改代码
- 与 ob-sync 不冲突：ob-sync 软链整个项目目录到 Obsidian/code/（用于跨设备同步源码），架构回顾软链单个 markdown 文件到项目根（用于在 Obsidian 编辑档案）

## 测试 Checklist

实现后用一个真实项目跑通：

- [ ] init 在空白项目上能生成两份档案 + 软链
- [ ] init 在已存在档案的项目上是 incremental 模式，保留 `[!review]` 块
- [ ] 项目根有同名实体文件时不覆盖，报警
- [ ] resolve 能识别三种类型并分别处理
- [ ] resolve 列出后让用户勾选，不勾选的不处理
- [ ] modify 类的 diff 经用户确认后才 apply
- [ ] 已 resolve 的 review 块从档案中删除
- [ ] resolve 失败的 teammate 不影响其他批注
- [ ] status 不修改任何文件
