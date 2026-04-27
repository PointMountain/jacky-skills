# Question.md 模板与 Answer 流程

> Question.md 是一篇自由格式的笔记文件，用户边看研究笔记边记录看不懂、想深挖的地方。AI 读取后自行拆解，补充对应笔记内容，解决后删除。

## 核心理念

**因为看不懂，所以才有这个文件。**

- 用户在 Obsidian 中阅读研究笔记时，遇到不懂的地方就切到 Question.md 写下来
- 每个 section 以 article_id 命名，关联到具体的研究笔记
- 内容完全自由：可以是问题、吐槽、"这段看不懂"、"想看个例子"等
- AI 读到后自行理解、拆解、找到对应笔记补充内容，把文章写好

## 文件位置

| 位置 | 路径 | 说明 |
|------|------|------|
| Study 项目（主） | `{study-project}/Question.md` | 源文件，git 可追踪 |
| Obsidian（symlink） | `{OB}/wiki/open-source/{project}/Question.md` | symlink 指向 study 项目 |

## 模板

```markdown
---
tags: [study-question]
type: question-tracker
project: {repo-name}
created_at: {date}
---

# Question

> 边看笔记边记录看不懂的地方。每个标题是 article_id，对应一篇研究笔记。写任何你想写的，AI 会来处理。

# 全局环境

> 不属于某篇具体笔记的全局性问题、建议或想法写在这里。

## {article_id 如 OBA-xxx}

{用户自由书写的内容：看不懂的地方、想深挖的点、需要的补充、想看个例子...}

## {article_id 如 OBA-yyy}

{另一段自由内容...}
```

### 用户写作示例

```markdown
## OBA-abc12345

sqlite3 是在什么时候用的？为什么不影响它 CDP 的核心功能？

## OBA-def67890

4.4 媒体资源的获取这部分看不太懂，没有实际的例子，能不能找一个 B 站视频测一下？

文件上传这个 case 也挺有意思，但没有展开说。

## OBA-ghi13579

我觉得当前这个探索少一篇综合性的测试文档。应该给一些挑战性的题目。
```

## Phase 10: Answer 流程

### Step 10.1: 读取 Question.md

1. 检查项目根目录 `Question.md` 是否存在
2. 读取全文，提取所有 `## {article_id}` section
3. 若无 section 或内容为空，提示"没有待处理的问题"并退出

### Step 10.2: AI 拆解（subagent）

启动一个 Explore 类型 subagent，将 Question.md 全文和对应的研究笔记一起传入：

```
你是代码分析和知识补充专家。

**任务**：用户在阅读研究笔记时，遇到看不懂的地方，写在了 Question.md 里。请你：
1. 读取 Question.md 全文
2. 对每个 article_id section，找到对应的研究笔记（通过 article_id 在 explorer/ 和 notes/ 中搜索）
3. 理解用户写的内容（可能是问题、困惑、"看不懂"、需求补充等）
4. 分析源码，找到答案或补充内容
5. 提出具体的补充方案：应该在原笔记的哪个位置补充什么内容

**源码路径**: {项目目录}/{repo-name}/
**研究笔记路径**: {项目目录}/explorer/ 和 {项目目录}/notes/
**Question.md 内容**:
{Question.md 全文}

**输出格式**（每个 section 一组）：

### section: {article_id}
- **对应笔记**: {找到的笔记路径}
- **用户诉求理解**: {AI 对用户内容的理解}
- **补充方案**: {具体要补充的内容，可直接写入笔记}
- **补充位置**: {在笔记中的哪个 section 之后插入}
```

### Step 10.3: 执行补充

主会话收到 subagent 的分析后：

1. 对每个 section：
   - 找到对应的研究笔记文件
   - 将补充内容插入到指定位置
   - 保留原有内容，只做追加/补充
2. 展示补充摘要给用户确认

### Step 10.4: 清理 Question.md

用户确认后：

1. 删除已解决的 section（整个 `## {article_id}` + 内容）
2. 如果某个 section 用户想保留，不删除（用户可在 section 末尾加 `<!-- keep -->` 标记）
3. 更新 frontmatter 的 `updated_at`

### Step 10.5: 输出摘要

```
✅ 已处理 {N} 个 section

| Article | 笔记 | 补充内容 |
|---------|------|---------|
| OBA-xxx | explorer/01-xxx.md | 补充了 sqlite3 使用场景说明 |
| OBA-yyy | notes/xxx.md | 添加了 B 站视频测试示例 |

Question.md 已清理，已解决的 section 已删除。
```
