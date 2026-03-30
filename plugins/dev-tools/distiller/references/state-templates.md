# 蒸馏器状态管理模板

## 状态文件: ~/.claude/distilled/.state.md

```markdown
---
current_phase: <phase-id>
resource_type: <code|visual|tech-stack|article|audio>
source: <资源来源>
started_at: <开始时间>
last_updated: <最后更新时间>
---

# 蒸馏状态

## 当前进度

| 阶段 | 状态 |
|------|------|
| Phase 1: 资源分类 | ✅ / ⏳ / ⬜ |
| Phase 2: 资源采集 | ✅ / ⏳ / ⬜ |
| Phase 3: 蒸馏框架 | ✅ / ⏳ / ⬜ |
| Phase 4: 执行蒸馏 | ✅ / ⏳ / ⬜ |
| Phase 5: 归档产物 | ✅ / ⏳ / ⬜ |

## 决策记录

- <关键决策 1>: <结果>
- <关键决策 2>: <结果>

## 输出位置

- 产物路径: <路径>
```

## 断点文件: ~/.claude/distilled/.continue-here.md

```markdown
---
phase: <phase-id>
task: <task-number>
status: in_progress
last_updated: <时间戳>
---

<current_state>
当前正在执行: <具体任务描述>
已完成的子步骤: <列表>
</current_state>

<completed_work>
- 已完成的工作项 1
- 已完成的工作项 2
</completed_work>

<remaining_work>
- 待完成的工作项 1
- 待完成的工作项 2
</remaining_work>

<context>
当时的思路/假设/风险
</context>

<next_action>
恢复后第一步执行的动作
</next_action>
```
