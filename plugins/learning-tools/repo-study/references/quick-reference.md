# 快速参考

本文档提供 repo-study 的使用示例、模式说明和常用命令速查。

---

## 使用示例

```bash
# 场景 1: 首次创建 + Yolo 模式研究
调研下 git@github.com:chris-hendrix/claudehub.git 在 Agent 通信方面是如何实现的
# → 选择 Yolo 模式 → 直接输出完整报告

# 场景 2: 首次创建 + 交互模式研究
调研下 claudehub 的 prompt engineering 技巧
# → 选择交互模式 → 分步骤渐进式教学

# 场景 3: 已存在 + 有更新 + 研究
调研下 claudehub 的错误处理机制
# → 检测到有更新，询问是否更新后继续研究

# 场景 4: 已存在 + 已是最新 + 直接研究
调研下 claudehub 的插件系统
# → 检测到已是最新，直接开始研究
```

---

## 研究模式选择

### 双模式：Survey + Incremental

项目研究分为两种模式，根据 `surveyState` 自动判断：

| 模式 | 触发条件 | 产出目录 | 说明 |
|------|----------|----------|------|
| **Survey** | `surveyState != "completed"` | `explorer/` | 首次系统调研，成体系笔记 |
| **Incremental** | `surveyState == "completed"` | `notes/` | 增量问答，零散笔记 |

### Survey 模式下的研究风格

**Yolo 模式（快速模式）**：
- 启动 subagent（蓝色标识）执行代码分析
- 主会话接收 subagent 研究结果后输出完整报告
- 包含完整的代码分析和设计亮点
- 支持并行研究多个独立课题
- 产出沉淀到 `explorer/`
- 适合快速了解整体实现

**交互模式（教学模式）**：
- 启动 subagent（蓝色标识）静默调研，不输出内容
- 主会话根据 subagent 结果创建 `.study-session.json` 会话状态文件
- 将发现拆分为多个小概念
- 逐步讲解（主会话执行），每步一个概念
- **实时归档**：讲解后立即写入文件（使用 Write 工具）
- **实时更新**：立即更新会话状态和思维导图（使用 Edit 工具）
- **实时思维导图**：每步展示当前知识树位置和进度
- 每步后提供选项：继续/暂停/更多解释/提问
- 产出沉淀到 `explorer/`
- 支持 `/repo-study continue` 恢复中断的学习
- 适合深入学习和教学场景

### Incremental 模式

- 直接启动针对性 subagent 分析相关代码区域
- 产出沉淀到 `notes/`（零散笔记，不成体系）
- 每个笔记独立，不需要与其他笔记形成链路
- 完成后更新 `.study-meta.json` 的 topics[]（location: "notes"）

---

## 版本检查命令

```bash
# 获取远程最新 commit
gh api repos/OWNER/REPO/commits/main --jq '.sha'

# 读取本地记录的 commit（study 项目路径从 CLAUDE.md 的 GitHub 项目目录配置中读取）
cat {GitHub项目目录}/{REPO}-study/.study-meta.json | jq -r '.repo.commitSha // .commitSha'
```

## 当前目录状态查询（status）

```bash
# 仅当前目录
scripts/repo-study-status.sh --check-remote

# JSON 输出
scripts/repo-study-status.sh --json --check-remote
```

---

## 文档翻译（translate）

```bash
# 生成翻译任务（默认跳过已存在 *.zh.md）
scripts/repo-study-translate.sh

# JSON 输出任务清单（给主会话派发 subagent 用）
scripts/repo-study-translate.sh --json

# 强制重译（已存在 *.zh.md 也加入任务）
scripts/repo-study-translate.sh --json --force
```

翻译约束：
- 源文件 `*.md` 不允许修改
- 译文只写到 `*.zh.md`
- 建议按 `group` 字段并行派发 subagent 执行
