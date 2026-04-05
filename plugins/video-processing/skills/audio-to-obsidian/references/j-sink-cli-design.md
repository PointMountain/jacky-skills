# j-sink CLI 工具设计方案

> 核心理念：j-sink 是多源信息收集中枢，Obsidian 只是查看层。
> 所有元信息、状态追踪、标签管理、查询检索统一通过 CLI 完成。
> 当前数据源：视频/音频（通过 video-processing pipeline）。后续扩展：文章、微信公众号、网页等。

## 1. 定位

```
┌──────────────────────────────────────────────────────────────────┐
│  j-sink CLI — 多源信息收集中枢                                    │
│  统一入口：收集、查询、状态、标签、同步                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│
│  │status│ │ list │ │query │ │ tags │ │ info │ │ sync │ │clip ││
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └─────┘│
├──────────────────────────────────────────────────────────────────┤
│  sink-catalog.json — 元数据中心                                   │
│  存放：~/.config/j-sink/sink-catalog.json                        │
│  内容：所有条目的元信息、标签、来源类型、管线状态、文件路径映射     │
├──────────────────────────────────────────────────────────────────┤
│  schemas/ — 配置与 Schema 文件                                    │
│  存放：~/.config/j-sink/schemas/                                 │
│  内容：标签体系定义、分类规则、作者别名映射                         │
└──────────────────────────────────────────────────────────────────┘
         │ sync 按需写入
         ▼
┌──────────────────────────────────────────────────────────────────┐
│  Obsidian（轻量查看层）                                           │
│  - 笔记保持简单格式，只有基本元数据                                │
│  - 深度查询、标签管理、时间筛选 → 用 j-sink CLI                    │
└──────────────────────────────────────────────────────────────────┘
```

## 2. 数据源抽象

j-sink 不绑定特定数据源，通过 `sourceType` 字段区分来源：

| sourceType | 来源 | 当前状态 | 集成方式 |
|-----------|------|---------|---------|
| `video` | 视频/音频（YouTube、B站等） | ✅ 已有 | pipeline.py 处理后 import |
| `article` | 微信公众号、博客文章 | 🔜 规划中 | URL 抓取 → 正文提取 → import |
| `web` | 网页片段、书签 | 🔜 规划中 | j-sink clip <url> |
| `podcast` | 播客音频 | 🔜 规划中 | RSS 订阅 + 转录 |
| `note` | 手动记录的想法、灵感 | 🔜 规划中 | j-sink note "内容" |

## 3. 元数据存储：sink-catalog.json

### 3.1 文件位置

```
~/.config/j-sink/
├── sink-catalog.json     # 元数据中心
├── schemas/
│   ├── tags.json         # 标签体系定义
│   ├── categories.json   # 分类规则
│   └── authors.json      # 作者别名映射
└── config.json           # CLI 配置（Obsidian 路径、默认参数等）
```

### 3.2 sink-catalog.json Schema

