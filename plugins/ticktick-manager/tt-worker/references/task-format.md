# 任务池任务格式规范

> tt-defer 和 tt-worker 共享的任务格式定义

## 任务结构

**标题**：简短描述做什么（≤15 字）

**Tag**：任务类型标签（见下方 tag 表）

**内容（Markdown）**：

```markdown
## 原始背景
（必填）为什么需要这个任务？用户原始需求是什么？

## 前置决策
（可选）已经考虑过/排除的方案、重要的决策依据

## 执行环境
仓库路径：/path/to/repo
分支：feature-xxx（可选）
相关文件：path/to/file1, path/to/file2（如有具体文件，列出完整路径）

## 执行计划
（完整的 plan 或 spec 内容直接贴在这里）

## 预期产出
描述期望的产出物

## 备注
额外说明
```

## Tag 定义

| Tag | 含义 | 执行方式 | 完成标志 |
|-----|------|---------|---------|
| `plan-exec` | Plan 执行 | 按 plan 逐步执行代码 | plan 所有步骤完成 |
| `spec-dev` | Spec 开发 | 根据 spec 开发新功能 | 代码提交 + 测试通过 |
| `research` | 调研分析 | 搜索资料、分析、输出报告 | 报告文档生成 |
| `article` | 文章阅读 | 阅读并提炼要点 | 摘要写入 Obsidian |
| `code-task` | 代码任务 | 通用代码任务 | 代码提交 |

## CLI 用法

```bash
# 创建任务（带 tag）
tt task-add "简短标题" -p <poolProjectId> --tag <tag> --content "<markdown>"

# 批量创建
echo '[{"title":"标题","content":"...","projectId":"...","tags":["plan-exec"]}]' | tt task-batch-add --stdin
```

## 执行记录格式

tt-worker 执行后追加到 content 末尾：

```markdown
## 执行记录（tt-worker 自动维护）
- 状态：completed / failed / skipped
- 执行时间：2026-04-06 02:15:00
- 耗时：12 分钟
- 产出物：3 commits, PR #42
```
