---
name: happy-visual-workflow
description: "Happy/Paws PC Web 视觉评审、自动修复、逐项截图、PR 验收与合并的完整交付编排。用户在 Happy 项目中只说‘视觉稿’、‘跑视觉稿流程’、‘再走一遍视觉稿’，或要求重复 PC 视觉走查闭环时使用；也用于把截图或当前页面从问题发现一路交付到 main。"
---

# Happy 视觉稿闭环

把“视觉稿”当作执行口令，不当作只输出建议的讨论请求。围绕当前 Happy/Paws 项目完成“基线走查 → 独立复核 → 修复 → 逐 Case 前后截图 → PR → 独立验收 → CI → 合并”的完整闭环。

## 触发契约

- 用户只说“视觉稿”时，直接执行完整流程；不要先把步骤复述给用户后停下。
- 用户附带截图、URL、页面名或问题范围时，以该输入为主；附件必须使用用户本轮明确给出的路径，不从附件目录猜测。
- 用户没有指定页面时，以当前 Happy `main` 的核心 PC 工作区和代表性动态状态为默认范围。只有同时存在多个项目或完全不同的候选目标时才问一个最小澄清问题。
- 该口令授权在隔离 worktree 中改代码、跑静态检查与测试、生成截图、提交分支、创建/更新 PR、等待 CI，并在全部门禁通过后合并与清理。
- 该口令同时构成启动任务 worktree 内 Happy Web 或 Playwright Harness 本地评审服务的明确确认；没有现成页面时可直接运行仓库的 `pnpm web`、`pnpm test:e2e:web` 及其传递启动的 `expo start --web`、Metro、Happy 本地测试 server。完成或中断后关闭全部子进程。本授权不包含移动端 Expo/Metro、Expo Go、iOS/Android 构建或模拟器、Tauri dev、生产服务或 daemon。
- 该口令不授权生产部署、手动发布 production OTA、重启 Happy daemon、删除业务数据或改变外部账号状态。仓库 PR 自动触发的 preview 检查可以等待并如实报告。
- 保留普通 UI 的真实画面；除非当前请求要求，不主动打码。始终禁止把 Cookie、Token、请求头、密钥或凭据写入截图、报告和 PR。

## 开始前

1. 读取目标仓库的 `AGENTS.md`、`CLAUDE.md` 和目标目录内更具体的指令。
2. 确认 Happy 根工作区处于 clean `main` 且与 `origin/main` 对齐；所有修改进入 sibling worktree。
3. 创建可见计划，任一时刻只保留一个进行中步骤；持续工作时至少每 60 秒发一次简短进展。
4. 加载 `pc-web-interaction-reviewer`。操作真实页面时加载 `dev-tools:browser-control`；自动化需要时加载 `web-e2e`。浏览器 provider 不可用时可使用项目 Playwright Harness，但必须明确披露，不能冒充 Browser Control 成功。
5. 读取 [delivery-contract.md](references/delivery-contract.md)，并从一开始建立 Case 与截图账本，不能在合并前临时补证据。
6. 优先复用已运行的安全本地页面；不可用时直接启动仓库规定的 Happy Web 或 Playwright Harness 服务，不为这一项再次询问用户。

## 阶段一：冻结修复前基线

1. 在改代码前捕获真实页面基线。至少覆盖 `1280×720`、`1440×900`、`1920×1080`，并补充与当前问题相关的断点。
2. 进入代表性的活跃、已填充或详情状态；只看到空壳或空状态时不得声称完成全站走查。
3. 先用 `pc-web-interaction-reviewer` 的截图评审或全站交互模式做盲测，冻结第一版问题清单后再读取历史反馈补漏。
4. 为每项问题分配稳定 Case ID，记录复现路径、实际结果、影响、严重度、验收标准、修复前截图和相关边界。
5. 启动一个没有生产者结论的新 Subagent，给它原始截图、URL 或构建做独立发现。合并双方有证据的问题，不按数量凑问题。

## 阶段二：处理评审能力缺口

只有用户反馈暴露了可跨产品复用的漏评规则时，才更新 `pc-web-interaction-reviewer`：

1. 在 Skill 仓库的独立 worktree 中更新反馈案例、规则与完成门。
2. 用 `skill-creator` 校验结构，并启动全新 Subagent 做无答案泄漏的前向测试。
3. Skill PR 通过仓库校验和 CI 后再合并；产品特例写本地经验，不污染共享规则。
4. 用更新后的 Skill 对产品做第二轮走查，确认它能主动发现原漏项。

