# Image Effects Skill and Gallery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 发布一个可安装的 `image-effects` Skill、一个经过来源验证的治愈系潦草淡彩效果，以及由同一效果卡确定性生成并部署到 GitHub Pages 的静态画廊。

**Architecture:** `skills/image-effects/references/effects/*.md` 是效果行为、版本、来源和许可证的唯一事实源。Node ESM 脚本解析并验证效果卡，生成索引、第三方声明和 Gallery 数据；另一个导出器只从干净 Git `HEAD` 读取白名单文件，单向同步到独立公开仓库。宿主负责实际图像生成与并发，Skill 只做效果解析、输入检查、Prompt 编译、一次可选重试和原生交付。

**Tech Stack:** Markdown Agent Skill、Node.js ESM、`node:test`、锁定版本 `sharp@0.35.3`（仅维护期完整图像解码）、原生 HTML/CSS/JavaScript、Git/GitHub CLI、GitHub Pages Actions。

---

## 文件结构与职责

- `skills/image-effects/SKILL.md`：Agent 的轻量入口、效果解析与宿主工具路由。
- `skills/image-effects/agents/openai.yaml`：Codex UI 元数据。
- `skills/image-effects/references/effects/healing-anime-scribble-v3.md`：首个版本化效果卡和唯一来源事实。
- `skills/image-effects/references/INDEX.md`：由效果卡生成的渐进披露索引。
- `skills/image-effects/assets/previews/healing-anime-scribble-v3.jpg`：已去元数据的公开预览。
- `skills/image-effects/assets/public-repo/*`：公开仓库根文件和 Pages workflow 模板。
- `skills/image-effects/scripts/effect-library.mjs`：frontmatter 解析、约束验证和 Library/Notice 数据建模。
- `skills/image-effects/scripts/build-gallery.mjs`：生成 INDEX、Library、Notice、预览和源码副本。
- `skills/image-effects/scripts/validate-effects.mjs`：离线验证与 `gh api` 在线来源哈希验证。
- `skills/image-effects/scripts/export-public-repo.mjs`：从干净 `HEAD` 原子化导出公开仓库。
- `skills/image-effects/gallery/gallery-model.mjs`：可独立测试的搜索、筛选、语言和选择状态。
- `skills/image-effects/gallery/gallery-runtime.mjs`：URL 筛选、焦点恢复、剪贴板降级与稳定 DOM ID。
- `skills/image-effects/gallery/{index.html,app.js,translations.js,styles.css}`：纯静态 Gallery UI。
- `skills/image-effects/tests/*.test.mjs`：机器协议和可观察行为测试。

## Chunk 1：Skill 契约与首个效果

### Task 1：官方脚手架与效果卡解析器

**Files:**
- Create: `skills/image-effects/SKILL.md`
- Create: `skills/image-effects/agents/openai.yaml`
- Create: `skills/image-effects/scripts/effect-library.mjs`
- Create: `skills/image-effects/tests/effect-library.test.mjs`

- [ ] **Step 1: 阅读 OpenAI YAML 规范并用官方脚手架初始化 Skill**

Run:

```bash
sed -n '1,240p' /Users/jiashengwang/.codex/skills/.system/skill-creator/references/openai_yaml.md
python3 /Users/jiashengwang/.codex/skills/.system/skill-creator/scripts/init_skill.py image-effects \
  --path skills \
  --resources scripts,references,assets \
  --interface 'display_name=Image Effects' \
  --interface 'short_description=Apply reusable visual effects to uploaded images' \
  --interface 'default_prompt=Use $image-effects to apply a selected versioned effect to my uploaded image.'
```

Expected: `skills/image-effects/` 只包含官方结构和待替换模板，不创建 README。

- [ ] **Step 2: 写解析器失败测试**

在 `effect-library.test.mjs` 用 `node:test` 覆盖：合法标量 frontmatter；重复键；未知字段；缺失必填字段；路径穿越；非法 ID/SemVer/SHA；`source_paths` 与 `source_sha256s` 不等长；重复来源路径；错误输入基数和许可证。

核心断言：

```js
const effect = parseEffect(validCard)
assert.equal(effect.ref, 'healing-anime-scribble-v3@1.0.0')
assert.deepEqual(effect.sources, [{
  path: 'skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md',
  sha256: '67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461',
}])
assert.throws(() => parseEffect(duplicateKeyCard), /duplicate/i)
assert.throws(() => parseEffect(mismatchedSourceHashes), /same length/i)
```

- [ ] **Step 3: 运行测试并确认红灯**

Run: `node --test skills/image-effects/tests/effect-library.test.mjs`

Expected: FAIL，因为解析器导出尚不存在。

- [ ] **Step 4: 实现最小严格解析器**

导出 `parseEffect(markdown, filePath)`、`loadEffects(root)`、`buildLibrary(effects, generatedAt)` 和纯函数 `renderThirdPartyNotices(effects, header)`。只支持设计稿字段与简单单行标量；拒绝重复键、未知键、空项、绝对路径和 `..`。将两个来源 CSV 按位置归一为 `sources[]`，并稳定按 ID、SemVer 排序；Notice 函数只拼接传入页眉与效果来源事实，不访问文件系统。

- [ ] **Step 5: 运行测试并确认绿灯**

Run: `node --test skills/image-effects/tests/effect-library.test.mjs`

