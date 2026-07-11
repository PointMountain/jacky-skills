# Benchmark Skill Naming Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将所有以量化评分为核心职责的 Skill 统一迁移到 `xxx-benchmark` 命名，并把约定固化为仓库规则和测试。

**Architecture:** 以一份显式命名契约测试固定五个迁移目标，再逐层更新目录、frontmatter、触发词、调用方、Plugin manifest 和公开清单。业务产物中的 `score`、`rating` 与 rubric 术语不改，避免把 Skill 身份命名与领域数据模型混为一谈。

**Tech Stack:** Markdown/YAML frontmatter、Python `unittest`、Claude Code Plugin JSON、仓库审计脚本。

---

## Chunk 1: 命名契约与迁移

### Task 1: 建立失败的命名契约

**Files:**
- Create: `tests/test_benchmark_naming_contract.py`

- [x] 声明五组旧名称到新名称的映射。
- [x] 断言新目录存在、旧目录消失、frontmatter `name` 与新目录一致。
- [x] 断言 `CLAUDE.md` 包含评分型 Skill 必须使用 `-benchmark` 的规则。
- [x] 运行 `python3 tests/test_benchmark_naming_contract.py -v`，确认因新目录尚不存在而失败。

### Task 2: 迁移正式 Plugin Skills

**Files:**
- Rename: `plugins/evaluators/harness-evaluator/` → `plugins/evaluators/harness-benchmark/`
- Modify: `plugins/evaluators/harness-benchmark/SKILL.md`
- Modify: `plugins/evaluators/.claude-plugin/plugin.json`
- Rename: `plugins/obsidian-tools/ob-rate/` → `plugins/obsidian-tools/ob-benchmark/`
- Modify: `plugins/obsidian-tools/ob-benchmark/SKILL.md`
- Modify: `plugins/obsidian-tools/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

- [x] 更新目录、frontmatter、标题、触发词和示例命令。
- [x] 更新 Plugin manifest；两个 Plugin 均升级 PATCH 版本。
- [x] 同步根 Marketplace 与 README 的版本和 Skill 列表。

### Task 3: 迁移实验性与归档 Skills

**Files:**
- Rename: `labs/web-flow/web-flow-review/` → `labs/web-flow/web-flow-benchmark/`
- Modify: `labs/web-flow/` 下所有调用引用与测试契约。
- Rename: `archived/tw-scorer/` → `archived/tw-benchmark/`
- Modify: `archived/tw-planner/SKILL.md`
- Modify: `archived/tw-generator/SKILL.md`
- Rename: `archived/agent-pipeline-score/` → `archived/agent-pipeline-benchmark/`
- Modify: `archived/agent-pipeline/SKILL.md` 及其 references。

- [x] 更新目录、frontmatter、触发词、角色名和编排调用名。
- [x] 保留 `score.json`、评分维度、工作目录等领域术语。

### Task 4: 固化仓库规则

**Files:**
- Modify: `CLAUDE.md`

- [x] 在 Skill 创建与修改规范中增加 `-benchmark` 命名边界。
- [x] 明确目录、frontmatter、触发词与调用引用必须同步迁移。

### Task 5: 验证

**Files:**
- Test: `tests/test_benchmark_naming_contract.py`

- [x] 运行命名契约测试并确认通过。
- [x] 搜索五个旧 Skill 标识，确认运行时引用清零。
- [x] 运行全量测试：补齐 README 中遗漏的 `tutorial-to-hyperframes-demo` 后，31 项全部通过。
- [x] 运行 `python3 scripts/audit_skills.py --scan-shared-content`。
- [x] 运行 `bash -n install.sh` 和 `claude plugin validate --strict .`。
- [x] 不提交、不推送，保留工作树中与本任务无关的既有改动。
