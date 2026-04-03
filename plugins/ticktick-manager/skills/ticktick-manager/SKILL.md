---
name: ticktick-manager
description: "TickTick（滴答清单）日程管理 Skill。查看今日/昨日任务、创建/修改任务、管理项目清单、日程复盘补全。触发词：日程、待办、ticktick、tt、计划、任务、滴答清单、一天结束、日程复盘、时间都去哪了、今天干了什么、补全日程、完善行程、回顾今天。"
---

# ticktick-manager

TickTick（滴答清单）日程管理 Skill，提供完整的任务读取、写入和项目管理功能。

<gsd:workflow>
  <gsd:meta>
    <name>ticktick-manager</name>
    <trigger>日程、待办、ticktick、tt、计划、任务、滴答清单、一天结束、日程复盘、时间都去哪了、今天干了什么、补全日程、完善行程、回顾今天</trigger>
    <requires>MCP dida365 工具, AskUserQuestion</requires>
    <checkpoints>
      <checkpoint order="0">MCP 配置完成后，提示用户重启 Claude Code 并验证连接</checkpoint>
      <checkpoint order="1">首次查询后展示结果，等待用户下一步指令</checkpoint>
      <checkpoint order="2">执行修改前确认操作内容</checkpoint>
      <checkpoint order="3">所有询问结束后，展示汇总并确认是否创建任务</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>Phase 0 必须首先执行，检测 MCP 工具可用性</constraint>
      <constraint>MCP 未配置时，必须提供安装引导，不得直接报错退出</constraint>
      <constraint>自动配置时，使用 Streamable HTTP 远程连接方式（OAuth 授权），无需本地安装</constraint>
      <constraint>配置文件修改前，必须备份原文件</constraint>
      <constraint>禁止硬编码 projectId，首次通过 list_projects 获取后缓存映射，失败时才刷新</constraint>
      <constraint>禁止串行调用 API，必须并行调用（已完成/未完成/项目列表）</constraint>
      <constraint>用户说"更新/修改"时，直接查找现有任务，不要问"是要修改还是要创建"</constraint>
      <constraint>日程复盘由主会话直接执行，3步完成：①并行获取数据 ②AskUserQuestion展示空白时段 ③批量创建任务</constraint>
      <constraint>历史任务（时间已过）必须自动标记为完成</constraint>
      <constraint>时区规则：API 返回的时间为 UTC（+0000/Z 后缀），必须 +8 转换为上海本地时间。例如 API 返回 18:40+0000 → 上海时间 02:40（次日）</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>提供完整的 TickTick 任务读取、写入和项目管理功能</gsd:goal>

  <gsd:phase name="前置检测" order="0">
    <gsd:step>检测 dida365 MCP 工具是否可用</gsd:step>
    <gsd:step>如果不可用，提供 Streamable HTTP 远程连接引导</gsd:step>
    <gsd:step>提供多客户端配置参考</gsd:step>
  </gsd:phase>

  <gsd:phase name="任务读取" order="1">
    <gsd:step>并行调用 MCP 工具获取今日任务数据</gsd:step>
    <gsd:step>合并数据并按时间排序</gsd:step>
    <gsd:step>输出格式化表格</gsd:step>
    <gsd:step>自动检测时间紧张度分析需求</gsd:step>
  </gsd:phase>

  <gsd:phase name="任务写入" order="2">
    <gsd:step>解析用户输入，提取任务名称和时间</gsd:step>
    <gsd:step>智能清单分配</gsd:step>
    <gsd:step>判断是否为历史任务</gsd:step>
    <gsd:step>创建任务并处理完成状态</gsd:step>
  </gsd:phase>

  <gsd:phase name="项目管理" order="3">
    <gsd:step>获取所有项目清单</gsd:step>
    <gsd:step>分类展示活跃/已归档清单</gsd:step>
  </gsd:phase>

  <gsd:phase name="日程复盘" order="4">
    <gsd:step>并行获取今日任务（已完成+未完成）+ 历史7天数据 + 项目列表</gsd:step>
    <gsd:step>生成时间轴，识别 ≥30min 空白时段，智能推断推荐活动</gsd:step>
    <gsd:step>使用 AskUserQuestion 展示所有空白时段选项</gsd:step>
    <gsd:step>根据用户选择调用 batch_add_tasks 批量创建</gsd:step>
  </gsd:phase>
