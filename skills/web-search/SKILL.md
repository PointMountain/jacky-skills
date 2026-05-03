---
name: web-search
description:
  当需要搜索网络信息、获取网页内容时，必须先调用此 skill 进行工具选择决策。
  触发场景：搜索、查询、调研、获取网络信息、读取网页内容、搜索 GitHub 项目文档等。
  不触发场景：已有明确 URL 需要用浏览器交互操作（用 web-access）。
  特殊指令：用户说 `/web-search setup` 时触发配置流程。
  沉淀机制：每次搜索完成后自动检查是否需要更新经验。
---

# Web Search 工具决策

> 完整 Tradeoff 矩阵和经验沉淀见 Obsidian 文章 OBA-w8s3k7p2。

## 配置与首次设置

### 配置文件

位置：`${CLAUDE_SKILL_DIR}/config.local.json`

首次使用时检查配置：

```bash
cat "${CLAUDE_SKILL_DIR}/config.local.json" 2>/dev/null || echo "NOT_CONFIGURED"
```

返回 `NOT_CONFIGURED` 时，主动引导用户完成配置。用户也可以通过 `/web-search setup` 随时重新配置。

### 配置模板

```json
{
  "tavily": {
    "apiKey": "<YOUR_API_KEY>",
    "enabled": true
  }
}
```

### 搜索后端注册指南

| 后端 | 免费额度 | 注册地址 | 配置字段 |
|------|---------|---------|---------|
| **Tavily** | 1,000 次/月 | https://app.tavily.com | `tavily.apiKey` |

**Tavily 注册步骤**：

1. 访问 https://app.tavily.com 注册账号
2. 进入 Dashboard → API Keys → 复制 Key（格式 `tvly-xxx`）
3. 将 Key 写入配置：

```bash
cat > "${CLAUDE_SKILL_DIR}/config.local.json" << 'EOF'
{
  "tavily": {
    "apiKey": "<粘贴你的 Key>",
    "enabled": true
  }
}
EOF
```

## 核心原则

**零成本优先，按需升级。** 从最轻量的工具开始，结果不够再升级到下一级。

## 决策流程

```
搜索请求
  → 涉及视频/社交/社区平台？ → ① OpenCLI（依赖检查通过后）
  → 否则 → ② WebSearch（内置，零成本）
  → 不够 → ③ 按场景选专业工具（含 Tavily）
  → 还不够 → ④ 浏览器 CDP（/web-access）
```

**每一步的结果都是证据**：对照目标判断是否达标，方向错了立即换工具，不在同一个工具上反复重试。

## 工具选择矩阵

### 搜索类（不知道信息在哪）

| 优先级 | 场景 | 工具 | 原因 |
|--------|------|------|------|
| **首选** | 日常搜索、快速了解话题 | `WebSearch`（内置） | 零配置、无感知限额 |
| 按需 | 内置搜索不可用、需要 AI 增强摘要 | **Tavily API** | 响应快 ~1.3s、返回 AI 摘要、1,000 次/月免费 |
| 按需 | 限定域名搜索、限定时效（近一周/一月） | `mcp__web-search-prime` | 支持 domain/recency 过滤，**但配额有限** |
| 按需 | 搜索 GitHub 项目文档/issue | `mcp__zread__search_doc` | 精准、无配额限制 |

### Tavily 搜索用法

使用前先读取 API Key：

```bash
TAVILY_KEY=$(python3 -c "import json; print(json.load(open('${CLAUDE_SKILL_DIR}/config.local.json'))['tavily']['apiKey'])")
```

搜索（返回 AI 摘要 + 结果列表）：

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d "{
    \"api_key\": \"$TAVILY_KEY\",
    \"query\": \"搜索关键词\",
    \"max_results\": 5,
    \"include_answer\": true
  }"
