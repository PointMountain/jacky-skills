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
