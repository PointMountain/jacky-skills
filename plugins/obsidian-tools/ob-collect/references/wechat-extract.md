# 微信公众号 / 网页图片提取规范

> **【硬约束】网页内容包含图片时，必须完整处理。图片归属 raw 层，wiki 层只做引用，不重复嵌入。**

## 一、为什么 innerText 会漏图片

最常见的错误：

```javascript
// ❌ 错误：只获取文字，img 标签被忽略
var content = document.querySelector('#js_content');
return content.innerText;  // 图片完全丢失
```

`element.innerText` 只返回**可见文字**，`<img>` 标签完全被忽略。

**正确做法**：文字和图片分开提取

```javascript
// ✅ 正确：文字 + 图片分别提取
var text = content.innerText;
var imgs = Array.from(content.querySelectorAll('img')).map(img => ({
  url: img.getAttribute('data-src') || img.src,
  width: img.getAttribute('data-w'),
  alt: img.alt
}));
```

## 二、懒加载陷阱

很多平台（微信、知乎、小红书等）的图片使用**懒加载**：

- `src` 属性可能是 1×1 像素的 SVG 占位符
- 真实图片地址藏在 `data-src` / `data-actualsrc` / `data-lazy-src` 属性中
- 只有图片滚动到可视区域，浏览器才会把 `data-src` 写到 `src`

### 解决方案：先滚动，再读 `data-src`

```bash
# 1. 滚动页面触发懒加载
agent-browser scroll down 1000 && agent-browser wait 2000

# 2. 用 eval 读取所有图片的 data-src
agent-browser eval --stdin <<'EVALEOF'
(function() {
  var content = document.querySelector('#js_content') || document.querySelector('.rich_media_content');
  var imgs = Array.from(content.querySelectorAll('img')).map(function(img, i) {
    // 优先 data-src，其次 src
    var url = img.getAttribute('data-src') || img.src;
    // 清理 webp 转换参数
    url = url.replace(/&tp=webp&wxfrom=\d+&wx_lazy=\d+/, '').replace(/#imgIndex=\d+/, '');
    return { index: i+1, url: url };
  }).filter(function(img) {
    // 过滤 SVG 占位符
    return img.url && !img.url.startsWith('data:image/svg');
  });
  return JSON.stringify(imgs, null, 2);
})()
EVALEOF
```

## 三、各平台 img 标签特性矩阵

| 平台 | 懒加载 | 真实地址属性 | 占位符特征 | 注意事项 |
|------|--------|-------------|------------|---------|
| **微信公众号** | ✅ | `data-src` | 1×1 SVG | `mp.weixin.qq.com`，先滚动；URL 含 `&watermark=1` 是水印 |
| **知乎** | ✅ | `data-actualsrc` 或 `data-original` | 模糊小图 | `zhihu.com` |
| **小红书** | ✅ | `data-src` | blob URL | `xiaohongshu.com` |
| **CSDN** | ✅ | `data-src` | gif loading | `csdn.net` |
| **Medium** | ✅ | `srcset` | progressive jpeg | 用最大尺寸的 srcset |
| **通用网页** | 部分 | `data-src` / `data-lazy-src` / `loading="lazy"` | 多样 | 先尝试 data-src，再 src |

## 四、下载与命名规范

### 下载位置（就近 attachments，不写死全局根目录）

raw md 文件和它的 attachments 必须**就近放在一起**，作为同一目录单元：

```bash
{raw_md_dir}/attachments/{YYYY-MM-DD}-{slug}/img_NNN.{ext}
```

按 raw md 归档路径计算 `{raw_md_dir}`：

| raw md 路径 | attachments 路径 |
|-------------|------------------|
| `raw/wechat/{author}/{date}-{slug}.md` | `raw/wechat/{author}/attachments/{date}-{slug}/img_NNN.{ext}` |
| `raw/web/{date}-{slug}.md` | `raw/web/attachments/{date}-{slug}/img_NNN.{ext}` |
| `raw/{author}/{title}.md` | `raw/{author}/attachments/{slug}/img_NNN.{ext}` |

