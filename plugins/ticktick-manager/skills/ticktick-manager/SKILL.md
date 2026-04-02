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
      <constraint>禁止硬编码 projectId，必须通过 list_projects 动态获取</constraint>
      <constraint>禁止串行调用 API，必须并行调用（已完成/未完成/项目列表）</constraint>
      <constraint>用户说"更新/修改"时，直接查找现有任务，不要问"是要修改还是要创建"</constraint>
      <constraint>日程复盘由主会话直接执行，3步完成：①并行获取数据 ②AskUserQuestion展示空白时段 ③批量创建任务</constraint>
      <constraint>历史任务（时间已过）必须自动标记为完成</constraint>
      <constraint>历史任务创建后必须立即调用 complete_task，因为 create_task API 会忽略 status 参数</constraint>
      <constraint>时区规则：API 返回 +0000 偏移表示 UTC 时间，需 +8 转换为上海时间（timeZone=Asia/Shanghai）</constraint>
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
    <gsd:step>检测已过期未完成任务，询问用户处理方式</gsd:step>
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

<trigger>
```
今天的任务
查看任务
今日日程
昨天任务
待办事项
任务列表
滴答清单
创建任务
修改任务
完成任务
时间紧不紧张
时间安排
日程
待办
ticktick
tt
计划
一天结束
日程复盘
时间都去哪了
今天干了什么
补全日程
完善行程
回顾今天
```
</trigger>

## 功能概览

| 功能 | 说明 | 触发词 |
|------|------|--------|
| **前置检测** | 自动检测 MCP 配置，提供安装引导 | skill 被调用时自动执行 |
| **读取任务** | 查看今日/昨日任务列表 | 查看任务、今天任务、昨天任务 |
| **写入任务** | 创建/修改/删除任务 | 创建任务、修改时间、标记完成 |
| **时间分析** | 分析任务时间紧张度 | 时间紧不紧张、时间安排 |
| **项目管理** | 查看/管理项目清单 | 查看清单、项目列表 |
| **日程复盘** | 智能补全空白时段，回顾一天行程 | 一天结束、日程复盘、时间都去哪了、补全日程 |

## 前置依赖

**必需**：dida365 MCP 服务已配置

验证方式：
```bash
# 检查 MCP 连接状态
/mcp
```

## 执行流程

### Phase 0: 前置检测（MCP 工具验证）

**触发**：skill 被调用时自动执行

**目标**：确保 dida365 MCP 工具已正确配置

**步骤**：

#### 0.1 检测 MCP 工具可用性

**检测方式**：
1. 尝试调用 `mcp__dida365__list_projects`（最轻量的查询）
2. 如果调用成功 → 继续执行 Phase 1
3. 如果调用失败 → 进入安装引导流程

**伪代码**：
```javascript
try {
  // 尝试调用最轻量的 MCP 工具
  await call_mcp("mcp__dida365__list_projects");
  // 成功，继续执行
  proceed_to_phase_1();
} catch (error) {
  // 失败，进入安装引导
  show_installation_guide();
}
```

#### 0.2 安装引导流程

**如果检测到 MCP 未配置，执行以下步骤**：

**Step 1: 检测当前环境**

```bash
# 读取 Claude Code MCP 配置文件
Read ~/.claude/mcp.json

# 如果文件不存在，读取 settings.json
Read ~/.claude/settings.json
```

**Step 2: 分析当前配置**

检查以下内容：
- ✅ MCP 配置中是否包含 `dida365`
- ✅ 是否使用了 Streamable HTTP 远程连接（`url` 字段）
- ⚠️ 如果仍使用旧的 `command`/`args`/`env` 本地模式，建议迁移到远程连接

**Step 3: 提供安装引导**

使用 `AskUserQuestion` 展示安装选项：

```
🔍 检测到 dida365 MCP 服务未配置

dida365 MCP 服务是 TickTick 任务管理的必需依赖。

📦 配置方式：

选项 1：一键远程连接（推荐）
  - 使用 Streamable HTTP 远程协议，无需本地安装
  - 支持 OAuth 自动授权，无需手动输入账号密码

选项 2：手动配置（多客户端参考）
  - 提供 Claude Code / Cursor / VS Code / Claude Desktop / ChatGPT 配置示例
  - 适合在不同客户端中使用

选项 3：查看官方配置文档
  - 展示官方文档链接
  - 适合高级用户

请选择配置方式：
```

