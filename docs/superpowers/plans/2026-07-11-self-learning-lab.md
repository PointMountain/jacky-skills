# Self Learning Lab Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `labs/self-learning` 实验域、增加动态调度入口，并把现有 HyperFrames 学习链路安全迁移为 `self-learning-hyperframes`。

**Architecture:** `self-learning` 只保存“固定意图、动态路径”的调度地图，不创建固定 Workflow；现有 HyperFrames Skill 作为完整实验链路保护性迁移。迁移采用先并存、验证新名称、再切除旧名称的顺序，避免当前 Claude Code/Codex 全局链接瞬间断裂。

**Tech Stack:** Markdown、YAML frontmatter、Python `unittest`（沿用仓库既有测试体系）、现有 Python 运行契约、`j-skills 0.1.0`、官方 `skill-creator`。

> **Git boundary:** 当前工作树包含大量与本任务无关的用户改动。只修改下列精确文件，不创建 worktree，不自动 commit 或 push；每个任务以定向测试和 `git diff -- <paths>` 代替提交步骤。

**Spec:** `docs/superpowers/specs/2026-07-11-self-learning-lab-design.md`

---

## Chunk 1: 实验入口与设计哲学

### Task 1: 用契约测试锁定最终结构

**Files:**
- Create: `tests/test_self_learning_lab_contract.py`
- Read: `README.md`
- Read: `labs/README.md`
- Read: `docs/philosophy/README.md`
- Read: `docs/philosophy/references/runtime-workflows.md`
- Read: `docs/philosophy/references/yaml-contracts.md`
- Read: `install.sh`

- [ ] **Step 1: 新增失败的结构契约测试**

使用仓库现有 Python `unittest`，避免引入第二套测试运行器：

```python
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "labs" / "self-learning"
OLD_NAME = "tutorial-to-hyperframes-demo"


def skill_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    return str(yaml.safe_load(frontmatter)["name"])


class SelfLearningLabContractTests(unittest.TestCase):
    def test_main_and_hyperframes_skill_names_match_directories(self) -> None:
        main = LAB_ROOT / "self-learning" / "SKILL.md"
        hyperframes = LAB_ROOT / "self-learning-hyperframes" / "SKILL.md"
        self.assertEqual(skill_name(main), "self-learning")
        self.assertEqual(skill_name(hyperframes), "self-learning-hyperframes")
        self.assertFalse((REPO_ROOT / "skills" / OLD_NAME).exists())

    def test_main_skill_keeps_workflow_dynamic(self) -> None:
        main_root = LAB_ROOT / "self-learning"
        text = (main_root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("固定意图，动态路径", text)
        self.assertIn("简单任务", text)
        self.assertIn("人工检查门", text)
        self.assertFalse((main_root / "workflow.yaml").exists())

    def test_public_surfaces_use_only_new_names(self) -> None:
        public_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "labs" / "README.md",
            LAB_ROOT / "README.md",
            LAB_ROOT / "self-learning" / "SKILL.md",
            LAB_ROOT / "self-learning-hyperframes" / "SKILL.md",
            LAB_ROOT / "self-learning-hyperframes" / "agents" / "openai.yaml",
        ]
        for path in public_files:
            with self.subTest(path=path):
                self.assertNotIn(OLD_NAME, path.read_text(encoding="utf-8"))

    def test_readmes_classify_self_learning_as_lab(self) -> None:
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        labs_readme = (REPO_ROOT / "labs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("[self-learning](./labs/self-learning)", root_readme)
        self.assertIn("[`self-learning`](./self-learning/)", labs_readme)
        independent_section = root_readme.split("## 独立 Skills", 1)[1].split(
            "## Harness Ops Skills", 1
        )[0]
        self.assertNotIn(OLD_NAME, independent_section)

    def test_labs_remain_outside_batch_install(self) -> None:
        install_script = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn('"$REPO_DIR/labs"', install_script)

    def test_philosophy_links_runtime_workflows(self) -> None:
        philosophy = (REPO_ROOT / "docs" / "philosophy" / "README.md").read_text(
            encoding="utf-8"
        )
        runtime_workflows = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "runtime-workflows.md"
        ).read_text(encoding="utf-8")
        yaml_contracts = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "yaml-contracts.md"
        ).read_text(encoding="utf-8")
        self.assertIn("固定意图，动态路径", philosophy)
        self.assertIn("references/runtime-workflows.md", philosophy)
        self.assertIn("用户指定的顺序", runtime_workflows)
        self.assertIn("未受硬约束的执行顺序", runtime_workflows)
        self.assertIn("开放任务", yaml_contracts)
        self.assertIn("Markdown", yaml_contracts)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认失败来自尚未创建的新 Lab**

Run:

```bash
python3 tests/test_self_learning_lab_contract.py -v
```

Expected: FAIL，首个失败为 `labs/self-learning/.../SKILL.md` 不存在；不得出现语法错误或导入错误。

- [ ] **Step 3: 检查本任务没有覆盖现有用户文件**

Run:

```bash
git status --short -- tests/test_self_learning_lab_contract.py
```

Expected: 只显示新测试文件。

### Task 2: 使用官方 skill-creator 建立总入口

**Files:**
- Create: `labs/self-learning/self-learning/SKILL.md`
- Create: `labs/self-learning/self-learning/agents/openai.yaml`
- Create: `labs/self-learning/README.md`
- Test: `tests/test_self_learning_lab_contract.py`

- [ ] **Step 1: 用官方脚本初始化最小 Skill**

Run:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/init_skill.py" \
  self-learning \
  --path labs/self-learning \
  --interface 'display_name=Self Learning' \
  --interface 'short_description=从视频、文章与链接中自主学习，并生成可运行、可复核的最小产物' \
  --interface 'default_prompt=Use $self-learning to study this source, research the techniques, and create the smallest useful verified artifacts.'
```

