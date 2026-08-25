# App Flow 与 Skill Memory 实施计划

> **执行方式：** 在当前会话按 `subagent-driven-development` 顺序执行；每个实现任务先做规范审查，再做质量审查。仓库规则禁止自动提交，因此本计划不包含 commit、push 或发布动作。

**目标：** 新增一个不固定技术栈、阶段和交付形式的 `labs/app-flow`，并新增可插拔的 `happy-app-experience` 经验包；两者各自拥有 Git ignored、按 Repo/WorkTree/Feature 渐进检索的本地 Memory。

**架构：** `app-flow` 只拥有目标、授权、能力发现、验证、停止和唯一任务恢复点。具体行动由宿主 Skill metadata 动态选择能力 Skill；`happy-app-experience` 只在用户或现场需要 Happy 经验时加载。稳定规则与真实 Happy 经验提交到小型 reference，本地运行资料全部进入各 Skill 自己的 `local/` 并被 Git 忽略。

**技术栈：** Markdown Agent Skills、YAML frontmatter、Python `unittest` 合约测试、Git ignore 规则。

**设计依据：** `docs/superpowers/specs/2026-07-12-app-flow-and-skill-memory-design.md`

**执行约束：**

- 当前工作区包含已审阅的设计文档；精确修改下列文件，不清理或改写无关内容。
- 先看测试按预期失败，再生成或编辑 Skill。
- 使用官方 `skill-creator/scripts/init_skill.py` 初始化两个 Skill，再删除不属于最小形态的生成文件。
- 不创建 `workflow.yaml`、固定阶段子 Skill、artifact manifest、评分 schema 或已提交的 `local/`。
- 不运行 App、Expo、模拟器、OTA、部署或 GitHub Release。
- 不自动 commit、push 或发布远端。

---

## Task 1：建立行为合约并确认 RED

**文件：**

- 新建：`tests/test_app_flow_contract.py`

- [ ] **Step 1：写 frontmatter 与文件读取 helper**

  使用 `Path`、`subprocess`、`unittest` 和 `yaml`。固定路径：

  ```python
  REPO_ROOT = Path(__file__).resolve().parents[1]
  APP_FLOW = REPO_ROOT / "labs" / "app-flow" / "app-flow"
  HAPPY_EXPERIENCE = REPO_ROOT / "skills" / "happy-app-experience"
  ```

  `load_skill()` 返回解析后的 frontmatter 和正文；不 mock 文件系统。

- [ ] **Step 2：写 `app-flow` 薄 Workflow 合约**

  方法名为 `test_app_flow_is_thin_and_metadata_driven` 与 `test_app_flow_has_bounded_durable_loop`，必须覆盖：

  - `name` 为 `app-flow`；description 能匹配自然语言 App 开发、截图输入和长时间自主执行；
  - `SKILL.md` 明确不固定技术栈、阶段或交付形式；
  - 能力通过宿主 metadata 发现，覆盖零匹配、多匹配与不可读候选降级；
  - 一次候选探查有界，且没有 `workflow.yaml` 或固定子 Skill；
  - `app-flow` 是唯一任务恢复点 owner，包含 `repo-key/task-key`、generation/fencing 和 checkpoint 降级语义；
  - task lease 覆盖严格递增 generation/sequence、每 10 秒续租、30 秒后可接管、写前 token 校验，以及非 owner 只能读 checkpoint 或回传 owner；
  - 默认执行 envelope 是 4 小时并预留 15 分钟验证；同一失败签名无新证据时不原样重试。