**Step 4: 根据用户选择执行**

**选项 1：一键远程连接（推荐）**

dida365 MCP 已支持 Streamable HTTP 远程传输协议，无需本地安装任何依赖。

1. 执行配置命令：
   ```bash
   claude mcp add --transport http dida365 https://mcp.dida365.com
   ```

2. 完成 OAuth 授权：
   - 配置完成后，在 Claude Code 会话中运行 `/mcp`
   - 按照提示完成 OAuth 授权流程（浏览器会自动打开授权页面）
   - 授权成功后即可使用

3. 如需使用 Bearer Token（代替 OAuth）：
   ```bash
   claude mcp add --transport http dida365 https://mcp.dida365.com --header "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

4. 提示用户重启：
   ```
   ✅ 配置完成！

   请重启 Claude Code 以加载新的 MCP 服务器：
   1. 退出 Claude Code
   2. 重新启动
   3. 运行 /mcp，按照提示完成 OAuth 授权
   4. 再次使用 ticktick-manager skill
   ```

**选项 2：手动配置（多客户端参考）**

展示不同客户端的配置方式：

```markdown
## 📝 多客户端手动配置

### Claude Code（终端命令）

\`\`\`bash
claude mcp add --transport http dida365 https://mcp.dida365.com
\`\`\`

### Cursor

编辑 \`.cursor/mcp.json\`：

\`\`\`json
{
  "mcpServers": {
    "dida365": {
      "url": "https://mcp.dida365.com"
    }
  }
}
\`\`\`

### VS Code

编辑 \`.vscode/mcp.json\`：

\`\`\`json
{
  "servers": {
    "dida365": {
      "type": "http",
      "url": "https://mcp.dida365.com"
    }
  }
}
\`\`\`

### Claude Desktop

进入 Customize > Connectors > Add Connector，填写 URL：
https://mcp.dida365.com

### ChatGPT

设置 > 应用 > 高级设置 > 开发人员模式 > 创建应用，填写 URL：
https://mcp.dida365.com

### 备选方案（本地安装，不推荐）

如果无法使用远程连接，可以使用旧的本地安装方式：

\`\`\`bash
npx @wangjs-jacky/dida365-mcp-server
\`\`\`

\`\`\`json
{
  "mcpServers": {
    "dida365": {
      "command": "npx",
      "args": ["-y", "@wangjs-jacky/dida365-mcp-server"],
      "env": {
        "DIDA365_USERNAME": "你的用户名",
        "DIDA365_PASSWORD": "你的密码"
      }
    }
  }
}
\`\`\`
```

**选项 3：查看官方配置文档**

展示官方配置文档链接和说明：

```markdown
## 📚 官方配置文档

### dida365 MCP 官方
- MCP 服务器地址：https://mcp.dida365.com
- 协议：Streamable HTTP（远程传输）

### 相关文档
- MCP 协议规范：https://modelcontextprotocol.io
- TickTick API 文档：https://developer.ticktick.com

### 常见问题

**Q: OAuth 授权流程是什么？**
A: 配置完成后运行 /mcp，浏览器会自动打开滴答清单授权页面，登录确认即可

**Q: 支持 Bearer Token 吗？**
A: 支持。可在配置时通过 --header 参数添加 Authorization: Bearer YOUR_TOKEN

**Q: 远程连接和本地安装有什么区别？**
A: 远程连接无需本地安装任何依赖，通过 OAuth 授权更安全便捷，推荐使用
```

#### 0.3 配置文件示例

**Claude Code mcp.json 示例**（Streamable HTTP 远程连接）：

```json
{
  "mcpServers": {
    "dida365": {
      "url": "https://mcp.dida365.com"
    }
  }
}
```

**使用 Bearer Token 的 mcp.json 示例**：