Expected: 创建 `SKILL.md` 与 `agents/openai.yaml`，不创建空 `scripts/`、`references/` 或 `assets/`。

- [ ] **Step 2: 把模板替换成高自由度调度地图**

`labs/self-learning/self-learning/SKILL.md` 的完整目标内容：

```markdown
---
name: self-learning
description: AI 自主阅读本地音视频、YouTube/B站/抖音链接、网页文章或用户文案，识别其中的技术知识与方法，按需扩展调研，并生成可验证的 Demo、教程、笔记等产物。用于从指定素材学习并做出成果、从主题自主寻找学习材料，或在复杂创作任务中按用户约束生成薄 Workflow；不用于模型训练、微调或自动创建 Agent Skill。
---

# Self Learning

把自己当作会寻找证据、建立理解并用产物证明理解的学习者。不要把摘要素材当成学会，也不要把模型记忆伪装成本轮调研事实。

## 固定意图，动态路径

保留用户给出的目标、强依赖、顺序约束、授权边界、人工检查门和验收条件。其余路径由当前任务决定：可以跳过、合并、重排、并行或增加动作，不套用统一阶段表。

- 简单、确定性的任务直接执行，不为形式生成 Workflow 文件。
- 复杂、长时间、无人值守、需要断点恢复或用户明确规定创作顺序的任务，先生成本轮薄 Workflow。
- 薄 Workflow 只需表达目标、约束、必需能力、检查门和验收；具体动作属于可修改的运行状态。
- 新证据改变原判断时允许调整路径，并说明依据；不能擅自删除用户固定的约束。

## 接收学习来源

接受本地音视频、用户文案、普通网页，以及 YouTube、B 站和抖音链接。用户只给主题时，可以自行寻找材料，但必须保留可追溯来源。

先确认来源可读取且用途获得授权。平台或网页不可访问时，探测当前可用的同类能力或请求用户提供本地材料，不静默退回模型记忆。

## 按需组合能力

从当前 Skill catalog 和工具面寻找需要的能力，而不是复制外部 Skill 的实现：

- 搜索、网页访问和平台发现；
- 视频摄取、转录和视觉观察；
- 技术资料调研与来源核对；
- Demo、文档、图片、动画或视频创作；
- 真实运行、观看、测试和结果验证。

在能力首次使用时验证其真实可用性。用户明确指定 GPT Image、HyperFrames 或其他具体能力时，把它视为硬依赖；不可用时在对应检查门报告，不擅自替换。

需要从教学音视频完整复现为 HyperFrames Demo 时，调用 `self-learning-hyperframes`。不要把该实验链路的固定阶段推广成所有 Self Learning 任务的默认答案。

## 选择最小有效产物

根据知识性质与用户目的选择 Demo、教程、笔记、代码、截图、渲染或测试。不是每次都要同时生成全部类型；产物必须足以证明当前理解并能被真实检查。

只有无人值守、耗时较长或需要恢复时，才把薄 Workflow 和状态写入目标工程的 gitignored 私有目录。普通任务使用当前 Agent 计划即可。

## 验收与停止

- 对照来源检查关键技术结论，不把推断冒充原文事实。
- 实际打开、运行、观看或测试产物，不接受工具自报成功。
- 用户预设人工检查门时必须停下；没有检查门时自主推进。
- 来源、强依赖或授权边界无法满足时明确阻断。
- 交付最终产物、来源证据、实际验证结果与仍存在的 residual。
```

