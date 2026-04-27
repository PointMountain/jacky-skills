#!/bin/bash
# pre-compact.sh — PreCompact Hook：上下文压缩前提醒
# 功能：上下文压缩前提醒用户使用 /todo add 或 /todo resolve 保存状态

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODO_FILE="$PROJECT_ROOT/todo.md"

# 守卫：检查 todo.md 是否存在（作为功能开关）
[ -f "$TODO_FILE" ] || exit 0

# 注入提醒，不阻止压缩
cat <<EOF
<system-reminder>
## TODO 上下文保存提醒 (todo-skill)

上下文即将压缩。如果有未保存的进展，建议：
- 使用 \`/todo add "进展描述"\` 保存当前状态（会自动生成 checkpoint 快照）
- 使用 \`/todo resolve\` 处理已保存的待办项
</system-reminder>
EOF

exit 0
