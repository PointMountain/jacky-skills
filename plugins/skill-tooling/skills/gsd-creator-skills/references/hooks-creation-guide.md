# Claude Code Hooks 创建指南

> 当需要为 skill 创建 hooks 时，**必须先读此文档**，再动手写代码。
> 参考实现：`plugins/monitoring/claude-monitor/`

---

## 核心原则

1. **Hooks 寄生于 Skill** — hooks 目录必须在具体 skill 目录内，不是 plugin 根目录
2. **静默失败** — hook 脚本永远 `exit 0`，任何错误不应影响 Claude Code 正常运行
3. **幂等安全** — hook 可能被多次触发，必须能安全重复执行
4. **开关可控** — 功能默认关闭，用户明确开启后才生效

---

## 目录结构

```
plugin-root/                        # 如 plugins/monitoring/
├── .claude-plugin/
│   └── plugin.json                 # 插件元数据（列出所有 skills）
├── skill-name/                     # ← 具体 skill 目录
│   ├── SKILL.md                    # Skill 文档
│   ├── hooks/                      # ← hooks 必须在这里
│   │   ├── hooks.json              # Hook 注册声明
│   │   ├── common/                 # 共享工具（可选）
│   │   │   └── config.sh           # 配置管理
│   │   ├── session-start.sh        # 各事件的 hook 脚本
│   │   ├── session-end.sh
│   │   └── response-end.sh
│   └── references/                 # 参考文档
└── other-skill/                    # 同一 plugin 下的其他 skill
    └── SKILL.md
```

### 错误示范

```
plugin-root/
├── hooks/              # ❌ 不要放在 plugin 根目录
│   └── hooks.json
└── skill-name/
    └── SKILL.md
```

### 正确示范

```
plugin-root/
├── skill-name/
│   ├── SKILL.md
│   └── hooks/          # ✅ 放在 skill 目录内
│       ├── hooks.json
│       └── *.sh
```

---

## hooks.json 格式

### 基本结构

```json
{
  "hooks": {
    "<事件名>": [
      {
        "matcher": "<匹配规则>",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/<脚本名>.sh"
          }
        ]
      }
    ]
  }
}
```

### 关键字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `${CLAUDE_PLUGIN_ROOT}` | 运行时解析为 skill 根目录的绝对路径 | `/Users/.../plugins/monitoring/claude-monitor` |
| `matcher` | 匹配规则，空字符串 `""` 匹配所有 | `""`、`"Write|Edit|Bash"`、`"AskUserQuestion"` |
| `type` | 固定为 `"command"` | `"command"` |

### 支持的事件类型

| 事件 | 触发时机 | 典型用途 |
|------|----------|----------|
| `SessionStart` | 会话开始 | 初始化、注册 |
| `SessionEnd` | 会话结束 | 清理、注销 |
| `UserPromptSubmit` | 用户提交消息 | 状态更新 |
| `PreToolUse` | 工具调用前 | 门禁、上下文注入 |
| `PostToolUse` | 工具调用后 | 日志、状态更新 |
| `Stop` | AI 响应结束 | 自动化收尾 |
| `Notification` | 通知事件 | 用户提醒 |

### Matcher 规则

| matcher 值 | 含义 |
|------------|------|
| `""` | 匹配所有工具/事件 |
| `"Write\|Edit\|Bash"` | 只匹配指定工具（`\|` 分隔） |
| `"AskUserQuestion"` | 只匹配特定工具 |

### 多 matcher 示例

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/waiting-input.sh" }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/tool-start.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/input-answered.sh" }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/tool-end.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/response-end.sh" }
        ]
      }
    ]
  }
}
```

---

## Hook 脚本编写规范

### 标准头部

每个 hook 脚本**必须**包含以下头部：

```bash
#!/bin/bash
# hooks/<script-name>.sh
# <一句话描述此 hook 的作用>

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"  # 如果有共享配置

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")
TERMINAL="${TERM_PROGRAM:-vscode}"
```

### 通用变量

| 变量 | 来源 | 说明 |
|------|------|------|
| `$PPID` | 系统 | Claude Code 进程 PID（同一会话内稳定） |
| `$PWD` | 系统 | 当前工作目录 |
| `$TERM_PROGRAM` | 系统 | 终端类型 |
| `stdin` | Claude Code | JSON 格式的输入数据 |

### 条件守卫模式

Hook 脚本应该**尽早退出**，不做无用功：

```bash
# 守卫 1：检查功能开关
if [ ! -f "$HOME/.claude/my-feature.enabled" ]; then
  exit 0
fi

# 守卫 2：检查环境条件
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  exit 0
fi

# 守卫 3：防重入（适用于 Stop hook）
MARKER="/tmp/my-feature-done-$SESSION_PID"
if [ -f "$MARKER" ]; then
  rm -f "$MARKER"
  exit 0
fi

# 通过所有守卫 → 执行实际逻辑
```

### 输出格式

Hook 的 stdout 输出决定 Claude Code 的行为：

#### 不输出任何内容（默认放行）

```bash
exit 0  # 无输出 → 事件正常继续
```

#### 阻止事件（用于 Stop/PreToolUse）

```bash
echo '{"decision":"block","reason":"告诉 Claude 应该做什么"}'
```

- `decision: "block"` — 阻止事件继续（如阻止停止、阻止工具执行）
- `decision: "allow"` — 显式允许（等同无输出）
- `reason` — Claude 看到的提示文本

**注意**：`Stop` hook 使用 `block` 时，**必须配套防死循环机制**（见下文）。

#### 注入上下文（用于注入提醒/信息）

```bash
echo "这是一条 Claude 会看到的提醒信息"
```

纯文本输出会作为上下文注入到对话中。

### 防死循环机制（Stop Hook 必备）

当 Stop hook 使用 `decision: "block"` 时，Claude 处理完后会再次尝试停止，触发同一个 hook → 死循环。

**解决方案：标记文件**

```bash
# Hook 脚本中
MARKER="/tmp/my-feature-synced-$SESSION_PID"

