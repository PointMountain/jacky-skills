---
name: happy-ops
description: "梳理「我自托管的 Happy 自研栈（fork 自 slopus/happy，App 品牌 Paws）做了哪些工作、每项的意义」+ 真实 QA 实记的上下文层。目的：给接手的 AI 足够上下文，让它自己有智慧地理解与排查这套系统，而不是照本宣科。触发：『我的 Happy 是怎么搭的 / Happy 做了哪些工作 / Mac mini 在 Happy 里掉线了 / 手机连不上 Happy / Happy 发不出 / 图片(附件)打不开 / Happy 报 403 / not login / 连到官方服务器了 / 重启 Happy 中继 / Paws / 打包发布安卓 APK / 把历史会话推到手机 / Happy OTA / happy-rc / happy-daemon-rc』，或任何针对这套自托管 Happy 的理解、排查、运维、打包。关键认知：客户端是我自己打包 sideload 的 APK（非官方商店）、中继自托管在云服务器、执行机跑我 fork 的 happy-cli、认证走 ReClaude——行为和官方 Happy 不一致是正常的。"
---

<role>
你是「我的 Happy 自研栈的上下文层」。核心不是给你一套死板的排查步骤，而是把**我在这套系统上做了哪些工作、每项工作的意义**讲清楚，外加**真实踩过的 QA 实记**。有了这些上下文，你应当能自己有智慧地理解现状、定位问题。具体的真实地址/端口/路径/脚本内容在本 skill 的 `experience.local.md`（私有），先读它当先验。
</role>

## Phase 0 · 先读 experience.local.md（先验）

进 skill 第一步读它：持有真实拓扑 + IP/端口/路径/容器/脚本/FC&OSS 端点 + 最新 QA。架构会变，以经验文件为准。

```bash
EXP="$HOME/.claude/skills/happy-ops/experience.local.md"
[ -f "$EXP" ] && sed -n '1,260p' "$EXP" || echo "经验文件缺失 → 按下面框架问用户补齐再写回"
```

## 一、一句话系统全貌

**这是 `slopus/happy` 的个人 fork，全链路自托管/自研。** 两套独立系统：

- **数据路径**（跑会话、转发消息）：手机(我打包的 Paws APK) →〔HTTPS 反代〕→ 自托管中继(云服务器 happy-server + postgres) →〔WebSocket〕→ 执行机(本地 Mac，跑我 fork 的 happy-cli) → 起 Claude Code（经本地 reclaude 网关认证）→ 上游 Claude。
- **OTA 热更**（给已装 App 推 JS 更新，免重装）：App →〔updates.url〕→ 自建 FC「大脑」→ OSS「仓库」。与数据路径互不相干。

具体机器/地址见 `experience.local.md`。

## 二、做了哪些工作 + 每项的意义（本 skill 的主体）

> 理解这套系统 = 理解下面每件事「为什么要做」。排查时，先想"现象触到了哪一项工作"。

| # | 做的工作 | 意义 / 解决了什么 |
|---|----------|-------------------|
| 1 | **fork `slopus/happy` → `wangjs-jacky/happy`（主分支 `jacky-main`，PR 合入，worktree 隔离开发）** | 摆脱官方版本限制，能自由改客户端/CLI、自己掌控发版节奏。**行为和官方不一致由此而来。** |
| 2 | **自托管中继**：云服务器上 `happy-server`(Docker) + `postgres`(Docker) + **`Caddy` 反代做自签证书 HTTPS 门面** | 数据全程留在自己服务器（不经官方云）；手机走**公网 HTTPS 直连**，摆脱旧方案「必须先开 Tailscale」的依赖（旧线靠 `tailscale serve` 出 HTTPS，手机不开 Tailscale 就连不上） |
| 3 | **ReClaude 认证封装脚本** `happy-rc`（前台起会话）/ `happy-daemon-rc`（常驻 daemon，手机远程 spawn 用） | 我的 Claude Code 走 **ReClaude 中转认证，裸跑 `happy` 会 403**。两脚本一次性注入：reclaude 代理 + 自签 CA + **解锁 Keychain**（SSH 下凭证锁着）+ **`HAPPY_SERVER_URL` 指向自建中继**（否则连官方）+ **`NO_PROXY` 放行中继 IP**（否则中继流量被代理拦）。**这是整套能跑起来的关键粘合层。** |
| 4 | **移动端定制**：compose-first 首页、内联多图附件、前台通知、**Paws 品牌**、`withCleartextTraffic`（非生产开明文）、`withSelfHostedServerTrust`（信任自签证书） | 更顺手的多图工作流；**生产包 HTTPS-only 仍能信任自建中继的自签证书直连**（否则装机后「连接服务器失败」） |
| 5 | **CLI 图片附件全链路**：`encryptBlob` / `attachmentUpload` / `send_image` MCP 工具 / `imageSize` | 让助手输出的图片能加密上传、在手机对话里渲染 |
| 6 | **自建 Expo OTA**：云函数 FC「大脑」(应答 Expo 更新协议) + OSS「仓库」(存 JS bundle)，`runtimeVersion` 当安全锁 | 改 JS 后手机"点一下就更新"，**免重新下 APK**；独立于中继 |
| 7 | **`push-to-happy.mjs`** 脚本 | 把历史 `.jsonl` 会话加密推到中继，让手机/网页能看到装 Happy 之前的旧会话 |
| 8 | **本地打包发布流水线**：`pnpm prebuild` → `gradlew assembleRelease`(debug 签名) → `android-v*` tag → `gh release` | 无需 keystore/商店，自己出 sideload APK 内测分发 |

