# WebFlow V3（Lab）

WebFlow 把一句产品意图推进成真实项目代码、浏览器证据和可选生产 URL。V3 使用 Markdown 解释工作流与阶段交接，使用 Node.js 的 JSON/JSONL 运行时保存必须精确重放的机器事实。

## 一、包含的 Skills

| Skill | 职责 |
| --- | --- |
| `web-flow` | 入口、渐进导航、profile 与视觉门调度 |
| `web-flow-research` | 内容来源、参考证据和素材需求 |
| `web-flow-prototype` | wireframe、full prototype、G1/G2 |
| `web-flow-design` | CSS design tokens 与布局契约 |
| `web-flow-build` | sourceDir 实现、更新安全、真实预览与 G3 |
| `web-flow-benchmark` | 独立 must-pass 和两轮有限评审 |
| `web-flow-deploy` | provider-neutral 预检、发布和线上验活 |

每个生产阶段拥有自己的 memory candidate；没有中心 memory Skill。只有真实错误、根因已验证且可能复现时，候选才回到发生错误的阶段。

## 二、前置条件

- Node.js 20 或更高版本；运行时与测试都使用原生 ESM 和 `node:test`。
- `j-skills` 已可用。
- 目标项目需要 update 时必须是 Git 仓库；create 模式的 sourceDir 必须不存在或为空。

## 三、显式链接

Lab 不属于默认分发面：仓库根 `install.sh` 不会扫描 `labs/`。需要使用时显式链接全部七个 Skill：

```bash
export JACKY_SKILLS_DIR="${JACKY_SKILLS_DIR:-$HOME/jacky-github/jacky-skills}"

j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-research"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-prototype"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-design"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-build"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-benchmark"
j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/web-flow-deploy"
```

`web-flow/archive/` 只保存历史方案，不参与当前运行、package validation 或安装。任何迁移前的 memory 目录也不属于共享运行契约。

## 四、V3 运行证据

目标项目中的 `.web-flow/runs/<run-id>/` 保存：

- `events.jsonl`：事件事实源；
- `run.json`：可重建投影；
- `artifacts.jsonl`：不可变 artifact revisions；
- reviews、gates、deploy、usage 与 retrospective 的 Markdown 证据。

源码始终写入项目内 `sourceDir`，不会复制进 runDir。attended 模式在 G1/G2/G3 等用户决定；unattended 只能依据绑定的独立评审继续，不能自动获得部署授权。

## 五、自检

在仓库根运行：

```bash
node --test labs/web-flow/web-flow/tests/*.test.mjs
node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs validate-package labs/web-flow
python3 -m unittest tests.test_trigger_contracts -v
```

运行时校验通过只说明结构、事件、hash、路径和有限敏感模式一致；真实页面仍需 build/deploy rubric 要求的 HTTP、browser、桌面/移动和 console 证据。

## 六、部署边界

请求部署不等于授权。用户只有在 G3 后、finalize 前才能显式授权发布；发布前必须重新 preflight。未授权或发布失败时保留已批准 preview，并以真实 residual 结束，不能伪造成功 URL。