- [ ] **Step 3：写渐进 Memory 与 Git ignore 合约**

  分成 `test_app_flow_local_memory_is_ignored_and_progressive` 与 `test_happy_experience_local_memory_is_ignored_and_progressive`，对两个 Skill 都验证：

  - `.gitignore` 包含精确规则 `local/` 和 `*.local.*`；
  - `git check-ignore -q --no-index <skill>/local/memories/example.md` 返回 0；
  - `git ls-files <skill>/local` 为空；
  - 入口约束为最多 1 个根入口、1 个作用域 map、3 条正文且合计不超过 32 KiB；
  - 路由优先级包含显式 ID、WorkTree、分支、Repo、主题；
  - Repo 命名空间、不可变 Memory、`supersedes`、敏感信息排除和损坏降级存在。
  - 按需写入协议链接到统一本地 Memory reference；该 reference 验收 per-map lease、过期后 fencing 接管、持锁重读合并、最多 50 个 `pending-index`，以及 `scope/status/evidence/created-at/verified-at/sensitivity` 最小字段。

- [ ] **Step 4：写 `happy-app-experience` 路由与证据合约**

  方法名为 `test_happy_experience_is_optional_and_evidence_backed`，必须覆盖：

  - `name` 为 `happy-app-experience`，description 明确“参考 Happy/Paws 经验”触发且它不是 Workflow；
  - `references/INDEX.md` 只做渐进导航；
  - `references/mobile-delivery.md` 包含验证日期、适用边界和真实 Happy 相对证据路径；
  - 经验明确 OTA 只适合 JavaScript 兼容改动，原生变化需要重建，并明确 OTA 不替代静态检查与回归测试；
  - 无 Happy 源码或证据不可读时降级为历史经验，不冒充当前事实；
  - `app-flow` 不硬编码 `happy-app-experience` 名称。

- [ ] **Step 5：写安装发现与文档合约**

  方法名为 `test_repository_docs_expose_both_skills`，验证：

  - 根 `README.md` 列出独立 Skill `happy-app-experience` 和实验 `app-flow`；
  - `labs/README.md` 给出 `j-skills link ./labs/app-flow/app-flow` 与安装命令；
  - `labs/app-flow/app-flow/SKILL.md` 可直接由 metadata parser 读取；缺少可选能力 Skill 不影响入口合约。

- [ ] **Step 6：运行 RED**

  ```bash
  PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages" \
    python3.11 -m unittest tests.test_app_flow_contract -v
  ```

  预期：因两个目标 Skill 尚不存在而失败；失败原因必须是缺少目标文件/合约，而不是测试语法或依赖错误。

---

## Task 2：实现薄 `app-flow`

**文件：**

- 新建：`labs/app-flow/app-flow/SKILL.md`
- 新建：`labs/app-flow/app-flow/.gitignore`
- 修改：`docs/philosophy/references/local-memory.md`
- 修改：`docs/philosophy/references/memory-and-scoring.md`
- 临时生成后删除：`labs/app-flow/app-flow/agents/openai.yaml`

- [ ] **Step 1：用官方初始化器生成 Skill**

  ```bash
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/init_skill.py" \
    app-flow --path labs/app-flow
  ```

  删除生成的 `agents/openai.yaml` 与空 `agents/`，因为本实验的最小分发接口只需要 `SKILL.md` 和 `.gitignore`。

- [ ] **Step 2：写小而完整的 metadata 与运行入口**

  description 同时说明：

  - 何时触发：用户以自然语言、模块或截图要求构建 App，并希望长时间自主工作；
  - 能做什么：从目标持续做到经验证的代码/当次授权交付；
  - 不做什么：不固定技术栈、阶段、交付形式，不把“长时间”解释为远端发布授权。

- [ ] **Step 3：写自然循环，不写阶段图**

  `SKILL.md` 保持单一循环：建立 goal/acceptance/authority/envelope → 读现场与局部 Memory → 选择下一项最高价值行动 → 从 metadata 有界发现能力 → 行动与验证 → 更新 checkpoint/Memory → 完成、继续或阻塞。

  必须包含：

  - metadata 最多 5 个候选，一次探查一个、最多两个；零个/多个/不可读的降级；
  - 相同上下文直接交接，不为了中转创建 Markdown；
  - 远端副作用仍需用户授权；
  - 4 小时默认 envelope、15 分钟验证预留、进展证据和停止条件。

