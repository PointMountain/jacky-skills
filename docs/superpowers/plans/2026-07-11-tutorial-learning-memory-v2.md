# Tutorial Learning Memory V2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按用户最新的自进化 Skill V2 哲学优化 `tutorial-to-hyperframes-demo`，补齐人类可读提取 SOP、运行事实工件、Skills 使用清单、任务复盘和有门槛的原子 memory。

**Architecture:** `SKILL.md` 保持薄地图；`references/` 保存提取 SOP、learning loop 和版本化 workflow。目标 run 私有目录保存 capability state、decision trace、usage manifest/ledger 和 retrospective；长期 `local/` 只在真实候选通过证据门槛后创建。保留 workflow `1.0.0` 原字节，新增 `1.1.0` sidecar，确保两个既有真实 run 不失效。

**Tech Stack:** Python 3 标准库、JSON、Markdown、`unittest`、Git index staged audit、FFmpeg/FFprobe。

**设计输入边界:** 主仓库中的 `docs/自进化-skill-设计哲学-v2.md` 与正在迁移的新目录 `docs/philosophy/references/` 当前都是用户未跟踪文件。本任务只读吸收其原则，不暂存、不提交、不移动这些文件，也不让可分享 Skill 依赖它们的存在。

**命令变量:** 执行示例统一使用 `SKILL_WORKTREE="$HOME/jacky-github/jacky-skills--tutorial-memory-ledger"`、`SKILL_ROOT="$SKILL_WORKTREE/skills/tutorial-to-hyperframes-demo"`、`AI_CLIP_LAB="$HOME/jacky-github/ai-clip-lab"`，避免把作者机器绝对主目录写入可提交文档。

---

## Chunk 1: V2 文档与版本化契约

### Task 1: 写独立提取 SOP 并压薄主 Skill

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/references/extraction-protocol.md`
- Create: `skills/tutorial-to-hyperframes-demo/references/learning-loop.md`
- Modify: `skills/tutorial-to-hyperframes-demo/SKILL.md`
- Modify: `skills/tutorial-to-hyperframes-demo/.gitignore`
- Modify: `skills/tutorial-to-hyperframes-demo/agents/openai.yaml`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_docs.py`

- [ ] **Step 1: 写失败的文档结构测试**

```python
def test_skill_routes_v2_references(self):
    body = SKILL.read_text(encoding="utf-8")
    for name in ("extraction-protocol.md", "learning-loop.md"):
        self.assertIn(f"references/{name}", body)
        self.assertTrue((REFERENCES / name).is_file())

def test_private_learning_memory_is_ignored(self):
    self.assertIn("/local/", GITIGNORE.read_text(encoding="utf-8").splitlines())

def test_skill_stays_a_thin_map(self):
    self.assertLessEqual(len(SKILL.read_text(encoding="utf-8").splitlines()), 200)
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_docs.py -v`

Expected: FAIL，references 与 ignore 尚不存在。

- [ ] **Step 3: 写 `extraction-protocol.md`**

按 V2 SOP 卡覆盖：本地视频/配对音轨/URL 摄取、音轨识别、时间码字幕、cue 复核、粗抽帧、关键段密抽帧、小主体放大、屏幕代码取证、四类事实分层、method/motion handoff、异常回退和记忆候选。每段包含触发、输入、观察、证据、判断、行动、产物、must-pass 和 fallback。

- [ ] **Step 4: 写 `learning-loop.md`**

集中解释：

```text
runtime-capabilities
→ decision-trace
→ skill-usage-manifest + usage-ledger
→ retrospective
→ candidate 分流
→ local 原子 memory / Skill-reference / backlog
```

明确这些工件不是 CoT；没有真实内容时不预建 memory/map；下一轮最多读取 1–3 条。

- [ ] **Step 5: 压薄 `SKILL.md` 并更新元数据**

保留触发边界、12 阶段、全局不变量、must-pass/两轮停止、blocked 条件和语义阅读入口。移走具体提取配方、长字段说明和候选 Skill 列表。更新 `openai.yaml` 的短描述与默认 prompt，使其包含“学习、复盘、可验证账本”。

