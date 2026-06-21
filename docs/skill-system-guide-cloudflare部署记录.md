# 把单个 HTML 部署到 Cloudflare Pages —— 全过程记录

> 一句话：把 `docs/skill-system-guide.html` 这一个静态 HTML，用 Cloudflare 官方 CLI `wrangler` 一条命令发布成公网可访问的网页，并记录用到的 CLI 工具与可借鉴的 Skills。

- **部署日期**：2026-06-22
- **被部署文件**：`/Users/jiashengwang/jacky-github/jacky-skills/docs/skill-system-guide.html`（34.2 KB，自包含单文件，无本地外链）
- **页面标题**：工程开发 Skill 流水线 + 沉淀底座
- **托管方式**：Cloudflare Pages（Direct Upload，非 Git 集成）
- **Cloudflare 账号**：`2409277719@qq.com`（Account ID `6388c4205d34261a324d0bf02a6f0584`）

## 一、最终成果（线上地址）

| 用途 | URL | 状态 |
|------|-----|------|
| **生产主入口** | https://skill-system-guide.pages.dev/ | HTTP 200 ✅ |
| 干净路径（无扩展名） | https://skill-system-guide.pages.dev/skill-system-guide | HTTP 200 ✅ |
| 本次部署的唯一快照 | https://7b0cbad3.skill-system-guide.pages.dev/ | HTTP 200 ✅ |

> 注：访问 `…/skill-system-guide.html`（带扩展名）会被 Cloudflare Pages 以 **308 永久重定向**到去掉 `.html` 的「clean URL」，跟随后正常返回 200。这是 Pages 的默认行为，不是错误。

## 二、用到的 CLI 工具（核心）

| 工具 | 角色 | 本次具体用法 |
|------|------|-------------|
| **`wrangler`** | Cloudflare 官方 CLI（本次主角），版本 `4.103.0` | 登录校验、创建/查询 Pages 项目、上传部署 |
| **`npx`** | Node 包临时执行器 | 本机没全局装 wrangler，用 `npx -y wrangler@latest …` 即用即跑，不污染全局 |
| **`curl`** | HTTP 客户端 | 部署后做可用性验证（状态码 / 标题 / 重定向终点） |
| `cp` / `mkdir` | 文件准备 | 建干净部署目录、把 HTML 复制成 `index.html` |

> **为什么用 `npx` 而不是全局 `npm i -g wrangler`**：免全局污染、永远拿最新版、换机器即用。代价是首次会下载 wrangler 包（约几十秒）。
>
> **`-y` 的作用**：`npx` 首次安装包会交互式问 "Ok to proceed?"，在后台/非交互(非 TTY)环境会卡住。`-y` 自动确认，是无人值守部署的关键。

## 三、完整步骤（含真实命令）

### 3.0 前置条件
- 已安装 Node.js（本机 `v24.9.0`，含 `npx`）
- 有 Cloudflare 账号，且 `wrangler` 已登录（见 3.1）

### 3.1 确认登录态（鉴权）

`wrangler` 的鉴权有两种方式：
1. **交互式 OAuth**：`wrangler login` —— 会打开浏览器授权，token 存在 `~/Library/Preferences/.wrangler/config/default.toml`（macOS 路径）
2. **API Token**：设置环境变量 `CLOUDFLARE_API_TOKEN`（适合 CI / 无浏览器环境）

本机已存在 OAuth 登录态（`default.toml` 里有 `oauth_token` + `refresh_token`，token 过期会自动用 refresh_token 续期），所以直接校验即可：

```bash
npx -y wrangler@latest whoami
```

关键看输出里的 Token 权限要包含 **`pages (write)`**，否则无法部署 Pages。

### 3.2 准备部署目录

`wrangler pages deploy` 上传的是「一个目录」，目录里的 `index.html` 会成为根路径 `/` 的内容。原文件只有一个 HTML，所以建一个干净目录，复制成 `index.html`（同时保留原名一份，让两个路径都能访问）：

```bash
DEPLOY_DIR=/path/to/cf-deploy
mkdir -p "$DEPLOY_DIR"
cp docs/skill-system-guide.html "$DEPLOY_DIR/index.html"
cp docs/skill-system-guide.html "$DEPLOY_DIR/skill-system-guide.html"
```

### 3.3 创建 Pages 项目（仅首次需要）

