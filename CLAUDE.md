# jacky-skills 项目

这是一个 Claude Code Skills 管理仓库，用于存放自定义 skill 并使用 j-skills 工具管理。

## 前提条件

**必须先安装 j-skills npm 包：**

```bash
npm install -g j-skills
```

## 目录结构

```
jacky-skills/
├── CLAUDE.md                    # 本文件
├── plugins/                     # Plugin 目录
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json      # Plugin 元数据（含版本号）
│       └── <skill-name>/
│           └── SKILL.md         # Skill 定义文件
├── skills/                      # 独立 Skills（无 Plugin）
│   └── <skill-name>/
│       └── SKILL.md
└── harness/                     # 长期经验 Ops Skills
    ├── CLAUDE.md
    └── <target>-ops/
        └── SKILL.md
```

## Docs 内容治理

以下规则从本次变更起约束新增或重构的文档；既有内容不在本次任务中批量迁移，后续触碰时再逐步归位。

- `docs/` 不是临时草稿区；新增内容必须有明确读者、长期价值和唯一归属。
- 当前有效的成体系主题必须使用简短的英文 kebab-case 目录，并以目录内的 `README.md` 作为唯一入口。
- 细节材料必须放入主题自身的 `references/`，不得继续堆放在 `docs/` 根目录。
- 失效但仍有历史价值的文档必须移入 `docs/archive/`；无保留价值的临时产物必须直接删除。
- 简单、本机私有、环境耦合的经验继续写入被忽略的 `experience.local.md`，不得为形式升级成复杂协议。
- 新增、移动或归档文档后，必须检查所有相关相对链接。

## Harness Ops 创建路由

当用户说“创建 harness skill”“给某工程建 harness”或要求长期维护某个工程、工具、第三方 Skill 的本地经验时，必须先读取 [`harness/CLAUDE.md`](harness/CLAUDE.md)，并使用官方 `skill-creator` 创建到：

```text
harness/<target>-ops/
```

- `harness` 是仓库分类；具体 Skill 一律使用 `<target>-ops`，不再使用 `*-harness`。
- `ops` 表示 Operations，覆盖运行维护、调试复盘、最佳实践、本机适配和第三方 Skill 水土不服经验。
- 可分享规则进入 `SKILL.md`；本机路径、代理、拓扑和验证记录进入 gitignored 的 `experience.local.md`。

## j-skills 工作流程

### 1. 创建 Skill

创建包含 `SKILL.md` 的目录：

```markdown
---
name: skill-name
description: 简短描述，用于触发条件判断
---

# Skill 标题

... skill 内容 ...
```

### 2. 链接到全局注册表

```bash
# 在 skill 目录下执行
j-skills link

# 或指定路径
j-skills link /path/to/skill
```

### 3. 安装到环境

```bash
# 全局安装（推荐）
j-skills install <skill-name> -g

# 安装到多个环境
j-skills install <skill-name> -g --env claude-code,cursor
```

### 常用命令

```bash
j-skills link --list      # 列出已链接
j-skills list --all       # 列出已安装
j-skills uninstall <name> -g  # 卸载
```

## 路径信息

- **本项目路径**: `/Users/jiashengwang/jacky-github/jacky-skills`
- **全局 Skills 目录**: `~/.claude/skills/`

## 快速参考

| 操作 | 命令 |
|------|------|
| 链接 skill | `j-skills link` |
| 全局安装 | `j-skills install <name> -g` |
| 列出已链接 | `j-skills link --list` |
| 列出已安装 | `j-skills list --all` |
| 卸载 | `j-skills uninstall <name> -g` |

## ⚠️ Git Push 注意事项

**修改 Plugin 文件后，必须更新版本号：**

| 变更类型 | 版本更新 | 示例 |
|----------|----------|------|
| 新增 Skill | **MINOR** | 1.0.0 → 1.1.0 |
| Bug 修复 | **PATCH** | 1.0.0 → 1.0.1 |

详见 `/github-repo-publish` skill。

## Durable 执行约定

当用户要求以 **Durable** 模式执行任务时，先读取 [`docs/durable.md`](docs/durable.md)，并按其中定义的无人值守长任务约定执行。
