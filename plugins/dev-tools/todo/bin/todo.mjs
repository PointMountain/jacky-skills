#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import {
  confirm,
  intro,
  isCancel,
  outro,
  select,
  text,
} from '@clack/prompts';
import YAML from 'yaml';
import {
  DURABLE_BASES,
  STATUSES,
  archiveTask,
  createTask,
  doctor,
  getSection,
  getStats,
  listTasks,
  moveTask,
  readTask,
  rebuildIndexes,
  resolveTaskRoot,
  setTaskStatus,
  updateTask,
  updateTaskSection,
} from '../src/store.mjs';

const cli = cac('todo');

function scopeOptions(command) {
  return command
    .option('--global', '使用全局目录（默认行为）')
    .option('--current-project', '使用当前 Git 项目')
    .option('--project <path>', '使用指定 Git 项目')
    .option('--root <path>', '直接指定 .agent-tasks 根目录');
}

function scopeFromOptions(options) {
  return {
    root: options.root,
    currentProject: options.currentProject,
    project: options.project,
  };
}

function fail(error) {
  process.stderr.write(`错误：${error.message}\n`);
  process.exitCode = 1;
}

function outputTask(task, asJson = false) {
  if (asJson) {
    process.stdout.write(
      `${JSON.stringify(
        {
          ...task.data,
          body: task.body,
          file: task.filePath,
        },
        null,
        2,
      )}\n`,
    );
    return;
  }
  process.stdout.write(
    `${task.id}  ${task.data.status}  ${task.data.title}\n${task.filePath}\n`,
  );
}