```json
{
  "version": 1,
  "updatedAt": "2026-04-06T10:00:00+08:00",
  "items": {
    "BV1NGQoBAEVv": {
      "id": "BV1NGQoBAEVv",
      "sourceType": "video",
      "platform": "bilibili",
      "url": "https://www.bilibili.com/video/BV1NGQoBAEVv",
      "title": "北漂猛男，十几年来靠打游戏住上大别墅",
      "author": "摩的司机徐师傅",
      "publishDate": "2026-03-15",
      "duration": "41:41",
      "tags": ["游戏", "生活方式"],
      "category": "Audio",
      "addedAt": "2026-04-06T02:11:00+08:00",
      "pipeline": {
        "status": "completed",
        "engine": "local",
        "startedAt": "2026-04-06T02:11:00+08:00",
        "completedAt": "2026-04-06T02:26:00+08:00",
        "duration": 900
      },
      "files": {
        "workDir": "~/Downloads/video-pipeline/bilibili/BV1NGQoBAEVv",
        "audio": "audio.wav",
        "transcript": "audio.md",
        "obsidianOriginal": "00-Inbox/Audio/摩的司机徐师傅/标题-原文.md",
        "obsidianSummary": "00-Inbox/Audio/摩的司机徐师傅/标题-归纳.md"
      }
    },
    "wechat-article-123": {
      "id": "wechat-article-123",
      "sourceType": "article",
      "platform": "wechat",
      "url": "https://mp.weixin.qq.com/s/xxx",
      "title": "2026年宏观经济展望",
      "author": "某公众号",
      "publishDate": "2026-04-01",
      "tags": ["财经", "宏观经济"],
      "category": "Articles",
      "addedAt": "2026-04-05T08:00:00+08:00",
      "files": {
        "rawHtml": "~/Downloads/sink-cache/wechat/article-123.html",
        "extracted": "~/Downloads/sink-cache/wechat/article-123.md",
        "obsidianNote": "00-Inbox/Articles/某公众号/2026年宏观经济展望.md"
      }
    }
  },
  "indexes": {
    "byTag": {
      "游戏": ["BV1NGQoBAEVv"],
      "财经": ["wechat-article-123"],
      "宏观经济": ["wechat-article-123"]
    },
    "byAuthor": {
      "摩的司机徐师傅": ["BV1NGQoBAEVv"],
      "某公众号": ["wechat-article-123"]
    },
    "bySourceType": {
      "video": ["BV1NGQoBAEVv"],
      "article": ["wechat-article-123"]
    },
    "byPlatform": {
      "bilibili": ["BV1NGQoBAEVv"],
      "wechat": ["wechat-article-123"]
    },
    "byDate": {
      "2026-03": ["BV1NGQoBAEVv"],
      "2026-04": ["wechat-article-123"],
      "2026-Q1": ["BV1NGQoBAEVv"],
      "2026-Q2": ["wechat-article-123"]
    }
  }
}
```

### 3.3 字段说明

#### 通用字段（所有 sourceType 共享）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 条目唯一标识 |
| `sourceType` | enum | 来源类型：video / article / web / podcast / note |
| `platform` | string | 平台标识（bilibili / youtube / wechat / web / local） |
| `url` | string | 原始 URL（无 URL 则为空） |
| `title` | string | 标题 |
| `author` | string | 作者/来源名 |
| `publishDate` | string | 内容发布日期（核心时间维度） |
| `tags` | string[] | 标签（人工或规则打的） |
| `category` | string | Obsidian 分类目录 |
| `addedAt` | string ISO8601 | 条目入库时间 |
| `files` | object | 文件路径映射（字段因 sourceType 而异） |

#### video 专有字段

| 字段 | 说明 |
|------|------|
| `duration` | 视频时长 |
| `pipeline.*` | 管线执行状态（extract → subtitle → obsidian） |
| `files.audio` | 音频文件 |
| `files.transcript` | 转录文件 |
| `files.obsidianOriginal` | Obsidian 原文笔记 |
| `files.obsidianSummary` | Obsidian 归纳笔记 |

#### article 专有字段

| 字段 | 说明 |
|------|------|
| `files.rawHtml` | 原始 HTML 缓存 |
| `files.extracted` | 提取后的 Markdown |
| `files.obsidianNote` | Obsidian 笔记 |

## 4. Schema 配置文件

### 4.1 tags.json — 标签体系

```json
{
  "version": 1,
  "tagGroups": [
    {
      "name": "财经",
      "description": "财经类内容，时间敏感度高",
      "decayRule": "monthly",
      "subTags": ["宏观经济", "股票", "利率", "加密货币", "房地产"]
    },
    {
      "name": "历史",
      "description": "历史类内容，按课题分类",
      "decayRule": "none",
      "subTags": ["明清史", "二战", "冷战", "中国古代史", "世界史"]
    },
    {
      "name": "技术",
      "description": "技术类内容",
      "decayRule": "yearly",
      "subTags": ["AI", "前端", "后端", "DevOps", "编程语言"]
    },
    {
      "name": "生活方式",
      "description": "生活类内容",
      "decayRule": "none",
      "subTags": ["游戏", "旅行", "美食", "摄影"]
    }
  ],
  "autoTagRules": [
    {
      "match": {"author": "半佛仙人"},
      "tags": ["财经", "商业分析"]
    },
    {
      "match": {"platform": "youtube", "author": "李永乐老师"},
      "tags": ["科普", "数学"]
    },
    {
      "match": {"sourceType": "article", "platform": "wechat", "authorRegex": ".*财经.*"},
      "tags": ["财经"]
    }
  ]
}
```