- [ ] **Step 4：写按需 Memory 与唯一恢复点入口**

  只在需要恢复或复用时访问 `local/`。先读 `local/INDEX.md`，再读一个 scope map 和最多 3 条正文/32 KiB；不存在就继续，不递归扫描。

  `app-flow` 独占任务级 `maps/resume/<repo-key>/<task-key>.md`；写明严格递增 generation/sequence、每 10 秒续租、30 秒后 fencing 接管、写前 token 校验、不可变 checkpoint、非 owner 行为与损坏降级。完整通用协议按需指向仓库 `docs/philosophy/references/local-memory.md`，避免把低频细节铺满入口。

- [ ] **Step 5：实现统一本地 Memory 协议**

  - Feature map 路径统一为 `maps/features/<repo-key>/<feature-key>.md`；
  - 写明默认只读 1 个入口、1 个 map、3 条正文且不超过 32 KiB；
  - 把“更新原条目”改为新增不可变记录，通过 `supersedes` 和 map 的 `superseded-by` 表达替代；
  - 明确敏感信息禁令覆盖整个 `local/`，而不只是可索引 Memory；
  - 明确只有 `app-flow` 可以额外拥有任务级 `maps/resume/`；
  - 写明 per-map lock 的 10/30 秒续租与 fencing 接管、持锁后重读合并、最多 50 个 `pending-index` 的有界恢复；
  - 写明 Memory 的 `scope/status/evidence/created-at/verified-at/sensitivity` 最小字段及损坏降级。

- [ ] **Step 6：写 `.gitignore`**

  ```gitignore
  local/
  *.local.*
  ```

- [ ] **Step 7：运行 `app-flow` 相关测试并确认 GREEN**

  运行 `test_app_flow_is_thin_and_metadata_driven`、`test_app_flow_has_bounded_durable_loop` 与 `test_app_flow_local_memory_is_ignored_and_progressive`。预期三项通过；`happy-app-experience` 相关测试仍因目标尚未实现而失败。

---

## Task 3：实现 `happy-app-experience` 与首批真实经验

**文件：**

- 新建：`skills/happy-app-experience/SKILL.md`
- 新建：`skills/happy-app-experience/.gitignore`
- 新建：`skills/happy-app-experience/references/INDEX.md`
- 新建：`skills/happy-app-experience/references/mobile-delivery.md`
- 临时生成后删除：`skills/happy-app-experience/agents/openai.yaml`

- [ ] **Step 1：用官方初始化器生成 Skill 与 reference 目录**

  ```bash
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/init_skill.py" \
    happy-app-experience --path skills --resources references
  ```

  删除生成的 `agents/openai.yaml` 与空 `agents/`；reference 目录保留并填入真实内容。

- [ ] **Step 2：写经验包入口**

  `SKILL.md` 明确它是上下文提供者，不是 App Workflow，也不强制 Expo/RN。激活条件是用户明确说参考 Happy/Paws，或当前移动开发/交付问题与 description 高度匹配。

  入口只读 `references/INDEX.md`；根据问题再读一个相关 reference。Happy 源码可用时重新核验证据；不可用时将内容标成带日期的历史经验。

- [ ] **Step 3：写渐进式 reference 索引**

  `references/INDEX.md` 只包含主题、适用问题、文件路径和最近验证日期，不复制正文。目前只索引 `mobile-delivery.md`，不预建空分类。

- [ ] **Step 4：写有证据的移动交付经验**

  `references/mobile-delivery.md` 至少包含两条：

  1. OTA 仅适用于 JavaScript 兼容改动；原生依赖、权限、Expo plugin、包 ID、更新 URL、runtime version 变化必须重建 App。
  2. OTA/真机是最终确认，不替代 typecheck、测试和结构化回归。

  每条写：决策、适用边界、Happy 相对证据路径、验证日期 `2026-07-12`、迁移到其他 App 时需重新确认的条件。证据路径：

  - `docs/getting-started.zh-CN.md`
  - `packages/happy-app/app.config.js`
  - `packages/happy-app/eas.json`
  - `docs/research/2026-07-04-right-swipe-panel-retrospective.md`