async function readStdin() {
  if (process.stdin.isTTY) return '';
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

async function promptValue(prompt) {
  const value = await prompt;
  if (isCancel(value)) {
    process.stderr.write('已取消\n');
    process.exit(1);
  }
  return value;
}

scopeOptions(
  cli
    .command('add [title]', '新增任务')
    .option('--status <status>', '初始状态')
    .option('--basis <basis>', 'Durable 判断依据')
    .option('--task-id <id>', '显式指定 Task ID')
    .option('--project-name <name>', '写入任务 YAML 的项目名称')
    .option('--workspace <path>', '任务 Workspace')
    .option('--body <markdown>', '初始 Markdown 正文')
    .option('--json', '输出 JSON'),
).action(async (titleArg, options) => {
  try {
    let titleValue = titleArg;
    let statusValue = options.status;
    let basisValue = options.basis;

    if (!titleValue) {
      intro('Todo · 新增任务');
      titleValue = await promptValue(
        text({ message: '任务标题', placeholder: '记录一个新想法' }),
      );
      statusValue =
        statusValue ||
        (await promptValue(
          select({
            message: '初始状态',
            initialValue: 'idea',
            options: STATUSES.map((value) => ({ value, label: value })),
          }),
        ));
      if (statusValue === 'canDurable') {
        basisValue = await promptValue(
          select({
            message: 'Durable 判断依据',
            options: DURABLE_BASES.map((value) => ({ value, label: value })),
          }),
        );
      }
    }

    const root = await resolveTaskRoot(scopeFromOptions(options));
    const projectScoped = Boolean(options.currentProject || options.project);
    const workspace =
      options.workspace || (projectScoped ? path.dirname(root) : undefined);
    const projectName =
      options.projectName ||
      (projectScoped ? path.basename(path.dirname(root)) : undefined);
    const task = await createTask(root, {
      title: titleValue,
      status: statusValue || 'idea',
      durableBasis: basisValue,
      taskId: options.taskId,
      project: projectName,
      workspace,
      body: options.body,
    });
    outputTask(task, options.json);
    if (!titleArg) outro(`已创建 ${task.id}`);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('list', '列出任务')
    .option('--status <status>', '按状态筛选')
    .option('--project-name <name>', '按项目名称筛选')
    .option('--json', '输出 JSON'),
).action(async (options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const tasks = await listTasks(root, {
      status: options.status,
      project: options.projectName,
    });
    if (options.json) {
      process.stdout.write(
        `${JSON.stringify(tasks.map((task) => task.data), null, 2)}\n`,
      );
      return;
    }
    if (tasks.length === 0) {
      process.stdout.write('暂无任务\n');
      return;
    }
    for (const task of tasks) {
      const basis = task.data.durable_basis
        ? ` · ${task.data.durable_basis}`
        : '';
      const project = task.data.project ? ` · ${task.data.project}` : '';
      process.stdout.write(
        `${task.id}  ${task.data.status.padEnd(12)}  ${task.data.title}${project}${basis}\n`,
      );
    }
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli.command('show <task-id>', '查看任务').option('--json', '输出 JSON'),
).action(async (taskId, options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const task = await readTask(root, taskId);
    if (options.json) outputTask(task, true);
    else process.stdout.write(task.source);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('set <task-id>', '修改任务 YAML 字段')
    .option('--title <title>', '修改标题')
    .option('--project-name <name>', '修改项目名称')
    .option('--workspace <path>', '修改 Workspace')
    .option('--references <items>', '逗号分隔的 Reference')
    .option('--json', '输出 JSON'),
).action(async (taskId, options) => {
  try {
    const fields = {};
    if (options.title !== undefined) fields.title = options.title;
    if (options.projectName !== undefined) fields.project = options.projectName;
    if (options.workspace !== undefined) fields.workspace = options.workspace;
    if (options.references !== undefined) {
      fields.references = options.references
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
    }
    if (Object.keys(fields).length === 0) {
      throw new Error('至少提供一个要修改的字段');
    }
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const task = await updateTask(root, taskId, fields);
    outputTask(task, options.json);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('status <task-id> [status]', '修改任务状态')
    .option('--basis <basis>', 'Durable 判断依据')
    .option('--json', '输出 JSON'),
).action(async (taskId, statusArg, options) => {
  try {
    let statusValue = statusArg;
    let basisValue = options.basis;
    if (!statusValue) {
      statusValue = await promptValue(
        select({
          message: '选择任务状态',
          options: STATUSES.map((value) => ({ value, label: value })),
        }),
      );
    }
    if (statusValue === 'canDurable' && !basisValue) {
      basisValue = await promptValue(
        select({
          message: '选择 Durable 判断依据',
          options: DURABLE_BASES.map((value) => ({ value, label: value })),
        }),
      );
    }
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const task = await setTaskStatus(root, taskId, statusValue, basisValue);
    outputTask(task, options.json);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli.command('edit <task-id>', '用默认编辑器打开任务'),
).action(async (taskId, options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const task = await readTask(root, taskId);
    const editor = process.env.EDITOR || process.env.VISUAL || 'vi';
    const result = spawnSync(editor, [task.filePath], { stdio: 'inherit' });
    if (result.status !== 0) throw new Error(`编辑器退出码：${result.status}`);
    await rebuildIndexes(root);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('stats', '输出任务统计')
    .option('--format <format>', 'table、json 或 yaml', { default: 'table' }),
).action(async (options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const stats = await getStats(root);
    if (options.format === 'json') {
      process.stdout.write(`${JSON.stringify(stats, null, 2)}\n`);
    } else if (options.format === 'yaml') {
      process.stdout.write(YAML.stringify(stats));
    } else {
      for (const [key, value] of Object.entries(stats)) {
        process.stdout.write(`${key.padEnd(14)} ${value}\n`);
      }
    }
  } catch (error) {
    fail(error);
  }
});

scopeOptions(cli.command('index', '重建任务与 Reference 索引')).action(
  async (options) => {
    try {
      const root = await resolveTaskRoot(scopeFromOptions(options));
      await rebuildIndexes(root);
      process.stdout.write(`${root}/index.md\n`);
    } catch (error) {
      fail(error);
    }
  },
);

scopeOptions(
  cli.command('doctor', '检查任务目录完整性').option('--json', '输出 JSON'),
).action(async (options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const report = await doctor(root);
    if (options.json) {
      process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    } else if (report.issues.length === 0) {
      process.stdout.write(`✓ ${report.taskCount} 个任务检查通过\n`);
    } else {
      for (const issue of report.issues) {
        process.stdout.write(`✗ ${issue.code}: ${issue.message}\n`);
      }
      process.exitCode = 1;
    }
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('delete <task-id>', '归档任务')
    .option('--yes', '跳过人工确认'),
).action(async (taskId, options) => {
  try {
    if (!options.yes) {
      const accepted = await promptValue(
        confirm({ message: `确认归档 ${taskId}？` }),
      );
      if (!accepted) return;
    }
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const destination = await archiveTask(root, taskId);
    process.stdout.write(`${destination}\n`);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('move <task-id>', '在全局和项目任务目录之间移动任务')
    .option('--to-root <path>', '目标 .agent-tasks 根目录')
    .option('--to-current-project', '移动到当前 Git 项目')
    .option('--to-project <path>', '移动到指定 Git 项目'),
).action(async (taskId, options) => {
  try {
    const sourceRoot = await resolveTaskRoot(scopeFromOptions(options));
    const destinationRoot = await resolveTaskRoot({
      root: options.toRoot,
      currentProject: options.toCurrentProject,
      project: options.toProject,
    });
    if (sourceRoot === destinationRoot) throw new Error('源目录和目标目录相同');
    const task = await moveTask(sourceRoot, destinationRoot, taskId);
    outputTask(task);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('section <action> <task-id> <heading>', '读取或修改 Markdown 章节')
    .option('--content <markdown>', '章节内容'),
).action(async (action, taskId, heading, options) => {
  try {
    const root = await resolveTaskRoot(scopeFromOptions(options));
    if (action === 'show') {
      const task = await readTask(root, taskId);
      const content = getSection(task.body, heading);
      if (content === null) throw new Error(`章节不存在：${heading}`);
      process.stdout.write(`${content}\n`);
      return;
    }
    if (!['set', 'append'].includes(action)) {
      throw new Error('section action 只支持 set、append、show');
    }
    const content =
      options.content !== undefined ? options.content : await readStdin();
    if (!content.trim()) throw new Error('章节内容不能为空');
    const task = await updateTaskSection(root, taskId, heading, content, action);
    outputTask(task);
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli.command('web', '启动本地 Web 看板').option('--port <port>', '监听端口', {
    default: '4187',
  }),
).action(async (options) => {
  try {
    const { startWebServer } = await import('../src/web-server.mjs');
    const root = await resolveTaskRoot(scopeFromOptions(options));
    await startWebServer(root, Number(options.port));
  } catch (error) {
    fail(error);
  }
});

scopeOptions(
  cli
    .command('migrate', '尽力迁移旧 todo.md 格式')
    .option('--apply', '执行迁移，默认仅预览'),
).action(async (options) => {
  try {
    const { migrateLegacy } = await import('../src/migrate.mjs');
    const root = await resolveTaskRoot(scopeFromOptions(options));
    const result = await migrateLegacy(root, { apply: options.apply });
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    fail(error);
  }
});

cli.help();
cli.version('0.1.0');
cli.parse();
