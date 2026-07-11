# Philosophy Docs Governance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将自进化设计思考整理为 `docs/philosophy/` 下的 blog 风格主题，把 V1 协议归档，并建立严格的 docs 治理规则与统一 Agent 指令入口。

**Architecture:** `docs/philosophy/README.md` 是面向读者的唯一入口，复杂实现细节下沉到同主题的 `references/`；历史但仍可参考的 V1 内容进入 `docs/archive/`。`CLAUDE.md` 作为仓库规则源，根目录 `AGENTS.md` 通过相对软链接复用它。

**Tech Stack:** Markdown、Git、ripgrep、POSIX 软链接

**约束:** 当前工作树已有大量用户改动。只修改本计划列出的目标文件与搜索确认的旧链接引用；不回退、不覆盖、不暂存、不提交其他内容，且本任务不自动 commit。

---

## Chunk 1: 文档迁移、改写与治理入口

### Task 1: 记录基线并迁移主题细节

**Files:**
- Move: `docs/self-evolving-skill-v2/external-skills.md` → `docs/philosophy/references/external-skills.md`
- Move: `docs/self-evolving-skill-v2/human-sop.md` → `docs/philosophy/references/human-sop.md`
- Move: `docs/self-evolving-skill-v2/memory-and-scoring.md` → `docs/philosophy/references/memory-and-scoring.md`
- Move: `docs/self-evolving-skill-v2/progressive-loading.md` → `docs/philosophy/references/progressive-loading.md`
- Move: `docs/self-evolving-skill-v2/yaml-contracts.md` → `docs/philosophy/references/yaml-contracts.md`

- [ ] **Step 1: 记录实施前工作树基线**

Run:

```bash
git status --short
git diff -- CLAUDE.md docs/自进化-skill-设计哲学-v2.md docs/自进化-skill-协议规范.md docs/self-evolving-skill-v2
shasum -a 256 docs/self-evolving-skill-v2/*.md
```

Expected: 输出当前已有改动和五个源文件哈希；后续必须保留这些内容，并把哈希输出留在任务执行记录中供迁移后逐项核对。本轮已知上述新文档属于未跟踪文件，不能用 HEAD 内容覆盖它们。

- [ ] **Step 2: 找出旧路径引用并检查引用文件现有 diff**

Run:

```bash
rg -n '自进化-skill-设计哲学-v2|self-evolving-skill-v2|自进化-skill-协议规范' . \
  -g '!node_modules' -g '!.git' -g '!docs/superpowers/specs/**' -g '!docs/superpowers/plans/**'
```

Expected: 至少命中旧主文、V1 归档文及它们之间的链接；若命中其他文件，编辑前对每个文件单独执行 `git diff -- <path>`。

- [ ] **Step 3: 迁移五个细节文档**

使用补丁保留文件正文，将五个文件移动到 `docs/philosophy/references/`。只修正因新目录层级造成的相对链接，不改写细节内容。

- [ ] **Step 4: 验证细节迁移完整**

Run:

```bash
find docs/philosophy/references -maxdepth 1 -type f -print | sort
test "$(find docs/philosophy/references -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')" = 5
for file in external-skills.md human-sop.md memory-and-scoring.md progressive-loading.md yaml-contracts.md; do test -f "docs/philosophy/references/$file"; done
shasum -a 256 docs/philosophy/references/*.md
test ! -d docs/self-evolving-skill-v2
```

Expected: 精确五个文件全部存在，旧目录不存在；目标文件按文件名对应的 SHA-256 与 Step 1 记录的源文件完全一致。

### Task 2: 改写 Philosophy 主文章

**Files:**
- Move and rewrite: `docs/自进化-skill-设计哲学-v2.md` → `docs/philosophy/README.md`

- [ ] **Step 1: 写入 blog 风格主文章**

文章使用第一人称，标题使用 `Skills 设计哲学`。正文必须完整表达以下内容：

1. 我为何不再从模板和文件结构开始设计 Skill，而先观察人真实如何完成任务。
2. 观察、行动与验证为什么构成同一个闭环。
3. `SKILL.md` 为什么应是地图和约束入口，而不是百科全书。
4. 复盘、有限评分、渐进加载和可审计事实链分别解决什么真实问题。
5. 自进化不等于保存原始思维过程，也不等于允许 Agent 随意改写自身。
6. 简单 Skill 不需要复杂架构；本机环境事实和少量已验证经验继续使用 `experience.local.md` 即可。
7. 复杂度只在真实知识、阶段与问题簇生长后增加。

文末以“继续展开”链接到 `references/` 下五篇细节文档。正文不使用“当前主规范”“V2 全面替代 V1”等制度化措辞。

- [ ] **Step 2: 检查主文章语气与入口链接**

Run:

```bash
rg -n '^# |^## |experience\.local\.md|references/' docs/philosophy/README.md
rg -n '当前主规范|V2 面向所有|必须统一接入' docs/philosophy/README.md
for file in external-skills.md human-sop.md memory-and-scoring.md progressive-loading.md yaml-contracts.md; do rg -F "references/$file" docs/philosophy/README.md >/dev/null; done
```

