# .todo.md 文件格式说明

## 概述

`.todo.md` 是 todo skill 的数据存储文件，存储在项目根目录。使用纯 Markdown 格式，Git 友好，可手动编辑。

## 完整模板

```markdown
# TODO

> 自动生成的任务追踪文件，由 /todo skill 管理
> 最后更新: YYYY-MM-DD

## 🧹 Cleanup

- [ ] 移除 `src/app.tsx` 中的 console.log 调试代码 @file:src/app.tsx
- [ ] 恢复 node_modules/lodash/index.js 的修改 @file:node_modules/lodash/index.js @action:git-checkout

## 📋 Todo

- [ ] 完成用户认证模块的单元测试
- [x] 修复登录页面的样式问题
- [ ] 重构 API 错误处理逻辑

## 💡 Ideas

- [ ] 可以用 WebSocket 实现实时通知功能
- [ ] 考虑引入 Zustand 替代 Context 做状态管理

## 📁 Temp Files

- [ ] 删除临时测试文件 @file:test-debug.tsx @action:delete
- [ ] 删除调试用的 HTML 文件 @file:debug.html @action:delete
```

## 四个分区

| 分区 | 标题 | 用途 |
|------|------|------|
| 🧹 Cleanup | `## 🧹 Cleanup` | 需要清理的临时代码（console.log、node_modules 修改等） |
| 📋 Todo | `## 📋 Todo` | 常规待办事项 |
| 💡 Ideas | `## 💡 Ideas` | 未来可能实现的想法 |
| 📁 Temp Files | `## 📁 Temp Files` | 需要删除的临时文件 |

## 条目格式

### 基本格式

```
- [ ] 描述文字
```

- `- [ ]` 表示未完成
- `- [x]` 表示已完成

### 标记系统

| 标记 | 说明 | 示例 |
|------|------|------|
| `@file:<path>` | 关联的文件路径（相对路径） | `@file:src/app.tsx` |
| `@action:delete` | 清理动作：删除文件 | `@action:delete` |
| `@action:git-checkout` | 清理动作：恢复 Git 修改 | `@action:git-checkout` |

### 标记规则

1. `@file:` 后面跟相对路径（从项目根目录开始）
2. `@action:` 必须和 `@file:` 搭配使用
3. 没有 `@file:` 的条目是纯文本，不支持自动清理
4. 同一条目可以有多个标记

## 时间戳

文件头部的 `> 最后更新: YYYY-MM-DD` 在每次修改时自动更新。