- [ ] **Step 3: 新增 Lab 级 README**

`labs/self-learning/README.md` 必须说明：

```markdown
# self-learning（预览版）

`self-learning` 是一组探索“AI 如何从外部素材自主学习并创造可验证产物”的实验性 Skills。

这里的 Self Learning 指 Agent 阅读视频、文章或链接，识别技术知识与方法，按需继续调研，再生成 Demo、教程、笔记或其他可验证成果。它不表示模型训练、微调、修改模型权重或自动创建 Agent Skill。

## 包含的 Skill

| Skill | 作用 |
|---|---|
| `self-learning` | 总入口；固定用户意图，按任务动态生成或省略薄 Workflow，并自主组合当前可用能力 |
| `self-learning-hyperframes` | 现有教学音视频到 HyperFrames Demo 的完整实验链路 |

## 实验原则

- 简单任务允许直接执行，复杂任务才生成本轮薄骨架。
- 预设模板只固定强依赖、顺序、人工检查门与验收，不接管全部步骤。
- Demo、教程和笔记都是可选产物，不要求每次全部生成。
- 新的子 Skill 只从真实、重复出现的职责边界中生长，不预建空模块。

两个 Skill 位于 `labs/`，不会被仓库一键安装脚本自动安装；试用时需要显式链接。
```

- [ ] **Step 4: 验证官方 Skill 结构**

Run:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  labs/self-learning/self-learning
```

Expected: `Skill is valid!`

### Task 3: 把运行时薄 Workflow 写入仓库哲学

**Files:**
- Modify: `docs/philosophy/README.md`
- Create: `docs/philosophy/references/runtime-workflows.md`
- Modify: `docs/philosophy/references/yaml-contracts.md`
- Test: `tests/test_self_learning_lab_contract.py`

- [ ] **Step 1: 在哲学入口增加核心章节与导航**

在“SKILL.md 是地图”之后加入“Workflow 是运行时骨架”章节，必须明确：

```markdown
## Workflow 是运行时骨架

我不希望先替 Agent 写完一套固定剧本，再要求所有任务逐步照做。简单任务可以由 AI 直接判断和执行；复杂任务才需要一份薄 Workflow，用来固定人已经知道、但 AI 未必能自行推断的意图。

固定的是目标、强依赖、先后约束、授权边界、人工检查门和验收条件。动态的是具体动作、能力组合、并行关系和调整路径。新证据出现后，AI 可以修订本轮骨架，但不能擅自删除用户固定的约束。

