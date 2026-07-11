# Browser Control Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 DevTools Plugin 中新增 `browser-control` 薄路由 Skill，以登录态为第一路由键选择 Chrome DevTools 或 WebAccess，并用 Markdown + Node.js 记录真实能力与复盘。

**Architecture:** `SKILL.md` 只负责入口、判断、委派、验收和写回；`references/capabilities.md` 保存稳定能力地图。每次真实运行写入 gitignored 的 `runs.local/<run-id>.md`，`experience.local.md` 只保存本机能力卡和经晋升经验；`usage-ledger.mjs` 初始化、校验和归档 Markdown，不复制浏览器实现。

**Tech Stack:** Agent Skills Markdown、Node.js 18+ ESM 标准库、Node test runner、Claude Plugin manifests、Python 仓库审计。

---

## 执行说明

- 当前 checkout 有与本任务直接相关的未提交 Plugin/README/marketplace 重构，不能从 `HEAD` 新建 worktree 后丢失真实基线；实施留在当前 checkout。
- 未经用户明确要求，不创建 commit、不 push。每个任务以测试绿灯和限定 diff 作为检查点。
- 所有编辑使用小范围补丁，保留无关用户改动。

## 文件职责

**新增：**

- `plugins/dev-tools/browser-control/SKILL.md`：唯一入口、登录态路由、运行闭环、复盘与晋升规则。
- `plugins/dev-tools/browser-control/agents/openai.yaml`：UI 名称、简短描述和默认调用提示。
- `plugins/dev-tools/browser-control/references/capabilities.md`：稳定能力槽位、候选、探测、契约和 fallback。
- `plugins/dev-tools/browser-control/scripts/usage-ledger.mjs`：Markdown 复盘账本 CLI。
- `plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs`：账本、安全、路径、Markdown 扩展和静态路由契约测试。
- `plugins/dev-tools/browser-control/.gitignore`：忽略 `runs.local/` 与 `experience.local.md`。

**修改：**

- `plugins/dev-tools/web-connect/SKILL.md`：收紧为登录态/当前页/配置讲解执行层；修复 `/new` POST body。
- `plugins/dev-tools/web-connect/references/providers.md`：同步 WebAccess 2.5.3 `/new` 与 `/navigate` 方法。
- `plugins/dev-tools/web-search/SKILL.md`：Layer 4 委派 `browser-control`，不再自行选择浏览器 provider。
- `plugins/dev-tools/.claude-plugin/plugin.json`：增加 Skill，版本升级到 `2.6.0`。
- `.claude-plugin/marketplace.json`：同步 DevTools `2.6.0`。
- `README.md`：同步版本和 Skill 列表。
- `.github/workflows/validate.yml`：增加三平台 Node 18+ 账本测试 job。

## Chunk 1: Skill、Markdown 账本与集成

### Task 0: 保存重叠文件的实施前基线

**Files:**
- Read-only snapshot: `README.md`
- Read-only snapshot: `plugins/dev-tools/.claude-plugin/plugin.json`
- Read-only snapshot: `plugins/dev-tools/web-connect/SKILL.md`
- Read-only snapshot: `plugins/dev-tools/web-connect/references/providers.md`
- Read-only snapshot: `plugins/dev-tools/web-search/SKILL.md`
- Read-only snapshot: `.claude-plugin/marketplace.json`
- Read-only snapshot: `.github/workflows/validate.yml`

- [ ] **Step 1: 在仓库外保存文件副本、diff 与哈希**

使用 `mktemp -d /tmp/jacky-skills-browser-control-baseline.XXXXXX` 创建只读基线目录。将上述存在的文件按相对路径复制进去，同时保存：

