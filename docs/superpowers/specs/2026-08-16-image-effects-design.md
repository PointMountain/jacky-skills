# Image Effects Skill 与静态画廊设计

> 日期：2026-08-16 ｜ 状态：已获用户批准，进入自主实现

## 一、目标

创建一个可公开分享的 `image-effects` Skill。社区只需安装一次，即可通过稳定的效果 ID 将文字或上传图片交给 Codex 的原生生图能力，复现仓库中经过封装的视觉效果。

同一仓库提供静态 Gallery，用于浏览效果、查看示例、搜索筛选、复制调用语句和跳转到效果源码。Gallery 不提供在线生成、账号、后端、模型额度或用户图片上传。

Happy 只是效果库的一个消费入口。效果定义的唯一事实源放在独立 Skill 中，不再依赖 Happy 的 TypeScript 目录才能理解或执行。

## 二、非目标

- 不建设在线生图服务。
- 不建设账号、收藏、评论、计费或社区内容系统。
- 不引入全局生成锁；并发和任务状态由具体宿主自行管理。
- 不把每张效果卡注册成一个全局 Skill。
- 不迁移许可证、来源或预览图授权不明确的案例。
- 第一版不修改 Happy 的现有画廊运行链路，只提供稳定的机器可读索引，供后续接入。

## 三、采用方案

采用与 Video Shotcraft 相同的核心模式：**一个可安装 Skill + 多张渐进披露效果卡 + 一个由效果卡生成的静态 Gallery**。

用户调用示例：

```text
使用 $image-effects 的 healing-anime-scribble-v3，
把我上传的照片生成对应效果。
```

`SKILL.md` 只负责解析效果 ID、选择效果卡、检查输入、调用宿主生图能力和交付结果。完整 Prompt、负面约束、质量门、来源与许可证放入 `references/effects/*.md`，只在选中对应效果时读取。

## 四、仓库与同步边界

开发事实源位于：

```text
jacky-skills/skills/image-effects/
```

公开发布目标为：

```text
https://github.com/wangjs-jacky/image-effects
```

公开仓库根目录就是完整 Skill，便于使用：

```bash
npx skills add wangjs-jacky/image-effects
```

同步时复制 Skill 的实际文件，不复制符号链接，不包含本机路径、密钥、私有图片、临时输出或本地经验文件。公开仓库拥有自己的 README、LICENSE、GitHub Pages 配置和发布历史；这些公开包装文件不反向污染 `jacky-skills` 中的 Agent Skill 目录。

## 五、目录结构

### 5.1 `jacky-skills` 中的事实源

```text
skills/image-effects/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── INDEX.md
│   └── effects/
│       ├── healing-anime-scribble-v3.md
│       └── <effect-id>.md
├── assets/
│   └── previews/
│       └── <effect-id>.jpg
├── gallery/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── translations.js
│   └── api/library.json
└── scripts/
    ├── effect-library.mjs
    ├── build-gallery.mjs
    └── validate-effects.mjs
```

### 5.2 公开仓库附加文件

```text
README.md
README_CN.md
LICENSE
.github/workflows/pages.yml
```

## 六、效果卡契约

每张 `references/effects/<effect-id>.md` 使用 Markdown frontmatter 保存 Gallery 与验证脚本需要的机器字段，正文保存 Agent 执行所需的完整视觉编译规则。

必填字段：

- `id`：稳定、kebab-case 的效果 ID。
- `version`：效果语义版本。
- `title` / `title_zh`：中英文标题。
- `summary` / `summary_zh`：中英文简述。
- `category`：Gallery 分类。
- `input_mode`：`text`、`image` 或 `text-or-image`。
- `preview`：相对于 Skill 根目录的预览图路径。
- `source_repository`：公开来源仓库。
- `source_revision`：不可变提交 SHA。
- `license`：兼容的许可证标识。
- `license_url`：许可证或来源声明地址。

正文必须包含：

- 适用场景；
- 输入解释与参考图角色；
- 完整效果 Prompt；
- 硬性禁止项；
- 交付前质量检查；
- 结果交付要求。

验证脚本解析这些字段并生成 `gallery/api/library.json`。Gallery JSON 是构建产物，不允许手工维护。

