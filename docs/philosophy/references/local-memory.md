# 可增长的本地 Memory

> Memory 是 Skill 的本机可增长工作区。它可以保存全量信息并持续膨胀，但默认不进入 Git，也绝不被一次性加载；上下文成本由索引命中的少量内容决定。

## 核心边界

Skill 的可提交部分和本地部分承担不同职责：

```text
<skill>/
├── SKILL.md                 # 可提交：触发边界、稳定原则、读取与写回协议
├── .gitignore               # 可提交：阻止本地 Memory 进入 Git
├── references/              # 可提交：脱敏、精选、可分享的稳定知识
└── local/                   # 不提交：按第一次真实使用懒创建
    ├── INDEX.md             # 只导航 maps，不平铺全部条目
    ├── maps/                # 主题与 namespaced Repo/WorkTree/Feature 索引
    ├── memories/            # 一个主题或根因一个 Markdown
    ├── runs/                # 全量临时资料、恢复点和证据
    └── archive/             # 已失效或不再活跃但仍需保留的资料
```

最小 `.gitignore`：

```gitignore
local/
*.local.*
```

不要为了保留空目录而提交一套占位结构。第一次确实需要写入时再创建 `local/`；如果已有项目选择保留 `.gitkeep`，也必须保证其余内容仍被忽略。

## 为什么可以保存全量

磁盘容量和上下文容量不是同一个约束。Memory 即使有数 GB，只要 Agent 不递归读取，就不会自动占用上下文。全量保留可以服务：

- 跨会话、上下文压缩或进程中断后的恢复；
- 回看某个 Feature 当时的资料、证据和选择；
- 重新提炼此前没有进入长期层的候选；
- 保存工具必须通过文件交接的大型内容；
- 为未来的索引和经验晋升提供原始证据。

保存不等于信任，也不等于加载。有用且已脱敏的资料可以尽量完整，进入当前上下文和稳定规则的内容仍必须经过选择。

## 两层索引

`local/INDEX.md` 只负责把当前任务送到正确 map：

```text
当前任务
→ local/INDEX.md
→ maps/features/<repo-key>/<feature-key>.md 或 maps/<topic>.md
→ 1–3 条 memories/<id>.md
→ 必要时再进入 runs/<run-id>/ 的原始证据
```

默认首次决策只读 **1 个根入口**、**1 个作用域 map** 和最多 **3 条**正文，正文合计不超过 **32 KiB**。只有当前决策明确需要证据时才继续展开；Memory 总文件数增长不能改变这个入口上限。

根索引只应包含：

- 稳定问题域及“什么时候进入”；
- 当前活跃 Feature/WorkTree 的短入口；
- 找不到入口时的检索提示；
- archive 的存在说明，不列出 archive 全部内容。

主题或 Feature map 才列原子 Memory。每一项只放简短摘要、适用范围、路径和最近验证时间；不要复制正文。

当 map 本身开始过大时，按真实问题模型拆分，而不是按文件数量机械分片。拆分后的每次跳转都必须缩小问题空间。

## 上下文标识与查找顺序

查找当前功能资料时按最明确的标识优先：

1. 用户、Goal 或任务系统明确提供的 Feature/Task ID；
2. 当前 WorkTree 名称；
3. 当前 Git 分支名；
4. Repo ID 或规范化远程地址；
5. 通用主题 map。

同一批功能可以共享 Feature ID。不同会话、子 Agent 或 WorkTree 只要解析出同一标识，就能落到同一组资料，不需要把内容复制进 prompt。

Feature ID 不能直接成为全局路径。先从去凭据、去查询参数、去 `.git` 的规范化远程标识形成 `repo-key`；没有远程时对仓库 realpath 做哈希且不在索引暴露绝对路径。Feature 再用安全 slug 与原值哈希形成 `feature-key`，最终路径始终是 `maps/features/<repo-key>/<feature-key>.md`。

找不到匹配项时直接按当前现场工作；不要为了“完整”扫描全部 memories。确有必要时先在索引摘要和 frontmatter 上做定向搜索，再读取少量命中正文。