模板不是完整 SOP。它只把类似“必须先用 GPT Image 生成原型，并在用户确认后才能实现”这样的创作意图交给 Agent；其余搜索、调研、工具选择和验证仍由 Agent 根据当前事实决定。
```

并在“继续展开”增加：

```markdown
- [运行时薄 Workflow：固定意图，动态路径](references/runtime-workflows.md)
```

- [ ] **Step 2: 新增一层 Markdown reference**

`runtime-workflows.md` 只展开以下语义，不定义 YAML schema：

```markdown
# 运行时薄 Workflow：固定意图，动态路径

> Workflow 的职责是保存本轮不可丢失的意图与边界，不是替 Agent 穷举执行步骤。

## 什么时候不需要 Workflow

当目标明确、动作短、可逆且不需要跨阶段协调时，让 AI 直接执行。不要为了结构完整制造空计划、状态目录或交接文件。

## 什么时候生成薄骨架

长时间、无人值守、需要恢复、存在多个能力依赖，或用户明确规定创作顺序时，先生成本轮行动骨架。骨架最少回答：目标是什么、哪些约束不能改变、必须具备哪些能力、何时停下来确认、什么事实证明完成。

## 固定与动态的边界

固定：用户目标、指定能力、用户指定的顺序、真实依赖、授权边界、人工检查门、验收条件。

动态：具体步骤、工具候选、步骤数量、未受硬约束的执行顺序与并行关系、产物组合，以及新证据出现后的调整。用户指定的顺序和真实依赖属于固定边界。

“读取、调研、创作、验证”只是可能出现的能力，不是必须依次经过的通用阶段。AI 可以跳过、合并、重排或增加动作。

## 模板只表达意图

模板适合保存 AI 难以自行推断的强依赖和观看节点。例如视觉优先模板可以要求：必须使用 GPT Image 生成原型；原型必须先让用户查看；确认后才能实现。模板不应继续规定如何搜索参考、生成几版或怎样编码。

## 运行中如何修订

当前证据优先于开局设想。AI 可以修改动态路径，但应说明触发变化的证据和影响；用户固定的约束只能由用户修改。范围实质变化、强依赖不可用或缺少外部写入授权时必须停下。

## 保存边界

普通任务使用当前 Agent 计划即可。只有无人值守、耗时较长或需要断点恢复时，才把骨架和状态写入 gitignored 私有运行目录。稳定模板与本轮运行状态必须分开。

## 反模式

- 把常见行为写成所有任务必经的固定阶段；
- 用 `workflow.yaml` 重建工作流引擎；
- 简单任务也强制生成计划文件；
- 借“AI 自主决定”删除用户指定的工具或人工检查门；
- 遇到新证据仍机械执行开局步骤。
```

- [ ] **Step 3: 收窄 YAML reference 的适用边界**

把 `yaml-contracts.md` 的 `workflow.yaml` 章节完整替换为以下边界说明：

```markdown
## `workflow.yaml` 的例外边界

不要默认用 YAML 描述工作流。开放任务的本轮薄 Workflow 优先使用 Agent 计划或 Markdown，只保存目标、约束、必需能力、人工检查门和验收条件，不预建固定阶段状态机。

只有同时满足以下条件时才使用 `workflow.yaml`：

1. 固定阶段已经由真实 SOP 反复验证；
2. 存在确定性机器解析、跨进程交换或 schema 校验需求；
3. 普通 Markdown 无法可靠表达或校验该需求。

即使使用 YAML，也只保存稳定、机器需要的事实；语义解释、判断边界和本轮可调整路径仍留在 Markdown 或 Agent 计划中。
```

- [ ] **Step 4: 运行哲学契约测试**

Run:

```bash
python3 tests/test_self_learning_lab_contract.py \
  SelfLearningLabContractTests.test_philosophy_links_runtime_workflows \
  -v
