import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { migrateLegacy } from '../src/migrate.mjs';
import { listTasks } from '../src/store.mjs';

test('旧版迁移可以重复执行且不会创建重复任务', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'agent-todo-migrate-'));
  await writeFile(
    path.join(root, 'todo.md'),
    '# TODO\n\n## 📋 Todo\n- [ ] 第一条旧任务\n',
    'utf8',
  );

  const first = await migrateLegacy(root, { apply: true });
  assert.equal(first.pending, 1);
  assert.equal(first.migrated, 1);
  assert.equal((await listTasks(root)).length, 1);

  const second = await migrateLegacy(root, { apply: true });
  assert.equal(second.pending, 0);
  assert.equal(second.alreadyMigrated, 1);
  assert.equal(second.migrated, 0);
  assert.equal((await listTasks(root)).length, 1);
});