Expected: PASS，且无网络访问。

- [ ] **Step 6: 写最小 SKILL 入口和合法 UI 元数据**

`SKILL.md` frontmatter 只保留 `name` 与第三人称 `description`。正文明确：解析版本化引用；无 ID 时从 INDEX 最多推荐 5 个；省略版本只在该 ID 当前恰有一个版本时解析；未知 ID/版本返回相近项但不执行；只读选中效果卡；仅接受当前请求中明确附带的一张 JPEG/PNG；不扫描附件目录；临时副本在任务结束后删除；优先宿主原生图像工具；最多一次针对性重试；无工具则返回最终 Prompt；无全局锁；Happy 可用时用原生图片交付工具。

- [ ] **Step 7: 验证并提交**

Run:

```bash
python3 /Users/jiashengwang/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/image-effects
node --test skills/image-effects/tests/effect-library.test.mjs
git add skills/image-effects
git commit -m "feat: scaffold image effects skill contract"
```

Expected: 两项验证通过，提交只包含 Task 1 文件。

### Task 2：效果卡、预览与媒体验证

**Files:**
- Create: `skills/image-effects/references/effects/healing-anime-scribble-v3.md`
- Create: `skills/image-effects/assets/previews/healing-anime-scribble-v3.jpg`
- Create: `skills/image-effects/package.json`
- Create: `skills/image-effects/package-lock.json`
- Create: `skills/image-effects/scripts/image-metadata.mjs`
- Create: `skills/image-effects/tests/effect-assets.test.mjs`

- [ ] **Step 1: 写效果资产失败测试**

覆盖：效果卡包含设计稿要求的全部 frontmatter 与六个协议标题；预览 SHA、1448×1086 尺寸并由 `sharp(...).raw().toBuffer()` 完整像素解码；JPEG 拒绝 EXIF、XMP、COM、GPS/设备文本；PNG 校验 chunk 并拒绝 `eXIf`、`tEXt`、`zTXt`、`iTXt`。测试用 `sharp` 在临时目录真实编码 JPEG/PNG fixture，再注入元数据失败样本，不只锁定当前预览格式。

- [ ] **Step 2: 运行测试并确认红灯**

Run: `node --test skills/image-effects/tests/effect-assets.test.mjs`

Expected: FAIL，因为效果卡、预览、锁定依赖和媒体检查器尚不存在。

- [ ] **Step 3: 锁定维护期图像解码依赖**

创建私有、ESM、Node ≥20 的 `package.json`，只把 `sharp` 固定为 `0.35.3` 的 devDependency，然后在 Skill 目录生成 lockfile 并安装。社区 Agent 读取 Skill/效果卡无需运行 npm；依赖只用于维护、构建和验证。

Run:

```bash
cd skills/image-effects
npm install --save-dev --save-exact sharp@0.35.3
node -p 'process.arch'
file node_modules/@img/sharp-darwin-arm64/lib/sharp-darwin-arm64.node
```

Expected: `package-lock.json` 生成；本机 Node 和 sharp 原生模块均为 `arm64`。CI 根据 lockfile 安装对应平台包。

- [ ] **Step 4: 实现真实解码与元数据检查器**

`image-metadata.mjs` 导出异步 `inspectImage(buffer, format)` 和 `assertMetadataFreeImage(buffer, format)`。先用 `sharp(buffer, { failOn: 'error' }).raw().toBuffer({ resolveWithObject: true })` 完整解码并取得尺寸，再解析 JPEG APP/COM segment 或 PNG chunk，拒绝上述元数据。文件只负责图片解码、结构和元数据，不解析效果卡或写文件。

- [ ] **Step 5: 创建完整效果卡**

使用完整 frontmatter，不留待定值：

```yaml
id: healing-anime-scribble-v3
version: 1.0.0
title_en: Healing Anime Scribble
title_zh: 治愈系潦草淡彩
summary_en: Redraw one portrait as an airy anime construction sketch with dense searching lines, sparse pale color, and quiet warm paper.
summary_zh: 将一张人物照片重绘为留白通透的动漫结构草图，以密集探索线条、稀薄淡彩和暖白纸张为核心。
category: portrait
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/healing-anime-scribble-v3.jpg
source_repository: ConardLi/garden-skills
source_revision: aaf9a82f5efd73e87cc0998edc398e75bfc35901
source_paths: skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md
source_sha256s: 67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461
source_license_spdx: MIT
source_license_url: https://github.com/ConardLi/garden-skills/blob/aaf9a82f5efd73e87cc0998edc398e75bfc35901/LICENSE
adaptation_notice: Preserves the one-photo anime construction sketch behavior and adds fixed v3 ratios, host-neutral delivery, privacy gates, and one targeted retry.
preview_origin: Text-only image generation of a fictional young adult with glasses, not based on a real person.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: 70a3c534832532faed62cb80816df56002382cb661b51d2077d7eab429760daf
```

正文从公开适配源 `../happy-study/happy/packages/happy-app/sources/components/agents/healingScribbleSketchPrompt.ts` 中的 `HEALING_SCRIBBLE_SKETCH_PROMPT` 迁移，不做摘要替代，并映射为：

