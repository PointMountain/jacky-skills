#!/bin/bash
# verify.sh — TODO Skill v2 自动验收脚本
# 用法: bash verify.sh [test-project-dir]
# 功能：自动测试所有 hook 脚本和 todo.md 操作

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

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

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
echo "${YELLOW}  TODO Skill v2 自动验收${RESET}"
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
  "references/file-format.md" \
  "references/commands.md" \
  "references/setup-guide.md"; do
  assert_file "文件存在: $f" "$SKILL_DIR/$f"
done

# 检查 hook 脚本可执行
for f in session-start.sh stop-check.sh pre-compact.sh; do
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

# 检查 hooks.json 不再包含 PreToolUse
TOTAL=$((TOTAL + 1))
if ! grep -q "PreToolUse" "$SKILL_DIR/hooks/hooks.json"; then
  echo "  ${GREEN}✓${RESET} hooks.json 已移除 PreToolUse（不再追踪临时文件）"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} hooks.json 仍包含 PreToolUse，应已移除"
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

# 创建测试用 todo.md（v2 格式，两分区）
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo
- [ ] 完成用户认证模块 @context:cp-20260427-143000.md
  已写完 3 个 case，还差错误处理分支
- [ ] 重构 API 错误处理逻辑 @context:cp-20260427-150000.md

## 💡 Ideas
- [ ] 用 WebSocket 实现实时通知
TODOMD

# --- 测试 session-start.sh ---
echo ""
echo "  ${DIM}→ 测试 session-start.sh${RESET}"

OUTPUT=$(bash "$SKILL_DIR/hooks/session-start.sh" 2>&1)
assert "SessionStart 输出包含统计" "$OUTPUT" "待处理项"
assert "SessionStart 统计 todo=2" "$OUTPUT" "📋 2"
assert "SessionStart 统计 ideas=1" "$OUTPUT" "💡 1"
assert "SessionStart 统计 total=3" "$OUTPUT" "3 个"
assert "SessionStart 建议 resolve" "$OUTPUT" "/todo resolve"

# 测试无 todo.md 时静默退出
rm todo.md
OUTPUT=$(bash "$SKILL_DIR/hooks/session-start.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无 todo.md 时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无 todo.md 时应静默退出，但输出了: $OUTPUT"
  FAIL=$((FAIL + 1))
fi

# 恢复 todo.md（空内容）
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo

## 💡 Ideas
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

# 恢复有内容的 todo.md
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo
- [ ] 完成测试 @context:cp-20260427-160000.md

## 💡 Ideas
- [ ] 想法 1
TODOMD

# 清除之前的 marker
rm -f /tmp/todo-checked-*

OUTPUT=$(bash "$SKILL_DIR/hooks/stop-check.sh" 2>&1)
assert "Stop 输出处理提醒" "$OUTPUT" "待办项未处理"
assert "Stop 统计 todo=1" "$OUTPUT" "1 个"
assert "Stop 建议 resolve" "$OUTPUT" "/todo resolve"

# 验证防死循环代码逻辑
assert_content "stop-check.sh 包含 marker 防死循环" "$SKILL_DIR/hooks/stop-check.sh" "MARKER"
assert_content "stop-check.sh 清理 marker" "$SKILL_DIR/hooks/stop-check.sh" "rm -f"

# 清除 marker
rm -f /tmp/todo-checked-*

# 测试无待处理 todo 项时放行（只有 Ideas）
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo

## 💡 Ideas
- [ ] 只有想法
TODOMD

OUTPUT=$(bash "$SKILL_DIR/hooks/stop-check.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无 Todo 项时静默退出（ Ideas 不触发提醒）"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无 Todo 项时应静默退出"
  FAIL=$((FAIL + 1))
fi

# --- 测试 pre-compact.sh ---
echo ""
echo "  ${DIM}→ 测试 pre-compact.sh${RESET}"

# 恢复有内容的 todo.md
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo
- [ ] 测试项 @context:cp-20260427-170000.md

## 💡 Ideas
TODOMD

OUTPUT=$(bash "$SKILL_DIR/hooks/pre-compact.sh" 2>&1)
assert "PreCompact 输出保存提醒" "$OUTPUT" "上下文保存提醒"
assert "PreCompact 建议 /todo add" "$OUTPUT" "/todo add"
assert "PreCompact 建议 /todo resolve" "$OUTPUT" "/todo resolve"
assert "PreCompact 提到 checkpoint" "$OUTPUT" "checkpoint"

# 测试无 todo.md 时静默
rm todo.md
OUTPUT=$(bash "$SKILL_DIR/hooks/pre-compact.sh" 2>&1)
TOTAL=$((TOTAL + 1))
if [ -z "$OUTPUT" ]; then
  echo "  ${GREEN}✓${RESET} 无 todo.md 时静默退出"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} 无 todo.md 时应静默退出"
  FAIL=$((FAIL + 1))
fi

# ============================================
echo ""
echo "📄 3. todo.md 文件格式测试"
echo "━━━━──────────────────────────────"

# 测试 awk 两分区统计
cat > todo.md <<'TODOMD'
# TODO

最后更新: 2026-04-27

## 📋 Todo
- [ ] todo 1
- [x] todo done
- [ ] todo 3

## 💡 Ideas
- [ ] idea 1
TODOMD

count_section() {
  local section="$1"
  awk -v section="$section" '
    $0 == "## " section { in_section=1; next }
    in_section && /^## / { in_section=0 }
    in_section && /^- \[ \]/ { count++ }
    END { print count + 0 }
  ' todo.md
}

TODO=$(count_section "📋 Todo")
IDEAS=$(count_section "💡 Ideas")

TOTAL=$((TOTAL + 1))
if [ "$TODO" = "2" ]; then
  echo "  ${GREEN}✓${RESET} Todo 分区统计正确 (2，排除已完成)"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} Todo 分区统计错误 (期望 2, 实际 $TODO)"
  FAIL=$((FAIL + 1))
