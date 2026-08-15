# Image Effects Skill 与静态画廊设计

> 日期：2026-08-16 ｜ 状态：已获用户批准，进入自主实现

## 一、目标与首版范围

创建一个可公开分享的 `image-effects` Skill。社区安装一次后，可用稳定、带版本的效果 ID，把一张上传图片交给 Codex 或其他宿主的原生生图工具，复现经过封装的视觉效果。

同一仓库提供纯静态 Gallery，用于浏览效果、查看示例、搜索筛选、复制调用语句和跳转到效果源码。Gallery 不提供在线生成、账号、后端、模型额度或用户图片上传。

首版只迁移一个完整、可公开证明来源与授权的效果：

```text
healing-anime-scribble-v3@1.0.0
```

Happy 是效果库的一个消费入口。首版不修改 Happy 代码，只稳定输出后续可消费的 `library.json`。

## 二、非目标

- 不建设在线生图或社区内容服务。
- 不引入全局生成锁、队列或跨会话调度。
- 不把每张效果卡注册成一个全局 Skill。
- 不迁移确定性照片处理、批量处理或授权不完整的效果。
- 不在首版审计或迁移其余 8 个 Happy `GitHub Skills` 候选。
- 不保证所有宿主都能实际出图；无图片工具时只返回可复制 Prompt。

## 三、采用方案

采用与 Video Shotcraft 相同的核心模式：**一个可安装 Skill + 多张渐进披露效果卡 + 一个由效果卡生成的静态 Gallery**。

用户调用：

```text
使用 $image-effects 的 healing-anime-scribble-v3@1.0.0，
把我上传的照片生成对应效果。
```

`SKILL.md` 负责解析效果 ID、读取对应效果卡、检查输入、选择宿主能力和交付结果。完整视觉编译规则、禁止项、质量门、来源与许可证放在 `references/effects/*.md`，只在选中效果时读取。

## 四、事实源与公开仓库

唯一开发事实源：

```text
jacky-skills/skills/image-effects/
```

公开目标：

```text
https://github.com/wangjs-jacky/image-effects
visibility: public
default branch: main
Pages source: GitHub Actions artifact from gallery/
```

用户已明确批准创建公开仓库、首次推送和启用 GitHub Pages。发布前仍须只读确认：

1. `gh` 已登录为 `wangjs-jacky`；
2. 同名仓库不存在，或存在且为空、属于当前用户；
3. 不覆盖任何已有远端内容，不 force push；
4. 远端创建或 Pages 配置失败时保留本地提交，并停止后续外部变更。

### 4.1 单向导出契约

`scripts/export-public-repo.mjs --target <absolute-path> --source-commit <sha>` 从事实源确定性导出公开仓库。允许导出的路径只有：

- `SKILL.md`
- `agents/`
- `references/`
- `assets/previews/`
- `gallery/`
- `scripts/`
- `tests/`
- 从 `assets/public-repo/` 映射到公开根目录的 `README.md`、`README_CN.md`、`LICENSE`、`THIRD_PARTY_NOTICES.md`、`.gitignore` 与 `.github/workflows/pages.yml`

导出器生成 `.image-effects-export.json`，记录：

- `schemaVersion`；
- `sourceRepository`；
- `sourceCommit`；
- 按路径排序的受管文件 SHA-256。

删除语义：只删除上一次导出清单中的受管文件；拒绝删除未受管文件。目标存在未提交修改、导出后仍有未受管冲突文件、或目标路径不是专用仓库时失败。每次导出先写临时目录，完成校验后再替换受管文件；失败不改目标。

`--check` 重新生成到临时目录并与目标清单比较，发现漂移返回非零。公开仓库只接受导出结果，不在远端直接编辑受管文件。Git 提交提供发布回滚，不重写历史。

## 五、目录结构

```text
skills/image-effects/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── INDEX.md                 # 构建生成
│   └── effects/
│       └── healing-anime-scribble-v3.md
├── assets/
│   ├── previews/
│   │   └── healing-anime-scribble-v3.jpg
│   └── public-repo/             # 导出到公开仓库根目录的模板
├── gallery/
│   ├── index.html
│   ├── app.js
│   ├── gallery-model.mjs
│   ├── styles.css
│   ├── translations.js
│   ├── api/library.json         # 构建生成
│   ├── media/                   # 构建生成
│   └── source/                  # 构建生成
├── scripts/
│   ├── effect-library.mjs
│   ├── build-gallery.mjs
│   ├── validate-effects.mjs
│   └── export-public-repo.mjs
└── tests/
    ├── effect-library.test.mjs
    ├── gallery-model.test.mjs
    └── export-public-repo.test.mjs
```

