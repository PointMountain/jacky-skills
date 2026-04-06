# 构建由 LLM 驱动的自我改进型个人知识库

> 原文：Building a Self-Improving Personal Knowledge Base Powered by LLM
> 来源：https://github.com/louiswang524/llm-knowledge-base
> 日期：2026 年 4 月 5 日

Andrej Karpathy 最近写了一段让我印象深刻的话：

> "相比在终端里看文本回答，我更喜欢让它渲染 Markdown 文件……我几乎从不需要手动编写或编辑 wiki，那是 LLM 的领域。"

他描述的不是用 LLM 来回答问题，而是用 LLM 来构建和维护个人知识库 —— 一个由模型完成所有组织工作的 wiki。你喂给它原始内容，它负责编译、打标签、建立链接、索引一切。你只需要提问。

这个模式 —— LLM 作为知识策展人，而不仅仅是知识检索器 —— 与大多数人今天使用 AI 工具的方式有着根本性的不同。大多数人把 LLM 当智能搜索引擎用。Karpathy 的洞察是：你可以把它们当作拥有图书馆的图书管理员。

我花了几天时间搭建了这套系统。结果是一套开源的 Claude Code skills，可以在 Obsidian 中管理个人 wiki，初始设置后完全自主运行。这篇文章是关于它如何工作的技术详解、我学到了什么，以及我认为这个模式将走向何方。

## 当今知识管理的问题

个人知识管理在理论上是一个已解决的问题，在实践中却是一场灾难。

**理论**：捕获一切、打标签、建立链接、定期回顾。Notion、Roam、Obsidian、Zotero 等工具正是为此而生。它们很强大。

**实践**：大多数人的"第二大脑"是半成品笔记的墓地、标签不一致的链接集合、以及六个月前裁剪但从未阅读的文章。瓶颈不是存储 —— 而是维护系统的认知开销。打标签需要精力。写摘要需要精力。在 400 条笔记中找到关联需要精力。大多数人会在"这很有前景"和"为什么我有三条关于注意力机制的不同笔记"之间放弃。

Karpathy 的洞察是：这些开销正是 LLM 擅长消除的。模型不会厌倦打标签。它不会忘记添加反向链接。它可以一次阅读 50 篇文章并找到连接它们的线索。

问题是：如何将它连接起来使其真正工作？

## 架构概览

系统分为三层：

1. **原始存储** —— 所有摄入的内容放入 `raw/`。网页文章、PDF、图片、笔记。这里不做任何处理，只是一个暂存区。你负责填充这一层。

2. **Wiki** —— 一个编译后的、由 LLM 管理的 Obsidian 格式 Markdown 文件集合。每个概念有自己的文章。每个来源有摘要。所有内容通过 Obsidian `[[wikilinks]]` 互相链接。LLM 完全拥有这一层。

3. **输出** —— 问答回答、综合报告、检查报告、幻灯片、图表。这些会被归档回 wiki，以便未来查询可以引用。

```
你的内容（URL/PDF/图片/笔记）
       ↓ /kb-ingest
  raw/（暂存内容）
       ↓ /kb-compile（自动触发 /kb-reflect 综合）
  wiki/ — LLM 管理的
  inputs/ · sources/ · archive/
  主索引 · 概念文章 · 来源摘要 · 合并文章
       ↓ /kb-ask / /kb-lint / /kb-merge / /kb-output
  问答回答    → outputs/*.md
  健康报告    → outputs/lint-*.md
  合并文章    → wiki/archive/
  幻灯片和图表 → outputs/*.md / *.png
       ↓ 归档回 wiki
```

系统以 9 个 Claude Code skills 的形式发布 —— 纯 Markdown 文件，告诉 Claude 在你输入触发命令时该如何行为。安装一次，可在任何 Claude Code 会话中使用。

## 九个 Skills

### /kb-ingest —— 分阶段摄入

每个摄入工作流都需要一个暂存区。原则是：**先捕获，后处理**。`/kb-ingest` 接受任何来源并写入 `raw/`，附带元数据 frontmatter：

```yaml
---
source: https://arxiv.org/abs/1706.03762
ingested_at: 2026-04-05T10:00:00Z
type: web
status: uncompiled
---
```

四种输入类型有不同处理方式：

- **URL**：用 WebFetch 抓取，提取主要内容，去除导航和广告
- **PDF**：用 Claude 的文档理解能力读取，提取文本到附属 `.md` 文件
- **图片**：视觉读取，Claude 写描述性附属文件
- **笔记**：直接写入自由格式文本

关键设计决策：**摄入从不触发处理**。你可以摄入 20 篇文章然后一次性编译，也可以每摄入一篇就编译一次。清单文件跟踪已处理的内容。