```bash
git diff --binary -- README.md plugins/dev-tools/.claude-plugin/plugin.json plugins/dev-tools/web-connect/SKILL.md plugins/dev-tools/web-connect/references/providers.md plugins/dev-tools/web-search/SKILL.md
shasum -a 256 README.md plugins/dev-tools/.claude-plugin/plugin.json plugins/dev-tools/web-connect/SKILL.md plugins/dev-tools/web-connect/references/providers.md plugins/dev-tools/web-search/SKILL.md .claude-plugin/marketplace.json .github/workflows/validate.yml
```

Expected: 基线位于 `/tmp`，仓库状态不变；未跟踪的 marketplace/workflow 也有完整副本和哈希。

- [ ] **Step 2: 记录基线目录并在后续逐文件比对**

在当前任务上下文保存 `BASELINE_DIR` 的实际值。最终审计时分别比较原副本、实施后文件和本任务意图，不能只依赖 `git diff` 判断原有内容。

### Task 1: 用官方 skill-creator 初始化目录

**Files:**
- Create: `plugins/dev-tools/browser-control/`

- [ ] **Step 1: 运行官方初始化器**

```bash
python3 "$HOME"/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  browser-control \
  --path plugins/dev-tools \
  --resources scripts,references \
  --interface 'display_name=AI 浏览器操控' \
  --interface 'short_description=按登录态选择浏览器能力，并记录实际路由结果与复盘经验' \
  --interface 'default_prompt=使用 $browser-control 选择合适的浏览器能力并完成这个网页任务。'
```

Expected: 创建 `SKILL.md`、`agents/openai.yaml`、`scripts/` 和 `references/`，不创建 examples/assets。

- [ ] **Step 2: 验证初始化结果未污染其他路径**

```bash
git status --short plugins/dev-tools/browser-control
```

Expected: 仅出现新目录文件。

### Task 2: 先写 Markdown 账本失败测试

**Files:**
- Create: `plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs`
- Test: `plugins/dev-tools/browser-control/scripts/usage-ledger.mjs`

- [ ] **Step 1: 写 Node test runner 测试**

测试必须从脚本导入以下接口：

```js
import {
  buildRunTemplate,
  finalizeRun,
  isPathInside,
  parseProbeStatuses,
  resolveSkillRoot,
  validateRunId,
  validateRunMarkdown,
} from "../scripts/usage-ledger.mjs";
```

最小用例：

```js
test("available 候选上的任务失败不会被写成 missing", async () => {
  const markdown = validRun({ probeStatus: "available", taskResult: "failed" });
  const result = validateRunMarkdown(markdown);
  assert.equal(result.probes.get("chrome-devtools").status, "available");
  assert.equal(result.taskResult, "failed");
});
```

同时覆盖：

- `init` 生成必需标题，且不会生成空 `experience.local.md`；
- `available | degraded | missing | not_checked`；
- 缺标题、重复必需标题、非法枚举、悬空证据引用；
- 额外标题/短项目可通过；
- fenced code、HTML、HTTP(S) URL、JWT、Authorization、Cookie、超长行与超大文件失败；
- 非法 `run_id`、`../`、绝对路径、Windows drive、UNC 逃逸失败；
- LF/CRLF 均可解析并保持换行风格；
- 状态哨兵缺失、重复、嵌套、交叉、错配时 fail closed；
- 更新一个能力卡时哨兵外字节不变；
- 多下游链和 fallback 都保留；
- 从非仓库 CWD 解析到脚本自身 Skill 根目录。

- [ ] **Step 2: 运行测试确认 RED**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

Expected: FAIL，原因是 `usage-ledger.mjs` 尚未导出所需实现。

### Task 3: 实现 Node.js Markdown 账本

**Files:**
- Create: `plugins/dev-tools/browser-control/scripts/usage-ledger.mjs`
- Modify: `plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs`

- [ ] **Step 1: 实现路径与输入硬边界**

实现并导出：

```js
export const RUN_ID_RE = /^[a-z0-9](?:[a-z0-9-]{0,62})$/;

export function resolveSkillRoot(metaUrl = import.meta.url) {
  return path.resolve(path.dirname(fileURLToPath(metaUrl)), "..");
}

export function validateRunId(runId) {
  if (!RUN_ID_RE.test(runId)) throw new Error("非法 run_id");
  return runId;
}
```

