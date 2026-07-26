import { randomInt } from 'node:crypto';
import {
  access,
  mkdir,
  readFile,
  readdir,
  rename,
  stat,
  writeFile,
} from 'node:fs/promises';
import { homedir } from 'node:os';
import path from 'node:path';
import { parseDocument } from 'yaml';

export const STATUSES = [
  'idea',
  'shaping',
  'canDurable',
  'doing',
  'waitingHuman',
  'done',
];

export const DURABLE_BASES = [
  'poc-passed',
  'human-confirmed',
  'ai-assessed',
];

export const TASK_ID_PATTERN = /^TSK-[a-z0-9]{8}$/;

const REQUIRED_FIELDS = ['task_id', 'title', 'status', 'created', 'updated'];
const ID_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789';
const FRONTMATTER_PATTERN = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/;

export function today() {
  return new Date().toISOString().slice(0, 10);
}

async function exists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

export async function findGitRoot(start = process.cwd()) {
  let cursor = path.resolve(start);
  const info = await stat(cursor).catch(() => null);
  if (info?.isFile()) cursor = path.dirname(cursor);

  while (true) {
    if (await exists(path.join(cursor, '.git'))) return cursor;
    const parent = path.dirname(cursor);
    if (parent === cursor) return null;
    cursor = parent;
  }
}

export async function resolveTaskRoot(options = {}, cwd = process.cwd()) {
  if (options.root) return path.resolve(options.root);

  if (options.currentProject) {
    const gitRoot = await findGitRoot(cwd);
    if (!gitRoot) throw new Error('当前目录不在 Git 项目中，无法使用 --current-project');
    return path.join(gitRoot, '.agent-tasks');
  }

  if (options.project) {
    const projectPath = path.resolve(options.project);
    const gitRoot = await findGitRoot(projectPath);
    if (!gitRoot || gitRoot !== projectPath) {
      throw new Error(`指定路径不是 Git 项目根目录：${projectPath}`);
    }
    return path.join(gitRoot, '.agent-tasks');
  }

  return path.resolve(
    process.env.AGENT_TASKS_HOME || path.join(homedir(), '.agent-tasks'),
  );
}

export async function ensureStore(root) {
  const resolved = path.resolve(root);
  await Promise.all([
    mkdir(path.join(resolved, 'tasks'), { recursive: true }),
    mkdir(path.join(resolved, 'references'), { recursive: true }),
    mkdir(path.join(resolved, 'archive'), { recursive: true }),
  ]);
  return resolved;
}

export function assertTaskId(taskId) {
  if (!TASK_ID_PATTERN.test(taskId)) {
    throw new Error(`无效 Task ID：${taskId}`);
  }
}

export function assertStatus(status) {
  if (!STATUSES.includes(status)) {
    throw new Error(`无效状态：${status}；允许值：${STATUSES.join(', ')}`);
  }
}

function assertTitle(title) {
  if (typeof title !== 'string' || !title.trim()) {
    throw new Error('任务标题不能为空');
  }
  if (/[\r\n]/.test(title)) throw new Error('任务标题不能包含换行');
  if (title.length > 200) throw new Error('任务标题不能超过 200 个字符');
}

export function assertDurableBasis(status, durableBasis) {
  if (status === 'canDurable') {
    if (!DURABLE_BASES.includes(durableBasis)) {
      throw new Error(
        `canDurable 必须指定 durable_basis：${DURABLE_BASES.join(', ')}`,
      );
    }
  } else if (durableBasis !== undefined && durableBasis !== null) {
    throw new Error('只有 canDurable 状态可以设置 durable_basis');
  }
}

function parseFrontmatter(source, filePath = '<memory>') {
  const match = source.match(FRONTMATTER_PATTERN);
  if (!match) throw new Error(`缺少 YAML Frontmatter：${filePath}`);

  const yamlSource = match[1];
  const document = parseDocument(yamlSource, { schema: 'core' });
  if (document.errors.length > 0) {
    throw new Error(
      `YAML 解析失败：${filePath}：${document.errors.map((item) => item.message).join('; ')}`,
    );
  }

  const data = document.toJS() || {};
  const body = source.slice(match[0].length);
  return { document, data, body };
}

function serializeFrontmatter(document, body) {
  const yaml = String(document).trimEnd();
  const normalizedBody = body.replace(/^\r?\n+/, '');
  return `---\n${yaml}\n---\n${normalizedBody ? `\n${normalizedBody}` : ''}`;
}

