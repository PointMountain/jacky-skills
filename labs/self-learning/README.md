# Self Learning Lab

> 预览性质的 AI 自主学习与创作实验：从视频、文章和链接中理解技术知识，并把理解转化为可运行、可复核的成果。

Self Learning 指 Agent 自主获取或阅读素材、识别技术知识、补充调研、实践并验证结果。它不涉及模型训练、微调或修改模型权重，也不以自动创建 Agent Skill 为目标。

## 包含内容

- `self-learning`：通用入口。保留用户指定的意图与检查门，根据任务现场组合能力和执行路径。
- `self-learning-hyperframes`：教学音视频完整复现为 HyperFrames Demo 的场景适配器。

## 实验原则

- 固定意图，动态路径：固定目标、强依赖、顺序、授权边界、人工检查门和验收，其余路径由 Agent 根据证据调整。
- 简单任务直接执行；复杂、长时间、无人值守、需要恢复或有指定创作顺序的任务，才生成薄 Workflow。
- 输入可来自本地音视频、YouTube、B 站、抖音、网页、文章或文案，也可由 Agent 围绕主题寻找素材。
- 输出按需选择 Demo、教程、笔记、代码、截图、渲染和测试，不把 HyperFrames 或视频当作唯一形态。
- 通过真实运行、观看和测试验证成果，并保留来源与残留限制。

## 使用方式

`labs/` 中的实验 Skill 不参与仓库批量安装。需要试用时显式链接目标 Skill：

```bash
j-skills link "$JACKY_SKILLS_DIR/labs/self-learning/self-learning"
j-skills link "$JACKY_SKILLS_DIR/labs/self-learning/self-learning-hyperframes"
```

这些接口仍处于探索阶段，名称、边界和组合方式可能随真实案例调整。
