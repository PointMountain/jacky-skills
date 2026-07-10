# Tutorial to HyperFrames Demo Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个薄的 `tutorial-to-hyperframes-demo` Skill，把教学视频/链接编排为有证据、有状态、有两轮评分的可渲染 HyperFrames Demo。

**Architecture:** `SKILL.md` 只做阶段地图与不变量；`references/` 保存能力候选、阶段事实、契约和 rubric；两个 Python 标准库脚本负责原子 run 初始化与确定性校验。外部转录、动效观察、素材、HyperFrames 创作和环境排障全部调用已有 Skill，不复制实现。

**Tech Stack:** Markdown/YAML、Python 3 标准库、`unittest`、官方 skill-creator 校验、j-skills。

---

## Chunk 1: 可恢复运行契约

### Task 1: 初始化 Skill 脚手架

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/SKILL.md`
- Create: `skills/tutorial-to-hyperframes-demo/agents/openai.yaml`
- Create: `skills/tutorial-to-hyperframes-demo/.gitignore`
- Create: `skills/tutorial-to-hyperframes-demo/references/`
- Create: `skills/tutorial-to-hyperframes-demo/scripts/`
- Create: `skills/tutorial-to-hyperframes-demo/tests/`

- [ ] **Step 1: 用官方脚本初始化**

Run:

```bash
python "$HOME/.codex/skills/.system/skill-creator/scripts/init_skill.py" \
  tutorial-to-hyperframes-demo \
  --path skills \
  --resources scripts,references \
  --interface display_name="HyperFrames Apprentice" \
  --interface short_description="从教学视频自主学习并产出可验证 HyperFrames Demo" \
  --interface default_prompt="Use $tutorial-to-hyperframes-demo to learn this tutorial and build a verified HyperFrames demo."
```

Expected: 新目录生成，frontmatter 仅含 `name` 与 `description`，`agents/openai.yaml` 字符串均有引号。

- [ ] **Step 2: 增加本地状态忽略规则**

`.gitignore` 只忽略：

```gitignore
experience.local.md
runtime.local.json
```

- [ ] **Step 3: 检查脚手架**

Run: `git status --short skills/tutorial-to-hyperframes-demo`

Expected: 只有新 Skill 目录文件，无其他路径变化。

### Task 2: 以 TDD 实现 run 初始化

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py`
- Create: `skills/tutorial-to-hyperframes-demo/scripts/init_run.py`

- [ ] **Step 1: 写失败测试**

测试真实 CLI 行为：

- 本地 source 生成稳定 SHA-256；
- URL source 只生成临时 locator hash，摄取完成前不能冒充媒体指纹；
- `start` 先在仓库级 `.learning/runs/` 创建 run，不占 Demo 编号；
- `bind-demo` 在规划后加锁选择未占用编号并绑定目录；
- 两个并发 `bind-demo` 不会取得同一编号；持锁进程异常退出后下一次绑定可恢复；
- 重复 `run_id` 拒绝覆盖；
- 输出 `run.json` 为 `status=running/current_stage=preflight`；
- 私密 source 绝对路径只在私有 run 内，不写公开 spec。
- `.learning/runs/` 或 `.learning.lock` 未被 Git 忽略时，在写入 private locator 前失败；
- 故障注入在 Demo `mkdir` 后 SIGKILL，重试同一 run 接管空目录并复用编号。

- [ ] **Step 2: 验证 RED**

Run:

```bash
python -m unittest skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py -v
```

Expected: FAIL，原因是 `init_run.py` 尚不存在或 CLI 未实现。

- [ ] **Step 3: 写最小实现**

使用 `argparse/hashlib/json/pathlib/tempfile/os.replace/fcntl`。`start` 先用 `git check-ignore` 验证两类私有状态；`bind-demo` 在持有 `fcntl.flock(LOCK_EX)` 时先写 intent，再建目录和 owner marker，重试可接管本 run 的空目录。锁文件可保留，不能用文件是否存在判断占用。所有 JSON 先写临时文件再 `os.replace`。

- [ ] **Step 4: 验证 GREEN**

Run: `python -m unittest skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py -v`

Expected: 全部 PASS。

### Task 3: 以 TDD 实现 run 校验与失效

**Files:**
- Modify: `skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py`
- Create: `skills/tutorial-to-hyperframes-demo/scripts/validate_run.py`