Expected: 第一条命令能看到标题、核心章节、轻量方案和五个细节链接；第二条命令无输出；循环确认五个细节入口逐一存在。

### Task 3: 归档 V1 协议

**Files:**
- Move: `docs/自进化-skill-协议规范.md` → `docs/archive/自进化-skill-协议规范.md`

- [ ] **Step 1: 移动 V1 文档并更新顶部状态**

保留正文历史内容，只把顶部说明改为“历史归档”：明确这是一套仍可用于简单、本机经验场景的轻量方法，但不再是仓库当前主题入口；主入口链接改为 `../philosophy/README.md`。

- [ ] **Step 2: 验证归档路径和链接**

Run:

```bash
test -f docs/archive/自进化-skill-协议规范.md
test ! -e docs/自进化-skill-协议规范.md
rg -n '历史归档|\.\./philosophy/README\.md|experience\.local\.md' docs/archive/自进化-skill-协议规范.md
```

Expected: 新文件存在、旧文件不存在，并命中归档状态、新入口和轻量经验方案。

### Task 4: 增加 docs 治理规则和 Agent 软链接

**Files:**
- Modify: `CLAUDE.md`
- Create symlink: `AGENTS.md` → `CLAUDE.md`

- [ ] **Step 1: 在 CLAUDE.md 增加 docs 治理章节**

在“核心结构”之后增加 `## Docs 内容治理`，明确：

- `docs/` 不是临时草稿区，新增内容必须有明确读者、长期价值和唯一归属。
- 当前有效的成体系主题使用简短英文 kebab-case 目录，以 `README.md` 作为唯一入口。
- 细节材料放入主题自身的 `references/`，不继续堆积在 `docs/` 根目录。
- 失效但仍有历史价值的文档进入 `docs/archive/`；没有保留价值的临时产物直接删除。
- 简单、本机私有、环境耦合的经验继续放在被忽略的 `experience.local.md`，不为形式升级成复杂协议。
- 新增、移动或归档后必须检查相对链接。

只做定点插入，保留 `CLAUDE.md` 现有未提交内容。

- [ ] **Step 2: 创建相对软链接**

Run:

```bash
ln -s CLAUDE.md AGENTS.md
```

Expected: 根目录此前不存在 `AGENTS.md`；命令成功创建相对软链接。

- [ ] **Step 3: 验证治理规则与软链接**

Run:

```bash
rg -n '^## Docs 内容治理|experience\.local\.md|docs/archive|references/' CLAUDE.md
test -L AGENTS.md
test "$(readlink AGENTS.md)" = 'CLAUDE.md'
cmp CLAUDE.md AGENTS.md
```

Expected: 治理规则命中；`AGENTS.md` 是值为 `CLAUDE.md` 的相对软链接，内容与源文件一致。

### Task 5: 修正引用并完成范围验证

**Files:**
- Modify only if discovered: repository files that still link to the old paths

- [ ] **Step 1: 修正搜索发现的有效旧链接**

只把有效链接替换为：

- 主文章：`docs/philosophy/README.md` 或按引用文件位置计算的相对路径。
- 细节文档：`docs/philosophy/references/<file>.md` 或对应相对路径。
- V1 归档：`docs/archive/自进化-skill-协议规范.md` 或对应相对路径。

不得改写引用文件的其他正文。

- [ ] **Step 2: 确认不再存在有效旧路径引用**

Run:

```bash
rg -n 'docs/自进化-skill-设计哲学-v2\.md|docs/self-evolving-skill-v2|\]\(self-evolving-skill-v2/|\]\(自进化-skill-设计哲学-v2\.md\)|\]\(自进化-skill-协议规范\.md\)' . \
  -g '!node_modules' -g '!.git' -g '!docs/superpowers/specs/**' -g '!docs/superpowers/plans/**'
```

Expected: 无输出。

- [ ] **Step 3: 检查所有新相对链接目标**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re

sources = sorted(Path("docs/philosophy").rglob("*.md"))
sources.append(Path("docs/archive/自进化-skill-协议规范.md"))
missing = []

for source in sources:
    text = source.read_text(encoding="utf-8")
    for raw_target in re.findall(r"\]\(([^)]+)\)", text):
        target = raw_target.strip().strip("<>").split("#", 1)[0]
        if not target or target.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        resolved = (source.parent / target).resolve()
        if not resolved.exists():
            missing.append(f"{source}: {raw_target}")

if missing:
    raise SystemExit("缺失相对链接目标:\n" + "\n".join(missing))

print(f"已验证 {len(sources)} 个 Markdown 文件的相对链接")
PY
```

Expected: exit code 0，输出已验证文件数量，且没有缺失链接报告。

- [ ] **Step 4: 对照 Git 基线审查最终范围**

Run:

```bash
git status --short
git diff -- CLAUDE.md AGENTS.md docs/philosophy docs/archive/自进化-skill-协议规范.md docs/自进化-skill-设计哲学-v2.md docs/自进化-skill-协议规范.md docs/self-evolving-skill-v2
```

Expected: 只包含计划内迁移、主文章改写、归档状态、CLAUDE 规则和软链接；仓库原有其他改动保持不变。由于源文档当前未跟踪，额外用 `find`、`sed` 和链接检查确认新文件内容。
