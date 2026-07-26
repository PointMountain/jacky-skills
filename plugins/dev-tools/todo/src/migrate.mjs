import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { createTask, ensureStore, listTasks } from './store.mjs';

function parseLegacyTodo(source) {
  const entries = [];
  let section = null;
  let current = null;

  const flush = () => {
    if (!current) return;
    current.description = current.lines.join('\n').trim();
    delete current.lines;
    entries.push(current);
    current = null;
  };

  for (const line of source.split(/\r?\n/)) {
    if (/^##\s+.*Ideas/i.test(line)) {
      flush();
      section = 'idea';
      continue;
    }
    if (/^##\s+.*Todo/i.test(line)) {
      flush();
      section = 'todo';
      continue;
    }

    const item = line.match(/^\s*-\s+\[([ xX])\]\s+(.+)$/);
    if (item) {
      flush();
      current = {
        checked: item[1].toLowerCase() === 'x',
        section,
        lines: [item[2]],
      };
      continue;
    }

    if (current && /^\s{2,}\S/.test(line)) current.lines.push(line.trim());
  }
  flush();
  return entries;
}

function cleanTitle(description) {
  return description
    .replace(/\s+@context:[^\s]+/g, '')
    .split('\n')[0]
    .trim()
    .slice(0, 120);
}

async function readCheckpoint(root, description) {
  const match = description.match(/@context:([^\s]+)/);
  if (!match) return null;
  const checkpointPath = path.resolve(root, match[1]);
  if (path.dirname(checkpointPath) !== path.resolve(root)) return null;
  return readFile(checkpointPath, 'utf8').catch(() => null);
}

export async function migrateLegacy(root, options = {}) {
  const resolved = await ensureStore(root);
  const legacyPath = path.join(resolved, 'todo.md');
  const source = await readFile(legacyPath, 'utf8').catch(() => null);
  if (!source) {
    return {
      root: resolved,
      found: false,
      planned: 0,
      migrated: 0,
      errors: [],
    };
  }

  const entries = parseLegacyTodo(source);
  const existingTasks = await listTasks(resolved);
  const isMigrated = (entry) =>
    existingTasks.some((task) =>
      task.body.includes(`## 原始任务\n\n${entry.description.trim()}`),
    );
  const pendingEntries = entries.filter((entry) => !isMigrated(entry));
  const result = {
    root: resolved,
    found: true,
    planned: entries.length,
    pending: pendingEntries.length,
    alreadyMigrated: entries.length - pendingEntries.length,
    migrated: 0,
    errors: [],
    preview: entries.map((entry) => ({
      title: cleanTitle(entry.description),
      status: entry.checked
        ? 'done'
        : entry.section === 'idea'
          ? 'idea'
          : 'shaping',
      already_migrated: isMigrated(entry),
    })),
  };

  if (!options.apply) return result;

  for (const entry of pendingEntries) {
    try {
      const title = cleanTitle(entry.description);
      if (!title) throw new Error('无法提取任务标题');
      const checkpoint = await readCheckpoint(resolved, entry.description);
      const body = [
        `# ${title}`,
        '',
        '## 原始任务',
        '',
        entry.description,
        '',
      ];
      if (checkpoint) {
        body.push(
          '## 迁移上下文',
          '',
          '<!-- legacy-checkpoint:start -->',
          '',
          checkpoint.trim(),
          '',
          '<!-- legacy-checkpoint:end -->',
          '',
        );
      }
      body.push('## 下一步', '', '');

      await createTask(resolved, {
        title,
        status: entry.checked
          ? 'done'
          : entry.section === 'idea'
            ? 'idea'
            : 'shaping',
        body: body.join('\n'),
      });
      result.migrated += 1;
    } catch (error) {
      result.errors.push({
        source: entry.description,
        message: error.message,
      });
    }
  }

  return result;
}
