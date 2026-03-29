---
name: monitor-setup
description: "安装 Claude Code Monitor 悬浮窗通知：编译 Swift 二进制、创建配置文件"
---

请执行以下步骤安装 Claude Monitor 悬浮窗通知：

1. 确认安装目录存在：

```bash
mkdir -p ~/.claude-monitor
```

2. 编译 Swift 悬浮窗二进制：

```bash
bash $CLAUDE_PLUGIN_ROOT/swift-notify/build.sh
```

如果编译失败，提示用户安装 Xcode Command Line Tools：`xcode-select --install`

3. 创建默认配置文件（仅在配置文件不存在时创建）：

```bash
if [ ! -f ~/.claude-monitor/config.json ]; then
cat > ~/.claude-monitor/config.json << 'EOF'
{
  "floatingWindow": {
    "enabled": true,
    "scenarios": {
      "thinking": { "enabled": true, "duration": 3 },
      "executing": { "enabled": true, "duration": 2 },
      "waitingInput": { "enabled": true, "duration": 0 },
      "sessionEnd": { "enabled": true, "duration": 3 }
    }
  }
}
EOF
fi
```

4. 验证安装：

```bash
~/.claude-monitor/claude-float-window thinking "test-project" "安装成功！" terminal 3
```

5. 告诉用户安装完成，悬浮窗已正常工作。提醒用户可以通过编辑 `~/.claude-monitor/config.json` 调整各场景的启用状态和显示时长。