`isPathInside` 同时支持注入 `path.posix` 与 `path.win32` 测试；CLI 不接受外部 root，只从 `import.meta.url` 定位。

- [ ] **Step 2: 实现 Markdown 模板与解析器**

必需二级标题：

```js
const REQUIRED_SECTIONS = [
  "任务",
  "候选探测",
  "路由决定",
  "实际使用的 Skills",
  "证据",
  "复盘",
];
```

解析规则：标题 + 单行项目；额外标题与项目允许；必需标题不得重复。候选三级标题下必须有状态、检查时间、状态证据引用；任务结果与候选状态分别解析。

- [ ] **Step 3: 实现确定性安全扫描**

限制：64 KiB、单行项目 500 字符、“证明”240 字符；拒绝 fenced code、原始 HTML、HTTP(S) URL、JWT、Cookie/Authorization/secret/password/token 等模式。允许 `run://` 和运行目录相对引用。

脚本输出必须明确：模式扫描不代替 AI 的语义脱敏。

- [ ] **Step 4: 实现 experience.local.md 能力卡更新**

哨兵格式固定：

```markdown
<!-- browser-control:status:<candidate-id>:start -->
### <candidate-id>

- 状态：available
- 检查时间：<ISO-8601>
- 状态证据引用：runs.local/<run-id>.md#E0
<!-- browser-control:status:<candidate-id>:end -->
```

`not_checked` 不更新旧卡；其他状态只从“候选探测”获取。缺失、重复、嵌套、交叉或错配哨兵时停止。新文件只有在存在可验证状态时创建，并包含“当前能力地图”和“经晋升经验”两个语义入口。

- [ ] **Step 5: 实现 CLI**

```text
node usage-ledger.mjs init <run-id>
node usage-ledger.mjs validate <run-id>
node usage-ledger.mjs finalize <run-id>
```

`init` 先在目标目录写入并同步临时文件，再用同目录 hard-link 排他发布到最终路径；目标已存在时链接失败，绝不覆盖首份内容，随后清理临时文件。`finalize` 使用临时文件 + 原子替换更新已存在文件，并添加锁定标记防止重复归档。

增加两个并发 `init` 的测试：只允许一个成功，另一个必须收到“已存在”，最终文件内容完整且与成功调用一致。

- [ ] **Step 6: 运行测试确认 GREEN**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

Expected: 全部 PASS。

### Task 4: 编写薄路由 Skill 与稳定能力地图

**Files:**
- Modify: `plugins/dev-tools/browser-control/SKILL.md`
- Create: `plugins/dev-tools/browser-control/references/capabilities.md`
- Create: `plugins/dev-tools/browser-control/.gitignore`
- Verify: `plugins/dev-tools/browser-control/agents/openai.yaml`

- [ ] **Step 1: 在测试中加入路由静态契约**

断言：

- `SKILL.md` frontmatter 只有 `name` 与 `description`；
- description 覆盖通用浏览器操控、静态页、当前登录页和工具选择；
- `SKILL.md` 明确“唯一入口”“登录态才用 WebAccess”“无登录态用 Chrome DevTools”；
- `references/capabilities.md` 定义三个能力槽位与跨槽位禁止降级；
- `.gitignore` 忽略 `runs.local/` 和 `experience.local.md`。

- [ ] **Step 2: 运行静态契约确认 RED**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

Expected: 路由契约测试 FAIL。

- [ ] **Step 3: 写 `SKILL.md`**

保持在 500 行内，只写：

1. 入口与边界；
2. 登录态第一路由键；
3. 按需读取单个能力槽位；
4. 最小探测与同槽位 fallback；
5. 调用下游 Skill 后的证据验收；
6. 每次运行的 Markdown 复盘；
7. 本机经验晋升与隐私规则；
8. 最小完成清单。

