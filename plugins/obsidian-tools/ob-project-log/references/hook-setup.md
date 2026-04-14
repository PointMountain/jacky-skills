# Stop Hook 自动沉淀配置指南

## 工作原理

当开启"项目自动沉淀"后，每次对话结束时，Stop Hook 会自动触发：

```
对话即将结束
  → Stop Hook 触发
  → 检查：是否开启自动沉淀？是否在 git 项目中？
  → 条件满足 → 阻止停止，让 Claude 检查是否有知识需要沉淀
  → Claude 分析对话内容
    → 有价值内容 → 自动沉淀到 wiki/projects/{project}/
    → 无价值内容 → 跳过
  → 创建标记文件（防死循环）
  → 下次触发时标记存在 → 放行，对话正常结束
```

## 开启方式

在 Claude Code 中说：

```
开启项目沉淀
```

Claude 会创建标记文件 `~/.claude/ob-auto-sync.enabled`，Hook 即生效。

## 关闭方式

```
关闭项目沉淀
```

Claude 会移除标记文件，Hook 不再触发。

## 涉及的文件

| 文件 | 作用 |
|------|------|
| `~/.claude/ob-auto-sync.enabled` | 开关标记，存在=开启 |
| `hooks/auto-project-log.sh` | Hook 脚本，检查条件并触发 |
| `hooks/hooks.json` | Hook 注册声明 |
| `/tmp/ob-project-log-synced-$PPID` | 防死循环标记（临时文件） |

## 注意事项

- 自动沉淀**不会覆盖**已有内容，只会追加和合并
- 敏感信息（API key、密码）会自动脱敏为 `{REDACTED}`
- 如果 OBSIDIAN_REPO 未配置，沉淀不会执行
- 非 git 项目目录下不会触发（如在家目录浏览文件时）
- 标记文件 `/tmp/ob-project-log-synced-*` 在系统重启后自动清除

## 常见问题

### 为什么对话没有自动沉淀？

检查以下几点：
1. 是否说过"开启项目沉淀"？
2. 当前目录是否在 git 项目中？
3. 对话是否包含值得沉淀的项目知识？

### 为什么对话停不下来？

这是防死循环机制失效的表现。手动创建标记文件即可：

```bash
echo $(date +%s) > /tmp/ob-project-log-synced-$PPID
```

### 想临时跳过一次沉淀？

在 Hook 触发后，直接说"本次对话无需沉淀"即可。
