---
name: claude-monitor
description: "Claude Code 原生悬浮窗通知 - 在 macOS 状态栏显示 Claude 的实时工作状态（思考中、执行工具、等待输入、任务完成）。当用户需要监控 Claude Code 运行状态、想知道 Claude 在做什么时触发。"
---

# Claude Code Monitor - macOS 原生悬浮窗通知

在 macOS 桌面右上角显示悬浮窗，实时展示 Claude Code 的工作状态。

## 功能特性

- **思考中** — 用户提交提问后，显示 Claude 正在思考
- **工具执行** — 显示当前正在执行的工具（Read、Bash、Edit 等）
- **并行执行** — 检测多个工具并行执行，显示执行数量
- **等待输入** — Claude 需要用户权限或输入时持续提醒
- **任务完成** — 任务执行完毕后短暂显示完成状态
- **会话结束** — Claude Code 会话关闭时通知

## 悬浮窗状态

| 状态 | 图标 | 颜色 | 说明 |
|------|------|------|------|
| thinking | 🧠 | 琥珀色 | Claude 正在思考 |
| executing | ⚙️ | 天蓝色 | 正在执行工具 |
| multi_executing | ⚡ | 亮蓝色 | 并行执行多个工具 |
| waiting_input | ⏳ | 橙色 | 等待用户输入/授权 |
| completed | ✅ | 绿色 | 任务完成 |
| error | ❌ | 红色 | 执行出错 |

## 安装

### 方式一：使用安装命令（推荐）

```
/monitor-setup
```

自动完成编译和配置。

### 方式二：手动安装

1. **编译 Swift 悬浮窗**：

```bash
cd ~/.claude-monitor  # 或 skill 目录下的 swift-notify/
bash swift-notify/build.sh
```

2. **确认二进制存在**：

```bash
ls ~/.claude-monitor/claude-float-window
```

3. **创建默认配置**（可选）：

```bash
mkdir -p ~/.claude-monitor
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
```

## 验证

手动测试悬浮窗是否正常工作：

```bash
~/.claude-monitor/claude-float-window thinking "test-project" "测试消息" terminal 3
```

应看到右上角弹出一个悬浮窗，3 秒后自动消失。

## 配置

配置文件：`~/.claude-monitor/config.json`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `floatingWindow.enabled` | 全局启用/禁用 | `true` |
| `scenarios.thinking.enabled` | 思考状态弹窗 | `true` |
| `scenarios.thinking.duration` | 思考弹窗显示秒数 | `3` |
| `scenarios.executing.enabled` | 工具执行弹窗 | `true` |
| `scenarios.executing.duration` | 执行弹窗显示秒数 | `2` |
| `scenarios.waitingInput.enabled` | 等待输入弹窗 | `true` |
| `scenarios.waitingInput.duration` | 等待输入显示秒数（0=持续） | `0` |
| `scenarios.sessionEnd.enabled` | 会话结束弹窗 | `true` |
| `scenarios.sessionEnd.duration` | 结束弹窗显示秒数 | `3` |

## 依赖

- macOS 12.0+
- `jq`（用于解析 JSON 配置）
- Swift 工具链（编译悬浮窗时需要，Xcode Command Line Tools）

## 触发场景

- 用户想了解 Claude Code 当前在做什么
- 用户需要一个可视化指示器来判断 Claude 是否在工作
- 用户想监控长时间运行的任务进度
