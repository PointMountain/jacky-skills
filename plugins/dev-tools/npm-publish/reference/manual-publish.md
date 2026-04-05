# 手动发布 npm 包

适合偶尔发布的场景。每次 `npm publish` 需要浏览器确认 OTP。

## 前置条件

- Node.js >= 16
- npm 账号（[npmjs.com](https://www.npmjs.com) 注册）

## 步骤

### 1. 登录 npm

```bash
npm login
```

浏览器会自动弹出，点击 **Authorize** 确认。

终端会显示：

```
Logged in as <username> on https://registry.npmjs.org/.
```

### 2. 检查项目配置

```bash
# 确认包名和版本
npm pkg get name version

# scoped 包必须有这个配置（免费账号发布公开包）
# package.json:
# {
#   "publishConfig": { "access": "public" }
# }
```

**Scoped 包注意**：名称带 `@org/` 的包，必须在 `package.json` 中设置 `"publishConfig": { "access": "public" }`，否则报 402 错误。

### 3. 验证项目

```bash
# 运行测试
npm test

# 检查哪些文件会被发布
npm pack --dry-run
```

确认发布内容正确，没有包含敏感文件（`.env`、密钥等）。

### 4. 升版本号

```bash
# 根据改动大小选择
npm version patch  # 修复 bug: 1.0.0 → 1.0.1
npm version minor  # 新功能:   1.0.0 → 1.1.0
npm version major  # 破坏变更: 1.0.0 → 2.0.0
```

此命令会自动创建 git commit 和 tag。

### 5. 发布

```bash
npm publish
```

浏览器会再次弹出要求 OTP 确认，点击 **Authorize** 即可。

如果收到 OTP 短信/验证器码，可以使用：

```bash
npm publish --otp=123456
```

### 6. 推送

```bash
git push origin main --tags
```

### 7. 验证发布

```bash
# 查看包信息
npm info <package-name>

# 或访问 https://www.npmjs.com/package/<package-name>
```

## 完整命令（复制粘贴）

```bash
npm login
npm test
npm version patch
npm publish
git push origin main --tags
```

## 常见问题

**Q: `npm login` 后浏览器没弹出？**

检查默认浏览器是否正常，或手动访问终端中打印的 URL。

**Q: 每次都要确认 OTP 太烦？**

参考 [自动化发布配置](auto-publish.md)，一次配置后不再需要。

**Q: 发布后多久可以在 npm 上搜到？**

通常 1-5 分钟，刷新 CDN 缓存需要时间。
