#!/bin/bash
# pre-compact.sh — PreCompact Hook：保存进展提醒
# 功能：上下文压缩前提醒 Claude 将进展写入 .todo.md

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODO_FILE="$PROJECT_ROOT/.todo.md"
ENABLED_FILE="$PROJECT_ROOT/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 守卫：检查 .todo.md 是否存在
[ -f "$TODO_FILE" ] || exit 0

# 注入提醒，不阻止压缩
cat <<EOF
<system-reminder>
## TODO 上下文保存提醒 (todo-skill)

上下文即将压缩。如果有未保存的进展，建议使用 \`/todo save "进展描述"\` 保存到 .todo.md。
这样即使上下文被压缩，任务信息也不会丢失。
</system-reminder>
EOF

exit 0