- `适用场景`：完整重绘、非滤镜、一个主角的使用边界；
- `输入契约`：一张当前请求图片、Character Map、4–6 个身份锚点、隐私与继续生成复用原图；
- `视觉编译规则`：原 Prompt 的 Composition、Drawing language、Color and paper 全部规则，含 80–90% 线墨、8–16% 淡彩、55–70% 暖白留白；
- `硬性禁止项`：原 Prompt 的 Hard failures 全量清单，包括任何文字/UI/水印；
- `质量检查`：原 Prompt 的 Quality gate 全量清单与至多一次定向重试；
- `交付要求`：宿主原生交付、1–3 句本地化说明、不暴露完整 Prompt/私有路径/详细参数；不硬编码 Happy 专属调用。

- [ ] **Step 6: 复制并验证已授权预览**

Run:

```bash
cp ../happy-study/happy/packages/happy-app/sources/assets/images/gpt-image-2/reference-examples/gpt-image-2-healing-scribble-portrait.jpg skills/image-effects/assets/previews/healing-anime-scribble-v3.jpg
shasum -a 256 skills/image-effects/assets/previews/healing-anime-scribble-v3.jpg
node --test skills/image-effects/tests/effect-assets.test.mjs
```

Expected: SHA 为 `70a3c534832532faed62cb80816df56002382cb661b51d2077d7eab429760daf`，全部媒体和效果卡测试 PASS。

- [ ] **Step 7: 提交效果资产**

```bash
git add skills/image-effects/references/effects skills/image-effects/assets/previews skills/image-effects/package.json skills/image-effects/package-lock.json skills/image-effects/scripts/image-metadata.mjs skills/image-effects/tests/effect-assets.test.mjs
git commit -m "feat: add healing scribble effect assets"
git status --short
```

Expected: 提交只包含 Task 2 声明文件；除尚未提交的计划文档外工作树无变化。

### Task 3：确定性构建与固定来源验证

**Files:**
- Create: `skills/image-effects/assets/public-repo/THIRD_PARTY_NOTICES.header.md`
- Create: `skills/image-effects/scripts/build-gallery.mjs`
- Create: `skills/image-effects/scripts/validate-effects.mjs`
- Create: `skills/image-effects/tests/build-gallery.test.mjs`
- Generate: `skills/image-effects/references/INDEX.md`
- Generate: `skills/image-effects/assets/public-repo/THIRD_PARTY_NOTICES.md`
- Generate: `skills/image-effects/gallery/api/library.json`
- Generate: `skills/image-effects/gallery/media/healing-anime-scribble-v3@1.0.0.jpg`
- Generate: `skills/image-effects/gallery/source/healing-anime-scribble-v3@1.0.0.md`

- [ ] **Step 1: 写构建和验证失败测试**

让构建函数接受显式 `sourceRoot` 与 `outputRoot`，在两个独立临时目录构建。覆盖：固定 `SOURCE_DATE_EPOCH=1786809600` 时两棵输出树的路径集合和逐文件 SHA 完全一致；删除陈旧生成文件；稳定排序；Library 正确投影 repository、revision、MIT SPDX/URL 和预览 origin/author/CC-BY-4.0；Notice 的逐路径 SHA 只来自效果卡；在线验证函数会请求固定 revision 的固定 path 并比较解码后内容哈希；写入失败不替换现有产物。

- [ ] **Step 2: 运行测试并确认红灯**

Run: `SOURCE_DATE_EPOCH=1786809600 node --test skills/image-effects/tests/build-gallery.test.mjs`

Expected: FAIL，因为构建器与来源验证器尚不存在。

- [ ] **Step 3: 固定 Notice 页眉与上游 MIT notice**

`THIRD_PARTY_NOTICES.header.md` 明确根 `LICENSE` 不自动覆盖第三方材料，并包含固定提交下上游 `LICENSE` 的完整 MIT notice。用以下只读命令核对原文，实际文件用 `apply_patch` 创建：

```bash
gh api 'repos/ConardLi/garden-skills/contents/LICENSE?ref=aaf9a82f5efd73e87cc0998edc398e75bfc35901' --jq .content | tr -d '\n' | base64 --decode
```

`build-gallery.mjs` 从显式 `sourceRoot` 读取固定页眉，再调用纯函数 `renderThirdPartyNotices(effects, header)`；该函数只做字符串建模，按效果排序追加仓库、revision、逐路径 SHA、许可证 URL 和 adaptation notice。效果级事实不得手写进页眉，`effect-library.mjs` 不访问文件系统。

- [ ] **Step 4: 实现确定性构建与在线验证**

`build-gallery.mjs` 只负责编排文件系统：读取效果卡、调用 `effect-library.mjs` 建模、调用 `image-metadata.mjs` 验证媒体，然后生成 INDEX、Notice、`gallery/api/library.json`、`gallery/source/*.md` 和去元数据的 `gallery/media/*`。`generatedAt` 来自 `SOURCE_DATE_EPOCH`；先在同盘临时目录构建完整受管树，再原子替换并清理陈旧产物。`validate-effects.mjs --online` 只用 `gh api repos/{owner}/{repo}/contents/{path}?ref={revision}`，base64 解码后算 SHA-256。

- [ ] **Step 5: 运行离线和在线验证**

Run:

```bash
SOURCE_DATE_EPOCH=1786809600 node skills/image-effects/scripts/build-gallery.mjs
node --test skills/image-effects/tests/effect-library.test.mjs skills/image-effects/tests/effect-assets.test.mjs skills/image-effects/tests/build-gallery.test.mjs
node skills/image-effects/scripts/validate-effects.mjs --online
git add skills/image-effects
SOURCE_DATE_EPOCH=1786809600 node skills/image-effects/scripts/build-gallery.mjs
git diff --exit-code -- skills/image-effects
git ls-files --others --exclude-standard -- skills/image-effects | awk 'BEGIN { found=0 } { print; found=1 } END { exit found }'
```

Expected: 全部 PASS；两个临时构建的逐文件哈希一致；第二次真实构建相对已暂存基线既无修改/删除，也无新增未跟踪文件。

- [ ] **Step 6: 提交构建链路**

```bash
git commit -m "feat: generate image effects library artifacts"
git status --short
```

Expected: 提交只包含 Task 3 声明文件与生成产物；除尚未提交的计划文档外工作树无变化。

## Chunk 2：静态 Gallery

### Task 4：可测试 Gallery 状态模型

**Files:**
- Create: `skills/image-effects/gallery/gallery-model.mjs`
- Create: `skills/image-effects/tests/gallery-model.test.mjs`

- [ ] **Step 1: 写失败测试**

覆盖：中文/英文标题投影；大小写不敏感搜索；分类筛选；多选按 Library 顺序生成版本化 invocation；不存在 ID 被忽略；清空选择；Library schemaVersion 错误时抛出可展示错误；`idle → loading → ready/error → loading` 的加载与重试转换，重试清除旧错误但保留筛选偏好。

- [ ] **Step 2: 运行测试确认红灯**

Run: `node --test skills/image-effects/tests/gallery-model.test.mjs`

Expected: FAIL，因为模型模块不存在。

- [ ] **Step 3: 实现纯函数状态模型**

导出 `assertLibrary`、`createGalleryState`、`startLoading`、`loadSucceeded`、`loadFailed`、`retryLoad`、`getVisibleEffects`、`toggleSelection`、`clearSelection`、`getSelectedInvocations` 和 `localizeEffect`。状态包含 `loadStatus`、`loadError` 与递增 `loadAttempt`；模块不得访问 DOM 或浏览器全局。

- [ ] **Step 4: 运行测试并提交**

```bash
node --test skills/image-effects/tests/gallery-model.test.mjs
git add skills/image-effects/gallery/gallery-model.mjs skills/image-effects/tests/gallery-model.test.mjs
git commit -m "feat: add gallery state model"
```

Expected: PASS。

### Task 5：响应式静态展示页

**Files:**
- Create: `skills/image-effects/gallery/index.html`
- Create: `skills/image-effects/gallery/app.js`
- Create: `skills/image-effects/gallery/gallery-runtime.mjs`
- Create: `skills/image-effects/gallery/translations.js`
- Create: `skills/image-effects/gallery/styles.css`
- Create: `skills/image-effects/tests/gallery-assets.test.mjs`

- [ ] **Step 1: 写资源契约失败测试**

启动临时静态服务器并实际请求 `/index.html`、`/api/library.json`、预览和效果源码，断言 HTTP 200、JSON 可解析、所有相对 URL 可解析。断言 Library 中来源仓库、revision、MIT SPDX/URL 以及预览作者、来源、CC-BY-4.0 均由效果卡投影；加载重试已经在纯模型测试覆盖。不要写锁普通 UI 文案的关键词测试。

- [ ] **Step 2: 运行测试确认红灯**

Run: `node --test skills/image-effects/tests/gallery-assets.test.mjs`

Expected: FAIL，因为页面资源尚不存在。

- [ ] **Step 3: 实现 Gallery UI**

实现无框架单页：大图优先、深色默认但支持系统/浅色、中英文、搜索、分类、单选/多选、复制调用语句、安装命令、来源和许可证链接、懒加载与加载失败重试。来源和许可证只读 `library.json.provenance`，浏览器不解析 Markdown。为浏览器验收提供稳定语义选择器：`[data-testid=effect-card]`、`language-toggle`、`theme-toggle`、`search-input`、`category-filter`、`effect-select`、`copy-selected`、`install-command`、`source-link`、`load-error`、`retry-load`、`source-license`。视觉采用 Terminal Noir：深黑分层背景、霓虹绿/琥珀高光、轻玻璃层、扫描线/颗粒细节、Outfit + IBM Plex Mono；避免白底紫色渐变和模板化等宽卡片墙。移动端保持触控目标 ≥44px，尊重 `prefers-reduced-motion`。

- [ ] **Step 4: 运行行为测试与浏览器级烟测**

先运行资源测试：

```bash
node --test skills/image-effects/tests/gallery-model.test.mjs skills/image-effects/tests/gallery-assets.test.mjs
```

然后用可回收的独立服务进程和命名浏览器会话验收：