### /kb-compile —— Wiki 编译器

这是核心 skill。对于每个未编译的 raw 文件，LLM：

1. 阅读内容
2. 写入 `wiki/sources/<slug>.md` —— 带标签、关键概念和显著细节的结构化摘要
3. 提取概念并创建或更新 `wiki/concepts/<concept>.md`，添加 `[[反向链接]]` 指向来源
4. 在 `wiki/index.md` 中追加单行条目
5. 更新清单状态为 `status: compiled`

**概念去重**步骤很重要。如果编译一篇关于注意力的新来源时 `wiki/concepts/attention.md` 已经存在，LLM 会读取现有文章并用新信息更新它，而不是创建重复。wiki 趋向收敛 —— 而非碎片化。

`wiki/index.md` 是导航层。它是一个包含 wiki 中每篇文章单行摘要的单一文件：

```markdown
## 概念
- [[concepts/attention]] — 允许模型动态权衡 token 相关性的机制
- [[concepts/transformers]] — 使用自注意力的序列建模基础架构

## 来源
- [[sources/attention-is-all-you-need]] — Vaswani 等人 2017，原始 Transformer 论文
```

这使得问答在规模化时无需 RAG 就能工作 —— LLM 先读索引，选择 3-5 篇最相关的文章，然后只读那些。它从不需要加载整个 wiki。

### /kb-ask —— 索引优先的问答

问答模式是系统中最有趣的架构决策。

对大型文档集合进行问答的朴素方法是 RAG：嵌入一切、嵌入查询、找最近邻、检索片段、回答。这能工作，但有一个根本问题 —— 检索是语义相似性匹配，找到"看起来像"查询的片段，而不理解知识库的结构。

这里的方案不同：**维护一个紧凑的、人类可读的索引，LLM 用它来导航。** 索引始终在上下文中。LLM 选择要阅读的完整文章。完整文章在上下文中用于回答。

这本质上是一个人类专家做的事：他们不会为每个问题搜索整个记忆。他们导航一个"我知道什么"的心理索引，然后回忆相关细节。

```
/kb-ask RLHF 与 chain-of-thought prompting 有什么关系？

→ 读取 wiki/index.md
→ 选择：concepts/rlhf.md, concepts/chain-of-thought.md, sources/instructgpt.md
→ 用 [[wiki-link]] 引用综合答案
→ 保存到 outputs/2026-04-05-rlhf-chain-of-thought.md
→ 将输出归档回 index.md
```

**答案被索引回去。** 这是第一个复利机制：你问的每个答案都让 wiki 为未来的查询变得更丰富。

### /kb-reflect —— 自我改进引擎

这是 Karpathy 描述中没有深入的部分。每次编译后，系统自动运行两阶段反思：

**阶段 1 —— 发现（仅索引）**：读取完整 `index.md`。仅使用单行摘要，识别 3-5 个连接候选：

- **跨领域主题** —— 一个出现在多个不相关来源中的概念
- **隐含关系** —— 两个看似相关但没有链接的概念
- **矛盾** —— 似乎持对立立场的来源
- **空白** —— 许多来源暗示但无专门文章的主题

**阶段 2 —— 综合（定向深度阅读）**：对于每个候选，阅读相关文章，如果证据足够充分，写一篇新的 `type: synthesis` 概念文章。

```yaml
---
tags: [synthesis, rlhf, attention]
type: synthesis
created_by: kb-reflect
---
```

综合文章是**二阶知识** —— 从知识中生成的知识。它们捕获了没有任何单一来源会表述的关联。这就是自我改进循环：wiki 不仅通过摄入更多内容变得更聪明，还通过推理已有内容来变得更聪明。

### /kb-lint —— 健康检查

Wiki 会积累技术债务：从未扩展的存根、被引用但从未撰写的概念、随时间分化出的近乎重复的文章。`/kb-lint` 运行五项检查：

- **薄弱文章** —— 少于 3 个实质性句子的概念文章
- **缺失概念** —— 来源中的 `[[concepts/X]]` 链接没有对应文章
- **断裂的 wikilink** —— 指向不存在文件的链接
- **重复概念** —— 近乎重复的 slug（attention 和 attention-mechanism）
- **新文章建议** —— wiki 中的空白，可选择网络搜索来补充数据

输出：终端摘要 + `outputs/` 中的完整报告，归档回 wiki。

### /kb-merge —— 概念合并

Lint 告诉你哪里有问题。Merge 修复一类特定问题：**重复概念**。

给定两个概念文章，LLM 阅读两者，写一篇包含各自所有实质性内容的干净合并文章，更新 `wiki/` 和 `outputs/` 中的所有反向链接，将被吸收的文章归档到 `wiki/archive/` 并附加重定向说明。每对合并一个 git commit，保持清晰的历史。

