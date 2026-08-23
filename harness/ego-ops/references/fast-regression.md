# 快速回归录像

在已验证 operation 的重复执行中使用本流程。目标是在同一个浏览器任务空间内同时完成操作、验证和连续录像，避免逐张截图与二次复演。

## 浏览器阶段

使用单次 `ego-browser nodejs` 调用：

1. 记录 `workflowStartedAt = Date.now()` 和各阶段耗时。
2. 进入已验证入口，只做一次登录态与关键入口复核。
3. 调用 `Page.startScreencast`，JPEG 质量使用 60–70，尺寸限制到回归审阅所需分辨率。
4. 每次点击、导航或小步滚动后调用 `drainEvents()`；保存 `Page.screencastFrame` 的 `params.data`，并立即用其 `sessionId` 调用 `Page.screencastFrameAck`。
5. 每约 120 毫秒排空一次事件。亚秒等待使用 `await new Promise(resolve => setTimeout(resolve, 120))`，避免混淆浏览器 `wait()` 的秒单位。
6. 达到成功标准后立即停止继续滚动或采集，调用 `Page.stopScreencast`，写出结果 JSON 与阶段耗时 JSON。

核心帧流结构：

```javascript
await cdp("Page.startScreencast", {
  format: "jpeg",
  quality: 65,
  maxWidth: 1454,
  maxHeight: 726,
  everyNthFrame: 1,
});

let frameNumber = 0;
async function drainFrames() {
  const events = await drainEvents();
  for (const event of events) {
    if (event.method !== "Page.screencastFrame") continue;
    frameNumber += 1;
    const name = `frame-${String(frameNumber).padStart(6, "0")}.jpg`;
    writeFileSync(join(frameDirectory, name), event.params.data, "base64");
    await cdp("Page.screencastFrameAck", {
      sessionId: event.params.sessionId,
    });
  }
}
```

动作之间调用 `drainFrames()`；连续滚动时把滚动拆成小步，在每一步后排空帧并用 120 毫秒定时器让页面更新。不要只在所有动作结束后才确认帧，否则 CDP 会因未确认帧而降低采集速率。

阶段耗时文件使用以下最小结构：

```json
{
  "stages": {
    "openEntry": 5004,
    "navigate": 7138,
    "extractAndVerify": 2152
  },
  "totalMs": 14294
}
```

字段名可按 operation 调整；所有值均为非负毫秒数。不得把用户名、认证数据、Cookie 或完整业务响应写入该文件。

## 编码阶段

浏览器阶段结束后只执行一次：

```bash
node "${CLAUDE_SKILL_DIR}/scripts/render-regression-video.mjs" \
  --frames "$FRAME_DIRECTORY" \
  --stage-timings "$TIMINGS_JSON" \
  --output "$OUTPUT_MP4" \
  --budget-ms 60000
```

帧文件必须从 `frame-000001.jpg` 或 `frame-000001.png` 开始连续编号，且扩展名一致。脚本会在临时文件中编码，成功且仍在预算内才原子替换目标文件。

## 性能验收

结构化输出中的 `budget.withinBudget` 必须为 `true`，且 `timings.workflowTotalMs <= budget.limitMs`。功能正确但超过预算时，不得宣称快速回归成功；保留阶段耗时并定位最慢阶段。

已验证参考量级：65 帧的浏览器阶段约 14.3 秒，`veryfast` 编码约 0.9 秒。该数字仅用于发现明显退化，不是跨设备的固定保证。