```json
{
  "mcpServers": {
    "dida365": {
      "url": "https://mcp.dida365.com",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

> 💡 **提示**：推荐使用 `claude mcp add --transport http dida365 https://mcp.dida365.com` 命令自动配置，OAuth 授权后无需手动管理 Token。

> 🛑 **Checkpoint**：MCP 配置完成后，提示用户重启 Claude Code 并验证连接

### Phase 1: 任务读取

**触发**：用户请求查看任务

**步骤**：
1. 并行调用 MCP 工具获取数据：
   - `mcp__dida365__list_undone_tasks_by_date` - 未完成任务
   - `mcp__dida365__list_completed_tasks_by_date` - 已完成任务
   - `mcp__dida365__list_projects` - 项目列表（用于清单名称映射）
2. 合并数据并按时间排序
3. 输出格式化表格
4. **自动检测**：如果用户询问包含以下关键词，自动触发时间分析：
   - "时间紧不紧张"、"紧张"、"宽裕"
   - "时间安排"、"日程安排"、"满不满"
   - "来得及"、"够不够"、"充不充裕"

> 🛑 **Checkpoint**：首次查询后展示结果，等待用户下一步指令

#### 时间紧张度分析

**自动触发检测**：
- 用户询问中包含时间紧张度相关关键词
- 或用户明确要求分析时间安排

**分析逻辑**：
1. 统计今天未完成任务的总时长
2. 计算剩余可用时间（当前时间到 22:00）
3. 对比任务时长 vs 可用时间

**输出格式**：
```
📊 今日时间分析

| 指标 | 数值 |
|------|------|
| 未完成任务 | X 个 |
| 预计总时长 | X 小时 X 分钟 |
| 剩余可用时间 | X 小时 X 分钟 |
| 紧张度 | 🟢 宽松 / 🟡 适中 / 🔴 紧张 |

💡 建议：{根据紧张度给出建议}
```

**紧张度判定标准**：
- 🟢 **宽松**：任务时长 < 可用时间的 60%
- 🟡 **适中**：任务时长占可用时间的 60%-80%
- 🔴 **紧张**：任务时长 > 可用时间的 80%

> ⚠️ **注意**：此功能为可选提示，不强制执行

### Phase 2: 任务写入

**触发**：用户请求创建/修改任务

#### 2.1 创建任务

**必填字段**（用户必须提供）：
| 字段 | 说明 | 示例 |
|------|------|------|
| **任务名称** | 任务标题 | "学习 React" |
| **时间** | 开始时间或时间段 | "晚上7:30" / "19:30-20:00" |

**可选字段**：
| 字段 | 默认值 | 说明 |
|------|--------|------|
| **清单** | 📥 收集箱 | 项目清单名称 |

**执行逻辑**：
1. 解析用户输入，提取任务名称和时间
2. 如果缺少必填字段，使用 `AskUserQuestion` 询问
3. 解析时间（支持自然语言）：
   - "晚上7:30" → 19:30
   - "下午3点" → 15:00
   - "早上9点到10点" → 09:00-10:00
4. **智能清单分配**（根据任务关键词自动匹配）：
   | 任务关键词 | 自动分配清单 | 清单名称 |
   |-----------|-------------|---------|
   | 睡觉、休息 | 🟣 紫 | 休息 |
   | 午休、午睡、午饭、午餐 | 🟡 黄 | 午休 |
   | 早饭、早餐、晚饭、晚餐、吃饭 | 🟡 黄 | 午休 |
   | 游戏、娱乐、看电影、刷剧 | 🔴 红 | 娱乐 |
   | 其他 | 📥 收集箱 | Inbox |

   > ⚠️ **注意**：清单名称映射通过 `mcp__dida365__list_projects` 动态获取，禁止硬编码 projectId

   **首次使用**：
   - 调用 `mcp__dida365__list_projects` 获取所有清单
   - 建立"清单名称 → projectId"映射表
   - 后续使用缓存映射（如映射失效则重新获取）

5. **判断是否为历史任务**：
   - 获取任务的结束时间（dueDate）
   - 与当前时间对比
   - 如果 `dueDate < 当前时间`，则为历史任务

