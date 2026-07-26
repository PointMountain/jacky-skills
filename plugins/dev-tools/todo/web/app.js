const state = {
  meta: null,
  tasks: [],
  selectedTaskId: null,
};

const board = document.querySelector('#board');
const metrics = document.querySelector('#metrics');
const rootPath = document.querySelector('#root-path');
const quickAddForm = document.querySelector('#quick-add-form');
const quickTitle = document.querySelector('#quick-title');
const refreshButton = document.querySelector('#refresh-button');
const dialog = document.querySelector('#task-dialog');
const taskForm = document.querySelector('#task-form');
const closeDialogButton = document.querySelector('#close-dialog');
const cancelButton = document.querySelector('#cancel-button');
const archiveButton = document.querySelector('#archive-button');
const toast = document.querySelector('#toast');
const taskStatus = document.querySelector('#task-status');
const taskBasis = document.querySelector('#task-basis');
const basisField = document.querySelector('#basis-field');
const legacyNotice = document.querySelector('#legacy-notice');
const legacyCount = document.querySelector('#legacy-count');

const labels = {
  idea: 'IDEA',
  shaping: 'SHAPING',
  canDurable: 'CAN DURABLE',
  doing: 'DOING',
  waitingHuman: 'WAITING HUMAN',
  done: 'DONE',
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || '请求失败');
  return payload;
}

let toastTimer;
let archiveConfirmTimer;
function showToast(message, type = 'success') {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast visible${type === 'error' ? ' error' : ''}`;
  toastTimer = setTimeout(() => {
    toast.className = 'toast';
  }, 2600);
}

function setButtonBusy(button, busy, busyText) {
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent.trim();
  }
  button.disabled = busy;
  button.textContent = busy ? busyText : button.dataset.defaultText;
}

function resetArchiveConfirmation() {
  clearTimeout(archiveConfirmTimer);
  archiveButton.dataset.confirming = 'false';
  archiveButton.textContent = '归档任务';
}

function metric(label, value) {
  const element = document.createElement('div');
  element.className = 'metric';
  const name = document.createElement('span');
  name.textContent = label;
  const number = document.createElement('strong');
  number.textContent = value;
  element.append(name, number);
  return element;
}

function renderMetrics() {
  metrics.replaceChildren();
  metrics.append(metric('TOTAL', state.tasks.length));
  for (const status of state.meta.statuses) {
    metrics.append(
      metric(
        labels[status] || status,
        state.tasks.filter((task) => task.status === status).length,
      ),
    );
  }
}

function taskCard(task) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'task-card';
  button.dataset.taskId = task.task_id;

  const taskId = document.createElement('small');
  taskId.textContent = task.task_id;
  const title = document.createElement('strong');
  title.textContent = task.title;
  const project = document.createElement('span');
  project.textContent = task.project || 'GLOBAL / UNBOUND';

  button.append(taskId, title, project);
  if (task.durable_basis) {
    const basis = document.createElement('span');
    basis.className = 'durable-basis';
    basis.textContent = `DURABLE · ${task.durable_basis}`;
    button.append(basis);
  }
  button.addEventListener('click', () => openTask(task.task_id));
  return button;
}

function renderBoard() {
  board.replaceChildren();
  for (const status of state.meta.statuses) {
    const tasks = state.tasks.filter((task) => task.status === status);
    const column = document.createElement('section');
    column.className = 'column';
    column.dataset.status = status;

    const header = document.createElement('header');
    header.className = 'column-header';
    const title = document.createElement('h3');
    title.textContent = labels[status] || status;
    const count = document.createElement('span');
    count.className = 'column-count';
    count.textContent = tasks.length;
    header.append(title, count);

    const list = document.createElement('div');
    list.className = 'task-list';
    if (tasks.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'NO TASKS';
      list.append(empty);
    } else {
      list.append(...tasks.map(taskCard));
    }
    column.append(header, list);
    board.append(column);
  }
}

async function load() {
  const [meta, tasks] = await Promise.all([
    request('/api/meta'),
    request('/api/tasks'),
  ]);
  state.meta = meta;
  state.tasks = tasks;
  rootPath.textContent = meta.root;
  const hasLegacyTasks = Number(meta.legacy?.planned || 0) > 0;
  legacyNotice.hidden = !hasLegacyTasks;
  legacyCount.textContent = meta.legacy?.planned || 0;
  renderMetrics();
  renderBoard();
}

function fillSelect(selectElement, values) {
  selectElement.replaceChildren();
  for (const value of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    selectElement.append(option);
  }
}

function toggleBasis() {
  const visible = taskStatus.value === 'canDurable';
  basisField.hidden = !visible;
  taskBasis.required = visible;
}

async function openTask(taskId) {
  const task = await request(`/api/tasks/${encodeURIComponent(taskId)}`);
  state.selectedTaskId = taskId;
  document.querySelector('#dialog-task-id').textContent = task.task_id;
  document.querySelector('#task-title').value = task.title || '';
  taskStatus.value = task.status;
  taskBasis.value = task.durable_basis || state.meta.durableBases[0];
  document.querySelector('#task-project').value = task.project || '';
  document.querySelector('#task-workspace').value = task.workspace || '';
  document.querySelector('#task-references').value = (
    task.references || []
  ).join('\n');
  document.querySelector('#task-body').value = task.body || '';
  toggleBasis();
  resetArchiveConfirmation();
  dialog.showModal();
}

quickAddForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = quickTitle.value.trim();
  if (!title) return;
  const submitButton = quickAddForm.querySelector('button[type="submit"]');
  try {
    setButtonBusy(submitButton, true, '正在新增…');
    const task = await request('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, status: 'idea' }),
    });
    quickTitle.value = '';
    await load();
    showToast(`已创建 ${task.task_id}`);
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setButtonBusy(submitButton, false, '');
  }
});

taskStatus.addEventListener('change', toggleBasis);
refreshButton.addEventListener('click', async () => {
  try {
    setButtonBusy(refreshButton, true, '正在刷新…');
    await load();
    showToast('已从 Markdown 刷新');
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setButtonBusy(refreshButton, false, '');
  }
});

taskForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.selectedTaskId) return;
  const payload = {
    title: document.querySelector('#task-title').value.trim(),
    status: taskStatus.value,
    durable_basis:
      taskStatus.value === 'canDurable' ? taskBasis.value : null,
    project: document.querySelector('#task-project').value.trim() || null,
    workspace: document.querySelector('#task-workspace').value.trim() || null,
    references: document
      .querySelector('#task-references')
      .value.split('\n')
      .map((item) => item.trim())
      .filter(Boolean),
    body: document.querySelector('#task-body').value,
  };
  const submitButton = taskForm.querySelector('button[type="submit"]');
  try {
    setButtonBusy(submitButton, true, '正在保存…');
    await request(`/api/tasks/${encodeURIComponent(state.selectedTaskId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    dialog.close();
    await load();
    showToast('任务已保存');
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setButtonBusy(submitButton, false, '');
  }
});

