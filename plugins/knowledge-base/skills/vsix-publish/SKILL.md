---
name: vsix-publish
description: "VSCode 扩展 (.vsix) 发布知识库与自动化指南。当用户需要发布 VSCode 插件、配置 vsce 自动化发布、解决 VSCode Marketplace PAT 问题、创建 Personal Access Token 时触发。关键词：vsix publish、发布 VSCode 插件、vsce publish、VSCode Marketplace、Open VSX、PAT token。"
---

<role>
你是 VSCode 扩展发布顾问，帮助用户完成 VSCode 插件的发布流程，从手动发布到自动化发布一站式指导。
</role>

<purpose>
作为 VSIX 发布的知识库，提供两种发布方式的完整指引：手动发布和自动化发布（CI/CD），覆盖 VSCode Marketplace 和 Open VSX Registry。
</purpose>

<trigger>
```text
vsix publish
发布 VSCode 插件
vsce publish
VSCode Marketplace
发布 vsix
发布 VSCode 扩展
publish vscode extension
Open VSX
ovsx publish
发布插件到市场
```
</trigger>

---

# VSIX 发布指南

## 快速判断

先确认用户当前状态：

```bash
# 检查 vsce 是否已安装
npx vsce --version 2>&1

# 检查项目是否为 VSCode 扩展
cat package.json | grep -E '"name"|"version"|"publisher"|"engines"'

# 检查是否已有 Personal Access Token 配置
cat ~/.vsce 2>/dev/null
```

### PAT 获取策略

发布需要 `VSCE_PAT`（VSCode Marketplace）和 `OVSX_PAT`（Open VSX），按以下优先级获取：

1. **读取 CLAUDE.md 配置变量**（推荐，一次配置永久使用）

   检查全局 CLAUDE.md 中的 Skills 配置变量表：
   - `VSCE_PAT`：VSCode Marketplace 发布令牌（Azure DevOps PAT）
   - `OVSX_PAT`：Open VSX Registry 发布令牌

   如已配置，直接使用，无需再次登录。