这让概念空间保持紧凑。随着 wiki 增长，merge 是防止它碎片化为 40 篇关于注意力机制的略有不同的文章的关键。

### /kb-output —— 渲染

有时你需要的是可交付物，而不只是一个答案。`/kb-output` 接受一个问题或现有输出文件，渲染为：

- **Marp 幻灯片** —— 用 `----` 分隔的 Markdown 幻灯片，每个概念一页，可在 Obsidian 中用 Marp 插件查看
- **Matplotlib 图表** —— Claude 根据内容选择正确的图表类型（网络图、时间线、柱状图），写一个独立的 Python 脚本，执行并保存 PNG

```bash
/kb-output --slides transformer 架构是什么？
/kb-output --chart 比较各论文中的注意力机制
```

### /kb-import —— 智能 Obsidian Vault 导入

大多数人已经有一个 Obsidian vault —— 几个月或几年收集的笔记。从零开始新建 KB 而忽略所有这些感觉很浪费，所以添加了导入 skill。

```bash
/kb-import ~/my-old-obsidian-vault
```

LLM 读取每个 `.md` 文件并分类：

- **概念文章** —— 结构化的、参考风格的笔记，有清晰定义 → 直接放入 `wiki/concepts/`，保留所有现有的 `[[wikilinks]]`
- **原始研究笔记** —— 瞬时笔记、来源引用、个人速记 → 放入 `raw/notes/` 等待编译

分类是基于判断的，不是基于规则的。一篇标题为"Attention Mechanism"、有结构化标题和清晰定义的笔记会被当作概念文章。一篇写着"注意力论文 —— 再读一遍，和 embeddings 有关"的笔记会被当作原始笔记。导入后，运行 `/kb-compile` 即可像处理其他摄入内容一样将原始笔记处理到 wiki 中。

### /kb-merge-vault —— 合并两个 KB Vault

如果你为工作和个人研究分别运行不同的 KB，或者想把协作者的 vault 合并到你的：

```bash
/kb-merge-vault ~/knowledge-base-work
```

非冲突内容直接复制。当两个 vault 对同一 slug 有概念文章时，LLM 阅读两者并综合出一篇干净的合并文章 —— 和 `/kb-merge` 相同的逻辑。合并完成后，`reflect_state.json` 被重置，这样下次 `/kb-reflect` 会在所有合并内容上运行完整的发现流程，找到跨越两个 vault 的关联。

## 搜索引擎

对于大型 wiki，当索引本身变得很长时，索引优先的导航模式开始吃力。添加了 `kb_search.py` —— 一个 LLM 在查询时可以调用的 Python CLI 工具：

```bash
python3 ~/knowledge-base/kb_search.py "attention mechanism" --top 5
```

输出是 JSON，易于解析。两种模式：

- **关键词搜索** —— TF-IDF 评分，标题 3 倍加权，快速，无依赖
- **语义回退** —— 如果关键词置信度低于阈值，用 sentence-transformers（all-MiniLM-L6-v2）编码查询并与缓存嵌入进行余弦相似度比较

搜索索引缓存在 `.kb/search_index.json`，每次 `/kb-compile` 后重建。这意味着搜索是即时的 —— 查询时无需嵌入计算。

语义回退对于知识库常见的那种查询很重要。"Transformers 如何处理长序列？" 应该找到关于注意力、位置编码和稀疏注意力的文章，即使这些确切词不出现在查询中。

## 完整循环

一切运行后，工作流是：

```bash
# 喂入内容 —— 每个来源 30 秒
/kb-ingest https://lilianweng.github.io/posts/2023-06-23-agent/
/kb-ingest https://arxiv.org/abs/2005.14165
/kb-ingest "我的直觉：RLHF 有效是因为人类偏好标签充当了策略行为的软先验"

# 编译 —— 处理所有内容并自动触发反思
/kb-compile

# 查询
/kb-ask LLM Agent 的关键组件是什么？
/kb-ask RLHF 与 chain-of-thought prompting 有什么关系？

# 维护
/kb-lint
/kb-merge
```

经过几个编译周期后，wiki 开始感觉像一个你可以查询的领域专家。综合文章浮现出你没有明确建立的关联。答案互相引用。知识在复利增长。

## 值得讨论的设计决策

**为什么用 Claude Code skills 而不是 Python 应用？**

Skills 是 Markdown 文件 —— 带有分步指令的纯文本。它们可读、可调试、任何人都可以修改而无需运行代码。当某些东西不对时，你编辑 skill 文件，下次调用时行为就变了。没有部署步骤，没有要安装的包，没有要运行的服务器。代价是执行是概率性的（LLM 遵循指令）而非确定性的（代码），但对于涉及判断的知识管理任务，这实际上是一个特性。