6. **创建任务**：
   - **历史任务**（时间已过）：
     1. 调用 `mcp__dida365__create_task` 创建任务
     2. **重要**：`create_task` API 会忽略 `status` 和 `completedTime` 参数，必须二次调用
     3. 立即调用 `mcp__dida365__complete_task` 标记完成（传入任务 ID）
     4. 输出："✅ 已完成（历史任务）"

   - **未来任务**（时间未到）：
     1. 调用 `mcp__dida365__create_task` 创建任务
     2. 保持未完成状态

> ⚠️ **重要**：用户说"更新/修改"时，直接在现有任务中查找相似任务，确认修改细节，不要问"是要修改还是要创建"

#### 2.2 修改任务

**支持操作**：
- 修改时间：`mcp__dida365__update_task`（修改 startDate/dueDate）
- 标记完成：`mcp__dida365__complete_task`
- 删除任务：`mcp__dida365__update_task`（status: -1）

> 🛑 **Checkpoint**：执行修改前确认操作内容

### Phase 3: 项目管理

**触发**：用户请求查看清单

**步骤**：
1. 调用 `mcp__dida365__list_projects` 获取所有清单
2. 分类展示：活跃清单 / 已归档清单
3. 可选：查看某个清单下的任务

### Phase 4: 日程复盘

**触发**：
- 命令：`/ticktick review`
- 触发词：一天结束、日程复盘、时间都去哪了、今天干了什么、补全日程、完善行程、回顾今天

**功能**：分析今天没有填写任务的时间段，逐个询问用户在做什么，然后批量记录到滴答清单。

**执行方式**：主会话直接执行，3 步完成（不使用 Agent）

#### Step 1: 并行获取数据

**同时调用 4 个 MCP 工具**：
- `mcp__dida365__list_projects` — 获取清单映射
- `mcp__dida365__list_undone_tasks_by_date` — 今日未完成任务
- `mcp__dida365__list_completed_tasks_by_date` — 今日已完成任务
- `mcp__dida365__list_completed_tasks_by_date` — 过去 7 天已完成（用于习惯推断）

**时区规则**（重要）：
> API 返回时间格式为 `"2026-04-02T02:15:00+0000"`，`+0000` 表示 UTC 时间。
> 如果 `timeZone: "Asia/Shanghai"`，需要 **+8 转换**为上海本地时间。
> 例如：`02:15 UTC + 8 = 10:15 上海时间`。

#### Step 2: 分析时间轴 + 展示选项

1. 合并今日已完成 + 未完成任务，按开始时间排序
2. 生成 06:00-22:00 时间轴，识别 ≥30 分钟空白时段
3. 基于智能推断规则生成推荐活动
4. **直接用 AskUserQuestion 展示所有空白时段和选项**（不要问"是否需要补全"）

**智能推断规则**：

| 时间段 | 推断优先级 |
|--------|-----------|
| 06:00-09:00 | 相邻任务 > 习惯 > 默认（通勤/早餐） |
| 11:30-14:00 | 习惯 > 默认（午餐/午休） |
| 17:00-19:00 | 相邻任务 > 习惯 > 默认（下班通勤） |
| 19:00-22:00 | 习惯 > 默认（晚餐/娱乐） |

**推断源权重**：相邻任务 0.4 / 历史习惯 0.4 / 时段特征 0.2

**推荐理由格式**：`← 推荐（工作日早晨 + 09:00有工作任务）`

#### Step 2.5: 检测已过期未完成任务

1. 筛选今日任务中 `dueDate < 当前时间` 且 `status != 2` 的任务
2. 如果存在未完成的过期任务，使用 AskUserQuestion 展示：
   ```
   ⚠️ 发现 N 个已过期但未完成的任务：

   1️⃣ 任务名称（原定时间：HH:MM-HH:MM）
      - 1. ✅ 标记完成
      - 2. 📅 调整时间
      - 3. ⏸️ 保持不变

   请选择处理方式：
   ```
3. 根据用户选择执行：
   - 标记完成：调用 `complete_task`
   - 调整时间：询问新时间后调用 `update_task`
   - 保持不变：跳过

