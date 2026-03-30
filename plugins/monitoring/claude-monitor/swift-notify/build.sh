#!/bin/bash
# 编译 Swift 悬浮窗工具

cd "$(dirname "$0")"

echo "=== 编译 claude-float-window ==="

# 检查 swiftc 是否可用
if ! command -v swiftc &> /dev/null; then
    echo "❌ swiftc 未找到。请安装 Xcode Command Line Tools:"
    echo "   xcode-select --install"
    exit 1
fi

# 确保目标目录存在
mkdir -p ~/.claude-monitor

# 编译
if swiftc -o claude-float-window main.swift -framework Cocoa 2>&1; then
    echo "✅ 编译成功: claude-float-window"
    chmod +x claude-float-window

    # 安装到全局目录
    cp claude-float-window ~/.claude-monitor/
    echo "✅ 已安装到: ~/.claude-monitor/claude-float-window"
else
    echo "❌ 编译失败，请检查 Swift 源码是否有误"
    echo "   提示: 确保已安装 Xcode Command Line Tools (xcode-select --install)"
    exit 1
fi
