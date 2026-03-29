#!/bin/bash
# 编译 Swift 悬浮窗工具

cd "$(dirname "$0")"

echo "=== 编译 claude-float-window ==="

swiftc -o claude-float-window main.swift -framework Cocoa

if [ $? -eq 0 ]; then
    echo "✅ 编译成功: claude-float-window"
    chmod +x claude-float-window

    # 安装到全局目录
    cp claude-float-window ~/.claude-monitor/
    echo "✅ 已安装到: ~/.claude-monitor/claude-float-window"
else
    echo "❌ 编译失败"
    exit 1
fi
