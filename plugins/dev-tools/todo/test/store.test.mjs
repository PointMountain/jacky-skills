import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {
  archiveTask,
  createTask,
  doctor,
  getSection,
  getStats,
  listTasks,
  moveTask,
  readTask,
  rebuildIndexes,
  setTaskStatus,
  updateTask,
  updateTaskSection,
} from '../src/store.mjs';

async function temporaryRoot() {
  return mkdtemp(path.join(tmpdir(), 'agent-todo-'));
}

test('创建、查询、更新状态并生成索引', async () => {
  const root = await temporaryRoot();
  const task = await createTask(root, {
    taskId: 'TSK-a1b2c3d4',
    title: '验证 Markdown Todo',
  });

  assert.equal(task.id, 'TSK-a1b2c3d4');
  assert.equal(task.data.status, 'idea');
  assert.equal((await listTasks(root)).length, 1);

  await assert.rejects(
    setTaskStatus(root, task.id, 'canDurable'),
    /durable_basis/,
  );
  const durable = await setTaskStatus(
    root,
    task.id,
    'canDurable',
    'human-confirmed',
  );
  assert.equal(durable.data.durable_basis, 'human-confirmed');

  const index = await readFile(path.join(root, 'index.md'), 'utf8');
  assert.match(index, /TSK-a1b2c3d4/);
  assert.match(index, /human-confirmed/);

  const renamed = await updateTask(root, task.id, { title: '更新后的标题' });
  assert.equal(renamed.data.title, '更新后的标题');
  assert.match(renamed.body, /^# 更新后的标题$/m);
  await assert.rejects(
    updateTask(root, task.id, { title: '非法\n标题' }),
    /不能包含换行/,
  );
});

test('只替换或追加指定 Markdown 章节', async () => {
  const root = await temporaryRoot();
  const task = await createTask(root, {
    taskId: 'TSK-b1c2d3e4',
    title: '章节测试',
  });

  await updateTaskSection(root, task.id, '想法', '第一版内容', 'set');
  await updateTaskSection(root, task.id, '想法', '第二段内容', 'append');
  await updateTaskSection(root, task.id, '目标', '形成可运行 POC', 'set');

  const updated = await readTask(root, task.id);
  assert.equal(getSection(updated.body, '想法'), '第一版内容\n\n第二段内容');
  assert.equal(getSection(updated.body, '目标'), '形成可运行 POC');
  assert.match(updated.body, /## 下一步/);
});

test('统计、归档和跨目录移动使用同一 Task ID', async () => {
  const source = await temporaryRoot();
  const destination = await temporaryRoot();
  await createTask(source, {
    taskId: 'TSK-c1d2e3f4',
    title: '移动测试',
    status: 'shaping',
  });

  assert.deepEqual(await getStats(source), {
    total: 1,
    idea: 0,
    shaping: 1,
    canDurable: 0,
    doing: 0,
    waitingHuman: 0,
    done: 0,
  });

  const moved = await moveTask(source, destination, 'TSK-c1d2e3f4');
  assert.equal(moved.id, 'TSK-c1d2e3f4');
  assert.equal((await listTasks(source)).length, 0);
  assert.equal((await listTasks(destination)).length, 1);

  const archivedPath = await archiveTask(destination, moved.id);
  assert.equal(path.basename(archivedPath), 'TSK-c1d2e3f4.md');
  assert.equal((await listTasks(destination)).length, 0);
  await assert.rejects(
    createTask(destination, {
      taskId: 'TSK-c1d2e3f4',
      title: '不应复用归档 ID',
    }),
    /Task ID 已存在/,
  );
});

test('doctor 发现文件名不一致与失效本地 Reference', async () => {
  const root = await temporaryRoot();
  const task = await createTask(root, {
    taskId: 'TSK-d1e2f3g4',
    title: 'Doctor 测试',
  });
  await updateTask(root, task.id, {
    references: ['references/not-found.md'],
  });

  const original = await readFile(task.filePath, 'utf8');
  await writeFile(path.join(root, 'tasks', 'wrong-name.md'), original, 'utf8');
  await rebuildIndexes(root);
  await writeFile(path.join(root, 'index.md'), '# Tasks\n', 'utf8');
  const report = await doctor(root);

  assert.ok(report.issues.some((issue) => issue.code === 'missing-reference'));
  assert.ok(report.issues.some((issue) => issue.code === 'filename-mismatch'));
  assert.ok(report.issues.some((issue) => issue.code === 'duplicate-id'));
  assert.ok(report.issues.some((issue) => issue.code === 'stale-index'));
});