**decayRule 说明**：

| 规则 | 含义 | 查询时效果 |
|------|------|-----------|
| `monthly` | 按月衰减 | 查询时优先展示近 3 个月内容 |
| `yearly` | 按年衰减 | 查询时优先展示今年内容 |
| `none` | 不衰减 | 始终同等展示 |

### 4.2 categories.json — 分类规则

```json
{
  "version": 1,
  "categories": [
    {
      "name": "Audio",
      "path": "00-Inbox/Audio",
      "description": "视频/音频笔记",
      "sourceTypes": ["video"]
    },
    {
      "name": "Articles",
      "path": "00-Inbox/Articles",
      "description": "文章笔记",
      "sourceTypes": ["article"]
    },
    {
      "name": "Clips",
      "path": "00-Inbox/Clips",
      "description": "网页剪藏",
      "sourceTypes": ["web"]
    },
    {
      "name": "财经",
      "path": "00-Inbox/Finance",
      "description": "财经观点（按时间线组织）"
    },
    {
      "name": "历史",
      "path": "00-Inbox/History",
      "description": "历史课题笔记（按课题组织）"
    }
  ]
}
```

### 4.3 authors.json — 作者别名映射

```json
{
  "version": 1,
  "aliases": {
    "半佛仙人": ["半佛", "半佛仙人Official"],
    "李永乐老师": ["李老师", "李永乐老师官方"]
  }
}
```

## 5. CLI 命令设计

### 5.1 全局选项

```bash
j-sink [global-options] <command> [command-args]

全局选项:
  --config-dir      配置目录（默认 ~/.config/j-sink）
  --format          输出格式：table / json / csv（默认 table）
  --no-color        禁用彩色输出
```

### 5.2 命令总览

```
j-sink
├── status              收集状态总览
├── list                列出所有条目
├── query               按条件查询（支持 decayRule）
├── info <id>           查看单个条目详情
├── tags                标签管理
│   ├── list            列出所有标签
│   ├── add             给条目添加标签
│   ├── remove          移除条目标签
│   ├── groups          查看标签分组
│   └── history         标签变更历史
├── sync                同步到 Obsidian
├── import              从 pipeline 导入条目
├── clip <url>          快速剪藏网页（未来）
├── note <content>      快速记录想法（未来）
├── config              配置管理
│   ├── show            显示当前配置
│   ├── init            初始化配置和 schema
│   └── path            显示配置文件路径
└── stats               统计信息
```

### 5.3 核心命令详解

#### `j-sink status` — 收集状态

```bash
$ j-sink status
📊 收集状态总览
  总条目: 42 | video: 25 | article: 15 | web: 2
  已完成: 38 | 处理中: 2 | 失败: 2
  最近入库: 2026-04-06 (3条)
  未同步 Obsidian: 5条

$ j-sink status --verbose
📊 收集状态总览
  总条目: 42 | video: 25 | article: 15 | web: 2
  已完成: 38 | 处理中: 2 | 失败: 2

⚠️  失败任务:
  BV1xx1 [video] → 转录失败: API timeout
  wechat-456 [article] → 正文提取失败

🔄 处理中:
  BV1yy1 [video] → subtitle 阶段 (重试 1/3)

📤 未同步到 Obsidian: 5 条
```

#### `j-sink list` — 列出条目

```bash
# 默认列出所有
$ j-sink list
ID                  类型     平台      作者             发布时间      标签         状态
BV1NGQoBAEVv        video   bilibili  摩的司机徐师傅   2026-03-15   游戏,生活   ✅
wechat-article-123  article wechat    某公众号         2026-04-01   财经        ✅

# 按来源类型筛选
$ j-sink list --type video
$ j-sink list --type article

# 按平台筛选
$ j-sink list --platform bilibili

# 按作者筛选
$ j-sink list --author "半佛仙人"

# 按时间范围（基于 publishDate）
$ j-sink list --after 2026-03-01 --before 2026-04-01

# 按状态
$ j-sink list --status failed

# JSON 输出
$ j-sink list --format json
```

