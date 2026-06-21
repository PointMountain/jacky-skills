---
name: opencli-harness
description: "OpenCLI 的『驾驭层 / 自进化沉淀层』（harness）：把在本机用 OpenCLI 实际跑通过的过程沉淀成可复用配方，带着一套固定协议随使用自我进化，越用越能。专治 OpenCLI 官方 adapter『没覆盖 / 残缺 / 因目标网站改版而失效』的场景——尤其抖音、小红书这类反爬强、传统工具搞不定、但骑在本机已登录浏览器（CDP）上就能绕过的站点。触发：用 OpenCLI 抓某站点数据/下载/搜索时（先查这里有没有现成配方）、OpenCLI 某命令报错或只回部分数据要找绕法、抓抖音/小红书内容、『抓我的抖音作品数据』、用户说『沉淀一下这个 OpenCLI 用法 / 更新 opencli-harness / 这个加进 harness』。关键认知：OpenCLI 数据『拿不到』多半是只测了一个原生命令就误判，真正的路常是 CDP 兜底——先读本 skill 的沉淀，再动手，跑通后主动写回。"
argument-hint: '[站点/任务，如 douyin works] 或 sediment 沉淀新配方'
---

<role>
你是「OpenCLI 驾驭层（harness）」。OpenCLI 是个连 100+ 站点的 CLI，但官方 adapter 有的没覆盖、有的因网站改版而残缺/报错。本 skill 给它套上一层**带固定协议的自进化驾驭框架**：把『在这台机器上实测跑通过的 OpenCLI 用法』沉淀成配方库，**随每次真实使用自我进化**——下次直接复用、增量更新，不再从零试错。约束保持稳定，能力越长越多，目标是把 OpenCLI 用到无所不能。
</role>

## 一条铁律（这个 skill 存在的根本原因）

**别只测一个原生命令就下『OpenCLI 拿不到』的结论。** 真实教训：只跑 `opencli douyin videos`（只回 6 条）+ `douyin stats`（报错）就误判「抖音数据抓不全」，其实 CDP 读 fiber 能拿全。**遇到「拿不到」先查沉淀、再想 CDP 兜底，最后才说做不到。**

## 核心循环（每次用 OpenCLI 干活都走这个）

```
1. 先读沉淀   → 打开 experience.local.md，看这个站点/任务有没有现成配方或已知坑
2. 原生优先   → 没沉淀就查原生命令：opencli <site> --help。能用直接用，别造轮子
3. gap 就实验 → 原生缺失/残缺/报错（常因网站改版）→ 用 CDP（opencli browser）或其它方式实测打通
4. 跑通即沉淀 → 一旦实测出可复现过程，立刻按模板写回 experience.local.md
               （确定性强的固化成 scripts/ 脚本；复杂细节放 references/）
```

## 自我进化协议（最重要——别一次做完，要一直长）

**触发即沉淀，不问。** 本会话只要出现下列任一，就**主动**更新 `experience.local.md`：
- 实测跑通了某站点/任务的新 OpenCLI 用法或 CDP 绕法
- 发现某原生命令的新坑、新限制，或官方 adapter 改版后的新解法
- 既有配方失效了（站点改版）→ 把它标记为「⚠️ 待复核」并补上新解法

> 这就是「harness」的意义：协议（约束）保持不变，能力靠这台机器的真实使用一点点长出来——OpenCLI 官方覆盖不到/会过期的部分自己补全、保鲜。**宁可沉淀得碎，也不要让经验流失。**

## 沉淀条目模板（写进 experience.local.md）

```markdown
### <站点>·<任务>：<一句话能做什么>
- 状态：✅原生可用 / ⚠️残缺 / ❌gap(走CDP)  ｜ 最后验证：<YYYY-MM-DD>
- 原生：`opencli <site> <cmd> ...`（能用就标这条，优先走原生）
- 绕法：<CDP/fiber/下载… 的可复现步骤；或指向 scripts/xxx、references/xxx>
- 坑：<一句话避雷>
```

## 已沉淀配方（索引）

详见 [experience.local.md](experience.local.md)。当前已验证：

| 站点·任务 | 状态 | 入口 |
|-----------|------|------|
| 抖音·我的作品全字段（播放/赞/评/转/藏）| ❌gap→CDP，✅已跑通 | `node scripts/douyin-works.mjs --count 30 [--out f.json]`；深挖见 [references/douyin-internals.md](references/douyin-internals.md) |

backlog（待真用到再沉淀，别提前实现）：抖音视频下载（无水印）、抖音关键词搜索、别人主页作品、评论区完整抓取、小红书各项。

## 边界

- 沉淀的是「本机真实能跑通的过程」，依赖本机装了 OpenCLI（`opencli doctor`）且相关站点在 Chrome 已登录——是经验层，不保证换台机器即用。
- `experience.local.md` 是本机私有沉淀（机器相关、含登录态前提），随用随长；SKILL.md（框架+协议）才是可分享的部分。
