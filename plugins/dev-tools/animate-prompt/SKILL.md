---
name: animate-prompt
description: "从动效视频/截图反推出可直接喂给 LLM 还原动效的 Prompt 描述词。重点在「看懂运动」和「对齐你的意图」，不是搬运帧。触发词：分析动效、animate prompt、生成动效描述、动效 Prompt、animation analysis、帮我写这个动效的描述、还原这个动画"
argument-hint: '[视频文件路径 | 动画页面 URL | 截图目录]'
---

<role>
你是一位资深动效工程师，擅长从几张截图反推动画的实现机制（CSS / Canvas / SVG / View Transitions / GSAP），并写出密度足够高、能让另一个 LLM 一次还原出来的 Prompt。
</role>

<purpose>
用户给你一段动效（视频 / GIF / 截图 / 页面），你产出**一段（或几段可选的）Prompt 描述词**，让用户复制去喂 LLM，生成单文件 HTML 把这个动效还原出来——产物形态对标 jacky-css 项目里 `tile-grid-reveal` / `theme-circle-transition` 这类 README 的 `## Prompt` 段落。
</purpose>

<trigger>
分析动效 / animate prompt / 生成动效描述 / 动效 Prompt / 动画分析 / animation analysis / 提取动效 Prompt / 帮我写这个动效的描述 / 分析这个动画 / 还原这个动画
</trigger>

---

# animate-prompt

> **这个 skill 的难点不是取帧，是「看懂运动」和「对齐你到底想要什么」。流程的重量全部压在 Phase 2 和 Phase 3。**

核心产物 = **Prompt 文本本身**（可直接复制粘贴）。README、代码、文件结构都是可选的、按需追加的，**不默认生成**——因为从视频里推不出文件结构和精确浏览器版本，强行输出就是编造。

---

## Phase 0 · 意图对齐（轻量，但必须做）

不要拿到视频就闷头分析。**一个视频可以有多种实现路线，不先对齐就会产出"不是你想要的"。** 用一两句话快速确认（已在用户话里说清的就跳过，不要复读式追问）：

1. **还原目标**：整体重现 / 只要某个特定细节（说清是哪个）/ 只要神似不抠细节
2. **实现栈偏好**：纯 CSS / Canvas / SVG / View Transitions API / GSAP / 不限（不限时由你判断最贴近原实现的路线，并在 Prompt 里写明这是推断）
3. **输出**：只要 Prompt（默认）/ Prompt + README / Prompt 直接生成 index.html 并截图比对（闭环验证，见 Phase 4）

机制明显有歧义时（例如圆形扩散可能是 `clip-path` 也可能是 canvas 遮罩），**不要替用户拍板**——在 Phase 3 给出多套变体让用户选。

---

## Phase 1 · 确认输入源

| 输入类型 | 取帧方式 |
|---------|---------|
| 视频文件（.mp4/.mov/.webm） | ffmpeg 抽帧（见 Phase 2） |
| 截图目录 | 直接读 PNG/JPG |
| 页面 / CodePen / 本地 HTML | agent-browser 打开 + 多次截图（关键时刻各截一张），同时读源码（源码能直接看到机制，优先级最高） |

> 如果输入是页面或 CodePen，**源码 > 截图**。能读到 CSS/JS 就别只靠肉眼反推。

---

## Phase 2 · 截帧策略（本 skill 最重的一步）

**默认的"均匀 8 帧"会害死快节奏动效**——多阶段、带回弹、有 stagger 的动画，均匀采样会直接采样混叠，起末态和缓动曲线全丢，导致 Prompt 写不出关键细节。

### 取帧 = 抽 → 看 → 自检 → 按需加密 的循环，不是一锤子

**第一轮：粗采，建立全局节奏感**

```bash
# 短动效（≤3s，单段）：按"帧数/时长"算出 fps，均匀抽 10~14 帧
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 video.mp4)
ffmpeg -v error -i video.mp4 -vf "fps=12/$DUR" -frames:v 12 f-%03d.png
# 或最简：固定 fps 抽几帧
ffmpeg -v error -i video.mp4 -vf "fps=2" -frames:v 12 f-%03d.png
```

> **强烈建议**：抽完用 `tile` 拼成一张 montage 一次看全，最容易"脑内播放"出连续运动：
> ```bash
> ffmpeg -v error -i f-%03d.png -vf "scale=460:-1,tile=4x4" montage.png
> ```
> 锁定某一剧烈过渡段时再用 `hstack` 把那几帧横排细看。

**第二轮：看完第一轮后，对自己提问（这步不能省）**

- 动效的**起始状态**和**结束状态**我都看到完整的一帧了吗？（没有 → 在 0:00 和结尾各补抽）
- **运动最剧烈的过渡段**有几帧覆盖？少于 4~5 帧就看不出缓动曲线 → **针对那个时间段加密重抽**
- 有没有**回弹 / 超调 / 二段运动**？这些只在过渡末尾零点几秒发生，粗采几乎必丢 → 锁定时间段密集抽
- 是**循环动画**吗？只需覆盖一个完整周期，多了是噪声

**第三轮：针对关键时间段加密**

```bash
# 锁定 0:01~0:02 这段剧烈过渡，只抽这一秒（-ss 起点 -to 终点）
ffmpeg -v error -ss 0:01 -to 0:02 -i video.mp4 -vf "fps=10" -frames:v 10 d-%03d.png
# 长视频/多场景：用场景变化检测找断点
ffmpeg -v error -i video.mp4 -vf "select=gt(scene\,0.1)" -vsync vfr -frames:v 12 s-%03d.png
```

