---
name: today-history
description: "查看 Claude Code 工作记录。触发词：today-history、今日工作、今天做了什么、cc-history、今日记录、昨天做了什么、历史工作、今天的工作。"
trigger: today-history, 今日工作, 今天做了什么, cc-history, 今日记录, 昨天做了什么, 历史工作, 今天的工作
---

# today-history

通过 Python 脚本直接读取 `~/.claude/projects/<encoded-path>/*.jsonl` 会话文件，解析时间戳和用户/助手消息，**无需大模型参与**即可输出结构化工作摘要。

## ⚠️ 强制规则

> **当用户问"今天做了什么/工作记录"时，必须第一时间运行本脚本，禁止手动 git log / find / grep 搜索。**
> 脚本执行仅需 ~2 秒，手动搜索浪费 5+ 分钟。

执行优先级：

```
1. python3 <脚本路径> --all --summary    # 第一步：全项目汇总（2 秒）
2. 根据 --summary 输出 → 提交滴答清单    # 第二步：按需提交
3. python3 <脚本路径> --all --ticktick   # 第三步：生成滴答清单 JSON（可选）
```

<gsd:workflow>
  <gsd:meta>
    <name>today-history</name>
    <trigger>today-history, 今日工作, 今天做了什么, cc-history, 今日记录, 昨天做了什么, 历史工作, 今天的工作</trigger>
    <requires>Python 3, Bash</requires>
    <checkpoints>
      <checkpoint order="1">脚本可执行性验证（python3 可用）</checkpoint>
      <checkpoint order="2">输出结果展示后等待下一步指令</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>时间必须从 UTC +8 转换为本地时间（脚本已内置处理）</constraint>
      <constraint>脚本路径使用绝对路径，支持在任意目录执行</constraint>
      <constraint>默认查看今天，不加参数时只查当前项目</constraint>
      <constraint>用户要求查看所有项目时使用 --all 参数</constraint>
      <constraint>禁止在大模型中手动解析 JSONL，必须通过脚本完成</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>快速输出指定日期的 Claude Code 工作记录，支持按项目或全局查看，并可联动 tt skill 提交到滴答清单。</gsd:goal>

  <gsd:phase name="query" order="1">
    <gsd:step>解析用户意图：日期（今天/昨天/指定日期）、范围（当前项目/所有项目/指定项目）</gsd:step>
    <gsd:step>构建并执行 Python 脚本命令</gsd:step>
    <gsd:step>展示输出结果</gsd:step>
    <gsd:step>询问用户是否需要进一步操作（提交到滴答清单等）</gsd:step>
  </gsd:phase>

  <gsd:phase name="submit" order="2" condition="用户要求提交到滴答清单">
    <gsd:step>根据工作记录内容，总结用户当天的工作事项</gsd:step>
    <gsd:step>调用 tt skill，将总结的工作事项创建为滴答清单任务</gsd:step>
    <gsd:step>历史任务（时间已过）自动标记为完成</gsd:step>
  </gsd:phase>
</gsd:workflow>

<commands>
```
today-history              # 查看今天（当前项目）
today-history --all        # 查看今天（所有项目）
today-history --yesterday  # 查看昨天（当前项目）
today-history --date 2026-04-04           # 查看指定日期
today-history --all --yesterday           # 所有项目 + 昨天
today-history --project /path/to/project  # 指定项目
```
</commands>

## 执行流程

### Phase 1: 查询工作记录

**Step 1 — 解析用户意图**

| 用户说法 | 日期参数 | 范围参数 |
|----------|---------|---------|
| "今天做了什么" / "今日工作" | （默认今天） | （默认当前项目） |
| "昨天做了什么" | `--yesterday` | （默认当前项目） |
| "所有项目今天做了什么" | （默认今天） | `--all` |
| "4月3号的工作" | `--date 2026-04-03` | （默认当前项目） |
| "所有项目昨天做了什么" | `--yesterday` | `--all` |

**Step 2 — 执行脚本**

脚本绝对路径：
```
/Users/jiashengwang/jacky-github/jacky-skills/plugins/monitoring/today-history/scripts/today-history.py
```

```bash
# 基本格式
python3 <脚本路径> [日期参数] [范围参数]

# 示例
python3 <脚本路径>                        # 今天，当前项目
python3 <脚本路径> --all                  # 今天，所有项目
python3 <脚本路径> --yesterday            # 昨天，当前项目
python3 <脚本路径> --date 2026-04-04      # 指定日期
python3 <脚本路径> --project ~/jacky-github/tt-cli  # 指定项目
python3 <脚本路径> --all --yesterday      # 所有项目 + 昨天
```

