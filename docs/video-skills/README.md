# Video Skills Research

本目录收纳视频处理、视频生成与视频下载相关 Skill 的调研材料。这里的内容用于设计仓库内媒体类 Skills 的边界、风控和实现取舍。

## 入口

| 文档 | 主题 | 何时读取 |
|------|------|----------|
| [Claude Code Video Toolkit 深度研究](references/claude-code-video-toolkit-deep-dive.md) | AI 视频生产工作区的架构、Skills、Commands、工具层与模板设计 | 设计视频生成、视频工作流或媒体生产类 Skill 时 |
| [视频 AI Skills 风控机制分析](references/risk-control-analysis.md) | 视频下载、API 调用、成本、网络容错和文件处理风控模式 | 设计视频下载、剪辑、转录或生成类 Skill 的安全边界时 |

## 维护规则

- 通用结论进入本目录或对应 Skill 的 `references/`。
- 本机路径、账号、Cookie、下载站点固定 Referer、代理和真实文件位置不得写入可提交文档。
- 历史实施计划若不再活跃，放入 `docs/archive/plans/`。