```bash
set -e
command -v playwright-cli
python3 -m http.server 4173 --bind 127.0.0.1 --directory skills/image-effects/gallery &
image_effects_server_pid=$!
trap 'playwright-cli -s=image-effects-gallery close >/dev/null 2>&1 || true; kill "$image_effects_server_pid" >/dev/null 2>&1 || true' EXIT
curl --fail --silent --show-error --retry 20 --retry-connrefused --retry-delay 1 http://127.0.0.1:4173/api/library.json >/dev/null
playwright-cli -s=image-effects-gallery open http://127.0.0.1:4173/
playwright-cli -s=image-effects-gallery resize 1440 900
playwright-cli -s=image-effects-gallery run-code "async page => {
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) });
  await page.reload();
  await page.locator('[data-testid=effect-card]').waitFor();
  const image = page.locator('[data-testid=effect-card] img');
  if (await image.getAttribute('loading') !== 'lazy') throw new Error('preview is not lazy');
  if (await image.evaluate(node => node.naturalWidth) < 1) throw new Error('preview did not decode');
  const license = await page.locator('[data-testid=source-license]').getAttribute('href');
  if (!license?.includes('ConardLi/garden-skills')) throw new Error('missing source license');
  const install = await page.locator('[data-testid=install-command]').innerText();
  if (!install.includes('npx skills add wangjs-jacky/image-effects')) throw new Error('install command is wrong');
  const sourceHref = await page.locator('[data-testid=source-link]').getAttribute('href');
  if (!sourceHref?.startsWith('./source/')) throw new Error('source link is not relative');
  const sourceResponse = await page.request.get(new URL(sourceHref, page.url()).href);
  if (!sourceResponse.ok()) throw new Error('effect source is not reachable');
  const desktopCard = await page.locator('[data-testid=effect-card]').boundingBox();
  if (!desktopCard || desktopCard.width < 620 || desktopCard.height < 500) throw new Error('desktop hero card is not image-forward');
  await page.screenshot({ path: '/tmp/image-effects-gallery-desktop.png', fullPage: true });
  await page.locator('[data-testid=language-toggle]').click();
  if (!(await page.locator('[data-testid=effect-card]').innerText()).includes('治愈')) throw new Error('language did not switch');
  await page.locator('[data-testid=search-input]').fill('不存在的效果');
  if (await page.locator('[data-testid=effect-card]').count() !== 0) throw new Error('search did not filter');
  await page.locator('[data-testid=search-input]').fill('');
  await page.locator('[data-testid=category-filter]').selectOption('portrait');
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.locator('[data-testid=effect-select]').check();
  await page.locator('[data-testid=copy-selected]').click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  if (!copied.includes('healing-anime-scribble-v3@1.0.0')) throw new Error('copy is not versioned');
  const themes = [];
  for (let index = 0; index < 3; index += 1) {
    themes.push(await page.locator('html').getAttribute('data-theme'));
    await page.locator('[data-testid=theme-toggle]').click();
  }
  if (new Set(themes).size !== 3) throw new Error('system/dark/light theme cycle failed');
  await page.setViewportSize({ width: 390, height: 844 });
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) throw new Error('mobile horizontal overflow');
  for (const testId of ['language-toggle', 'theme-toggle', 'search-input', 'category-filter', 'effect-card']) {
    if (!(await page.locator('[data-testid=' + testId + ']').isVisible())) throw new Error(testId + ' is hidden on mobile');
  }
  const mobileCard = await page.locator('[data-testid=effect-card]').boundingBox();
  if (!mobileCard || mobileCard.width > 390 || mobileCard.width < 340) throw new Error('mobile card width is not responsive');
  const targets = await page.locator('button, input, select, a').evaluateAll(nodes => nodes
    .map(node => node.getBoundingClientRect())
    .filter(box => box.width > 0 && box.height > 0)
    .map(box => ({ width: box.width, height: box.height })));
  if (targets.some(box => box.width < 44 || box.height < 44)) throw new Error('touch target below 44px');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  if ((await page.locator('[data-testid=effect-card]').evaluate(node => getComputedStyle(node).animationDuration)) !== '0s') throw new Error('reduced motion ignored');
  await page.screenshot({ path: '/tmp/image-effects-gallery-mobile.png', fullPage: true });
  if (errors.length) throw new Error('console errors before failure test: ' + errors.join(' | '));
  page.removeAllListeners('console');
  await page.route('**/api/library.json', route => route.abort('internetdisconnected'));
  await page.reload();
  await page.locator('[data-testid=load-error]').waitFor();
  await page.unroute('**/api/library.json');
  const retryErrors = [];
  page.on('console', message => { if (message.type() === 'error') retryErrors.push(message.text()) });
  await page.locator('[data-testid=retry-load]').click();
  await page.locator('[data-testid=effect-card]').waitFor();
  if (retryErrors.length) throw new Error('console errors after retry: ' + retryErrors.join(' | '));
  return 'gallery smoke passed';
}"
playwright-cli -s=image-effects-gallery close
kill "$image_effects_server_pid"
wait "$image_effects_server_pid" || true
trap - EXIT
```

Expected: Node tests PASS；浏览器命令返回 `gallery smoke passed`，覆盖桌面大图卡片、移动无横向溢出与主要控件可见、语言、主题、搜索、分类、选择、复制、安装命令、效果源码、来源许可证、图片解码、懒加载、触控尺寸、减弱动效和错误重试；控制台无错误。用本地图片查看工具检查 `/tmp/image-effects-gallery-desktop.png` 与 `/tmp/image-effects-gallery-mobile.png` 没有裁切、遮挡或明显视觉回归。无论中途成功或失败，必须关闭命名浏览器会话并终止已记录 PID 的服务进程。

- [ ] **Step 5: 提交静态 Gallery**

```bash
git add skills/image-effects/gallery skills/image-effects/tests/gallery-assets.test.mjs
git commit -m "feat: build image effects gallery"
git status --short
```