不得复制 Chrome DevTools/WebAccess 操作命令，不得把 SPA/JS 渲染自动等同于 WebAccess。

- [ ] **Step 4: 写 `references/capabilities.md`**

能力槽位：

```text
browser_without_existing_login
  candidates: chrome-devtools -> browser:control-in-app-browser
  forbid: WebAccess fallback

browser_with_existing_login
  candidates: web-access:web-access
  adapter: dev-tools:web-connect（仅配置讲解/当前标签页）

web_information_discovery
  delegate: dev-tools:web-search
```

每个槽位给出适用条件、候选顺序、最小 probe、输入输出契约、fallback 和验收证据。

- [ ] **Step 5: 写 `.gitignore` 并复核 UI 元数据**

```gitignore
runs.local/
experience.local.md
```

`agents/openai.yaml` 必须使用：

```yaml
interface:
  display_name: "AI 浏览器操控"
  short_description: "按登录态选择浏览器能力，并记录实际路由结果与复盘经验"
  default_prompt: "使用 $browser-control 选择合适的浏览器能力并完成这个网页任务。"
```

- [ ] **Step 6: 运行 Skill 自测与官方校验**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
python3 "$HOME"/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/dev-tools/browser-control
```

Expected: PASS；frontmatter、名称与目录一致。

### Task 5: 收口现有浏览器入口

**Files:**
- Modify: `plugins/dev-tools/web-connect/SKILL.md:1-4,130-160`
- Modify: `plugins/dev-tools/web-connect/references/providers.md:64-87`
- Modify: `plugins/dev-tools/web-search/SKILL.md:254-289`

- [ ] **Step 1: 先增加跨 Skill 静态契约测试**

断言：

- `web-connect` description 写明仅由 `browser-control` 在登录态/当前页/配置讲解场景委派；
- `web-search` Layer 4 调用 `browser-control`，不再自行默认 WebAccess/OpenCLI browser；
- `web-connect` 与 providers reference 不再出现 `/new?url=` 或 `/navigate?...&url=`。

- [ ] **Step 2: 运行确认 RED**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

Expected: 跨 Skill 契约 FAIL。

- [ ] **Step 3: 收紧 `web-connect` 并修复 WebAccess 2.5.3 API**

`/new` 和 `/navigate` 改为 POST body：

```bash
curl -s -X POST --data-raw '<URL>' http://localhost:3456/new
curl -s -X POST --data-raw '<URL>' "http://localhost:3456/navigate?target=<ID>"
```

保留当前工作树已有的 WebAccess Skill 路径探测改动。

- [ ] **Step 4: 修改 `web-search` Layer 4**

保留 Layer 1-3 的搜索/读取职责；需要浏览器时统一委派 `browser-control`：已有登录态 → WebAccess，无登录态交互 → Chrome DevTools。删去本层自行维护的 provider Trade-off 与默认建议。

- [ ] **Step 5: 运行确认 GREEN**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
python3 -m unittest tests.test_execution_paths -v
```

Expected: PASS；若 `test_execution_paths` 的旧接口断言需要同步，只改与 WebAccess 2.5.3 契约直接相关的期望。

### Task 6: Plugin 版本、README 与跨平台 CI

**Files:**
- Modify: `plugins/dev-tools/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`
- Modify: `.github/workflows/validate.yml`

- [ ] **Step 1: 先运行分发测试并增加 CI 静态契约，确认 RED**

```bash
python3 -m unittest tests.test_install_contract -v
```

Expected: 新 Skill 已存在但 manifest/README 尚未声明，因此分发一致性测试 FAIL。

在 `usage-ledger.test.mjs` 增加静态契约：workflow 必须包含 `ubuntu-latest`、`macos-latest`、`windows-latest`、`actions/setup-node@v4`、Node 18 和明确的账本测试路径。再次运行 Node 测试，Expected: CI 契约 FAIL。

- [ ] **Step 2: 更新 DevTools 清单**