- [ ] **Step 1: 写失败测试**

新增行为：

- 非法状态/阶段失败；
- 合法 JSON 但缺必填字段、字段类型错误或枚举错误失败；
- method/motion evidence 缺 `source_id`、实际媒体 hash、时间范围或证据 hash 失败；
- score 缺 `reviewed_render_sha256` 或观看/解码证据失败；
- completed 阶段工件缺失或空文件失败；
- source/media、上游 artifact、workflow/schema 版本或输出 hash 变化后，从首个不匹配阶段向下失效；
- final 0 个或多个候选失败；
- 单一 final 且 MP4 非空通过；
- final render hash 与 R2 审阅 hash 不一致失败；
- run-id 逃逸、实时源文件变化、workflow 内容漂移、current/next 错位失败；
- evidence、binding、Demo 源码/fixture、验证日志/snapshot/draft 任一缺失或 hash 伪造失败；
- R1/R2 的 render、framemd5、6fps watch sheets、密集帧带必须真实存在并互相绑定；
- 修正维度不等于 R1 top_fix、冻结维度缺失、加权总分不一致、低分却标 completed 失败；
- `--json` 输出机器可读的 `ok/errors/warnings`。

- [ ] **Step 2: 验证 RED**

Run: `python -m unittest skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py -v`

Expected: 新测试因 validator 缺失而 FAIL。

- [ ] **Step 3: 写最小实现**

校验只做确定性事实；主观判断由 Reviewer 完成，但逐维度分数按 rubric 权重重算。存在 ffprobe 时校验时长、尺寸与帧率，没有时返回 warning 而不伪造成功证据。

- [ ] **Step 4: 验证 GREEN**

Run: `python -m unittest skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py -v`

Expected: 全部 PASS。

## Chunk 2: 薄工作流与能力路由

### Task 4: 编写机器事实参考

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/references/workflow.json`
- Create: `skills/tutorial-to-hyperframes-demo/references/capabilities.json`
- Create: `skills/tutorial-to-hyperframes-demo/references/rubric.json`
- Create: `skills/tutorial-to-hyperframes-demo/references/contracts.md`

- [ ] **Step 1: 写 workflow.json**

定义 `preflight -> ingest -> transcript -> learn_method -> observe_motion -> plan_demo -> build -> verify -> review_r1 -> revise -> review_r2 -> finalize`，每阶段只列输入、输出、能力 ID 与 next。

- [ ] **Step 2: 写 capabilities.json**

稳定注册能力候选与降级：链接摄取、本地转录、动效观察、素材、HyperFrames 路由、环境、渲染。每项写 `applies_when`、通过运行时 Skill catalog 或本地 binary resolver 的无副作用 probe、输入、输出与 fallback；probe 禁止 `npx` 下载/安装，不提交“当前已安装”这类漂移状态。

- [ ] **Step 3: 写 rubric.json**

must-pass 与主观维度分开；机械 must-pass 在 R1 前修到全绿或 blocked；主观阈值 80/100，写清权重与 1–5 锚点，明确 `review_rounds: 2`、`revision_rounds: 1`，R1 只允许一个 `top_fix`。

- [ ] **Step 4: 写 contracts.md**

给出 run、method、motion、asset、score、final 的 JSON 最小示例；每条教程事实包含 source ID、媒体 hash、时间码、cue 与帧/代码证据 hash；解释六类 evidence 来源与隐私边界。

### Task 4.1: 编写 staged-files 隐私审计器

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/scripts/audit_staged.py`
- Modify: `skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py`

- [ ] **Step 1: 先写失败测试**

覆盖：未暂存目标时明确失败；从 index blob 拦截私人图片/MP4/LFS 伪装/未知二进制；真实用户主目录、鉴权头、Cookie、SSH/PEM 私钥、带前缀 key/token、常见平台 token 与敏感 query 失败；公开字体仅在路径、扩展、大小和魔数全部匹配时放行；安全策略与审计器自身不自匹配；`--paths` 之外的用户改动不进入本任务审计。

- [ ] **Step 2: 最小实现并转绿**

枚举实际 staged 路径并用 `git cat-file` 读取 `:path` 对应的 index 对象；使用拆分构造的精确规则和最小 allowlist；输出 JSON 结果与非零退出码。两个仓库提交前调用同一个脚本。