### 命名规则

- `{date-slug}` 目录：每篇文章独占一个子目录，与 md 文件名 slug 部分一致
- `img_NNN`：图片序号，**1-based 三位补零**（`img_001`、`img_002`、…、`img_099`、`img_100`）
- 扩展名：根据 URL/MIME 推断（`.jpeg` / `.png` / `.webp` / `.gif`）

### 示例

```bash
# 微信文章 raw/wechat/唱山羊/2023-08-11-定投1845天.md 对应：
raw/wechat/唱山羊/attachments/2023-08-11-定投1845天/img_001.jpeg
raw/wechat/唱山羊/attachments/2023-08-11-定投1845天/img_002.jpeg
```

### 下载命令

```bash
TARGET_DIR="$OBSIDIAN_REPO/raw/wechat/${AUTHOR}/attachments/${DATE}-${SLUG}"
mkdir -p "$TARGET_DIR"
curl -sL "$IMG_URL" -o "${TARGET_DIR}/img_$(printf '%03d' ${N}).${EXT}"
```

### 不要这样做

```bash
# ❌ 错误：写死全局 attachments 根目录
$OBSIDIAN_REPO/attachments/{date}-{slug}-img{N}.jpg

# 原因：raw 内容和图片分离在两棵树，迁移/删除/备份不一致；Obsidian app.json 的
# attachmentFolderPath 是手动新建笔记的默认目录，不适用程序化采集。
```

## 五、OCR 提取

下载图片后，**直接用 Read 工具读取图片文件**（Claude 具备多模态视觉能力，可直接识别图片内容）。

```
Read file_path="<vault>/raw/wechat/{author}/attachments/{date}-{slug}/img_001.jpeg"
```

读取后从图片中提取：
- 文字内容（标题、正文、数据表）
- 数值数据（保留格式）
- 关键信息（时间戳、账户信息等）

### OCR 与批量采集的关系

批量采集场景下 OCR 解耦成**独立异步阶段**：

1. 阶段 1（采集 + normalize）：图片下载到就近 attachments 目录，raw md 的 frontmatter 标 `status: uncompiled`，正文里每张图上方占位 `<!-- TODO OCR -->`
2. 阶段 2（OCR）：扫所有 `status: uncompiled` 的 raw md，Read 每张本地 img → 多模态识别 → 把 `<!-- TODO OCR -->` 替换为 `[!note] OCR callout`
3. 阶段 3（status 翻转）：所有图都 OCR 完，frontmatter 改为 `status: compiled`，进入 wiki 编译候选池

## 六、raw 层写入格式（硬约束）

每张图片在 raw 文件中的写入格式：**OCR callout 在前，图片嵌入在后**。

### 标准模板

```markdown
> [!note] OCR · 图片{NNN}（{时间/说明}）
> {从图片中识别的完整文字内容，保留数据格式}
> 
> | 列1 | 列2 | 列3 |
> |-----|-----|-----|
> | 数据 | 数据 | 数据 |

![[attachments/{date}-{slug}/img_{NNN}.jpeg]]
```

> 注意：`![[]]` 用相对 wikilink，Obsidian 会从当前 md 同级目录解析。这要求 md 文件和 attachments 目录在同一父目录（即 raw/{platform}/{author}/）下。

### 实际示例（微信收盘截图）

```markdown
> [!note] OCR · 持仓截图001（17:50）
> **浮动盈亏：+587,907.12 元** | 当日：+8,961.10
> 账户资产：1,966,749.00 | 总市值：1,956,163.65 | 仓位：99.46%
> 
> | 名称/市值 | 浮动盈亏 | 当日盈亏 | 仓位 |
> |-----------|---------|---------|------|
> | 500ETF 沪 618,783.30 | +298,601（+93.26%） | +5,119（+0.83%） | 31.46% |
> | HS300ETF 沪 608,728.85 | +179,286（+41.75%） | +2,581（+0.43%） | 30.95% |

![[attachments/2026-05-19-changshanyang-closing/img_001.jpeg]]
```

## 七、wiki 层约束

