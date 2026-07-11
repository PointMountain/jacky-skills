# 项目生成模板与输出规范

> Phase 3 生成项目结构、采集/处理脚本、测试和输出文件时必须读取。

## 目录

- [项目结构与生成步骤](#phase-3-项目生成)
- [输出格式规范](#输出格式规范)
- [process.mjs 模板](#processmjs-模板)

### Phase 3: 项目生成

**目标**：生成完整的项目文件

**步骤**：
1. 生成项目目录结构
2. 生成采集函数（`scripts/collect.mjs`）
3. 生成测试用例（`scripts/__tests__/collect.test.mjs`）
4. 运行测试验证
5. 测试通过后生成 Workflow

**生成的项目结构**：

```
<project-name>/
├── .github/
│   └── workflows/
│       └── collect.yml      # GitHub Actions Workflow
├── scripts/
│   ├── collect.mjs          # 数据采集（Node.js ESM）
│   ├── process.mjs          # 数据处理（AI 分析）
│   ├── test-api.mjs         # API 连通性测试脚本
│   ├── verify-workflow.mjs  # Workflow 验证脚本
│   └── __tests__/
│       ├── collect.test.mjs # 采集测试
│       └── process.test.mjs # 处理测试
├── trending/                # AI 分析报告（不是 skills/）
│   └── <owner>-<repo>/
│       └── README.md        # 不是 SKILL.md
├── output/                  # 原始数据（JSON）
│   └── trending.json
├── .ai-prompt.txt           # 用户确认的 Prompt
├── README.md
├── package.json
├── .env                     # 真实的环境变量
└── .gitignore
```

### 输出格式规范

**文件夹结构**：
```
trending/
├── <owner>-<repo>/
│   └── README.md
```

**命名规则**：
- 文件夹名：`<owner>-<repo>`（将 `/` 替换为 `-`）
- 文件名：`README.md`（不是 SKILL.md）

**YAML Frontmatter 格式**：
```yaml
---
name: {repo.name}
full_name: {repo.full_name}
owner: {repo.owner}
url: {repo.url}
language: {repo.language}
stars: {repo.stars}
forks: {repo.forks}
today_stars: {repo.today_stars}
rank: {repo.rank}
date: {YYYY-MM-DD}
text: |
  {AI 生成的分析内容}
  - 每行缩进 2 个空格
  - 不要包含 ```markdown 代码块标记
  - 直接是纯文本内容
---
```

**正文格式**：
```markdown
# {repo.full_name}

{repo.description}

{AI 分析内容（与 text 字段相同）}

---

> 采集时间: {date} | 排名: #{rank} | 今日新增: {today_stars} ⭐
```

**重要约束**：
1. `text` 字段不要包含代码块标记（` ```markdown ` 或 ` ``` `）
2. AI 分析内容直接输出，不要有"AI 分析"之类的标题
3. 元数据全部放在 YAML frontmatter 中

**TDD 流程**：
1. 先生成 `collect.mjs` 函数
2. 生成 `collect.test.mjs` 测试用例
3. 运行 `node --test` 验证
4. 测试通过后继续

### process.mjs 模板

**数据处理脚本**（调用 AI 生成仓库分析报告）：

```javascript
#!/usr/bin/env node

/**
 * 数据处理脚本：调用 AI 生成仓库分析报告
 */

import 'dotenv/config';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const AI_PROVIDER = process.env.AI_PROVIDER || 'qwen';
const QWEN_API_KEY = process.env.QWEN_API_KEY;
const QWEN_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions';

if (!QWEN_API_KEY) {
  console.error('❌ 错误：未找到 QWEN_API_KEY 环境变量');
  process.exit(1);
}

// 确保 trending 目录存在
if (!existsSync('trending')) {
  mkdirSync('trending', { recursive: true });
  console.log('📁 Created trending directory');
}

// 读取采集的数据
const trendingData = JSON.parse(readFileSync('output/trending.json', 'utf-8'));
console.log(`📊 Processing ${trendingData.repos.length} repos with ${AI_PROVIDER} AI...`);

/**
 * 调用 AI API 生成仓库分析
 */
async function analyzeRepo(repo, aiPrompt) {
  // 使用用户确认的 Prompt，或使用默认 Prompt
  const prompt = aiPrompt || `你是一个 GitHub 项目分析专家。请分析以下 GitHub 仓库并生成简洁的分析报告。

## 仓库信息

- **名称**: ${repo.full_name}
- **描述**: ${repo.description || '暂无描述'}
- **语言**: ${repo.language}
- **星标数**: ${repo.stars.toLocaleString()}
- **今日新增**: ${(repo.today_stars || 0).toLocaleString()} stars

## 分析要求

请从以下维度进行分析（直接输出内容，不要代码块标记）：

1. **项目定位**（50-100字）- 这个项目是做什么的？解决什么问题？

2. **核心功能**（3-5 个要点）

3. **技术特点**（50-100字）

4. **适用场景**（3-5 个场景）

5. **推荐理由**（50-100字）

请用 Markdown 格式输出，简洁明了，直接开始内容，不要使用代码块标记。`;

  const response = await fetch(QWEN_API_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${QWEN_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'qwen-turbo',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 1000,
      temperature: 0.7
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`AI API error: ${response.status} - ${errorText}`);
  }

  const data = await response.json();
  return data.choices[0].message.content;
}

/**
 * 生成 Markdown 文件
 */
function generateMarkdown(repo, analysis) {
  const date = new Date().toISOString().split('T')[0];

  // 清理分析文本（移除代码块标记）
  const cleanAnalysis = analysis
    .replace(/```markdown\n?/gi, '')
    .replace(/```\n?/g, '')
    .trim();

  return `---
name: ${repo.name}
full_name: ${repo.full_name}
owner: ${repo.owner}
url: ${repo.url}
language: ${repo.language}
stars: ${repo.stars}
forks: ${repo.forks}
today_stars: ${repo.today_stars || 0}
rank: ${repo.rank}
date: ${date}
text: |
${cleanAnalysis.split('\n').map(line => '  ' + line).join('\n')}
---

# ${repo.full_name}

${repo.description || '暂无描述'}

${cleanAnalysis}

---

> 采集时间: ${date} | 排名: #${repo.rank} | 今日新增: ${(repo.today_stars || 0).toLocaleString()} ⭐
`;
}

// 读取用户确认的 Prompt（如果存在）
let aiPrompt = null;
try {
  const promptFile = readFileSync('.ai-prompt.txt', 'utf-8');
  aiPrompt = promptFile.trim();
  console.log('📝 使用用户确认的 Prompt');
} catch {
  console.log('📝 使用默认 Prompt');
}

// 处理每个仓库
const results = [];
for (let i = 0; i < trendingData.repos.length; i++) {
  const repo = trendingData.repos[i];
  const dirName = repo.full_name.replace('/', '-');
  const trendingDir = join('trending', dirName);

  console.log(`\n[${i + 1}/${trendingData.repos.length}] 处理 ${repo.full_name}...`);

  try {
    if (!existsSync(trendingDir)) {
      mkdirSync(trendingDir, { recursive: true });
    }

    console.log(`   🤖 调用 AI 分析...`);
    const analysis = await analyzeRepo(repo, aiPrompt);
    const markdown = generateMarkdown(repo, analysis);
    writeFileSync(join(trendingDir, 'README.md'), markdown);

    console.log(`   ✅ 完成`);
    results.push({ repo: repo.full_name, status: 'success' });

    // 避免 API 限流
    if (i < trendingData.repos.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  } catch (error) {
    console.error(`   ❌ 失败: ${error.message}`);
    results.push({ repo: repo.full_name, status: 'failed', error: error.message });
  }
}

console.log(`\n📊 处理完成！成功: ${results.filter(r => r.status === 'success').length}, 失败: ${results.filter(r => r.status === 'failed').length}`);
```

**Checkpoint**：项目生成并测试通过

---