## 六、效果卡机器契约

效果卡使用简单标量 Markdown frontmatter。解析器拒绝未知必填语义、重复键、多行 YAML、路径穿越或不受支持的值。

必填字段：

| 字段 | 约束 |
|---|---|
| `id` | kebab-case，稳定逻辑名 |
| `version` | SemVer，不带 `v` |
| `title_en` / `title_zh` | 非空 |
| `summary_en` / `summary_zh` | 非空 |
| `category` | 首版枚举仅 `portrait` |
| `execution_kind` | 首版仅 `host-image-generation` |
| `input_mode` | 首版仅 `image` |
| `input_min` / `input_max` | 首版都为 `1` |
| `input_formats` | 逗号分隔；首版必须为 `jpeg,png` |
| `output_count` | 首版为 `1` |
| `preview` | Skill 根目录内相对路径，不允许 `..` |
| `source_repository` | `owner/repo` |
| `source_revision` | 40 位 Git SHA |
| `source_paths` | 逗号分隔的上游行为来源路径 |
| `source_license_spdx` | 首版允许 `MIT` |
| `source_license_url` | HTTPS URL |
| `adaptation_notice` | 简短说明保留与修改 |
| `preview_origin` | 预览生成或创作来源 |
| `preview_author` | 权利主体 |
| `preview_license_spdx` | 首版允许 `CC-BY-4.0` |
| `preview_sha256` | 64 位 SHA-256 |

正文必须包含这六个二级标题：适用场景、输入契约、视觉编译规则、硬性禁止项、质量检查、交付要求。标题属于 Agent 协议导航，验证器检查结构；不锁定普通说明句子。

稳定引用格式为 `<id>@<version>`。省略版本时解析当前仓库中该 ID 的唯一版本，但 Gallery 复制和文档示例始终使用带版本引用。效果行为发生可观察变化时升级 MINOR；仅修正文案且不改变生成约束时升级 PATCH；破坏输入或输出契约时升级 MAJOR。

## 七、来源、授权与隐私

首版效果来源为 `ConardLi/garden-skills` 的固定提交与模板路径，Happy 中的 v3 编译规则属于公开仓库作者的适配内容。公开包必须包含：

- 根 `LICENSE`：只覆盖仓库原创代码与原创适配内容；
- `THIRD_PARTY_NOTICES.md`：记录上游仓库、SHA、精确文件路径、MIT notice、适配说明与内容 SHA；
- 效果卡中的上游来源字段；
- 独立的预览图来源、作者、许可证与 SHA；
- 不把根许可证描述为自动覆盖第三方材料。

验证器检查许可证允许列表、来源路径、内容哈希、预览哈希和元数据。在线验证模式通过 `gh api` 确认公开仓库与提交存在；离线测试使用固定 fixture，不依赖网络。

参考图隐私规则：

- 只使用用户当前请求明确附带的图片；不扫描附件目录或历史文件猜测输入；
- 不公开、提交、复制到 Gallery 或记录用户源图路径；
- 仅在宿主传输限制要求时创建临时副本；任务结束后删除临时副本；
- 只向图片工具发送最终 Prompt 和本次明确参考图；
- 最终回复不暴露私有路径、完整命令或工具日志。

## 八、执行流程

1. 解析 `<id>@<version>`；未提供 ID 时读取生成的 `references/INDEX.md`，最多推荐 5 个。
2. 只读取选中效果卡全文。
3. 确认当前请求恰好有 1 张 JPEG/PNG；否则停止，不启动图片工具。
4. 探测宿主是否提供图像生成工具。若有，将完整效果规则、用户目标和该参考图直接交给工具。
5. 工具调用错误或结果触发硬质量失败时，最多自动重试 1 次；重试保持同一效果版本与主体约束。
6. 无图片工具时，在回复中返回可复制的最终 Prompt，不写本地文件，除非用户明确要求保存；明确说明未实际出图。
7. 图片生成成功后通过宿主原生方式交付；若存在 `mcp__happy__send_image`，用生成图片的绝对路径发送。

Skill 不承担全局锁、排队或并发限制。多个效果由宿主并发处理，每个输出独立成功或失败。

## 九、Library 与 Gallery 契约

`gallery/api/library.json` 使用 `schemaVersion: 1`：