**为什么 Obsidian 是前端？**

Obsidian 的图谱视图是 LLM 构建的所有内容的免费可视化 —— LLM 写的每个 `[[wikilink]]` 都成为图中的一条边。你无需构建任何东西就能获得知识库的实时地图。Marp 插件将 `/kb-output --slides` 的结果变成可查看的幻灯片。反向链接面板显示引用任何给定概念的所有内容。

**为什么索引优先而不是 RAG？**

RAG 检索片段时不理解结构。索引优先模式让 LLM 像人类专家一样导航知识库 —— 使用目录而非向量搜索。这也意味着检索步骤是可解释的：你可以看到 LLM 选择阅读哪些文章以及为什么。限制是索引需要保持足够紧凑以始终适配上下文。在约 100-200 篇文章时这没问题；超过这个规模，搜索引擎成为主要导航工具。

**为什么用 Git？**

每次编译、反思、合并和问答会话都提交到 git。这给你一个理解如何演变的完整历史 —— 每篇被创建的综合文章、每个被合并的概念、每个被提出的问题。对概念文章运行 `git blame` 告诉你是哪个来源触发了它的创建。`git diff` 显示新来源编译时文章如何变化。Wiki 是版本控制的知识。

## 下一步

显而易见的方向：

- **过时检测** —— 文章没有新鲜度信号。一篇 2021 年描述"最先进技术"的来源现在已经过时。需要日期感知的 lint 检查。
- **主动发现** —— 系统目前等待你摄入。它应该根据检测到的空白告诉你下一步该摄入什么。
- **微调** —— Karpathy 在文章末尾提到了这一点。一旦 wiki 足够大，你可以用它作为训练数据将领域知识烘焙到模型权重中，而不是每次加载到上下文里。那就是终极形态：一个真正知道你知识库的模型，而不是每次查询时才阅读它的模型。

## 快速开始

仓库地址：[louiswang524/llm-knowledge-base](https://github.com/louiswang524/llm-knowledge-base)。九个 skills，一条设置命令：

```bash
git clone https://github.com/louiswang524/llm-knowledge-base.git
cd llm-knowledge-base
bash setup.sh ~/knowledge-base
```

你需要 Claude Code 和 Obsidian。图表和语义搜索的 Python 依赖是可选的：

```bash
pip install -r requirements.txt
```

然后打开 `~/knowledge-base` 作为 Obsidian vault 开始摄入。如果你有现有的 Obsidian vault，从 `/kb-import` 开始。

## 安全说明

个人知识库是私人的。使用本系统前，了解数据流向很重要。

**什么会离开你的机器**：每次运行 `/kb-ingest`、`/kb-compile`、`/kb-ask` 或其他 skill 时，你的原始文件和 wiki 文章内容会作为 Claude 对话上下文的一部分发送到 Anthropic 的 API。这是不可避免的 —— LLM 需要读取你的内容来处理它。适用 Anthropic 的数据处理策略。如果你在围绕商业敏感工作、医疗健康信息或有保密义务的信息构建知识库，在摄入前请先审查这些策略。

**你的 KB Git 仓库**：`setup.sh` 将 KB 目录初始化为 git 仓库。该仓库仅限本地 —— 不会被推送到任何地方。系统不会代你推送到远程。如果你选择将 KB 备份到远程（GitHub、GitLab 等），确保该仓库是私有的。公开的 KB 仓库会暴露一切 —— 原始笔记、编译的 wiki、综合文章、问答输出和搜索索引。

**什么不该放入**：如果你不想让某些内容被 LLM 处理或存储在版本控制中，就不要摄入它。系统没有"敏感"与"非敏感"内容的概念 —— 它对你喂给它的一切一视同仁。有些东西属于密码管理器，不属于知识库。

**安全默认值**：

- 保持 KB git 远程仓库为私有（或者根本不添加 —— 本地 git 历史对大多数用例足够了）
- 不要摄入凭据、token 或密钥
- 定期运行 `/kb-lint` —— "缺失概念"检查会浮现你可能不打算编译的原始文件引用的主题

## 最令人惊讶的发现

构建这个系统最让我惊讶的是：**综合文章**。我没预料到反思流程在小型 wiki 上能产生什么有趣的东西。但即使只有 10-15 个来源被编译，LLM 就找到了我没有明确建立的关联 —— 并把它们写成独立文章，立刻成为 wiki 中最有价值的内容。

这就是与搜索的质的不同。搜索找到你知道在那里的东西。这个系统浮现出你不知道自己知道的东西。
