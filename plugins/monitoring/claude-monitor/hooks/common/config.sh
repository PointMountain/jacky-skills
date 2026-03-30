#!/bin/bash
# hooks/common/config.sh
# 配置读取工具函数

# 确保配置目录存在
mkdir -p "$HOME/.claude-monitor" 2>/dev/null

CONFIG_FILE="$HOME/.claude-monitor/config.json"

# 引入二进制管理
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/ensure-binary.sh"

# 读取配置值 (支持嵌套路径，如 "floatingWindow.scenarios.thinking.enabled")
get_config() {
  local path="$1"
  local default="$2"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "$default"
    return
  fi

  # 将路径转换为 jq 格式
  local jq_path=$(echo "$path" | sed 's/\./\./g')

  local value=$(jq -r "$jq_path // \"$default\"" "$CONFIG_FILE" 2>/dev/null)

  if [[ -z "$value" ]] || [[ "$value" == "null" ]]; then
    echo "$default"
  else
    echo "$value"
  fi
}

# 检查悬浮窗是否启用
is_floating_window_enabled() {
  local enabled=$(get_config ".floatingWindow.enabled" "true")
  [[ "$enabled" == "true" ]]
}

# 检查特定场景是否启用
is_scenario_enabled() {
  local scenario="$1"
  local global_enabled=$(get_config ".floatingWindow.enabled" "true")
  local scenario_enabled=$(get_config ".floatingWindow.scenarios.$scenario.enabled" "true")

  [[ "$global_enabled" == "true" ]] && [[ "$scenario_enabled" == "true" ]]
}

# 获取场景持续时间
get_scenario_duration() {
  local scenario="$1"
  local default="$2"
  get_config ".floatingWindow.scenarios.$scenario.duration" "$default"
}

# 检查工具是否在过滤列表中
is_tool_in_filter() {
  local tool="$1"

  # 获取工具过滤列表
  local tools=$(get_config ".floatingWindow.scenarios.executing.tools" "")

  # 如果为空，表示所有工具都显示
  if [[ -z "$tools" ]] || [[ "$tools" == "[]" ]]; then
    return 0
  fi

  # 检查工具是否在列表中
  echo "$tools" | jq -e "index(\"$tool\")" >/dev/null 2>&1
}

# 检查依赖是否就绪（jq 等）
# 返回值: 0=依赖就绪, 1=缺少关键依赖
ensure_dependencies() {
  if ! command -v jq &> /dev/null; then
    echo "[claude-monitor] jq 未安装，部分功能可能受限。建议安装: brew install jq" >&2
    # jq 缺失不阻塞，降级处理
    return 0
  fi
  return 0
}