function validateTaskData(data, filePath = '<memory>') {
  for (const field of REQUIRED_FIELDS) {
    if (data[field] === undefined || data[field] === null || data[field] === '') {
      throw new Error(`缺少必填字段 ${field}：${filePath}`);
    }
  }
  assertTaskId(String(data.task_id));
  assertTitle(data.title);
  assertStatus(String(data.status));
  assertDurableBasis(data.status, data.durable_basis);
  if (data.references !== undefined && !Array.isArray(data.references)) {
    throw new Error(`references 必须是数组：${filePath}`);
  }
  if (
    Array.isArray(data.references) &&
    data.references.some((reference) => typeof reference !== 'string')
  ) {
    throw new Error(`references 只能包含字符串：${filePath}`);
  }
}

function taskFile(root, taskId, directory = 'tasks') {
  assertTaskId(taskId);
  const base = path.resolve(root, directory);
  const target = path.resolve(base, `${taskId}.md`);
  if (path.dirname(target) !== base) throw new Error('任务路径越界');
  return target;
}

async function atomicWrite(target, content) {
  const directory = path.dirname(target);
  await mkdir(directory, { recursive: true });
  const temporary = path.join(
    directory,
    `.${path.basename(target)}.${process.pid}.${Date.now()}.tmp`,
  );
  await writeFile(temporary, content, 'utf8');
  await rename(temporary, target);
}

export async function readTask(root, taskId, directory = 'tasks') {
  const filePath = taskFile(root, taskId, directory);
  const source = await readFile(filePath, 'utf8');
  const parsed = parseFrontmatter(source, filePath);
  validateTaskData(parsed.data, filePath);
  return {
    ...parsed,
    id: parsed.data.task_id,
    filePath,
    source,
  };
}

export async function writeTask(task, changes = {}) {
  const { document, body, filePath } = task;
  const nextBody = changes.body ?? body;
  const fields = changes.fields || {};

  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined) continue;
    if (value === null || value === '') document.delete(key);
    else document.set(key, value);
  }
  document.set('updated', today());

  const nextData = document.toJS() || {};
  validateTaskData(nextData, filePath);
  await atomicWrite(filePath, serializeFrontmatter(document, nextBody));
  return readTask(path.dirname(path.dirname(filePath)), nextData.task_id);
}

async function generateTaskId(root) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    let suffix = '';
    for (let index = 0; index < 8; index += 1) {
      suffix += ID_ALPHABET[randomInt(ID_ALPHABET.length)];
    }
    const taskId = `TSK-${suffix}`;
    if (
      !(await exists(taskFile(root, taskId))) &&
      !(await exists(taskFile(root, taskId, 'archive')))
    ) {
      return taskId;
    }
  }
  throw new Error('无法生成唯一 Task ID');
}

function defaultBody(title) {
  return `# ${title}\n\n## 想法\n\n\n## 下一步\n`;
}

export async function createTask(root, input) {
  const resolved = await ensureStore(root);
  const title = String(input.title || '').trim();
  assertTitle(title);
  if (
    input.references !== undefined &&
    (!Array.isArray(input.references) ||
      input.references.some((reference) => typeof reference !== 'string'))
  ) {
    throw new Error('references 必须是字符串数组');
  }

  const status = input.status || 'idea';
  assertStatus(status);
  assertDurableBasis(status, input.durableBasis);
  const taskId = input.taskId || (await generateTaskId(resolved));
  assertTaskId(taskId);
  const filePath = taskFile(resolved, taskId);
  if (
    (await exists(filePath)) ||
    (await exists(taskFile(resolved, taskId, 'archive')))
  ) {
    throw new Error(`Task ID 已存在：${taskId}`);
  }

  const data = {
    task_id: taskId,
    title,
    status,
    created: today(),
    updated: today(),
  };
  if (input.project) data.project = String(input.project);
  if (input.workspace) data.workspace = String(input.workspace);
  if (input.references?.length) data.references = input.references;
  if (input.durableBasis) data.durable_basis = input.durableBasis;

  const document = parseDocument('', { schema: 'core' });
  document.contents = document.createNode(data);
  const body = input.body?.trim()
    ? `${input.body.trim()}\n`
    : defaultBody(title);
  await atomicWrite(filePath, serializeFrontmatter(document, body));
  const task = await readTask(resolved, taskId);
  await rebuildIndexes(resolved);
  return task;
}