#### `j-sink query` — 高级查询

```bash
# 查询财经类、最近3个月的内容（利用 decayRule）
$ j-sink query --tag 财经 --recent 3m

# 查询历史类、按课题分组
$ j-sink query --tag 历史 --group-by tag

# 跨数据源查询（视频 + 文章中的财经内容）
$ j-sink query --tag 财经 --sort-by publishDate --order desc

# 全文搜索标题
$ j-sink query --search "利率"

# 只看视频来源
$ j-sink query --type video --tag 技术

# 输出为 CSV
$ j-sink query --tag 财经 --format csv -o finance-notes.csv
```

#### `j-sink info <id>` — 条目详情

```bash
$ j-sink info BV1NGQoBAEVv

📋 北漂猛男，十几年来靠打游戏住上大别墅
  ID:       BV1NGQoBAEVv
  类型:     video
  平台:     bilibili
  作者:     摩的司机徐师傅
  发布:     2026-03-15
  时长:     41:41
  标签:     游戏, 生活方式
  状态:     ✅ 已完成

📁 文件:
  工作目录: ~/Downloads/video-pipeline/bilibili/BV1NGQoBAEVv
  音频:     audio.wav (76MB)
  转录:     audio.md (82KB)
  原文:     00-Inbox/Audio/摩的司机徐师傅/标题-原文.md
  归纳:     00-Inbox/Audio/摩的司机徐师傅/标题-归纳.md

⏱ 管线耗时:
  extract:   45s
  subtitle:  4m15s (asr-mlx-whisper)
  obsidian:  6m30s

🔗 URL: https://www.bilibili.com/video/BV1NGQoBAEVv
```

#### `j-sink tags` — 标签管理

```bash
# 查看所有标签及统计
$ j-sink tags list
标签        数量  分组     衰减规则   涵盖来源
财经         15   财经     monthly   video(8) article(7)
游戏          8   生活方式  none      video(8)
历史          6   历史     none      video(4) article(2)

# 给条目添加标签
$ j-sink tags add BV1NGQoBAEVv --tag "游戏" --tag "生活方式"

# 批量添加（按作者）
$ j-sink tags add --author "半佛仙人" --tag 财经

# 跨来源类型批量打标
$ j-sink tags add --type article --platform wechat --tag "微信文章"

# 移除标签
$ j-sink tags remove BV1NGQoBAEVv --tag "生活方式"

# 查看标签分组定义
$ j-sink tags groups

# 查看标签变更历史
$ j-sink tags history --tag 财经 --last 10
```

#### `j-sink sync` — 同步到 Obsidian

```bash
# 同步所有未同步的条目
$ j-sink sync
📤 同步 5 个条目到 Obsidian...
  ✅ BV1NGQoBAEVv [video] → 00-Inbox/Audio/摩的司机徐师傅/
  ✅ wechat-123 [article] → 00-Inbox/Articles/某公众号/

# 只同步特定类型
$ j-sink sync --type video

# 只同步特定标签
$ j-sink sync --tag 财经

# 预览模式
$ j-sink sync --dry-run
```

#### `j-sink import` — 导入条目

```bash
# 从 video pipeline 导入
$ j-sink import --from-pipeline ~/Downloads/video-pipeline/bilibili/BV1NGQoBAEVv

# 批量导入所有已完成 pipeline
$ j-sink import --from-pipeline ~/Downloads/video-pipeline/ --all

# 从自定义来源导入（未来用于 article 等）
$ j-sink import --source-type article --url "https://mp.weixin.qq.com/s/xxx"
```

#### `j-sink stats` — 统计信息

```bash
$ j-sink stats

📊 统计概览
  总条目: 42
  按类型: video(25) article(15) web(2)
  按平台: bilibili(18) youtube(7) wechat(15) web(2)
  按标签: 财经(15) 游戏(8) 历史(6) 技术(5) ...
  按月份:
    2026-03: 15
    2026-04: 27
  视频总时长: 18h30m
  总处理耗时: 2h15m

$ j-sink stats --by-source
$ j-sink stats --timeline
$ j-sink stats --by-tag
```