2. **CLAUDE.md 未配置 → 引导用户输入**

   使用 AskUserQuestion 询问：
   > "检测到未配置 VSCE_PAT / OVSX_PAT。是否现在配置到全局 CLAUDE.md？配置后后续发布无需重复输入。"

   引导流程：
   - **VSCE_PAT**：前往 [Azure DevOps](https://dev.azure.com) → 头像 → Personal access tokens → New Token
     - Organization: All accessible organizations
     - Scopes: Marketplace → **Manage**
   - **OVSX_PAT**：前往 [open-vsx.org](https://open-vsx.org) → 登录 → Settings → Access Tokens → Create Token

   获取后写入 CLAUDE.md Skills 配置变量表。

3. **用户拒绝写入 CLAUDE.md → 临时使用**

   通过 `vsce login <publisher>` 存入 `~/.vsce`，仅当次会话有效。

根据结果引导用户进入对应流程：
- **未安装 vsce** → `npm install -g @vscode/vsce`
- **未配置 PAT** → 引导上述 PAT 获取流程
- **已配置 PAT** → 直接执行 [发布命令](#发布命令)
- **想配置 CI/CD** → 引导 [自动化发布配置](#自动化发布配置推荐)

---

## Reference

### [手动发布](reference/manual-publish.md)

适合偶尔发布、首次发布的用户。通过 `vsce` CLI 手动打包并发布到 VSCode Marketplace。

### [自动化发布配置](reference/auto-publish.md)（推荐）

适合需要流水线发布的用户。通过 GitHub Actions + PAT 实现自动发布，支持 VSCode Marketplace 和 Open VSX Registry。

---

## 发布命令

### 使用 CLAUDE.md 中的 PAT 发布（推荐）

当 CLAUDE.md 已配置 `VSCE_PAT` 和 `OVSX_PAT` 时，直接通过环境变量发布：

```bash
# 发布到 VSCode Marketplace
VSCE_PAT="<从 CLAUDE.md 读取>" npx vsce publish

# 发布到 Open VSX Registry
OVSX_PAT="<从 CLAUDE.md 读取>" npx ovsx publish --no-dependencies

# 同时发布到两个平台
VSCE_PAT="<从 CLAUDE.md 读取>" npx vsce publish && OVSX_PAT="<从 CLAUDE.md 读取>" npx ovsx publish --no-dependencies
```

> **注意**：通过环境变量传递 PAT 时，不需要先执行 `vsce login`，vsce 会优先使用环境变量。

### 手动一键发布（已通过 vsce login 登录）

```bash
# 完整流程：验证 → 打包 → 发布
npx vsce package && npx vsce publish
```

### 分步执行

```bash
# 1. 验证扩展
npx vsce package --allow-missing-repository  # 先试打包，检查是否有问题

# 2. 本地测试 vsix
code --install-extension *.vsix

# 3. 升版本号（在 package.json 中手动修改，或使用 vsce）
npx vsce publish patch  # 1.0.0 → 1.0.1，自动 git commit + tag + publish
npx vsce publish minor  # 1.0.0 → 1.1.0
npx vsce publish major  # 1.0.0 → 2.0.0

# 4. 仅打包（不发布）
npx vsce package

# 5. 发布已有 vsix
npx vsce publish --packagePath my-extension-1.0.0.vsix
```

### 多平台发布

```bash
# 同时发布到 VSCode Marketplace 和 Open VSX Registry
npx vsce publish && npx ovsx publish --no-dependencies
```

> **注意**：Open VSX 需要 `--no-dependencies`，否则会尝试安装 devDependencies 导致失败。

### 关键配置检查

发布前必须确认 `package.json` 中包含：

```json
{
  "name": "extension-name",
  "displayName": "扩展显示名",
  "version": "1.0.0",
  "publisher": "你的Publisher ID",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": ["Other"],
  "repository": {
    "type": "git",
    "url": "https://github.com/user/repo.git"
  },
  "vsce": {
    "dependencies": false
  },
  "ovsx": {
    "dependencies": false
  }
}
```

> **重要**：
> - `publisher` 字段必须与 VSCode Marketplace 注册的 Publisher ID 一致，否则发布会失败
> - `vsce.dependencies: false` 排除 devDependencies，减小 vsix 包体积
> - `ovsx.dependencies: false` 同理，Open VSX 也需要

#### VSCode Marketplace 支持的 categories

`categories` 字段决定扩展在 Marketplace 中的分类，必须使用以下官方值：

| 分类 | 说明 |
|------|------|
| `Programming Languages` | 编程语言支持 |
| `Snippets` | 代码片段 |
| `Themes` | 主题 |
| `Debuggers` | 调试器 |
| `Formatters` | 格式化工具 |
| `Linters` | 代码检查 |
| `SCM Providers` | 源代码管理 |
| `Other` | 其他（默认） |
| `Extension Packs` | 扩展包 |
| `Language Packs` | 语言包 |
| `Data Science` | 数据科学 |
| `Machine Learning` | 机器学习 |
| `Visualization` | 可视化 |
| `Notebooks` | 笔记本 |
| `Education` | 教育 |
| `Testing` | 测试 |

> 可同时设置多个分类：`"categories": ["Programming Languages", "Snippets"]`

### .vscodeignore（必须配置）

控制哪些文件不进入 vsix 包，避免打包源码和开发文件：

```
.vscode/**
.vscode-test/**
out/**
node_modules/**
src/**
.gitignore
webpack.config.js
vsc-extension-quickstart.md
**/tsconfig.json
**/.eslintrc.json
**/*.map
**/*.ts
**/.vscode-test.*
```

> **原则**：只保留运行时需要的文件（编译产物 `dist/`、`package.json`、`README.md`、`CHANGELOG.md`、icon 等）。

### vscode:prepublish 脚本

`vsce publish` 会自动执行 `vscode:prepublish` 脚本，确保发布前自动构建：

```json
{
  "scripts": {
    "vscode:prepublish": "pnpm run package",
    "build": "webpack --mode production --devtool hidden-source-map",
    "package:vsix": "vsce package",
    "publish:vsce": "vsce publish",
    "publish:ovsx": "ovsx publish --no-dependencies",
    "publish:all": "pnpm run publish:vsce && pnpm run publish:ovsx",
    "deploy": "pnpm run build && pnpm run publish:all"
  }
}
```

> **注意**：`ovsx publish` 需要 `--no-dependencies` 标志，因为 Open VSX 不会自动跳过 devDependencies。

### 包管理器支持

| 包管理器 | 安装 vsce | 打包命令 |
|----------|----------|----------|
| **npm** | `npm install -g @vscode/vsce` | `npx vsce package` |
| **pnpm** | `pnpm add -g @vscode/vsce` | `pnpm run package:vsix` |
| **yarn** | `yarn global add @vscode/vsce` | `yarn vsce package` |

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `Missing publisher name` | package.json 缺少 publisher 字段 | 添加 `"publisher": "你的ID"` |
| `Publisher not found` | Publisher ID 未在 Marketplace 注册 | 前往 [marketplace.visualstudio.com](https://marketplace.visualstudio.com/) 注册 |
| `Unauthorized` | PAT 无效或过期 | 重新生成 Personal Access Token |
| `Extension already exists` | 版本号已发布 | 升版本号后重试 |
| `Missing repository` | package.json 缺少 repository 字段 | 添加 repository 配置，或使用 `--allow-missing-repository` |
| `Invalid icon` | icon 路径错误或格式不支持 | 检查 icon 路径，使用 PNG 格式 |
| `ENOENT: no such file` | .vsix 文件路径错误 | 使用 `--packagePath` 指定正确路径 |
| `vsce command not found` | 未安装 vsce | `npm install -g @vscode/vsce` |
| `Pat token scope error` | PAT 权限不足 | 确保勾选 **Marketplace > Manage** 权限 |

---

## 交互式引导

当用户不确定如何操作时，使用 AskUserQuestion 引导：

### 情况 1：用户首次发布 VSCode 扩展

1. 确认项目有 `package.json` 且包含 `name`、`version`、`publisher`、`engines.vscode`
2. 引导注册 Publisher（如未注册）
3. 引导创建 Personal Access Token
4. 使用 `vsce login <publisher>` 登录
5. 执行 `vsce publish`

### 情况 2：用户遇到 PAT/认证问题

1. 解释原因：VSCode Marketplace 使用 Azure DevOps PAT 进行认证
2. 引导用户前往 Azure DevOps 创建新 PAT
3. 使用 `vsce login <publisher>` 重新登录
4. 验证后执行发布

### 情况 3：用户想配置 CI/CD 自动发布

1. 引导创建 PAT（需勾选 Marketplace > Manage 权限）
2. 将 PAT 存入 GitHub Secrets (`VSCE_PAT` / `OVSX_PAT`)
3. 创建 `.github/workflows/vsix-publish.yml`