- [ ] **Step 6: 运行测试与官方校验**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_docs.py -v
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skills/tutorial-to-hyperframes-demo
```

Expected: PASS，`Skill is valid!`。

- [ ] **Step 7: 提交**

```bash
git add skills/tutorial-to-hyperframes-demo/SKILL.md \
  skills/tutorial-to-hyperframes-demo/.gitignore \
  skills/tutorial-to-hyperframes-demo/agents/openai.yaml \
  skills/tutorial-to-hyperframes-demo/references/extraction-protocol.md \
  skills/tutorial-to-hyperframes-demo/references/learning-loop.md \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_docs.py
git commit -m "docs(skill): align tutorial learning with v2 philosophy"
```

### Task 2: 版本化 workflow 并定义运行事实契约

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/references/workflows/1.0.0.json`
- Create: `skills/tutorial-to-hyperframes-demo/references/workflows/1.1.0.json`
- Modify: `skills/tutorial-to-hyperframes-demo/references/workflow.json`
- Create: `skills/tutorial-to-hyperframes-demo/references/learning-contract.json`
- Modify: `skills/tutorial-to-hyperframes-demo/references/capabilities.json`
- Modify: `skills/tutorial-to-hyperframes-demo/references/contracts.md`
- Modify: `skills/tutorial-to-hyperframes-demo/references/rubric.json`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_contracts.py`

- [ ] **Step 1: 写失败的版本/契约测试**

至少断言：

```python
def test_frozen_v1_workflow_preserves_original_hash(self):
    self.assertEqual(sha256(V1.read_bytes()),
                     "ba38112d9af58bb268b8052cde776928a1a1d24ed7b5afa783f6dc32fb973ab8")

def test_current_and_v11_workflows_are_byte_identical(self):
    self.assertEqual(CURRENT.read_bytes(), V11.read_bytes())
```

另校验 learning contract 的 artifact/enums、manifest/result/candidate destination、selection 上限和所有 JSON 可解析。

- [ ] **Step 2: 运行并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_contracts.py -v`

- [ ] **Step 3: 冻结 1.0、建立 1.1**

`workflows/1.0.0.json` 与 commit `0dcb131` 原文件逐字节相同。`1.1.0` 保持原 12 阶段，并增加终止态 sidecar：

```text
memory-selection.json
runtime-capabilities.json
decision-trace.json
skill-usage-manifest.json
usage-ledger.json
retrospective.json
```

`workflow.json` 与 `workflows/1.1.0.json` 相同。

- [ ] **Step 4: 定义最小机器契约**

`learning-contract.json` 只定义稳定字段、有限枚举、状态 `collecting|frozen|backfilled`、sidecar 指针和候选分流；详细语义留在 `learning-loop.md`。

`capabilities.json` 明确为稳定能力槽位注册表，候选增加 priority/probe/fallback；当前可用性只写 `runtime-capabilities.json`。`rubric.json` 明确低分与 R2 residual 只产生 candidate。

- [ ] **Step 5: 控制 `contracts.md` 增长**

只补 core run 对 extension 的指针、sidecar 私有边界和 validator 责任；字段细节直接链接 `learning-loop.md`/`learning-contract.json`，不重复整份 schema。

- [ ] **Step 6: 运行测试并提交**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_contracts.py -v
git add skills/tutorial-to-hyperframes-demo/references \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_contracts.py
git commit -m "feat(skill): version tutorial learning contracts"
```

### Task 3: 让 init/validator 兼容 legacy 1.0 与新 1.1

**Files:**
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/init_run.py`
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/validate_run.py`
- Modify: `skills/tutorial-to-hyperframes-demo/tests/test_init_safety.py`
- Modify: `skills/tutorial-to-hyperframes-demo/tests/test_run_contract.py`
- Modify: `skills/tutorial-to-hyperframes-demo/tests/test_validator_truth.py`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_compatibility.py`

- [ ] **Step 1: 写失败的兼容矩阵测试**

