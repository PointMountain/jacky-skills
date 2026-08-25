---
name: github-repo-publish
description: "Use when user wants to publish, sync, push, or update local code repository to GitHub. Also triggers on requests to create remote repo, generate README, set about info, or release packaged artifacts like VSCode extensions (.vsix). Triggers on phrases like \"publish to GitHub\", \"push to remote\", \"sync to GitHub\", \"push to GitHub\", \"update to GitHub\", \"upload to GitHub\", \"帮我同步\", \"推送到 GitHub\", \"同步到 GitHub\", \"更新到 GitHub\", \"上传到 GitHub\", \"create GitHub repo\", or \"release extension\"."
---

<role>
你是 GitHub 仓库发布执行器，负责把本地项目安全、完整地发布到 GitHub，并处理 README、About 与 Release。
</role>

<purpose>
用最少交互完成仓库发布闭环：环境检查、仓库创建/推送、项目信息补齐，以及插件或库的后续发布动作。
</purpose>

<trigger>
```text
publish to GitHub
push to remote
create GitHub repo
release extension
发布到 GitHub
同步到 GitHub
帮我同步一下
sync to GitHub
推送到 GitHub
push to GitHub
更新到 GitHub
上传到 GitHub
npm publish
发布 npm 包
发布到 npm
publish to npm
配置自动发布
setup npm auto publish
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <owner>github-repo-publish</owner>
    <mode>minimal-interaction</mode>
  </gsd:meta>
  <gsd:goal>在可审计前提下完成从本地代码到 GitHub 仓库与可选 Release 的全流程发布。</gsd:goal>
  <gsd:phase id="1" name="preflight">检查远程状态、gh 登录、项目类型与版本条件，确定执行模式。</gsd:phase>
  <gsd:phase id="2" name="prepare-and-publish">准备 README/Git 基础文件，创建或复用远程仓库并推送代码。</gsd:phase>
  <gsd:phase id="3" name="post-publish">设置 About 信息，按项目类型执行 Tauri Release（只上传 dmg）、VSCode Release 或 npm 发布提示，并完成验证。</gsd:phase>
</gsd:workflow>

# GitHub 仓库发布

将本地代码仓库一键发布到 GitHub，自动处理 README、About 信息、Release 发布等。

**核心原则：最小化交互，自动化处理。**

## 前置依赖

- `gh` CLI (GitHub CLI) - `brew install gh`
- 已登录 gh - `gh auth login`
- Git 已初始化（可选，会自动处理）

## 运行模式

**开始时确认模式：**

| 模式 | 行为 |
|------|------|
| `yolo` | 自动推进低风险步骤，仅高危操作确认 |
| `interactive` | 每步确认（默认） |

## 执行流程

### Phase 1: 前置检查

**目标**：确认环境就绪，检测项目类型

**步骤**：

1. **检查远程仓库状态**
   ```bash
   git remote -v
   ```
   - origin 已存在 → 直接进入 Phase 5（推送更新）
   - origin 不存在 → 继续创建流程

2. **验证 gh CLI**
   ```bash
   gh --version && gh auth status
   ```

3. **检测项目类型**
   ```bash
   # Tauri 桌面应用
   [ -f "src-tauri/tauri.conf.json" ] && echo "tauri-app"

   # VSCode 插件
   grep -q '"engines".*"vscode"' package.json && echo "vscode-extension"

   # Node.js 库
   grep -qE '"main"|"module"|"exports"' package.json && echo "nodejs-library"

   # Skills 项目（含 Plugin）
   [ -d "plugins" ] && find plugins -name "plugin.json" | head -1
   ```

**Checkpoint**：gh 已登录且远程仓库状态已确认

### Phase 2: 版本检查（Skills 项目专用）

**目标**：确保 Plugin 版本号正确

**触发条件**：检测到 `plugins/` 目录和 `.claude-plugin/plugin.json`

**步骤**：

1. **识别改动的 Plugin**
   ```bash
   git diff --name-only HEAD | grep "plugins/" | sed 's|plugins/\([^/]*\)/.*|\1|' | sort -u
   ```

2. **分析变更类型并建议版本**
   | 变更类型 | 版本更新 | 示例 |
   |----------|----------|------|
   | 新增/删除 Skill | MINOR | 1.0.0 → 1.1.0 |
   | 修改 Skill | PATCH | 1.0.0 → 1.0.1 |
   | 破坏性变更 | MAJOR | 1.0.0 → 2.0.0 |

3. **更新版本号**（如需要）
   ```bash
   # 使用 jq
   jq '.version = "1.1.0"' plugin.json > tmp.json && mv tmp.json plugin.json

   # 或使用 sed（无 jq）
   sed -i '' 's/"version": "[0-9]\+\.[0-9]\+\.[0-9]\+"/"version": "1.1.0"/' plugin.json
   ```

**Checkpoint**：所有改动 Plugin 的版本号已确认/更新

### Phase 3: 仓库准备

**目标**：生成必要文件，确定仓库名

**步骤**：

1. **确定仓库名**（最多一次交互）
   优先级：用户指定 > package.json name（清理 scope） > 目录名
   ```bash
   # 清理 scope: @org/cool-tool → cool-tool
   CLEANED_NAME=$(echo "$PACKAGE_NAME" | sed 's/^@[\w-]*\//')
   ```

2. **生成 README 文件**（如不存在）
   ```
   project/
   ├── README.md      # 英文版（主文件）
   └── README_CN.md   # 中文版
   ```
   两个文件互相链接，README.md 为 GitHub 默认显示。

3. **初始化 Git**（如需要）
   ```bash
   [ ! -d .git ] && git init && git add . && git commit -m "Initial commit"
   ```

4. **补充 .gitignore**（如需要）
   VSCode 插件需添加 `*.vsix`

**Checkpoint**：仓库名已确认，README 已就绪

### Phase 4: 创建远程仓库

**目标**：创建 GitHub 仓库并推送代码

**步骤**：

1. **创建仓库并推送**
   ```bash
   gh repo create $REPO_NAME --public --source=. --push --description "$DESCRIPTION"
   ```

3. **设置 About 信息**
   ```bash
   # Description 使用中文
   gh repo edit --description "中文描述"

   # Topics 使用英文
   gh repo edit --add-topic "nodejs,typescript,cli-tool"
   ```

4. **清理代理**（如已配置）
   ```bash
   git config --global --unset http.proxy
   git config --global --unset https.proxy
   ```

> **代理注意**：本机可用代理端口与排查细节见同目录 `experience.local.md`（本地私有）。**沙箱/后台 agent 环境会注入连不上外网的 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量，git 自动读取后 push 会 502（CONNECT tunnel failed）——此时「不指定代理」并非直连，而是走了坏代理。** 改用 `git -c http.proxy=<可用代理> -c https.proxy=<可用代理> push ...` 一步到位（端口见 experience.local.md），别反复直连重试。

**Checkpoint**：仓库已创建，代码已推送，About 已设置

### Phase 5: 推送更新（远程已存在时）

**目标**：推送本地更新到已有仓库

**步骤**：
```bash
# push 失败(502 / CONNECT tunnel failed)多半是 env 注入了坏代理被 git 自动读取，详见同目录 experience.local.md
# 沙箱/后台 agent 环境一步到位：git -c http.proxy=<可用代理> -c https.proxy=<可用代理> push origin <branch>
git push origin $(git branch --show-current)
```

### Phase 6: 特殊处理

**目标**：处理项目特定的发布流程

#### Tauri 桌面应用 → Release（只上传 DMG）

> **重要：Tauri 构建产物包含 `.dmg` 和 `.zip`，Release 只上传 `.dmg`，不上传 `.zip`。**

1. **确认构建产物**
   ```bash
   # 检查版本号
   VERSION=$(node -p "require('./src-tauri/tauri.conf.json').version" 2>/dev/null || node -p "require('./package.json').version")

   # 查找 dmg 文件
   find src-tauri/target/release/bundle -name "*.dmg" -type f
   ```

2. **创建 tag 并推送**
   ```bash
   git tag "v$VERSION" && git push origin "v$VERSION"
   ```

3. **创建 Release（只上传 .dmg）**
   ```bash
   # 精确指定 dmg 文件路径，不使用通配符匹配 zip
   DMG_PATH=$(find src-tauri/target/release/bundle -name "*.dmg" -not -name "rw.*" -type f | head -1)

   gh release create "v$VERSION" --title "v$VERSION" --notes "Release v$VERSION" "$DMG_PATH"
   ```

   > **注意**：
   > - 使用 `-not -name "rw.*"` 排除 macOS 临时文件
   > - **禁止上传 `.zip` 文件**，Tauri 构建产出的 zip 只是 dmg 的冗余副本
   > - 如果找到多个 dmg（如多架构），全部上传：`find ... -name "*.dmg" -not -name "rw.*"`

#### VSCode 插件 → Release

```bash
# 打包
npx vsce package

