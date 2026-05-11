# 批量采集详解

> SKILL.md 主体保留触发条件 + 执行策略表 + 自动停止规则；本文是状态追踪和报告模板的完整细节。

## 状态追踪

批量任务使用工作目录追踪状态：

```
~/Downloads/collect-pipeline/
└── {platform}-{id}/
    ├── meta.json    # 状态 + 时间记录
    └── (临时文件)
```

### meta.json schema

```json
{
  "id": "task-identifier",
  "url": "https://...",
  "platform": "youtube",
  "title": "标题",
  "status": "pending|in_progress|completed|failed|skipped",
  "startedAt": "ISO8601",
  "completedAt": "ISO8601",
  "duration": 123.4,
  "error": null
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 任务唯一标识，建议 `{platform}-{contentId}` |
| `url` | string | 原始 URL |
| `platform` | string | youtube / bilibili / zhihu / ... |
| `title` | string | 内容标题（采集到后填充）|
| `status` | enum | 五种状态见 schema |
| `startedAt` | ISO8601 | 任务开始时间 |
| `completedAt` | ISO8601 | 任务完成时间（成功/失败/跳过都填） |
| `duration` | number | 总耗时（秒） |
| `error` | string\|null | 失败原因，成功时为 null |

## 断点续传

扫描 `~/Downloads/collect-pipeline/` 下所有 meta.json，找到 `status != completed` 的任务，从断点继续。

伪代码：

```bash
for meta in ~/Downloads/collect-pipeline/*/meta.json; do
  status=$(python3 -c "import json; print(json.load(open('$meta'))['status'])")
  if [ "$status" != "completed" ]; then
    # 重新执行该任务
    ...
  fi
done
```

## 批量报告模板

完成后生成的报告格式：

```
📊 批量采集完成
✅ 成功: 8 (耗时: 12m30s)    ❌ 失败: 1    ⏭ 跳过: 1

生成文件:
  • $OBSIDIAN_REPO/raw/作者/标题.md
  • $OBSIDIAN_REPO/wiki/标题-归纳.md

失败项:
  • https://... → 原因: OpenCLI download 超时
```

### 报告生成要点

1. **统计三种状态**：成功 / 失败 / 跳过
2. **总耗时**：从首个任务的 `startedAt` 到末尾任务的 `completedAt`
3. **生成文件列表**：列出本批次写入 raw/ 和 wiki/ 的所有文件
4. **失败项**：附原因（来自 meta.json 的 `error` 字段）

## 工作目录清理

批量完成后，是否清理 `~/Downloads/collect-pipeline/` 由用户决定：

- 默认**保留**，便于后续问题排查
- 用户说"清理批量目录"时再清空
- 单个任务的临时文件（如下载的视频）在任务结束时立即删除
