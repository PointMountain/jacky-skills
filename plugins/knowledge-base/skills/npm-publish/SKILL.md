---
name: npm-publish
description: "npm 包发布知识库与自动化指南。当用户需要发布 npm 包、配置 npm 自动化发布、解决 npm publish 2FA/OTP 问题、创建 npm Access Token 时触发。关键词：npm publish、发布 npm 包、npm automation token、npm 2FA。"
---

<role>
你是 npm 发布顾问，帮助用户完成 npm 包的发布流程，从手动发布到自动化发布一站式指导。
</role>

<purpose>
作为 npm 发布的知识库，提供两种发布方式的完整指引：手动发布和自动化发布（绕过 2FA）。
</purpose>

<trigger>
```text
npm publish
发布 npm 包
npm 发布
npm 2FA
npm OTP
npm token
npm automation
发布到 npm
publish to npm
```
</trigger>

---

# npm 发布指南

## 快速判断

先确认用户当前状态：

```bash
# 检查是否已登录
npm whoami 2>&1

# 检查是否有 token 配置
cat ~/.npmrc | grep authToken

# 检查项目类型
cat package.json | grep -E '"name"|"version"|"publishConfig"'
```

根据结果引导用户进入对应流程：
- **未登录 + 无 token** → 引导 [自动化发布配置](#自动化发布配置推荐)
- **已登录但 publish 需要 OTP** → 引导 [自动化发布配置](#自动化发布配置推荐)
- **已配置 automation token** → 直接执行 [发布命令](#发布命令)

---

## Reference

### [手动发布](reference/manual-publish.md)

适合偶尔发布、不想配置 token 的用户。每次 `npm publish` 需要浏览器确认 OTP。

### [自动化发布配置](reference/auto-publish.md)（推荐）

适合需要流水线发布的用户。通过 Granular Access Token 绕过 2FA，一次配置永久使用。

---

## 发布命令

配置好 automation token 后，一键发布：

```bash
# 完整流程：验证 → 升版本 → 发布 → 推送
npm run verify && npm version patch && npm publish && git push origin main --tags
```

分步执行：

```bash
# 1. 验证项目
npm run verify    # 或 npm test

# 2. 升版本
npm version patch  # 1.0.0 → 1.0.1
npm version minor  # 1.0.0 → 1.1.0
npm version major  # 1.0.0 → 2.0.0

# 3. 发布
npm publish

# 4. 推送 tag
git push origin main --tags
```

### Scoped 包注意

名称带 `@org/` 的 scoped 包必须设置：

```json
{
  "publishConfig": {
    "access": "public"
  }
}
```

否则 `npm publish` 默认按私有包处理，免费账号会报 402 错误。

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `E401 Unauthorized` | 未登录或 token 无效 | `npm login` 或检查 `~/.npmrc` token |
| `E403 Forbidden` | 无权限发布该包名 | 检查包名是否已被占用或 scope 权限 |
| `EOTP` | 需要 OTP 验证 | 配置 automation token 或使用 `--otp=验证码` |
| `E402 Payment Required` | scoped 包未设 public | 添加 `publishConfig.access: "public"` |
| `EPUBLISHCONFLICT` | 版本号已存在 | `npm version patch` 升版本后重试 |
| `ENEEDAUTH` | 未认证 | 检查 `~/.npmrc` 中 authToken 是否正确 |

---

## 交互式引导

当用户不确定如何操作时，使用 AskUserQuestion 引导：

### 情况 1：用户从未发布过 npm 包

1. 确认项目有 `package.json` 且包含 `name`、`version`
2. 检查 `publishConfig.access` 是否为 `"public"`（scoped 包）
3. 引导用户选择发布方式（手动 / 自动化）
4. 按所选方式的 reference 执行

### 情况 2：用户遇到 2FA/OTP 问题

1. 解释原因：npm 对发布操作强制要求双因素认证
2. 引导用户前往 npmjs.com 创建 Granular Access Token
3. 帮助配置 `~/.npmrc`
4. 验证 `npm whoami` 通过后执行发布

### 情况 3：用户想配置 CI/CD 自动发布

1. 引导创建 Granular Access Token
2. 将 token 存入 GitHub Secrets (`NPM_TOKEN`)
3. 创建 `.github/workflows/npm-publish.yml`
