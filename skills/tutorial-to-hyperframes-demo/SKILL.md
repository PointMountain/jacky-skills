---
name: tutorial-to-hyperframes-demo
description: 自主学习本地教学音视频或公开视频链接，把教程讲授的方法、可观察动效和屏幕代码转成有证据、可恢复、可渲染的 HyperFrames Demo。用于从教程复刻方法、在 ai-clip-lab 增加独立 Demo、用本地素材替换示例、连续观看并修正成片，或执行无人值守的批量视频学习任务。
---

# Tutorial to HyperFrames Demo

把自己当作会看、会验证、会复盘的学习者。忠实复现教程教授的因果机制与时间关系，不追求逐像素复制，也不要把“看起来像”当成学会。

本工作流固定为两轮独立评审、一次定向修正：R1 只选一个 `top_fix`，实现者只改该维度，R2 复评后硬停止。这里的“两轮”不是两次修正。

## Phase 0：载入本机经验

1. 若存在 `experience.local.md`，先完整读取。
2. 若存在 `runtime.local.json`，把它只当作可能过期的提示；仍在本轮探测真实能力。
3. 不提交这两个文件。把本机路径、代理、照片根、工具安装状态和临时绕行只写在这里。

## 选择执行模式

- 用户明确授权无人值守或批量执行时，进入自动模式：持续选择范围内最安全、可逆的下一步，不为风格小选择停下；只有来源未授权、目标范围会实质改变或 must-pass 能力全不可用时才标记 `blocked`。
- 其余情况进入协作模式：只对会改变 Demo 数量、核心方法或公开素材边界的选择询问用户。
- 无论哪种模式，都先建立 run、保存证据、真实渲染并观看，不凭记忆跳阶段。

## 建立或恢复 run

下列命令中的 `SKILL_ROOT` 是本 Skill 的实际目录。新任务先确认目标是 Git 仓库，且 `.learning/runs/` 与 `.learning.lock` 都被 Git 忽略；`init_run.py start` 会在写入任何绝对路径前强制核验，缺少隔离时直接失败。随后才在私有 run 中初始化，不要提前占 Demo 编号：

```bash
python "$SKILL_ROOT/scripts/init_run.py" start \
  --repo "$TARGET_REPO" \
  --run-id "$RUN_ID" \
  --source "$SOURCE" \
  --source-id "$SAFE_SOURCE_ID" \
  --json
```

恢复任务时先校验 hash 链，并应用从首个漂移点向下失效：

```bash
python "$SKILL_ROOT/scripts/validate_run.py" \
  --repo "$TARGET_REPO" \
  --run-id "$RUN_ID" \
  --apply-invalidation \
  --json
```

只跳过仍同时匹配真实源媒体字节、当前 workflow 文件 hash、上游 artifact、schema/workflow 版本和输出 hash 的已完成阶段。来源、证据文件、Demo 源码、fixture、日志、观看材料或最终视频任一缺失/漂移，都必须从首个不可信阶段向下失效。读取 [contracts.md](references/contracts.md) 后再写任何机器 artifact。

## 按阶段学习

以 [workflow.json](references/workflow.json) 为机器事实，严格按下面的阶段前进：

| 阶段 | 必须完成的动作 | 交付 |
|---|---|---|
| `preflight` | 确认来源授权、目标仓库、执行模式和必需工具面 | `preflight.json` |
| `ingest` | 取得本地可读媒体并计算媒体字节 SHA-256；URL hash 只能临时定位 | `ingest.json` |
| `transcript` | 用现有本地 ASR 能力提取带时间码字幕 | `transcript.json` + 私有转录 |
| `learn_method` | 分开记录教程事实、屏幕代码、实现推断和本地决定 | `method-spec.json` |
| `observe_motion` | 粗采、观看、关键段加密、必要时放大小主体 | `motion-spec.json` + 帧证据 |
| `plan_demo` | 决定一个源产出几个独立 Demo、每个 slug、机制边界和素材画幅 | `asset-plan.json` |
| `build` | 规划后再绑定编号；调用官方 HyperFrames 工作流实现 | Demo 源码 + draft MP4 |
| `verify` | 先修完全部机械 must-pass | tests/check/snapshot/render 证据 |
| `review_r1` | 独立完整审阅 draft，只选一个最大主观问题 | `score-r1.json` |
| `revise` | 只改 `top_fix.dimension`，冻结已经正确的维度，生成新 MP4 hash | `revision.json` |
| `review_r2` | 独立完整审阅新 MP4，记录残余并停止 | `score-r2.json` |
| `finalize` | 把唯一 final 指向 R2 审阅的同一 hash，更新仓库索引 | `final.json` |

不要静默跳过失败阶段。阶段能力不可用时读取 [capabilities.json](references/capabilities.json)，只对当前输入满足 `applies_when` 的候选执行无副作用 probe；probe 禁止下载、安装或改写环境。通过运行时 Skill catalog 解析现有能力，不猜作者机器目录。全部适用候选失败则保存日志并标记 `blocked`。不要把 ASR、抽帧、素材管理或 HyperFrames 实现复制进本 Skill。

## 路由已有能力