```

Expected: PASS。

---

## Chunk 2: HyperFrames 链路保护性迁移

### Task 4: 先复制新链路，再迁移公开身份与持久标记

**Files:**
- Copy: `skills/tutorial-to-hyperframes-demo/` → `labs/self-learning/self-learning-hyperframes/`
- Modify: `labs/self-learning/self-learning-hyperframes/SKILL.md`
- Modify: `labs/self-learning/self-learning-hyperframes/agents/openai.yaml`
- Modify: `labs/self-learning/self-learning-hyperframes/scripts/init_run.py`
- Modify: `labs/self-learning/self-learning-hyperframes/tests/test_init_safety.py`
- Test: `labs/self-learning/self-learning-hyperframes/tests/test_*.py`

- [ ] **Step 1: 保留旧全局链接，机械复制完整目录**

Run:

```bash
test ! -e labs/self-learning/self-learning-hyperframes
cp -R \
  skills/tutorial-to-hyperframes-demo \
  labs/self-learning/self-learning-hyperframes
```

Expected: 新旧目录暂时并存；若旧目录存在 `experience.local.md`，新目录也保留该 ignored 私有文件。

- [ ] **Step 2: 在任何修改前运行复制后的 60 项基线测试**

Run:

```bash
python3 -m unittest discover \
  -s labs/self-learning/self-learning-hyperframes/tests \
  -p 'test_*.py' \
  -v
```

Expected: 原有 60 项全部 PASS，证明机械复制本身没有破坏相对路径。

- [ ] **Step 3: 先增加旧持久 marker 迁移测试**

在复制后的 `test_init_safety.py` 增加表驱动测试，覆盖旧 root pair、旧 nested pair、`LEGACY_PRIVATE_IGNORE_COMMENT` 单行标记、仅新 marker、旧新并存和重复旧 marker。每个可修复场景运行 `start` 后都要断言旧 marker 被移除、新 marker 只出现一次、用户规则仍保留；第二次使用不同 run-id，断言成功且文件字节幂等。另增加未闭合旧 block 场景，断言失败且原文件不变。

Run:

```bash
python3 -m unittest \
  labs.self-learning.self-learning-hyperframes.tests.test_init_safety \
  -v
```

Expected: 新测试 FAIL，因为复制后的脚本仍把旧 marker 当作当前 marker，不会输出新的 `self-learning-hyperframes` marker，也不会合并旧新并存场景。

- [ ] **Step 4: 更新公开身份**

只修改身份和路由，不改现有阶段、契约、评分或 Python 子系统：

- frontmatter `name` 改为 `self-learning-hyperframes`；
- 标题改为 `Self Learning · HyperFrames`；
- description 明确“由 `self-learning` 调用，或用户明确要求教学素材生成 HyperFrames Demo 时使用；普通学习任务不单独触发”；
- `agents/openai.yaml` 使用 `display_name: Self Learning · HyperFrames` 和 `$self-learning-hyperframes`；
- 保留正文中与教程事实相关的 `tutorial_fact` 等领域术语。

- [ ] **Step 5: 迁移持久 marker 与故障注入环境变量**

在 `init_run.py` 中：

- 当前 marker 改为 `self-learning-hyperframes`；
- 保留旧 root/nested marker pair 与 `LEGACY_PRIVATE_IGNORE_COMMENT` 作为明确的 legacy 输入；
- 扩展 `rewrite_authoritative_ignore_block`，在一次重写中跳过当前或旧 block，并只写一个新 block；
- 故障注入变量改为 `SELF_LEARNING_HYPERFRAMES_FAULT`；
- 更新测试期望，并保留旧 marker 迁移测试。

- [ ] **Step 6: 跑完整迁移后自有测试**

Run:

```bash
python3 -m unittest discover \
  -s labs/self-learning/self-learning-hyperframes/tests \
  -p 'test_*.py' \
  -v
```

Expected: 现有 60 项加新增兼容测试全部 PASS。

- [ ] **Step 7: 用官方校验器检查迁移后的 Skill**

Run:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  labs/self-learning/self-learning-hyperframes
```

Expected: `Skill is valid!`

### Task 5: 更新仓库索引并让结构契约转绿

**Files:**
- Modify: `README.md`
- Modify: `labs/README.md`
- Test: `tests/test_self_learning_lab_contract.py`

- [ ] **Step 1: 更新根 README**

