# 功能交付契约

编排层维护一张最小 Case 表，其他 Skill 只返回当前 gate 的结果。

## Case 表

| Case | 用户可观察结果 | Before/base | 独立验收 | E2E | 交互评审 | Video | After | PR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

每个 gate 只使用四种状态：

- `pass`：有新鲜证据通过；
- `fail`：已观察到不符合通过标准；
- `blocked`：缺环境、权限或证据，无法判断；
- `not-required`：当前 Case 不需要该 gate，并附一句理由。

## 委派返回契约

任何被替换或新增的能力 Skill 都返回：

```text
case: 对应 Case ID
status: pass | fail | blocked | not-required
evidence: 支持结论的文件、截图、日志或命令结果
artifacts: 测试、图片、视频或报告路径
delivery: sent | local-ready | blocked | not-required
risks: 残余风险和未覆盖项
next: 建议的唯一下一步
```

能力 Skill 不改变全局阶段、不代替其他 gate，也不自行创建 PR、等待 CI 或合并；这些转换由编排层决定。新增平台或测试框架时，只需提供同一返回契约，不必改写整条流程。

## Before / After

- 只为用户可见变化建立图片组；纯逻辑 Case 不凑图。
- 每个可见 Case 对应一组可定位的 Before / After。共享图片时在 Case 表说明。
- Before 可在开发前捕获，也可由记录的 base revision 和复现路径重放。
- 前后图使用相同 CSS 视口、DPR、缩放和状态；只补与当前问题相关的断点。
- 总览图可以补充上下文，不能替代多个 Case 的独立证据。

## 视频产物

视频至少返回：对应 Case、平台、绝对 MP4 路径、时长、分辨率、codec、完整解码结果和脱敏结果。

移动端可见变化必须有视频。PC/Web Case 只要 E2E 为 `pass`，就必须保留同 Case 截图和最终通过视频；纯静态 Case 可将 E2E 与视频记为有理由的 `not-required`。运行时有 Happy/Paws 媒体能力时必须实际发送截图和 MP4，本机路径不等于跨设备交付。发送失败不改变 E2E verdict，但 `delivery` 必须保持 `local-ready` 或 `blocked`，不能写成 `sent`。

## PR 边界

PR 编排层消费各 gate 已有证据，不要求 reviewer 或 E2E Skill 再检查 PR。

可见 UI PR 使用仓库模板，并保证：

```text
Visible UI cases = PR 中的可见 Case 行数 = Before/After 证据组数
```

创建 PR 的完成点是：提交已推送、PR 已创建、正文和图片已实际渲染、URL 已返回。CI、OTA、合并和分支清理属于后续动作，除非用户明确要求一起完成。
