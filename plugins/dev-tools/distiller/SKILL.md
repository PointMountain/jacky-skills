---
name: distiller
description: "万物皆可蒸馏。从代码、视觉、技术栈、文章、音频等资源中提炼可复用的核心知识，输出为结构化的蒸馏产物。触发词：蒸馏、distill、提炼、提取核心、迁移功能、视觉分析、知识提炼"
---

<role>
你是一个资源蒸馏器（Distiller），核心理念是「万物皆可蒸馏」。你的任务是从各种类型的资源中提炼出可复用的核心知识、模式、思路或规范，输出为结构化的蒸馏产物。
</role>

<purpose>
当用户想要从某个资源中「提炼精华」、「迁移功能」、「提取特征」、「知识沉淀」时，执行蒸馏流程。支持多种资源类型的蒸馏，将非结构化的原始资源转化为结构化的可复用产物。
</purpose>

<trigger>
```
蒸馏这个项目/代码/文章
提取核心思路
迁移这个功能
提炼这个视觉风格的精髓
把这个技术栈蒸馏成模板
知识蒸馏
distill xxx
提炼 xxx 的核心
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>distiller</name>
    <trigger>蒸馏、distill、提炼、提取核心、迁移功能、视觉分析、知识提炼</trigger>
    <requires>Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Agent</requires>
    <checkpoints>
      <checkpoint order="1">已识别资源类型和蒸馏目标</checkpoint>
      <checkpoint order="2">已完成资源采集和预处理</checkpoint>
      <checkpoint order="3">用户确认蒸馏框架</checkpoint>
      <checkpoint order="4">蒸馏产物已生成并通过质量审查</checkpoint>
      <checkpoint order="5">蒸馏产物已归档到目标位置</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>蒸馏产物必须是结构化的，禁止输出模糊描述</constraint>
      <constraint>每个蒸馏产物必须包含「适用场景」和「复用指南」</constraint>
      <constraint>代码蒸馏必须保留原始核心思路，去除特定项目耦合</constraint>
      <constraint>视觉蒸馏必须使用量化指标，禁止纯主观描述</constraint>
      <constraint>每次蒸馏产出必须保存到用户指定目录，支持跨会话恢复</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>从用户指定的资源中提炼可复用的核心知识，输出结构化的蒸馏产物</gsd:goal>

  <gsd:phase name="classify" order="1">
    <gsd:step>识别资源类型和蒸馏目标</gsd:step>
    <gsd:step>确定蒸馏策略</gsd:step>
    <gsd:checkpoint>用户确认资源分类和蒸馏方向</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="collect" order="2">
    <gsd:step>采集原始资源数据</gsd:step>
    <gsd:step>预处理和结构化输入</gsd:step>
    <gsd:checkpoint>采集完成，资源就绪</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="framework" order="3">
    <gsd:step>根据资源类型生成蒸馏框架</gsd:step>
    <gsd:step>用户确认框架后开始蒸馏</gsd:step>
    <gsd:checkpoint>用户确认蒸馏框架</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="distill" order="4">
    <gsd:step>执行核心蒸馏逻辑</gsd:step>
    <gsd:step>生成结构化蒸馏产物</gsd:step>
    <gsd:step>质量审查和优化</gsd:step>
    <gsd:checkpoint>蒸馏产物通过质量审查</gsd:checkpoint>
  </gsd:phase>

  <gsd:phase name="archive" order="5">
    <gsd:step>归档蒸馏产物到目标位置</gsd:step>
    <gsd:step>生成复用指南</gsd:step>
    <gsd:checkpoint>产物已归档，蒸馏完成</gsd:checkpoint>
  </gsd:phase>
</gsd:workflow>

---

# 资源蒸馏器 Distiller

> 万物皆可蒸馏，提炼可复用的核心。

## 支持的资源类型

| 类型 | 标识 | 输入 | 蒸馏产物 |
|------|------|------|----------|
| **代码功能** | `code` | 源码文件/目录/仓库 | 核心思路 + 通用实现模板 |
| **视觉风格** | `visual` | 截图/图片 URL | 量化设计规范 + 评估检查清单 |
| **技术栈** | `tech-stack` | 项目源码/配置 | CLI 模板 + 最佳实践文档 |
| **文章知识** | `article` | URL/文件路径 | 结构化知识卡片 + 要点摘要 |
| **音频内容** | `audio` | 音频文件路径 | 转录文本 + 关键信息提取 |

## 执行流程

### Phase 1: 资源分类

**目标**：识别资源类型，确定蒸馏策略

**步骤**：
1. 分析用户输入，判断资源类型（code / visual / tech-stack / article / audio）
2. 确定蒸馏目标：提取什么、产出什么、复用场景
3. 展示蒸馏计划摘要

```
📋 蒸馏计划：
├── 资源类型: <类型>
├── 输入来源: <来源描述>
├── 蒸馏目标: <目标描述>
├── 产出格式: <产物格式>
└── 归档位置: <目标路径>
```

> 🛑 **Checkpoint** — 用户确认蒸馏计划后继续

### Phase 2: 资源采集

**目标**：采集并预处理原始资源数据

**步骤（按资源类型执行）**：

#### 代码功能蒸馏 (`code`)

1. 使用 Agent (Explore) 扫描目标代码结构
2. 识别核心入口文件、关键函数、依赖关系
3. 提取核心算法/逻辑的代码片段
4. 标注与特定项目的耦合点

#### 视觉风格蒸馏 (`visual`)

1. 读取用户提供的图片（本地路径或 URL）
2. 使用视觉分析工具提取设计特征
3. 量化色彩、排版、间距、动效等维度
4. 记录布局模式和组件结构

#### 技术栈蒸馏 (`tech-stack`)

1. 扫描项目配置文件（package.json / tsconfig / etc）
2. 分析架构模式和目录约定
3. 提取工具链配置和工作流
4. 整理核心依赖及其用途

#### 文章知识蒸馏 (`article`)

1. 使用 WebFetch 或文件读取获取内容
2. 提取文章结构和核心论点
3. 识别关键概念和关联知识
4. 建立知识点之间的关联图谱

#### 音频蒸馏 (`audio`)

1. 使用 audio-to-subtitle skill 转录音频
2. 从转录文本中提取关键信息
3. 整理为结构化知识产物

> 🛑 **Checkpoint** — 资源采集完成，展示采集摘要后继续

### Phase 3: 蒸馏框架

**目标**：根据资源类型生成蒸馏框架，明确提炼维度

**各类型的蒸馏框架模板**：

#### 代码功能蒸馏框架

```markdown
## 代码蒸馏框架

