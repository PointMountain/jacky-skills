# WebFlow 运行时状态

> Markdown 负责解释和导航；JSON/JSONL 只承载必须精确重放的机器状态。权威实现位于 [`scripts/lib/`](../scripts/lib/) 和 [`web-flow-runtime.mjs`](../scripts/web-flow-runtime.mjs)。

## 一、状态目录

每轮运行写入目标项目：

```text
.web-flow/runs/<run-id>/
├── events.jsonl
├── run.json
├── artifacts.jsonl
├── preexisting-state.md
├── reviews/
├── gates/
├── deploy/
├── skill-usage.md
└── retrospective.md
```

- `events.jsonl`：唯一事件事实源，按序追加，不允许改写。
- `run.json`：事件重放得到的投影；丢失或落后时可 reconcile。
- `artifacts.jsonl`：工件 revision 账本；路径与内容 hash 共同确认身份。
- Markdown 证据：给人阅读，同时由事件记录路径和原始字节 hash。

## 二、CLI 入口

```bash
node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs init <project-root> \
  --input-file <input.json> --metadata-file <event.json>

node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs reconcile \
  <project-root>/.web-flow/runs/<run-id>

node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs validate-run \
  <project-root>/.web-flow/runs/<run-id>

node labs/web-flow/web-flow/scripts/web-flow-runtime.mjs finalize \
  <project-root>/.web-flow/runs/<run-id> --input-file <finalize.json>
```

阶段变化、artifact、review、gate、source 和 deploy 都有窄命令入口。先用命令产生 typed event，再读取输出投影；不要直接编辑机器文件。

## 三、源码安全

create 模式只能写新的、空的 sourceDir。update 模式初始化时记录 Git 基线和已有 dirty 文件；进入 build 前必须通过 `source plan` 明确 allowlist。若 allowlist 与既有 dirty 文件重叠，必须得到逐路径确认。

build 后运行 `source verify`：不在 allowlist 的变化、既有 dirty 内容漂移、symlink、逃逸路径都会阻断。`.web-flow/` 与运行时管理的 `.gitignore` 变化按固定规则排除，不能扩大成通用忽略。

## 四、artifact 与证据绑定

artifact 首次登记为 revision 1；内容变化只能追加 revision。跨 run 复用要记录原 run、artifact ref 和 SHA-256，且当前字节必须一致。

review、gate、deployment 和 finalize 不只检查“文件存在”，还检查：

1. 事件中记录的路径；
2. 文档原始字节 hash；
3. 当前 artifact revision 和 live hash；
4. producer stage、reviewer 独立性与 gate 顺序。

因此修改已登记 Markdown 也会被视为证据漂移；应创建下一版本文件并追加事件。

## 五、恢复与终止

`events.jsonl` 已追加而 `run.json` 未替换时，执行 `reconcile` 重建投影。投影领先、事件序号断裂、hash 不一致则拒绝继续，先修复真实损坏原因。

终态前运行一般验证；`finalize` 会预验证固定 usage/retrospective 文档，追加一个 terminal event，再执行 `validate-run --require-terminal`。若只落下 terminal event，重复 finalize 会先 reconcile，而不会追加第二个终态。

## 六、隐私边界

机器状态和 run 内 Markdown 都接受有限模式扫描：已知凭证形态、认证头、用户绝对路径、localhost 和私网 URL 会被拒绝。这个扫描是最后防线，不代表可以先写秘密再依赖自动清理；证据应从源头只保存相对路径和公开 URL。
