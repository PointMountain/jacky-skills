# Docs 治理与 Skills Design Philosophy 设计

## 目标

收紧 `docs/` 的内容边界，把当前仍有价值的设计思考整理成一篇可阅读、可分享的 blog 风格文章，同时把已被新思路取代的 V1 协议移入明确的归档区。

## 目录设计

```text
docs/
├── philosophy/
│   ├── README.md
│   └── references/
│       ├── external-skills.md
│       ├── human-sop.md
│       ├── memory-and-scoring.md
│       ├── progressive-loading.md
│       └── yaml-contracts.md
└── archive/
    └── 自进化-skill-协议规范.md
```

- `docs/philosophy/README.md` 是唯一主入口，由现有 `自进化-skill-设计哲学-v2.md` 改写而来。
- `docs/philosophy/references/` 承接现有 `self-evolving-skill-v2/` 的细节文档，避免主文章继续膨胀。
- `docs/archive/` 只放不再作为当前指导、但仍有历史参考价值的内容。
- `docs/archive/自进化-skill-协议规范.md` 保留原中文文件名，降低历史引用辨识成本。

## 迁移映射

| 源路径 | 目标路径 | 链接处理 |
|---|---|---|
| `docs/自进化-skill-设计哲学-v2.md` | `docs/philosophy/README.md` | 改写正文，并把细节链接改为 `references/<file>.md` |
| `docs/self-evolving-skill-v2/external-skills.md` | `docs/philosophy/references/external-skills.md` | 修正因目录变化而失效的相对链接 |
| `docs/self-evolving-skill-v2/human-sop.md` | `docs/philosophy/references/human-sop.md` | 修正因目录变化而失效的相对链接 |
| `docs/self-evolving-skill-v2/memory-and-scoring.md` | `docs/philosophy/references/memory-and-scoring.md` | 修正因目录变化而失效的相对链接 |
| `docs/self-evolving-skill-v2/progressive-loading.md` | `docs/philosophy/references/progressive-loading.md` | 修正因目录变化而失效的相对链接 |
| `docs/self-evolving-skill-v2/yaml-contracts.md` | `docs/philosophy/references/yaml-contracts.md` | 修正因目录变化而失效的相对链接 |
| `docs/自进化-skill-协议规范.md` | `docs/archive/自进化-skill-协议规范.md` | 内容作为历史记录保留；仅修正指向新主文章的链接并显式标注归档状态 |

迁移后删除空的 `docs/self-evolving-skill-v2/`。仓库内其他文件如引用上述旧路径，只更新链接，不借机改写其正文。

## 主文章写作方向

文章使用第一人称、blog 风格，不再以“V2 主规范”的口吻罗列制度。核心思路是：

1. Skill 不应从文件模板开始，而应从人真实完成任务的方式开始。
2. 复杂工作流需要观察、验证、复盘、渐进加载和有限反馈，目的是让下次决策更好，而不是制造更多文件。
3. `SKILL.md` 应是导航和约束入口，而不是百科全书。
4. 复杂度必须与真实问题匹配；简单 Skill 继续使用 `experience.local.md` 完全足够。
5. 自进化不是让 Agent 随意修改自身，也不是保存原始思维过程，而是沉淀经过验证、能改变未来行动的事实。

文章保留指向细节文档的链接，但把具体契约、评分表和实现细节下沉到 `references/`。

## CLAUDE.md 规则

新增 `docs/` 治理章节，至少明确：

- `docs/` 不是临时草稿区；新增内容必须有清晰读者、长期价值和唯一归属。
- 当前有效的成体系主题使用英文 kebab-case 目录，并以 `README.md` 作为入口。
- 主题细节放入主题目录的 `references/`，不继续堆在 `docs/` 根目录。
- 已失效但仍有历史价值的文档移入 `docs/archive/`；无保留价值的临时产物应删除，而不是一律归档。
- 简单、本机私有、环境耦合的 Skill 经验使用被忽略的 `experience.local.md`，不为追求形式升级成复杂协议。
- 新增或迁移文档后必须检查相对链接，避免留下旧路径。

这些规则从本次变更后开始约束新内容。本次实施范围只包括上方迁移表、`CLAUDE.md` 和根目录软链接，不批量搬迁、删除、归档或改写 `docs/` 中的其他既有文件。

## AGENTS.md

在仓库根目录创建相对软链接：

```text
AGENTS.md -> CLAUDE.md
```

这样两个 Agent 入口共享同一份仓库规则，不产生双份内容漂移。

## 验证

1. 实施前记录 `git status --short`，并分别查看 `CLAUDE.md`、迁移表中的全部源路径和目标路径的现有 diff；已有改动视为用户内容，禁止回退或覆盖。搜索发现其他需要修正旧链接的引用文件时，也必须在编辑该文件前单独检查其现有 diff。
2. 确认精确旧路径 `docs/自进化-skill-设计哲学-v2.md` 与 `docs/self-evolving-skill-v2/` 不再存在。
3. 确认 V1 协议位于 `docs/archive/自进化-skill-协议规范.md`。
4. 搜索仓库，确认不存在仍指向上述旧路径的有效引用。
5. 检查新主文章到 `references/`、归档文章到新主文章，以及迁移后细节文档内部的相对链接。
6. 检查 `AGENTS.md` 是指向 `CLAUDE.md` 的相对软链接。
7. 将完成后的 `git status --short` 和目标路径 diff 与实施前基线对照，只允许出现迁移表、`CLAUDE.md`、`AGENTS.md` 及必要引用修正；不得回退、覆盖或夹带其他既有改动。
