# Happy App Experience 索引

本文件只负责渐进导航，不复制经验正文。先判断当前问题是否命中，再读取一个目标文件。

| 主题 | 什么时候读取 | 文件 | 最近验证 |
|---|---|---|---|
| 移动交付边界 | 判断 OTA、重新构建、真机确认、安装包或 Release 的关系 | [mobile-delivery.md](mobile-delivery.md) | 2026-07-12 |
| 独立 App 建立与发布 | 从 0 到 1 建独立 App：工程边界、preview/production 语义、runtimeVersion 命名、复用自托管 OTA、release-doctor 与验证 gate；**打 sideload APK / arm64-only 构建 / 发 GitHub Release / preview OTA 版本切换悬浮球** 也在此 | [app-build-and-release.md](app-build-and-release.md) | 2026-07-12 |
| 视觉资产前置 | 何时/如何前置生成 icon/splash/插画等资产（走 gpt-image-2 委托 Codex 出图） | [asset-pipeline.md](asset-pipeline.md) | 2026-07-12 |
| PC Web 视觉基线 | 延续 Happy 桌面浮层的字体层级、信息密度、位置、圆角、边框、阴影、主题 token 和交互状态；命令面板、搜索选择器或复杂菜单优先读取 | [pc-web-visual-baseline.md](pc-web-visual-baseline.md) | 见正文 |

> 本机私有事实（具体桶名、FC 端点、凭据变量名、Obsidian 路径、先例项目）在被忽略的 `local/experience.local.md`。

找不到匹配主题时直接返回当前任务，不扫描目录，也不创建空分类。
