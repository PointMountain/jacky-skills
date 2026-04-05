# tt-auto-pool 实现计划

> **For agentic workers:** Use superpowers:executing-plans to implement.

**Goal:** 实现 tt-defer（推送端）和 tt-worker（执行端）两个 skill

**Architecture:** 双 skill 架构，通过滴答清单「任务池」作为中间队列。tt-defer 推任务+打 tag，tt-worker 读任务+按 tag 执行。

**Tech Stack:** Claude Code SKILL.md, tt CLI, Bash

---

## Chunk 1: 共享资源

### Task 1: 创建 task-format.md 参考文档

**Files:**
- Create: `plugins/ticktick-manager/tt-defer/references/task-format.md`
- Create: `plugins/ticktick-manager/tt-worker/references/task-format.md`

- [ ] **Step 1:** 创建 tt-defer/references/task-format.md（任务格式规范）
- [ ] **Step 2:** 复制同一份到 tt-worker/references/task-format.md
- [ ] **Step 3:** Commit

### Task 2: 更新 plugin.json 注册新 skills

**Files:**
- Modify: `plugins/ticktick-manager/.claude-plugin/plugin.json`

- [ ] **Step 1:** 在 skills 数组中添加 `./tt-defer/` 和 `./tt-worker/`
- [ ] **Step 2:** 更新版本号 MINOR（1.1.3 → 1.2.0）
- [ ] **Step 3:** Commit

---

## Chunk 2: tt-defer skill

### Task 3: 创建 tt-defer SKILL.md

**Files:**
- Create: `plugins/ticktick-manager/tt-defer/SKILL.md`

- [ ] **Step 1:** 使用 gsd-creator-skills 创建 tt-defer skill
  - 触发词：推到待办、丢到池子、tt-defer、推任务
  - 包含：前置检测（tt CLI + 任务池清单检测/创建）、上下文提取、tag 推断、任务推送
  - 输出风格：轻松俏皮（延续 tt skill）
- [ ] **Step 2:** Commit

---

## Chunk 3: tt-worker skill

### Task 4: 创建 tt-worker SKILL.md

**Files:**
- Create: `plugins/ticktick-manager/tt-worker/SKILL.md`

- [ ] **Step 1:** 使用 gsd-creator-skills 创建 tt-worker skill
  - 触发词：执行任务池、tt-worker、处理待办
  - 包含：前置检测、任务读取（仅任务池清单）、按 tag 执行策略、进度追踪、完成标记
  - 输出风格：简洁日志
  - 安全机制：任务上限、超时、跳过策略
- [ ] **Step 2:** Commit

---

## Chunk 4: 安装验证

### Task 5: 链接并安装 skills

- [ ] **Step 1:** `j-skills link` 链接新 skills
- [ ] **Step 2:** `j-skills install tt-defer -g` 和 `j-skills install tt-worker -g`
- [ ] **Step 3:** 验证安装成功
- [ ] **Step 4:** Commit（如有变更）
