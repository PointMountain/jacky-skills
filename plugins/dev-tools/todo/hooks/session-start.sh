#!/bin/bash
# session-start.sh — SessionStart Hook：注入 TODO 提醒
# 功能：会话启动时检查 .todo.md 并注入未完成项统计

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODO_FILE="$PROJECT_ROOT/.todo.md"
ENABLED_FILE="$PROJECT_ROOT/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 守卫：检查 .todo.md 是否存在
[ -f "$TODO_FILE" ] || exit 0

# 统计分区未完成项数量（以"下一个 ## 标题"为边界）
count_open_items() {
  local section="$1"
  awk -v section="$section" '
    $0 == "## " section { in_section=1; next }
    in_section && /^## / { in_section=0 }
    in_section && /^- \[ \]/ { count++ }
    END { print count + 0 }
  ' "$TODO_FILE"
}

cleanup_count=$(count_open_items "🧹 Cleanup")
todo_count=$(count_open_items "📋 Todo")
ideas_count=$(count_open_items "💡 Ideas")
temp_count=$(count_open_items "📁 Temp Files")

total=$((cleanup_count + todo_count + ideas_count + temp_count))

# 如果没有未完成项，不注入
[ "$total" -eq 0 ] && exit 0

# 注入提醒
cat <<EOF
<system-reminder>
## TODO 提醒 (todo-skill)

当前项目有 ${total} 个待处理项：
  - 🧹 ${cleanup_count} 个清理项
  - 📋 ${todo_count} 个待办项
  - 💡 ${ideas_count} 个想法
  - 📁 ${temp_count} 个临时文件

使用 \`/todo list\` 查看详情，\`/todo restore\` 恢复上下文，\`/todo clean\` 执行清理
</system-reminder>
EOF

exit 0
