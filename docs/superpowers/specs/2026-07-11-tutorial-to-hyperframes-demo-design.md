# 教学视频到 HyperFrames Demo：Skill 设计

> 把“人看教学视频、理解方法、动手复现、观看成片、只修最大问题”的过程，固化为一条可恢复、可审计、会积累验证经验的薄工作流。

## 目标

用户提供本地音视频或公开视频链接后，Skill 在自主或协作模式下完成：素材摄取、转录、分层观察、方法规格化、Demo 规划、HyperFrames 创作、真实渲染、最多一次定向修正，以及索引更新。最终产物是 `ai-clip-lab/demos/NN-slug/` 下可运行的独立 Demo 和一个经过验证的 MP4。

本 Skill 不以逐像素复制教程成片为目标。它应忠实复现教程明确教授的机制、视觉关系和时间逻辑，并用用户自有或可授权素材形成独立案例。

## 真实人类 SOP

首个成功样本 `06-hyperframes-opening` 表明，人实际做了以下事情：

1. 听懂教程把画面拆成固定目录、前景相框、模糊背景三层。
2. 把“相框快、背景慢”理解成视差，而不是只记住一个视觉形容词。
3. 在自己的项目仓库中建立独立 Demo。
4. 从本机照片中按目标画幅筛选素材并裁切。
5. 生成首版、真正观看成片，再把“慢一点、稳一点、间隔长一点”翻译为时长与缓动参数。
6. 加入声音，重新检查并保留最终成片。

两条新教程补充了两类学习方式：

- 3D 海报墙：从屏幕代码和参数对照实验建立 `perspective`、`rotationX`、`rotationY` 与视觉结果的因果映射；先做最小海报，再扩成多元素编舞。
- 三角函数空间：先构造三块共享坐标的二维投影平面，再让同一个相位同时驱动圆点、正弦波与余弦波；先有静态数据关系，后有动态效果。

因此总流程必须同时保留“教程说了什么”“帧中能观察到什么”“实现机制是推断还是屏幕代码证实”“本地项目为何这样决定”四类证据。

## 边界

### Skill 拥有

- 流程路由、自动/协作模式和停止规则；
- 运行状态、输入指纹、阶段交接和断点恢复；
- 方法、运动、素材与验收规格的统一契约；
- must-pass 与两轮主观评分；
- 验证后经验的去重、候选与上移规则。

### Skill 不拥有

- 平台下载器、ASR 模型或通用字幕实现；
- 通用抽帧/动效分析知识；
- HyperFrames composition、动画 API、素材库或渲染器实现；
- 本机代理、Node、FFmpeg、浏览器与字体排障；
- 通用视频模板。

这些能力分别调用现有 `video-to-text`、`audio-to-subtitle`、`animate-prompt`、`media-use`、官方 `hyperframes` 系列和 `hyperframes-ops`。运行时先探测真实可用性，失败时按能力注册表降级，不能静默跳过阶段。

## 总体架构

```text
用户输入
  -> preflight / run 初始化
  -> ingest + transcript
  -> learn-method + observe-motion
  -> plan-demo + choose-assets
  -> 官方 HyperFrames workflow 构建
  -> check + snapshot + render
  -> 独立评分 R1
  -> 只修一个 top_fix
  -> 独立评分 R2 / final
  -> 索引更新 + 经验候选上移
```

`SKILL.md` 只保存触发边界、阶段地图、全局不变量和下一跳。详细字段、能力候选与评分表放在一层 `references/`。确定性的 run 初始化与校验放在 `scripts/`，并以 Python 标准库实现，避免引入新的运行时依赖。

## 目录

```text
skills/tutorial-to-hyperframes-demo/
├── SKILL.md
├── .gitignore
├── agents/openai.yaml
├── references/
│   ├── workflow.json
│   ├── capabilities.json
│   ├── contracts.md
│   └── rubric.json
├── scripts/
│   ├── audit_staged.py
│   ├── init_run.py
│   └── validate_run.py
└── tests/
    └── test_run_contract.py
```

不预建空的 memory 树。只有在三个真实案例结束后出现“真实错误、根因已验证、未来会复现”的经验，才增加一层验证经验文件；能直接变成稳定动作的规则同步写回 `SKILL.md` 或 rubric。

## 运行状态

摄取与学习阶段先使用仓库级被忽略目录；只有 `plan_demo` 确认一个源应产出几个 Demo、slug 与范围后，才原子分配编号并绑定目标目录：

```text
<repo>/.learning/runs/<run-id>/
├── run.json
├── evidence/
├── method-spec.json
├── motion-spec.json
├── asset-plan.json
├── score-r1.json
├── score-r2.json
├── final.json
├── frames/
└── logs/
```

