#!/bin/bash
# verify.sh — TODO Skill 自动验收脚本
# 用法: bash verify.sh [test-project-dir]
# 功能：自动测试所有 hook 脚本和 .todo.md 操作

set -e

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
DIM='\033[2m'
RESET='\033[0m'

PASS=0
FAIL=0
TOTAL=0

# 验收项目录
if [ -n "$1" ]; then
  TEST_DIR="$1"
else
  TEST_DIR="/tmp/todo-skill-verify-$$"
fi

SKILL_DIR="/Users/jiashengwang/jacky-github/jacky-skills/plugins/dev-tools/todo"

assert() {
  local desc="$1"
  local actual="$2"
  local expected="$3"
  TOTAL=$((TOTAL + 1))

  if echo "$actual" | grep -q "$expected"; then
    echo "  ${GREEN}✓${RESET} $desc"
    PASS=$((PASS + 1))
  else
    echo "  ${RED}✗${RESET} $desc"
    echo "    ${DIM}期望包含: $expected${RESET}"
    echo "    ${DIM}实际输出: $(echo "$actual" | head -3)${RESET}"
    FAIL=$((FAIL + 1))
  fi
}

assert_file() {
  local desc="$1"
  local file="$2"
  TOTAL=$((TOTAL + 1))

  if [ -f "$file" ]; then
    echo "  ${GREEN}✓${RESET} $desc"
    PASS=$((PASS + 1))
  else
    echo "  ${RED}✗${RESET} $desc (文件不存在: $file)"
    FAIL=$((FAIL + 1))
  fi
}

assert_content() {
  local desc="$1"
  local file="$2"
  local expected="$3"
  TOTAL=$((TOTAL + 1))

  if [ -f "$file" ] && grep -q "$expected" "$file"; then
    echo "  ${GREEN}✓${RESET} $desc"
    PASS=$((PASS + 1))
  else
    echo "  ${RED}✗${RESET} $desc"
    echo "    ${DIM}期望文件包含: $expected${RESET}"
    if [ -f "$file" ]; then
      echo "    ${DIM}文件内容: $(cat "$file")${RESET}"
    fi
    FAIL=$((FAIL + 1))
  fi
}

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# ============================================
echo ""
echo "${YELLOW}═══════════════════════════════════════════${RESET}"
echo "${YELLOW}  TODO Skill 自动验收${RESET}"
echo "${YELLOW}═══════════════════════════════════════════${RESET}"
echo ""

# ============================================
echo "📦 1. 文件完整性检查"
echo "━━━━──────────────────────────────"
for f in \
  "SKILL.md" \
  "hooks/hooks.json" \
  "hooks/session-start.sh" \
  "hooks/stop-check.sh" \
  "hooks/pre-compact.sh" \
  "hooks/pre-tool-use.sh" \
  "references/file-format.md" \
  "references/commands.md" \
  "references/setup-guide.md"; do
  assert_file "文件存在: $f" "$SKILL_DIR/$f"
done

# 检查 hook 脚本可执行
for f in session-start.sh stop-check.sh pre-compact.sh pre-tool-use.sh; do
  TOTAL=$((TOTAL + 1))
  if [ -x "$SKILL_DIR/hooks/$f" ]; then
    echo "  ${GREEN}✓${RESET} 可执行权限: $f"
    PASS=$((PASS + 1))
  else
    echo "  ${RED}✗${RESET} 缺少可执行权限: $f"
    FAIL=$((FAIL + 1))
  fi
done

# 检查 hooks.json 格式
TOTAL=$((TOTAL + 1))
if python3 -m json.tool "$SKILL_DIR/hooks/hooks.json" > /dev/null 2>&1; then
  echo "  ${GREEN}✓${RESET} hooks.json 格式有效"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} hooks.json 格式无效"
  FAIL=$((FAIL + 1))
fi

# ============================================
echo ""
echo "🧪 2. Hook 脚本功能测试"
echo "━━━━──────────────────────────────"

# 准备测试项目
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
git init -q 2>/dev/null || true

# 创建测试用 .todo.md
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

- [ ] 移除 console.log 调试代码 @file:src/app.tsx
- [ ] 恢复 node_modules 修改 @file:node_modules/lodash/index.js @action:git-checkout

## 📋 Todo

- [ ] 完成用户认证模块
- [x] 修复样式问题

## 💡 Ideas

- [ ] 用 WebSocket 实现实时通知

## 📁 Temp Files

- [ ] 删除临时文件 @file:test-debug.tsx @action:delete
TODOMD

# --- 测试 session-start.sh ---
echo ""
echo "  ${DIM}→ 测试 session-start.sh${RESET}"

