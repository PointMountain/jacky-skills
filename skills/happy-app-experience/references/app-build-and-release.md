# 独立 App 从 0 到 1 的建立与发布经验

**最近验证：** 2026-07-12

**证据仓库：** https://github.com/wangjs-jacky/happy （以当前源码为准）

这些是从 Happy/Paws 自托管实践提炼的可迁移经验，**不是所有 App 的通用强制规则**，也不
强制 Expo 或任何技术栈。本机具体的桶名、FC 端点、凭据变量名、路径等私有事实见被忽略的
`local/experience.local.md`，不在本文件展开。

## 独立工程边界优先于堆功能

**决策：** 从 0 到 1 时先立**工程与产品边界**，再写代码：独立仓库（不做主仓库里的临时
demo）、先出 spec/用户旅程/信息架构/状态机/点击矩阵、禁止假入口、第一屏必须是可用产品而
非说明页。初始工程要自带 README、脚本、typecheck、基础可验证测试、权限最小化、gitignore、
资产目录与文档目录，并建立 `AGENTS.md`/`CLAUDE.md` 写清命令、架构、发布流程与索引。

**适用边界：** 「先边界后功能」跨技术栈普适；具体技术栈（Expo/RN/Expo Router/TS/Expo
Updates 是常用候选）按项目现场决定，不照搬。内容型/生活方式 App 要沉浸留白，不要用卡片堆
功能冒充产品。

**迁移到其他 App：** 保留顺序——产品定义与点击矩阵 → 独立工程骨架 → 可用首屏 → 主流程闭环
（输入/选择 → 状态变化 → 持久化/反馈 → 结果可见），不要一上来就铺功能。

## preview / production 双语义 + runtimeVersion 独立命名

**决策：** 至少区分 preview 与 production 两种构建语义，二者的 package/channel/name 清晰
分开。**每个 App 用独立命名的 runtimeVersion**，避免污染主 App 的 OTA 通道。只改 JS/资产
可走 OTA；新增原生依赖、权限、plugin、package、签名或 runtimeVersion 变化必须重新打 APK——
一次成功的 OTA 导出不能证明原生包仍兼容。

**适用边界：** 直接适用于 Expo Updates + 自托管 OTA 结构。非 Expo、其他更新协议或商店策略要
重建自己的兼容边界，不照抄 runtime 数字或命令。

**迁移到其他 App：** runtimeVersion 与装机 APK 必须完全一致，否则该机器永远跳过更新；各
runtime 是互不相通的独立通道。

## 复用自托管 OTA 基建，但按 platform/runtime/channel 隔离

**决策：** 新 App 默认**复用已有自托管 OTA 基建**（FC 服务 + OSS 桶），不新建付费资源，
但路径必须按 `manifests/<platform>/<runtime>/<channel>/latest.json` 隔离，避免不同 App /
不同环境互相覆盖。FC 服务端按请求头动态取路径，改 runtime/channel 映射要重新构建装机才生效。

**适用边界（易踩）：**
- **preview 频道的 `latest.json` 被所有 PR 共享**、谁最后发谁覆盖；想在真机看某个具体 PR，
  必须用定向锁版本（版本站扫码 / App 内 OTA Versions 选 stamp），不能只跟 latest。
- **production OTA 常不在 PR checks 里**：若由「push 到 main（合并）」触发，它是合并后独立的
  workflow run，去 Actions 页看，不是 PR 页面。
- 改 FC 服务端代码需要单独部署并 live probe；发布 OTA 只上传 manifest/bundle，不会自动部署 FC。

**迁移到其他 App：** 先确认更新运行时、原生依赖、权限、包标识、更新端点；任一项跨过现有二进制
兼容边界，就选新包而不是 OTA。具体桶/FC/频道映射见 `local/`。

## 发布前 release-doctor 与验证 gate

**决策：** 正式发布前先跑一遍准备度自检，再按顺序验证，不跳步：
- **release-doctor**：git 状态/分支/远端/tag/repo；工具链（Node/pnpm、Expo、JDK 17、Android
  SDK/Gradle）；签名 keystore 存在且不入库、后续升级用同一个；APP_ENV/package/channel/
  runtimeVersion/更新端点/权限列表；发布凭据（OSS/FC CLI 与 CI Secrets）具备发布能力。
- **验证顺序**：本地静态检查/测试（typecheck、单测、`git diff --check`）→ preview 构建或 OTA
  → 真机最终确认 → **取得授权后**才正式发布。APK 验证用 apksigner verify / aapt dump
  badging/permissions / SHA256 / 下载 asset HEAD 200；OTA 验证 GET latest manifest 核对
  channel/runtime/updateId/launchAsset 且 HEAD 200。

**适用边界：** 真机只验证机器观察不到的最后一层（手势、触感、系统权限），不替代静态检查与
自动化回归。APK 是构建产物，不 commit 进仓库；签名密钥、AccessKey 只放本机环境或 CI Secrets。

**迁移到其他 App：** 按技术栈替换具体命令，但保留「静态检查 → 预览 → 真机 → 授权后正式」这个
不可颠倒的 gate 顺序。外部副作用（push、Release、production OTA、部署）每次都要重新确认授权。
