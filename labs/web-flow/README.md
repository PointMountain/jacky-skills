# web-flow（预览版）

`web-flow` 是一套用于构建真实网站的轻量 Workflow。主 Skill 负责调度，阶段能力保持独立，并且只在进入对应阶段时渐进加载。

## 包含的 Skill

| Skill | 作用 |
|---|---|
| `web-flow` | 总入口与渐进调度 |
| `web-flow-research` | 调研参考、内容来源与素材需求 |
| `web-flow-prototype` | 线框图和视觉原型 |
| `web-flow-design` | Design Tokens 与布局契约 |
| `web-flow-build` | 页面实现、动效与真实预览 |
| `web-flow-deploy` | 部署预检、发布与线上验活 |
| `web-flow-benchmark` | 独立评测与有限返工 |

每个 Skill 独立维护自己的 `memory/` 模块；没有中心化的 memory Skill。通过三项验证的错误候选只回写到发生错误的 Skill。

## 预览版边界

- Skill 名称、阶段契约和目录结构仍可能调整。
- 默认只按当前任务加载必要阶段。
- 未获得用户明确授权时不会执行真实部署。
