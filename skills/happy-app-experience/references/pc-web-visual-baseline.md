# Happy PC Web 视觉基线

> 最近验证：2026-08-07
>
> 已验证样例：Happy Web 命令面板，PR #293，合并提交 `7805ff8c075a95f7ae45442b065e54a8cd0de8b5`

## 适用边界

本基线用于在 Happy/Paws PC Web 中设计或调整命令面板、搜索选择器、复杂菜单等“输入 + 分组结果 + 快捷操作”浮层。它记录已经通过代码、前后截图和桌面运行态验证的比例关系与实现取舍。

这些数值不是全站所有 Dialog 的统一硬编码。其他组件先复用排版、主题和状态原则，再根据任务复杂度、内容长度与视口重新确定宽高；Happy 当前源码与本文件冲突时，以当前源码为准。

## 设计结论

1. 桌面高频浮层使用克制、紧凑但可读的层级，不沿用移动端的大字号和大行高。
2. 输入区是首要视觉入口，结果标题、辅助说明、分类标签和快捷键依次降级；层级同时依靠字号、行高、字重和颜色，不能只靠字号。
3. 命令面板位于视线中心偏上区域，让输入框和首屏结果优先进入扫描路径；使用相对视口位置，不绑定某一台显示器的固定像素。
4. 边框、分割线、背景、文字、强调色和阴影全部复用主题 token，保证明暗主题及主题包之间的一致性。
5. `hover / selected / pressed` 使用同一强调体系并保持克制；选中态可组合浅背景和细边框，但不让背景、描边与图标同时形成高饱和重块。

## 命令面板样例参数

### 容器与位置

| 项目 | 已验证值 | 目的 |
|---|---:|---|
| 面板最大宽度 | `720px` | 在宽屏上保留完整命令信息，同时避免像普通页面一样横向铺开 |
| 外层水平安全边距 | `16px` | 小视口仍不贴边 |
| Web 顶部位置 | `18vh` | 保持视线中心偏上，并随视口高度变化 |
| 面板最大高度 | `64vh` | 防止整体超出视口 |
| 结果区最大高度 | `48vh` | 输入区固定可见，结果区独立滚动 |
| 面板圆角 | `14px` | 与 Happy PC 端中型浮层圆角保持一致 |
| 面板边框 | `hairlineWidth` + `theme.colors.divider` | 提供克制边界并适配主题 |
| Web 阴影 | `0 12px 32px theme.colors.shadow.color` | 建立浮层层级，不使用脱离主题的固定黑色 |
| 遮罩 | `rgba(0, 0, 0, 0.42)` | 聚焦浮层，同时保留背景上下文 |

### 字体层级

| 内容 | 字体 | 行高与辅助参数 |
|---|---:|---|
| 搜索输入 | `16px` | `22px` 行高，默认字体，`-0.15px` 字间距 |
| 结果主标题 | `14px` | `19px` 行高，semibold，`-0.1px` 字间距 |
| 结果辅助说明 | `12px` | `16px` 行高，次级文字色 |
| Metadata | `11px` | 默认字体，次级文字色，`-0.1px` 字间距 |
| 分类标题 | `11px` | semibold、uppercase、`0.3px` 字间距 |
| 快捷键 | `10px` | `14px` 行高，mono，`500` 字重 |
| 空结果提示 | `13px` | 默认字体，次级文字色 |

### 列表密度与状态

| 项目 | 已验证值或规则 |
|---|---|
| 单行最小高度 | `48px` |
| 行内边距 | 水平 `12px`、垂直 `8px` |
| 行外边距 | 水平 `8px`、垂直 `1px` |
| 行圆角 | `10px` |
| 图标容器 | `30 × 30px`，圆角 `8px`，图标 `18px` |
| 标题与图标间距 | `10px` |
| 快捷键胶囊 | 水平 `7px`、垂直 `3px`，圆角 `6px`，hairline 分割色边框 |
| Selected | `accent` 约 `8%` 背景 + `22%` 边框；图标容器约 `10%` 背景 |
| Hover | `theme.colors.surfaceHigh` |
| Pressed | `accent` 约 `12%` 背景 |
| 搜索命中 | `accent` 文字色 + `600` 字重 |

## 实现约束

- 颜色优先使用 `surface`、`surfaceHigh`、`text`、`textSecondary`、`divider`、`accent` 和 `shadow` 等主题语义，不直接复制某个亮色主题下的十六进制颜色。
- React Native Unistyles 组件使用主题函数模式集中声明颜色与排版；交互状态使用 variants 表达，避免在 JSX 中叠加多组临时内联样式。
- Web 主题颜色可能是 CSS variable。需要透明度时，CSS variable 使用 `color-mix(...)`，普通颜色再使用颜色透明度工具，避免主题切换后生成无效颜色。
- 新浮层先与当前 Header、侧栏、输入区和既有 Dialog 对照，再决定是否复用本样例数值；优先保持相对层级和 token 一致，不机械复制 `720px` 或 `48px`。

## 开发与评审顺序

1. 截取当前页面基线，登记主标签、辅助文字、常用间距、圆角、分割线和阴影来源。
2. 先确定输入、标题、说明、分类、快捷键的相对层级，再调整容器宽高与行密度。
3. 分别检查 rest、hover、selected、pressed 和搜索命中状态；确认强调色没有重复叠加。
4. 在低高度笔记本和标准桌面视口检查顶部位置、内部滚动和安全边距。
5. 使用相同 CSS 视口、DPR、缩放与裁切对比前后画面，避免截图条件变化掩盖真实差异。

## 当前证据入口

在 Happy 仓库中复核以下相对路径：

- `packages/happy-app/sources/components/CommandPalette/CommandPalette.tsx`
- `packages/happy-app/sources/components/CommandPalette/CommandPaletteInput.tsx`
- `packages/happy-app/sources/components/CommandPalette/CommandPaletteItem.tsx`
- `packages/happy-app/sources/components/CommandPalette/CommandPaletteModal.tsx`
- `packages/happy-app/sources/components/CommandPalette/CommandPaletteResults.tsx`
- `packages/happy-app/e2e/web-compose-home.spec.ts`
- `docs/visual-evidence/command-palette/before.png`
- `docs/visual-evidence/command-palette/after.png`

主题 token、排版常量、Unistyles API 或命令面板结构发生变化时，重新核验本基线并更新“最近验证”日期。