</gsd:workflow>

<commands>
```
/ticktick         # 主命令，显示今日任务
/tt               # 主命令别名
/ticktick today   # 今日任务
/ticktick tomorrow # 明日任务
/ticktick add <任务> # 创建任务
/ticktick done <任务ID> # 完成任务
/ticktick review  # 日程复盘，补全空白时段
```
</commands>

## 核心规则

### 时区处理

API 返回的时间为 **UTC**（`+0000` 或 `Z` 后缀），**必须 +8 转换为上海本地时间**。

- `18:40:00+0000` → 上海时间次日 `02:40`
- `05:30:00Z` → 上海时间 `13:30`
- `timeZone: "Asia/Shanghai"` 仅表示用户时区设置，不影响时间存储格式

输出时只显示 `HH:mm`，不显示日期。

### projectId 缓存策略

首次使用时调用 `list_projects` 获取清单并缓存映射：

```json
{
  "紫": "67bb37ad7a1a51746f577c69",
  "黄": "67bb37638f1311746f5777dd",
  "红": "67bb3747071251746f57750e",
  "绿": "67bb37a279e011746f577c4d",
  "蓝": "645afe5ff858510297fb8690",
  "Inbox": "inbox1019223045"
}
```

**缓存规则**：同一会话内只调一次 `list_projects`，后续直接用缓存。仅在 API 报 projectId 无效时才刷新。

### 智能清单分配

| 任务关键词 | 清单 | projectId |
|-----------|------|-----------|
| 睡觉、休息 | 紫（休息） | 紫的 ID |
| 午休、午睡、午饭、午餐、早饭、早餐、晚饭、晚餐、吃饭 | 黄（午休） | 黄的 ID |
| 游戏、娱乐、看电影、刷剧 | 红（娱乐） | 红的 ID |
| 其他 | Inbox | inbox |

> 映射通过 `list_projects` 动态获取，禁止硬编码。

### 时间解析

自然语言 → 标准时间：
- "晚上7:30" → 19:30
- "下午3点" → 15:00
- "早上9点到10点" → 09:00-10:00

## 执行流程

### Phase 0: 前置检测

尝试调用 `list_projects`，成功则跳过。失败时提供安装引导：

**一键配置（推荐）**：
```bash
claude mcp add --transport http dida365 https://mcp.dida365.com
```

**其他客户端**：
| 客户端 | 配置文件 | 格式 |
|--------|---------|------|
| Cursor | `.cursor/mcp.json` | `{"mcpServers":{"dida365":{"url":"https://mcp.dida365.com"}}}` |
| VS Code | `.vscode/mcp.json` | `{"servers":{"dida365":{"type":"http","url":"https://mcp.dida365.com"}}}` |
| Claude Desktop | Customize > Connectors | URL: `https://mcp.dida365.com` |
| ChatGPT | 设置 > 开发人员模式 | URL: `https://mcp.dida365.com` |

配置后运行 `/mcp` 完成 OAuth 授权，重启 Claude Code。

> 🛑 **Checkpoint**：配置完成后提示用户重启并验证连接

### Phase 1: 任务读取

**并行调用**（一次发出，不等）：
- `list_undone_tasks_by_time_query`（query: "today"）
- `list_completed_tasks_by_date`（今日日期范围）

**处理**：
1. 所有时间 +8 转上海时间
2. 合并已/未完成，按开始时间排序
3. 输出表格，标注状态（✅已完成 / ⏳待办 / ⚠️已过期 / 🔜即将）

