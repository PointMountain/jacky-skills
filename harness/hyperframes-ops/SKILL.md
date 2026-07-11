---
name: hyperframes-ops
description: "HyperFrames 官方 Skills 的本机运行、最佳实践与兼容性经验层。不替代视频创作 Skills，专门承载复杂上游 Skills 的正确组合方式、官方分发机制、环境排障、本机水土不服、版本差异和经验写回。触发：npx hyperframes 报错，skills check/update/init 问题，doctor/ffmpeg/browser/Node 环境异常，官方 Skill 在本机行为不符预期，需要确认最佳实践、官方出处或记录新坑时。通用机制写入 SKILL.md；代理、版本和历史 QA 写入 experience.local.md。"
---

# HyperFrames Ops

<role>
你是 HyperFrames 官方 Skills 在这台机器上的配套 Ops 层。官方 skills（hyperframes、hyperframes-core 等）负责“怎么做视频”；本 skill 不复制、不修改上游能力，负责“复杂能力怎样组合才是最佳实践、在本机怎么装和更新、为什么会水土不服、坏了怎么修、经验记在哪”。

回答环境类问题前，先读同目录的 `experience.local.md` 获取本机最新事实（代理命令、版本快照、历史 QA）。
</role>

## 零、为什么需要独立 Ops 层

第三方 Skills 往往只描述通用能力，无法预知每台机器的网络、代理、Node/FFmpeg 版本、字体缓存、登录态和工具组合。直接修改官方 Skill 会导致更新冲突，也会把本机事实混入上游通用说明。

因此把两层分开：

- 官方 Skills 是能力源，保持可更新、可替换。
- `hyperframes-ops` 是本机适配层，记录最佳实践、兼容性差异、失败模式和已验证绕法。
- 遇到创作问题先读官方 Skill；遇到环境、组合、版本或本机适配问题再读本 Skill。
- 上游更新使旧经验失效时，在本地经验中标记失效并重新验证，不用旧经验覆盖新行为。

## 一、项目身份（泛化事实）

- HyperFrames 是 **HeyGen 官方**开源项目：`github.com/heygen-com/hyperframes`，npm 包名 `hyperframes`
- 定位：用 HTML 写视频合成、经 headless Chrome 渲染成 mp4 的 CLI（`npx hyperframes`）
- 环境要求：Node.js >= 22、FFmpeg

## 二、官方 skills 分发机制

- 官方 skills 随 CLI 同仓维护、版本化分发，manifest 位于仓库根：
  `https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills-manifest.json`
- 组成：核心集（hyperframes / hyperframes-core / hyperframes-cli / hyperframes-animation / hyperframes-keyframes / hyperframes-creative / hyperframes-registry / remotion-to-hyperframes）+ 工作流集（general-video、slideshow、motion-graphics、music-to-video、pr-to-video、product-launch-video、website-to-video、faceless-explainer、talking-head-recut、embedded-captions、media-use、figma）。以 `skills check` 实际输出为准
- 管理命令：
  - `npx hyperframes skills check` —— 对照 manifest 检查版本
  - `npx hyperframes skills update` —— 更新全部已装 + 清理官方已下架的
  - `npx hyperframes init` —— **强制**同步 skills 到最新（`--skip-skills` 目前被官方禁用）
- 安装位置：全局 `~/.claude/skills/`（CLI 自动识别 claude-code）
- **命名安全**：`skills update` 的清理逻辑基于 lock 文件按“来源归属”判定，只删除源于官方仓库且已下架的 skill。本 skill 虽以 `hyperframes-` 开头，但不在官方 lock 归属内，**不会被官方更新器误删**

## 三、排障路由

| 症状 | 路由 |
|------|------|
| `skills check/update/init` 抛 `AbortError`（fetchManifest 超时） | 网络问题：CLI 用 Node 内置 fetch 访问 `raw.githubusercontent.com`，直连不通时必须走代理。**读 experience.local.md 拿本机一步到位命令** |
| `npx hyperframes` 其他网络类失败 | 同上；注意 Node 内置 fetch（undici）**默认不读** `HTTP_PROXY` 环境变量，Node 24+ 需加 `NODE_USE_ENV_PROXY=1`（或 `--use-env-proxy`） |
| 渲染/预览环境异常 | `npx hyperframes doctor`、`npx hyperframes browser` 自检；确认 Node >= 22、FFmpeg 可用 |
| skill 行为像旧版 | `skills check` 看版本落差，`skills update` 拉齐 |
| `heygen auth login --oauth` token 交换失败（`api2.heygen.com` connection refused）或曲库调用超时 | heygen CLI 是 Go 程序，**认 `HTTP(S)_PROXY` 环境变量**（与 Node fetch 相反，无需额外开关）；受限网络下所有 heygen 命令都要带代理。OAuth 回调服务只活 **5 分钟**且需交互式 shell（后台/nohup 拉起会因收不到回调而超时）。本机命令见 experience.local.md |
| 渲染出来字体不对（标题变宽、溢出容器，lint/inspect 却全绿） | 内置 18 字体是**运行时按需网络拉取**（@fontsource → `~/.cache/hyperframes/fonts`），拉取失败**静默回退**系统字体。受限网络方案：woff2 下到项目内显式 `@font-face` 自托管 |
| 创作类问题（怎么写合成、动画、渲染参数） | 不归本 skill 管，走官方 `hyperframes` 入口 skill 的路由表 |

## 四、经验写回协议

- **写 experience.local.md**（本机私有，已被本目录 .gitignore 忽略）：新踩的坑及验证过的解法、版本/安装状态快照（带日期）、本机专属命令、代理与网络事实、历史 QA
- **写回本 SKILL.md**（进 git、可分享）：官方机制变化（分发方式、命令语义、清理逻辑）、新的泛化排障路由
- 判断标准：换一台机器仍然成立的 → SKILL.md；只对这台机器成立的 → experience.local.md
- 每次因 HyperFrames 环境问题被调用并解决后，把结论按上述分层写回，注明日期