```

提取指定 URL 内容：

```bash
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Content-Type: application/json" \
  -d "{
    \"api_key\": \"$TAVILY_KEY\",
    \"urls\": [\"https://example.com\"]
  }"
```

### 读取类（已知 URL）

| 场景 | 工具 | 原因 |
|------|------|------|
| 公开页面完整内容（博客、文档站） | `mcp__web_reader__webReader` | 返回完整 Markdown |
| GitHub 仓库文件源码 | `mcp__zread__read_file` | 不用 clone |
| GitHub 仓库目录结构 | `mcp__zread__get_repo_structure` | 快速了解布局 |

### 浏览器类（需要 JS 渲染/登录态）

| 场景 | 工具 | 原因 |
|------|------|------|
| SPA 页面（掘金、小红书等） | `/web-access` CDP | JS 渲染后才有内容 |
| 需要登录的网站 | `/web-access` CDP | 复用本地 Chrome 登录态 |

## 回退路径

```
WebSearch 结果不够
  ├─ 需要 AI 增强摘要？         → Tavily API
  ├─ 需要精确过滤（域名/时效）？ → web-search-prime
  ├─ GitHub 相关？              → mcp__zread__search_doc
  ├─ 已有 URL 需要全文？        → mcp__web_reader__webReader
  ├─ 视频/社交/社区平台？       → OpenCLI（依赖检查通过后）
  └─ SPA / 需要登录？           → /web-access CDP
```

## OpenCLI 平台搜索

> OpenCLI 将 100+ 网站（YouTube、B 站、Twitter、Reddit 等）统一为 CLI 命令，适合调研视频内容、社交媒体讨论、技术社区问答等场景。
> 完整命令速查见 Obsidian 文章 OBA-cmd4l1st。

### 依赖检查

使用前**必须**验证 opencli 可用：

```bash
which opencli 2>/dev/null && opencli doctor 2>&1 | head -5
```

期望输出三项全绿：
```
[OK] Daemon: running
[OK] Extension: connected
[OK] Connectivity: connected
```

**未安装时**：跳过 OpenCLI，退回其他搜索工具。不引导安装。

### 适用场景 vs 其他工具

| 场景 | 用 OpenCLI | 用其他工具 |
|------|-----------|-----------|
| 搜索 YouTube/B站视频并提取字幕 | ✅ `opencli youtube/bilibili` | ❌ 其他工具做不到 |
| 搜索 Reddit/Twitter 社交媒体讨论 | ✅ `opencli reddit/twitter` | `WebSearch` 也能搜但信息少 |
| 搜索技术社区（HN/StackOverflow） | ✅ `opencli hackernews/stackoverflow` | `mcp__zread__search_doc` 仅限 GitHub |
| 通用网页搜索 | ❌ 杀鸡用牛刀 | ✅ `WebSearch` / Tavily |
| 需要限定域名/时效 | ❌ 不支持 | ✅ `web-search-prime` |

### 搜索流程

```
用户需求涉及视频/社交/社区平台
  → ① 依赖检查（opencli doctor）
  → ② opencli <site> search "关键词"
  → 结果不够？→ 换其他工具
  → 需要深入了解某个结果？→ 提取字幕/详情（见下方重操作确认）