fi

TOTAL=$((TOTAL + 1))
if [ "$IDEAS" = "1" ]; then
  echo "  ${GREEN}✓${RESET} Ideas 分区统计正确 (1)"
  PASS=$((PASS + 1))
else
  echo "  ${RED}✗${RESET} Ideas 分区统计错误 (期望 1, 实际 $IDEAS)"
  FAIL=$((FAIL + 1))
fi

# ============================================
echo ""
echo "🎯 4. SKILL.md 内容验证"
echo "━━━━──────────────────────────────"

assert_content "SKILL.md 包含 add 命令" "$SKILL_DIR/SKILL.md" "add"
assert_content "SKILL.md 包含 resolve 命令" "$SKILL_DIR/SKILL.md" "resolve"
assert_content "SKILL.md 包含 checkpoint 概念" "$SKILL_DIR/SKILL.md" "checkpoint"
assert_content "SKILL.md 包含 @context 引用" "$SKILL_DIR/SKILL.md" "@context"
assert_content "SKILL.md 包含 cp- 文件格式" "$SKILL_DIR/SKILL.md" "cp-"
assert_content "SKILL.md 包含安全规则" "$SKILL_DIR/SKILL.md" "安全规则"
assert_content "SKILL.md 使用 todo.md（非 .todo.md）" "$SKILL_DIR/SKILL.md" "todo.md"
assert_content "SKILL.md 两个分区" "$SKILL_DIR/SKILL.md" "📋 Todo"
assert_content "SKILL.md Ideas 分区" "$SKILL_DIR/SKILL.md" "💡 Ideas"

# ============================================
echo ""
echo "📊 验收结果"
echo "━━━━──────────────────────────────"
echo ""
echo "  通过: ${GREEN}$PASS${RESET} / $TOTAL"
echo "  失败: ${RED}$FAIL${RESET} / $TOTAL"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "${GREEN}全部通过！${RESET}"
  echo ""
  echo "下一步："
  echo "  1. 执行 j-skills install todo -g 安装到全局"
  echo "  2. 在项目中创建 todo.md 启用功能"
  echo "  3. 执行 /todo add 测试条目 验证 skill 命令"
  exit 0
else
  echo "${RED}有 $FAIL 项未通过，请检查上面的输出${RESET}"
  exit 1
fi
