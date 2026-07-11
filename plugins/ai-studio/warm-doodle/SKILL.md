---
name: warm-doodle
description: "暖绘——为技术文章生成温暖手绘风插图。圆滚滚的小人 + 铅笔底稿 + 水彩晕染，把抽象概念画成有人情味的小场景。当用户说「暖绘」、「warm-doodle」、「给文章配几张手绘图」、「Q版配图」、「温暖手绘风插图」时触发。"
argument-hint: '[文章路径或主题]'
---

# warm-doodle（暖绘）

> 把技术文章里的抽象概念，画成牛皮纸上圆滚滚的小人小场景——亲切、松弛、有手温，但不幼稚。

## 设计哲学

三条原则贯穿所有出图决策，冲突时按顺序取舍：

1. **纸感优先**：一切都像画在米色纸面上。颜色要"洇"进纸里，而不是"贴"在屏幕上。
2. **人比图标重要**：能用"小人正在做某事"表达的概念，就不用抽象图标。读者记住的是场景，不是符号。
3. **一图一事**：每张图只讲一个论点。想塞两个论点，就拆成两张图。

## 出图工作流

### Step 1 — 读文拆点

通读文章，列出候选配图点。常见的五类位置：

| 配图点 | 作用 | 典型版式 |
|--------|------|----------|
| 开篇定调图 | 建立文章氛围，点出核心矛盾 | 单幕剧 |
| 概念解释图 | 把抽象机制具象化 | 单幕剧 / 放射图 |
| 方案对比图 | 新旧/优劣并置 | 左右对照 |
| 步骤流程图 | 展示先后顺序 | 流程跑道 / 时间轴 |
| 收尾总结图 | 回收全文要点 | 四宫格 |

向用户确认数量和位置后再动笔（用户已明确要求时跳过确认）。

### Step 2 — 选版式

从下方版式库中为每张图挑一种，系列图版式尽量不重复。

### Step 3 — 组装 Prompt

按「四层叠加公式」组装（见下文），完整成品示例见 `references/prompt-recipes.md`。

### Step 4 — 生成与体检

调用当前环境可用的生图工具（如 gpt-image-2），尺寸选最接近目标比例的档位（16:9 → 1792×1024）。生成后过一遍「一致性自查」。

> 国内生图服务（如 CogView）会在右下角强制加「AI生成」标识。私人笔记使用时可用 PIL 羽化贴片修复（从同一晕染带取干净区域覆盖，先备份原图）；若图片要**公开发布**，按 AIGC 标识规定应保留标识或在文中注明 AI 生成。

## 调色盘

| 名字 | 色值 | 用在哪 |
|------|------|--------|
| 米纸 | `#FBF3E4` | 全图底色，纸张本身 |
| 桃绒 | `#FFE3C8` | 卡片底、需要轻微强调的区域 |
| 杏黄 | `#F4B860` | 高光、暖意、次级强调 |
| 暖橙 | `#E8833A` | 主强调色、标题横幅、视觉焦点 |
| 砖赭 | `#A65A2E` | 边框、重点字、压住画面的深色 |
| 咖啡 | `#5C4033` | 正文字、最深的接地元素 |
| 朱砂 | `#D9534F` | 情绪爆点、错误标记，每图至多一处 |
| 暖灰 | `#4E4B47` | 小字标注 |
| 雾灰 | `#ADB2BD` | 失败方案、被淘汰的旧物、配角化处理 |

口诀：**米纸打底，橙黄唱戏，砖咖压场，朱砂点睛，雾灰退后。**

## 小人画法

口诀：**圆脑袋、豆豆眼、短手短脚、动作说话。**

- 头身比约 **2 ~ 2.5**，头要明显大于身
- 眼睛是两颗小豆豆，嘴巴一条小弧线，五官越省越好
- 情绪全靠肢体：耸肩摊手 = 困惑，原地跳起 = 惊喜，瘫坐成一滩 = 崩溃，叉腰挺胸 = 得意
- 轮廓线是铅笔质感，允许轻微抖动和断笔——画得太"准"反而出戏

### 常驻角色班底

系列配图共用同一套班底，保证人物认得出来：

| 角色 | 长相 | 穿着 | 出场场景 |
|------|------|------|----------|
| **阿码** | 圆框眼镜，头发微乱 | 姜黄色套头衫 | 写代码、踩坑、修 bug 的主角 |
| **小绘** | 丸子头，常抱画板 | 杏色围裙式上衣 | 设计、审美、界面相关 |
| **豆豆** | 一根呆毛，眼睛最大 | 米白连帽衫 | 新手提问、引出概念 |
| **波特** | 奶白色小机器人，单根弹簧天线，胸口一颗橙色圆灯 | —— | AI / 自动化 / 工具拟人 |
| **橘猫** | 一只圆橘猫 | —— | 彩蛋，可趴在任何画面角落，不抢戏 |