- 从“独立 Skills”表删除 `tutorial-to-hyperframes-demo`；
- 在“Skill Labs”增加 `[self-learning](./labs/self-learning)`；
- 不修改当前工作树中其他 Plugin、Harness 或文档内容。

- [ ] **Step 2: 更新 Labs 唯一入口**

在 `labs/README.md` 增加：

```markdown
- [`self-learning`](./self-learning/)：让 AI 从视频、文章或主题自主学习、扩展调研并生成可验证产物。
```

- [ ] **Step 3: 运行除旧目录断言外的契约测试**

Run:

```bash
python3 tests/test_self_learning_lab_contract.py \
  SelfLearningLabContractTests.test_main_skill_keeps_workflow_dynamic \
  SelfLearningLabContractTests.test_public_surfaces_use_only_new_names \
  SelfLearningLabContractTests.test_readmes_classify_self_learning_as_lab \
  SelfLearningLabContractTests.test_labs_remain_outside_batch_install \
  -v
```

Expected: PASS；完整测试仍因旧源目录暂时存在而失败，这是安全切换前的预期状态。

---

## Chunk 3: 全局切换、真实验证与收尾

### Task 6: 先安装两个新名称，再执行可恢复的受保护切换

**Files:**
- Remove after cutover: `skills/tutorial-to-hyperframes-demo/`
- Keep: `labs/self-learning/self-learning/`
- Keep: `labs/self-learning/self-learning-hyperframes/`

- [ ] **Step 1: 切换前再次运行关键测试**

Run:

```bash
python3 -m unittest discover \
  -s labs/self-learning/self-learning-hyperframes/tests \
  -p 'test_*.py' \
  -v
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  labs/self-learning/self-learning
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  labs/self-learning/self-learning-hyperframes
```

Expected: 全部 PASS；失败时不得动旧安装。

- [ ] **Step 2: 显式链接并安装两个新 Skill**

Run:

```bash
j-skills link "$PWD/labs/self-learning/self-learning"
j-skills install self-learning -g -e claude-code,codex --json
j-skills link "$PWD/labs/self-learning/self-learning-hyperframes"
j-skills install self-learning-hyperframes -g -e claude-code,codex --json
```

Expected: 两个新名称都返回成功 JSON。

- [ ] **Step 3: 验证 registry 与 Claude/Codex 实际符号链接**

Run:

```bash
j-skills link --list --json | rg -q '"name": "self-learning"'
j-skills link --list --json | rg -q '"name": "self-learning-hyperframes"'
j-skills list --global --json | rg -q '"self-learning"'
j-skills list --global --json | rg -q '"self-learning-hyperframes"'
test "$(readlink "$HOME/.claude/skills/self-learning")" = \
  "$PWD/labs/self-learning/self-learning"
test "$(readlink "$HOME/.codex/skills/self-learning")" = \
  "$PWD/labs/self-learning/self-learning"
test "$(readlink "$HOME/.claude/skills/self-learning-hyperframes")" = \
  "$PWD/labs/self-learning/self-learning-hyperframes"
test "$(readlink "$HOME/.codex/skills/self-learning-hyperframes")" = \
  "$PWD/labs/self-learning/self-learning-hyperframes"
```

Expected: 所有命令退出码为 0。不要用 `j-skills list --all` 代替这些检查。

- [ ] **Step 4: 新名称验证通过后卸载并取消链接旧名称**

保留旧源目录，使用同一 shell 的 fail-fast 保护完成切换：

