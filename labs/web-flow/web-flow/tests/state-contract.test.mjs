import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import {
  SAFE_RUN_ID_PATTERN,
  canonicalJson,
  computeStateHash,
  createRunInitialization,
  createSourcePlanEvent,
  replayEvents,
} from '../scripts/lib/state-contract.mjs';
import {
  appendRuntimeEvent,
  assertProjectionMatchesEvents,
  initializeRun,
  recordSourcePlan,
  recordWorkflowTransition,
  reconcileRun,
  verifySourceChanges,
} from '../scripts/lib/runtime-store.mjs';
import { captureGitBaseline } from '../scripts/lib/source-safety.mjs';
import {
  assertSupersessionAllowed,
  createWorkflowEvent,
  workflowEventReducer,
} from '../scripts/lib/workflow-contract.mjs';

const runtimeCli = new URL(
  '../scripts/web-flow-runtime.mjs',
  import.meta.url,
);

const initializationInput = {
  runId: '20260711T120000Z-a1b2',
  intent: '制作产品落地页',
  projectRoot: '.',
  source: { mode: 'create', dir: 'site' },
  interactionMode: 'attended',
  profile: { requested: 'adaptive' },
  deployment: { requested: false, authorized: false, provider: null },
};

const eventMetadata = {
  eventId: 'evt-run-initialized',
  at: '2026-07-11T12:00:00.000Z',
  actor: 'web-flow-runtime',
};

test('initialization creates a safe run id and the first typed event', () => {
  const { event, state } = createRunInitialization(
    initializationInput,
    eventMetadata,
  );

  assert.match(state.runId, SAFE_RUN_ID_PATTERN);
  assert.equal(event.type, 'run_initialized');
  assert.equal(event.sequence, 1);
  assert.equal(event.beforeStateHash, null);
  assert.equal(event.afterStateHash, state.stateHash);
  assert.equal(state.eventSequence, 1);
  assert.equal(event.payload.runId, initializationInput.runId);
  assert.deepEqual(event.payload.source, initializationInput.source);
});

test('initialization rejects an unsafe run id', () => {
  assert.throws(
    () =>
      createRunInitialization(
        { ...initializationInput, runId: '../escape' },
        eventMetadata,
      ),
    /run id/i,
  );
});

test('initialization rejects invalid enums and deployment combinations', () => {
  const invalidInputs = [
    {
      input: {
        ...initializationInput,
        source: { ...initializationInput.source, mode: 'patch' },
      },
      expected: /source\.mode/,
    },
    {
      input: { ...initializationInput, interactionMode: 'interactive' },
      expected: /interactionMode/,
    },
    {
      input: {
        ...initializationInput,
        profile: { requested: 'turbo' },
      },
      expected: /profile\.requested/,
    },
    {
      input: {
        ...initializationInput,
        deployment: {
          ...initializationInput.deployment,
          requested: 'false',
        },
      },
      expected: /deployment\.requested/,
    },
    {
      input: {
        ...initializationInput,
        deployment: {
          ...initializationInput.deployment,
          authorized: 1,
        },
      },
      expected: /deployment\.authorized/,
    },
    {
      input: {
        ...initializationInput,
        deployment: {
          ...initializationInput.deployment,
          provider: '',
        },
      },
      expected: /deployment\.provider/,
    },
    {
      input: {
        ...initializationInput,
        deployment: { requested: false, authorized: true, provider: null },
      },
      expected: /authorized.*requested/,
    },
  ];

  for (const { input, expected } of invalidInputs) {
    assert.throws(() => createRunInitialization(input, eventMetadata), expected);
  }
});

test('replay rebuilds the same projection from only the initialization event', () => {
  const { event, state } = createRunInitialization(
    initializationInput,
    eventMetadata,
  );

  assert.deepEqual(replayEvents([event]), state);
});

test('replay state hash uses canonical JSON without the stateHash field', () => {
  const { state } = createRunInitialization(initializationInput, eventMetadata);
  const { stateHash: _ignored, ...hashableState } = state;
  const expectedHash = createHash('sha256')
    .update(canonicalJson(hashableState))
    .digest('hex');

  assert.equal(
    canonicalJson({ z: 1, nested: { z: 2, a: 1 }, a: 2 }),
    '{"a":2,"nested":{"a":1,"z":2},"z":1}',
  );
  assert.equal(state.stateHash, expectedHash);
  assert.equal(computeStateHash({ ...state, stateHash: 'ignored' }), expectedHash);
});