### Task 5: 编写薄 SKILL.md

**Files:**
- Modify: `skills/tutorial-to-hyperframes-demo/SKILL.md`
- Modify: `skills/tutorial-to-hyperframes-demo/agents/openai.yaml`

- [ ] **Step 1: 写触发描述**

覆盖：给教学视频/链接学习、复刻方法、在 ai-clip-lab 增加 HyperFrames Demo、无人值守批量学习。frontmatter 不含额外字段。

- [ ] **Step 2: 写阶段地图**

正文只保存：自动模式规则、Phase 0 本地经验读取、阶段表、证据不变量、先仓库级学习后绑定 Demo、恢复/评分/经验上移、按需 reference 路由。R1/R2 都必须记录新 MP4 hash、完整解码/连续观看状态与问题时间码。不得复制任何外部 Skill 的完整操作说明。

- [ ] **Step 3: 写经验规则**

通用规则只有经过验证才能进共享 Skill；本机路径、代理、照片根与工具状态进入 `experience.local.md/runtime.local.json`；被用户纠正的共享行为必须固化回 SKILL/reference，不能只写个人 auto memory。

- [ ] **Step 4: 自检长度与重复**

Run:

```bash
wc -l skills/tutorial-to-hyperframes-demo/SKILL.md
python skills/tutorial-to-hyperframes-demo/scripts/audit_staged.py --help
```

Expected: SKILL.md < 500 行；审计 CLI 可用。真实 staged 内容在提交前统一扫描。

## Chunk 3: 校验、前向测试与安装

### Task 6: 官方校验和全量测试

**Files:**
- Test: `skills/tutorial-to-hyperframes-demo/`

- [ ] **Step 1: 跑单元测试**

Run: `python -m unittest skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py -v`

Expected: 0 failures。

- [ ] **Step 2: 跑官方校验**

Run:

```bash
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/tutorial-to-hyperframes-demo
```

Expected: validation passed。

- [ ] **Step 3: 用 06 成功案例做前向测试**

以 `06-hyperframes-opening` 的教学音频与现有 final 为 raw artifact，先仓库级初始化私有 run、补最小阶段工件、规划后 bind，并执行 validator。不得把预期诊断喂给测试 Agent。

- [ ] **Step 4: 独立 spec 与质量评审**

Reviewer 只拿 Skill 路径与请求：“使用该 Skill 学习一个本地教程并规划 Demo”。修复所有重要问题后重跑测试与官方校验。

### Task 7: 提交并链接 Skill

**Files:**
- Stage: `skills/tutorial-to-hyperframes-demo/`
- Stage: `docs/superpowers/specs/2026-07-11-tutorial-to-hyperframes-demo-design.md`
- Stage: `docs/superpowers/plans/2026-07-11-tutorial-to-hyperframes-demo.md`

- [ ] **Step 1: 检查差异**

Run: `git diff --check && git status --short`

- [ ] **Step 2: 精确暂存并运行统一审计**

```bash
git add skills/tutorial-to-hyperframes-demo docs/superpowers/specs/2026-07-11-tutorial-to-hyperframes-demo-design.md docs/superpowers/plans/2026-07-11-tutorial-to-hyperframes-demo.md
python skills/tutorial-to-hyperframes-demo/scripts/audit_staged.py --paths skills/tutorial-to-hyperframes-demo docs/superpowers/specs/2026-07-11-tutorial-to-hyperframes-demo-design.md docs/superpowers/plans/2026-07-11-tutorial-to-hyperframes-demo.md
```

Expected: 审计明确看到非空 staged 文件集并返回 `ok=true`。

- [ ] **Step 3: 只提交本任务文件**

```bash
git commit -m "feat(skill): add tutorial-to-hyperframes workflow"
```

- [ ] **Step 4: 带回主工作树后链接**

在原 `jacky-skills` 工作树安全 cherry-pick 后：

```bash
j-skills link skills/tutorial-to-hyperframes-demo
j-skills install tutorial-to-hyperframes-demo --global --env codex,claude-code
j-skills link --list --json
j-skills list --all --json
```

Expected: Skill 指向 `jacky-skills/skills/tutorial-to-hyperframes-demo`，Codex 与 Claude Code 全局可发现。
