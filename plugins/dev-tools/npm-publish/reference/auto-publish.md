# 自动化发布配置（推荐）

通过 Granular Access Token 绕过 2FA，一次配置后 `npm publish` 不再需要浏览器确认。

## 原理

| 方式 | `npm publish` 是否需要 OTP |
|------|---------------------------|
| `npm login` 交互登录 | 每次都需要 |
| **Granular Access Token** | **不需要** |
| Legacy Automation Token | 不需要（但权限不可控） |

Granular Access Token 可以限定包范围和权限，比旧式 Automation Token 更安全。

## 配置步骤

### Step 1：打开 npmjs.com

在浏览器中访问 [npmjs.com](https://www.npmjs.com) 并登录你的账号。

### Step 2：进入 Token 管理页

点击右上角头像 → **Access Tokens**

### Step 3：生成新 Token

1. 点击 **Generate New Token**
2. 选择 **Granular Access Token**（推荐，权限可控）
3. 填写配置：

| 配置项 | 推荐值 |
|--------|--------|
| Token name | `publish-automation` 或项目名 |
| Expiration | 90 天（按需） |
| Packages | **Read and write** |
| Organizations | 选择你的 org（如 `@wangjs-jacky`） |

4. 点击 **Generate Token**
5. **立即复制 token**（只显示一次）

> **关键**：Granular Access Token 默认绕过 2FA/OTP，创建后 `npm publish` 不再需要浏览器确认。

### Step 4：写入本地配置

将 token 写入 `~/.npmrc`：

```bash
# 添加 auth token（只需一次）
echo '//registry.npmjs.org/:_authToken=npm_你的token' >> ~/.npmrc
```

如果已有旧 token，需要替换：

```bash
# 替换旧 token
sed -i '' 's|//registry.npmjs.org/:_authToken=.*|//registry.npmjs.org/:_authToken=npm_你的新token|' ~/.npmrc
```

### Step 5：验证

```bash
npm whoami
# 应显示你的用户名，不再需要浏览器确认
```

## 配置完成后的一键发布

```bash
npm run verify && npm version patch && npm publish && git push origin main --tags
```

## CI/CD 自动发布（GitHub Actions）

将 token 存入 GitHub Secrets 后可实现 tag 触发自动发布。

### 1. 添加 GitHub Secret

仓库 → Settings → Secrets and variables → Actions → **New repository secret**

- Name: `NPM_TOKEN`
- Value: 你的 Granular Access Token

### 2. 创建 Workflow

`.github/workflows/npm-publish.yml`：

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

### 3. 触发发布

```bash
npm version patch
git push origin main --tags
# 自动触发 CI 发布
```

## 安全注意事项

| 事项 | 说明 |
|------|------|
| **不要提交 token 到 Git** | `~/.npmrc` 加入 `.gitignore` |
| **定期轮换 token** | 设置 90 天过期，到期重新生成 |
| **最小权限原则** | Granular Token 限定包范围，不要用全权限 token |
| **CI/CD 用 Secrets** | 不要在 workflow 文件中硬编码 token |

## 故障排查

| 问题 | 检查 |
|------|------|
| `E401 Unauthorized` | token 过期或无效，重新生成 |
| `EOTP` | token 不是 Granular/Automation 类型，需重新创建 |
| `E403` | token 权限不足，检查 Packages 权限是否为 Read and write |
| `E404 Not found` | org 不存在或 token 未关联该 org |

## Token 类型对比

| 类型 | 绕过 2FA | 限定包范围 | 设过期时间 | 推荐场景 |
|------|----------|-----------|-----------|----------|
| **Granular Access Token** | ✅ | ✅ | ✅ | **首选** |
| Legacy Automation | ✅ | ❌ | ❌ | 旧项目兼容 |
| Legacy Publish | ❌ | ❌ | ❌ | 不推荐 |
