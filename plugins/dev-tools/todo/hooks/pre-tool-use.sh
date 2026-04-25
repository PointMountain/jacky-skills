#!/bin/bash
# pre-tool-use.sh — PreToolUse Hook：临时文件检测
# 功能：检测 Write/Bash 操作是否创建临时文件，提醒加入追踪
# Matcher: Write|Bash

INPUT="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ENABLED_FILE="$PROJECT_ROOT/.todo-enabled"

# 守卫：检查功能开关
[ -f "$ENABLED_FILE" ] || exit 0

# 从输入中提取文件路径（静默，不在 stdout 打印中间结果）
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    fp = d.get('file_path', '')
    if fp:
        print(fp)
    else:
        cmd = d.get('command', '')
        print(cmd)
except:
    pass
" 2>/dev/null)

# 如果没有提取到内容，放行
[ -z "$FILE_PATH" ] && exit 0

# 规范化为项目相对路径，避免丢失目录信息
if [[ "$FILE_PATH" == "$PROJECT_ROOT/"* ]]; then
  TRACK_PATH="${FILE_PATH#"$PROJECT_ROOT"/}"
elif [[ "$FILE_PATH" == /* ]]; then
  TRACK_PATH="$FILE_PATH"
else
  TRACK_PATH="$FILE_PATH"
fi

# 提取文件名用于模式匹配
FILENAME=$(basename "$TRACK_PATH" 2>/dev/null)
[ -z "$FILENAME" ] && exit 0

# 临时文件匹配模式
MATCHED=false
for pattern in "test-*" "tmp-*" "debug-*" "*.tmp" "*.bak" "*.temp"; do
  case "$FILENAME" in
    $pattern)
      MATCHED=true
      break
      ;;
  esac
done

# 如果不匹配，放行
[ "$MATCHED" = false ] && exit 0

# 匹配到临时文件，注入提醒
cat <<EOF
<system-reminder>
## TODO 临时文件检测 (todo-skill)

检测到可能创建临时文件: ${TRACK_PATH}
建议使用 \`/todo add-file ${TRACK_PATH}\` 将此文件加入追踪列表，防止遗忘清理。
</system-reminder>
EOF

exit 0