- **❌ 不重复嵌入图片**：图片和 OCR 数据只保留在 raw 层
- **✅ 引用 raw 文件**：wiki 通过 `[[raw/.../文件名]]` 引用 raw
- **✅ 基于 OCR 做整理**：wiki 可以用 raw 的 OCR 数据做表格、分析、归纳
- **✅ 独立观点**：wiki 是分析层，添加自己的洞察、对比、思考

### wiki 层示例

```markdown
# 2026-05-19 收盘总结（唱山羊）

> 来源：[[raw/wechat/2026-05-19-changshanyang-closing]]（含原始截图与 OCR）

## 持仓结构分析

| ETF | 仓位 | 浮盈 | 当日 |
|-----|------|------|------|
| 500ETF 沪 | 31.46% | +93.26% | +0.83% ✅ |
| HS300ETF 沪 | 30.95% | +41.75% | +0.43% ✅ |

## 观察要点

- A 股宽基合计 62%，是核心仓位
- 满仓状态，无加仓空间
```

## 八、完整提取工作流

### 8.1 单篇模式（手工抓取）

```text
1. agent-browser open <url>
2. agent-browser wait --load networkidle
3. agent-browser eval 提取文字内容（innerText）
4. agent-browser scroll down 1000 && agent-browser wait 2000
5. agent-browser eval 提取所有图片 data-src
6. curl 下载图片到 {raw_md_dir}/attachments/{date-slug}/
7. Read 工具读取每张图片（多模态 OCR）
8. 组装 raw 文件：YAML frontmatter + 文字 + OCR callout + ![[本地 wikilink]]
9. 编译 wiki 文件：仅引用 raw，不嵌入图片
10. agent-browser close
```

### 8.2 批量模式（推荐用 opencli 包装）

> 同一公众号 ≥ 50 篇时不走单篇模式，参见 SKILL.md「微信公众号批量采集模式」段落。流程概要：

```text
1. xlsx / URL 列表 → 写 meta.json
2. opencli weixin download 并发抓取（粗产物落 raw/wechat/{author}/__opencli_raw/）
3. normalize 脚本：
   a. md 平铺 → raw/wechat/{author}/{date}-{slug}.md
   b. 顶部 > 引用块 → YAML frontmatter
   c. 图片迁移 + 重编号 → attachments/{date-slug}/img_NNN.{ext}
   d. 正文 ![图片](远程URL) → ![[attachments/{date-slug}/img_NNN.jpeg]]
   e. 每张图片上方插 <!-- TODO OCR --> 占位
   f. 删除 __opencli_raw/
4. OCR 异步阶段：扫 status: uncompiled，逐张 Read+OCR，替换占位
5. wiki 蒸馏：多对一调 distiller
```

## 九、常见陷阱

| 陷阱 | 表现 | 解决方案 |
|------|------|----------|
| 用 innerText 读全部内容 | 图片完全丢失 | 单独 querySelectorAll('img') |
| 直接读 img.src | 拿到 SVG 占位符 | 优先 data-src |
| 不滚动就提取 | 懒加载图片全是占位符 | scroll down → wait → eval |
| URL 含 webp 转换参数 | 下载下来是 webp 不是 jpg | 清理 `&tp=webp&wxfrom=...` |
| 把图片放 wiki 层 | wiki 和 raw 重复 | 严格分层：图片归 raw |
| OCR 写在图片下方 | 不利于阅读 | callout 在前，图片在后 |
| 把图片放全局 `$OBSIDIAN_REPO/attachments/` | raw 和图片分离两棵树，迁移/备份不一致 | 就近放 `{raw_md_dir}/attachments/{date-slug}/` |
| 用微信 URL 哈希作为本地文件名 | 不可读，无序 | 按出现顺序重编号 `img_001.jpeg` |
| 单篇就同步 OCR | 批量场景下阻塞 | 解耦：先 status: uncompiled 占位，后批量 OCR |
| 正文 ![图片](远程URL) 不替换为本地 wikilink | 微信图片 URL 会过期，将来打不开 | normalize 阶段一次替换为 `![[attachments/...]]` |