- [ ] **Step 5：写 `.gitignore` 与本地进化入口**

  `.gitignore` 使用与 `app-flow` 相同两条规则。`SKILL.md` 说明本地经验只在有价值时写入 `local/`，保存不等于可信；稳定、脱敏且反复验证后才晋升到 committed reference。

- [ ] **Step 6：运行经验包相关测试并确认 GREEN**

  运行 `test_happy_experience_is_optional_and_evidence_backed` 与 `test_happy_experience_local_memory_is_ignored_and_progressive`。预期两项通过。

---

## Task 4：补齐发现与使用文档

**文件：**

- 修改：`README.md`
- 修改：`labs/README.md`

- [ ] **Step 1：更新根 README**

  - 在独立 Skills 表加入 `happy-app-experience`；
  - 在 Labs 列表加入 `app-flow`，描述为不固定技术栈/阶段/交付形式的长任务 App Workflow；
  - 在目录树加入两个路径；
  - 在单 Skill 安装示例加入 `./install.sh --skill happy-app-experience`；
  - 不把实验 `app-flow` 加进默认 `install.sh --all` 或 Plugin Marketplace。

- [ ] **Step 2：更新 Labs README**

  - 把 `app-flow` 列为当前实验；
  - 说明它与固定阶段 `web-flow` 的差异；
  - 给出手动预览安装命令：

    ```bash
    j-skills link ./labs/app-flow/app-flow
    j-skills install app-flow -g --env claude-code,codex
    ```

- [ ] **Step 3：运行文档与分发合约**

  ```bash
  PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages" \
    python3.11 -m unittest tests.test_app_flow_contract tests.test_install_contract -v
  ```

  预期：全部通过，且 Marketplace 不需要变化。

---

## Task 5：全量验证与交付审计

**文件：**

- 仅在发现本轮实现问题时修改上述文件。

- [ ] **Step 1：验证两个 Skill 结构**

  ```bash
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
    labs/app-flow/app-flow
  python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
    skills/happy-app-experience
  ```

  预期：两次都输出 `Skill is valid!`。

- [ ] **Step 2：运行定向与全量测试**

  ```bash
  PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages" \
    python3.11 -m unittest tests.test_app_flow_contract -v
  PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages" \
    python3.11 -m unittest discover -s tests -p 'test_*.py' -v
  ```

  预期：新增合约和原有 47 项基线全部通过。

- [ ] **Step 3：运行仓库审计**

  ```bash
  PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages" \
    python3.11 scripts/audit_skills.py --scan-shared-content
  bash -n install.sh
  claude plugin validate --strict .
  git diff --check
  ```

  预期：Skill audit 零 error/零 warning；shell 与 diff 检查通过；Plugin 校验不因两个非 Plugin Skill 发生变化。

- [ ] **Step 4：验证 Git ignored 与最小文件形态**

  ```bash
  git check-ignore -v --no-index labs/app-flow/app-flow/local/memories/example.md
  git check-ignore -v --no-index skills/happy-app-experience/local/memories/example.md
  find labs/app-flow/app-flow skills/happy-app-experience -maxdepth 3 -type f | sort
  git status --short
  ```

  预期：两个本地 Memory 路径都命中各自 `.gitignore`；没有已提交/待提交的 `local/`、`workflow.yaml`、空分类或生成的 `agents/openai.yaml`。

- [ ] **Step 5：最终独立审查**

  先按设计稿逐条做 spec compliance review；通过后再做代码/内容质量 review。所有重要问题修复并复验后才交付。

- [ ] **Step 6：交付说明**

  汇报新增能力、关键路径、验证结果、已知边界和工作区状态。明确本轮没有执行 commit、push、OTA 或 Release。
