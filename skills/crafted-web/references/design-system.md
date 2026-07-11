# 设计系统：纪律 + Token 脚手架 + 配色方法论

> 在定 design tokens、写 CSS 前读本文。「贵感」来自纪律与一致性，不是堆元素。

## 目录

- 一、设计原则（贵感从哪来）
- 二、可复用 Design-Token 脚手架
- 三、配色定调方法论
- 四、4 套起手配色（锚点，非锁定）

---

## 一、设计原则（贵感从哪来）

### 字体纪律（最影响精致度）

- 用**模块化字号阶梯**（如比例 1.2~1.25：12/14/16/20/25/31/39…），全页就这一套阶梯；小字可 .5px 微调。
- **字重 ≤ 3 档**（700 标题 / 600 强调 / 400 正文）。克制 = 高级。
- 正文 `line-height` 1.5~1.7，密集小字 1.3~1.4；大标题 `letter-spacing:-0.01em ~ 0.02em`。
- 数字密集处用 `font-variant-numeric:tabular-nums`；全局 `-webkit-font-smoothing:antialiased`。
- 界面字体优先系统栈 `-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif`；代码 `ui-monospace,SFMono-Regular,Menlo,monospace`。

### 颜色纪律

- 背景分 **2~3 层**（页面底 / 一级面板 / 二级卡片），靠明度差建立深度。
- **1 套中性 ramp + ≤ 2 强调色**；强调色只用在小面积焦点。
- 多用 **alpha 微妙感**：淡填充 8~15%、边框 20~40%，而非实色块。
- 文字分 3 级，对比达标（正文 ≥ 4.5:1，大字 ≥ 3:1）。

### 间距与节奏

- 走 **8px 基准网格**（4/8/12/16/24/32/48/64），间距成体系。
- 留白要足；相关近、无关远（亲密性原则）。严格对齐。

### 深度与细节

- 暗色靠**发光**、亮色靠**柔和投影**；阴影大而淡，不要硬黑边。
- 圆角成阶梯且全站一致；边框克制（1~1.5px、低对比）。
- 可交互元素都有 hover/focus 微反馈。

---

## 二、可复用 Design-Token 脚手架

先填这块，全站只用变量。按下方「配色方法论」决定 ramp 与强调色后回填颜色值。

```css
:root{
  /* —— 颜色：1 套中性 ramp + 1~2 强调色 —— */
  --bg:; --surface-1:; --surface-2:; --border:;
  --text-1:; --text-2:; --text-3:;
  --accent:; --accent-2:;
  --ok:#3fb950; --warn:#d29922; --danger:#f85149;

  /* —— 字号阶梯 —— */
  --fs-xs:12px; --fs-sm:14px; --fs-base:16px; --fs-lg:20px;
  --fs-xl:25px; --fs-2xl:31px; --fs-3xl:39px;

  /* —— 间距 8px 网格 —— */
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px;
  --sp-6:24px; --sp-8:32px; --sp-12:48px; --sp-16:64px;

  /* —— 圆角 —— */
  --r-sm:6px; --r-md:10px; --r-lg:14px; --r-pill:999px;

  /* —— 阴影 / 发光 —— */
  --shadow-1:0 1px 3px rgba(0,0,0,.12), 0 1px 2px rgba(0,0,0,.08);
  --shadow-2:0 8px 30px rgba(0,0,0,.16);
  --glow:0 0 0 1px var(--accent), 0 0 24px -6px var(--accent);

  /* —— 动效 —— */
  --dur-1:160ms; --dur-2:320ms; --dur-3:640ms;
  --ease-out:cubic-bezier(0.16,1,0.3,1);
  --ease-inout:cubic-bezier(0.65,0,0.35,1);
  --ease-spring:cubic-bezier(0.34,1.56,0.64,1);
}
```

- **亮色**用上面的 `--shadow-*`。
- **暗色**把背景换深，深度改用 `--glow` 和提亮，阴影用 `rgba(0,0,0,.3+)`。

---

## 三、配色定调方法论（风格中立）

1. **先决定明 / 暗**：深度阅读 / 密集信息 → 亮色或柔和暗；展示 / 戏剧 / 沉浸 → 暗色。
2. **选 1 套中性 ramp**（冷灰 / 暖灰 / 中性，5~6 级）铺背景 / 面板 / 文字 / 边框——占画面 90%。
3. **选 1 主强调色 + 可选 1 次色**：取素材「主题色」，只用在焦点。
4. **情绪 → 色相**：
   - 科技 / 信任 = 蓝 / 青
   - 活力 / 紧迫 = 橙 / 红
   - 增长 / 金融 = 绿
   - 高端 / 创意 = 紫
   - 冷静 / 专业 = teal / slate
   - 温暖 / 人文 = 琥珀 / coral
5. **校验对比度**，必要时加语义色（ok/warn/danger）。

---

## 四、4 套起手配色（锚点，非锁定）

**暗色科技**
```
--bg:#0d1117  --surface-1:#161b22  --surface-2:#1c2330
--text-1:#e6edf3  --text-2:#9da7b3  --border:#30363d
--accent:#58a6ff  --accent-2:#39c5cf
```

**简洁亮色**
```
--bg:#fafafa  --surface-1:#ffffff  --surface-2:#f5f5f5
--text-1:#1a1a1a  --text-2:#666666  --border:#e5e7eb
--accent:#2563eb
```

**暖调高端暗**
```
--bg:#15110d  --surface-1:#211a12  --text-1:#f5ede0
--text-2:#b8a890  --border:#3a2f22
--accent:#f0883e  --accent-2:#d29922
```

**冷静 slate**
```
--bg:#0f172a  --surface-1:#1e293b  --text-1:#f1f5f9
--text-2:#94a3b8  --border:#334155
--accent:#38bdf8  --accent-2:#a78bfa
```
