# 视觉稿交付契约

在阶段一建立本页的 Case 账本，在阶段四至六持续更新。不要等到 PR 创建后再反推截图数量。

## Case 账本

| Case ID | 页面/状态 | 修复前问题 | 严重度 | 复现步骤 | 验收标准 | Before | After | 结果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

计数规则：

- `Visible UI cases` 只统计用户能直接观察到变化的 Case。
- 每个可见 Case 必须有唯一的前后截图组。多个技术断言属于同一视觉变化时可共享一组，但要在表中说明。
- 一张原始整页截图可以被多个 Case 裁切使用；每个 Case 仍需自己的裁切或标注结果。
- 总览图、contact sheet、自动化日志和测试结果不计入截图组数。

## 文件命名

```text
<batch>-<case-id>-<slug>-before-<viewport>.png
<batch>-<case-id>-<slug>-after-<viewport>.png
<batch>-<case-id>-<slug>-before-after.png
```

在报告中记录 CSS 视口、DPR、缩放、页面状态和截图来源。对响应式问题增加对应断点文件，不用不同比例画面冒充前后对比。

## PR 正文模板

```markdown
## Summary

- 修复范围与用户影响

## Visual evidence

Visible UI cases: 2

### PC-001 — 问题名称

![PC-001 before and after](https://raw.githubusercontent.com/<owner>/<repo>/<40-char-head-sha>/<path>/pc-001-before-after.png)

### PC-002 — 问题名称

![PC-002 before and after](https://raw.githubusercontent.com/<owner>/<repo>/<40-char-head-sha>/<path>/pc-002-before-after.png)

## Validation

- 单测 / typecheck / E2E
- 独立 PC 回归：通过项与未解决项
- Browser Control 或 Playwright 的真实执行说明
```

## 合并前核对

1. PR 声明的 Case 数与 Case 账本一致。
2. 每个可见 Case 都有独立小节和可渲染图片。
3. 图片 URL 使用不可变 commit SHA 或 GitHub 上传附件。
4. 独立验收者检查实际 PR，而非仅检查本地 Markdown。
5. 图片缺失、链接失效、Case 错配或 CI 失败时不合并。
