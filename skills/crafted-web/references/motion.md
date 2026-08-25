# 动效法则（精美动画核心）

> 在加动效前读本文。每个动效都要有目的——引导注意、表达关系/因果、或给操作反馈。纯装饰删掉。

## 目录

- 一、目的性
- 二、缓动曲线
- 三、时长阶梯 + 错峰编排
- 四、动效类型清单
- 五、性能
- 六、克制与可访问

---

## 一、目的性

每个动效要么**引导注意**、要么**表达关系/因果**、要么**给操作反馈**。三者都不沾的纯装饰，删掉。

## 二、缓动曲线（精致感关键，禁默认 linear，循环除外）

```css
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1);     /* 进场：快进慢出，干脆又柔和（首选） */
--ease-inout:  cubic-bezier(0.65, 0, 0.35, 1);    /* 状态间移动 */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* 轻微回弹的 pop（按钮/徽标） */
```

## 三、时长阶梯 + 错峰编排（stagger）

- 微交互 **120~200ms**；标准（卡片/面板/状态切换）**250~400ms**；大块（区块/Hero）**500~800ms**；持续循环 **1~4s**（用 linear / ease-in-out）。
- 兄弟元素**依次出现**，延迟错开 **40~80ms**（`animation-delay` 按索引递增）。

## 四、动效类型清单（按需取用）

- **进场揭示**：`opacity 0→1` + `translateY(8~24px)`（可加 `scale(.96→1)`）。
- **滚动触发**：IntersectionObserver 给进入视口的元素加 `.in` 触发，**默认只一次**。
- **状态切换**：在 `transform`/`opacity` 间过渡。
- **持续循环**：呼吸、浮动、渐变位移、虚线流动（`stroke-dashoffset`）、沿路径跑的光点。
- **视差**：随滚动小幅 `translateY`（系数 ≤ 0.3，宁弱勿过）。
- **SVG 路径跟随**：`<animateMotion>` 或 WAAPI。
- **数字滚动**：`requestAnimationFrame` 插值 + 缓动。
- **Hover 微交互**：卡片 `translateY(-2px)` + 提亮/发光，图标轻微放大。
- **文字进场**：标题按词/行错峰 fade-up；可选渐变文字。

## 五、性能

- **只动 `transform` 和 `opacity`**（GPU，60fps）。
- 避免动 `width`/`height`/`top`/`left`/`box-shadow`/`filter`；需要动阴影就**动伪元素的 `opacity`**。
- `will-change` 仅用在高频元素。

## 六、克制与可访问

- 同屏别太多东西同时动；首屏一个主焦点。
- **务必加** reduced-motion 兜底：

```css
@media (prefers-reduced-motion: reduce){
  *{ animation:none!important; transition:none!important; scroll-behavior:auto!important }
}
```
