# Skill 模板库

本文档包含所有可用的 SKILL.md 模板。由 `gsd-creator-skills` Phase 3 根据用户问卷结果选择组合。

## 模板选择逻辑

根据 Phase 0 问卷的 4 个选项组合选择模板：

### argument-hint 字段指南

`argument-hint` 是 skill frontmatter 中的可选字段，用于在用户输入 `/skill-name` 时自动展示参数用法提示。

**何时添加**：
- skill 接受用户参数（通过 `$ARGUMENTS` 变量传递）
- skill 有子命令或互斥选项
- 用户调用时需要知道可以传什么参数

**何时省略**：
- skill 不接受任何参数
- skill 的触发方式不涉及参数输入

**格式约定**：
| 符号 | 含义 | 示例 |
|------|------|------|
| `[...]` | 可选参数 | `[--verbose]` |
| `{...}` | 必填参数 | `{file-path}` |
| `\|` | 互斥选项 | `[--json\|--text]` |
| `[...]` | 可选位置参数 | `[query ...]` |

**示例**：
```yaml
# 无参数（省略 argument-hint）
argument-hint: 不写此行

# 可选互斥参数
argument-hint: '[--enable-review-gate|--disable-review-gate]'

# 带必填参数
argument-hint: '[job-id]'

# 复杂参数
argument-hint: '[--wait|--background] [--base <ref>] [--scope auto|working-tree|branch]'
```

---
|-----------|--------|-----|----------|
| 门禁 | ✅ | ✅ | 模板 A + Resume 块 + LLM 块 |
| 门禁 | ✅ | ❌ | 模板 A + Resume 块 |
| 门禁 | ❌ | ✅ | 模板 A + LLM 块 |
| 门禁 | ❌ | ❌ | 模板 A（基础版） |
| YOLO | ✅ | ✅ | 模板 B + Resume 块 + LLM 块 |
| YOLO | ✅ | ❌ | 模板 B + Resume 块 |
| YOLO | ❌ | ✅ | 模板 B + LLM 块 |
| YOLO | ❌ | ❌ | 模板 B（基础版） |

---

## 模板 A：门禁模式

每个 phase 结束都有 Checkpoint，必须用户确认后继续。

```markdown
---
name: <skill-name>
description: "<简短描述，说明何时触发此 skill>"
argument-hint: '<参数提示，如 [--option|--alt] [required-arg]。无参数时省略此行>'
---

<role>
你是一个 xxx 专家。
</role>

<purpose>
当用户需要 xxx 时，执行 yyy。
</purpose>

<trigger>
触发示例
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name><skill-name></name>
    <trigger>关键词列表</trigger>
    <requires>所需工具</requires>
    <checkpoints>
      <checkpoint order="1">检查点 1</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>约束 1</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>一句话目标</gsd:goal>

  <gsd:phase name="phase-1" order="1">
    <gsd:step>步骤 1</gsd:step>
    <gsd:checkpoint>检查点</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

# <Skill 标题>

## 执行流程

### Phase 1: <阶段名称>

**目标**：<可验证目标>

**步骤**：
1. <步骤 1>
2. <步骤 2>

> ⚠️ **Checkpoint** — <停止条件>，确认后继续

## 验证

<完成后的验证方式>

## Next Up

- [ ] <下一阶段目标>
- [ ] 可复制命令: `<command>`
```

---

## 模板 B：YOLO 模式

自动推进，仅 HARD_GATE（安全门）阻塞。

```markdown
---
name: <skill-name>
description: "<简短描述，说明何时触发此 skill>"
argument-hint: '<参数提示，如 [--option|--alt] [required-arg]。无参数时省略此行>'
---

<role>
你是一个 xxx 专家。
</role>

<purpose>
当用户需要 xxx 时，执行 yyy。
</purpose>

<trigger>
触发示例
</trigger>

<yolo:config>
  <yolo:mode>auto-advance</yolo:mode>
  <yolo:safety-gates>
    <gate>生产环境变更</gate>
    <gate>删除/覆盖关键数据</gate>
    <gate>认证、权限变更</gate>
    <gate>付费资源调用</gate>
    <gate>用户需求不明确的关键决策</gate>
  </yolo:safety-gates>
</yolo:config>

<gsd:workflow>
  <gsd:meta>
    <name><skill-name></name>
    <trigger>关键词列表</trigger>
    <requires>所需工具</requires>
    <constraints>
      <constraint>约束 1</constraint>
      <constraint>YOLO 模式下安全门仍需人工确认</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>一句话目标</gsd:goal>

  <gsd:phase name="phase-1" order="1">
    <gsd:step>步骤 1</gsd:step>
  </gsd:phase>
</gsd:workflow>

# <Skill 标题>

> 🚀 **YOLO 模式** — 自动推进，低风险操作跳过确认。安全门操作仍会暂停。

## 执行流程

### Phase 1: <阶段名称>

**目标**：<可验证目标>

**步骤**：
1. <步骤 1>
2. <步骤 2>

<!-- 仅高风险步骤才有 HARD_GATE -->
<!-- 🛑 **HARD_GATE** — <必须确认的原因> -->

## 验证

<完成后的自动验证方式>
```

---

## 扩展块：Resume

当问卷选择「需要 Resume」时，追加到 SKILL.md 末尾。

```markdown
## Resume 协议

本 skill 支持跨会话恢复。

### 状态管理

- **状态文件**: `state.md` — 记录当前阶段、进度、决策
- **断点文件**: `.continue-here.md` — 任务级断点详情

### 恢复流程

1. 新会话中触发本 skill
2. 自动读取 `state.md` 定位当前阶段
3. 读取 `.continue-here.md` 获取断点详情
4. 执行 `next_action` 继续推进

### Next Up 契约

每个阶段结束输出：

---
## ▶ Next Up

**{phase-id}: {phase-name}** — {one_line_goal}

`{next_command}`

---
**Also available:**
- `{status_command}` — 查看状态
- `{resume_command}` — 恢复断点
---

### Resume Signal

阶段末尾给出明确恢复信号：
- `回复 "approved" 继续` 或 `回复 "next" 进入下一阶段`
```

---

## 扩展块：LLM

当问卷选择「需要 LLM」时，追加到 SKILL.md 中。

```markdown
## LLM 集成

本 skill 需要调用大模型。

### 预检查（每次执行前）

1. 发送最小化测试请求验证 API 可用
2. 失败时静默处理，给出人类可读的修复建议
3. **禁止**在 CLI 中暴露原始错误堆栈或 HTTP 状态码

### 错误处理规范

遇到 LLM 调用失败时：
1. 捕获异常，记录到内部日志（不展示给用户）
2. 转换为可操作的修复建议
3. 提供降级方案（如可用）

### 错误消息模板

```
❌ AI 服务暂时不可用

问题：<人类可读的问题描述>
建议：<具体的修复步骤>

请修复后重试。
```
```