```json
{
  "schemaVersion": 1,
  "generatedAt": "由 SOURCE_DATE_EPOCH 决定的 ISO 时间",
  "effects": [
    {
      "ref": "healing-anime-scribble-v3@1.0.0",
      "id": "healing-anime-scribble-v3",
      "version": "1.0.0",
      "title": { "en": "...", "zh": "..." },
      "summary": { "en": "...", "zh": "..." },
      "category": "portrait",
      "input": { "mode": "image", "min": 1, "max": 1, "formats": ["jpeg", "png"] },
      "outputCount": 1,
      "previewUrl": "./media/healing-anime-scribble-v3.jpg",
      "sourceUrl": "./source/healing-anime-scribble-v3.md",
      "invocation": "Use $image-effects effect healing-anime-scribble-v3@1.0.0 on my uploaded image."
    }
  ]
}
```

效果按 `id`、SemVer 升序稳定排序。`SOURCE_DATE_EPOCH` 未设置时使用当前时间；测试和发布构建必须设置。构建脚本同时生成：

- `references/INDEX.md`；
- `gallery/api/library.json`；
- `gallery/media/` 中去元数据的预览副本；
- `gallery/source/` 中效果卡副本。

所有 Gallery URL 都是相对 `gallery/` 的 `./` 路径，因此在本地服务器和 `/image-effects/` Pages base path 下都成立。公开工作流上传整个 `gallery/` 目录作为 Pages artifact。

Gallery 使用原生 HTML、CSS 和 JavaScript，提供响应式大图卡片、中英文、系统/深/浅主题、分类筛选、搜索、懒加载、来源/许可证信息、单选或多选复制版本化调用语句、安装命令和可重试加载错误。

## 十、确定性构建与测试

### 10.1 Node 行为测试

使用 `node:test` 覆盖：

- frontmatter 解析、未知/重复字段和路径穿越；
- ID、SemVer、枚举、输入基数与格式；
- 来源 SHA、来源路径、许可证允许列表；
- 预览可解码、尺寸有效、SHA 匹配；
- JPEG/PNG 不含 EXIF、XMP、文本块、位置或设备元数据；
- 生成的 INDEX、Library、预览和源码副本可重复；
- Library schema、排序、相对 URL 与版本化 invocation；
- Gallery 搜索、分类筛选、语言标题和多选复制模型；
- 导出白名单、删除受管旧文件、保护未受管文件、清单哈希和 `--check` 漂移；
- 公开内容不含绝对用户路径、密钥模式或私有附件路径。

### 10.2 发布门

发布前依次运行：

1. 官方 `quick_validate.py`；
2. Skill 自有 Node 测试；
3. `validate-effects.mjs --online`；
4. 设置固定 `SOURCE_DATE_EPOCH` 构建 Gallery；
5. 再次构建并断言工作树无差异；
6. `jacky-skills` 全仓测试、共享内容扫描、Shell 与 Plugin 校验；
7. 导出公开仓库并运行 `--check`；
8. 本地 HTTP 服务验证 Gallery 桌面与移动视口；
9. 推送后检查 Actions、Pages URL、资源状态和公开安装发现。

普通说明文案不使用关键词正则测试；测试只覆盖机器协议与可观察行为。

## 十一、错误与回滚

- ID 或版本不存在：返回最多 5 个相近效果，不猜测执行。
- 缺少、过多或格式错误的图片：不启动图片工具。
- 宿主无图片工具：只返回 Prompt，不声称出图。
- 单次生成失败：最多重试 1 次，仍失败则报告当前效果失败。
- 预览、来源、许可证、哈希或公开内容扫描失败：构建失败，不发布。
- Gallery 加载失败：显示重试入口，不展示虚假空库。
- 同名远端已有内容：停止，不创建、不推送、不覆盖。
- 导出失败：临时目录删除，目标不变。
- 推送或 Pages 失败：保留本地与远端 Git 提交，通过新修复提交前进或回滚 Pages 部署，不 force push。

## 十二、交付结果

首版完成条件：

- `jacky-skills` 中存在可安装、可验证的 `image-effects` Skill；
- `healing-anime-scribble-v3@1.0.0` 可被 Agent 正确解析并执行或降级；
- 静态 Gallery 由效果卡确定性生成；
- 公开仓库 `wangjs-jacky/image-effects` 创建并可安装；
- GitHub Pages 可公开访问且 Gallery 资源完整；
- 公开导出清单可追溯到 `jacky-skills` 源提交；
- 所有本地、公开仓库与在线验证门通过。