**Step 3 — 展示结果**

脚本输出格式示例：

**单项目模式**：
```
============================================================
  Claude Code 工作记录 - 2026-04-05
  项目: ~/jacky-github/tt-cli
============================================================

--- c20d267d...7667 (14:08 -> 14:51) ---
    文件: ~/.claude/projects/-Users-jiashengwang.../c20d267d-...jsonl
    用户消息: 5 | 编辑: 11 | 命令: 45
    [14:08] > 帮我将上午没有完成的任务分配到下午...
    [14:09] $ Check tt CLI version
    [14:15] ~ Edit: task.ts
```

**全项目模式（--all）**：
```
============================================================
  Claude Code 工作记录（全部项目）- 2026-04-05
============================================================

──────────────────────────────────────────────────
  📂 ~/jacky-github/tt-cli  (3 个会话, 120 条记录)
──────────────────────────────────────────────────

--- c20d267d...7667 (14:08 -> 14:51) ---
    ...

──────────────────────────────────────────────────
  合计: 5 个项目 | 12 个会话 | 450 条记录
──────────────────────────────────────────────────
```

> **Checkpoint**: 展示结果后等待用户下一步指令

### Phase 2: 提交到滴答清单（联动 tt skill）

**触发条件**：用户说"帮我提交到滴答清单"、"记录到滴答清单"、"补全日程"等。

**执行步骤**：

1. **分析工作记录**：从 Phase 1 的输出中，提取用户当天完成的工作事项
2. **生成任务列表**：将工作内容整理为滴答清单任务格式（简短标题 + 详细内容）
3. **调用 tt skill**：使用 tt skill 的批量创建功能，将任务提交到滴答清单
   - 工作时间已过的任务自动标记为完成
   - 标题 ≤15 字，具体细节写入 content
4. **确认结果**：展示创建的任务清单

**联动命令参考**（由 tt skill 执行）：
```bash
# 批量创建任务
echo '[{"title":"简短标题","content":"- 要点1\n- 要点2","projectId":"...","startDate":"...","dueDate":"..."}]' | tt task-batch-add --stdin

# 历史任务标记完成
tt task-batch-done <projectId> --task-ids <ids> --force
```

> **Checkpoint**: 批量创建前展示汇总确认

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| （无参数） | 查看今天，当前项目 | `python3 today-history.py` |
| `--all` | 扫描所有项目的会话 | `python3 today-history.py --all` |
| `--project <path>` | 指定项目路径 | `python3 today-history.py --project ~/jacky-github/tt-cli` |
| `--yesterday` | 查看昨天 | `python3 today-history.py --yesterday` |
| `--date YYYY-MM-DD` | 查看指定日期 | `python3 today-history.py --date 2026-04-04` |

参数可组合使用，如 `--all --yesterday` 表示查看所有项目昨天的工作记录。

## 脚本工作原理

1. 根据参数定位会话目录：
   - 默认：当前工作目录 → `~/.claude/projects/<encoded-cwd>/`
   - `--project`：指定路径 → `~/.claude/projects/<encoded-path>/`
   - `--all`：遍历 `~/.claude/projects/` 下所有子目录
2. 遍历目标目录下的所有 `.jsonl` 会话文件
3. 按日期过滤（JSONL 内部 UTC 时间戳 +8 转本地时间）
4. 提取用户消息和关键操作（Edit/Write/Bash）
5. 按时间排序输出（`--all` 模式按项目分组）

## 注意事项

- 时间已从 UTC 自动 +8 转换为本地时间（CST）
- Skill 加载等超长内容会被自动过滤，只保留有效用户输入
- 每个会话显示统计：用户消息数、编辑数、命令数
- `--all` 模式下项目名通过读取 JSONL 文件中的 cwd 字段获取，部分无法获取的会显示为编码名
- 脚本支持在任意目录执行，无需从 skill 目录运行

## Check List

- [ ] 脚本路径使用绝对路径
- [ ] 日期参数正确（今天/昨天/指定日期）
- [ ] 时间已从 UTC +8 转换为本地时间
- [ ] `--all` 模式按项目分组显示
- [ ] 展示结果后等待用户下一步指令
- [ ] 联动 tt skill 时：标题 ≤15 字，具体细节写入 content
- [ ] 联动 tt skill 时：历史任务自动标记完成
