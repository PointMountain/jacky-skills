import { randomUUID } from 'node:crypto';
import {
  mkdir,
  open,
  readFile,
  rename,
  rm,
} from 'node:fs/promises';
import path from 'node:path';

import {
  canonicalJson,
  createRunInitialization,
  createSourcePlanEvent,
  replayEvents,
} from './state-contract.mjs';
import {
  createWorkflowEvent,
  workflowEventReducer,
} from './workflow-contract.mjs';
import { resolveSourceDirectory } from './artifact-store.mjs';
import { deploymentEventReducer } from './deployment-contract.mjs';
import { finalizationEventReducer } from './finalize-contract.mjs';
import { gateEventReducer } from './gate-contract.mjs';
import { reviewEventReducer } from './review-contract.mjs';
import { assertNoSensitiveContent } from './sensitive-scan.mjs';
import {
  captureGitBaseline,
  captureManagedPath,
  prepareSourcePlan,
  projectRootFromRunDir,
  renderPreexistingState,
  verifySourceState,
} from './source-safety.mjs';

const RUNTIME_IGNORE_ENTRY = '.web-flow/';

function replayRuntimeEvents(events) {
  return replayEvents(events, (state, event) =>
    workflowEventReducer(state, event) ??
    reviewEventReducer(state, event) ??
    gateEventReducer(state, event) ??
    deploymentEventReducer(state, event) ??
    finalizationEventReducer(state, event),
  );
}

function isMissingFile(error) {
  return error?.code === 'ENOENT';
}

async function readOptionalText(filePath) {
  try {
    return await readFile(filePath, 'utf8');
  } catch (error) {
    if (isMissingFile(error)) return null;
    throw error;
  }
}

async function writeSyncedFile(filePath, contents, flags = 'wx') {
  const handle = await open(filePath, flags, 0o600);
  try {
    await handle.writeFile(contents, 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function createProjectionTemp(runDir, state) {
  const temporaryPath = path.join(
    runDir,
    `.run.json.${process.pid}.${randomUUID()}.tmp`,
  );
  await writeSyncedFile(
    temporaryPath,
    `${JSON.stringify(state, null, 2)}\n`,
  );
  return temporaryPath;
}

async function replaceProjection(runDir, state) {
  const temporaryPath = await createProjectionTemp(runDir, state);
  try {
    await rename(temporaryPath, path.join(runDir, 'run.json'));
  } finally {
    await rm(temporaryPath, { force: true });
  }
}

function statesMatch(left, right) {
  return canonicalJson(left) === canonicalJson(right);
}

async function readProjection(runDir) {
  const projectionPath = path.join(runDir, 'run.json');
  const text = await readOptionalText(projectionPath);
  if (text === null) return null;

  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`run.json 不是合法 JSON：${error.message}`, {
      cause: error,
    });
  }
}

export async function readRuntimeEvents(runDir) {
  const eventsPath = path.join(runDir, 'events.jsonl');
  const text = await readFile(eventsPath, 'utf8');
  const lines = text.endsWith('\n') ? text.slice(0, -1).split('\n') : text.split('\n');

  if (lines.length === 1 && lines[0] === '') {
    throw new Error('events.jsonl 不能为空');
  }
  if (lines.some((line) => line.length === 0)) {
    throw new Error('events.jsonl 包含空行');
  }

  return lines.map((line, index) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      throw new Error(`events.jsonl 第 ${index + 1} 行不是合法 JSON`, {
        cause: error,
      });
    }
  });
}

export async function ensureRuntimeIgnored(projectRoot) {
  const gitignorePath = path.join(path.resolve(projectRoot), '.gitignore');
  const original = (await readOptionalText(gitignorePath)) ?? '';
  const hasEntry = original
    .split(/\r?\n/u)
    .some((line) => line === RUNTIME_IGNORE_ENTRY);

  if (hasEntry) return false;

  const separator = original.length > 0 && !original.endsWith('\n') ? '\n' : '';
  const updated = `${original}${separator}${RUNTIME_IGNORE_ENTRY}\n`;
  const temporaryPath = `${gitignorePath}.${process.pid}.${randomUUID()}.tmp`;

  try {
    await writeSyncedFile(temporaryPath, updated);
    await rename(temporaryPath, gitignorePath);
  } finally {
    await rm(temporaryPath, { force: true });
  }
  return true;
}

