# Workflow 验证与自动修复

> Phase 5 触发、轮询、分析日志与自动修复 GitHub Actions Workflow 时必须读取。

## 目录

- [验证步骤](#phase-5-workflow-验证)
- [状态轮询与日志分析](#phase-5-workflow-验证)
- [最多三次自动修复](#phase-5-workflow-验证)
- [成功输出与状态清理](#phase-5-workflow-验证)

### Phase 5: Workflow 验证

**目标**：自动触发并验证 Workflow 运行状态

**步骤**：
1. 触发 GitHub Workflow
2. 轮询检查运行状态
3. 如果失败，分析错误日志
4. 尝试自动修复（最多 3 次）
5. 多次失败后让用户协助排查

**自动化验证流程**：

```bash
# 1. 触发 Workflow
gh workflow run collect.yml

# 2. 获取最新的 run ID
RUN_ID=$(gh run list --workflow=collect.yml --limit 1 --json | jq -r '.[0].id')

# 3. 轮询检查状态（最多等待 5 分钟）
for i in {1..30}; do
  STATUS=$(gh run view $RUN_ID --json | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    echo "✅ Workflow 运行成功"
    exit 0
  elif [ "$STATUS" = "failed" ]; then
    echo "❌ Workflow 运行失败"
    # 获取错误日志
    gh run view $RUN_ID --log-failed
    exit 1
  fi
  echo "⏳ 等待中... ($i/30)"
  sleep 10
done
```

**错误分析逻辑**：

```javascript
// 分析 Workflow 失败原因
function analyzeFailure(logs) {
  const errorPatterns = [
    {
      pattern: /API key.*invalid/i,
      fix: '检查 GitHub Secrets 中的 API Key 是否正确配置'
    },
    {
      pattern: /permission denied/i,
      fix: '检查 workflow 的 permissions 配置是否正确'
    },
    {
      pattern: /module not found/i,
      fix: '运行 npm install 检查依赖是否完整'
    },
    {
      pattern: /ENOENT.*no such file/i,
      fix: '检查文件路径是否正确，确保所有脚本文件已提交'
    }
  ];

  for (const { pattern, fix } of errorPatterns) {
    if (pattern.test(logs)) {
      return { detected: true, fix };
    }
  }

  return { detected: false, fix: '未知错误，请查看完整日志' };
}
```

**自动修复流程**：

```
修复尝试次数: 0/3

循环:
  1. 分析错误日志
  2. 如果是已知错误:
     - 自动应用修复
     - 提交修复代码
     - 重新触发 Workflow
     - 等待结果
  3. 如果是未知错误或修复失败:
     - 增加尝试次数
  4. 如果达到 3 次:
     - 输出完整错误日志
     - 提供手动排查建议
     - 让用户协助处理
```

**轮询状态脚本** `scripts/verify-workflow.mjs`:

```javascript
#!/usr/bin/env node

import { execSync } from 'child_process';

const WORKFLOW_NAME = process.env.WORKFLOW_NAME || 'collect.yml';
const MAX_ATTEMPTS = 30; // 5 分钟
const RETRY_DELAY = 10000; // 10 秒

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function triggerWorkflow() {
  try {
    console.log(`🚀 触发 Workflow: ${WORKFLOW_NAME}`);
    execSync(`gh workflow run ${WORKFLOW_NAME}`, { stdio: 'inherit' });
    return true;
  } catch (error) {
    console.error('❌ 触发失败:', error.message);
    return false;
  }
}

async function getLatestRunId() {
  const result = execSync(
    `gh run list --workflow=${WORKFLOW_NAME} --limit 1 --json`,
    { encoding: 'utf-8' }
  );
  const runs = JSON.parse(result);
  return runs[0]?.id;
}

async function getRunStatus(runId) {
  const result = execSync(
    `gh run view ${runId} --json`,
    { encoding: 'utf-8' }
  );
  const run = JSON.parse(result);
  return run.status;
}

async function getFailedLogs(runId) {
  try {
    const result = execSync(
      `gh run view ${runId} --log-failed`,
      { encoding: 'utf-8' }
    );
    return result;
  } catch (error) {
    return error.stdout || error.message;
  }
}

async function main() {
  // 1. 触发 Workflow
  const triggered = await triggerWorkflow();
  if (!triggered) {
    process.exit(1);
  }

  // 2. 等待 run 创建
  await sleep(5000);

  // 3. 获取 run ID
  const runId = await getLatestRunId();
  if (!runId) {
    console.error('❌ 无法获取 run ID');
    process.exit(1);
  }

  console.log(`📋 Run ID: ${runId}`);

  // 4. 轮询状态
  for (let i = 1; i <= MAX_ATTEMPTS; i++) {
    const status = await getRunStatus(runId);
    console.log(`⏳ 状态检查 ${i}/${MAX_ATTEMPTS}: ${status}`);

    if (status === 'completed') {
      console.log('✅ Workflow 运行成功！');
      process.exit(0);
    }

    if (status === 'failed') {
      console.log('❌ Workflow 运行失败');
      const logs = await getFailedLogs(runId);
      console.log('\n📜 错误日志:\n');
      console.log(logs);
      process.exit(1);
    }

    await sleep(RETRY_DELAY);
  }

  console.log('⏰ 超时：等待时间过长');
  process.exit(1);
}

main();
```

**Checkpoint**：Workflow 运行成功

---