Expected: 提交只包含 Task 5 声明的 UI 与资源测试文件；除尚未提交的计划文档外工作树无变化。

## Chunk 3：公开导出、发布与安装

### Task 6：公开仓库模板与安全导出器

**Files:**
- Create: `skills/image-effects/assets/public-repo/README.md`
- Create: `skills/image-effects/assets/public-repo/README_CN.md`
- Create: `skills/image-effects/assets/public-repo/LICENSE`
- Create: `skills/image-effects/assets/public-repo/.gitignore`
- Create: `skills/image-effects/assets/public-repo/.github/workflows/pages.yml`
- Create: `skills/image-effects/scripts/export-public-repo.mjs`
- Create: `skills/image-effects/tests/export-public-repo.test.mjs`

- [ ] **Step 1: 写导出器失败测试**

在临时 Git fixture 中覆盖：从 `git show HEAD:path` 导出；脏源失败；调用方不能传 `--source-commit`；`--target` 必须是规范化绝对路径；拒绝目标为文件系统根、用户目录、源仓库根、Skill 源目录或其祖先；首次目标只能为空；现有目标必须有清单、`.git` 且干净；拒绝旧清单里的绝对路径、`..`、空段、重复路径、路径分隔符逃逸和 symlink 逃逸；所有删除目标 `realpath`/父目录解析后必须仍在目标根内；只删除旧清单受管文件；保护未受管文件；原子失败保持目标；清单路径排序与 SHA；`--check` 接受本轮受管变更但拒绝额外漂移；公开内容扫描不含绝对用户路径、附件路径、密钥模式或禁止属性内容。

- [ ] **Step 2: 运行测试确认红灯**

Run: `node --test skills/image-effects/tests/export-public-repo.test.mjs`

Expected: FAIL，因为导出器不存在。

- [ ] **Step 3: 实现公开模板与导出器**

README 提供 `npx skills add wangjs-jacky/image-effects`、版本化调用示例、Gallery 链接、效果贡献契约和许可边界。Pages workflow 同时支持 `push` 与 `workflow_dispatch`，用 `actions/configure-pages`、`actions/upload-pages-artifact` 和 `actions/deploy-pages` 发布 `gallery/`。导出器只允许设计稿白名单，并把 `assets/public-repo/` 映射到公开根；所有目标验证和旧清单路径约束在任何创建、删除或替换动作之前完成，且不跟随目标内 symlink 写出根目录。

- [ ] **Step 4: 运行测试并提交**

```bash
node --test skills/image-effects/tests/export-public-repo.test.mjs
git add skills/image-effects
git commit -m "feat: add safe public repository export"
```

Expected: PASS，且源工作树在提交后干净。

### Task 7：源仓库集成、全量验证与合并

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `.claude-plugin/marketplace.json`
- Create: `plugins/image-effects/.claude-plugin/plugin.json`
- Create shared-content link: `plugins/image-effects/skills/image-effects`

- [ ] **Step 1: 按仓库既有 standalone Skill 模式集成**

先检查一个现有 standalone Skill 的 marketplace、双语 README、plugin manifest 和共享内容链接，再以相同结构注册 `image-effects`。共享 Skill 内容必须链接 `skills/image-effects`，不得复制出第二份事实源；只修改 Files 清单中的集成文件。

