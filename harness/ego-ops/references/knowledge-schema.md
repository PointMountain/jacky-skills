# Ego Ops 知识 schema

只将已验证、可复用且脱敏的事实写入 `references/sites/`。真实操作时按“全局索引 → 一个站点索引 → 一个 operation”的顺序读取。

## 一级站点索引

路径：`references/sites/index.md`

```markdown
---
format: ego-site-index
updated: YYYY-MM-DD
---

# 站点索引

| site | domains | aliases | last_verified | reference |
| --- | --- | --- | --- | --- |
| <site-slug> | <canonical-domain> | <产品别名> | YYYY-MM-DD | [说明](<site-slug>/index.md) |
```

只放路由信息，不写页面步骤、临时对象或完整响应。

## 站点索引

路径：`references/sites/<site>/index.md`

```markdown
---
site: <site-slug>
domains:
  - <canonical-domain>
aliases:
  - <产品别名>
updated: YYYY-MM-DD
---

# <站点名称>

## 平台特征

只记录会影响多个 operation 的登录、导航或加载事实。

## 操作目录

| operation | intent | risk | last_verified | reference |
| --- | --- | --- | --- | --- |
| <operation-slug> | <一句话目的> | low | YYYY-MM-DD | [说明](operations/<operation-slug>.md) |
```

一个产品的不同域名和环境优先复用同一个站点 slug，在 `domains` 或 `aliases` 中维护映射；不要因环境复制同一份操作经验。

## Operation

路径：`references/sites/<site>/operations/<operation>.md`

Frontmatter 必须包含：

```yaml
site: <site-slug>
operation: <operation-slug>
title: <中文标题>
risk: low | medium | high
last_verified: YYYY-MM-DD
```

正文必须按以下顺序包含八个章节：

1. `目标`：可复用目标与适用边界。
2. `前置条件与授权`：登录、角色、唯一对象与不可逆确认边界。
3. `入口`：不含敏感参数的稳定 URL 或导航语义。
4. `已验证步骤`：本次真实走通的语义步骤，不用坐标、瞬态引用或动态标识。
5. `检查点`：结果不确定时应停止的位置。
6. `成功标准`：证明业务结果真正生效的可观察结果。
7. `失败模式与恢复`：只记录已证实且可恢复的失败。
8. `验证证据`：最小、脱敏的 URL、状态、列表变化或确认提示。

不要保存认证材料、完整响应、个人数据、动态标识、临时元素引用、坐标或未完成占位符。验证器只证明目录结构与安全边界；页面步骤是否仍然正确，必须由实时浏览结果证明。
