# Harness Ops Consolidation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将工程与第三方 Skill 的长期运行经验统一收敛到顶层 `harness/`，并以 `<target>-ops` 作为唯一命名规范。

**Architecture:** `harness/` 是仓库级经验驾驭层，负责放置可安装的 Ops Skills；每个 `<target>-ops` 用 `SKILL.md` 保存可分享协议，用 gitignored 的 `experience.local.md` 保存本机事实。根目录规范负责路由新建请求，`harness/CLAUDE.md` 负责该分类的详细创建、迁移和写回约束。

**Tech Stack:** Markdown、Agent Skills、Bash、Python unittest、python-docx、LibreOffice 渲染

---

## Chunk 1: 目录与 Skill 迁移

### Task 1: 建立 Harness 分类规则

**Files:**
- Create: `harness/CLAUDE.md`
- Modify: `CLAUDE.md`

- [x] 定义 `harness` 与 `ops` 的语义边界。
- [x] 规定用户说“创建 harness skill”时默认创建 `harness/<target>-ops/`。
- [x] 规定通用规则进入 `SKILL.md`、本机事实进入 `experience.local.md`。
- [x] 规定第三方 Skill 最佳实践与水土不服经验由配套 Ops Skill 承载。

### Task 2: 迁移现有 Harness/Ops Skills

**Files:**
- Move: `skills/happy-ops/` -> `harness/happy-ops/`
- Move: `skills/opencli-harness/` -> `harness/opencli-ops/`
- Move: `skills/hyperframes-harness/` -> `harness/hyperframes-ops/`
- Modify: migrated `SKILL.md` files and internal references

- [x] 原样迁移所有 gitignored 本机经验和配套资源。
- [x] 将目录名、frontmatter 名称、触发词和自引用统一为 `*-ops`。
- [x] 强化 `hyperframes-ops` 的第三方 Skill 适配层职责。
- [x] 保持 `harness-benchmark` 等评测 Skill 原位不动。

## Chunk 2: 仓库发现、文档与验证

### Task 3: 让仓库工具识别 Harness Skills

**Files:**
- Modify: `install.sh`
- Modify: `scripts/audit_skills.py`
- Modify: `tests/test_install_contract.py`
- Modify: `tests/test_audit_skills.py`

- [x] 让安装器扫描 `plugins/`、`skills/`、`harness/`。
- [x] 让统一审计把 `harness/` 视为正式 Skill 根目录。
- [x] 增加 Harness 发现和命名契约测试。

### Task 4: 更新仓库说明和跨 Skill 引用

**Files:**
- Modify: `README.md`
- Modify: `skills/tutorial-to-hyperframes-demo/SKILL.md`
- Modify: `docs/新机器-skill-配置清单.md`
- Modify: `docs/bootstrap-new-machine.sh`
- Modify: `docs/自进化-skill-协议规范.md`
- Modify: `docs/superpowers/specs/2026-07-11-tutorial-to-hyperframes-demo-design.md`

- [x] 更新所有活跃引用和安装示例。
- [x] 将 Ops Skills 从普通独立 Skill 表移动到 Harness Ops 表。

### Task 5: 生成设计理念 DOCX

**Files:**
- Create: `docs/Harness 与 Ops 设计理念.docx`
- Create temporarily: document builder and render QA artifacts outside final deliverables

- [x] 使用 `standard_business_brief` 预设和 `memo_masthead` 首屏结构生成文章。
- [x] 覆盖 Worktree、经验实时写回、分享边界和第三方 Skill 水土不服问题。
- [x] 渲染全部页面为 PNG 并逐页检查。

### Task 6: 验证

- [x] 运行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`。
- [x] 运行 `python3 scripts/audit_skills.py --scan-shared-content`。
- [x] 运行 `bash -n install.sh`。
- [x] 对三个迁移后的 Skill 运行官方 `quick_validate.py`。
- [x] 运行 `claude plugin validate --strict .`，若环境不可用则如实记录。