export async function listTasks(root, filters = {}) {
  const resolved = await ensureStore(root);
  const directory = path.join(resolved, 'tasks');
  const names = (await readdir(directory))
    .filter((name) => TASK_ID_PATTERN.test(name.replace(/\.md$/, '')))
    .filter((name) => name.endsWith('.md'))
    .sort();

  const tasks = [];
  for (const name of names) {
    const taskId = name.slice(0, -3);
    const task = await readTask(resolved, taskId);
    if (filters.status && task.data.status !== filters.status) continue;
    if (filters.project && task.data.project !== filters.project) continue;
    tasks.push(task);
  }

  return tasks.sort((left, right) => {
    const updated = String(right.data.updated).localeCompare(
      String(left.data.updated),
    );
    return updated || left.data.title.localeCompare(right.data.title, 'zh-CN');
  });
}

export async function updateTask(root, taskId, fields) {
  const task = await readTask(root, taskId);
  if (fields.title !== undefined) {
    fields.title = String(fields.title).trim();
    assertTitle(fields.title);
  }
  const nextStatus = fields.status ?? task.data.status;
  const nextBasis =
    fields.durable_basis !== undefined
      ? fields.durable_basis || undefined
      : task.data.durable_basis;

  if (nextStatus !== 'canDurable') fields.durable_basis = null;
  assertStatus(nextStatus);
  assertDurableBasis(
    nextStatus,
    nextStatus === 'canDurable' ? nextBasis : undefined,
  );

  const body =
    fields.title !== undefined
      ? task.body.match(/^#\s+.+$/m)
        ? task.body.replace(/^#\s+.+$/m, `# ${fields.title}`)
        : `# ${fields.title}\n\n${task.body}`
      : task.body;
  const updated = await writeTask(task, { fields, body });
  await rebuildIndexes(root);
  return updated;
}

export async function setTaskStatus(root, taskId, status, durableBasis) {
  assertStatus(status);
  assertDurableBasis(status, durableBasis);
  return updateTask(root, taskId, {
    status,
    durable_basis: status === 'canDurable' ? durableBasis : null,
  });
}

function sectionPattern(heading) {
  if (
    typeof heading !== 'string' ||
    !heading.trim() ||
    /[\r\n]/.test(heading)
  ) {
    throw new Error('章节标题不能为空或包含换行');
  }
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(
    `(^##[ \\t]+${escaped}[ \\t]*\\r?\\n)([\\s\\S]*?)(?=^##[ \\t]+|(?![\\s\\S]))`,
    'm',
  );
}

export function getSection(body, heading) {
  const match = body.match(sectionPattern(heading));
  return match ? match[2].trim() : null;
}

export function setSection(body, heading, content, mode = 'set') {
  const normalized = String(content || '').trim();
  const pattern = sectionPattern(heading);
  const match = body.match(pattern);

  if (!match) {
    const separator = body.endsWith('\n') ? '\n' : '\n\n';
    return `${body}${separator}## ${heading}\n\n${normalized}\n`;
  }

  let nextContent = normalized;
  if (mode === 'append') {
    const existing = match[2].trim();
    nextContent = [existing, normalized].filter(Boolean).join('\n\n');
  }

  return body.replace(pattern, `${match[1]}\n${nextContent}\n\n`);
}

export async function updateTaskSection(
  root,
  taskId,
  heading,
  content,
  mode = 'set',
) {
  const task = await readTask(root, taskId);
  const body = setSection(task.body, heading, content, mode);
  const updated = await writeTask(task, { body });
  await rebuildIndexes(root);
  return updated;
}

export async function replaceTaskBody(root, taskId, body) {
  const task = await readTask(root, taskId);
  const updated = await writeTask(task, { body });
  await rebuildIndexes(root);
  return updated;
}

function indexTaskLine(task) {
  const basis =
    task.data.status === 'canDurable'
      ? ` — ${task.data.durable_basis}`
      : '';
  const project = task.data.project ? ` · ${task.data.project}` : '';
  return `- [[tasks/${task.id}|${task.data.title}]] \`${task.id}\`${project}${basis}`;
}

export async function buildTaskIndex(root) {
  const tasks = await listTasks(root);
  const lines = [
    '# Tasks',
    '',
    `> 自动生成：${new Date().toISOString()}`,
    `> 任务总数：${tasks.length}`,
    '',
  ];

  for (const status of STATUSES) {
    const group = tasks.filter((task) => task.data.status === status);
    lines.push(`## ${status}`, '');
    if (group.length === 0) lines.push('暂无');
    else lines.push(...group.map(indexTaskLine));
    lines.push('');
  }

  await atomicWrite(path.join(root, 'index.md'), `${lines.join('\n').trim()}\n`);
}

export async function buildReferenceIndex(root) {
  const directory = path.join(root, 'references');
  const names = (await readdir(directory))
    .filter((name) => name.endsWith('.md') && name !== 'index.md')
    .sort();
  const lines = ['# References', '', `> 文件总数：${names.length}`, ''];

  for (const name of names) {
    const source = await readFile(path.join(directory, name), 'utf8');
    const title =
      source.match(/^#\s+(.+)$/m)?.[1]?.trim() || path.basename(name, '.md');
    lines.push(`- [[${path.basename(name, '.md')}|${title}]]`);
  }

  await atomicWrite(
    path.join(directory, 'index.md'),
    `${lines.join('\n').trim()}\n`,
  );
}

export async function rebuildIndexes(root) {
  const resolved = await ensureStore(root);
  await buildTaskIndex(resolved);
  await buildReferenceIndex(resolved);
}

export async function getStats(root) {
  const tasks = await listTasks(root);
  const result = { total: tasks.length };
  for (const status of STATUSES) {
    result[status] = tasks.filter((task) => task.data.status === status).length;
  }
  return result;
}

export async function archiveTask(root, taskId) {
  const resolved = await ensureStore(root);
  const task = await readTask(resolved, taskId);
  const destination = taskFile(resolved, taskId, 'archive');
  if (await exists(destination)) {
    throw new Error(`归档中已存在同名任务：${taskId}`);
  }
  await rename(task.filePath, destination);
  await rebuildIndexes(resolved);
  return destination;
}

export async function moveTask(sourceRoot, destinationRoot, taskId) {
  const source = await ensureStore(sourceRoot);
  const destination = await ensureStore(destinationRoot);
  const task = await readTask(source, taskId);
  const target = taskFile(destination, taskId);
  if (
    (await exists(target)) ||
    (await exists(taskFile(destination, taskId, 'archive')))
  ) {
    throw new Error(`目标目录已存在任务：${taskId}`);
  }
  await rename(task.filePath, target);
  await Promise.all([rebuildIndexes(source), rebuildIndexes(destination)]);
  return readTask(destination, taskId);
}

export async function doctor(root) {
  const resolved = await ensureStore(root);
  const directory = path.join(resolved, 'tasks');
  const names = (await readdir(directory)).filter((name) => name.endsWith('.md'));
  const issues = [];
  const seen = new Map();

  for (const name of names) {
    const filePath = path.join(directory, name);
    try {
      const source = await readFile(filePath, 'utf8');
      const parsed = parseFrontmatter(source, filePath);
      validateTaskData(parsed.data, filePath);
      const taskId = parsed.data.task_id;

      if (name !== `${taskId}.md`) {
        issues.push({
          code: 'filename-mismatch',
          file: filePath,
          message: `文件名应为 ${taskId}.md`,
        });
      }
      if (seen.has(taskId)) {
        issues.push({
          code: 'duplicate-id',
          file: filePath,
          message: `Task ID 与 ${seen.get(taskId)} 重复`,
        });
      } else {
        seen.set(taskId, filePath);
      }

      for (const reference of parsed.data.references || []) {
        if (
          typeof reference === 'string' &&
          reference.startsWith('references/')
        ) {
          const referencePath = path.resolve(resolved, reference);
          const referenceRoot = path.resolve(resolved, 'references');
          if (
            !referencePath.startsWith(`${referenceRoot}${path.sep}`) ||
            !(await exists(referencePath))
          ) {
            issues.push({
              code: 'missing-reference',
              file: filePath,
              message: `本地 Reference 不存在：${reference}`,
            });
          }
        }
      }
    } catch (error) {
      issues.push({
        code: 'invalid-task',
        file: filePath,
        message: error.message,
      });
    }
  }

  const indexPath = path.join(resolved, 'index.md');
  const indexSource = await readFile(indexPath, 'utf8').catch(() => '');
  const indexedIds = new Set(indexSource.match(/TSK-[a-z0-9]{8}/g) || []);
  const actualIds = new Set(seen.keys());
  const indexIsStale =
    indexedIds.size !== actualIds.size ||
    [...actualIds].some((taskId) => !indexedIds.has(taskId));
  if (indexIsStale) {
    issues.push({
      code: 'stale-index',
      file: indexPath,
      message: 'index.md 与 tasks/*.md 不一致，请运行 todo index',
    });
  }

  return { root: resolved, taskCount: names.length, issues };
}
