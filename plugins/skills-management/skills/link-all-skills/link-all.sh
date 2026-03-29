#!/usr/bin/env bash

# link-all.sh - 批量链接项目内所有 skills 并全局安装到所有环境
# 用法:
#   ./link-all.sh [项目路径]
#   ./link-all.sh --dry-run
#   ./link-all.sh [项目路径] --dry-run

set -euo pipefail

GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
NC='\033[0m'

DRY_RUN=0
TARGET_PATH=""

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=1
      ;;
    *)
      if [[ -z "$TARGET_PATH" ]]; then
        TARGET_PATH="$arg"
      else
        echo -e "${RED}参数错误: 仅支持一个项目路径参数${NC}" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -n "$TARGET_PATH" ]]; then
  PROJECT_DIR="$(cd "$TARGET_PATH" && pwd)"
elif git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  PROJECT_DIR="$git_root"
else
  PROJECT_DIR="$PWD"
fi

if command -v j-skills >/dev/null 2>&1; then
  JSKILLS=(j-skills)
else
  JSKILLS=(npx -y @wangjs-jacky/j-skills)
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  批量链接并安装 Skills${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "项目路径: ${PROJECT_DIR}"
echo -e "执行命令: ${JSKILLS[*]}"
[[ "$DRY_RUN" -eq 1 ]] && echo -e "${YELLOW}模式: DRY RUN（仅预览，不执行）${NC}"
echo ""

declare -a SKILL_DIRS=()
declare -a DUPLICATES=()
SEEN_NAMES="|"

while IFS= read -r -d '' skill_md; do
  dir="$(dirname "$skill_md")"
  name="$(basename "$dir")"

  if [[ "$SEEN_NAMES" == *"|$name|"* ]]; then
    DUPLICATES+=("$name:$dir")
    continue
  fi

  SEEN_NAMES="${SEEN_NAMES}${name}|"
  SKILL_DIRS+=("$dir")
done < <(
  find "$PROJECT_DIR" \
    -type d \( -name .git -o -name node_modules -o -name dist -o -name build -o -name .next \) -prune -o \
    -type f -name "SKILL.md" -print0
)

if [[ "${#SKILL_DIRS[@]}" -eq 0 ]]; then
  echo -e "${YELLOW}未找到任何 SKILL.md${NC}"
  exit 0
fi

echo -e "${BLUE}找到 ${#SKILL_DIRS[@]} 个 Skills:${NC}"
for dir in "${SKILL_DIRS[@]}"; do
  echo "  - $(basename "$dir")"
done
echo ""

if [[ "${#DUPLICATES[@]}" -gt 0 ]]; then
  echo -e "${YELLOW}发现重复 skill 名称（按名称去重，后续重复项已跳过）:${NC}"
  for item in "${DUPLICATES[@]}"; do
    echo "  - $item"
  done
  echo ""
fi

LINKED=0
INSTALLED=0
FAILED=0
SKIPPED=0
declare -a FAILURES=()

for dir in "${SKILL_DIRS[@]}"; do
  skill_name="$(basename "$dir")"
  abs_dir="$(cd "$dir" && pwd)"

  echo -e "${BLUE}处理: ${skill_name}${NC}"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  [dry-run] ${JSKILLS[*]} link --unlink \"$skill_name\" --force"
    echo "  [dry-run] ${JSKILLS[*]} link \"$abs_dir\" -y --json"
    echo "  [dry-run] ${JSKILLS[*]} install \"$skill_name\" -g --all-env --yes --json"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  "${JSKILLS[@]}" link --unlink "$skill_name" --force >/dev/null 2>&1 || true

  if link_out="$("${JSKILLS[@]}" link "$abs_dir" -y --json 2>&1)"; then
    echo -e "${GREEN}✓ ${skill_name}${NC} (链接成功)"
    LINKED=$((LINKED + 1))
  else
    echo -e "${RED}✗ ${skill_name}${NC} (链接失败)"
    FAILURES+=("${skill_name}: link failed")
    echo "  $link_out" | sed 's/^/  /'
    FAILED=$((FAILED + 1))
    continue
  fi

  if install_out="$("${JSKILLS[@]}" install "$skill_name" -g --all-env --yes --json 2>&1)"; then
    echo -e "${GREEN}  → 已安装到所有环境${NC}"
    INSTALLED=$((INSTALLED + 1))
  else
    echo -e "${YELLOW}  → 安装失败${NC}"
    FAILURES+=("${skill_name}: install failed")
    echo "  $install_out" | sed 's/^/  /'
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "已链接: ${GREEN}${LINKED}${NC}  已安装: ${GREEN}${INSTALLED}${NC}  失败: ${RED}${FAILED}${NC}  跳过: ${YELLOW}${SKIPPED}${NC}"
echo ""

if [[ "${#FAILURES[@]}" -gt 0 ]]; then
  echo -e "${YELLOW}失败明细:${NC}"
  for item in "${FAILURES[@]}"; do
    echo "  - $item"
  done
  echo ""
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  echo -e "${BLUE}当前已链接技能（JSON）:${NC}"
  "${JSKILLS[@]}" link --list --json || true
  echo ""
  echo -e "${BLUE}当前全局安装技能（JSON）:${NC}"
  "${JSKILLS[@]}" list --global --json || true
  echo ""
  echo -e "${BLUE}链接健康检查（JSON）:${NC}"
  "${JSKILLS[@]}" link --doctor --json || true
fi
