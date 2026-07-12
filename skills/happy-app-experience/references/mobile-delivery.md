# Happy 移动交付经验

**最近验证：** 2026-07-12

**证据仓库：** https://github.com/wangjs-jacky/happy

**核验 revision：** `8cba242a8833867a0a60d3c12974184592b28552`

这些是从 Happy/Paws 当前仓库提炼的可迁移经验，不是所有 App 的通用强制规则。使用前先确认当前项目是否采用 Expo Updates、是否包含原生变化，以及交付渠道的真实要求。

## OTA 与重新构建是两条边界

**决策：** 只有 JS 兼容的改动适合通过 OTA。涉及原生依赖、新增或变更原生权限声明、Expo plugin、package ID、更新 URL 或 runtime version 的变化时，需要重新构建 App；不能用一次成功的 OTA 导出来证明原生包仍兼容。若权限已经在当前二进制声明，只有 JS 交互或文案变化，则仍按实际 native diff 判断，不因出现“权限”二字一概重建。

**适用边界：** 这条经验直接适用于 Happy 当前的 React Native/Expo 与自托管 OTA 结构。非 Expo 项目、不同更新协议或不同商店策略需要重新建立自己的兼容边界，不能照抄命令或 runtime 数字。

**Happy 证据：**

- [`docs/getting-started.zh-CN.md`](https://github.com/wangjs-jacky/happy/blob/8cba242a8833867a0a60d3c12974184592b28552/docs/getting-started.zh-CN.md)：明确区分 JS 兼容改动与需要重建的原生变化。
- [`packages/happy-app/app.config.js`](https://github.com/wangjs-jacky/happy/blob/8cba242a8833867a0a60d3c12974184592b28552/packages/happy-app/app.config.js)：variant、package ID、OTA channel、runtime version 和 update 配置在构建侧形成边界。
- [`packages/happy-app/eas.json`](https://github.com/wangjs-jacky/happy/blob/8cba242a8833867a0a60d3c12974184592b28552/packages/happy-app/eas.json)：development、preview、production 使用独立构建 profile 与 channel。

**迁移到其他 App：** 先检查更新运行时、原生依赖图、权限、plugin、包标识和更新端点；任一项跨过现有二进制兼容边界，就选择新包而不是 OTA。

## OTA 和真机是最终确认，不是基础 QA

**决策：** OTA 不替代 typecheck、自动化测试和结构化回归。手势、触感、系统权限等仍需要真机确认，但发布 preview OTA 前，Agent 应先完成能够在本地或 CI 证明的检查。

**适用边界：** 这条经验对移动 UI、手势、触感和平台行为尤其重要。纯逻辑改动也需要相称的静态检查与测试；真机只验证机器可观察不到的最后一层，不负责发现基础结构错误。

**Happy 证据：**

- [`docs/research/2026-07-04-right-swipe-panel-retrospective.md`](https://github.com/wangjs-jacky/happy/blob/8cba242a8833867a0a60d3c12974184592b28552/docs/research/2026-07-04-right-swipe-panel-retrospective.md)：复盘指出曾把 OTA 当作主要 QA，并要求在 preview OTA 前先完成结构化回归清单。
- [`docs/getting-started.zh-CN.md`](https://github.com/wangjs-jacky/happy/blob/8cba242a8833867a0a60d3c12974184592b28552/docs/getting-started.zh-CN.md)：记录 App 构建与 OTA 的不同交付边界。

**迁移到其他 App：** 根据技术栈替换具体命令，但保留顺序：静态检查和自动化回归 → 预览构建或 OTA → 真机最终确认 → 获得授权后正式发布。