# 创建 tag 并推送
VERSION=$(node -p "require('./package.json').version")
git tag "v$VERSION" && git push origin "v$VERSION"

# 创建 Release
gh release create "v$VERSION" --title "v$VERSION" --notes "Release v$VERSION" "*.vsix"
```

#### Node.js 库 → npm 发布

**Step 1：检查 npm 环境**

```bash
npm whoami 2>/dev/null
```
- 未登录 → 提示用户运行 `npm login`，不自动登录
- 已登录 → 继续

**Step 2：检测自动发布（CI/CD）是否已配置**

```bash
# 检查是否存在 GitHub Actions 发布工作流
ls .github/workflows/npm-publish.yml 2>/dev/null
# 检查 NPM_TOKEN 是否已配置到 GitHub Secrets
gh secret list 2>/dev/null | grep NPM_TOKEN
```

| 状态 | 动作 |
|------|------|
| workflow + NPM_TOKEN 都有 | 自动发布已就绪，跳到 Step 4（仅 tag 触发） |
| 缺少任一项 | 进入 Step 3 引导配置 |

**Step 3：配置自动发布（首次或缺失时）**

当检测到项目未配置自动发布时，使用 `AskUserQuestion` 询问用户：

> "检测到这是一个 npm 包但未配置自动发布。是否现在配置？
> 配置后 `git push --tags` 即可自动触发 npm 发布，无需手动操作。"

如果用户同意，按以下步骤配置：

1. **检查 npm token 类型**（是否支持绕过 2FA）
   ```bash
   # 检查 ~/.npmrc 中的 token
   grep '_authToken' ~/.npmrc | head -1
   ```
   - 无 token → 引导用户创建 Granular Access Token（见下方参考）
   - 有 token → 验证是否可用：`npm whoami`

2. **创建 GitHub Actions 工作流**（如不存在）
   创建 `.github/workflows/npm-publish.yml`：
   ```yaml
   name: npm Publish

   on:
     push:
       tags:
         - 'v*.*.*'

   jobs:
     publish:
       runs-on: ubuntu-latest
       permissions:
         contents: read
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: '20'
             cache: 'npm'
         - run: npm ci
         - run: npm test
         - run: npm publish
           env:
             NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
   ```

3. **配置 NPM_TOKEN Secret**（如未配置）
   ```bash
   # 从 ~/.npmrc 提取 token
   NPM_TOKEN=$(grep '_authToken' ~/.npmrc | head -1 | sed 's/.*_authToken=//')
   gh secret set NPM_TOKEN --body "$NPM_TOKEN"
   ```

4. **提交工作流文件**
   ```bash
   git add .github/workflows/npm-publish.yml
   git commit -m "ci: 添加 npm 自动发布工作流"
   git push origin $(git branch --show-current)
   ```

**Step 4：执行发布**

根据自动发布配置状态选择不同路径：

**路径 A：已配置自动发布（推荐）**
```bash
VERSION=$(node -p "require('./package.json').version")
git tag "v$VERSION" && git push origin "v$VERSION"
# CI 自动执行 npm publish
```

**路径 B：手动发布（未配置或用户跳过）**
```bash
PKG_NAME=$(node -p "require('./package.json').name")
# scoped package（如 @wangjs-jacky/xxx）需要 --access public
echo "$PKG_NAME" | grep -q '^@' && npm publish --access public || npm publish
```

> **注意**：
> - 如果 `package.json` 中有 `prepublishOnly` 脚本，会自动先构建
> - 发布失败时检查：1) 版本号是否已存在 2) npm login 是否过期 3) 网络代理
> - 网络不通时尝试：`npm publish --access public --registry https://registry.npmjs.org/`