```bash
set -euo pipefail
OLD_NAME=tutorial-to-hyperframes-demo

j-skills uninstall "$OLD_NAME" -g -y --json
j-skills link --unlink "$OLD_NAME" --json

! j-skills link --list --json | rg -q "\"name\": \"$OLD_NAME\""
! j-skills list --global --json | rg -q "\"$OLD_NAME\""
test ! -e "$HOME/.claude/skills/$OLD_NAME"
test ! -e "$HOME/.codex/skills/$OLD_NAME"
test ! -L "$HOME/.claude/skills/$OLD_NAME"
test ! -L "$HOME/.codex/skills/$OLD_NAME"

j-skills link --list --json | rg -q '"name": "self-learning"'
j-skills link --list --json | rg -q '"name": "self-learning-hyperframes"'
test "$(readlink "$HOME/.claude/skills/self-learning")" = \
  "$PWD/labs/self-learning/self-learning"
test "$(readlink "$HOME/.codex/skills/self-learning")" = \
  "$PWD/labs/self-learning/self-learning"
test "$(readlink "$HOME/.claude/skills/self-learning-hyperframes")" = \
  "$PWD/labs/self-learning/self-learning-hyperframes"
test "$(readlink "$HOME/.codex/skills/self-learning-hyperframes")" = \
  "$PWD/labs/self-learning/self-learning-hyperframes"
```

Expected: 旧 registry、global list 和两条旧链接均消失；两个新名称与四条新链接仍然有效。任一步失败都立即停止且不删除旧源目录；若旧安装已卸载但后续检查失败，使用仍存在的旧源目录重新 `link/install` 后再排查。

- [ ] **Step 5: 删除旧仓库源目录**

先证明所有非跟踪私有文件都已复制，再删除精确旧目标。允许忽略可重建的 `__pycache__`/`.pyc`，其他 ignored 文件必须在新目录存在且字节一致；旧目录不得存在非忽略的 untracked 文件：

```bash
OLD_ROOT=skills/tutorial-to-hyperframes-demo
NEW_ROOT=labs/self-learning/self-learning-hyperframes

test -z "$(git ls-files --others --exclude-standard -- "$OLD_ROOT")"
while IFS= read -r old_path; do
  case "$old_path" in
    */__pycache__/*|*.pyc) continue ;;
  esac
  relative="${old_path#"$OLD_ROOT"/}"
  new_path="$NEW_ROOT/$relative"
  test -f "$new_path"
  cmp -s "$old_path" "$new_path"
done < <(git ls-files --others --ignored --exclude-standard -- "$OLD_ROOT")

rm -rf -- skills/tutorial-to-hyperframes-demo
```

Expected: 旧目录不存在；新目录、两个新全局链接仍存在。

- [ ] **Step 6: 删除后重新运行全部迁移测试与结构契约**

Run:

```bash
python3 -m unittest discover \
  -s labs/self-learning/self-learning-hyperframes/tests \
  -p 'test_*.py' \
  -v
python3 tests/test_self_learning_lab_contract.py -v
```

Expected: 迁移后的全部自有测试与结构契约全部 PASS。

### Task 7: 验证迁移后同一条真实链路、仓库质量门与新进程发现

**Files:**
- Test: `labs/self-learning/self-learning-hyperframes/tests/`
- Test: `tests/`
- Validate: `README.md`, `labs/`, `docs/philosophy/`, `install.sh`

- [ ] **Step 1: 用新路径完成 init，并验证已有成功 run**

Run:

```bash
SMOKE_REPO="${AI_CLIP_LAB_SMOKE_REPO:-../ai-clip-lab--tutorial-hyperframes-demos}"
RUN_ID=2026-07-11-poster-wall
SOURCE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source"]["private_locator"])' \
  "$SMOKE_REPO/.learning/runs/$RUN_ID/run.json")"
test -f "$SOURCE"

INIT_ROOT="$(mktemp -d)"
python3 labs/self-learning/self-learning-hyperframes/scripts/init_run.py start \
  --repo "$INIT_ROOT" \
  --run-id migration-smoke \
  --source "$SOURCE" \
  --source-id migration-smoke \
  --json
test -f "$INIT_ROOT/.learning/runs/migration-smoke/run.json"
rm -rf -- "$INIT_ROOT"

python3 labs/self-learning/self-learning-hyperframes/scripts/validate_run.py \
  --repo "$SMOKE_REPO" \
  --run-id "$RUN_ID" \
  --ffprobe on \
  --json
```

