# Setup 和 Hooks 配置指南

## 快速开始

### 1. 安装 Skill

```bash
# 链接到全局
cd ~/jacky-github/jacky-skills
j-skills link todo

# 安装到全局
j-skills install todo -g
```

> 如果 j-skills 命令不可用，参考 jacky-skills-package 项目安装 CLI

### 2. 在项目中启用

在项目根目录创建 `todo.md` 文件即可：

```markdown
# TODO

最后更新: 2026-04-27

## 📋 Todo
（无）

## 💡 Ideas
（无）
```

> hooks 通过检测 `todo.md` 是否存在来决定是否激活。删除 `todo.md` 即可禁用。

## Hooks 配置详情

### 事件类型

| 事件 | 脚本 | 触发时机 | 用途 |
|------|------|----------|------|
| SessionStart | session-start.sh | 会话启动 | 注入 TODO 统计提醒 |
| Stop | stop-check.sh | AI 响应结束 | 检查未处理条目 |
| PreCompact | pre-compact.sh | 上下文压缩前 | 提醒执行 resolve 或 add |

### 手动配置 hooks

如果需要手动配置，在 `~/.claude/settings.json` 的 `hooks` 中添加：

```json
{
  "SessionStart": [{
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "bash /path/to/todo/hooks/session-start.sh # skill: todo"
    }]
  }]
}
```

## 安全规则

1. resolve 前必须经用户确认
2. checkpoint 文件路径必须在项目目录内
3. 清理 checkpoint 前确认任务已完成

## .gitignore 建议

根据团队偏好选择：

**加入 .gitignore（推荐）**：
```
todo.md
todo-*.md
cp-*.md
```

适合：个人项目，不想把 TODO 追踪提交到仓库

**提交到仓库**：
不做任何 gitignore 配置。

适合：团队项目，希望所有成员看到待办事项
