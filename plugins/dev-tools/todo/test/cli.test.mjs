import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const cliPath = path.resolve('bin/todo.mjs');

function run(root, args, input) {
  return spawnSync(process.execPath, [cliPath, ...args], {
    cwd: path.dirname(path.dirname(cliPath)),
    env: { ...process.env, AGENT_TASKS_HOME: root },
    input,
    encoding: 'utf8',
  });
}

test('CLI 默认操作全局目录并支持 YAML 统计', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-cli-'));
  const added = run(root, [
    'add',
    'CLI 测试任务',
    '--task-id',
    'TSK-e1f2g3h4',
    '--json',
  ]);
  assert.equal(added.status, 0, added.stderr);
  assert.equal(JSON.parse(added.stdout).task_id, 'TSK-e1f2g3h4');

  const status = run(root, [
    'status',
    'TSK-e1f2g3h4',
    'canDurable',
    '--basis',
    'ai-assessed',
  ]);
  assert.equal(status.status, 0, status.stderr);

  const stats = run(root, ['stats', '--format', 'yaml']);
  assert.equal(stats.status, 0, stats.stderr);
  assert.match(stats.stdout, /canDurable: 1/);

  const section = run(
    root,
    ['section', 'set', 'TSK-e1f2g3h4', '目标'],
    '通过 CLI 修改正文',
  );
  assert.equal(section.status, 0, section.stderr);

  const shown = run(root, [
    'section',
    'show',
    'TSK-e1f2g3h4',
    '目标',
  ]);
  assert.equal(shown.status, 0, shown.stderr);
  assert.equal(shown.stdout.trim(), '通过 CLI 修改正文');
});