**自动触发时间分析**（用户问"紧不紧张/满不满/够不够"时）：

| 紧张度 | 判定 | 标准 |
|--------|------|------|
| 🟢 宽松 | 任务时长 < 可用时间 60% | |
| 🟡 适中 | 占 60%-80% | |
| 🔴 紧张 | > 可用时间 80% | |

可用时间 = 当前时间到 22:00。

> 🛑 **Checkpoint**：展示结果后等待用户下一步指令

### Phase 2: 任务写入

**创建任务**：
1. 解析用户输入 → 提取任务名 + 时间
2. 缺少必填字段时用 `AskUserQuestion` 询问
3. 智能清单分配（见上方规则）
4. 判断是否历史任务（dueDate < 当前时间）

**历史任务**（时间已过）：`create_task` → 立即 `complete_task`
**未来任务**（时间未到）：`create_task`，保持未完成

**修改任务**：
- 用户说"更新/修改" → 直接在现有任务中查找相似任务，确认修改细节
- 不要问"是要修改还是要创建"
- `update_task`（改时间/标题）、`complete_task`（标记完成）

> 🛑 **Checkpoint**：执行修改前确认操作内容

### Phase 3: 项目管理

调用 `list_projects` → 分类展示活跃/已归档清单。

### Phase 4: 日程复盘

**触发词**：一天结束、日程复盘、时间都去哪了、今天干了什么、补全日程、完善行程、回顾今天

**Step 1** — 并行获取 4 类数据：
- `list_projects`
- `list_undone_tasks_by_date`（今日）
- `list_completed_tasks_by_date`（今日）
- `list_completed_tasks_by_date`（过去 7 天，习惯推断用）

**Step 2** — 分析 + 展示：
1. 合并任务，+8 转上海时间，按时间排序
2. 生成 06:00-22:00 时间轴，识别 ≥30min 空白时段
3. 智能推断推荐活动：

| 时间段 | 推断优先级 |
|--------|-----------|
| 06:00-09:00 | 相邻任务 > 习惯 > 默认（通勤/早餐） |
| 11:30-14:00 | 习惯 > 默认（午餐/午休） |
| 17:00-19:00 | 相邻任务 > 习惯 > 默认（下班通勤） |
| 19:00-22:00 | 习惯 > 默认（晚餐/娱乐） |

推断权重：相邻任务 0.4 / 历史习惯 0.4 / 时段特征 0.2

4. 用 `AskUserQuestion` 直接展示所有空白时段选项（不问"是否需要补全"）

**Step 3** — 批量创建：
- `batch_add_tasks` 一次性创建
- 历史任务创建后立即 `complete_task` 标记完成

> 🛑 **Checkpoint**：批量创建前展示汇总确认

## 注意事项

- 旧任务 `tags` 可能为 `null`，新任务可设置标签
- 优先使用 `list_undone_tasks_by_time_query`（query 模式），它比 `list_undone_tasks_by_date` 更稳定
- `filter_tasks` 支持按 projectIds/priority/tag/status 多维度过滤

## Check List

- [ ] MCP 连接正常
- [ ] 首次查询并行获取数据
- [ ] 时间已从 UTC +8 转换为上海时区
- [ ] 表格包含清单名称列
- [ ] projectId 已缓存，非首次不重复调 list_projects
- [ ] 创建任务：判断是否为历史任务，自动标记完成
- [ ] 修改操作前已确认
- [ ] 日程复盘：主会话直接执行（不使用 Agent）
- [ ] 日程复盘：并行获取 4 类数据
- [ ] 日程复盘：时区 +8 转换正确
- [ ] 日程复盘：基于相邻任务/历史习惯/时段特征智能推断
- [ ] 日程复盘：AskUserQuestion 直接展示所有空白时段选项
- [ ] 日程复盘：使用 `batch_add_tasks` 批量创建
