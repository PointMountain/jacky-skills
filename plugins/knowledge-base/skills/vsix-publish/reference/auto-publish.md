# 自动化发布配置（推荐）

通过 GitHub Actions + PAT 实现自动发布，tag 推送后自动打包发布到 VSCode Marketplace。

## 支持的平台

| 平台 | 工具 | Secret 名称 |
|------|------|-------------|
| VSCode Marketplace | `vsce` | `VSCE_PAT` |
| Open VSX Registry | `ovsx` | `OVSX_PAT` |

## 配置步骤

### Step 1：创建 Personal Access Token

如果已有有效的 PAT 可跳过此步。

1. 访问 [dev.azure.com](https://dev.azure.com) → 头像 → **Personal access tokens** → **New Token**
2. 配置：

| 配置项 | 推荐值 |
|--------|--------|
| Name | `github-actions-publish` |
| Organization | **All accessible organizations** |
| Expiration | 自定义（如 180 天或 1 年） |
| Scopes | **Custom defined** |
| Marketplace | **Manage** |

3. 复制 token（只显示一次）

### Step 2：配置 GitHub Secrets

PAT 来源优先级：
1. **CLAUDE.md 配置变量**（`VSCE_PAT` / `OVSX_PAT`）— 直接读取使用
2. **手动输入** — 通过引导获取

```bash
# 从 CLAUDE.md 读取或手动输入 PAT
# VSCE_PAT 来自 Azure DevOps: https://dev.azure.com → Personal access tokens
# OVSX_PAT 来自 Open VSX: https://open-vsx.org → Settings → Access Tokens

# 设置 VSCode Marketplace PAT
gh secret set VSCE_PAT --body "$VSCE_PAT"

# 设置 Open VSX Registry PAT
gh secret set OVSX_PAT --body "$OVSX_PAT"
```

### Step 3：创建 GitHub Actions 工作流

创建 `.github/workflows/release.yml`：

#### 使用 npm 的项目

```yaml
name: Release Extension

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: read

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write  # 用于 OIDC 发布到 Open VSX
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Build extension
        run: npm run build

      - name: Publish to VSCode Marketplace
        run: npx vsce publish
        env:
          VSCE_PAT: ${{ secrets.VSCE_PAT }}

      - name: Publish to Open VSX Registry
        run: npx ovsx publish --no-dependencies
        env:
          OVSX_PAT: ${{ secrets.OVSX_PAT }}

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            *.vsix
          generate_release_notes: true
```

#### 使用 pnpm 的项目（推荐）

```yaml
name: Release Extension

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: read

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - run: pnpm install

      - name: Run tests
        run: pnpm test
        continue-on-error: true

      - name: Build extension
        run: pnpm run build

      - name: Publish to VSCode Marketplace
        run: pnpm run publish:vsce
        env:
          VSCE_PAT: ${{ secrets.VSCE_PAT }}

      - name: Publish to Open VSX Registry
        run: pnpm run publish:ovsx
        env:
          OVSX_PAT: ${{ secrets.OVSX_PAT }}

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            *.vsix
          generate_release_notes: true
```

> **关键点**：
> - `id-token: write` 权限用于 Open VSX 的 OIDC 认证
> - `softprops/action-gh-release@v2` 自动生成 release notes，比 `gh release create` 更优雅
> - `continue-on-error: true` 让测试失败不阻塞发布（按需调整）
> - pnpm 工作流使用 `pnpm/action-setup@v4` 安装 pnpm

### Step 4：提交工作流

```bash
git add .github/workflows/vsix-publish.yml
git commit -m "ci: 添加 VSIX 自动发布工作流"
git push origin main
```

### Step 5：触发发布

```bash
# 修改 package.json 版本号
npm version patch  # 1.0.0 → 1.0.1

# 推送 tag 触发自动发布
git push origin main --tags
```

推送 tag 后 GitHub Actions 自动执行：打包 → 发布到 Marketplace → 创建 GitHub Release。

## 配置完成后的一键发布

```bash
# 修改版本 + 推送 tag = 自动发布
npm version patch && git push origin main --tags
```

## Open VSX Registry 配置（可选）

如果需要同时发布到 Open VSX Registry（供 VSCodium 等使用）：

1. 访问 [open-vsx.org](https://open-vsx.org/)
2. 使用 GitHub 账号登录
3. 进入 **Settings** → **Access Tokens** → **Create Token**
4. 将 token 配置为 GitHub Secret `OVSX_PAT`
5. 取消工作流中 Open VSX 步骤的注释

## 安全注意事项

| 事项 | 说明 |
|------|------|
| **不要提交 PAT 到 Git** | PAT 只存 GitHub Secrets |
| **定期轮换 PAT** | Azure PAT 支持设过期时间，到期重新生成 |
| **最小权限原则** | PAT 只勾选 Marketplace > Manage 权限 |
| **Open VSX token 保护** | 与 VSCE PAT 分开管理，独立轮换 |

## 故障排查

| 问题 | 检查 |
|------|------|
| `Unauthorized (401)` | PAT 过期或无效，重新生成并更新 Secret |
| `Forbidden (403)` | PAT 权限不足，确认勾选了 Marketplace > Manage |
| `Extension not found` | Publisher ID 不匹配，检查 package.json 的 publisher 字段 |
| `Version already exists` | 版本号已发布，必须升版本 |
| `Missing publisher` | package.json 缺少 publisher 字段 |
| GitHub Actions 未触发 | 检查 tag 格式是否为 `v*.*.*`（如 `v1.0.0`） |
| `.vsix` 打包失败 | 检查 package.json 完整性，尝试本地 `npx vsce package` |

## 对比：手动 vs 自动

| 维度 | 手动发布 | 自动发布（CI/CD） |
|------|----------|-------------------|
| 操作复杂度 | 每次手动执行多个命令 | 推送 tag 即触发 |
| 认证方式 | `vsce login` 存本地 | PAT 存 GitHub Secrets |
| 适用场景 | 偶尔发布、个人项目 | 频繁发布、团队协作 |
| 多平台发布 | 需分别执行 | 工作流中并行处理 |
| 回滚能力 | 手动撤销 | 通过重新推送旧 tag 或手动处理 |
