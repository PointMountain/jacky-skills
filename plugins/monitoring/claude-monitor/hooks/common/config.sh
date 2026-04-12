#!/bin/bash
# hooks/common/config.sh
# 配置读取工具函数

# 监控配置文件路径（由 Tauri app 管理）
MONITOR_CONFIG_DIR="$HOME/.config/j-skills"
MONITOR_CONFIG_FILE="$MONITOR_CONFIG_DIR/monitor-config.json"

# 引入二进制管理
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/ensure-binary.sh"

# 读取监控配置值
get_monitor_config() {
  local path="$1"
  local default="$2"

  if [[ ! -f "$MONITOR_CONFIG_FILE" ]]; then
    echo "$default"
    return
  fi

  if ! command -v jq &> /dev/null; then
    echo "$default"
    return
  fi

  local value=$(jq -r "$path // \"$default\"" "$MONITOR_CONFIG_FILE" 2>/dev/null)

  if [[ -z "$value" ]] || [[ "$value" == "null" ]]; then
    echo "$default"
  else
    echo "$value"
  fi
}

# 检查悬浮弹窗是否启用（默认关闭）
is_floating_window_enabled() {
  local enabled=$(get_monitor_config ".floatingWindow.enabled" "false")
  [[ "$enabled" == "true" ]]
}

# 守护进程地址
DAEMON_URL="http://127.0.0.1:17530"

# 获取悬浮窗二进制路径（仅在悬浮窗启用时调用）
get_float_binary() {
  get_binary_path
}