## 写入与晋升

每次使用 Skill 后都可以判断是否要保存或更新，但四种内容要分开：

| 内容 | 默认位置 | 是否进入根索引 | 是否可直接成为稳定规则 |
|---|---|---:|---:|
| 同一上下文里的普通交接 | 不落盘 | 否 | 否 |
| 全量临时资料、原始证据 | `runs/<run-id>/` | 只登记 Run/Feature 摘要 | 否 |
| 会影响未来决策的原子经验 | `memories/<id>.md` | 经 map 可达 | 需验证、查重和边界 |
| 通用且反复成立的方法 | `SKILL.md` 或 `references/` | 由 Skill 地图导航 | 是，晋升后才是 |

一次任务结束时：

1. 保留用户希望保留的全量 Run 资料；
2. 更新对应 Feature map 的状态和下一步；
3. 把有未来价值的内容提炼为原子 Memory；
4. 对重复根因新增不可变记录，用 `supersedes` 指向旧 ID，并由 map 写 `superseded-by`；
5. 只有多次验证、与本机无关的结论才进入可提交层。

“每次自主进化”表示每次都做一次判断，不表示每次都改写 `SKILL.md`。

## Memory 最小契约

可进入 map 的 Memory 使用不可变文件。至少包含：

```text
id
scope: repo / worktree / feature / run
status: raw | observed | verified
created-at
verified-at
evidence
supersedes
sensitivity: public | redacted | local-private
```

`verified` 必须有仍可访问的 evidence；否则只能是 `raw` 或 `observed`。修正结论时新建 Memory，通过 `supersedes` 指向旧 ID，旧文件保持不变；map 的 `superseded-by` 表达派生生命周期。缺字段、断链或损坏条目直接跳过并把 map 标为待修复，以当前证据继续。

## 并发写入

同一 run 只指定一个 memory writer。跨 run 更新同一 map 时使用原子创建的 **per-map lock**：

1. 锁保存 owner、30 秒租约和随机 fencing token；持锁者每 10 秒续租。
2. 租约到期后，不论旧进程是否仍存活，新 writer 都可原子归档旧锁并取得新 token。
3. writer 必须**持锁后重读** map，按 Memory ID 合并，写唯一临时文件，再次校验 token 后原子 rename。
4. 旧 writer 的 token 失效后不得提交；拿不到锁时只保存不可变 Memory 与 `pending-index` 指针。
5. 下一位成功持锁者一次合并当前 run 和**最多 50 个**最新 `pending-index`；其余保留游标，避免恢复成本随总量失控。

只有 `app-flow` 可以在自己的通用结构外增加任务级 `maps/resume/<repo-key>/<task-key>.md`；其他能力 Skill 与经验包不创建全局恢复点。

## Git 与隐私规则

- `local/` 整体默认忽略；动态 INDEX、maps 和 memories 也不例外。
- 不使用 `git add -f` 提交本地 Memory。
- 提交前检查 `git status --ignored` 或等价结果，确认本地内容确实被排除。
- 敏感信息禁令覆盖整个 `local/`，包括 runs、checkpoint、临时文件、原始证据、maps 和 memories。Token、密码、私钥、完整环境变量、个人聊天原文和未经授权的第三方私密数据都不能写入；密钥属于专门的凭据系统。
- 需要分享的经验必须先脱敏、验证和提炼，再复制到 `references/` 或 `SKILL.md`，不能直接发布整个本地池。
- Memory 的备份、同步和清理是独立生命周期，不通过代码仓库解决。

## 反模式

- 每次进入 Skill 就递归读取整个 `local/`；
- 把所有条目平铺到一个巨大的 `experience.local.md`；
- 把全部文件名平铺到根 `INDEX.md`；
- 同一上下文里写 MD 再原样读回；
- 把“已经保存”误当成“已经验证”；
- 每次成功或失败都直接重写稳定 Skill；
- 因为 Memory 很大就放进 Git LFS 或代码仓库；
- 为尚不存在的内容提前创建大量空目录、空 map 和空模板。