## 6. 管线集成

### 6.1 数据流

```
                         j-sink CLI
                         ──────────
                         统一收集入口
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         video pipeline   article fetcher   web clipper
         ──────────────   ─────────────   ─────────────
         extract.py       (未来)           (未来)
              │
              ▼
         yt-dlp --dump-single-json
              │
              ▼
         upload_date ──┐
         title         │
         author        ├──▶ sink-catalog.json
         duration      │
                        │
         pipeline.py ──┘
         处理完成后自动 import
```

### 6.2 extract.py 改动

在 `write_meta()` 中新增 `publishDate` 字段：

```python
# yt-dlp 返回的 upload_date 格式为 "20260315"
upload_date = info.get("upload_date")  # "YYYYMMDD"
if upload_date:
    publish_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
else:
    publish_date = None

data = {
    "id": info.get("id"),
    "platform": ...,
    "publishDate": publish_date,  # 新增
    ...
}
```

### 6.3 pipeline.py 改动

处理完成后，自动注册到 sink-catalog.json：

```python
def register_to_sink(work_dir: Path, result: dict) -> None:
    """将处理结果注册到 j-sink catalog。"""
    catalog = load_catalog()
    meta = read_meta(work_dir)
    item_id = meta.get("id", "")
    catalog["items"][item_id] = {
        "id": item_id,
        "sourceType": "video",
        "platform": meta.get("platform", ""),
        "publishDate": meta.get("publishDate", ""),
        ...
    }
    rebuild_indexes(catalog)
    save_catalog(catalog)
```

## 7. Obsidian 轻量化

### 7.1 笔记保持简单

笔记只保留最基本的信息，不加重度 frontmatter：

```markdown
# 标题

> **作者**: xxx | **来源**: URL | **发布**: 2026-03-15
> **类型**: video | **时长**: xx:xx

## 完整文案 / 正文
...
---
#sink #视频笔记 #作者名
```

### 7.2 深度查询走 CLI

```bash
# 不需要在 Obsidian 里装 Dataview
# 终端一条命令搞定：
j-sink query --tag 财经 --after 2026-03-01 --sort-by publishDate

# 跨来源查询：视频 + 文章中的财经内容
j-sink query --tag 财经 --format table
```

## 8. 内部机制

### 8.1 ID 生成策略

| sourceType | ID 来源 | 示例 | 冲突处理 |
|-----------|--------|------|---------|
| `video` | 平台原生 ID | `BV1NGQoBAEVv`、`dQw4w9WgXcQ` | 平台 + ID 天然唯一 |
| `article` | `{platform}-{hash(url,8)}` | `wechat-a3f5b7c9` | URL 去重 |
| `web` | `{domain}-{hash(url,8)}` | `mp.weixin-a3f5b7c9` | URL 去重 |
| `note` | `note-{timestamp}` | `note-20260406103000` | 时间戳唯一 |

导入时如果 catalog 中已存在同 ID 条目，则合并更新（不覆盖已有标签）。

### 8.2 catalog.ts 核心 API

```typescript
// 读取 catalog（懒加载 + 内存缓存）
function loadCatalog(configDir: string): Catalog

// 保存 catalog（原子写入：tmp → rename）
function saveCatalog(catalog: Catalog): void

// 重建所有倒排索引
function rebuildIndexes(catalog: Catalog): void

// 单条 CRUD
function getItem(catalog: Catalog, id: string): CatalogItem | undefined
function upsertItem(catalog: Catalog, item: CatalogItem): void  // 合并不覆盖 tags
function deleteItem(catalog: Catalog, id: string): void

// 查询
function queryItems(catalog: Catalog, filter: QueryFilter): CatalogItem[]
function queryWithDecay(catalog: Catalog, filter: QueryFilter, schemas: Schemas): CatalogItem[]

// 标签操作
function addTags(catalog: Catalog, id: string, tags: string[]): void
function removeTags(catalog: Catalog, id: string, tags: string[]): void
function getItemsByTag(catalog: Catalog, tag: string): CatalogItem[]
```

### 8.3 索引维护策略