所有机器契约统一使用 JSON；Markdown 只保存面向人的语义解释。这样 Python 标准库能够校验字段、枚举和 hash，不形成“JSON 状态 + 只检查非空的 YAML”双事实源。`init_run.py` 提供 `start` 与 `bind-demo` 两个子命令，负责：

- `start`：本地源直接计算 SHA-256；URL 只保存 locator 与临时 locator hash，摄取完成后必须以下载媒体 SHA-256 替代，不能用 URL 字符串证明内容未变化；
- `start`：在写入任何私人 locator 前证明 `.learning/runs/` 与 `.learning.lock` 被目标 Git 仓库忽略；否则阻断并给出精确修复规则；
- `bind-demo`：规划完成后加锁分配 Demo 编号，并在建目录前写持久 intent、建目录后写 owner marker；崩溃重试必须接管同一 run 的空目录，而不是永久跳号；
- 写入 `status=running`、当前/下一阶段和输入摘要；
- 绝不保存 token、cookie 或私人素材绝对路径到公开文件。

编号分配使用 `fcntl.flock` 持有仓库级锁文件描述符；进程退出或崩溃时由内核自动释放，不以“创建后删除锁文件”充当互斥。锁文件本身可以长期存在，其内容只用于诊断，不决定锁是否有效。并发测试必须证明两个绑定不会取得同一编号；故障注入必须真正终止“mkdir 后、run 写回前”的进程，并证明同一 run 重试复用原编号。

`validate_run.py` 负责：

- 拒绝不安全 run ID；严格从 `completed_stages` 前缀推导并核对状态、当前/下一阶段；
- 按 artifact 类型校验必填字段、类型、枚举与 evidence 定位字段，不能把合法 hash 的空对象视为完成；
- 重新读取本地源或 URL 摄取后的 run 内媒体文件，校验真实字节 hash；
- 读取当前 `workflow.json` 内容 hash，校验 schema/workflow 版本与 descriptor，不接受 run 自我声明的任意版本；
- 校验 evidence 文件、binding、Demo 目录/源码/fixture、测试/check/inspect 日志、snapshots、draft、framemd5、watch sheets 和密集帧带实际存在且内容 hash 匹配；
- 强制 R1 审阅 hash 等于 verification draft、R2 等于 revision output；按 rubric 维度与权重重算总分，校验 revision 只改 R1 top_fix 并记录冻结维度；
- 校验 source/media 指纹、每阶段上游 artifact hash、workflow 内容 hash与输出 hash未漂移，从首个不匹配阶段向下失效；
- 校验 `final.json` 只有一个最终候选；
- 校验 `score-r2.json.reviewed_render_sha256` 与 `final.json.render_sha256` 完全相同；final 指针建立后不得再生成候选成片；
- 可选调用 ffprobe 校验最终 MP4 的时长、尺寸和帧率；R2 分数阈值、run 状态与 final 状态必须一致。

恢复时，只有实时源媒体、真实证据/产物、上游 artifact、当前 workflow 内容 hash、schema/workflow 版本和阶段输出 hash 全部匹配，才能跳过 `completed` 阶段。任何一项变化会使首个不匹配阶段及全部下游失效。

## 证据分层

`method-spec.json` 与 `motion-spec.json` 中的每条结论必须标记来源类型：

- `tutorial_fact`：字幕明确说出；
- `visual_observation`：帧序列直接可见；
- `code_fact`：屏幕代码或项目源码可确认；
- `implementation_inference`：对 CSS、Canvas、GSAP、Three.js 等机制的推断；
- `local_project_decision`：本地 Demo 的创作选择；
- `verified_result`：由 check、snapshot、ffprobe 或渲染比较证明。

每条教程忠实度结论还必须包含可定位 evidence：脱敏 `source_id`、实际媒体 SHA-256、`time_range`、字幕 cue/时间码，以及帧或代码截图的相对路径与 SHA-256。只标来源类型而没有定位证据不算完成；推断必须独立标注，不能冒充教程事实。

抽帧必须遵循“粗采 -> 看 -> 对关键段时间加密 -> 小主体空间放大”的循环。必须覆盖起始态、主要过渡中段、稳定态与退场，不能只看均匀接触表。

## 素材策略

- 先从构图推导所需画幅，不把上一次的 16:9 经验硬套到下一次；海报墙应优先竖图，滑动相册才优先 16:9。
- 对本地候选按尺寸、宽高比、清晰度、主体安全区和色彩差异记录选择理由。
- 私人源路径、候选缩略图和原视频留在仓库级 `.learning/runs/`；公开 README 只保留脱敏 source ID、媒体 hash、时间码、规则、逻辑资产名与裁剪说明。
- 已有素材交给 `media-use --adopt` 建账，不能另造重复 ledger。
- 公开 Demo 必须带明确授权的默认 fixture，clean checkout 无私人照片也能 check/render；本地照片通过声明的图片变量覆盖 fallback fixture。

