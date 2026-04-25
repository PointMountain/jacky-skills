---
name: todo
description: "项目级 TODO 追踪：管理临时代码清理、待办事项、想法和临时文件，支持跨会话恢复"
argument-hint: '[add|done|clean|list|setup|save|restore|add-file] [内容]'
---

<role>你是一个任务管理专家，帮助用户追踪和管理项目中的临时代码、待办事项、想法和临时文件。</role>

<purpose>当用户需要管理项目中的临时任务、记录想法、追踪临时代码或恢复上下文时，使用此 skill。</purpose>

<trigger>
用户说 /todo、TODO、任务列表、临时文件清理、恢复上下文 时触发
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>todo</name>
    <trigger>/todo, TODO, 任务列表, 临时文件, 清理, 想法</trigger>
    <requires>Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion</requires>
    <checkpoints>
      <checkpoint order="1">命令解析完成</checkpoint>
      <checkpoint order="2">文件操作确认</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>所有清理操作（delete/git-checkout）必须经过用户确认</constraint>
      <constraint>删除操作必须校验路径在项目目录内</constraint>
      <constraint>默认不修改 .todo.md 之外的项目文件；仅 clean/setup 命令可修改，且必须通过用户确认与路径安全校验</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>为项目提供持久化的任务追踪，管理临时代码、待办事项、想法和临时文件</gsd:goal>

  <gsd:phase name="parse" order="1">
    <gsd:step>读取用户输入的参数，解析子命令</gsd:step>
    <gsd:step>支持子命令：add, done, clean, list, setup, save, restore, add-file</gsd:step>
    <gsd:step>解析选项：--cleanup, --idea, @file:, @action:</gsd:step>
    <gsd:step>如果没有子命令，默认执行 list</gsd:step>
    <checkpoint>命令解析完成，确认操作意图</checkpoint>
  </gsd:phase>

  <gsd:phase name="execute" order="2">
    <gsd:step>检查 .todo.md 是否存在，不存在则创建初始模板</gsd:step>
    <gsd:step>
根据子命令执行对应操作：

**add 命令：**
1. 确定目标分区：`--cleanup` → 🧹 Cleanup，`--idea` → 💡 Ideas，默认 → 📋 Todo
2. 解析内容中的 @file: 和 @action: 标记
3. 在目标分区末尾添加 `- [ ] <内容>`
4. 更新 `最后更新` 时间戳

**add-file 命令：**
1. 验证文件路径在项目内
2. 在 📁 Temp Files 分区添加 `- [ ] 删除 <filename> @file:<path> @action:delete`

**list 命令：**
1. 读取 .todo.md 全部分区
2. 按分类展示未完成项，统计各分区数量

**done 命令：**
1. 查找匹配的项（支持编号或关键词）
2. 将 `- [ ]` 改为 `- [x]`
    </gsd:step>
    <gsd:step>
**clean 命令：**
1. 读取 🧹 Cleanup 和 📁 Temp Files 分区的未完成项
2. 对每项执行路径安全校验：
   - 解析 @file: 路径为绝对路径
   - 验证绝对路径以项目根目录开头
   - 验证路径不包含 .. 穿越
   - 验证文件是否存在
   - 不安全的项标注 ⚠️
3. 展示待清理项列表，按编号排列
4. 使用 AskUserQuestion 让用户选择要清理的项
5. 执行对应操作：
   - @action:delete → 删除文件（仅项目内路径）
   - @action:git-checkout → `git checkout -- <file>`（node_modules 需二次确认）
   - 无 @action → 仅提醒手动处理
    </gsd:step>
    <gsd:step>
**save 命令：**
1. 在 📋 Todo 分区追加进展描述作为新项
2. 更新时间戳

**restore 命令：**
1. 读取 .todo.md 全部内容
2. 展示各分区的未完成项摘要
3. 建议用户下一步操作（如先 /todo clean）
    </gsd:step>
    <gsd:step>
**setup 命令：**
1. 读取 hooks/hooks.json 配置
2. 将 hooks 配置合并到 ~/.claude/settings.json 中
3. 如果 .todo.md 不存在，创建初始模板
4. 询问用户是否将 .todo.md 加入 .gitignore
    </gsd:step>
    <checkpoint>操作完成，反馈结果</checkpoint>
  </gsd:phase>

  <gsd:phase name="cleanup" order="3">
    <gsd:step>展示操作结果</gsd:step>
    <gsd:step>对于 clean 操作，标记已清理的项为 [x]</gsd:step>
    <gsd:step>更新 .todo.md 最后更新时间戳</gsd:step>
  </gsd:phase>
</gsd:workflow>

## .todo.md 文件格式

> 详细格式说明见 references/file-format.md

文件存储在项目根目录 `.todo.md`，包含四个分区：

## 🧹 Cleanup（需要清理的临时代码）
## 📋 Todo（待办事项）
## 💡 Ideas（想法记录）
## 📁 Temp Files（需要删除的临时文件）

每条项格式：`- [ ] 描述内容 @file:path @action:type`

## 安全规则

> 详细安全说明见 references/setup-guide.md

1. 所有清理操作必须经用户确认
2. 路径安全校验：解析后绝对路径必须在项目目录内
3. 禁止操作绝对路径（以 / 开头）
4. node_modules 的 git-checkout 需二次确认
5. 所有 hook 脚本以 exit 0 结束