```typescript
// 写入时同步维护索引（增量更新，不全量重建）
function updateIndexForItem(catalog: Catalog, item: CatalogItem): void {
  const { indexes } = catalog;

  // byTag: 移除旧条目 + 添加新条目
  for (const [tag, ids] of Object.entries(indexes.byTag)) {
    indexes.byTag[tag] = ids.filter(id => id !== item.id);
  }
  for (const tag of item.tags) {
    indexes.byTag[tag] = [...(indexes.byTag[tag] || []), item.id];
  }

  // byAuthor / bySourceType / byPlatform / byDate 同理
}
```

### 8.4 autoTag 执行流程

```
import 触发
    │
    ▼
读取 item（author, platform, sourceType, title）
    │
    ▼
遍历 tags.json → autoTagRules
    │
    ▼
规则匹配:
  match.author 精确匹配（含 authors.json 别名展开）
  match.platform 精确匹配
  match.sourceType 精确匹配
  match.authorRegex 正则匹配
    │
    ▼
匹配成功 → 合并 tags（去重）
    │
    ▼
写入 catalog.item.tags
```

### 8.5 原子写入

所有 catalog.json 写入使用原子操作：

```typescript
function atomicWriteJSON(filePath: string, data: unknown): void {
  const tmpPath = filePath + '.tmp';
  writeFileSync(tmpPath, JSON.stringify(data, null, 2));
  renameSync(tmpPath, filePath);  // 同文件系统 rename 是原子操作
}
```

### 8.6 Schema 版本迁移

```typescript
interface Migration {
  fromVersion: number;
  toVersion: number;
  migrate(catalog: any): Catalog;
}

const MIGRATIONS: Migration[] = [
  {
    fromVersion: 1,
    toVersion: 2,
    migrate: (old) => ({
      ...old,
      version: 2,
      // 示例：给所有 video 条目新增 subtitleSource 字段
      items: mapValues(old.items, item =>
        item.sourceType === 'video'
          ? { ...item, subtitleSource: item.subtitleSource ?? 'none' }
          : item
      )
    })
  }
];

function migrateCatalog(catalog: any): Catalog {
  let current = catalog;
  while (current.version < LATEST_VERSION) {
    const migration = MIGRATIONS.find(m => m.fromVersion === current.version);
    if (!migration) break;
    current = migration.migrate(current);
  }
  return current;
}
```

### 8.7 config.json — CLI 配置

```json
{
  "version": 1,
  "obsidianRepo": "~/jacky-github/jacky-obsidian",
  "pipelineDir": "~/Downloads/video-pipeline",
  "defaults": {
    "sourceType": "video",
    "engine": "local",
    "model": "large-v3-turbo",
    "category": "Audio"
  },
  "display": {
    "dateFormat": "YYYY-MM-DD",
    "tableMaxWidth": 120,
    "colorScheme": "terminal-noir"
  }
}
```

`j-sink config init` 初始化时自动生成默认配置，并尝试从环境变量 `OBSIDIAN_REPO` 读取 Obsidian 路径。

### 8.8 性能边界

| 指标 | 阈值 | 策略 |
|------|------|------|
| catalog 条目数 | < 10,000 | JSON 全量读写，无性能问题 |
| catalog 文件大小 | < 5MB | 单次读写 < 50ms |
| 索引重建 | 增量更新 | 单条变更只更新相关索引 |
| 全量重建 | 启动时/手动 | `j-sink config rebuild-index` |

> 对于个人使用场景，JSON 存储 + 内存缓存足够。如果未来条目超过 10,000，考虑迁移到 SQLite。

## 9. 与现有 pipeline 的集成细节

### 9.1 pipeline.py 集成点

pipeline.py 在 `process_url_task()` 和 `process_local_task()` 的**成功路径末尾**，新增一个可选步骤：

```python
# pipeline.py 末尾，pipeline status 设为 completed 之后
if which("j-sink"):
    subprocess.run(
        ["j-sink", "import", "--from-pipeline", str(work_dir)],
        capture_output=True, text=True,
    )
else:
    # j-sink 未安装时静默跳过
    pass
```

**设计决策**：j-sink 是可选依赖。pipeline.py 不 import j-sink 的任何代码，通过 subprocess 调用，解耦合。