---

<details>
<summary>📚 npm Granular Access Token 创建指南（展开查看）</summary>

如果用户没有可用的 npm token，引导以下步骤：

1. 访问 [npmjs.com](https://www.npmjs.com) → 点击头像 → **Access Tokens**
2. 点击 **Generate New Token** → 选择 **Granular Access Token**
3. 填写配置：

| 配置项 | 推荐值 |
|--------|--------|
| Token name | `publish-automation` 或项目名 |
| Expiration | 90 天 |
| Packages | **Read and write** |
| Organizations | 选择对应 org（如 `@wangjs-jacky`） |

4. 复制 token（只显示一次）
5. 写入本地配置：
   ```bash
   echo '//registry.npmjs.org/:_authToken=npm_你的token' >> ~/.npmrc
   npm whoami  # 验证
   ```

**Token 类型对比**：

| 类型 | 绕过 2FA | 限定包范围 | 设过期时间 | 推荐 |
|------|----------|-----------|-----------|------|
| **Granular Access Token** | ✅ | ✅ | ✅ | **首选** |
| Legacy Automation | ✅ | ❌ | ❌ | 旧项目兼容 |

</details>

**Checkpoint**：项目特定发布流程已完成

## 验证

- [ ] 远程仓库可访问：`gh repo view`
- [ ] README 正确显示
- [ ] About 信息（中文描述 + Topics）
- [ ] Tauri 应用：Release 只包含 `.dmg`（无 `.zip`）
- [ ] VSCode 插件：Release 包含 `.vsix`
- [ ] Node.js 库：npm 发布成功，`npm view <pkg>@<version>` 可查

## 快速参考

| 操作 | 命令 |
|------|------|
| 创建仓库 | `gh repo create $NAME --public --source=. --push` |
| 设置描述 | `gh repo edit --description "$中文描述"` |
| Tauri Release | `gh release create $TAG --title "$TITLE" "$DMG_PATH"` |
| VSCode Release | `gh release create $TAG --title "$TITLE" "*.vsix"` |
| npm 发布（scoped） | `npm publish --access public` |
| npm 发布（regular） | `npm publish` |
| 推送更新 | `git push origin <branch>` |

## 错误处理

| 错误 | 解决 |
|------|------|
| `gh: command not found` | `brew install gh` |
| 未登录 gh | `gh auth login` |
| 仓库已存在 | 直接推送更新 |
| 代理连接失败 / push 502 (CONNECT tunnel failed) | env 注入了连不上外网的坏代理、被 git 自动读取所致；用 `git -c http.proxy=<可用代理> -c https.proxy=<可用代理>` 注入可用代理。具体端口见 experience.local.md |
| `.vsix already exists` | 删除旧文件重新打包 |
| npm 403/未登录 | `npm login` |
| npm 版本已存在 | 更新 package.json 版本号后重试 |
| npm 网络超时 | 加 `--registry https://registry.npmjs.org/` 或配代理 |

## 禁止事项

- ❌ 多次交互确认（最多一次）
- ❌ 询问 README（自动生成）
- ❌ 询问 About（自动总结）
- ❌ 合并中英文 README
- ❌ 提交 .vsix 到仓库
- ❌ 远程已存在时报错退出
- ❌ Tauri Release 上传 `.zip` 文件（只上传 `.dmg`）

## Next Up

- [ ] 确认运行模式（yolo/interactive）
- [ ] 可复制命令: `gh repo create <name> --public --source=. --push`
- [ ] 验证: `gh repo view`