- [ ] **Step 2: 先验证集成行为，再提交集成改动**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
git add README.md README_CN.md .claude-plugin/marketplace.json plugins/image-effects
git commit -m "feat: register image effects skill"
```

Expected: 仓库集成门通过；提交只包含 Task 7 集成文件。

- [ ] **Step 3: 在最终源提交上运行全部发布门**

```bash
npm ci --prefix skills/image-effects
python3 /Users/jiashengwang/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/image-effects
node --test skills/image-effects/tests/*.test.mjs
node skills/image-effects/scripts/validate-effects.mjs --online
SOURCE_DATE_EPOCH=1786809600 node skills/image-effects/scripts/build-gallery.mjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
git diff --exit-code
git status --porcelain --untracked-files=all
```

Expected: 全部 PASS；最后两个命令无输出，证明 tracked、staged、unstaged 和 untracked 均干净。

- [ ] **Step 4: 推送分支、等待 CI 并执行已授权合并**

```bash
git push -u origin image-effects
image_effects_pr_url=$(gh pr create --base main --head image-effects --title "feat: add image effects skill and gallery" --body "Adds one versioned image effect, deterministic validation/build tooling, a static gallery, and a safe public-repository exporter. Validated locally with Skill, Node, repository audit, shell, and plugin gates.")
gh pr checks "$image_effects_pr_url" --watch --fail-fast
gh pr merge "$image_effects_pr_url" --squash
image_effects_merge_sha=$(gh pr view "$image_effects_pr_url" --json mergeCommit --jq .mergeCommit.oid)
git fetch origin main
git checkout --detach "$image_effects_merge_sha"
git rev-parse HEAD
git rev-parse origin/main
git status --porcelain --untracked-files=all
```

Expected: PR checks 成功、PR 已合并；`HEAD`、记录的 merge SHA 和 `origin/main` 三者一致；当前事实源工作树完全干净。若 CI 或仓库规则阻止合并，保留 PR 并停止公开导出，不绕过保护。

- [ ] **Step 5: 安全快进常用 main checkout**

```bash
git -C ../jacky-skills rev-parse --show-toplevel
git -C ../jacky-skills remote get-url origin
git -C ../jacky-skills branch --show-current
git -C ../jacky-skills rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
git -C ../jacky-skills status --short
git -C ../jacky-skills pull --ff-only origin main
git -C ../jacky-skills status --short
```

Expected: 顶层路径以 `/jacky-skills` 结尾，origin 精确为 `https://github.com/wangjs-jacky/jacky-skills.git`，当前分支为 `main`，upstream 为 `origin/main`。记录 pull 前的无关改动，pull 后逐项仍存在。Git 若因用户改动可能被覆盖而拒绝，则保持原状并报告，不 stash、不 reset。

Expected: 远端 `main` 已含合并提交；常用 checkout 在安全时快进且用户无关改动不丢失。此步骤失败不改变远端事实，但本地安装必须等待一个耐久源路径可用。

### Task 8：从最终 main 导出并首次推送公开仓库

**Files:**
- External generated checkout: absolute sibling path resolved from `../image-effects`
- External remote: `wangjs-jacky/image-effects`

- [ ] **Step 1: 解析绝对目标并完成远端/本地只读预检**

```bash
gh auth status
gh api user --jq .login
public_image_effects_target=$(python3 -c 'from pathlib import Path; print(Path("../image-effects").resolve())')
printf '%s\n' "$public_image_effects_target"
gh api graphql -f query='query { viewer { login } repository(owner: "wangjs-jacky", name: "image-effects") { name isEmpty owner { login } defaultBranchRef { name } } }'
if test -d "$public_image_effects_target/.git"; then
  git -C "$public_image_effects_target" status --porcelain --untracked-files=all
  if git -C "$public_image_effects_target" remote get-url origin >/dev/null 2>&1; then
    test "$(git -C "$public_image_effects_target" remote get-url origin)" = "https://github.com/wangjs-jacky/image-effects.git"
  fi
fi
```

Expected: viewer/login 都是 `wangjs-jacky`；目标是绝对 sibling 路径，不是 home、源仓库或其祖先。GraphQL 的 `repository` 只能为 `null`（不存在）或 `owner.login=wangjs-jacky` 且 `isEmpty=true`；任何已有内容、其他 owner、认证/网络不确定都立即停止。若本地目标非空，只允许它是带 `.git`、有效导出清单且工作树干净的专用仓库；若已有 `origin`，它必须精确等于 `https://github.com/wangjs-jacky/image-effects.git`，未知 remote 立即停止。

- [ ] **Step 2: 从已合并的干净 Git tree 导出并检查**

```bash
public_image_effects_target=$(python3 -c 'from pathlib import Path; print(Path("../image-effects").resolve())')
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test -z "$(git status --porcelain --untracked-files=all)"
node skills/image-effects/scripts/export-public-repo.mjs --target "$public_image_effects_target"
node skills/image-effects/scripts/export-public-repo.mjs --target "$public_image_effects_target" --check
node -e "const fs=require('node:fs'); const manifest=JSON.parse(fs.readFileSync(process.argv[1])); if (manifest.sourceCommit!==process.argv[2]) process.exit(1)" "$public_image_effects_target/.image-effects-export.json" "$(git rev-parse HEAD)"
```

Expected: 目标内容与清单逐文件匹配，`sourceCommit` 等于最终 `origin/main`。发现冲突或漂移时目标保持原状，不继续外部变更。

- [ ] **Step 3: 初始化/复用本地公开 Git 仓库并提交唯一导出结果**

```bash
public_image_effects_target=$(python3 -c 'from pathlib import Path; print(Path("../image-effects").resolve())')
if test ! -d "$public_image_effects_target/.git"; then git -C "$public_image_effects_target" init -b main; fi
node skills/image-effects/scripts/export-public-repo.mjs --target "$public_image_effects_target" --check
git -C "$public_image_effects_target" add --all
git -C "$public_image_effects_target" diff --cached --name-only
git -C "$public_image_effects_target" diff --cached --name-only | rg '^\.image-effects-export\.json$'
git -C "$public_image_effects_target" commit -m "feat: publish image effects skill and gallery"
git -C "$public_image_effects_target" status --porcelain --untracked-files=all
node skills/image-effects/scripts/export-public-repo.mjs --target "$public_image_effects_target" --check
```

Expected: 暂存路径已先被 `--check` 证明全部属于导出结果，清单包含在公开提交中；提交后公开工作树干净，最终 `--check` 仍通过。

- [ ] **Step 4: 重新查询远端状态，验证/配置 origin 后推送**

每次进入此步骤都重新解析目标并查询 GraphQL，不依赖 Step 1 的 Shell 变量：

```bash
public_image_effects_target=$(python3 -c 'from pathlib import Path; print(Path("../image-effects").resolve())')
gh api graphql -f query='query { viewer { login } repository(owner: "wangjs-jacky", name: "image-effects") { name isEmpty owner { login } defaultBranchRef { name } } }'
git -C "$public_image_effects_target" remote -v
```

若最新查询的 `repository` 为 `null`，先创建不带 README 的空远端；本地若尚无 origin 则添加，已有时必须已在 Step 1 验证为精确 HTTPS URL：

```bash
gh repo create image-effects --public --description "Reusable image effect recipes and a static gallery for AI coding agents"
if ! git -C "$public_image_effects_target" remote get-url origin >/dev/null 2>&1; then git -C "$public_image_effects_target" remote add origin https://github.com/wangjs-jacky/image-effects.git; fi
git -C "$public_image_effects_target" push -u origin main
```

若最新查询显示远端已存在但为空且属于当前用户，只验证/添加 origin 后首次推送：

```bash
if ! git -C "$public_image_effects_target" remote get-url origin >/dev/null 2>&1; then git -C "$public_image_effects_target" remote add origin https://github.com/wangjs-jacky/image-effects.git; fi
test "$(git -C "$public_image_effects_target" remote get-url origin)" = "https://github.com/wangjs-jacky/image-effects.git"
git -C "$public_image_effects_target" push -u origin main
```

两种分支之后共同运行：

```bash
gh repo edit wangjs-jacky/image-effects --add-topic agent-skills --add-topic image-generation --add-topic codex
git -C "$public_image_effects_target" status --porcelain --untracked-files=all
git -C "$public_image_effects_target" rev-parse HEAD
```

Expected: 只执行一个远端分支；`main` 首次推送成功且未 force，公开工作树仍干净。任何失败都保留本地提交和已创建远端现状，停止 Pages 配置，不覆盖重试。

### Task 9：Pages、公开安装与最终交付验收

**Files:**
- No source file changes
- External state: GitHub Pages configuration and local global Skill link

- [ ] **Step 1: 设置 Pages 为 Actions source，显式触发并等待精确 workflow**

若 `gh api repos/wangjs-jacky/image-effects/pages` 成功，执行 `PUT`；若明确返回 404，执行 `POST`；其他错误停止：

```bash
gh api --method PUT repos/wangjs-jacky/image-effects/pages -f build_type=workflow
```

或仅在明确未创建时：

```bash
gh api --method POST repos/wangjs-jacky/image-effects/pages -f build_type=workflow
```

启用后显式 dispatch，避免首次 push 早于 Pages 配置；随后在 40 秒内轮询 GitHub 登记的、属于精确公开提交的 `workflow_dispatch` run，再等待结果：

```bash
public_image_effects_target=$(python3 -c 'from pathlib import Path; print(Path("../image-effects").resolve())')
image_effects_public_sha=$(git -C "$public_image_effects_target" rev-parse HEAD)
gh workflow run pages.yml --repo wangjs-jacky/image-effects --ref main
image_effects_pages_run=''
for image_effects_attempt in {1..20}; do
  image_effects_pages_run=$(gh run list --repo wangjs-jacky/image-effects --workflow pages.yml --event workflow_dispatch --branch main --commit "$image_effects_public_sha" --limit 1 --json databaseId --jq '.[0].databaseId // empty')
  if test -n "$image_effects_pages_run"; then break; fi
  sleep 2
done
test -n "$image_effects_pages_run"
gh run watch "$image_effects_pages_run" --repo wangjs-jacky/image-effects --exit-status
gh api repos/wangjs-jacky/image-effects/pages
```

Expected: `build_type=workflow`，精确公开提交的 Pages run 成功，API 返回公开 `html_url`。

- [ ] **Step 2: 验证 Pages 全部公开资源与仓库完整性**

```bash
curl --fail --location --retry 30 --retry-all-errors --retry-delay 2 https://wangjs-jacky.github.io/image-effects/ >/dev/null
curl --fail --location --retry 30 --retry-all-errors --retry-delay 2 https://wangjs-jacky.github.io/image-effects/api/library.json >/dev/null
curl --fail --location --retry 30 --retry-all-errors --retry-delay 2 'https://wangjs-jacky.github.io/image-effects/media/healing-anime-scribble-v3@1.0.0.jpg' >/dev/null
curl --fail --location --retry 30 --retry-all-errors --retry-delay 2 'https://wangjs-jacky.github.io/image-effects/source/healing-anime-scribble-v3@1.0.0.md' >/dev/null
gh api repos/wangjs-jacky/image-effects/contents/SKILL.md --jq .sha
gh api repos/wangjs-jacky/image-effects/contents/.image-effects-export.json --jq .sha
npx skills add wangjs-jacky/image-effects --list
```

Expected: 四个 Pages URL 都返回 2xx；公开 Skill 与导出清单可读；社区安装器列出 `image-effects`。

- [ ] **Step 3: 从耐久 jacky-skills main 路径链接并安装**

仅在 Task 7 Step 5 已安全快进后运行：

```bash
j-skills link ../jacky-skills/skills/image-effects
j-skills install image-effects -g
j-skills list -g
```

Expected: 全局列表存在 `image-effects`，链接指向常用 `jacky-skills` checkout，不指向临时 worktree 或公开导出副本。

- [ ] **Step 4: 完成最终审查与交付记录**

记录并相互核对：源 PR URL、源合并提交、导出清单 `sourceCommit`、公开仓库提交、Pages workflow run、Pages URL、四个 HTTP 验收、公开安装发现、全局链接状态和全部本地验证门。明确首版只有 `healing-anime-scribble-v3@1.0.0`；说明新增效果只需追加符合契约的效果卡与预览并重建，不声称其余 8 个效果已迁移。

Expected: 交付记录中的源合并提交等于导出 `sourceCommit`，公开提交包含该清单，Pages 与安装发现均来自同一公开提交；没有遗漏失败或未完成项。