非交互环境下，项目不存在会报错，需先显式创建：

```bash
npx -y wrangler@latest pages project create skill-system-guide --production-branch main
```

> 本次该项目**已存在**（昨天建过），所以这步返回 `A project with this name already exists`——属正常，直接进入部署。可用 `pages project list` 查看已有项目。

### 3.4 部署

```bash
npx -y wrangler@latest pages deploy <部署目录> \
  --project-name skill-system-guide \
  --branch main \
  --commit-dirty=true
```

参数说明：
- `--project-name`：目标项目名
- `--branch main`：部署到生产分支（决定它是不是「正式版」而非预览版）
- `--commit-dirty=true`：部署目录不是干净 git 仓库时，跳过告警

成功输出：
```
✨ Success! Uploaded 2 files (2.51 sec)
🌎 Deploying...
✨ Deployment complete! Take a peek over at https://7b0cbad3.skill-system-guide.pages.dev
```

### 3.5 验证（检查点）

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://skill-system-guide.pages.dev/
# 期望: 200
curl -sL -o /dev/null -w "%{http_code} %{url_effective}\n" https://skill-system-guide.pages.dev/skill-system-guide.html
# 期望: 200 …/skill-system-guide （308 跟随后到达）
```

## 四、有哪些 Skills 可以用（盘点）

> **诚实结论：本次部署没有用到任何 skill**——因为本地 skill 库里**没有 Cloudflare 专属 skill**，全程靠 `wrangler` CLI 直接完成。以下是相关 / 可类比 / 可配套的 skill，以及一个明显的 gap。

### 4.1 可直接类比的（部署类）
| Skill | 关系 | 说明 |
|-------|------|------|
| `deploy-to-vercel` | ⭐ 最接近 | Vercel 的一键静态部署，思路与 Cloudflare Pages 几乎一一对应（CLI 登录 → deploy → 拿 URL），是做 Cloudflare 版的最佳模板 |
| `vercel-cli` | 类比 | Vercel CLI 用法集合，可对照 wrangler |
| `github-profile-coolify` | 方向不同 | 走自建服务器 + Coolify 部署，适合需要自托管时参考 |

### 4.2 配套可用的
| Skill | 用途 |
|-------|------|
| `web-connect` / `playwright-cli` | 部署后用真实浏览器打开页面、截图、检查渲染（比 curl 更直观的验证） |
| `web-search` | 查 Cloudflare 官方文档时按全局硬约束必须先走此 skill 选工具 |
| `ob-collect` / `ob-topic` / `distiller` | 把这份部署经验沉淀进 Obsidian 知识库 |
| `skill-creator` | 若要把这套流程固化成可复用 skill，用它来创建 |

### 4.3 Gap（建议）
- **缺一个 `deploy-to-cloudflare` skill**：对标已有的 `deploy-to-vercel`，把「准备目录 → whoami 校验 → project create → pages deploy → curl 验证 → 处理 clean URL 308」固化成标准流程，下次一句话即可复用。

## 五、踩坑记录

1. **后台/非交互环境下 `npx wrangler` 会卡住**：首次安装的 "Ok to proceed?" 确认在非 TTY 下无人应答 → 必须加 `-y`。
2. **OAuth token 有有效期**：`default.toml` 里 `expiration_time` 到期后，靠 `refresh_token` 自动续；若两者都失效需重新 `wrangler login`（要浏览器）。无浏览器环境改用 `CLOUDFLARE_API_TOKEN`。
3. **项目同名报错不是 bug**：`pages project create` 对已存在项目会报 `code: 8000002`，直接跳到 `pages deploy` 即可。
4. **`.html` 被 308 重定向**：Pages 默认 clean URL，`/x.html` → `/x`。要让访问者拿到稳定地址，对外只给根路径 `/` 或无扩展名路径。
5. **代理**：wrangler 会自动识别环境里的 `http_proxy`/`https_proxy` 并用于请求（本机命令行走 HTTP 代理 `127.0.0.1:10802`）。

## 六、一句话复盘

> 单个静态 HTML 上 Cloudflare，最短路径就是 `npx -y wrangler@latest pages deploy <目录> --project-name <名字> --branch main`；难点不在命令，而在**鉴权（OAuth/Token）**、**非交互的 `-y`**、和 **clean URL 的 308 行为**这三个隐性点。

#教程 #Cloudflare #wrangler #部署