```text
new 1.1 start → extension state=collecting
1.1 preflight complete → selection required
1.1 completed → all sidecars + state=frozen required
1.1 --core-only → only validate original 12 stages
legacy 1.0 default → pass without sidecar
legacy 1.0 --require-learning-memory → fail until backfill
unknown workflow/hash → fail closed
extension failure → invalidated_from remains null
```

- [ ] **Step 2: 运行并确认失败**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_compatibility.py -v
python3 -m unittest discover -s skills/tutorial-to-hyperframes-demo/tests -p 'test_*.py'
```

- [ ] **Step 3: 修改 init 默认和 extension**

`init_run.py` 只创建新 workflow `1.1.0`；初始化：

```json
{
  "extensions": {
    "learning_loop": {
      "required": true,
      "state": "collecting",
      "contract_version": "1.0.0",
      "selection": null,
      "sidecars": {}
    }
  }
}
```

- [ ] **Step 4: 按 run 版本解析 workflow**

`Validator.__init__()` 先读取 run，再用显式 allowlist resolver 选择 `workflows/1.0.0.json` 或 `1.1.0.json`。`validate_state/descriptor` 比较 run 自己的受支持版本和所选文件真实 hash，不再强制 current。

- [ ] **Step 5: 增加 core/full 模式**

CLI 增加互斥 `--core-only`、`--require-learning-memory`。extension 校验错误不绑定原 stage，不触发 `--apply-invalidation`。现有 core fixture helper 使用 `--core-only`；legacy truth fixture继续走默认 full。

- [ ] **Step 6: 运行全部测试并提交**

```bash
python3 -m unittest discover -s skills/tutorial-to-hyperframes-demo/tests -p 'test_*.py' -v
git add skills/tutorial-to-hyperframes-demo/scripts/init_run.py \
  skills/tutorial-to-hyperframes-demo/scripts/validate_run.py \
  skills/tutorial-to-hyperframes-demo/tests
git commit -m "feat(skill): preserve legacy tutorial runs"
```

## Chunk 2: 运行事实与原子 memory

### Task 4: 实现确定性 JSON、路径与隐私基础

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/scripts/learning_common.py`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_common.py`

- [ ] **Step 1: 写失败测试**

覆盖 canonical JSON、NFC、SHA-256、原子写、run-relative containment、`..`/symlink、绝对/Unicode/Windows home、Cookie/token/private key、敏感 URL/query 和 Git ignore 证明。

- [ ] **Step 2: 运行并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_common.py -v`

- [ ] **Step 3: 实现聚焦 helper**

```python
def canonical_json_bytes(value: Any) -> bytes: ...
def sha256_file(path: Path) -> str: ...
def secure_run_relative(run_dir: Path, value: str, *, must_exist: bool) -> Path: ...
def reject_private_payload(value: Any) -> None: ...
def atomic_write_json(path: Path, value: dict[str, Any]) -> None: ...
def write_immutable_or_adopt(path: Path, value: dict[str, Any]) -> None: ...
```

不构建通用数据库、远端服务、宿主签名或工具执行代理。