> 💡 **提示**：此步骤在空白时段补全之前执行，确保用户先处理过期任务

#### Step 3: 批量创建任务

根据用户选择，调用 `mcp__dida365__batch_add_tasks` 一次性创建。

**清单分配规则**（同 Phase 2.1）：
| 活动关键词 | 分配清单 |
|-----------|---------|
| 睡觉、休息 | 休息（紫） |
| 午休、午睡、午饭、午餐、早饭、晚餐、吃饭 | 午休（黄） |
| 游戏、娱乐、看电影、刷剧 | 娱乐（红） |
| 其他 | Inbox |

**历史任务处理**：时间已过的任务，创建后必须立即调用 `complete_task` 标记完成（`create_task` API 会忽略 status 参数）。

**输出格式**：
```
📝 汇总：
1️⃣ 07:00-09:00 → 通勤/上班路上 ✅
2️⃣ 12:00-14:00 → 午餐/午休 ✅

已创建 2 个任务
```

> 🛑 **Checkpoint**：批量创建前展示汇总确认

## MCP 工具清单

### 读取类

| 工具 | 用途 |
|------|------|
| `mcp__dida365__list_undone_tasks_by_date` | 按日期查询未完成任务 |
| `mcp__dida365__list_completed_tasks_by_date` | 按日期查询已完成任务 |
| `mcp__dida365__list_undone_tasks_by_time_query` | 按时间窗口查询（today/tomorrow/last7day） |
| `mcp__dida365__get_task_by_id` | 获取单个任务详情 |
| `mcp__dida365__list_projects` | 获取所有项目清单 |

### 写入类

| 工具 | 用途 |
|------|------|
| `mcp__dida365__create_task` | 创建新任务 |
| `mcp__dida365__update_task` | 修改任务（时间/标题/内容/标签） |
| `mcp__dida365__complete_task` | 标记任务完成 |
| `mcp__dida365__batch_add_tasks` | 批量创建任务（日程复盘使用） |
| `mcp__dida365__batch_update_tasks` | 批量更新任务 |

### 辅助类

| 工具 | 用途 |
|------|------|
| `mcp__dida365__search_task` | 搜索任务 |
| `mcp__dida365__filter_tasks` | 按条件过滤任务 |
| `mcp__dida365__move_task` | 移动任务到其他项目 |

## 最佳实践

### 时区处理

**关键**：API 返回 `"2026-04-01T06:30:00+0000"`，`+0000` 表示 UTC 时间。如果 `timeZone: "Asia/Shanghai"`，需要 **+8 转换**。

**转换规则**：
1. 检查时间偏移量（如 `+0000` 表示 UTC）
2. 检查 `timeZone` 字段是否为 `Asia/Shanghai`
3. 如果是 → UTC 时间 + 8 = 上海时间（`06:30 UTC + 8 = 14:30 上海时间`）
4. 如果 `timeZone` 缺失或为其他值 → 按实际时区偏移转换

**输出格式**：
```
| 时间（上海） | 任务 | 清单 | 状态 |
|-------------|------|------|------|
| 14:30-15:00 | xxx | Inbox | ⏳ |
```

> ⚠️ **注意**：只显示时间部分（HH:mm），不显示日期

### 性能优化

**避免重复查询**：
- 首次查询后缓存结果
- 合并已完成 + 未完成任务为单次请求
- 同时获取项目列表建立映射

**并行调用**：
```
✅ 正确：同时调用 3 个 API（已完成/未完成/项目列表）
❌ 错误：串行调用 3 次
```

### 标签管理

**重要发现**：
- 旧任务的 `tags` 字段可能为 `null`
- 新创建的任务可以设置标签
- 通过 `mcp__dida365__get_task_by_id` 可以读取到标签

### 动态获取 projectId

> ⚠️ **禁止硬编码 projectId**：
> 1. 首次使用时调用 `mcp__dida365__list_projects` 获取所有清单
> 2. 建立"清单名称 → projectId"映射表（示例）：
>    ```json
>    {
>      "休息": "67bb37ad7a1a51746f577c69",
>      "午休": "67bb37638f1311746f5777dd",
>      "娱乐": "67bb3747071251746f57750e",
>      "Inbox": "inbox1019223045"
>    }
>    ```
> 3. 后续通过清单名称查找对应的 projectId
> 4. 如果映射失效或找不到，重新调用 `list_projects` 刷新映射