export async function initializeRun({ projectRoot, input, metadata }) {
  assertNoSensitiveContent(canonicalJson({ input, metadata }), '初始化输入');
  if (input?.projectRoot !== '.') throw new Error('projectRoot 必须严格为 .');
  const absoluteProjectRoot = path.resolve(projectRoot);
  const sourceTarget = await resolveSourceDirectory({
    projectRoot: absoluteProjectRoot,
    sourceDir: input.source?.dir,
    mode: input.source?.mode,
    allowProjectRoot: input.source?.allowProjectRoot === true,
  });
  let baseline = null;
  if (input.source.mode === 'update') {
    baseline = await captureGitBaseline(absoluteProjectRoot);
    assertNoSensitiveContent(canonicalJson(baseline), 'source baseline');
  }

  const ignoreChanged = await ensureRuntimeIgnored(absoluteProjectRoot);
  if (baseline && ignoreChanged) {
    baseline.managed.push(
      await captureManagedPath(absoluteProjectRoot, '.gitignore'),
    );
  }
  const effectiveInput = {
    ...input,
    source: {
      ...input.source,
      dir: sourceTarget.relativePath,
      ...(baseline ? { baseline } : {}),
    },
  };
  const { event, state } = createRunInitialization(effectiveInput, metadata);
  assertNoSensitiveContent(canonicalJson(event), 'run_initialized event');
  const runsRoot = path.join(absoluteProjectRoot, '.web-flow', 'runs');
  const runDir = path.join(runsRoot, state.runId);

  await mkdir(runsRoot, { recursive: true });
  await mkdir(runDir);

  let projectionTemp;
  try {
    projectionTemp = await createProjectionTemp(runDir, state);
    await writeSyncedFile(path.join(runDir, 'artifacts.jsonl'), '');
    if (baseline) {
      await writeSyncedFile(
        path.join(runDir, 'preexisting-state.md'),
        renderPreexistingState(baseline),
      );
    }
    await writeSyncedFile(
      path.join(runDir, 'events.jsonl'),
      `${canonicalJson(event)}\n`,
    );
    await rename(projectionTemp, path.join(runDir, 'run.json'));
    projectionTemp = null;
  } catch (error) {
    await rm(runDir, { recursive: true, force: true });
    throw error;
  } finally {
    if (projectionTemp) await rm(projectionTemp, { force: true });
  }

  return { runDir, event, state };
}

export async function assertProjectionMatchesEvents(runDir) {
  const events = await readRuntimeEvents(runDir);
  const expectedState = replayRuntimeEvents(events);
  const storedState = await readProjection(runDir);

  if (storedState === null) {
    throw new Error('run.json 缺失；请先执行 reconcile');
  }
  if (!statesMatch(storedState, expectedState)) {
    throw new Error('run.json 投影与权威事件日志不一致');
  }

  return { events, state: expectedState };
}

export async function reconcileRun(runDir) {
  const events = await readRuntimeEvents(runDir);
  const expectedState = replayRuntimeEvents(events);
  const storedState = await readProjection(runDir);

  if (storedState === null) {
    await replaceProjection(runDir, expectedState);
    return expectedState;
  }
  if (statesMatch(storedState, expectedState)) return expectedState;

  const storedSequence = storedState.eventSequence;
  if (
    Number.isInteger(storedSequence) &&
    storedSequence > 0 &&
    storedSequence < events.length
  ) {
    const prefixState = replayRuntimeEvents(events.slice(0, storedSequence));
    if (statesMatch(storedState, prefixState)) {
      await replaceProjection(runDir, expectedState);
      return expectedState;
    }
  }

  throw new Error('run.json 投影与事件日志不一致，拒绝猜测修复');
}

export async function appendRuntimeEvent(runDir, event) {
  assertNoSensitiveContent(canonicalJson(event), 'runtime event');
  const { events, state } = await assertProjectionMatchesEvents(runDir);
  const existing = events.find((candidate) => candidate.eventId === event.eventId);

  if (existing) {
    if (canonicalJson(existing) !== canonicalJson(event)) {
      throw new Error(`eventId ${event.eventId} 已存在但内容不同`);
    }
    return { appended: false, state };
  }

  const nextState = replayRuntimeEvents([...events, event]);
  const projectionTemp = await createProjectionTemp(runDir, nextState);
  try {
    const eventsHandle = await open(path.join(runDir, 'events.jsonl'), 'a');
    try {
      await eventsHandle.writeFile(`${canonicalJson(event)}\n`, 'utf8');
      await eventsHandle.sync();
    } finally {
      await eventsHandle.close();
    }
    await rename(projectionTemp, path.join(runDir, 'run.json'));
  } finally {
    await rm(projectionTemp, { force: true });
  }

  return { appended: true, state: nextState };
}

export async function recordSourcePlan({
  runDir,
  allowlist,
  confirmedDirtyPaths = [],
  metadata,
}) {
  await projectRootFromRunDir(runDir);
  const { state } = await assertProjectionMatchesEvents(runDir);
  const payload = prepareSourcePlan({
    source: state.source,
    allowlist,
    confirmedDirtyPaths,
    actor: metadata?.actor,
  });
  const { event } = createSourcePlanEvent(state, payload, metadata);
  return appendRuntimeEvent(runDir, event);
}

export async function verifySourceChanges(runDir) {
  const projectRoot = await projectRootFromRunDir(runDir);
  const { state } = await assertProjectionMatchesEvents(runDir);
  return verifySourceState({ projectRoot, source: state.source });
}

export async function recordWorkflowTransition(runDir, eventInput) {
  const { state } = await assertProjectionMatchesEvents(runDir);
  const { event } = createWorkflowEvent(state, eventInput);
  return appendRuntimeEvent(runDir, event);
}