- 链接摄取：优先调用 `video-to-text` 或现有通用视频能力。
- 本地转录：调用 `audio-to-subtitle`；必要时用本地 FFmpeg 抽音频并切换已安装的本地 ASR。
- 动效观察：调用 `animate-prompt`，并亲自查看实际帧；字幕不能替代视觉证据。
- 素材：调用 `media-use --adopt` 复用已有资产账本。先从构图推导画幅，海报优先竖图，滑动相册才通常需要横图。
- 创作：先读官方 `hyperframes` 路由，再按需使用 core、creative、animation 与 CLI 能力。环境故障才调用 `hyperframes-harness`，不要把环境排障写回本工作流。
- 验证：调用 HyperFrames lint、validate、inspect、snapshot 和 render；最终 MP4 用 ffprobe 和 SHA-256 证明。

只探测当前机器的真实状态。把探测结果留在本次 run 或 `runtime.local.json`，不要改写共享能力表为“当前已安装”。

## 规划后才绑定 Demo

先让 `plan_demo` 明确 Demo 数量与 slug，再为每个确认的独立 Demo 执行一次绑定：

```bash
python "$SKILL_ROOT/scripts/init_run.py" bind-demo \
  --repo "$TARGET_REPO" \
  --run-id "$RUN_ID" \
  --slug "$DEMO_SLUG" \
  --json
```

脚本通过 `fcntl.flock` 原子分配编号。不要以锁文件是否存在判断锁状态，也不要手工猜下一个编号。一个 run 默认只绑定一个 Demo；一个教程含多个互不相干的机制时，拆成多个 run 或在规划阶段明确拆分，不把浅尝辄止的 sampler 塞进一个 Demo。

## 守住证据不变量

- 让每条方法和动效结论包含 source ID、实际媒体 hash、时间范围、字幕 cue、帧或代码证据相对路径与真实 hash；validator 会读取文件本身，字符串占位不能通过。
- 把 `implementation_inference` 与 `tutorial_fact` 分开。教程没有说过的参数不能伪装成教程事实。
- 覆盖起始态、主要过渡中段、稳定态和退场。均匀接触表只是导航，不是关键动效分析。
- 把教程原媒体、完整转录、私人照片、候选缩略图和真实本地绝对路径留在 `.learning/runs/`。
- 让公开 Demo 自带原创或明确授权的 fixture；把私人照片作为被忽略的变量覆盖，确保 clean checkout 仍能 check/render。
- 每阶段完成时写语义 artifact，并在 `run.json.artifacts` 中记录当前输出、直接上游、source/media、schema、workflow 内容 hash。build/verify/score 还必须绑定真实 Demo 源码、fixture、日志、snapshot、render、framemd5、watch sheets 与密集帧带。

## 先机械验收，再主观评分

评审前完整读取 [rubric.json](references/rubric.json)。must-pass 不参与平均分；任何一项失败都先修复，无法修复则 `blocked`，不消耗 R1/R2。

R1 与 R2 都必须审阅真实完整 MP4，而不是只看 snapshots。评分写逐维度值，由 validator 按 rubric 权重重算总分；不能只自报一个总分。没有直接播放器时至少完成：

1. 全片无错误解码；
2. 生成并 hash `framemd5`；
3. 生成覆盖全时长的 6fps 顺序 watch sheets；
4. 为主要过渡生成高密度帧带；
5. 逐段记录问题时间码。

让独立 Reviewer 只看到原始 MP4、来源证据和 rubric，不给它生成者自评、预期答案或诊断。R1 只输出一个当前可修的 `top_fix`。修正后必须渲染新 hash；R2 不得复用 R1 的观看结论。R2 后停止，把 `top_fix` 设为 `null`。低于 80 分但 must-pass 全绿时标记 `completed_with_residuals`。

`revision.changed_dimension` 必须等于 R1 的 `top_fix.dimension`，并显式记录冻结维度。写入 `final.json` 后禁止重新渲染或替换候选；R2 低于阈值时只能使用 `completed_with_residuals`，且 run/final 状态必须一致。最终校验时开启 ffprobe：

```bash
python "$SKILL_ROOT/scripts/validate_run.py" \
  --repo "$TARGET_REPO" \
  --run-id "$RUN_ID" \
  --ffprobe on \
  --json
```

## 固化经验而不耦合机器

- 只把“真实失败、根因已验证、未来会复现”的规则列为经验候选。
- 至少跨三个真实案例仍成立后，才新增共享经验层；能直接成为稳定动作的规则同步收敛到本文件、contracts 或 rubric。
- 把被用户纠正的共享行为直接修回 Skill/reference，不要只写个人 auto memory。
- 不让一次教程的主题、画幅、素材路径或参数成为下一个教程的默认答案。

## 安全收尾

更新 Demo 索引后，只暂存本任务的精确文件。用同一个审计器分别检查 Skill 仓库与 Demo 仓库：

```bash
python "$SKILL_ROOT/scripts/audit_staged.py" \
  --repo "$TARGET_REPO" \
  --paths <exact-target-paths>
```

目标暂存集为空时必须失败。审计器读取 Git index 中的实际 blob：教程媒体、私人图片、未知二进制、私钥与凭证默认拒绝；只有明确安全类型或授权 fixture manifest 才能放行。修复所有私人主目录路径、真实鉴权头、Cookie、密钥赋值和敏感 query 后再提交。最终报告 Demo 路径、final hash、测试/check/render 结果、R2 分数与仍保留的残余，不隐藏 `completed_with_residuals`。
