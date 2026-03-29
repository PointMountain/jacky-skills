#!/bin/bash
# hooks/common/config.sh
# 配置读取工具函数

CONFIG_FILE="$HOME/.claude-monitor/config.json"

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
