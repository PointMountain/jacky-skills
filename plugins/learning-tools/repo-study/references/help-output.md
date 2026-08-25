# Help 输出模板

> 仅当参数为空、为 help 或 --help 时读取并原样遵循。

### 空值 / help 时的输出格式

当用户输入 `/repo-study` 不带参数，或带 `help`/`--help` 时，输出以下提示：

```
📖 repo-study — GitHub 仓库研究助手

用法: /repo-study <子命令> 或 /repo-study <仓库URL> [研究问题]

子命令:
  list      列出所有 *-study 项目
  status    查看当前项目状态（进度、模式、版本）
  update    更新当前项目源码到最新版本
  sync      同步所有 study 笔记到 Obsidian
  translate 并行翻译文档（*.md → *.zh.md）
  distill   将研究发现蒸馏为独立 demo 或设计文档
  answer    回答 Question.md 中的研究问题
  continue  恢复上次中断的交互学习

研究模式:
  /repo-study <URL> <问题>     首次研究 → Survey 模式（产出 explorer/）
                               后续提问 → Incremental 模式（产出 notes/）

示例:
  /repo-study https://github.com/user/repo 它的缓存策略是怎么实现的
  /repo-study list
  /repo-study sync
```

> **注意**：如果 args 不匹配任何子命令也不含 URL，则当作研究问题处理（在当前 study 项目中执行增量问答）。

---


