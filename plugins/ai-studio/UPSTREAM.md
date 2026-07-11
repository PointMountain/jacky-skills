# AI Studio · 上游同步与能力映射

> 本文件是 `ai-studio` 域的**治理入口**：记录哪些 skill 来自上游、能力矩阵归属，以及如何跟上游 garden-skills 保持同步。

## 一、能力矩阵映射

`ai-studio` 收敛「AI 外接生成能力」。物理上平铺（不做三级目录，遵循「复杂度后长出来」原则），逻辑分类见下表：

| 能力格 | Skill | 层级 | 来源 |
|--------|-------|------|------|
| 🖼️ 图像 | `gpt-image-2` | 底座（通用图像生成/编辑） | 上游 garden-skills |
| 🖼️ 图像 | `warm-doodle` | 场景（技术文章手绘插图） | 本地原生 |
| 🖼️ 图像 | `article-with-images` | 场景（Obsidian 图文/封面） | 本地原生 |
| 🔊 音频 | `subtitle-to-audio` | 底座（TTS 文本转语音） | 本地原生 |
| 🌐 网页 | `web-design-engineer` | 底座（精品前端/网页生成） | 上游 garden-skills |
| 🎬 视频/演示 | `web-video-presentation` | 场景（口播稿→网页视频演示） | 上游 garden-skills |

> 空缺待封装（**不预建空目录**，能力真正做出来时再新增）：🎙️ 播客生成、📊 传统 PPT。

## 二、上游同步锚点

| 项 | 值 |
|----|-----|
| 上游仓库 | https://github.com/ConardLi/garden-skills |
| 分支 | `main` |
| **同步基线 commit** | `fbd6453c984e2a150c9553efe3075e1f62338df8` |
| 同步日期 | 2026-07-11 |
| 纳管的上游 skill | `gpt-image-2`、`web-design-engineer`、`web-video-presentation` |
| 未纳管的上游 skill | `kb-retriever`（不需要）、`beautiful-article`（待评估） |

**约定**：上游三个 skill 原样跟随上游，**本地不做改造**（保持可干净同步）。若确需本地化，另起 `*.local` 覆盖或在本文件记录 diff，不直接改原文件。

## 三、同步操作 SOP

每次想跟上游对齐时：

```bash
# 1. 拉上游最新（走代理，见全局 CLAUDE.md）
TMP=$(mktemp -d)
https_proxy=http://127.0.0.1:10802 http_proxy=http://127.0.0.1:10802 \
  git clone --depth 50 --filter=blob:none --sparse --branch main \
  https://github.com/ConardLi/garden-skills.git "$TMP"
git -C "$TMP" sparse-checkout set skills

# 2. 看基线之后大佬改了哪些纳管 skill
git -C "$TMP" log --oneline fbd6453c984e2a150c9553efe3075e1f62338df8..HEAD -- \
  skills/gpt-image-2 skills/web-design-engineer skills/web-video-presentation

# 3. 逐个 diff 决定是否吸收
diff -ru plugins/ai-studio/gpt-image-2 "$TMP/skills/gpt-image-2"

# 4. 吸收后，把本文件「同步基线 commit」更新为新的 HEAD，并记录同步日期
```

> 本地原生 skill（warm-doodle / article-with-images / subtitle-to-audio）不受上游同步影响，自由演进。

## 四、研究出处

设计理念研究见 `garden-skills-study/`（ConardLi/garden-skills 的学习笔记），核心：`explorer/03-skill-design-philosophy.md`。