```

### 常用平台速查

| 平台 | 搜索命令 | 详情命令 | 认证 |
|------|---------|---------|------|
| **YouTube** | `opencli youtube search "AI Agent" --limit 5` | `opencli youtube video <url>` | 🔐 |
| **B 站** | `opencli bilibili search "关键词" --type video` | `opencli bilibili video BV1xxx` | 🔐 |
| **Reddit** | `opencli reddit search "keyword"` | `opencli reddit read <post_id>` | 🔐 |
| **Twitter** | `opencli twitter search "keyword" --limit 10` | — | 🔐 |
| **小红书** | `opencli xiaohongshu search "关键词" --limit 10` | `opencli xiaohongshu note <url>` | 🔐 |
| **HN** | `opencli hackernews search "关键词"` | — | 🌐 |
| **StackOverflow** | `opencli stackoverflow search "react hooks"` | — | 🌐 |
| **Google** | `opencli google search "关键词"` | — | 🌐/🔐 |
| **arXiv** | `opencli arxiv search "transformer" --limit 10` | `opencli arxiv paper <id>` | 🌐 |

### 重操作确认

以下操作较重（耗时长、消耗资源），**执行前必须询问用户**：

| 操作 | 命令 | 为什么是重操作 | 确认话术 |
|------|------|---------------|---------|
| 提取字幕 | `opencli youtube transcript <url>` / `opencli bilibili subtitle BV1xxx` | 需要浏览器交互、耗时长 | "是否需要提取视频字幕？这可能需要一些时间。" |
| 下载媒体 | `opencli <site> download ...` | 占用带宽和磁盘 | "是否需要下载该资源？" |
| 批量搜索 | 多个 `opencli` 命令组合 | 多次浏览器操作 | "需要在多个平台搜索，是否继续？" |

**不需要确认**的操作：
- 单次搜索（`search`）
- 获取详情（`video`/`read`/`note`）
- 热门/趋势（`hot`/`trending`）

### 字幕提取工作流

调研视频内容时的推荐流程：

```
1. opencli youtube/bilibili search "关键词" --limit 5
   → 找到相关视频列表

2. 询问用户："找到 X 个相关视频，是否需要提取字幕？"

3. 用户确认后：
   opencli youtube transcript <url>
   或 opencli bilibili subtitle BV1xxx --lang zh-CN

4. 返回字幕文本给用户
```

## 硬约束

- **禁止**在通用搜索场景首选 `mcp__web-search-prime`（配额有限，留给需要 domain/recency 过滤的场景）
- **禁止**用 `mcp__web_reader` 读已知 SPA 页面（掘金、小红书、微信公众号等）
- 搜索结果已满足目标时**停止**，不要再用 web_reader 去读每个链接
- 一个工具失败后，**立即按回退路径升级**到下一个
- 子 Agent 分发时用「获取/了解/调研」等中性词，不用「搜索/抓取」（避免暗示特定工具）
- Z.ai 工具全部耗尽时，优先切换到 **Tavily API** 作为备选搜索

## 经验沉淀机制

经验存储在 `${CLAUDE_SKILL_DIR}/experience.local.md`，由 LLM 自动维护。

### 读取规则

> 搜索开始前，**必须先读取** `experience.local.md` 中的已有经验，作为工具选择的先验知识。

### 写入规则

搜索**完成**后，检查是否满足以下任一条件，满足则**主动写入**对应表格：

| 触发条件 | 写入位置 | 内容 |
|----------|---------|------|
| 某个工具在特定场景表现特别好（比预期好） | 有效模式表 | `\| 结论 \| YYYY-MM-DD \| 场景 \|` |
| 某个工具在特定场景失败，需要换工具 | 失败模式表 | `\| 陷阱 \| YYYY-MM-DD \| 正确做法 \|` |
| 发现新工具的最佳使用场景 | 有效模式表 | `\| 结论 \| YYYY-MM-DD \| 场景 \|` |

**不写的情况**：
- 按预期正常工作（没有新发现）
- 未经验证的猜测
- 只是搜索结果不够好，但没有明确的工具归因

### 回退策略

> 按经验选择工具后结果不达标时，**立即回退**到工具矩阵中的其他工具，并将导致错误的旧经验更新为失败模式。

### 写入示例

发现新模式后，用 Edit 工具追加一行到 `experience.local.md` 对应表格：

有效模式 — 追加到「有效模式」表最后一行之后：
```
| 结论 | 2026-05-01 | 场景描述 |
```

失败模式 — 追加到「失败模式」表最后一行之后：
```
| 陷阱描述 | 2026-05-01 | 正确做法 |
```