如果没有可泛化缺口，跳过本阶段，避免每轮无意义改 Skill。

## 阶段三：实现全部确认问题

1. 从最新 `origin/main` 创建一个产品 worktree，保留根工作区 clean。
2. 把相互独立、边界明确的代码任务委派给 Subagent；主 Agent 负责范围、冲突、集成与最终结果。生产者不得担任最终验收者。
3. 一次处理冻结范围内的全部确认问题，不能修完第一项就宣称结束。范围变化必须写入 Case 账本。
4. 遵循现有设计 token、响应式结构和可访问语义；修复语义后仍要检查图标轮廓、层级、间距和真实页面集成。
5. 运行与风险相称的单测、typecheck、E2E 和 `git diff --check`；不擅自启动生产服务、daemon 或真机发布。

## 阶段四：生成逐 Case 视觉证据

1. 每个可见 UI Case 生成一组独立的 Before / After 证据；总览图和 contact sheet 只作补充，不进入 Case 计数。
2. 前后图保持相同 CSS 视口、DPR、浏览器缩放和裁切比例。状态型交互按需要增加展开、激活、收起或恢复帧。
3. 在真实页面验证共享 Header、多栏区域、浮层锚点和响应式边界；孤立 fixture 不能证明页面不拥挤或空间已回收。
4. 保存独立前图、后图和清楚标注的前后拼接图，并写入仓库内的评审报告。
5. 交付前核对 `Visible UI cases = 独立截图组数`。缺任意一组时保持视觉证据不完整。

## 阶段五：独立回归循环

1. 启动新的验收 Subagent，使用 `pc-web-interaction-reviewer` 回归模式读取 Case 表、真实页面和截图；不给它生产者自评作为结论。
2. 要求逐 Case 返回“已修复 / 仍失败 / 证据不足 / 阻断”，并检查常用视口、相关断点和路径内回归。
3. 任一 Case 未通过时回到实现阶段，重新生成受影响证据并再次独立验收。
4. 只有全部 Case 通过，且验收输出采用的任一严重度口径（`P0–P3` 或 `Critical / Important / Minor`）未解决项均为 0，才进入 PR 合并阶段；不要把两套标签重复计数。

## 阶段六：PR 证据门与合并

1. 提交最终代码和证据，推送功能分支并创建 PR。
2. PR 正文声明 `Visible UI cases: N`，为每个 Case 直接嵌入唯一的前后截图组。使用最终 head commit SHA 或 GitHub 上传附件，不使用删除分支后失效的分支 URL。
3. 打开实际 PR，核对 Case 数、证据小节数、独立截图组数相等，并验证每张图片可以渲染。聊天图片、本地报告或仓库路径不能代替 PR 内证据。
4. 让独立验收 Subagent 检查实际 PR 正文、截图和 CI；测试或 OTA 通过不能覆盖视觉证据缺口。
5. 等待全部必需检查通过后合并。合并后确认 merge commit，快进 Happy 根工作区到 `origin/main`，删除已合并任务 worktree 与本地分支。
6. 如果同时修改了 Skill，独立完成 Skill PR 的 CI、合并和安全清理；不得覆盖 Skill 根工作区内其他用户改动。

## 最终交付

- 先报告是否已合并到 `main`，再列问题数、通过数、测试、PR 与 merge commit。
- 通过 Happy 客户端展示图片时调用 `mcp__happy__send_image`；不能只打印本地路径或 Markdown 图片。
- PR 自动发布 preview OTA 时，从真实工作流结果提取元数据并输出 `<happy-ota-preview>`；未做真机验证就明确写未验证。
- 保持最终回复简洁，但必须说明 Browser Control 与 Playwright 的真实执行边界。

## 完成门

- [ ] 修复前基线在改代码前冻结，核心动态状态和相关断点已覆盖。
- [ ] 独立发现 Agent 与生产者分离；最终验收 Agent 未依赖生产者自评。
- [ ] 冻结范围内所有问题均有 Case、实现、测试和逐项结论。
- [ ] `Visible UI cases = 独立 Before/After 组数 = PR 内证据组数`。
- [ ] 前后证据同尺度并来自真实页面；PR 图片使用稳定 URL 且实际可渲染。
- [ ] 回归结果全部通过，CI 全绿，才执行合并。
- [ ] Happy Web、Playwright Harness、Metro 与本地测试 server 已停止；临时端口、PID、Harness environment、测试数据和运行产物已清理，失败或中断路径也执行同一收尾。
- [ ] Happy 根工作区最终 clean `main = origin/main`；其他仓库的用户改动没有被覆盖。