- [ ] **Step 4: 运行测试、py_compile 并提交**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_common.py -v
python3 -m py_compile skills/tutorial-to-hyperframes-demo/scripts/*.py
git add skills/tutorial-to-hyperframes-demo/scripts/learning_common.py \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_common.py
git commit -m "feat(skill): add private learning primitives"
```

### Task 5: 实现运行事实记录和 finalize

**Files:**
- Create: `skills/tutorial-to-hyperframes-demo/scripts/record_learning.py`
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/validate_run.py`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_runtime.py`

- [ ] **Step 1: 写失败测试**

分组覆盖：

- `record-capability` 的 available/degraded/missing、selected/fallback/evidence；
- `record-decision` 的事实链、无证据 root cause 拒绝；
- `record-usage` 自行 hash evidence refs，并要求每个已完成阶段/capability 有真实或明确 missing/degraded/not_recorded 事件；
- skill usage manifest 的 capability/candidates/selected/result/evidence/friction；
- usage ledger 的 content/tool/evidence refs；
- retrospective 的 result/findings/destination/status；
- `passed` 但 output/evidence 不存在失败；
- 零 candidate 合法；猜测/审美/residual 只能 backlog；
- finalize 从 `collecting` 原子变为 `frozen`，重复同字节幂等，不同字节拒绝覆盖。

- [ ] **Step 2: 运行并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_runtime.py -v`

- [ ] **Step 3: 实现 CLI 与唯一输入契约**

所有语义 draft 必须是当前 run 内相对 JSON 文件，通过 `--input <run-relative-path>` 传入；禁止 stdin、内联 JSON、绝对路径和 `..`。`--json` 只表示“stdout 使用机器 JSON”，不是输入。Task 5 只注册本任务已有失败测试覆盖的子命令：

```text
record-capability --input drafts/runtime-capability.json
record-decision --input drafts/decision.json
record-usage --input drafts/usage-event.json
finalize --manifest-input drafts/skill-usage-manifest.json \
         --ledger-input drafts/usage-ledger.json \
         --retrospective-input drafts/retrospective.json
```

模型写语义 draft；脚本读取实际 refs、重算 hash、校验枚举和隐私。`record-usage` 写入不可变 `usage-events/`；finalize 按 workflow stage/capability 矩阵检查覆盖并聚合 ledger，不能只验证已声明条目。Skills/工具无法从当前 run 证实时只能 `not_recorded`，不能用当前机器倒推历史。

完整调用示例：

```bash
python3 skills/tutorial-to-hyperframes-demo/scripts/record_learning.py finalize \
  --repo /path/to/target-repo \
  --run-id tutorial-001 \
  --manifest-input drafts/skill-usage-manifest.json \
  --ledger-input drafts/usage-ledger.json \
  --retrospective-input drafts/retrospective.json \
  --json
```

- [ ] **Step 4: 实现 full extension validator**

原 core validation 后检查 sidecar 真实文件/hash、manifest/ledger/output/evidence、decision trace、retrospective 与 R1/R2/final 绑定。完成态 workflow 1.1 缺任一必需 sidecar即失败；legacy 只在显式 require 或存在 extension 时校验。

- [ ] **Step 5: 运行测试并提交**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_runtime.py -v
python3 -m py_compile skills/tutorial-to-hyperframes-demo/scripts/*.py
git add skills/tutorial-to-hyperframes-demo/scripts \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_runtime.py
git commit -m "feat(skill): record evidence-backed learning runs"
```

### Task 6: 实现渐进选择、候选分流和原子 memory

**Files:**
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/record_learning.py`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_memory.py`

- [ ] **Step 1: 写失败测试**

覆盖：

- 无真实 memory 时不创建 `local/`，仍生成空 selection；
- 只读取 active、作用域匹配的 1–3 条；当前证据冲突时拒绝；
- selection 冻结当时 snapshot/hash，后续更新原 memory 不破坏旧 run；
- 同根因查重、superseded/archived、无孤立 index；
- feedback 写入私有 `feedback-candidates/`，只生成 candidate；promotion 消费该 candidate 并写私有 receipt；
- failure root cause 缺证据/未来复现边界不能进入 error memory；
- environment fact 缺 verified_at/边界不能进入 local memory；
- 通用模式和 skill friction 只生成 adjustment/reference candidate，不自动改 registry/Skill；
- 本地 memory 无绝对路径、媒体、字幕、秘密。

- [ ] **Step 2: 运行并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_memory.py -v`

- [ ] **Step 3: 实现 select/promote/feedback/lint**

在本任务才注册：

```text
select-memory --input drafts/memory-query.json
record-feedback --input drafts/feedback-candidate.json
promote-memory --input feedback-candidates/<candidate-id>.json
lint
```

`memory-query.json` 是当前 run 内相对文件，至少包含 `task_intents`、`mechanisms`、`capability_ids` 和 `conflicting_evidence_refs`；脚本读取真实冲突证据并最多选 1–3 条。完整调用示例：

```bash
python3 skills/tutorial-to-hyperframes-demo/scripts/record_learning.py select-memory \
  --repo /path/to/target-repo --run-id tutorial-001 \
  --input drafts/memory-query.json --json
```

root index 必须说明何时/为何进入；至少 3 条共享问题模型后才创建 map。原子 memory 一条一个根因；同根因更新原条并保留 selection snapshot。feedback candidate 绑定 run/final/R2/evidence；冻结后的 retrospective 不回写。

- [ ] **Step 4: 运行测试并提交**

```bash
python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_memory.py -v
git add skills/tutorial-to-hyperframes-demo/scripts/record_learning.py \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_memory.py
git commit -m "feat(skill): add gated atomic learning memory"
```

## Chunk 3: Backfill、真实验收与交付

### Task 7: 实现受限 legacy backfill

**Files:**
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/record_learning.py`
- Modify: `skills/tutorial-to-hyperframes-demo/scripts/validate_run.py`
- Test: `skills/tutorial-to-hyperframes-demo/tests/test_learning_backfill.py`

- [ ] **Step 1: 写失败测试**

覆盖：只接受完成的 1.0；从已有 artifact/receipt/score/final 派生；未知 Skills/工具为 `not_recorded`；不产生 active memory；第二次执行字节幂等；除新增 sidecar 和 `run.json.extensions` 外旧文件/final hash 不变；extension 错误不 invalidation core。

- [ ] **Step 2: 运行并确认失败**

Run: `python3 -m unittest skills/tutorial-to-hyperframes-demo/tests/test_learning_backfill.py -v`

- [ ] **Step 3: 实现并注册 backfill**

此时才在 CLI 注册 `backfill`。生成空历史 selection、已知 capability/decision/usage refs、`historical_best_effort` manifest/ledger、R1→R2 retrospective，state=`backfilled`。禁止读取当前 Skill/工具版本补历史。

- [ ] **Step 4: 运行全部测试并提交**

```bash
python3 -m unittest discover -s skills/tutorial-to-hyperframes-demo/tests -p 'test_*.py' -v
python3 -m py_compile skills/tutorial-to-hyperframes-demo/scripts/*.py
git add skills/tutorial-to-hyperframes-demo/scripts \
  skills/tutorial-to-hyperframes-demo/tests/test_learning_backfill.py
git commit -m "feat(skill): backfill legacy learning facts"
```

### Task 8: 回填两个真实 run 并做 forward test

**Files:**
- Private only: `$AI_CLIP_LAB/.learning/runs/2026-07-11-poster-wall/`
- Private only: `$AI_CLIP_LAB/.learning/runs/2026-07-11-trig-room/`
- Temporary: `/tmp/tutorial-learning-memory-forward-*`

- [ ] **Step 1: 保存回填前 manifest 和未回填 forward-test 副本**

排除 `run.json` 与未来新增 sidecar，对两个 run 其余全部已有文件和两个 final MP4 建 `/tmp` 字节 manifest；另外保存一份规范化 `run.json`（移除顶层 `extensions` 后）用于前后语义比较。必须在真实 run backfill 前建立隔离副本：

```bash
rm -rf /tmp/tutorial-learning-memory-forward-poster
git clone --no-hardlinks "$AI_CLIP_LAB" \
  /tmp/tutorial-learning-memory-forward-poster
mkdir -p /tmp/tutorial-learning-memory-forward-poster/.learning/runs
ditto "$AI_CLIP_LAB/.learning/runs/2026-07-11-poster-wall" \
  /tmp/tutorial-learning-memory-forward-poster/.learning/runs/2026-07-11-poster-wall
```

断言副本 `run.json` 尚无 `extensions.learning_loop`，且六种 sidecar 均不存在；把该断言结果和副本原 final hash 保存到 `/tmp`。之后真实 run 的 backfill不得再覆盖这个副本。

- [ ] **Step 2: 执行 backfill 两次验证幂等**

对两个 run 各执行两次 `record_learning.py backfill`。第二次输出必须说明 reused/unchanged，不能因 timestamp 产生新字节。

- [ ] **Step 3: 严格验证与 final hash 对比**

```bash
PATH=/opt/homebrew/bin:$PATH python3 skills/tutorial-to-hyperframes-demo/scripts/validate_run.py \
  --repo "$AI_CLIP_LAB" \
  --run-id 2026-07-11-poster-wall --require-learning-memory --ffprobe on --json
PATH=/opt/homebrew/bin:$PATH python3 skills/tutorial-to-hyperframes-demo/scripts/validate_run.py \
  --repo "$AI_CLIP_LAB" \
  --run-id 2026-07-11-trig-room --require-learning-memory --ffprobe on --json
```

Expected: 两者 `ok=true`；排除 `run.json` 的旧文件和成片 hash 不变；回填后 `run.json` 移除顶层 `extensions` 后与回填前规范化内容完全相同。

- [ ] **Step 4: 对真实完成 run 做无答案泄漏 forward test**

使用 Step 1 冻结的未回填副本，重新断言无 extension/sidecar 后 dispatch fresh Agent。原始任务只写：

```text
Use $tutorial-to-hyperframes-demo at
$SKILL_ROOT
to resume the completed legacy run 2026-07-11-poster-wall in
/tmp/tutorial-learning-memory-forward-poster. Upgrade its private learning facts,
record what content, Skills, tools and review evidence were actually available,
do not change the Demo or final MP4, and validate the result.
```

不给 Agent 设计文档、实施计划、预期字段或诊断。验收：Agent 找到提取/learning references；使用 backfill；六种 sidecar齐全；以下命令 `ok=true`：

```bash
PATH=/opt/homebrew/bin:$PATH python3 \
  "$SKILL_ROOT/scripts/validate_run.py" \
  --repo /tmp/tutorial-learning-memory-forward-poster \
  --run-id 2026-07-11-poster-wall \
  --require-learning-memory --ffprobe on --json
```

### Task 9: 完整审计、独立 Review、合入与安装

**Files:**
- Verify all task files
- Private only: `skills/tutorial-to-hyperframes-demo/experience.local.md`

- [ ] **Step 1: 更新本机职责边界**

只在被忽略的 `experience.local.md` 说明：机器事实留在本文件；run 事实在目标 `.learning/runs/`；行为 memory 在 `/local/`。不写具体 memory 或秘密。

- [ ] **Step 2: 运行完整验证**

```bash
python3 -m unittest discover -s skills/tutorial-to-hyperframes-demo/tests -p 'test_*.py' -v
python3 -m py_compile skills/tutorial-to-hyperframes-demo/scripts/*.py
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skills/tutorial-to-hyperframes-demo
git diff --check
```

- [ ] **Step 3: 精确暂存与 index 隐私审计**

只暂存本设计、计划和 `skills/tutorial-to-hyperframes-demo/`。运行 `audit_staged.py`，必须非空且零 findings；主仓库 V2 哲学未跟踪文件、`local/`、`experience.local.md`、run sidecar 均不得进入 index。

- [ ] **Step 4: 两类独立 Review**

- 安全 Reviewer：检查路径/秘密/私有素材、伪造 passed evidence、legacy 漂移、backfill 越权；
- Skill Reviewer：检查薄入口、人类 SOP、运行清单、候选分流、无空 memory、无重型事件数据库和 V2 一层导航。

问题修复后重复测试、审计和 Review，直至 APPROVED。

- [ ] **Step 5: 精确提交 Review 修正**

Review 全绿后再次运行 staged audit，然后提交尚未进入先前任务提交的设计、计划与修正：

```bash
git add docs/superpowers/specs/2026-07-11-tutorial-memory-ledger-design.md \
  docs/superpowers/plans/2026-07-11-tutorial-learning-memory-v2.md \
  skills/tutorial-to-hyperframes-demo
git commit -m "feat(skill): add v2 tutorial learning loop"
```

若 index 为空，必须证明所有目标改动已在前面精确提交；不得制造空提交。

- [ ] **Step 6: 合入主仓库并刷新安装**

重新读取主仓库状态，只 cherry-pick 本分支提交。随后：

```bash
j-skills link "$HOME/jacky-github/jacky-skills/skills/tutorial-to-hyperframes-demo" --json
j-skills install tutorial-to-hyperframes-demo -g -e codex,claude-code --json
```

验证两个环境 symlink 指向主仓库；使用 ARM64 Node。未要求时不 push。