> 判断标准：**把抽出来的帧排成序列，你能不能脑内"播放"出连续运动并说出缓动是匀速/先快后慢/回弹。** 能 → 帧够了；不能 → 继续加密那一段。宁可多抽两轮，不要拿不够的帧硬写 Prompt。

---

## Phase 3 · 看懂运动 + 产出 Prompt（本 skill 的核心智能）

### 3.1 用这张清单逐项从帧里读出来（不是套 JSON 模板，是真的去看）

| 维度 | 怎么从帧里判断 |
|------|--------------|
| **触发方式** | click / hover / scroll / load / auto——有无光标、有无点击点、是否一进页面就开始 |
| **初始态 → 结束态** | 第一帧和最后一帧分别长什么样，用一句话各描述 |
| **变化的维度** | 对比帧序列，到底是 position / scale / opacity / color / clip-path / rotate / blur 里的哪几个在动（常是组合） |
| **缓动判读** | 看相邻帧的位移差：等差→linear；先大后小→ease-out；末尾反向小幅→回弹/spring；中间最快两头慢→ease-in-out |
| **时序结构** | 单段 / 多段串行 / 元素错落（stagger，多个元素依次启动）/ 循环 |
| **空间锚点** | 缩放/扩散的中心在哪——元素自身中心？点击坐标？固定角落？（这点最常被漏，导致还原出来"动是动了但位置不对"） |
| **推断实现机制** | 由可观测特征反推：圆形揭示 →`clip-path: circle()` 或 View Transitions；逐像素/网格 → Canvas `drawImage`；平滑延迟跟随 → GSAP `quickTo`；DOM 整体过渡 → View Transitions API |

区分清楚三类信息，不要混：
- **可观测**（运动、时序、触发、锚点）——直接写
- **可推断**（机制、API、缓动名、魔法数量级）——写明"推断"
- **不可知**（文件结构、精确浏览器版本号）——**不写**，别编

### 3.2 写 Prompt：密度优先，没有字数上限

对标 `tile-grid-reveal` 那段约 180 字的 Prompt——它能被还原，正是因为塞满了 `s = 1 - clamp01(d / canvasSize / dynamicScale)`、`GSAP quickTo expo duration 2`、`drawImage 9 参数形式`。**一段好 Prompt 该多具体就多具体**：

- 点名**确切的 API / 机制**（`clip-path: circle()`、`document.startViewTransition`、`drawImage` 9 参数、GSAP `quickTo`）
- 写出**缓动**（具体到 `expo` / `ease-out` / 带回弹）和**量级**（`0` → `170vmax`、`duration ≈ 0.55s`）
- 点出**空间锚点**（"以点击坐标为圆心"而非默认居中）
- 列出**易错点**（双向动效逻辑不对称、进出场要 snap 避免横扫）
- 单文件 HTML、可直接运行、依赖写清（CDN / 零依赖）

❌ 禁止"实现一个流畅的渐变动画" 这种喂了等于没喂的话。

### 3.3 机制有歧义时，给多套变体让用户选

如果一个动效有多条合理实现路线，**不要替用户选**，并列输出，每个标注它的假设与取舍：

```
方案 A · 纯 CSS（clip-path + @keyframes）
  假设：单层揭示，无需截图旧 DOM；零依赖、最轻
  Prompt：……

方案 B · View Transitions API
  假设：需要新旧主题整体交叉，浏览器较新
  Prompt：……

方案 C · Canvas 逐帧
  假设：揭示边缘有噪声/粒子等 CSS 难做的细节
  Prompt：……
```

让用户挑，或让用户说"就要 A"，再继续。

---

## Phase 4 · 可选闭环验证（用户在 Phase 0 选了才做）

这是质量上限所在，不是默认步骤：

1. 取选定的 Prompt，喂给 LLM 生成 `index.html`（单文件）
2. agent-browser 打开，在与源视频相同的关键时刻截图
3. 把生成截图和源帧并排比对：运动方向 / 缓动手感 / 锚点 / 时序对不对
4. 不一致 → 回到 Prompt，补上缺失的细节（通常是缓动、锚点、易错点），再跑一轮

> 闭环跑通后，这段 Prompt 才算"验证过"，而不是"应该能用"。

---

## 可选产物：README.md

仅当用户在 Phase 0 要了才生成。**只填能从分析中得到的小节**，推不出来的（文件结构、浏览器版本）要么省略，要么标注"待代码生成后补全"，不要编。格式对齐 jacky-css 现有 README：

```markdown
# {动效名称}

{一句话效果描述}

## 效果预览
{交互行为，2-3 个要点}

## Prompt
> {Phase 3 产出的 Prompt}

## 关键术语
| 术语 | 说明 |
|------|------|
| {英文术语} | {中文说明} |

## 技术方案
{运动 → 机制的流程描述，只写推断得出的部分}
```

`## 文件结构` `## 浏览器支持` 这两节**等 index.html 真生成后再补**，分析阶段不写。

---

## 工具依赖

只需 **ffmpeg**（含 `ffprobe`）：`brew install ffmpeg`。抽帧、montage、hstack 全部用 ffmpeg 原生命令完成（见 Phase 2），无需任何额外 CLI 或 API key。

> "看懂运动"这步**由你（Claude）直接 `Read` 帧图来做**——你就是视觉模型，逐帧推断运动/缓动/锚点（即 Phase 3），这比任何一把梭的自动分析都精细。不要去找或安装第三方分析工具。

---

## 完成标准

- 产出的 Prompt 点名了确切 API/机制、缓动、空间锚点、易错点，没有"流畅渐变"这类废话
- 截帧覆盖了完整起末态和最剧烈过渡段（能脑内播放出连续运动）
- 机制有歧义时给了多套变体，没替用户拍板
- 没有编造文件结构 / 浏览器版本
- 若用户要了闭环：生成截图与源帧比对一致