## 评分与停止规则

must-pass 不进入平均分：来源可读、转录非空、关键帧覆盖、Demo 文件完整、数学/合约测试通过、`npm run check` 退出 0、最终 MP4 可由 ffprobe 验证、clean checkout 能使用 fixture smoke render、私人源未被 Git 跟踪、final 指针唯一。机械性 must-pass 必须在 R1 前修到全绿；无法修复时进入 `blocked`，不消耗主观评分轮次。

主观评分按教程方法忠实度、动效/时序忠实度、视觉层级、素材选择、连续观看节奏和工程可复现性加权；机器从逐维度评分重算总分。产品合同固定为两轮评审、一次修正：R1 审阅 draft，只输出一个影响最大且当前可修的 `top_fix`；原实现者只改该枚举维度并记录冻结维度。修正后直接渲染高质量候选，R2 必须完整审阅这个新 hash，不能复用 R1 结论。R2 后停止，并把同一 hash 写入 `final.json`；final 指针建立后不得重新渲染或替换成片。仍低于 80/100、但 must-pass 全绿时强制标记 `completed_with_residuals`，不得伪装成达标。

在当前工具面没有直接视频播放器时，“连续审阅”至少包括：完整 MP4 解码、framemd5、覆盖全时长的 6fps 顺序 watch sheets，以及关键过渡段的高密度帧带；Reviewer 必须逐段给时间码。评审 Agent 只拿原始产物、参考证据与 rubric，不拿生成者的自评、预期答案或诊断，避免答案泄漏。

## 隐私、版权与公开边界

- 不把教程原视频、完整转录、cookies、私人照片或绝对路径提交到公开仓库；两个仓库都必须先暂存精确目标文件，再用同一个审计器读取 Git index 中的真实 blob。媒体、未知二进制、私钥与凭证默认拒绝；只有扩展名、路径、大小和魔数都满足精确策略的公开字体等资产才可放行。文本规则覆盖用户主目录、Authorization/Bearer、Cookie/Set-Cookie、常见平台 token、带前缀的 key/token 赋值和敏感 query。策略文档与扫描器自身必须避免自匹配，不能靠空暂存区制造假绿。
- Demo 可提交方法摘要和自己实现的代码；原教程只记录标题/公开链接或本地文件指纹，不复制长段口播。
- 本地照片默认 gitignored；README 必须说明如何补素材。若需要 clean clone 开箱运行，应提供明确授权的占位素材，而不是误提交私人照片。

## 本轮两个验收案例

1. `11-hyperframes-3d-poster-wall`：293 帧 / 9.7667 秒，DOM/CSS 3D + GSAP。标题从水平中线展开，海报按边缘方向分组错峰进入；组装后整座舞台在 `perspective:2200px` 下倾斜到 `rotationX:20deg / rotationY:-10deg` 并巡航。素材按海报构图选竖图，不套用 16:9。
2. `12-hyperframes-trig-projection-room`：约 11–12 秒，Canvas 2D + 单条 paused GSAP 时间线。同一相位驱动单位圆点、后墙正弦波、地面余弦波；三块面共享坐标并以透视投影形成空间，不伪装成真正 Three.js 场景。

五段式数据 sampler 本轮不做：它横跨 Canvas、地图 GeoJSON、Three.js、DOM 时间尺和排名插值，压进一个 Demo 会让每段只能展示结果，违背教程“先讲清静态关系，再用单一原理驱动动态”的核心方法。其余四类登记为后续独立候选。

## 验收

- 官方 `quick_validate.py` 通过；
- run 合约测试覆盖私有状态 ignore 门、仓库级 start、规划后 bind、并发编号、mkdir 后 SIGKILL 恢复、路径逃逸、实时媒体/证据/Demo/日志/观看产物漂移、workflow 内容变化、阶段指针错位、artifact 缺字段/错类型/错枚举、R1/R2 与真实 render 解绑、错误修正维度、加权分伪造、低分状态伪装、final 多指针及 final 与 R2 hash 不一致；
- staged 对抗测试覆盖私人图片/MP4、LFS 伪装、Cookie、SSH/PEM 私钥、带前缀 secret 变量和常见平台 token；
- 用 `06` 作为成功夹具初始化并校验一份私有 run；
- 两个新 Demo 分别通过数学/合约测试、lint、validate、inspect、关键帧 snapshot、高质量 render 与全时长连续审阅；
- 每个 Demo 保存接触表、R1/R2 评分与唯一 final；R2 审阅 hash 与最终 MP4 hash 相同；
- 两个仓库索引更新后，工作树中只有本任务文件被提交。