- version: `2.6.0`；
- skills 添加 `./browser-control/`；
- description 增加浏览器操控语义。

- [ ] **Step 3: 同步根 marketplace 与 README**

- marketplace DevTools version `2.6.0`；
- README DevTools 行 version `2.6.0`；
- Skills 列表增加 `browser-control`。

- [ ] **Step 4: 增加独立 Node CI job**

```yaml
  browser-control:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

不得改写现有 Python/Bash job 的平台边界。

- [ ] **Step 5: 运行分发一致性与 CI 契约测试确认 GREEN**

```bash
python3 -m unittest tests.test_install_contract -v
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
```

Expected: Plugin manifest、marketplace、README 与实际 Skill 一致。

### Task 7: 全量验证、Forward Test 与本机安装

**Files:**
- Verify all files above
- Runtime-only: `plugins/dev-tools/browser-control/runs.local/`
- Runtime-only: `plugins/dev-tools/browser-control/experience.local.md`

- [ ] **Step 1: 运行仓库级验证**

```bash
node --test plugins/dev-tools/browser-control/tests/usage-ledger.test.mjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
```

Expected: 全部通过；若存在与本任务无关的基线失败，保留完整错误并证明本任务定向测试已通过，不顺手改无关文件。

- [ ] **Step 2: 验证 Node 为原生 ARM64**

```bash
node -p '`${process.platform} ${process.arch} ${process.version}`'
```

Expected on current machine: `darwin arm64 v18+`。

- [ ] **Step 3: 独立 Forward Test 八个路由与负向场景**

使用新上下文、只提供 Skill 路径与用户式请求，逐场景保存路由、Skill 链、结果和证据摘要：

1. 本地静态 HTML / 无登录态；
2. 公开 SPA / 无登录态；
3. 内部系统 / 需要现有登录态；
4. 当前登录页配置讲解；
5. 仅搜索信息；
6. Chrome DevTools 不可用，验证只走同能力槽 fallback，不切 WebAccess；
7. 下游自报成功但没有独立证据，验证结果不能记为 passed；
8. 主候选失败后使用 fallback，验证适配层、失败主候选与 fallback 的完整链路都被保留。

检查：路由是否正确、是否只加载相关下游、是否生成每个实际 Skill 的能力/结果/证据复盘。不得向测试 Agent 透露预期工具答案；测试汇总必须列出八项各自的 pass/fail 与证据引用。

- [ ] **Step 4: 本机链接并安装**

```bash
j-skills link "$JACKY_SKILLS_DIR/plugins/dev-tools/browser-control"
j-skills install browser-control -g --env claude-code,codex
```

Expected: 非交互完成，Claude Code 与 Codex 均能发现 `browser-control`。

- [ ] **Step 5: 安装后 smoke test**

```bash
test -L "$HOME/.j-skills/linked/browser-control"
test -f "$HOME/.codex/skills/browser-control/SKILL.md"
test -f "$HOME/.claude/skills/browser-control/SKILL.md"
```

Expected: 三项返回 0；链接指向当前仓库 Skill。

- [ ] **Step 6: 最终限定 diff 审计**

```bash
git diff --check
git status --short
git diff -- plugins/dev-tools/browser-control plugins/dev-tools/web-connect plugins/dev-tools/web-search plugins/dev-tools/.claude-plugin/plugin.json .claude-plugin/marketplace.json README.md .github/workflows/validate.yml
```

Expected: 仅出现本任务文件与原有相关用户改动的叠加；无 `runs.local/`、`experience.local.md` 或敏感内容进入共享 diff。

- [ ] **Step 7: 与实施前基线逐文件复核**

使用 Task 0 的 `BASELINE_DIR` 比较七个重叠文件。确认每个文件只增加本计划声明的路由、版本、API 或 CI 变化；原有未提交内容逐字保留。重新计算哈希并将“原有内容保留 + 本任务增量”记录在最终验收摘要中。
