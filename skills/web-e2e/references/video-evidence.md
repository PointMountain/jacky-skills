# Web E2E 视频证据

只负责把已经通过的 Web E2E Case 录成可复核 MP4。原生移动端录屏、文件发送、手机确认和 PR 编排由调用方负责。

## 1. 对应同一个 Case

开始实现前建立最小 Case 表：

| Requirement / Case | 用户可观察结果 | E2E Spec | 视频片段或时间码 |
| --- | --- | --- | --- |

每个用户可观察结果对应一个可执行 Case。已有 Case 优先复用；没有时补最小 Case。提前声明环境、登录方式、真实数据副作用、清理方式，以及录屏中禁止出现的账号或设备信息。

## 2. 先自动通过，再录制人工版

1. 用普通模式运行目标 E2E，修到稳定通过。
2. 再开启录像模式复跑同一 Case；不要把失败中断的视频包装成验收视频。
3. 人工版需保留操作节奏：关键状态通常停留 0.7–1.2 秒。快捷键、持久化和不可见断言若单看画面无法理解，增加简短画面标注或在视频报告写明时间码。
4. 登录、密钥输入和敏感页面默认不录；必须登录时，登录完成后再开始保存录像。交付前抽帧检查账号、Session、设备、内部 URL 和通知内容。

## 3. 生成通用 MP4

最低交付规格：

- MP4 容器，H.264，`yuv420p`，`faststart`；
- 1280×720 或更高，25/30 fps；
- 默认静音，只有声音本身属于验收目标时才保留；
- 文件名稳定且能识别 Case，不用随机 Playwright 目录名作为最终入口。

Playwright 原始 WebM 可用以下等价参数转码：

```bash
ffmpeg -y -i video.webm \
  -c:v libx264 -crf 20 -pix_fmt yuv420p -movflags +faststart -an \
  e2e-acceptance.mp4
```

交付前必须完成三层验证：

1. `ffprobe`：codec、pixel format、宽高、帧率、时长和文件大小符合预期；
2. 完整解码：`ffmpeg -v error -i e2e-acceptance.mp4 -f null -` 退出码为 0；
3. 视觉核对：覆盖全时长抽帧或完整观看，确认首尾不是空白、每个 Case 真正出现、关键文字可辨认。

## 4. 返回产物

把最终 MP4 从 Playwright 临时目录复制到稳定的任务产物目录，不直接交付可能被清理的 `test-results/` 文件。向调用方返回：

```text
case: E2E Case ID
status: pass | fail | blocked
path: 稳定 MP4 绝对路径
media: codec、pixel format、宽高、帧率、时长、大小
validation: 完整解码与视觉核对结果
side_effects: 环境、数据副作用与清理结果
```

在终端输出绝对路径。运行时存在文件发送能力时，调用方可以再发送同一文件；没有发送能力时保持 `local-ready`，不要把本地路径描述成手机已收到或 PR 已挂载。

## 5. 完成门

- [ ] 普通 E2E 与录像复跑均通过，环境和副作用已说明并清理。
- [ ] Case、Spec、视频片段可追溯。
- [ ] MP4 通过媒体信息、完整解码、视觉覆盖和脱敏检查。
- [ ] 稳定绝对路径已输出给调用方。
- [ ] 未把视频当作交互评审、Before / After 或 PR 交付的替代品。