test('replay rejects an unknown event type', () => {
  const { event } = createRunInitialization(initializationInput, eventMetadata);
  const unknownEvent = {
    ...event,
    sequence: 2,
    eventId: 'evt-unknown',
    type: 'unknown_event',
    beforeStateHash: event.afterStateHash,
  };

  assert.throws(() => replayEvents([event, unknownEvent]), /unknown event type/i);
});

test('replay rejects a sequence gap and a mismatched hash', () => {
  const { event } = createRunInitialization(initializationInput, eventMetadata);

  assert.throws(
    () => replayEvents([{ ...event, sequence: 2 }]),
    /sequence.*1/i,
  );
  assert.throws(
    () => replayEvents([{ ...event, afterStateHash: '0'.repeat(64) }]),
    /afterStateHash/i,
  );
});

test('replay validates every required event metadata field directly', () => {
  const { event } = createRunInitialization(initializationInput, eventMetadata);

  for (const field of ['eventId', 'at', 'actor']) {
    assert.throws(
      () => replayEvents([{ ...event, [field]: '' }]),
      new RegExp(`event\\.${field}.*非空`),
    );
  }
});

test('replay rejects non-JSON event values before reducing', () => {
  const { event } = createRunInitialization(initializationInput, eventMetadata);

  assert.throws(
    () => replayEvents([{ ...event, debug: () => undefined }]),
    /event.*合法 JSON/,
  );
});

async function createTemporaryProject(prefix = 'web-flow-runtime-') {
  return mkdtemp(path.join(tmpdir(), prefix));
}

function inputForRun(runId) {
  return { ...initializationInput, runId };
}

function metadataForRun(eventId, second = 0) {
  return {
    ...eventMetadata,
    eventId,
    at: `2026-07-11T12:00:0${second}.000Z`,
  };
}

