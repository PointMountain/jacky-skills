import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { ensureStore, listTasks, readTask } from '../src/store.mjs';
import { createWebServer } from '../src/web-server.mjs';

async function startTestServer(root) {
  await ensureStore(root);
  const server = createWebServer(root);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  return {
    server,
    baseUrl: `http://127.0.0.1:${address.port}`,
  };
}

test('Web 与 CLI 核心共享同一份 Markdown 数据', async (context) => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-web-'));
  const { server, baseUrl } = await startTestServer(root);
  context.after(() => new Promise((resolve) => server.close(resolve)));

  const page = await fetch(baseUrl);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /AGENT CONSOLE/);

  const createdResponse = await fetch(`${baseUrl}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Web 新增任务' }),
  });
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json();
  assert.match(created.task_id, /^TSK-[a-z0-9]{8}$/);
  assert.equal((await listTasks(root)).length, 1);

  const rejectedResponse = await fetch(
    `${baseUrl}/api/tasks/${created.task_id}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: '不应写入的标题',
        status: 'canDurable',
      }),
    },
  );
  assert.equal(rejectedResponse.status, 400);
  assert.equal((await readTask(root, created.task_id)).data.title, 'Web 新增任务');

  const updatedResponse = await fetch(
    `${baseUrl}/api/tasks/${created.task_id}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: 'canDurable',
        durable_basis: 'poc-passed',
        body: '# Web 新增任务\n\n## 目标\n\n验证完整闭环。\n',
      }),
    },
  );
  assert.equal(updatedResponse.status, 200);
  const task = await readTask(root, created.task_id);
  assert.equal(task.data.status, 'canDurable');
  assert.equal(task.data.durable_basis, 'poc-passed');
  assert.match(task.body, /验证完整闭环/);

  const archivedResponse = await fetch(
    `${baseUrl}/api/tasks/${created.task_id}`,
    { method: 'DELETE' },
  );
  assert.equal(archivedResponse.status, 200);
  assert.equal((await listTasks(root)).length, 0);
});

test('Web API 拒绝非法 Task ID 和过大请求体', async (context) => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-web-safe-'));
  const { server, baseUrl } = await startTestServer(root);
  context.after(() => new Promise((resolve) => server.close(resolve)));

  const invalid = await fetch(`${baseUrl}/api/tasks/..%2Fsecret`);
  assert.equal(invalid.status, 400);

  const oversized = await fetch(`${baseUrl}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'x'.repeat(1024 * 1024 + 10) }),
  });
  assert.equal(oversized.status, 400);
});

test('Web API 拒绝非法 Reference 且不会留下损坏任务', async (context) => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-web-ref-'));
  const { server, baseUrl } = await startTestServer(root);
  context.after(() => new Promise((resolve) => server.close(resolve)));

  const response = await fetch(`${baseUrl}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: '非法 Reference',
      references: [{ path: 'references/a.md' }],
    }),
  });

  assert.equal(response.status, 400);
  assert.match((await response.json()).error, /字符串数组/);
  assert.equal((await listTasks(root)).length, 0);
});

test('Web 元信息提示尚未迁移的旧版任务数量', async (context) => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-web-legacy-'));
  await writeFile(
    path.join(root, 'todo.md'),
    '# TODO\n\n## 📋 Todo\n- [ ] 第一条\n- [x] 第二条\n',
    'utf8',
  );
  const { server, baseUrl } = await startTestServer(root);
  context.after(() => new Promise((resolve) => server.close(resolve)));

  const response = await fetch(`${baseUrl}/api/meta`);
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).legacy, {
    found: true,
    planned: 2,
  });
});