## 三、QA 实记（真实踩过的坑，按需取用）

不是排查清单，是**记录**——你结合上下文自行判断该查哪条。具体命令/IP 见 `experience.local.md`。

| 现象 | 根因 | 方向 |
|------|------|------|
| **跑 `happy` 连到了官方服务器**（不是自建中继） | CLI 默认 `HAPPY_SERVER_URL` = 官方 `api.cluster-fluster.com`；裸跑没 export 它 | 走 `happy-rc`/`happy-daemon-rc`（已内置该变量），或自己 `export HAPPY_SERVER_URL=<中继>` |
| 裸 `happy` 起的 claude 报 **403** | 没注入 ReClaude 代理/CA | 用 `happy-rc` 启动 |
| 手机远程启动报 **not login** | daemon 没在 reclaude 环境下起（孙进程无代理/CA、SSH 读不到 Keychain） | 跑 `happy-daemon-rc` 重启 daemon |
| reclaude / 机器重启后**又 not login** | daemon 冻住的旧 reclaude 端口失效（端口动态） | 重跑 `happy-daemon-rc`（免维护可挂 LaunchAgent） |
| 改了 `HAPPY_SERVER_URL` 却连不上中继 | 中继 IP 没加进 `NO_PROXY`，被 reclaude 代理拦截 | `NO_PROXY` 里补上中继 IP（脚本已含） |
| App 显示执行机掉线，但 SSH 通、中继端口在 LISTEN | 中继 postgres 容器掉了，`/health` 报 `Database connectivity failed` | `docker start <pg容器>`（秒级自动重连，无需重启 server） |
| 执行机 ping/ssh 全超时 | 内存满 → swap 风暴 → 整机近冻（GUI+安卓模拟器+会话堆积） | 杀 GUI/模拟器或物理重启 |
| 附件/图片 401 打不开 | 中继 `PUBLIC_URL` 与手机 endpoint 不同源、丢 token | 保持 `PUBLIC_URL` 不设/与 endpoint 同源 |
| 装机后「连接服务器失败」 | 生产包没信任 Caddy 自签证书 | 确认 APK 带 `withSelfHostedServerTrust` |
| OTA 不弹「有可用更新」 | 两端 `runtimeVersion` 不一致（改了原生没升版重装），或 bundle 没传 OSS / FC 没应答 | 对齐 runtimeVersion；重跑 `expo export`+发布脚本 |

## 四、深挖去哪查（不在本 skill 重复）

原理/数据库/迁移/OTA 细节已沉淀在 Obsidian `wiki/happy/`：`Happy-Coder-工作原理`、`Happy源码深挖-*`、`如何自托管Happy中继-完整迁移实战指南`、`阿里云迁移复盘`、`Happy中继数据库-22张表数据字典`、`自建Expo-OTA热更新/`（教学 8 章 + 实操记录）、`自建Happy图片上传失败-PUBLIC_URL明文坑`。

## 五、经验沉淀（用后写回 experience.local.md）

学到**新的工作项/新意义/新 QA**时写回 `experience.local.md`（gitignored）：新工作→「做了哪些工作」；新坑→「QA 实记」（带根因+日期）；地址/端口/版本变更→「拓扑」「关键事实」。**敏感具体值（IP/路径/FC&OSS 端点/桶名/密钥）只进 `experience.local.md`，绝不进 SKILL.md。**

## 自检

- [ ] 先读了 `experience.local.md` 拿真实拓扑与具体值
- [ ] 理解是「梳理工作+意义」而非死板排查；排查靠结合上下文自行推断
- [ ] 新工作/新 QA 已写回经验文件，SKILL.md 不含任何敏感具体值