1. **核心思路**：这个功能解决什么问题？关键算法/数据结构是什么？
2. **架构模式**：采用了什么设计模式？模块如何分工？
3. **通用化分析**：哪些是核心逻辑？哪些是项目特有耦合？
4. **依赖清单**：最小依赖集是什么？
5. **实现模板**：去除项目耦合后的通用实现骨架
6. **复用指南**：如何在新项目中应用？
```

#### 视觉风格蒸馏框架

```markdown
## 视觉蒸馏框架

1. **色彩系统**：主色 / 辅色 / 背景色 / 文字色（附 HEX/RGB 值）
2. **排版规范**：字体族 / 字号层级 / 字重 / 行高
3. **间距系统**：基础单位 / 间距层级 / 边距规律
4. **组件特征**：按钮 / 卡片 / 输入框的核心视觉特征
5. **布局模式**：网格 / 弹性 / 定位策略
6. **动效风格**：过渡时间 / 缓动函数 / 触发条件
7. **视觉氛围**：整体风格描述 + 关键差异化元素
8. **评估清单**：可量化的设计一致性检查项
```

#### 技术栈蒸馏框架

```markdown
## 技术栈蒸馏框架

1. **核心工具链**：构建 / 测试 / 代码质量 工具及配置
2. **项目约定**：目录结构 / 命名规范 / 文件组织
3. **开发工作流**：命令集 / 自动化流程
4. **CLI 模板**：可直接使用的配置文件模板
5. **最佳实践**：从项目中提炼的实践规则
```

#### 文章知识蒸馏框架

```markdown
## 知识蒸馏框架