## 七、执行流程

1. 从用户请求中解析效果 ID；未提供时读取 `references/INDEX.md`，根据意图推荐少量候选。
2. 只读取被选中的效果卡全文。
3. 按 `input_mode` 检查输入；缺少必需图片时停止并明确提示。
4. 将效果卡中的完整规则、用户目标和参考图直接交给当前宿主的原生生图工具。
5. 当前宿主没有图片工具时，输出并保存可直接复用的最终 Prompt，明确说明未实际出图。
6. 每张成功图片立即通过当前宿主支持的方式交付；Happy 环境使用 `mcp__happy__send_image`。

Skill 不承担全局排队或锁。批量任务允许宿主并发执行；每个输出独立成功、失败或重试。

## 八、静态 Gallery

Gallery 使用原生 HTML、CSS 和 JavaScript，不引入构建框架或服务端依赖。数据来自 `gallery/api/library.json`。

第一版提供：

- 响应式效果卡瀑布流；
- 中英文切换；
- 深色、浅色与跟随系统主题；
- 分类筛选和关键词搜索；
- 懒加载预览图；
- 查看输入类型、版本、来源与许可证；
- 复制单个或多个效果的调用语句；
- 跳转到对应 Markdown 效果卡；
- 复制安装命令。

视觉方向为深色图片编辑台：大图优先、克制信息密度、霓虹青绿色只用于选中态和操作反馈，不使用白底紫色渐变或模板化卡片网格质感。

## 九、首批迁移

候选范围为 Happy 当前 `GitHub Skills` 分类中的 9 个效果。每个效果在迁移前必须通过：

1. 来源仓库与固定 SHA 可验证；
2. Skill 或 Prompt 内容具备兼容许可证；
3. 预览图允许公开发布，并移除 EXIF/XMP/位置/设备元数据；
4. 不包含用户私有源照片或无法证明授权的输入图片；
5. 生成型与确定性处理型能力不会混用引擎。

不满足任一条件的效果不会进入公开首版，并在迁移报告中说明原因。首版至少包含 `healing-anime-scribble-v3`，确保仓库与 Gallery 即使只迁移一个效果也完整可用。

## 十、测试与验证

### 10.1 行为测试

使用 `node:test` 验证：

- 效果 ID 唯一且格式正确；
- 必填字段完整；
- 预览图存在且为可解码 JPEG/PNG；
- 来源 SHA 为完整提交哈希；
- 许可证与来源声明非空；
- `input_mode` 只接受允许值；
- Gallery JSON 由效果卡确定性生成；
- 搜索索引与调用语句包含正确效果 ID；
- 不同排序或重复执行不会产生非确定性差异。

测试验证可观察行为和数据约束，不通过正则锁定普通说明文案。

### 10.2 集成验证

- 运行官方 `quick_validate.py`；
- 运行 Skill 自有 Node 测试与验证脚本；
- 运行 `jacky-skills` 全仓测试和共享内容扫描；
- 本地启动静态 Gallery，验证桌面和移动端浏览、筛选、复制与来源链接；
- 检查公开仓库安装命令能安装并发现 `image-effects`；
- GitHub Pages 发布后验证公开 URL、资源加载和 Library 数量。

## 十一、错误处理

- 效果 ID 不存在：给出最多 5 个相近效果，不猜测执行。
- 缺少必需图片：不启动图片工具。
- 预览图缺失或损坏：构建失败，不发布不完整卡片。
- 来源或许可证不明确：迁移失败但不阻塞其他合规效果。
- 宿主图片工具不可用：降级为最终 Prompt，不声称已经生成图片。
- 单张图片生成失败：报告该效果失败，其他并发效果继续。
- Gallery 数据加载失败：显示可重试错误，不展示虚假空库。

## 十二、交付结果

完成后应具备：

- `jacky-skills` 中可安装、可验证的 `image-effects` Skill；
- 至少一个完整迁移、可实际调用的公开效果；
- 与效果卡自动同步的静态 Gallery；
- 公开 GitHub 仓库和 GitHub Pages URL；
- 清晰的安装与调用示例；
- 首批 9 个候选效果的迁移/排除结果与证据。
