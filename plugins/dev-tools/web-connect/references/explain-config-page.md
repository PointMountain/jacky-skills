# 配置页讲解 — 核心产出形态：HTML 重建页 + 逐行讲解 + 交互折叠

> 这是 web-connect 的旗舰产出，经真实验收确定（Tailscale DNS 页实测）。
> **被否决的旧形态**：① 纯截图当底图旁边贴气泡批注（糊、对不齐）；② 另起炉灶重排的卡片面板（脱离原页）。
> **正确形态**：读取页面真实内容 → 用 HTML/CSS 把原页 **1:1 重画**出来（左栏）→ 右栏**逐行对齐**讲解，默认折叠、点击展开。

---

## 一、为什么是这个形态

| 维度 | 截图批注（已弃） | HTML 重建（采用） |
|------|------------------|-------------------|
| 清晰度 | 截图糊、retina 缩放失真 | 矢量文字，锐利 |
| 对齐 | 靠坐标 hack，易歪 | grid 同行，天然精确 |
| 交互 | 死图 | 可折叠/展开/hover |
| 还原 | 像但死 | 重画原 UI，深色还原 |

关键：**左右两栏用 `grid-template-columns` 同一行**，左 cell 重建配置项、右 cell 放讲解，对齐由布局保证，不需要算任何坐标。

---

## 二、工作流（6 步）

1. **读内容**：截图（看视觉）+ `/eval` 提取每个区块的标题、描述、字段值、按钮文字、开关状态、🔒锁定标记。
2. **识别状态**：按钮写 "Disable X" → X 当前**已启用**；带 🔒/灰显 → **套餐锁定的付费功能**（必须标出，别教用户点用不了的）。
3. **重建左栏**：用 HTML/CSS 把每个区块的 UI 画出来（标题、描述+Learn more、输入框、按钮、开关、锁图标、彩色标签）。深色还原。
4. **写右栏讲解**：每个区块对齐一段三段式讲解（见第四节）。
5. **加折叠交互**：右栏讲解默认折叠（只显示「讲解·一句话摘要 ▸」），点击展开完整内容；概览常显。
6. **落盘 + 打开**：存到**用户能找到的持久位置**（`~/Desktop/web-connect-<topic>/` 或用 `/ob-to-claudian` 进 Obsidian），`open` 打开。**不要**留在 job 临时目录。

---

## 三、HTML 骨架（可直接套用）

```html
<style>
  .row{display:grid;grid-template-columns:1.05fr 1fr;border-top:1px solid #3a3a40}
  .L{padding:22px 26px}                         /* 左：重建的原页 UI */
  .R{padding:22px 26px;border-left:1px solid #3a3a40;background:#0d0d0f} /* 右：讲解 */
  .note{display:none}                           /* 默认折叠 */
  .R.open .note{display:block}                  /* 展开 */
  .note-h{cursor:pointer;display:flex;align-items:center;gap:6px;color:#ff5468} /* 点击头 */
  .caret{margin-left:auto;transition:transform .2s} .R.open .caret{transform:rotate(90deg);color:#00ff88}
  /* 重建控件：.field 输入框 / .btn 按钮 / .sw 开关 / .magicdns 彩标 / .lockicon 🔒 */
</style>
<div class="row">
  <div class="L">… 重画的配置项 UI（标题/描述/输入框/按钮/开关/🔒）…</div>
  <div class="R"><div class="note-h">讲解 · 一句话摘要</div>
    <div class="note">… 三段式 …</div></div>
</div>
<script>
document.querySelectorAll('.row .R').forEach(function(r){
  var h=r.querySelector('.note-h'); if(!h) return;
  h.insertAdjacentHTML('beforeend','<i class="caret">▸</i>');
  h.addEventListener('click',function(){r.classList.toggle('open')});
});
</script>
```

配色用 Terminal Noir（深黑 + 霓虹绿/琥珀/红点缀）。状态徽章：已启用=绿、核心=琥珀、Free锁定=琥珀🔒、普通=红。

---

## 四、讲解三段式（每个配置项）

| 段 | 讲什么 |
|----|--------|
| **是什么** | 大白话，术语第一次出现给一句解释 |
| **改了影响** | 打开/关闭/填不同值的实际后果，对谁生效 |
| **建议** | 默认值、大多数人怎么设、什么情况才改、改错风险 |

补充：关联项点出依赖（A 只在 B 开时有意义）；从结构读到的当前值告诉用户"你现在是 X，默认是 Y"；不确定就明说，不编。

---

## 五、降级：简单页用纯文字

页面就几个选项、没必要重建时，直接终端「概览 + 逐项三段式」Markdown 输出即可，不生成 HTML。判断权交给 LLM（YOLO），复杂密集配置页才上 HTML 重建。

---

## 六、整页截图（重建时对照视觉用）

web-access `/screenshot` 是**视口截图**，长页截不全。用 `scripts/fullpage-shot.py` 分段滚动 + 按 `devicePixelRatio` 精确裁剪拼接成整页长图（详见该脚本）。重建 UI 时对照整页图，确保不漏区块。
