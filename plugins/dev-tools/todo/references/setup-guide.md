# Setup 和 Hooks 配置指南

## 快速开始

### 1. 安装 Skill

```bash
# 链接到全局
cd /Users/jiashengwang/jacky-github/jacky-skills
j-skills link todo

# 安装到全局
j-skills install todo -g
```

> 如果 j-skills 命令不可用，参考 jacky-skills-package 项目安装 CLI

### 2. 在项目中启用

```bash
# 在项目根目录执行
/todo setup
```

这会：
- 将 hooks 配置注入 `~/.claude/settings.json`
- 创建 `.todo.md` 初始文件（如果不存在）

> hooks 通过检测 `.todo.md` 是否存在来决定是否激活，无需额外开关文件。删除 `.todo.md` 即可禁用。

## Hooks 配置详情

### 事件类型

| 事件 | 脚本 | 触发时机 | 用途 |
|------|------|----------|------|
| SessionStart | session-start.sh | 会话启动 | 注入 TODO 统计提醒 |
| Stop | stop-check.sh | AI 响应结束 | 检查未清理项 |
| PreCompact | pre-compact.sh | 上下文压缩前 | 提醒保存进展 |
| PreToolUse | pre-tool-use.sh | Write/Bash 调用前 | 检测临时文件 |

### 手动配置 hooks（不使用 setup）

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

### 路径安全校验

所有文件操作（delete/git-checkout）都经过以下安全检查：

| 检查项 | 规则 | 不通过时 |
|--------|------|---------|
| 项目内路径 | 绝对路径必须在项目目录下 | 跳过，标注 ⚠️ |
| 路径穿越 | 禁止 .. 和符号链接指向项目外 | 跳过，标注 ⚠️ |
| 文件存在性 | @file: 标记的文件必须存在 | 跳过 |
| 绝对路径 | 禁止以 / 开头 | 拒绝执行 |

### 操作确认

- delete 操作：列出 + 用户选择确认
- git-checkout 操作：列出 + 用户选择确认
- node_modules 中的 git-checkout：二次确认

## .gitignore 建议

根据团队偏好选择：

**加入 .gitignore（推荐）**：
```
.todo.md
```

适合：个人项目，不想把 TODO 追踪提交到仓库

**提交到仓库**：
不做任何 gitignore 配置。

适合：团队项目，希望所有成员看到待办事项
