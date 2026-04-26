# repo-study Translate 模式指南

本文档定义 `/repo-study translate` 的执行规范：通过 subagent 并行翻译 Markdown 文档，并输出 `*.zh.md` 文件，不修改原始文档。

---

## 1. 执行目标

- 输入：study 项目中的 `*.md` 文档
- 输出：同路径的 `*.zh.md` 文档（例如 `README.md -> README.zh.md`）
- 强约束：**禁止修改源文件**

---

## 2. 任务编排

先在项目根目录生成翻译任务：

```bash
scripts/repo-study-translate.sh --json
```

脚本输出字段：

- `tasks[].source`：源文件相对路径
- `tasks[].target`：目标文件相对路径（自动转换为 `.zh.md`）
- `tasks[].group`：建议 subagent 分组编号
- `pendingTasks`：待翻译文件数
- `skippedExisting`：已有 `*.zh.md` 而被跳过的文件数

如需重译已存在的 `.zh.md`：

```bash
scripts/repo-study-translate.sh --json --force
```

---

## 3. Subagent 并行策略

- 每个 group 启动 1 个 subagent
- subagent 仅处理分配到的文件集合
- 默认每组 20 个文件，可通过 `--group-size` 调整
- 主会话负责汇总结果，不直接翻译正文

---

## 4. Subagent Prompt 模板

```text
你负责翻译以下 Markdown 文件为中文，只输出到对应 *.zh.md 文件。

任务列表：
{source_1} -> {target_1}
{source_2} -> {target_2}
...

硬性规则：
1) 绝对不要修改源文件 *.md
2) 仅写入目标文件 *.zh.md（可覆盖该目标文件）
3) frontmatter 保持 key 结构不变
4) 保留标题层级、列表层级、表格结构
5) 代码块里的代码不翻译
6) 链接 URL 不改动

输出格式：
- DONE: <target path>
- FAIL: <source path> | <reason>
```

---

## 5. 翻译质量规则

- 术语一致：同一术语在同项目内统一译法
- 技术准确：命令、参数、配置项保持原文
- 语义完整：不丢段落、不丢示例、不丢警告
- 可读性优先：中文表达自然，不做逐词直译

---

## 6. 失败重试

对失败文件单独重试，不重跑全量任务：

```bash
scripts/repo-study-translate.sh --json | jq '.tasks[] | select(.source=="notes/xxx.md")'
```

重试时仅将失败文件重新派发给 subagent。

---

## 7. 完成态汇总

主会话最终输出：

- 总文件数
- 成功翻译数
- 跳过数（目标已存在）
- 失败清单（文件 + 原因）
- 是否需要二次重试
