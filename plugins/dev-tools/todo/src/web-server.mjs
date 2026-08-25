import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  DURABLE_BASES,
  STATUSES,
  TASK_ID_PATTERN,
  archiveTask,
  createTask,
  ensureStore,
  getStats,
  listTasks,
  readTask,
  rebuildIndexes,
  replaceTaskBody,
  updateTask,
} from './store.mjs';
import { migrateLegacy } from './migrate.mjs';

const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const webDirectory = path.resolve(moduleDirectory, '..', 'web');
const MAX_BODY_BYTES = 1024 * 1024;

const STATIC_FILES = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);

function sendJson(response, statusCode, value) {
  const body = JSON.stringify(value);
  response.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
  });
  response.end(body);
}

function sendError(response, error, statusCode = 400) {
  sendJson(response, statusCode, { error: error.message });
}

async function readJson(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) throw new Error('请求体超过 1 MiB 限制');
    chunks.push(chunk);
  }
  if (chunks.length === 0) return {};
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new Error('请求体不是合法 JSON');
  }
}

function taskPayload(task) {
  return {
    ...task.data,
    body: task.body,
    file: task.filePath,
  };
}

function apiTaskId(pathname) {
  const match = pathname.match(/^\/api\/tasks\/([^/]+)$/);
  if (!match) return null;
  const taskId = decodeURIComponent(match[1]);
  if (!TASK_ID_PATTERN.test(taskId)) throw new Error('无效 Task ID');
  return taskId;
}

async function handleApi(root, request, response, url) {
  if (request.method === 'GET' && url.pathname === '/api/meta') {
    const [stats, tasks, legacy] = await Promise.all([
      getStats(root),
      listTasks(root),
      migrateLegacy(root),
    ]);
    sendJson(response, 200, {
      root,
      statuses: STATUSES,
      durableBases: DURABLE_BASES,
      stats,
      taskCount: tasks.length,
      legacy: {
        found: legacy.found,
        planned: legacy.pending ?? legacy.planned,
      },
    });
    return true;
  }

  if (request.method === 'GET' && url.pathname === '/api/tasks') {
    const tasks = await listTasks(root, {
      status: url.searchParams.get('status') || undefined,
    });
    sendJson(response, 200, tasks.map(taskPayload));
    return true;
  }

  if (request.method === 'POST' && url.pathname === '/api/tasks') {
    const input = await readJson(request);
    const task = await createTask(root, {
      title: input.title,
      status: input.status || 'idea',
      durableBasis: input.durable_basis,
      project: input.project,
      workspace: input.workspace,
      references: input.references,
      body: input.body,
    });
    sendJson(response, 201, taskPayload(task));
    return true;
  }

  const taskId = apiTaskId(url.pathname);
  if (!taskId) return false;

  if (request.method === 'GET') {
    sendJson(response, 200, taskPayload(await readTask(root, taskId)));
    return true;
  }

  if (request.method === 'PATCH') {
    const input = await readJson(request);
    const fields = {};
    for (const key of [
      'title',
      'status',
      'project',
      'workspace',
      'references',
      'durable_basis',
    ]) {
      if (Object.hasOwn(input, key)) fields[key] = input[key];
    }

    let task =
      Object.keys(fields).length > 0
        ? await updateTask(root, taskId, fields)
        : await readTask(root, taskId);
    if (Object.hasOwn(input, 'body')) {
      task = await replaceTaskBody(root, taskId, String(input.body));
    }
    sendJson(response, 200, taskPayload(task));
    return true;
  }

  if (request.method === 'DELETE') {
    const destination = await archiveTask(root, taskId);
    sendJson(response, 200, { task_id: taskId, archived_to: destination });
    return true;
  }

  return false;
}

async function serveStatic(response, pathname) {
  const asset = STATIC_FILES.get(pathname);
  if (!asset) return false;
  const [name, contentType] = asset;
  const filePath = path.join(webDirectory, name);
  const info = await stat(filePath);
  response.writeHead(200, {
    'Content-Type': contentType,
    'Content-Length': info.size,
    'Cache-Control': 'no-cache',
  });
  createReadStream(filePath).pipe(response);
  return true;
}

export function createWebServer(root) {
  const resolvedRoot = path.resolve(root);
  return createServer(async (request, response) => {
    const url = new URL(request.url || '/', 'http://127.0.0.1');
    try {
      if (url.pathname.startsWith('/api/')) {
        const handled = await handleApi(resolvedRoot, request, response, url);
        if (!handled) sendJson(response, 404, { error: 'API 不存在' });
        return;
      }
      if (!(await serveStatic(response, url.pathname))) {
        response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        response.end('Not Found');
      }
    } catch (error) {
      sendError(response, error);
    }
  });
}

export async function startWebServer(root, port = 4187) {
  const resolvedRoot = await ensureStore(root);
  await rebuildIndexes(resolvedRoot);
  const server = createWebServer(resolvedRoot);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  const address = server.address();
  const actualPort = typeof address === 'object' ? address.port : port;
  process.stdout.write(
    `Todo Web 已启动：http://127.0.0.1:${actualPort}\n任务目录：${resolvedRoot}\n按 Ctrl+C 停止\n`,
  );
  return server;
}