# 检查标记 → 刚处理过，放行
if [ -f "$MARKER" ]; then
  rm -f "$MARKER"
  exit 0
fi

# 首次触发 → 阻止并要求处理
echo '{"decision":"block","reason":"请执行 XXX，完成后运行: date +%s > '"$MARKER"'"'
```

Claude 在处理完后创建标记文件：
```bash
echo $(date +%s) > /tmp/my-feature-synced-$PPID
```

下次 hook 触发时，标记存在 → 清除标记 → 放行。

### JSON 输入处理

部分事件会通过 stdin 传递 JSON 数据：

```bash
INPUT=$(cat)

# 优先使用 jq，降级使用 sed
if command -v jq &> /dev/null; then
  FIELD=$(echo "$INPUT" | jq -r '.field // empty')
else
  FIELD=$(echo "$INPUT" | sed 's/.*"field"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
fi
```

### 错误处理

```bash
# 所有错误静默处理，绝不影响 Claude Code 运行
some_command 2>/dev/null || true

# 错误日志输出到 stderr（用户可见但不影响执行）
echo "[skill-name] 错误信息" >&2

# 永远以 exit 0 结束
exit 0
```

---

## 共享配置（common/config.sh）

当多个 hook 脚本需要共享配置时，创建 `hooks/common/config.sh`：

```bash
#!/bin/bash
# hooks/common/config.sh
# <skill-name> 共享配置

# 配置路径
CONFIG_DIR="$HOME/.config/j-skills"
CONFIG_FILE="$CONFIG_DIR/<skill-name>-config.json"

# 读取配置（带默认值）
get_config() {
  local path="$1"
  local default="$2"

  if ! command -v jq &> /dev/null; then
    echo "$default"
    return
  fi

  local value=$(jq -r "$path // \"$default\"" "$CONFIG_FILE" 2>/dev/null)
  echo "${value:-$default}"
}

# 功能开关检查
is_feature_enabled() {
  local enabled=$(get_config ".feature.enabled" "false")
  [[ "$enabled" == "true" ]]
}
```

在 hook 脚本中引用：

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common/config.sh"
```

---

## 功能开关设计

### Flag 文件模式（推荐简单场景）

```bash
# 开启
echo "enabled" > ~/.claude/<feature-name>.enabled

# 检查
[ -f "$HOME/.claude/<feature-name>.enabled" ] || exit 0

# 关闭
rm -f ~/.claude/<feature-name>.enabled
```

### JSON 配置模式（推荐复杂场景）

```bash
# 配置文件
~/.config/j-skills/<skill-name>-config.json

# 内容示例
{
  "floatingWindow": {
    "enabled": true,
    "duration": 3
  },
  "daemon": {
    "url": "http://127.0.0.1:17530"
  }
}
```

---

## 完整 Hook 脚本模板

```bash
#!/bin/bash
# hooks/<event-name>.sh
# <描述此 hook 的作用>
# skill: <skill-name>

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/common/config.sh" ] && source "$SCRIPT_DIR/common/config.sh"

SESSION_PID=$PPID
PROJECT_NAME=$(basename "$PWD")

# ===== 守卫条件 =====

# 1. 功能开关检查
[ -f "$HOME/.claude/<feature>.enabled" ] || exit 0

# 2. 环境检查（如需要）
# command -v jq &> /dev/null || exit 0
# git rev-parse --is-inside-work-tree &>/dev/null || exit 0

# 3. 防重入检查（Stop hook 必备）
# MARKER="/tmp/<feature>-done-$SESSION_PID"
# if [ -f "$MARKER" ]; then
#   rm -f "$MARKER"
#   exit 0
# fi

# ===== 读取输入 =====
INPUT=$(cat)

# ===== 核心逻辑 =====
# ... 你的逻辑 ...

# ===== 输出 =====
# 无输出 → 放行
# echo '{"decision":"block","reason":"..."}' → 阻止
# echo "文本" → 注入上下文

exit 0
```

---

## 检查清单

创建 hooks 前核对：

- [ ] hooks 目录放在 **skill 目录内**，不是 plugin 根目录
- [ ] hooks.json 使用 `${CLAUDE_PLUGIN_ROOT}` 引用脚本路径
- [ ] hook 脚本有标准头部（SCRIPT_DIR、source config.sh）
- [ ] 守卫条件在逻辑之前（功能开关、环境检查）
- [ ] Stop hook 有防死循环机制（标记文件）
- [ ] 所有错误静默处理（`2>/dev/null || true`）
- [ ] 永远 `exit 0`
- [ ] 功能默认关闭，用户需主动开启
- [ ] SKILL.md 中说明 hook 的触发逻辑和开关方式
- [ ] 版本号已更新（plugin.json）

---

## 参考实现

| Skill | Hook 事件 | 特点 |
|-------|-----------|------|
| `plugins/monitoring/claude-monitor` | 全部事件 | 最完整的参考，含守护进程、浮窗、配置管理 |
| `plugins/dev-tools/task-memory` | PreToolUse, Stop | 简单的上下文注入模式 |
| `plugins/obsidian-tools/ob-project-log` | Stop | 自动沉淀模式，含防死循环 |
