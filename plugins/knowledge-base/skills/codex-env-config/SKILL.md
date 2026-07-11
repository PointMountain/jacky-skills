---
name: codex-env-config
description: "记录、迁移和排查 Codex CLI 环境配置。适用于 Codex 安装升级、订阅制认证、代理注入、Homebrew、skills 同步及远端环境适配。"
---

# Codex 环境配置知识库

用于沉淀、迁移和排查 Codex CLI 的本机/远端环境配置，包括安装来源、订阅制认证、代理注入、Homebrew 更新、skills 同步和远端适配策略。

## 强制前置步骤

进入本 skill 后，第一件事必须读取同目录下的 `experience.local.md`：

```bash
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || pwd)"
test -f "$SKILL_DIR/experience.local.md" && sed -n '1,220p' "$SKILL_DIR/experience.local.md"
```

如果当前执行环境无法可靠解析 `SKILL_DIR`，从本 skill 目录直接读取 `experience.local.md`。该文件是本地经验文件，允许包含真实路径、主机别名、代理端口、密钥文件位置和已验证事实。

## 边界

- `SKILL.md` 只记录可分享的通用流程，不写真实用户名、绝对路径、IP、端口、token 或 API key。
- 真实环境值必须写入 `experience.local.md`，并确保该文件被 `.gitignore` 忽略。
- 不在聊天回复、日志或命令输出里打印 token、refresh token、session key、API key 明文。
- 需要同步认证时，只复制认证文件或使用官方登录流程，不展开其中的密钥内容。
- 远端环境不能盲目照抄本机配置，尤其是 MCP server、hooks、绝对路径和 App 路径。

## 使用场景

当用户提出以下需求时使用本 skill：

- 记录或复原 Codex CLI 环境配置。
- 将本机 Codex 订阅制配置迁移到远端机器。
- 排查 Codex 连接慢、升级失败、旧版本残留、代理未生效。
- 沉淀 Codex 的 Homebrew、Shell alias/function、认证模式、skills 同步经验。

## 标准工作流

### 1. 读取经验

先读取 `experience.local.md`，确认当前已验证的本机和远端事实：

- Codex 安装方式和真实二进制路径。
- 当前认证模式，是订阅制还是 API key。
- 代理端口和注入方式。
- Homebrew 镜像配置。
- 远端 SSH 入口、远端路径、hooks 和 MCP 的适配要求。

### 2. 盘点当前环境

本机检查：

```bash
command -v codex
codex --version
codex doctor
```

认证检查必须只输出结构化摘要，不输出密钥明文。可检查：

- 认证文件是否存在。
- `auth_mode` 是否为订阅制模式。
- 是否存在 ChatGPT tokens。
- 是否仍残留 API key 字段。

### 3. 安装或升级 Codex

优先使用 Homebrew cask 管理 Codex：

```bash
brew install --cask codex
brew upgrade --cask codex
```

如果发现旧的独立二进制：

1. 先确认 Homebrew 管理的 `codex` 可用。
2. 确认 `codex --version` 为预期版本。
3. 再清理旧二进制，避免 PATH 命中旧版本。

### 4. 配置代理注入

Codex 代理应优先使用命令级注入，避免污染全局 shell：

```bash
codex_proxy_env() {
  env HTTP_PROXY="$CODEX_HTTP_PROXY" HTTPS_PROXY="$CODEX_HTTPS_PROXY" ALL_PROXY="$CODEX_ALL_PROXY" "$@"
}

codex() { codex_proxy_env command codex "$@"; }
```

真实代理地址从 `experience.local.md` 读取，不写入本文件。

### 5. 迁移到远端

远端迁移时按以下顺序处理：

1. 通过经验文件里的 SSH 入口连接远端。
2. 检查远端是否已有 Codex、Homebrew、shell 配置、认证文件。
3. 安装或升级 Homebrew cask Codex。
4. 复制订阅制认证文件，但不打印文件内容。
5. 为远端生成适配后的 `config.toml`。
6. 同步 skills 时解引用软链，避免远端出现断链。
7. 远端 hooks 默认保留，除非确认本机 hooks 引用的路径在远端也存在。
8. 运行 `codex doctor` 验证。

远端配置适配原则：

- 本机 MCP server 中的本机绝对路径不能直接复制。
- 本机 App 路径不能直接复制到远端。
- 远端已有 hooks 且路径有效时优先保留。
- 远端项目 trust path 要按远端真实目录生成。

### 6. 验证

完成后至少验证：

```bash
command -v codex
codex --version
codex doctor
```

同时检查：

- Codex 来自预期安装来源。
- 认证模式为预期模式。
- 代理环境在 Codex 执行时存在。
- WebSocket 或 ChatGPT/OpenAI 连接可达。
- 旧版本二进制没有继续被 PATH 命中。

### 7. 经验沉淀

每次完成配置或排障后，把已验证事实追加到 `experience.local.md`：

- 日期。
- 操作目标。
- 当前安装路径和版本。
- 认证模式摘要。
- 代理和镜像配置。
- 成功/失败命令的关键结论。
- 后续再次执行时必须避开的坑。

只写已经验证过的事实，不写猜测。