### 任务更新最佳实践

**关键原则**：用户说"更新/修改"时，直接在现有任务中查找，不要问"是要修改还是要创建"

**示例**：
```
❌ 错误方式：
用户：帮我更新一下晚上7点的任务
Claude：你说的晚上7点是指哪个任务？是要修改"晚饭"任务（18:00-18:30），还是创建一个新任务？

✅ 正确方式：
用户：帮我更新一下晚上7点的任务
Claude：我找到"晚饭"任务（18:00-18:30），你说的晚上7点是要把它改到19:00-19:30吗？
用户：对
Claude：[执行修改]
```

**查找策略**：
1. 用户说"更新/修改" → 在现有任务中查找相似任务
2. 用户说"创建/新增" → 直接创建新任务
3. 找到相似任务后，直接确认修改细节，不要提供"修改或创建"的选项

## 使用示例

### 查看今天任务

```
用户：帮我看下今天的任务
Claude：[并行调用 MCP 获取数据，输出表格]
```

### 创建任务（完整信息）

```
用户：帮我创建一个任务，晚上7:30到8点，学习React技术
Claude：
  ✅ 任务已创建
  - 任务：学习 React 技术
  - 时间：今天 19:30-20:00
  - 清单：📥 收集箱
```

### 创建任务（缺少时间）

```
用户：帮我创建一个任务，学习Vue
Claude：请问这个任务的时间是什么时候？
用户：明天下午3点
Claude：[创建任务，时间设为明天 15:00]
```

### 创建历史任务（自动标记完成）

```
用户：帮我记录一下，早上9点吃了早餐
Claude：
  ✅ 已完成（历史任务）
  - 任务：吃早餐
  - 时间：今天 09:00-09:30
  - 清单：黄（午休）
```

### 查看时间紧张度

```
用户：帮我看下今天的时间安排紧不紧张
Claude：
  📊 时间分析
  - 总任务时长：6 小时 30 分钟
  - 剩余可用时间：2 小时
  - 紧张度：🔴 紧张

  💡 建议：任务较多，建议优先完成重要任务
```

### 修改任务时间

```
用户：把第三个任务改成 9 点到 9:45
Claude：[确认任务 ID，调用 update_task]
```

### 日程复盘

```
用户：/ticktick review
Claude：
  📊 今日日程复盘

  正在分析今天的时间轴...
  正在查询历史习惯数据（过去 7 天）...

  ⚠️ 发现 2 个已过期但未完成的任务：

  1️⃣ 晨间运动（原定时间：06:30-07:00）
     - 1. ✅ 标记完成
     - 2. 📅 调整时间
     - 3. ⏸️ 保持不变

  2️⃣ 回复重要邮件（原定时间：11:00-11:30）
     - 1. ✅ 标记完成
     - 2. 📅 调整时间
     - 3. ⏸️ 保持不变

  请选择处理方式（如 "1-1 2-1" 表示第1个标记完成，第2个标记完成）：

  用户：1-1 2-2

  ✅ 已标记"晨间运动"为完成
  📅 请输入"回复重要邮件"的新时间：
  用户：明天上午10点

  ✅ 已调整"回复重要邮件"到明天 10:00-10:30

  ✅ 已记录时段：
    09:00-10:00  晨会
    10:00-12:00  开发功能 A
    14:00-15:30  代码审查

  ⚠️ 发现 3 个空白时段：

  1️⃣ 07:00-09:00（2小时）
     可能的活动：
     - 1. 🚗 通勤/上班路上 ← 推荐（工作日早晨 + 09:00有工作任务）
     - 2. 🍳 吃早餐
     - 3. 😴 睡觉/休息
     - 4. 📱 刷手机/娱乐
     - 5. ✏️ 其他

  2️⃣ 12:00-14:00（2小时）
     可能的活动：
     - 1. 🍱 午餐/午休 ← 推荐（过去3天此时段都是"午餐/午休"）
     - 2. 🚶 散步/休息
     - 3. 📱 刷手机/娱乐
     - 4. ✏️ 其他

  3️⃣ 17:00-19:00（2小时）
     可能的活动：
     - 1. 🚗 下班通勤 ← 推荐（工作日晚间 + 17:00前有工作任务）
     - 2. 🍲 晚餐
     - 3. 🏃 运动/健身
     - 4. ✏️ 其他

  请输入时段编号 + 活动编号（如 "11 21 31"）：

  用户：11 21 31

  📝 汇总：
  1️⃣ 07:00-09:00 → 通勤/上班路上
  2️⃣ 12:00-14:00 → 午餐/午休
  3️⃣ 17:00-19:00 → 下班通勤

  ✅ 已创建 3 个任务
```

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| MCP 连接失败 | dida365 未认证 | 运行 `/mcp` 重新认证 |
| 标签读取为空 | 旧任务未设置标签 | 通过 update_task 添加标签 |
| 时间显示错误 | 时区转换规则错误 | UTC 时间 + 8 = 上海时间 |
| 找不到清单 | projectId 过期 | 调用 list_projects 刷新映射 |

