# Jacky's Claude Code Skills

[![Stars](https://img.shields.io/github/stars/wangjs-jacky/jacky-skills?style=flat)](https://github.com/wangjs-jacky/jacky-skills/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code](https://img.shields.io/badge/-Claude%20Code-8A2BE2?logo=claude&logoColor=white)

**实用的 Claude Code 技能集合，模块化设计，按需安装。**

---

## Plugin 模块

本项目采用**多 Plugin 架构**，每个 Plugin 包含一组相关 Skills，可独立安装和启用。

| Plugin | 图标 | 版本 | 说明 | 包含 Skills |
|--------|------|------|------|-------------|
| [video-processing](./plugins/video-processing) | 🎬 | 3.0.0 | 音视频 ASR 转录 | audio-to-subtitle |
| [dev-tools](./plugins/dev-tools) | 🛠️ | 2.0.0 | 开发工具 | github-repo-publish, feature-tracker, task-harness, task-memory, task-workflow, efficiency-audit |
| [knowledge-base](./plugins/knowledge-base) | 💡 | 1.0.0 | 知识库与工具集 | chrome-ext-ai-script, gh-workflow-generator, github-profile-coolify, harness-benchmark, npm-publish, vscode-extension-dev, web-to-tauri-migration-loop |
| [skill-tooling](./plugins/skill-tooling) | 🔧 | 1.0.0 | Skill 开发工具 | gsd-creator-skills, skill-optimizer, skill-researcher |
| [ticktick-manager](./plugins/ticktick-manager) | ✅ | 1.2.1 | 滴答清单管理 | tt, tt-defer, tt-worker |
| [learning-tools](./plugins/learning-tools) | 📚 | 1.1.1 | 学习与研究 | doc-to-tutorial, learn-repo, repo-study |
| [monitoring](./plugins/monitoring) | 📊 | 2.5.0 | 监控与历史 | cc-history, claude-monitor |
| [translation-tools](./plugins/translation-tools) | 🌐 | 1.0.0 | 翻译工具 | parallel-translation |
| [obsidian-tools](./plugins/obsidian-tools) | 📝 | 1.0.0 | Obsidian 工具 | config-obsidian, ob-summary |
| [claude-config](./plugins/claude-config) | ⚙️ | 0.3.0 | Claude Code 配置 | statusline-setup |
| [distiller-tools](./plugins/distiller-tools) | 🧪 | 1.1.0 | 提示词精炼 | distiller |
| [evaluators](./plugins/evaluators) | 📐 | 1.0.0 | 评估工具 | harness-evaluator |
| [language-skills](./plugins/language-skills) | 🗣️ | 1.0.0 | 语言技能 | spoken-english-coach |
| [troubleshooting](./plugins/troubleshooting) | 🔍 | 1.1.0 | 故障排查 | agent-browser-troubleshooting, cli-tool-troubleshooting, tauri-troubleshooting |
| [skills-management](./plugins/skills-management) | 📦 | 1.0.1 | Skills 管理 | j-skills, link-all-skills |

## Harness Ops Skills

`harness/` 保存工程、工具和第三方 Skills 的长期经验层。具体 Skill 统一使用 `<target>-ops` 命名：`harness` 表示稳定的读取、验证和写回框架，`ops`（Operations）表示目标对象的运行、维护、适配和持续改进。

| Skill | 对象 | 主要职责 |
|-------|------|----------|
| [happy-ops](./harness/happy-ops) | Happy/Paws 自托管工程 | 拓扑理解、运行维护、故障路由和复盘经验 |
| [opencli-ops](./harness/opencli-ops) | OpenCLI | 站点配方、adapter 缺口、浏览器兜底和本机实测经验 |
| [hyperframes-ops](./harness/hyperframes-ops) | HyperFrames 官方 Skills | 最佳实践、复杂能力组合、本机水土不服和环境兼容性 |

每个 Ops Skill 的 `SKILL.md` 保存可分享协议，gitignored 的 `experience.local.md` 保存本机路径、代理、版本、拓扑和验证记录。创建新的 harness skill 时，默认放到 `harness/<target>-ops/`；详细规范见 [`harness/CLAUDE.md`](./harness/CLAUDE.md)。

---

## 快速开始

### 方式一：从 skills.sh 安装（推荐）

[![skills.sh](https://img.shields.io/badge/skills.sh-Open%20Skills%20Ecosystem-blue)](https://skills.sh)

```bash
# 交互式安装
npx skills add

# 安装特定 Plugin
npx skills add wangjs-jacky/jacky-skills/plugins/video-processing
npx skills add wangjs-jacky/jacky-skills/plugins/dev-tools
npx skills add wangjs-jacky/jacky-skills/plugins/obsidian-tools
```

### 方式二：通过 Claude Code 插件市场安装

```bash
# 添加市场
/plugin marketplace add wangjs-jacky/jacky-skills

# 安装单个 Plugin
/plugin install video-processing@jacky-skills
/plugin install dev-tools@jacky-skills

# 启用/禁用 Plugin（命令会自动修改 settings.json）
/plugin enable video-processing@jacky-skills
/plugin disable dev-tools@jacky-skills
```

### 方式三：本地开发模式（j-skills）

适合需要修改 skills 源码的开发者，使用软链接实现热更新。

```bash
# 1. 克隆仓库
git clone https://github.com/wangjs-jacky/jacky-skills.git
cd jacky-skills

# 2. 安装 j-skills CLI
npm install -g j-skills

# 3. 链接所有 skills 到全局注册表
j-skills link --all

# 4. 安装到 Claude Code（全局）
j-skills install video-processing -g

# 常用命令
j-skills link --list      # 查看已链接
j-skills list --all       # 查看已安装
j-skills uninstall <name> -g  # 卸载
```

---

## 安装方式对比

| 方式 | 工具 | 适用场景 | 特点 |
|------|------|----------|------|
| **skills.sh** | `npx skills add` | 跨 Agent 使用 | 一键安装，支持 35+ Agent |
| **/plugin** | Claude Code 命令 | 仅 Claude Code | 官方原生支持，操作简单 |
| **j-skills** | CLI 工具 | 本地开发修改 | 软链接热更新，修改即生效 |

---

## 配置说明

### 配置文件位置

`/plugin enable` 和 `/plugin disable` 命令会自动修改 `settings.json` 中的 `enabledPlugins` 字段。

| 作用范围 | 文件路径 | 说明 |
|----------|----------|------|
| **全局** | `~/.claude/settings.json` | 所有项目生效 |
| **项目共享** | `.claude/settings.json` | 当前项目生效，提交到 git |
| **项目本地** | `.claude/settings.local.json` | 当前项目生效，不提交 git |

### 优先级

```
项目本地 > 项目共享 > 全局
```

### 手动配置示例

```json
// ~/.claude/settings.json 或 .claude/settings.json
{
  "enabledPlugins": {
    "video-processing@jacky-skills": true,
    "dev-tools@jacky-skills": true,
    "obsidian-tools@jacky-skills": false,
    "ticktick-manager@jacky-skills": true,
    "skills-management@jacky-skills": true
  }
}
```

### 验证配置

```bash
# 查看当前生效的配置和 Plugin 状态
/status

# 查看已安装的 Plugin
/plugin list
```

---

## 版本管理

### 更新到最新版本

```bash
# skills.sh 方式 - 检查更新
npx skills check

# skills.sh 方式 - 更新所有已安装的 skills
npx skills update

# /plugin 方式 - 更新特定 Plugin
/plugin update video-processing@jacky-skills

# j-skills 方式 - 拉取最新代码
cd jacky-skills && git pull
j-skills link --all
```

### 安装特定版本

```bash
# skills.sh 方式 - 指定 Git ref（branch/tag/commit）
npx skills add wangjs-jacky/jacky-skills/plugins/video-processing@v1.0.0
npx skills add wangjs-jacky/jacky-skills/plugins/video-processing@main
npx skills add wangjs-jacky/jacky-skills/plugins/video-processing@abc123

# j-skills 方式 - 切换到特定版本
cd jacky-skills
git checkout v1.0.0
j-skills link --all
j-skills install video-processing -g
```

### 版本管理对比

| 方式 | 更新命令 | 安装特定版本 |
|------|----------|--------------|
| **skills.sh** | `npx skills update` | `@<ref>` 后缀，如 `@v1.0.0` |
| **/plugin** | `/plugin update <name>` | 暂不支持 |
| **j-skills** | `git pull` + `link --all` | `git checkout <ref>` |

---

## Skills 详情

### 🎬 Video Processing

> 音视频 ASR 转录工具，支持多种格式和引擎。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| audio-to-subtitle | 音频转字幕、转录字幕 | 音视频转字幕工具，支持 mp3/wav/m4a/mp4 转录为 SRT/VTT/TXT/MD 格式，支持本地 MLX-Whisper 和豆包云端两种引擎 |

### 🛠️ Dev Tools

> 开发效率工具集，覆盖发布、测试、任务管理、效率审计等场景。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| github-repo-publish | publish to GitHub、push to remote | 一键发布本地代码仓库到 GitHub，支持创建远程仓库、推送代码、生成 README、设置 about 信息、发布 VSCode 扩展等 |
| feature-tracker | 功能追踪、功能规格、写测试 | 项目功能规格书生成器：为项目页面生成带线框图、编号功能清单、步骤化测试用例的产品规格文档 |
| task-harness | 验收边界、测试用例、harness 设计 | BDD 验收边界设计，生成 BDD case 文件和测试脚本，融入项目现有 tests/bdd/ 体系 |
| task-memory | 跨会话任务、任务记忆 | 跨多个会话持续推进的任务持久化记录：进展、偏差和复盘，在新会话快速恢复上下文 |
| task-workflow | 工作流编排、任务流程 | 任务工作流编排工具，整合 task-memory、superpowers、task-harness 形成完整的任务执行流程 |
| efficiency-audit | 效率分析、耗时分析、为什么这么慢 | 分析当前会话的任务执行效率：定位耗时瓶颈、拆解步骤耗时、给出具体优化方案 |

### 💡 Knowledge Base

> 知识库与工具集，包含开发脚手架、发布工具、参考方案等。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| chrome-ext-ai-script | Chrome 扩展参考、Plasmo 参考 | AI 驱动的 Chrome Extension 架构参考方案：Plasmo + Vercel AI SDK，侧边栏对话生成并执行页面脚本 |
| gh-workflow-generator | 定时采集、GitHub Actions | 快速生成带 GitHub Actions Workflow 的自动化采集项目 |
| github-profile-coolify | GitHub Profile、美化主页 | 一键优化 GitHub Profile README（酷炫风格、Snake 动画、图卡健康检查与自动回退） |
| harness-benchmark | harness 评估、skill 基准 | Harness Engineering Benchmark — 7 维度 70 分制评估 Skill 智能体驾驭能力 |
| npm-publish | npm publish、发布 npm 包 | npm 包发布知识库与自动化指南，覆盖 2FA/OTP、Access Token 等常见问题 |
| vscode-extension-dev | VSCode 插件开发、创建插件 | VSCode 插件完整开发脚手架，从项目初始化、功能模块生成到发布自动化 |
| web-to-tauri-migration-loop | Tauri migration、dev:tauri | Web-first 到 Tauri v2 迁移，合约优先架构、双传输适配器、fail-fast 运行时检查 |

### 🔧 Skill Tooling

> Skill 开发工具集，覆盖创建、优化、研究全流程。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| gsd-creator-skills | 创建 skill、新 skill、gsd skill | 基于 GSD 风格的 skills 生成与指导型元技能，支持外部 skill 依赖管理（离线/j-skills 两种模式） |
| skill-optimizer | 优化 skill、skill 没触发、skill 诊断 | 诊断并优化 Skills 的持续改进工具，支持调用 efficiency-audit 进行效率审计 |
| skill-researcher | 研究 skills、对比 skills | 研究 Claude Code Skills 的元技能，支持搜索热门项目、下载翻译、生成对比报告 |

### ✅ TickTick Manager

> 滴答清单集成，支持任务管理、延迟、自动执行。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| tt | /tt、日程、待办、滴答清单 | TickTick 日程管理：日程复盘、补全日程、回顾今天、时间统计 |
| tt-defer | 推到待办、明天再做、推迟任务 | 将任务推送到滴答清单任务池，支持自然语言触发 |
| tt-worker | 执行任务池、跑任务池、自动执行 | 读取滴答清单任务池中的任务并自动执行 |

### 📚 Learning Tools

> 学习与研究工具，支持仓库学习、文档转教程、技术调研。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| doc-to-tutorial | 文档转教程、生成交互式教程 | 将任意内容（文件夹/文件/文字）转换为交互式教程并启动预览服务 |
| learn-repo | 学习仓库、初始化学习项目 | 初始化 GitHub 仓库学习项目：克隆仓库、翻译文档、生成定制化 CLAUDE.md |
| repo-study | 调研、研究仓库、分析开源项目 | 研究 GitHub 仓库的特定技术实现 |

### 📊 Monitoring

> Claude Code 运行监控与历史记录查询。

| Skill | 触发词 | 说明 |
|-------|--------|------|
| cc-history | CC 历史、今天做了什么、工作记录 | 查询 Claude Code 会话历史记录 |
| claude-monitor | 监控 Claude、Claude 在做什么 | Claude Code 原生悬浮窗通知，在 macOS 状态栏显示实时工作状态（思考中、执行工具、等待输入、任务完成） |

### 🌐 Translation Tools

| Skill | 触发词 | 说明 |
|-------|--------|------|
| parallel-translation | 翻译、translate、多文件翻译 | 智能翻译调度器：自动判断单文件/多文件，使用 haiku 模型低成本翻译 |

### 📝 Obsidian Tools

| Skill | 触发词 | 说明 |
|-------|--------|------|
| config-obsidian | 配置 Obsidian、同步 | 配置 Obsidian 同步环境，支持 Remotely Save 后台触发和 REST API 配置 |
| ob-summary | Obsidian 概览、知识库总结 | Obsidian 知识库概览总结，了解内容结构、查找特定主题的笔记 |

### ⚙️ Claude Config

| Skill | 触发词 | 说明 |
|-------|--------|------|
| statusline-setup | 状态栏、statusline、配置状态栏 | 交互式配置 Claude Code 状态栏，支持多种方案切换 |

### 🧪 Distiller Tools

| Skill | 触发词 | 说明 |
|-------|--------|------|
| distiller | 蒸馏、distill、提炼、知识提炼 | 万物皆可蒸馏 — 从代码、技术栈、文章等资源中提炼可复用的核心知识，支持产出代码模板、技术方案整合、知识卡片 |

### 📐 Evaluators

| Skill | 触发词 | 说明 |
|-------|--------|------|
| harness-evaluator | 评估任务、设计评估、质量评估 | 基于 Anthropic Harness 框架的任务目标评估器，生成器-评估器分离架构，支持前端设计和全栈开发 4 维度评估 |

### 🗣️ Language Skills

| Skill | 触发词 | 说明 |
|-------|--------|------|
| spoken-english-coach | 口语表达、这个用英文怎么说 | 英语口语表达教练，建立个性化表达库，支持口述文章处理 |

### 🔍 Troubleshooting

| Skill | 触发词 | 说明 |
|-------|--------|------|
| agent-browser-troubleshooting | agent-browser 失败、浏览器无法启动 | agent-browser 故障排查：命令失败、连接超时、页面操作异常 |
| cli-tool-troubleshooting | CLI 报错、npm 全局包、spawnSync 错误 | 通用 CLI 工具故障排查：npm 全局包安装后运行报错、二进制文件损坏、optional 依赖缺失等 |
| tauri-troubleshooting | Tauri 插件权限、Tauri 命令调用 | Tauri v2 开发中常见问题的故障排查指南 |

### 📦 Skills Management

| Skill | 触发词 | 说明 |
|-------|--------|------|
| j-skills | 管理 skills、link、install | Agent Skills 管理 CLI 工具，支持 link、install、跨 35+ Agent 环境管理 |
| link-all-skills | 链接所有 skills、批量链接 | 将当前项目下所有 skills 链接到全局注册表并安装到所有环境 |

---

## 目录结构

```
jacky-skills/
├── .claude-plugin/           # 根插件配置
│   ├── plugin.json           # 元插件清单
│   └── marketplace.json      # 市场配置
├── plugins/                  # 子插件目录
│   ├── video-processing/     # 🎬 视频与音频处理
│   ├── dev-tools/            # 🛠️ 开发工具
│   ├── knowledge-base/       # 💡 知识库与工具集
│   ├── skill-tooling/        # 🔧 Skill 开发工具
│   ├── ticktick-manager/     # ✅ 滴答清单管理
│   ├── learning-tools/       # 📚 学习与研究
│   ├── monitoring/           # 📊 监控与历史
│   ├── translation-tools/    # 🌐 翻译工具
│   ├── obsidian-tools/       # 📝 Obsidian 工具
│   ├── claude-config/        # ⚙️ Claude Code 配置
│   ├── distiller-tools/      # 🧪 提示词精炼
│   ├── evaluators/           # 📐 评估工具
│   ├── language-skills/      # 🗣️ 语言技能
│   ├── troubleshooting/      # 🔍 故障排查
│   └── skills-management/    # 📦 Skills 管理
├── install.sh                # 一键安装脚本
├── CLAUDE.md                 # 项目配置
└── README.md                 # 本文件
```

---

## 相关链接

- **GitHub**: https://github.com/wangjs-jacky/jacky-skills
- **skills.sh**: https://skills.sh (Open Agent Skills Ecosystem)
- **npm Organization**: [@wangjs-jacky](https://www.npmjs.com/org/wangjs-jacky)

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

[MIT](LICENSE) - 自由使用，按需修改。
