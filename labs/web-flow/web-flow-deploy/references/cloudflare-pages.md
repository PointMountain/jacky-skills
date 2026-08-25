# Cloudflare Pages Provider

> 仅当主部署 Skill 已确认 G3、用户授权和当前 preflight 条件时使用。不要把这里的供应者命令复制回 provider-neutral 入口。

## 前置条件

- Node.js 可用；优先使用项目锁定的 CLI 版本。
- 用户已登录正确账号，并明确目标项目名和生产分支。
- sourceDir 的构建产物已完成，build hash 与 G3 artifact 一致。

## Preflight

```bash
npx wrangler whoami
npx wrangler pages project list
```

记录命令类别、退出码、账号/项目是否匹配和检查时间；不要复制 token、认证头、用户目录或私有 endpoint。项目不存在时只返回 needs-project-create，等 publish 再按授权创建。

## Publish

发布前重复 whoami 和项目查询。项目缺失且已获创建授权时：

```bash
npx wrangler pages project create <project-name> \
  --production-branch <branch>
```

发布已构建目录：

```bash
npx wrangler pages deploy <build-directory> \
  --project-name <project-name> \
  --branch <branch>
```

只把公开 HTTPS URL 和脱敏后的命令结果写入 deployment evidence。

## 验活

1. 请求生产 URL，记录 HTTP 状态与关键资源结果。
2. 用真实浏览器打开桌面和移动视图。
3. 检查 console 是否存在阻断错误。
4. 对比线上页面与 G3 build hash 所代表的 preview。

任一事实门失败都保留本地 preview，返回 deploy blocked；不要反复发布来掩盖未定位问题。
