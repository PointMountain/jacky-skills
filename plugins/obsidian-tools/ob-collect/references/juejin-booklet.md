# 掘金小册采集

> 当采集来源为掘金小册 URL（`juejin.cn/book/xxx`）时，使用专用提取脚本。SKILL.md 主体只保留一行入口命令，本文是完整流程。

## 触发条件

- URL 匹配 `juejin.cn/book/{booklet_id}`
- 或用户说"采集掘金小册"、"提取掘金小册"

## 提取流程

1. **解析 URL**：提取 `booklet_id`（19 位数字）
2. **获取元数据**：调用掘金 API 获取小册标题、作者、章节列表
3. **批量提取**：逐章获取内容（Markdown/HTML），下载所有图片
4. **保存到 raw/juejin/**：

   ```
   raw/juejin/{booklet-slug}/
   ├── README.md          # 小册索引（标题、作者、目录）
   ├── 01-章节标题.md      # 每章一篇，带 frontmatter
   ├── 02-章节标题.md
   ├── ...
   └── images/
       ├── cover.png       # 封面图
       ├── 01-1.png        # 章节图片
       └── ...
   ```

5. **图片处理**：Markdown 中的图片 URL 替换为本地相对路径 `./images/xx`

## 脚本调用

```bash
# 提取脚本（ob-collect 内置）
node scripts/extract-juejin-booklet.mjs <booklet_url_or_id> \
  --output-dir "$OBSIDIAN_REPO/raw/juejin/{slug}" \
  --download-images
```

> 脚本依赖：`{SKILL_DIR}/scripts/node_modules/`，首次使用前 `cd {SKILL_DIR}/scripts && npm install`。

## 章节文件格式

```markdown
---
title: "章节标题"
booklet: "小册标题"
section_id: "7304230207517360169"
section_index: 2
date: "2026-04-28"
tags: ["掘金小册", "小册标题"]
---

章节内容（HTML 或 Markdown）
```

## HTML → Markdown 自动转换

脚本内置 HTML→Markdown 转换（基于 turndown 库），自动处理：

- **API 返回的 HTML**：免费小册 API 返回的内容可能是 HTML 格式
- **web-access 浏览器提取**：使用 web-access 从 DOM 提取的 innerHTML 会自动转为 Markdown
- **转换规则**：去掉 `<style>` 标签、`data-v-*` 属性、掘金特有 class；保留代码块语言标记
- **无需手动二次处理**：脚本输出即为干净的 Markdown

## 图片下载优化

v2 版本图片下载性能优化：

| 参数 | 值 | 说明 |
|------|-----|------|
| 并发数 | 20 | 高并发批量下载 |
| 超时 | 5s | 快速跳过失败图片 |
| 连接复用 | keepAlive | 减少 TCP 握手 |
| 去重 | URL hash | 相同 URL 只下载一次 |
| 跳过 | 已存在 | 断点续传友好 |

## web-access 模式（付费小册）

当 API 方式无法获取内容（如付费小册）时，可使用 web-access 通过浏览器 DOM 提取：

1. 启动 Chrome 调试模式 + cdp-proxy
2. 使用 web-access 导航到小册页面
3. 从 DOM 提取 innerHTML（得到的是 HTML）
4. 运行提取脚本 `--download-images` 自动完成 HTML→Markdown 转换 + 图片下载

## 注意事项

- **免费小册**：无需登录，直接 API 提取
- **付费小册**：需要通过 web-access 浏览器模式提取（API 方式返回空内容）
- **请求间隔**：脚本内置 300ms 延迟，避免频率限制
- **图片格式**：掘金 CDN 图片可能无标准扩展名，自动检测并保持原始格式
- **内容格式**：自动检测 HTML/Markdown，HTML 自动转换为 Markdown
- **版权**：仅下载用户已购买或免费的小册内容
