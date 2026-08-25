# 可复用配置、故障排查与完整示例

> 需要生成 Workflow/README 模板、排查常见错误或参考完整 Trending 采集器案例时读取。

## 目录

- [复用的配置](#复用的配置来自-trending-skills)
- [模板文件](#模板文件)
- [验证](#验证)
- [Next Up](#next-up)
- [故障排查](#故障排查)
- [完整示例](#示例使用本-skill-创建-github-trending-采集器)

## 复用的配置（来自 trending-skills）

### Workflow 模板

```yaml
name: Collect Data

on:
  workflow_dispatch:
    inputs: {}
  schedule:
    - cron: '{{CRON_SCHEDULE}}'  # 用户配置

permissions:
  contents: write

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'

      - name: Install dependencies
        run: npm install

      - name: Collect data
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          {{#AI_ENABLED}}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          {{/AI_ENABLED}}
        run: node scripts/collect.mjs

      - name: Process data
        if: success()
        run: node scripts/process.mjs

      - name: Commit and push
        run: |
          git config user.name "bot"
          git config user.email "bot@users.noreply.github.com"
          git add -A
          git diff --staged --quiet && exit 0
          git commit -m "chore: update data $(date +%Y-%m-%d)"
          git push
```

---

## 模板文件

详细的模板文件存放在 `templates/` 目录：

| 文件 | 用途 |
|------|------|
| `workflow.yml.tmpl` | GitHub Actions Workflow 模板 |
| `collect.mjs.tmpl` | 采集脚本模板 |
| `process.mjs.tmpl` | 处理脚本模板 |
| `test.mjs.tmpl` | 测试用例模板 |
| `README.md.tmpl` | README 模板 |
| `package.json.tmpl` | package.json 模板 |

---

## 验证

项目生成完成后，验证以下内容：

- [ ] Workflow 语法正确（`actionlint` 或手动检查）
- [ ] 测试用例通过（`node --test`）
- [ ] README 包含完整使用说明
- [ ] .env 文件已创建并包含有效的 API Key
- [ ] .env.example 包含所有必需变量（不含真实值）
- [ ] API 连通性测试通过（`node scripts/test-api.mjs`）
- [ ] Git 仓库已创建
- [ ] GitHub Secrets 已配置
- [ ] 代码已推送到 GitHub
- [ ] Workflow 自动运行成功（通过 `scripts/verify-workflow.mjs`）

---

## Next Up

- [ ] 自定义采集逻辑: 编辑 `scripts/collect.mjs`
- [ ] 添加更多数据源: 扩展 `collect.mjs`
- [ ] 修改采集频率: 编辑 `.github/workflows/collect.yml` 中的 cron 表达式

## 故障排查

如果 Workflow 运行失败，检查以下内容：

### 常见错误

| 错误类型 | 可能原因 | 解决方案 |
|----------|----------|----------|
| `API key invalid` | API Key 配置错误 | 重新运行 `node scripts/test-api.mjs` 验证 Key |
| `permission denied` | GitHub Token 权限不足 | 检查 workflow 的 `permissions` 配置 |
| `module not found` | 依赖未安装 | 在 workflow 中添加 `npm ci` 步骤 |
| `ENOENT no such file` | 文件未提交到 Git | 确保 `.gitignore` 没有排除必要文件 |

### 手动触发 Workflow

```bash
# 手动触发
gh workflow run collect.yml

# 查看运行日志
gh run watch

# 查看失败的日志
gh run view <run-id> --log-failed
```

---

## 示例：使用本 Skill 创建 GitHub Trending 采集器

```
用户: /gh-workflow-generator

Skill: 你想监控什么数据源？
用户: GitHub Trending 仓库

Skill: 采集频率？
用户: 每 30 分钟

Skill: 是否需要 AI 处理？
用户: 是，使用 OpenAI

Skill: [展示生成的 Prompt]
用户: 确认

Skill: [生成项目文件...]
Skill: [运行测试...]
Skill: [创建仓库并推送...]

Skill: 完成！ 仓库地址: https://github.com/user/github-trending-collector
```

