# UP 主 UID 解析

## 当用户只提供名字时

用户给出 UP 主名字（非 UID/URL）时，需要先通过 B 站搜索获取 UID。

### 方法：搜索页解析

```bash
agent-browser open --headed "https://search.bilibili.com/upuser?keyword=${encodeURIComponent(NAME)}"
agent-browser wait --load networkidle && agent-browser wait 5000
```

### 提取 UID

```bash
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(
  Array.from(document.querySelectorAll('.user-item, .search-user-item, [class*="user"]'))
    .slice(0, 5)
    .map(el => {
      const nameEl = el.querySelector('a[title], .user-name a, [class*="name"] a, h2 a');
      const name = nameEl ? nameEl.textContent.trim() : '';
      const href = nameEl ? nameEl.href : '';
      const uid = href ? (href.match(/space\.bilibili\.com\/(\d+)/) || [,''])[1] : '';
      return { name, uid };
    })
    .filter(r => r.name && r.uid)
)
EVALEOF
```

### 输出示例

```json
[
  {"name": "摩的司机徐师傅", "uid": "3493117728656046"}
]
```

### 处理逻辑

1. 如果只有 1 个结果 → 直接使用该 UID
2. 如果有多个结果 → 列出给用户选择（表格形式）
3. 如果没有结果 → 提示用户检查名字或提供 UID

## 注意

- 搜索页也需要 `--headed` 模式
- 搜索结果最多显示前 5 个即可
- 获取到 UID 后关闭搜索页，重新打开空间页
