# ob-bridge 设计文档

> 终端 Claude Code ⇄ Obsidian 的双向上下文桥（前身 ob-to-claudian）。
> 重建于 2026-06-14（原 SPEC 在改名时丢失）。SKILL.md 为活文档，本文仅设计记录。

## 一、解决什么

终端结论易逝；换到 Obsidian 的 Claudian / 新 AI 时上下文续不上。本 skill 用 vault 的 `_inbox/` 作中转区，双向打通：

- **卸货（dump）**：把工作产物（md/html/图片）+ 可选完整会话 transcript 写进 `_inbox/{日期}-{话题}/`。
- **接手（resume）**：新会话从 `_inbox/` 发现并读回之前的上下文继续干。

不进 wiki、无 ceremony。

## 二、与现有 ob-* 边界

- `ob-collect` 采外部内容入 raw/；`ob-topic`/`ob-project-log` 直接写 wiki/。
- 本 skill 卸的是 **Claude 自己的工作产物 + 完整上下文**，落 `_inbox/`，给人/新 AI 读回。填补「人工决策驱动的工作产物中转 + 跨环境续接」空位。

## 三、关键设计决策（迭代结论）

1. **路径绝不写死**：`$OBSIDIAN_REPO` 运行时解析（ob-router→env→CLAUDE.md→询问）；skill 内零真实路径/用户名/vault名/密钥。
2. **新人视角前置探测**：ob-router / advanced-uri / claudian 全探测 + 缺失降级；深链用核心 `obsidian://open`（零插件依赖）。
3. **默认无摩擦**：卸货不设确认门。
4. **不写交接文件**：曾试 `_next.md` 一行交接，实测无意义已移除。
5. **完整上下文 = 桥接 transcript**：摘要有损（< 1%），要"接着干"得带完整 transcript。
   - 安全：transcript 几乎必含密钥。默认 sync-ignore（不上云）/ 用户接受上云（个人单用户私有云）可跳过；打码始终 best-effort（运行时读用户配置，skill 不内置密钥值）。
6. **接手端**：query `_inbox/` 列出会话 + 文件结构（transcript=全量 / md=摘要 / html·图片=产物），按用户选择读回。**只读**。

## 四、落地

- 位置：`jacky-skills/plugins/obsidian-tools/ob-bridge/`
- plugin.json：skills 数组 `./ob-bridge/`（前身 `./ob-to-claudian/`，2.11.0 引入）
- `j-skills link` + `install -g`

## 五、待解（可选增强）

- **新 AI 自动发现**：纯零上下文的新 AI 不会主动去 `_inbox/` 找。可在 vault 的 CLAUDE.md 加一行指针（「上下文桥在 `_inbox/`，用 ob-bridge 恢复」），让 Claudian 启动读 vault CLAUDE.md 时自动知晓。**待用户确认是否加**。