### 9.2 extract.py → publishDate 映射

yt-dlp `--dump-single-json` 返回的时间字段：

| yt-dlp 字段 | 格式 | 说明 |
|-------------|------|------|
| `upload_date` | `"20260315"` | 上传日期（最常用） |
| `release_date` | `"20260315"` | 发布日期（部分视频有） |
| `timestamp` | `unix timestamp` | 上传时间戳 |

优先级：`upload_date` > `release_date` > `timestamp` > `None`

### 9.3 import 命令的 meta.json 解析

`j-sink import --from-pipeline <work-dir>` 会读取 work-dir 下的 meta.json，做字段映射：

```typescript
function mapPipelineMetaToCatalogItem(meta: PipelineMeta): CatalogItem {
  return {
    id: meta.id,
    sourceType: 'video',
    platform: meta.platform,
    url: meta.url,
    title: meta.title,
    author: meta.author,
    publishDate: meta.publishDate,  // 来自 extract.py 新增字段
    duration: meta.duration,
    tags: [],                        // 导入时先空，后续 autoTag 或手动打
    category: meta.pipeline?.category || 'Audio',
    addedAt: new Date().toISOString(),
    pipeline: {
      status: 'completed',
      engine: meta.pipeline?.engine,
      startedAt: meta.pipeline?.startedAt,
      completedAt: meta.pipeline?.completedAt,
      duration: meta.pipeline?.duration,
    },
    files: {
      workDir: meta.workDir || workDir,
      audio: meta.stages?.media?.audioFile,
      transcript: meta.stages?.subtitle?.file,
      obsidianOriginal: meta.stages?.obsidian?.files?.originalPath,
      obsidianSummary: meta.stages?.obsidian?.files?.summaryPath,
    },
  };
}
```

## 10. 技术实现

### 8.1 工具链

| 组件 | 选择 | 理由 |
|------|------|------|
| CLI 框架 | `cac` | 轻量，和 j-skills 一致 |
| 交互 UI | `@clack/prompts` | 终端交互统一风格 |
| 颜色 | `picocolors` | 超轻量 |
| 构建 | `tsup` | 零配置 |
| 存储 | JSON 文件 | 透明、可 git 跟踪、无外部依赖 |

### 8.2 包结构

```
j-sink/
├── package.json
├── src/
│   ├── index.ts            # CLI 入口（cac）
│   ├── commands/
│   │   ├── status.ts
│   │   ├── list.ts
│   │   ├── query.ts
│   │   ├── info.ts
│   │   ├── tags.ts
│   │   ├── sync.ts
│   │   ├── import.ts
│   │   └── stats.ts
│   ├── catalog.ts          # sink-catalog.json 读写 + 索引维护
│   ├── schemas.ts          # schema 文件加载
│   ├── query-engine.ts     # 查询引擎（过滤 + 排序 + 分组 + decayRule）
│   ├── format.ts           # 输出格式化（table/json/csv）
│   └── types.ts            # TypeScript 类型定义
├── schemas/                # 默认 schema 文件
│   ├── tags.json
│   ├── categories.json
│   └── authors.json
└── tsconfig.json
```

### 8.3 npm 包名

`@wangjs-jacky/j-sink`

## 9. 实施路径

### Phase 1：核心框架 + 基础命令

1. 初始化项目（cac + tsup）
2. 实现 catalog.ts（读写 + 索引维护）
3. 实现基础命令：`status`、`list`、`info`
4. 实现 `import` 命令（从 pipeline 目录导入）
5. 修改 extract.py 提取 publishDate

### Phase 2：查询 + 标签

6. 实现 `query` 命令（过滤 + 排序 + decayRule）
7. 实现 `tags` 命令组
8. 实现 schema 文件加载

### Phase 3：同步 + 集成

9. 实现 `sync` 命令
10. 修改 pipeline.py 自动注册到 catalog
11. 实现 `stats` 命令

### Phase 4：发布 + 扩展

12. 发布 `@wangjs-jacky/j-sink` 到 npm
13. 更新 SKILL.md 文档
14. （未来）实现 article 数据源
15. （未来）实现 web clipper