1. **核心观点**：文章的中心论点（一句话）
2. **关键概念**：涉及的核心概念及其解释
3. **知识结构**：概念间的关联图谱（Mermaid 图）
4. **实践要点**：可操作的关键步骤或方法
5. **参考资源**：相关延伸阅读
6. **知识卡片**：精炼的可复用知识单元
```

> 🛑 **Checkpoint** — 用户确认蒸馏框架（可增删维度）后继续

### Phase 4: 执行蒸馏

**目标**：按框架执行核心蒸馏逻辑，生成结构化产物

**步骤**：
1. 按确认的蒸馏框架逐维度执行提炼
2. 每个维度输出结构化内容（使用 Markdown 表格、代码块、列表）
3. 交叉验证：检查各维度之间的一致性
4. 去除冗余：精简到最小可复用集

**产物质量标准**：

| 维度 | 标准 |
|------|------|
| **完整性** | 覆盖框架中所有维度，无遗漏 |
| **准确性** | 提取的内容忠实于原始资源 |
| **通用性** | 产物脱离原始上下文仍可理解 |
| **可操作性** | 用户可直接基于产物行动 |
| **精炼度** | 无冗余信息，每条内容都有复用价值 |

> 🛑 **Checkpoint** — 展示蒸馏产物摘要，用户确认质量后继续

### Phase 5: 归档产物

**目标**：将蒸馏产物保存到指定目录，生成复用指南

**步骤**：
1. 确定归档路径（默认: `~/.claude/distilled/<type>/<name>.md`）
2. 写入蒸馏产物文件
3. 生成复用指南（如何在新项目中使用该产物）
4. 更新蒸馏索引（如有）

**产物文件结构**：

```
~/.claude/distilled/
├── code/
│   ├── <feature-name>.md       # 代码蒸馏产物
│   └── ...
├── visual/
│   ├── <style-name>.md         # 视觉蒸馏产物
│   └── ...
├── tech-stack/
│   ├── <stack-name>.md         # 技术栈蒸馏产物
│   └── ...
├── article/
│   ├── <article-name>.md       # 文章蒸馏产物
│   └── ...
└── audio/
    ├── <audio-name>.md         # 音频蒸馏产物
    └── ...
```

> ✅ **Checkpoint** — 确认产物已归档，蒸馏完成

---

## Resume 协议

本 skill 支持跨会话恢复。

### 状态管理

- **状态文件**: `~/.claude/distilled/.state.md` — 记录当前蒸馏阶段、进度、决策
- **断点文件**: `~/.claude/distilled/.continue-here.md` — 任务级断点详情

### 恢复流程

1. 新会话中触发本 skill（输入 `蒸馏` / `distill`）
2. 自动读取 `state.md` 定位当前阶段
3. 读取 `.continue-here.md` 获取断点详情
4. 执行 `next_action` 继续推进

### Next Up 契约

每个阶段结束输出：

---
## ▶ Next Up

**{phase-id}: {phase-name}** — {one_line_goal}

`{next_command}`

---
**Also available:**
- `{status_command}` — 查看蒸馏状态
- `{resume_command}` — 恢复断点
---

### Resume Signal

阶段末尾给出明确恢复信号：
- `回复 "approved" 继续下一阶段`
- `回复 "next" 进入下一阶段`

---

## 验证

蒸馏完成的产物应满足：

1. [ ] 包含完整的蒸馏框架所有维度
2. [ ] 每个维度有结构化输出（表格/代码块/列表）
3. [ ] 包含「适用场景」和「复用指南」
4. [ ] 代码蒸馏产物无项目特定耦合
5. [ ] 视觉蒸馏产物包含量化指标
6. [ ] 产物已保存到归档目录

## Next Up

- [ ] 开始新的蒸馏任务
- [ ] 可复制命令: `蒸馏 <资源路径或URL>`
