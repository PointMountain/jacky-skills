#!/bin/bash
# hooks/common/ensure-binary.sh
# 自动检测并编译悬浮窗二进制

# 悬浮窗二进制相关常量
FLOAT_WINDOW_DIR="$HOME/.claude-monitor"
FLOAT_WINDOW_BIN="$FLOAT_WINDOW_DIR/claude-float-window"
SETUP_FAILED_MARKER="/tmp/claude-monitor/setup_failed"

# 获取 build.sh 所在目录（基于当前脚本位置推导）
_ENSURE_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_HOOKS_DIR="$(dirname "$_ENSURE_BIN_DIR")"
_SKILL_DIR="$(dirname "$_HOOKS_DIR")"
BUILD_SCRIPT="$_SKILL_DIR/swift-notify/build.sh"

# 确保悬浮窗二进制就绪，如果不存在则自动编译
# 返回值: 0=二进制就绪, 1=不可用（静默退出）
ensure_float_window_binary() {
  # 如果之前编译失败，不再重试（避免每次 hook 都重试）
  if [[ -f "$SETUP_FAILED_MARKER" ]]; then
    # 检查标记文件是否超过 1 小时，超过则允许重试
    local marker_age=$(( $(date +%s) - $(stat -f %m "$SETUP_FAILED_MARKER" 2>/dev/null || echo 0) ))
    if [[ $marker_age -lt 3600 ]]; then
      return 1
    fi
    rm -f "$SETUP_FAILED_MARKER"
  fi

  # 二进制已存在且可执行
  if [[ -x "$FLOAT_WINDOW_BIN" ]]; then
    return 0
  fi

  # 尝试自动编译
  _attempt_build
}

# 尝试编译悬浮窗
_attempt_build() {
  # 检查 swiftc 是否可用
  if ! command -v swiftc &> /dev/null; then
    echo "[claude-monitor] swiftc 未找到，请安装 Xcode Command Line Tools: xcode-select --install" >&2
    _mark_setup_failed
    return 1
  fi

  # 检查 build.sh 是否存在
  if [[ ! -f "$BUILD_SCRIPT" ]]; then
    echo "[claude-monitor] build.sh 未找到: $BUILD_SCRIPT" >&2
    _mark_setup_failed
    return 1
  fi

  # 确保目标目录存在
  mkdir -p "$FLOAT_WINDOW_DIR"

  # 执行编译
  if bash "$BUILD_SCRIPT" 2>&1; then
    # 编译成功，清除失败标记
    rm -f "$SETUP_FAILED_MARKER"
    return 0
  else
    echo "[claude-monitor] 悬浮窗编译失败，悬浮窗通知将不可用" >&2
    _mark_setup_failed
    return 1
  fi
}

# 标记编译失败
_mark_setup_failed() {
  mkdir -p "$(dirname "$SETUP_FAILED_MARKER")"
  touch "$SETUP_FAILED_MARKER"
}

# 获取悬浮窗二进制路径（如果不存在则尝试编译）
# 输出: 二进制路径，或空字符串表示不可用
get_binary_path() {
  if ensure_float_window_binary; then
    echo "$FLOAT_WINDOW_BIN"
  fi
}
