#!/bin/bash
# stop-check.sh — Stop Hook：检查未处理条目
# 功能：AI 响应结束时检查是否有未处理的 Todo 条目

SESSION_PID="$PPID"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODO_FILE="$PROJECT_ROOT/todo.md"
MARKER="/tmp/todo-checked-${SESSION_PID}"

# 守卫：检查 todo.md 是否存在（作为功能开关）
[ -f "$TODO_FILE" ] || exit 0

# 防死循环：如果刚处理过，允许停止
if [ -f "$MARKER" ]; then
  rm -f "$MARKER"
  exit 0
fi

# 检查 Todo 分区是否有未完成项
count_open_items() {
  local section="$1"
  awk -v section="$section" '
    $0 == "## " section { in_section=1; next }
    in_section && /^## / { in_section=0 }
    in_section && /^- \[ \]/ { count++ }
    END { print count + 0 }
  ' "$TODO_FILE"
}

todo_pending=$(count_open_items "📋 Todo")

# 如果没有待处理项，放行
[ "$todo_pending" -eq 0 ] && exit 0

# 有待处理项，创建标记并注入提醒
touch "$MARKER"

cat <<EOF
<system-reminder>
## TODO 处理提醒 (todo-skill)

还有 ${todo_pending} 个待办项未处理。
建议使用 \`/todo resolve\` 处理待办，避免遗忘。
</system-reminder>
EOF

exit 0
