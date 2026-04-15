# 手动发布 VSCode 扩展

适合首次发布、偶尔发布的场景。通过 `vsce` CLI 手动完成整个流程。

## 前置条件

- Node.js >= 16
- VSCode 扩展项目（含 `package.json`）
- [VSCode Marketplace](https://marketplace.visualstudio.com/) 账号（微软/GitHub 账号即可登录）

## 步骤

### 1. 注册 Publisher

首次发布必须先注册 Publisher ID：

1. 访问 [marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage)
2. 使用微软或 GitHub 账号登录
3. 点击 **Create Publisher**
4. 填写 Publisher ID（唯一标识，如 `jackywjs`）

> Publisher ID 将出现在扩展的 Marketplace URL 中：`https://marketplace.visualstudio.com/publisher/<Publisher ID>`

### 2. 创建 Personal Access Token (PAT)

VSCode Marketplace 使用 Azure DevOps PAT 进行认证：

1. 访问 [dev.azure.com](https://dev.azure.com)
2. 点击右上角头像 → **Personal access tokens** → **New Token**
3. 填写配置：

| 配置项 | 推荐值 |
|--------|--------|
| Name | `vsce-publish` |
| Organization | **All accessible organizations** |
| Expiration | 自定义（如 90 天） |
| Scopes | **Custom defined** |
| Marketplace | **Manage** |

4. 点击 **Create**，**立即复制 token**（只显示一次）

> **关键**：PAT 必须勾选 **Marketplace > Manage** 权限，否则发布会报 401/403。

### 3. 安装 vsce

```bash
npm install -g @vscode/vsce
```

### 4. 登录 Publisher

```bash
vsce login <publisher-id>
# 粘贴刚才复制的 PAT
```

登录成功后会显示：
```
The Personal Access Token has been stored in /Users/<user>/.vsce
```

### 5. 检查项目配置

```bash
# 确认关键字段
node -p "JSON.stringify({name: require('./package.json').name, version: require('./package.json').version, publisher: require('./package.json').publisher, engines: require('./package.json').engines}, null, 2)"
```

确认以下字段存在且正确：
- `name`：扩展标识名
- `version`：语义化版本号
- `publisher`：与注册的 Publisher ID 一致
- `engines.vscode`：支持的 VSCode 版本

### 6. 配置 .vscodeignore（重要）

创建 `.vscodeignore` 控制打包内容，避免包含源码和开发文件：

```
.vscode/**
.vscode-test/**
out/**
node_modules/**
src/**
.gitignore
webpack.config.js
vsc-extension-quickstart.md
**/tsconfig.json
**/.eslintrc.json
**/*.map
**/*.ts
**/.vscode-test.*
```

> **原则**：只保留运行时需要的文件（`dist/`、`package.json`、`README.md`、`CHANGELOG.md`、icon 等）。
> 打包前可用 `npx vsce package --dry-run` 预览将包含哪些文件。

### 7. 打包测试

```bash
# 打包为 .vsix 文件
npx vsce package

# 本地安装测试
code --install-extension <name>-<version>.vsix
```

在本地 VSCode 中验证扩展功能正常。

### 8. 发布

```bash
# 方式 1：直接发布（推荐）
npx vsce publish

# 方式 2：发布指定 vsix 文件
npx vsce publish --packagePath <name>-<version>.vsix

# 方式 3：发布同时升版本
npx vsce publish patch  # 自动修改版本 → git commit → git tag → 发布
```

### 9. 推送 tag（如使用 vsce publish patch）

```bash
git push origin main --tags
```

### 10. 验证发布

```bash
# 访问 Marketplace 页面
# https://marketplace.visualstudio.com/items?itemName=<publisher>.<name>

# 或在 VSCode 中搜索
# 打开 VSCode → Extensions → 搜索扩展名
```

发布后通常需要 1-5 分钟才能在 Marketplace 搜索到。

## 完整命令（复制粘贴）

```bash
# 首次配置（只需一次）
npm install -g @vscode/vsce
vsce login <publisher-id>

# 每次发布
npx vsce package                        # 打包
code --install-extension *.vsix         # 本地测试
npx vsce publish                        # 发布
```

## 常见问题

**Q: `vsce login` 后在哪里存储 PAT？**

存储在 `~/.vsce` 文件中。PAT 过期后需要重新登录。

**Q: 每次 `vsce publish` 都要输入 PAT？**

不需要。`vsce login` 只需一次，后续 `vsce publish` 自动读取 `~/.vsce` 中的 token。

**Q: 发布后多久可以在 Marketplace 搜到？**

通常 1-5 分钟，CDN 缓存刷新需要时间。可以通过直接链接访问：
`https://marketplace.visualstudio.com/items?itemName=<publisher>.<name>`

**Q: 如何更新已发布的扩展？**

修改 `package.json` 中的 `version` 字段（必须比已发布版本高），然后重新 `npx vsce publish`。

**Q: 可以撤销已发布的版本吗？**

可以。访问 [Publisher 管理页面](https://marketplace.visualstudio.com/manage)，找到对应扩展，点击 **Unpublish** 或删除特定版本。但建议尽量避免撤销，而是发布新版本修复。