## 多客户端配置参考

dida365 MCP 服务支持 Streamable HTTP 远程传输协议，可在多种 AI 客户端中使用。

### 客户端配置速查表

| 客户端 | 配置方式 | 配置文件/位置 |
|--------|---------|--------------|
| **Claude Code** | 终端命令 | `claude mcp add --transport http` |
| **Cursor** | JSON 配置 | `.cursor/mcp.json` |
| **VS Code** | JSON 配置 | `.vscode/mcp.json` |
| **Claude Desktop** | UI 配置 | Customize > Connectors |
| **ChatGPT** | UI 配置 | 设置 > 开发人员模式 |

### Claude Code

```bash
# 推荐：OAuth 授权（自动管理 Token）
claude mcp add --transport http dida365 https://mcp.dida365.com

# 或使用 Bearer Token
claude mcp add --transport http dida365 https://mcp.dida365.com --header "Authorization: Bearer YOUR_TOKEN_HERE"
```

配置完成后运行 `/mcp`，按照提示完成 OAuth 授权。

### Cursor

编辑 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "dida365": {
      "url": "https://mcp.dida365.com"
    }
  }
}
```

### VS Code

编辑 `.vscode/mcp.json`：

```json
{
  "servers": {
    "dida365": {
      "type": "http",
      "url": "https://mcp.dida365.com"
    }
  }
}
```

### Claude Desktop

1. 打开 Claude Desktop
2. 进入 **Customize > Connectors > Add Connector**
3. 填写 URL：`https://mcp.dida365.com`
4. 保存并按照提示完成授权

### ChatGPT

1. 打开 ChatGPT
2. 进入 **设置 > 应用 > 高级设置 > 开发人员模式**
3. 点击 **创建应用**
4. 填写 URL：`https://mcp.dida365.com`
5. 保存并按照提示完成授权

## Check List

- [ ] MCP 连接正常（`/mcp` 验证）
- [ ] 首次查询并行获取 3 类数据
- [ ] 时间已转换为上海时区
- [ ] 表格包含清单名称列
- [ ] 创建任务：判断是否为历史任务，自动标记完成
- [ ] 修改操作前已确认
- [ ] 动态获取 projectId 映射（禁止硬编码）
- [ ] 日程复盘：主会话直接执行（不使用 Agent）
- [ ] 日程复盘：并行获取 4 类数据（今日已完成+未完成+历史7天+项目列表）
- [ ] 日程复盘：时区规则正确（timeZone=Asia/Shanghai 时直接使用时间值）
- [ ] 日程复盘：检测已过期未完成任务，询问用户处理方式
- [ ] 日程复盘：基于相邻任务/历史习惯/时段特征智能推断
- [ ] 日程复盘：AskUserQuestion 直接展示所有空白时段选项
- [ ] 日程复盘：使用 `batch_add_tasks` 批量创建