function runGit(projectRoot, args) {
  const result = spawnSync('git', args, {
    cwd: projectRoot,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

async function initializeGitProject(projectRoot, files) {
  runGit(projectRoot, ['init', '-q']);
  runGit(projectRoot, ['config', 'user.name', 'Web Flow Test']);
  runGit(projectRoot, ['config', 'user.email', 'web-flow@example.test']);
  for (const [relativePath, contents] of Object.entries(files)) {
    const absolutePath = path.join(projectRoot, relativePath);
    await mkdir(path.dirname(absolutePath), { recursive: true });
    await writeFile(absolutePath, contents, 'utf8');
  }
  runGit(projectRoot, ['add', '.']);
  runGit(projectRoot, ['commit', '-qm', 'baseline']);
}

function updateInputForRun(runId, sourceDir = 'src') {
  return {
    ...inputForRun(runId),
    source: { mode: 'update', dir: sourceDir },
  };
}

test('runtime store init writes one event, an empty artifact ledger, and its projection', async () => {
  const projectRoot = await createTemporaryProject();

  try {
    const result = await initializeRun({
      projectRoot,
      input: initializationInput,
      metadata: eventMetadata,
    });
    const eventsText = await readFile(
      path.join(result.runDir, 'events.jsonl'),
      'utf8',
    );
    const events = eventsText
      .trimEnd()
      .split('\n')
      .map((line) => JSON.parse(line));
    const artifactsText = await readFile(
      path.join(result.runDir, 'artifacts.jsonl'),
      'utf8',
    );
    const storedProjection = JSON.parse(
      await readFile(path.join(result.runDir, 'run.json'), 'utf8'),
    );

    assert.equal(events.length, 1);
    assert.equal(events[0].type, 'run_initialized');
    assert.equal(artifactsText, '');
    assert.deepEqual(events[0], result.event);
    assert.deepEqual(storedProjection, result.state);
    assert.deepEqual(replayEvents(events), storedProjection);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('gitignore keeps original bytes and contains only one .web-flow entry after repeated init', async () => {
  const projectRoot = await createTemporaryProject('web-flow-gitignore-');
  const original = '# 用户原有内容\nnode_modules/';

  try {
    await writeFile(path.join(projectRoot, '.gitignore'), original, 'utf8');
    await initializeRun({
      projectRoot,
      input: inputForRun('20260711T120001Z-b2c3'),
      metadata: metadataForRun('evt-init-b2c3', 1),
    });
    await initializeRun({
      projectRoot,
      input: inputForRun('20260711T120002Z-c3d4'),
      metadata: metadataForRun('evt-init-c3d4', 2),
    });

    const gitignore = await readFile(path.join(projectRoot, '.gitignore'), 'utf8');
    const ignoredRuntimeEntries = gitignore
      .split(/\r?\n/u)
      .filter((line) => line.trim() === '.web-flow/');

    assert.ok(gitignore.startsWith(original));
    assert.equal(ignoredRuntimeEntries.length, 1);
    assert.equal(gitignore, `${original}\n.web-flow/\n`);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('reconcile rebuilds a deleted projection from the authoritative event log', async () => {
  const projectRoot = await createTemporaryProject('web-flow-reconcile-');

  try {
    const initialized = await initializeRun({
      projectRoot,
      input: inputForRun('20260711T120003Z-d4e5'),
      metadata: metadataForRun('evt-init-d4e5', 3),
    });
    const projectionPath = path.join(initialized.runDir, 'run.json');
    await unlink(projectionPath);

    const reconciled = await reconcileRun(initialized.runDir);
    const storedProjection = JSON.parse(await readFile(projectionPath, 'utf8'));

    assert.deepEqual(reconciled, initialized.state);
    assert.deepEqual(storedProjection, initialized.state);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('runtime store rejects ordinary writes when run.json was manually advanced or drifted', async () => {
  const projectRoot = await createTemporaryProject('web-flow-drift-');

  try {
    const initialized = await initializeRun({
      projectRoot,
      input: inputForRun('20260711T120004Z-e5f6'),
      metadata: metadataForRun('evt-init-e5f6', 4),
    });
    const projectionPath = path.join(initialized.runDir, 'run.json');
    const driftedProjection = {
      ...initialized.state,
      eventSequence: 2,
      intent: '手工改写的投影',
    };
    driftedProjection.stateHash = computeStateHash(driftedProjection);
    await writeFile(
      projectionPath,
      `${JSON.stringify(driftedProjection, null, 2)}\n`,
      'utf8',
    );

    await assert.rejects(
      () => assertProjectionMatchesEvents(initialized.runDir),
      /run\.json.*事件|投影.*不一致/i,
    );
    await assert.rejects(
      () => appendRuntimeEvent(initialized.runDir, initialized.event),
      /run\.json.*事件|投影.*不一致/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('idempotent event id returns the existing projection without appending', async () => {
  const projectRoot = await createTemporaryProject('web-flow-idempotent-');

  try {
    const initialized = await initializeRun({
      projectRoot,
      input: inputForRun('20260711T120005Z-f6g7'),
      metadata: metadataForRun('evt-init-f6g7', 5),
    });
    const repeated = await appendRuntimeEvent(
      initialized.runDir,
      initialized.event,
    );
    const eventLines = (
      await readFile(path.join(initialized.runDir, 'events.jsonl'), 'utf8')
    )
      .trimEnd()
      .split('\n');

    assert.equal(repeated.appended, false);
    assert.deepEqual(repeated.state, initialized.state);
    assert.equal(repeated.state.eventSequence, 1);
    assert.equal(eventLines.length, 1);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('runtime store CLI only routes init and reconcile to the disk layer', async () => {
  const projectRoot = await createTemporaryProject('web-flow-cli-');
  const inputPath = path.join(projectRoot, 'init-input.json');
  const metadataPath = path.join(projectRoot, 'event-metadata.json');

  try {
    const input = inputForRun('20260711T120006Z-g7h8');
    const metadata = metadataForRun('evt-init-g7h8', 6);
    await writeFile(inputPath, JSON.stringify(input), 'utf8');
    await writeFile(metadataPath, JSON.stringify(metadata), 'utf8');

    const init = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'init',
        projectRoot,
        '--input-file',
        inputPath,
        '--metadata-file',
        metadataPath,
      ],
      { encoding: 'utf8' },
    );
    assert.equal(init.status, 0, init.stderr);
    const initResult = JSON.parse(init.stdout);
    await unlink(path.join(initResult.runDir, 'run.json'));

    const reconcile = spawnSync(
      process.execPath,
      [runtimeCli.pathname, 'reconcile', initResult.runDir],
      { encoding: 'utf8' },
    );

    assert.equal(reconcile.status, 0, reconcile.stderr);
    assert.deepEqual(JSON.parse(reconcile.stdout), initResult.state);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('update init captures Git dirty hashes before changing ignore state and writes relative evidence', async () => {
  const projectRoot = await createTemporaryProject('web-flow-update-init-');

  try {
    await initializeGitProject(projectRoot, {
      '.gitignore': '# existing\n',
      'src/dirty.txt': 'committed',
      'src/deleted.txt': 'delete-me',
    });
    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-change');
    await unlink(path.join(projectRoot, 'src', 'deleted.txt'));
    await writeFile(path.join(projectRoot, 'src', 'untracked.txt'), 'new-file');

    const beforeInit = await captureGitBaseline(projectRoot);
    const initialized = await initializeRun({
      projectRoot,
      input: updateInputForRun('20260712T050000Z-h8i9'),
      metadata: {
        eventId: 'evt-update-init-h8i9',
        at: '2026-07-12T05:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    const baseline = initialized.event.payload.source.baseline;
    const dirtyByPath = new Map(
      baseline.dirty.map((entry) => [entry.path, entry]),
    );
    const evidence = await readFile(
      path.join(initialized.runDir, 'preexisting-state.md'),
      'utf8',
    );

    assert.deepEqual(baseline.dirty, beforeInit.dirty);
    assert.equal(dirtyByPath.get('src/dirty.txt').status, ' M');
    assert.equal(
      dirtyByPath.get('src/dirty.txt').sha256,
      createHash('sha256').update('local-change').digest('hex'),
    );
    assert.equal(dirtyByPath.get('src/deleted.txt').sha256, null);
    assert.equal(dirtyByPath.get('src/untracked.txt').status, '??');
    assert.equal(baseline.managed.length, 1);
    assert.equal(baseline.managed[0].path, '.gitignore');
    assert.deepEqual(initialized.state.source.baseline, baseline);
    assert.match(evidence, /src\/dirty\.txt/);
    assert.match(evidence, /src\/deleted\.txt/);
    assert.doesNotMatch(evidence, new RegExp(projectRoot.replaceAll('/', '\\/')));
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('update init rejects a non-Git project before writing .gitignore', async () => {
  const projectRoot = await createTemporaryProject('web-flow-update-nongit-');

  try {
    await mkdir(path.join(projectRoot, 'src'));
    await assert.rejects(() => captureGitBaseline(projectRoot), /Git/i);
    await assert.rejects(
      () =>
        initializeRun({
          projectRoot,
          input: updateInputForRun('20260712T051000Z-i9j0'),
          metadata: {
            eventId: 'evt-update-init-i9j0',
            at: '2026-07-12T05:10:00.000Z',
            actor: 'web-flow-runtime',
          },
        }),
      /Git/i,
    );
    await assert.rejects(
      () => readFile(path.join(projectRoot, '.gitignore'), 'utf8'),
      { code: 'ENOENT' },
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('source plan records one typed canonical allowlist and requires exact user confirmation for dirty overlap', async () => {
  const projectRoot = await createTemporaryProject('web-flow-source-plan-');

  try {
    await initializeGitProject(projectRoot, {
      '.gitignore': '.web-flow/\n',
      'src/dirty.txt': 'committed',
      'src/clean.txt': 'clean',
    });
    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-v1');
    const initialized = await initializeRun({
      projectRoot,
      input: updateInputForRun('20260712T060000Z-j0k1'),
      metadata: {
        eventId: 'evt-source-init-j0k1',
        at: '2026-07-12T06:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });

    await assert.rejects(
      () =>
        recordSourcePlan({
          runDir: initialized.runDir,
          allowlist: ['.'],
          metadata: {
            eventId: 'evt-root-plan',
            at: '2026-07-12T06:00:01.000Z',
            actor: 'user',
          },
        }),
      /项目根|allowlist|\./i,
    );
    await assert.rejects(
      () =>
        recordSourcePlan({
          runDir: initialized.runDir,
          allowlist: ['src/dirty.txt'],
          metadata: {
            eventId: 'evt-unconfirmed-plan',
            at: '2026-07-12T06:00:02.000Z',
            actor: 'agent',
          },
        }),
      /dirty|冲突|确认/i,
    );
    await assert.rejects(
      () =>
        recordSourcePlan({
          runDir: initialized.runDir,
          allowlist: ['src/dirty.txt'],
          confirmedDirtyPaths: ['src/dirty.txt'],
          metadata: {
            eventId: 'evt-agent-confirmed-plan',
            at: '2026-07-12T06:00:03.000Z',
            actor: 'agent',
          },
        }),
      /actor|user|确认/i,
    );

    const planned = await recordSourcePlan({
      runDir: initialized.runDir,
      allowlist: ['src/dirty.txt', './src/new.txt'],
      confirmedDirtyPaths: ['src/dirty.txt'],
      metadata: {
        eventId: 'evt-user-confirmed-plan',
        at: '2026-07-12T06:00:04.000Z',
        actor: 'user',
      },
    });
    const events = (
      await readFile(path.join(initialized.runDir, 'events.jsonl'), 'utf8')
    )
      .trimEnd()
      .split('\n')
      .map((line) => JSON.parse(line));

    assert.equal(events.length, 2);
    assert.equal(events[1].type, 'source_plan_recorded');
    assert.deepEqual(planned.state.source.plan.allowlist, [
      'src/dirty.txt',
      'src/new.txt',
    ]);
    assert.deepEqual(planned.state.source.plan.confirmedDirtyPaths, [
      'src/dirty.txt',
    ]);

    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'user-approved');
    assert.equal((await verifySourceChanges(initialized.runDir)).valid, true);
    await writeFile(path.join(projectRoot, 'outside.txt'), 'outside');
    await assert.rejects(
      () => verifySourceChanges(initialized.runDir),
      /outside\.txt|allowlist|越界/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('source plan reducer independently rejects an incomplete dirty confirmation', () => {
  const input = {
    ...initializationInput,
    source: {
      mode: 'update',
      dir: 'src',
      baseline: {
        dirty: [
          { path: 'src/dirty.txt', status: ' M', sha256: 'a'.repeat(64) },
        ],
        managed: [],
      },
    },
  };
  const { state } = createRunInitialization(input, eventMetadata);

  assert.throws(
    () =>
      createSourcePlanEvent(
        state,
        { allowlist: ['src/dirty.txt'], confirmedDirtyPaths: [] },
        {
          eventId: 'evt-forged-source-plan',
          at: '2026-07-12T06:30:00.000Z',
          actor: 'user',
        },
      ),
    /confirmedDirtyPaths|精确|dirty/i,
  );
});

test('source verify rejects unauthorized dirty drift or restoration and changes outside allowlist', async () => {
  const projectRoot = await createTemporaryProject('web-flow-source-verify-');

  try {
    await initializeGitProject(projectRoot, {
      '.gitignore': '.web-flow/\n',
      'src/dirty.txt': 'committed',
      'src/allowed.txt': 'clean',
    });
    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-v1');
    const initialized = await initializeRun({
      projectRoot,
      input: updateInputForRun('20260712T070000Z-k1l2'),
      metadata: {
        eventId: 'evt-verify-init-k1l2',
        at: '2026-07-12T07:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await recordSourcePlan({
      runDir: initialized.runDir,
      allowlist: ['src/allowed.txt'],
      metadata: {
        eventId: 'evt-verify-plan-k1l2',
        at: '2026-07-12T07:00:01.000Z',
        actor: 'agent',
      },
    });

    await writeFile(path.join(projectRoot, 'src', 'allowed.txt'), 'allowed');
    assert.equal((await verifySourceChanges(initialized.runDir)).valid, true);

    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-v2');
    await assert.rejects(
      () => verifySourceChanges(initialized.runDir),
      /dirty\.txt|hash|未确认/i,
    );
    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-v1');
    assert.equal((await verifySourceChanges(initialized.runDir)).valid, true);

    runGit(projectRoot, ['checkout', '--', 'src/dirty.txt']);
    await assert.rejects(
      () => verifySourceChanges(initialized.runDir),
      /dirty\.txt|恢复|未确认/i,
    );
    await writeFile(path.join(projectRoot, 'src', 'dirty.txt'), 'local-v1');
    await writeFile(path.join(projectRoot, 'outside.txt'), 'outside');
    await assert.rejects(
      () => verifySourceChanges(initialized.runDir),
      /outside\.txt|allowlist|越界/i,
    );
    await rm(path.join(projectRoot, 'outside.txt'));
    assert.equal((await verifySourceChanges(initialized.runDir)).valid, true);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('source verify accepts only the exact runtime-managed gitignore snapshot when gitignore was already dirty', async () => {
  const projectRoot = await createTemporaryProject('web-flow-managed-ignore-');

  try {
    await initializeGitProject(projectRoot, {
      '.gitignore': '# committed\n',
      'src/allowed.txt': 'clean',
    });
    await writeFile(
      path.join(projectRoot, '.gitignore'),
      '# committed\n# local user note\n',
    );
    const initialized = await initializeRun({
      projectRoot,
      input: updateInputForRun('20260712T073000Z-m3n4'),
      metadata: {
        eventId: 'evt-managed-ignore-init-m3n4',
        at: '2026-07-12T07:30:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await recordSourcePlan({
      runDir: initialized.runDir,
      allowlist: ['src/allowed.txt'],
      metadata: {
        eventId: 'evt-managed-ignore-plan-m3n4',
        at: '2026-07-12T07:30:01.000Z',
        actor: 'agent',
      },
    });

    assert.equal((await verifySourceChanges(initialized.runDir)).valid, true);
    await writeFile(
      path.join(projectRoot, '.gitignore'),
      '# committed\n# local user note\n.web-flow/\n# changed later\n',
    );
    await assert.rejects(
      () => verifySourceChanges(initialized.runDir),
      /\.gitignore|hash|未确认/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('runtime CLI routes source plan and source verify', async () => {
  const projectRoot = await createTemporaryProject('web-flow-source-cli-');

  try {
    await initializeGitProject(projectRoot, {
      '.gitignore': '.web-flow/\n',
      'src/allowed.txt': 'clean',
    });
    const initialized = await initializeRun({
      projectRoot,
      input: updateInputForRun('20260712T080000Z-l2m3'),
      metadata: {
        eventId: 'evt-cli-source-init-l2m3',
        at: '2026-07-12T08:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    const plan = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'source',
        'plan',
        initialized.runDir,
        '--allow',
        'src/allowed.txt',
        '--event-id',
        'evt-cli-source-plan-l2m3',
        '--at',
        '2026-07-12T08:00:01.000Z',
        '--actor',
        'agent',
      ],
      { encoding: 'utf8' },
    );
    assert.equal(plan.status, 0, plan.stderr);

    await writeFile(path.join(projectRoot, 'src', 'allowed.txt'), 'changed');
    const verify = spawnSync(
      process.execPath,
      [runtimeCli.pathname, 'source', 'verify', initialized.runDir],
      { encoding: 'utf8' },
    );

    assert.equal(verify.status, 0, verify.stderr);
    assert.equal(JSON.parse(verify.stdout).valid, true);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

function rehashState(state) {
  const next = structuredClone(state);
  next.stateHash = computeStateHash(next);
  return next;
}

function approvedG1State(requested = 'adaptive') {
  const { state } = createRunInitialization(
    {
      ...initializationInput,
      profile: { requested },
    },
    eventMetadata,
  );
  return rehashState({
    ...state,
    currentStage: 'wireframe',
    stages: {
      ...state.stages,
      research: { status: 'completed' },
      wireframe: { status: 'completed' },
    },
    gates: {
      ...state.gates,
      G1: { decision: 'approved' },
    },
    resume: null,
  });
}

function approvedG3State(overrides = {}) {
  const state = approvedG1State('adaptive');
  return rehashState({
    ...state,
    currentStage: 'build',
    profile: {
      ...state.profile,
      resolved: 'fast',
      lockedAt: '2026-07-12T09:00:00.000Z',
    },
    stages: {
      ...state.stages,
      prototype: { status: 'skipped' },
      design: { status: 'completed' },
      build: { status: 'completed' },
    },
    gates: {
      ...state.gates,
      G2: { decision: 'not_applicable' },
      G3: { decision: 'approved' },
    },
    resume: null,
    ...overrides,
  });
}

function createTypedWorkflowEvent(
  state,
  type,
  payload,
  {
    eventId = `evt-${type}-${state.eventSequence + 1}`,
    actor = 'agent',
    at = '2026-07-12T09:00:01.000Z',
  } = {},
) {
  return createWorkflowEvent(state, {
    eventId,
    type,
    at,
    actor,
    payload,
  });
}

test('stage transitions initialize all stages and enforce legal edges, gates, blocking, and terminal immutability', () => {
  const initialized = createRunInitialization(
    initializationInput,
    eventMetadata,
  );
  assert.deepEqual(Object.keys(initialized.state.stages), [
    'research',
    'wireframe',
    'prototype',
    'design',
    'build',
    'deploy',
  ]);
  assert.deepEqual(Object.keys(initialized.state.gates), ['G1', 'G2', 'G3']);

  const researchRunning = createTypedWorkflowEvent(
    initialized.state,
    'stage_transition',
    { stage: 'research', to: 'running' },
  );
  assert.equal(researchRunning.state.stages.research.status, 'running');
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        initialized.state,
        'stage_transition',
        { stage: 'research', to: 'skipped' },
      ),
    /skipped|profile_locked|跳过/i,
  );
  assert.deepEqual(
    replayEvents(
      [initialized.event, researchRunning.event],
      workflowEventReducer,
    ),
    researchRunning.state,
  );

  assert.throws(
    () =>
      createTypedWorkflowEvent(
        researchRunning.state,
        'stage_transition',
        { stage: 'research', to: 'completed' },
      ),
    /latestReview|review|mustPass/i,
  );
  const reviewedResearch = rehashState({
    ...researchRunning.state,
    stages: {
      ...researchRunning.state.stages,
      research: {
        ...researchRunning.state.stages.research,
        latestReview: {
          kind: 'subjective',
          attempt: 1,
          mustPass: 'passed',
          decision: 'pass',
        },
        subjectiveRound: 1,
      },
    },
  });
  const researchCompleted = createTypedWorkflowEvent(
    reviewedResearch,
    'stage_transition',
    { stage: 'research', to: 'completed' },
  );
  assert.equal(researchCompleted.state.currentStage, 'wireframe');
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        researchCompleted.state,
        'stage_transition',
        { stage: 'research', to: 'running' },
      ),
    /completed|终态|迁移/i,
  );

  const wireframeRunning = createTypedWorkflowEvent(
    researchCompleted.state,
    'stage_transition',
    { stage: 'wireframe', to: 'running' },
  );
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        wireframeRunning.state,
        'stage_transition',
        { stage: 'wireframe', to: 'completed' },
      ),
    /awaiting_gate|gate/i,
  );
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        wireframeRunning.state,
        'stage_transition',
        { stage: 'wireframe', to: 'awaiting_gate' },
      ),
    /latestReview|review|mustPass/i,
  );
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        wireframeRunning.state,
        'stage_transition',
        { stage: 'wireframe', to: 'blocked' },
      ),
    /resume/i,
  );

  const blocked = createTypedWorkflowEvent(
    wireframeRunning.state,
    'stage_transition',
    {
      stage: 'wireframe',
      to: 'blocked',
      resume: { stage: 'wireframe', action: '补充素材' },
    },
  );
  assert.equal(blocked.state.status, 'blocked');
  assert.equal(blocked.state.resume.action, '补充素材');
  const resumed = createTypedWorkflowEvent(
    blocked.state,
    'stage_transition',
    { stage: 'wireframe', to: 'running' },
  );
  assert.equal(resumed.state.status, 'running');
  assert.equal(resumed.state.resume, null);

  const deployReady = rehashState({
    ...approvedG3State(),
    currentStage: 'deploy',
    resume: { stage: 'deploy', action: 'start' },
  });
  const deployRunning = createTypedWorkflowEvent(
    deployReady,
    'stage_transition',
    { stage: 'deploy', to: 'running' },
  );
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        deployRunning.state,
        'stage_transition',
        { stage: 'deploy', to: 'completed' },
      ),
    /latestReview|review|mustPass/i,
  );
  const reviewedDeploy = rehashState({
    ...deployRunning.state,
    stages: {
      ...deployRunning.state.stages,
      deploy: {
        ...deployRunning.state.stages.deploy,
        latestReview: {
          kind: 'subjective',
          attempt: 1,
          mustPass: 'passed',
          decision: 'proceed_with_residual',
        },
        subjectiveRound: 1,
      },
    },
  });
  const deployCompleted = createTypedWorkflowEvent(
    reviewedDeploy,
    'stage_transition',
    { stage: 'deploy', to: 'completed' },
  );
  assert.equal(deployCompleted.state.currentStage, null);
  assert.equal(deployCompleted.state.resume, null);

  const terminal = rehashState({ ...resumed.state, status: 'partial' });
  assert.throws(
    () =>
      createTypedWorkflowEvent(terminal, 'stage_transition', {
        stage: 'wireframe',
        to: 'awaiting_gate',
      }),
    /terminal|终态|partial/i,
  );
});

test('profiles lock only after G1 and route fast or full without inserting prototype later', () => {
  const ready = approvedG1State('adaptive');
  const fast = createTypedWorkflowEvent(ready, 'profile_locked', {
    resolved: 'fast',
  });
  assert.equal(fast.state.profile.resolved, 'fast');
  assert.equal(fast.state.stages.prototype.status, 'skipped');
  assert.equal(fast.state.gates.G2.decision, 'not_applicable');
  assert.equal(fast.state.currentStage, 'design');

  const full = createTypedWorkflowEvent(ready, 'profile_locked', {
    resolved: 'full',
  });
  assert.equal(full.state.profile.resolved, 'full');
  assert.equal(full.state.stages.prototype.status, 'not_started');
  assert.equal(full.state.gates.G2.decision, 'pending');
  assert.equal(full.state.currentStage, 'prototype');

  const beforeG1 = createRunInitialization(
    initializationInput,
    eventMetadata,
  ).state;
  assert.throws(
    () =>
      createTypedWorkflowEvent(beforeG1, 'profile_locked', {
        resolved: 'fast',
      }),
    /G1|wireframe/i,
  );
  const designStarted = rehashState({
    ...ready,
    stages: { ...ready.stages, design: { status: 'running' } },
  });
  assert.throws(
    () =>
      createTypedWorkflowEvent(designStarted, 'profile_locked', {
        resolved: 'fast',
      }),
    /design|锁定/i,
  );
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        approvedG1State('fast'),
        'profile_locked',
        { resolved: 'full' },
      ),
    /requested|fast|匹配/i,
  );
});

test('supersession allows cancellation without preview but partial requires completed build and approved G3', () => {
  const initial = createRunInitialization(
    initializationInput,
    eventMetadata,
  ).state;
  assert.equal(
    assertSupersessionAllowed(
      initial,
      'cancelled',
      '20260712T100000Z-b2c3',
    ),
    true,
  );
  assert.throws(
    () =>
      assertSupersessionAllowed(
        initial,
        'partial',
        '20260712T100000Z-b2c3',
      ),
    /build|G3|preview/i,
  );
  assert.equal(
    assertSupersessionAllowed(
      approvedG3State(),
      'partial',
      '20260712T100000Z-b2c3',
    ),
    true,
  );
  assert.throws(
    () => assertSupersessionAllowed(initial, 'cancelled', initial.runId),
    /自身|same|runId/i,
  );
  assert.throws(
    () => assertSupersessionAllowed(initial, 'cancelled', '../escape'),
    /run id|runId|安全/i,
  );
});

test('deployment authorization requires an explicit user event after G3 and before terminal state', () => {
  const requestedInput = {
    ...initializationInput,
    interactionMode: 'unattended',
    deployment: { requested: true, authorized: false, provider: null },
  };
  const beforeG3 = createRunInitialization(requestedInput, eventMetadata).state;
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        beforeG3,
        'deployment_authorization_changed',
        { authorized: true, provider: 'cloudflare-pages' },
        { actor: 'user' },
      ),
    /G3|build/i,
  );

  const ready = approvedG3State({
    interactionMode: 'unattended',
    deployment: { requested: true, authorized: false, provider: null },
  });
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        ready,
        'deployment_authorization_changed',
        { authorized: true, provider: 'cloudflare-pages' },
        { actor: 'agent' },
      ),
    /actor=user|用户/i,
  );
  const authorized = createTypedWorkflowEvent(
    ready,
    'deployment_authorization_changed',
    { authorized: true, provider: 'cloudflare-pages' },
    { actor: 'user' },
  );
  assert.equal(authorized.state.deployment.authorized, true);
  assert.equal(authorized.state.deployment.provider, 'cloudflare-pages');
  assert.equal(authorized.state.currentStage, 'deploy');

  const blockedReady = rehashState({
    ...ready,
    status: 'blocked',
    resume: { stage: 'build', action: '等待用户授权部署' },
  });
  const authorizedFromBlocked = createTypedWorkflowEvent(
    blockedReady,
    'deployment_authorization_changed',
    { authorized: true, provider: 'cloudflare-pages' },
    { actor: 'user' },
  );
  assert.equal(authorizedFromBlocked.state.status, 'running');
  assert.deepEqual(authorizedFromBlocked.state.resume, {
    stage: 'deploy',
    action: 'start',
  });

  const terminal = rehashState({ ...ready, status: 'partial' });
  assert.throws(
    () =>
      createTypedWorkflowEvent(
        terminal,
        'deployment_authorization_changed',
        { authorized: true, provider: 'cloudflare-pages' },
        { actor: 'user' },
      ),
    /terminal|终态|partial/i,
  );
});

test('stage transitions are persisted through the narrow transition CLI', async () => {
  const projectRoot = await createTemporaryProject('web-flow-transition-cli-');
  const eventPath = path.join(projectRoot, 'transition.json');

  try {
    const initialized = await initializeRun({
      projectRoot,
      input: inputForRun('20260712T110000Z-c3d4'),
      metadata: {
        eventId: 'evt-transition-init-c3d4',
        at: '2026-07-12T11:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await writeFile(
      eventPath,
      JSON.stringify({
        eventId: 'evt-research-running-c3d4',
        type: 'stage_transition',
        at: '2026-07-12T11:00:01.000Z',
        actor: 'agent',
        payload: { stage: 'research', to: 'running' },
      }),
      'utf8',
    );

    const transition = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'transition',
        initialized.runDir,
        '--event-file',
        eventPath,
      ],
      { encoding: 'utf8' },
    );
    assert.equal(transition.status, 0, transition.stderr);
    assert.equal(
      JSON.parse(transition.stdout).state.stages.research.status,
      'running',
    );
    assert.equal(
      (await assertProjectionMatchesEvents(initialized.runDir)).state.stages
        .research.status,
      'running',
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});