OUTPUT=$(bash "$SKILL_DIR/hooks/session-start.sh" 2>&1)
assert "SessionStart 输出包含统计" "$OUTPUT" "待处理项"
assert "SessionStart 统计 cleanup=2" "$OUTPUT" "🧹 2"
assert "SessionStart 统计 todo=1" "$OUTPUT" "📋 1"
assert "SessionStart 统计 ideas=1" "$OUTPUT" "💡 1"
assert "SessionStart 统计 temp=1" "$OUTPUT" "📁 1"
assert "SessionStart 统计 total=5" "$OUTPUT" "5 个"

# 测试无 .todo.md 时静默退出
rm .todo.md
OUTPUT=$(bash "$SKILL_DIR/hooks/session-start.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无 .todo.md 时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无 .todo.md 时应静默退出，但输出了: $OUTPUT"
  FAIL=$((FAIL + 1))
fi

# 恢复 .todo.md
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

## 📋 Todo

## 💡 Ideas

## 📁 Temp Files
TODOMD

# 测试全部完成时静默退出
OUTPUT=$(bash "$SKILL_DIR/hooks/session-start.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无未完成项时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无未完成项时应静默退出"
  FAIL=$((FAIL + 1))
fi

# --- 测试 stop-check.sh ---
echo ""
echo "  ${DIM}→ 测试 stop-check.sh${RESET}"

# 恢复有内容的 .todo.md
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

- [ ] 移除 console.log @file:src/app.tsx

## 📋 Todo

- [ ] 完成测试

## 💡 Ideas

## 📁 Temp Files

- [ ] 删除临时文件 @file:test.tsx @action:delete
TODOMD

# 清除之前的 marker
rm -f /tmp/todo-checked-*

OUTPUT=$(bash "$SKILL_DIR/hooks/stop-check.sh" 2>&1)
assert "Stop 输出清理提醒" "$OUTPUT" "待清理项"
assert "Stop 统计 pending=2" "$OUTPUT" "2 个"

# 验证防死循环代码逻辑（运行时测试依赖 PPID 稳定性，仅在真实会话中可测）
assert_content "stop-check.sh 包含 marker 防死循环" "$SKILL_DIR/hooks/stop-check.sh" "MARKER"
assert_content "stop-check.sh 清理 marker" "$SKILL_DIR/hooks/stop-check.sh" "rm -f"

# 清除 marker
rm -f /tmp/todo-checked-*

# 测试无待清理项时放行
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

## 📋 Todo

- [ ] 只有 todo 项

## 💡 Ideas

## 📁 Temp Files
TODOMD

OUTPUT=$(bash "$SKILL_DIR/hooks/stop-check.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无待清理项时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无待清理项时应静默退出"
  FAIL=$((FAIL + 1))
fi

# --- 测试 pre-compact.sh ---
echo ""
echo "  ${DIM}→ 测试 pre-compact.sh${RESET}"

# 恢复有内容的 .todo.md
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

## 📋 Todo

- [ ] 测试项

## 💡 Ideas

## 📁 Temp Files
TODOMD

OUTPUT=$(bash "$SKILL_DIR/hooks/pre-compact.sh" 2>&1)
assert "PreCompact 输出保存提醒" "$OUTPUT" "上下文保存提醒"
assert "PreCompact 建议 /todo save" "$OUTPUT" "/todo save"

# 测试无 .todo.md 时静默
rm .todo.md
OUTPUT=$(bash "$SKILL_DIR/hooks/pre-compact.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无 .todo.md 时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无 .todo.md 时应静默退出"
  FAIL=$((FAIL + 1))
fi

# --- 测试 pre-tool-use.sh ---
echo ""
echo "  ${DIM}→ 测试 pre-tool-use.sh${RESET}"

# 恢复 .todo.md
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

## 📋 Todo

## 💡 Ideas

## 📁 Temp Files
TODOMD

# 测试临时文件检测
INPUT='{"file_path": "test-debug-output.tsx"}'
OUTPUT=$(echo "$INPUT" | bash "$SKILL_DIR/hooks/pre-tool-use.sh" "$INPUT" 2>&1)
assert "PreToolUse 检测 test-* 文件" "$OUTPUT" "临时文件检测"
assert "PreToolUse 建议追踪" "$OUTPUT" "/todo add-file"

# 测试普通文件不触发
INPUT='{"file_path": "src/app.tsx"}'
OUTPUT=$(echo "$INPUT" | bash "$SKILL_DIR/hooks/pre-tool-use.sh" "$INPUT" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 普通文件不触发提醒"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 普通文件不应触发提醒"
  FAIL=$((FAIL + 1))
fi

# 测试 .tmp 文件
INPUT='{"file_path": "output.tmp"}'
OUTPUT=$(echo "$INPUT" | bash "$SKILL_DIR/hooks/pre-tool-use.sh" "$INPUT" 2>&1)
assert "PreToolUse 检测 .tmp 文件" "$OUTPUT" "临时文件检测"

# 测试 Bash 命令中的临时文件（仅当 file_path 可提取时生效）
# 注：纯命令字符串无法提取文件名，这是已知限制
INPUT='{"command": "echo hello"}'
OUTPUT=$(echo "$INPUT" | bash "$SKILL_DIR/hooks/pre-tool-use.sh" "$INPUT" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 纯命令不触发误报"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 纯命令不应触发提醒"
  FAIL=$((FAIL + 1))
fi

# ============================================
echo ""
echo "📄 3. .todo.md 文件格式测试"
echo "━━━━──────────────────────────────"

# 测试 awk 分区统计
cat > .todo.md <<'TODOMD'
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: 2026-04-25

## 🧹 Cleanup

- [ ] item 1
- [x] item done
- [ ] item 3

## 📋 Todo

- [ ] todo 1

## 💡 Ideas

## 📁 Temp Files

- [ ] temp 1
- [ ] temp 2
TODOMD

count_section() {
  local section="$1"
  awk -v section="$section" '
    $0 == "## " section { in_section=1; next }
    in_section && /^## / { in_section=0 }
    in_section && /^- \[ \]/ { count++ }
    END { print count + 0 }
  ' .todo.md
}

CLEANUP=$(count_section "🧹 Cleanup")
TODO=$(count_section "📋 Todo")
IDEAS=$(count_section "💡 Ideas")
TEMP=$(count_section "📁 Temp Files")

TOTAL=$((TOTAL + 1))
if [ "$CLEANUP" = "2" ]; then
  echo "  ${GREEN}✓${RESET} Cleanup 分区统计正确 (2)"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} Cleanup 分区统计错误 (期望 2, 实际 $CLEANUP)"
  FAIL=$((FAIL + 1))
fi

TOTAL=$((TOTAL + 1))
if [ "$TODO" = "1" ]; then
  echo "  ${GREEN}✓${RESET} Todo 分区统计正确 (1)"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} Todo 分区统计错误 (期望 1, 实际 $TODO)"
  FAIL=$((FAIL + 1))
fi

TOTAL=$((TOTAL + 1))
if [ "$TEMP" = "2" ]; then
  echo "  ${GREEN}✓${RESET} Temp Files 分区统计正确 (2)"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} Temp Files 分区统计错误 (期望 2, 实际 $TEMP)"
  FAIL=$((FAIL + 1))
fi

# ============================================
echo ""
echo "🎯 4. SKILL.md 内容验证"
echo "━━━━──────────────────────────────"

assert_content "SKILL.md 包含 name: todo" "$SKILL_DIR/SKILL.md" "name: todo"
assert_content "SKILL.md 包含 Phase 1 parse" "$SKILL_DIR/SKILL.md" 'name="parse"'
assert_content "SKILL.md 包含 Phase 2 execute" "$SKILL_DIR/SKILL.md" 'name="execute"'
assert_content "SKILL.md 包含 Phase 3 cleanup" "$SKILL_DIR/SKILL.md" 'name="cleanup"'
assert_content "SKILL.md 包含 add 命令" "$SKILL_DIR/SKILL.md" "add 命令"
assert_content "SKILL.md 包含 clean 命令" "$SKILL_DIR/SKILL.md" "clean 命令"
assert_content "SKILL.md 包含安全规则" "$SKILL_DIR/SKILL.md" "安全规则"
assert_content "SKILL.md 包含 constraints" "$SKILL_DIR/SKILL.md" "constraints"

# ============================================
echo ""
echo "📊 验收结果"
echo "━━━━──────────────────────────────"
echo ""
echo "  通过: ${GREEN}$PASS${RESET} / $TOTAL"
echo "  失败: ${RED}$FAIL${RESET} / $TOTAL"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "${GREEN}🎉 全部通过！${RESET}"
  echo ""
  echo "下一步："
  echo "  1. 在新 Claude Code 会话中执行 /todo setup 启用功能"
  echo "  2. 执行 /todo add 测试项目 验证 skill 命令"
  echo "  3. 重启会话验证 SessionStart hook 注入"
  exit 0
else
  echo "${RED}❌ 有 $FAIL 项未通过，请检查上面的输出${RESET}"
  exit 1
fi