archiveButton.addEventListener('click', async () => {
  if (!state.selectedTaskId) return;
  if (archiveButton.dataset.confirming !== 'true') {
    archiveButton.dataset.confirming = 'true';
    archiveButton.textContent = '再次点击确认归档';
    showToast(`归档后文件会移入 archive/：${state.selectedTaskId}`);
    archiveConfirmTimer = setTimeout(resetArchiveConfirmation, 10000);
    return;
  }
  try {
    clearTimeout(archiveConfirmTimer);
    setButtonBusy(archiveButton, true, '正在归档…');
    await request(`/api/tasks/${encodeURIComponent(state.selectedTaskId)}`, {
      method: 'DELETE',
    });
    dialog.close();
    await load();
    showToast('任务已归档');
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setButtonBusy(archiveButton, false, '');
    resetArchiveConfirmation();
  }
});

closeDialogButton.addEventListener('click', () => {
  resetArchiveConfirmation();
  dialog.close();
});
cancelButton.addEventListener('click', () => {
  resetArchiveConfirmation();
  dialog.close();
});
dialog.addEventListener('click', (event) => {
  if (event.target === dialog) {
    resetArchiveConfirmation();
    dialog.close();
  }
});

async function bootstrap() {
  try {
    const meta = await request('/api/meta');
    state.meta = meta;
    fillSelect(taskStatus, meta.statuses);
    fillSelect(taskBasis, meta.durableBases);
    await load();
  } catch (error) {
    rootPath.textContent = '任务目录连接失败';
    showToast(error.message, 'error');
  }
}

bootstrap();