按文章题材可临时加新角色，但外观必须能用一句话描述清楚（方便后续图保持一致）。

## 版式库

| 代号 | 版式 | 结构 | 适合 |
|------|------|------|------|
| A | 单幕剧 | 一个完整小场景占满画面 | 定调、讲一个概念 |
| B | 左右对照 | 左右两栏，中间手绘虚线或留白分隔 | 新旧对比、方案优劣 |
| C | 四宫格 | 2×2，每格一个小标题横幅 | 总结四个要点 |
| D | 流程跑道 | 横向 3~5 站，角色沿路前进 | 步骤、管线 |
| E | 放射图 | 中心一个主体，周围辐射小节点卡片 | 一拖多的结构关系 |
| F | 时间轴 | 横向时间线，节点上方小场景 | 演进史、版本变迁 |

对比版式（B）的惯例：胜者一侧用橙黄暖调 + 角色表情积极；败者一侧整体降为雾灰 + 角色蔫掉，**不画大红叉**，用色彩和情绪分胜负。

## Prompt 四层叠加公式

每张图的 prompt = **基底层 + 版式层 + 角色层 + 手写字层**，按顺序拼接。

### ① 基底层（固定，每张图原样带上）

```
A 16:9 illustration that looks hand-drawn on warm cream paper (#FBF3E4).
Chibi-proportioned cartoon characters: big round heads, tiny bodies
(roughly 2 to 2.5 heads tall), bean-dot eyes, a single curved line for
the mouth, emotions shown through exaggerated body language.

Rendering: visible graphite pencil linework with slightly wobbly, human
strokes, filled with soft watercolor washes that bleed gently past the
outlines. Palette anchored on apricot (#F4B860), warm orange (#E8833A),
brick (#A65A2E) and coffee brown (#5C4033) over the cream paper ground.
Generous empty breathing room around every element.

Never: cool blue/purple dominance, 3D rendering, glossy gradients,
photo-realistic faces, dense paragraphs of text, hard ruler-straight
boxes, flat digital fill without watercolor texture.
```

### ② 版式层

声明选用的版式和各区块内容，如：

```
LAYOUT: split comparison. LEFT half "<左侧主题>" in warm tones; RIGHT
half "<右侧主题>" desaturated to muted gray (#ADB2BD). A loose
hand-drawn wavy line divides the two halves.
```

### ③ 角色层

每个出场角色一行：`谁 + 在做什么 + 什么情绪`，如：

```
CHARACTERS:
- A-Ma (round glasses, ginger sweater): typing happily, surrounded by
  three floating done-checkmarks.
- Bot (cream-white little robot, spring antenna, orange chest light):
  handing him a steaming cup, proud.
```

### ④ 手写字层

```
HANDWRITTEN LABELS (casual Chinese brush handwriting, large and legible):
"<标注1>" above the left scene, "<标注2>" below the robot.
```

**中文乱码降级路径**（部分生图模型如 CogView 画手写汉字易出错字）：
1. 首选标签 ≤ 4 字，并在 prompt 里强调 every stroke accurate
2. 生成后检查仍有错字 → 去掉图内文字（`TEXT: absolutely no text anywhere`），标签改写进笔记的图注（引用块）里
3. 宁可无字，不可错字——带错字的图一律不交付

## 尺寸与落盘

- **封面/横幅**：16:9，生图档位 1792×1024
- **内文插图**：同为 16:9，或方图 1024×1024（放射图、四宫格也适合方图）
- **命名**：`<文章slug>-fig01.png`、`-fig02.png` … 按出现顺序编号
- **存放**：文章同级 `assets/` 目录；若目标是 Obsidian 笔记，则存 vault 的附件目录并用 `![[]]` 嵌入

## 一致性自查（系列图必做）

- [ ] 同一角色的发型、眼镜、衣服颜色在每张图里一致
- [ ] 所有用色都在调色盘九色之内
- [ ] 手写中文清晰可读、没有错字
- [ ] 每张图留白充足，没有塞满
- [ ] 没有出现红线清单里的元素

## 红线清单

以下元素一旦出现即重画：

- 冷色（蓝/紫/青）主导画面
- 3D 立体效果、投影硬阴影、光泽渐变
- 写实比例或写实人脸
- 直尺画出来的方框、生硬表格线
- 大段密排文字
- 没有水彩纹理的纯平涂色块
- 复杂的背景纹理或照片素材

## 适用与不适用

**适用**：技术博客、教程、复盘文章、方法论分享、团队协作话题、产品功能说明。

**不适用**：正式商务汇报、数据密集的报表图、需要精确品牌色的营销物料、学术论文插图。