Expected: 新路径成功初始化一个临时 run；已有 `poster-wall` run 在迁移后的 validator 下完整通过，且仍绑定 `demos/11-hyperframes-3d-poster-wall`。

- [ ] **Step 2: 对同一成功 run 绑定的 Demo 执行 check/render**

Run:

```bash
SMOKE_REPO="${AI_CLIP_LAB_SMOKE_REPO:-../ai-clip-lab--tutorial-hyperframes-demos}"
test -d "$SMOKE_REPO/demos/11-hyperframes-3d-poster-wall"
SMOKE_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$SMOKE_ROOT"' EXIT
rsync -a --exclude node_modules --exclude renders --exclude snapshots \
  "$SMOKE_REPO/demos/11-hyperframes-3d-poster-wall/" \
  "$SMOKE_ROOT/demo/"
(
  cd "$SMOKE_ROOT/demo"
  NODE_USE_ENV_PROXY=1 \
    HTTPS_PROXY=http://127.0.0.1:10802 \
    HTTP_PROXY=http://127.0.0.1:10802 \
    npm run check
  NODE_USE_ENV_PROXY=1 \
    HTTPS_PROXY=http://127.0.0.1:10802 \
    HTTP_PROXY=http://127.0.0.1:10802 \
    npm run render
  MP4="$(find renders -type f -name '*.mp4' -size +0 -print -quit)"
  test -n "$MP4"
  ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1 "$MP4"
)
rm -rf -- "$SMOKE_ROOT"
trap - EXIT
```

Expected: 与 Step 1 已验证 run 相同的 Demo 完成 `check`、`render`、MP4 存在性与 `ffprobe`；不修改真实 Demo 仓库。

- [ ] **Step 3: 运行仓库统一质量门**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
```

Expected: 全部退出码 0。

- [ ] **Step 4: 检查旧名称只存在于历史文档或明确的 legacy 兼容测试**

Run:

```bash
rg -n 'tutorial-to-hyperframes-demo' \
  README.md \
  labs/README.md \
  labs/self-learning \
  docs/philosophy \
  tests/test_self_learning_lab_contract.py
```

Expected: 两份 README、两个公开 `SKILL.md`、`agents/openai.yaml` 和哲学文档零命中；允许 `init_run.py` 与迁移测试中明确标注的 legacy marker 命中。

- [ ] **Step 5: 用三个无上下文新鲜子 Agent 前向测试全局发现**

使用 `collaboration.spawn_agent`，每次设置 `fork_turns="none"`，不传设计文档或预期答案；记录返回的 agent id 与最终文本作为本轮验证证据。分别发送三个原始任务：

1. 使用 `$self-learning` 阅读 `docs/philosophy/README.md`，选择最小有效产物并说明如何验证；不得修改源文件。
2. 使用 `$self-learning` 规划一个复杂视觉学习任务，要求“必须先用 GPT Image 生成原型并停下等待确认”；不得真正生成图片或实现。
3. 使用 `$self-learning-hyperframes` 读取任意本地教学视频前，说明它会先检查什么以及何时调用现有外部能力；不得下载、生成或修改文件。

Expected: 第一个任务可以直接执行而不制造固定 Workflow；第二个任务保留指定工具与人工检查门，同时自行决定其余路径；第三个任务证明 breaking rename 后的新子 Skill 能被全局发现并加载。若任一任务出现固定通用阶段、把 Self Learning 解释为模型训练、忽略人工门或找不到新名称，先修对应 `SKILL.md`/链接再用新 agent id 重测。

- [ ] **Step 6: 精确检查最终 diff，不提交**

Run:

```bash
git status --short -- \
  README.md \
  labs/README.md \
  labs/self-learning \
  docs/philosophy \
  docs/superpowers/specs/2026-07-11-self-learning-lab-design.md \
  docs/superpowers/plans/2026-07-11-self-learning-lab.md \
  skills/tutorial-to-hyperframes-demo \
  tests/test_self_learning_lab_contract.py
```

Expected: 只包含本计划列出的新增、修改和旧目录删除；不得 stage、commit 或 push。
