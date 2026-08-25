import assert from 'node:assert/strict';
import { access, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { addArtifact } from '../scripts/lib/artifact-ledger.mjs';
import { createFinalizationEvent } from '../scripts/lib/finalize-contract.mjs';
import { finalizeRun } from '../scripts/lib/finalize-store.mjs';
import {
  recordDeploymentPreflight,
  recordDeploymentPublish,
} from '../scripts/lib/deployment-store.mjs';
import { recordGateDecision } from '../scripts/lib/gate-store.mjs';
import {
  readCanonicalRubricBinding,
  recordReview,
} from '../scripts/lib/review-store.mjs';
import {
  initializeRun,
  reconcileRun,
  recordSourcePlan,
  recordWorkflowTransition,
} from '../scripts/lib/runtime-store.mjs';
import { assertTerminalTransitionAllowed } from '../scripts/lib/terminal-validator.mjs';
import {
  assertNoSensitiveContent,
  scanRunSensitiveFiles,
} from '../scripts/lib/sensitive-scan.mjs';
import {
  computeStateHash,
  createRunInitialization,
} from '../scripts/lib/state-contract.mjs';
import { validateRun } from '../scripts/lib/validators.mjs';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);

function initInput(runId, overrides = {}) {
  return {
    runId,
    intent: '验证 WebFlow run',
    projectRoot: '.',
    source: { mode: 'create', dir: 'site' },
    interactionMode: 'attended',
    profile: { requested: 'fast' },
    deployment: { requested: false, authorized: false, provider: null },
    ...overrides,
  };
}

async function temporaryProject(prefix = 'web-flow-validator-') {
  return mkdtemp(path.join(tmpdir(), prefix));
}

function rehash(state) {
  const copy = structuredClone(state);
  copy.stateHash = computeStateHash(copy);
  return copy;
}

test('sensitive scan rejects finite credential, user path, and private URL patterns while allowing public URLs and relative paths', () => {
  const rejected = [
    'Authorization: Bearer abc.def.ghi',
    'token = live-token-value',
    'api-key: abc123',
    'secret="hidden"',
    'password: hunter2',
    ['', 'Users', 'example', 'project', 'file.md'].join('/'),
    ['', 'home', 'example', 'project', 'file.md'].join('/'),
    'C:\\Users\\example\\project\\file.md',
    'http://localhost:3000',
    'http://127.0.0.1:8080',
    'http://10.1.2.3',
    'https://192.168.1.2/path',
    'http://172.16.0.1',
    'http://172.31.255.254',
    'https://service.local/path',
    JSON.stringify({ token: 'json-secret-value' }),
    JSON.stringify({ path: 'C:\\Users\\example\\project\\file.md' }),
  ];
  for (const value of rejected) {
    assert.throws(
      () => assertNoSensitiveContent(value, 'fixture.md'),
      /sensitive|Authorization|token|路径|private|URL|凭证/i,
    );
  }
  assert.doesNotThrow(() =>
    assertNoSensitiveContent(
      '公开地址 https://example.com/docs，文件 reviews/build/result.md，IP 8.8.8.8',
      'safe.md',
    ),
  );
});

test('validate-run scans machine state and Markdown, replays projection, validates ledger, and exposes a narrow CLI', async () => {
  const projectRoot = await temporaryProject();
  try {
    await assert.rejects(
      () =>
        initializeRun({
          projectRoot,
          input: initInput('20260712T155959Z-v0z0', {
            projectRoot: projectRoot,
          }),
          metadata: {
            eventId: 'evt-invalid-project-root',
            at: '2026-07-12T15:59:59.000Z',
            actor: 'web-flow-runtime',
          },
        }),
      /projectRoot.*\./,
    );
    await assert.rejects(() => access(path.join(projectRoot, '.web-flow')));
    const initialized = await initializeRun({
      projectRoot,
      input: initInput('20260712T160000Z-v1a1'),
      metadata: {
        eventId: 'evt-validator-init',
        at: '2026-07-12T16:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await writeFile(
      path.join(initialized.runDir, 'notes.md'),
      '公共 URL：https://example.com，证据路径 reviews/research.md\n',
    );
    assert.equal((await validateRun(initialized.runDir)).valid, true);
    assert.ok((await scanRunSensitiveFiles(initialized.runDir)).scanned >= 4);

    const cli = spawnSync(
      process.execPath,
      [runtimeCli.pathname, 'validate-run', initialized.runDir],
      { encoding: 'utf8' },
    );
    assert.equal(cli.status, 0, cli.stderr);
    assert.equal(JSON.parse(cli.stdout).valid, true);

    await writeFile(path.join(initialized.runDir, 'notes.md'), 'token = exposed\n');
    await assert.rejects(
      () => validateRun(initialized.runDir),
      /sensitive|token|凭证/i,
    );
    await writeFile(path.join(initialized.runDir, 'notes.md'), 'safe\n');

    const projectionPath = path.join(initialized.runDir, 'run.json');
    const projection = JSON.parse(await readFile(projectionPath, 'utf8'));
    await writeFile(
      projectionPath,
      `${JSON.stringify({ ...projection, intent: '手工漂移' }, null, 2)}\n`,
    );
    await assert.rejects(
      () => validateRun(initialized.runDir),
      /投影|events|事件|不一致/i,
    );
    await writeFile(projectionPath, `${JSON.stringify(projection, null, 2)}\n`);

    await writeFile(path.join(initialized.runDir, 'artifacts.jsonl'), '{broken}\n');
    await assert.rejects(
      () => validateRun(initialized.runDir),
      /artifact|JSON|ledger/i,
    );
    await writeFile(path.join(initialized.runDir, 'artifacts.jsonl'), '');
    await assert.rejects(
      () => validateRun(initialized.runDir, { requireTerminal: true }),
      /terminal|终态|finalize/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

async function setupBoundRun(runId = '20260712T163000Z-v2b2') {
  const projectRoot = await temporaryProject('web-flow-bound-validator-');
  const initialized = await initializeRun({
    projectRoot,
    input: initInput(runId, {
      deployment: {
        requested: true,
        authorized: true,
        provider: 'cloudflare-pages',
      },
    }),
    metadata: {
      eventId: `evt-init-${runId}`,
      at: '2026-07-12T16:30:00.000Z',
      actor: 'web-flow-runtime',
    },
  });
  await mkdir(path.join(projectRoot, 'site'), { recursive: true });
  let eventIndex = 0;
  const transition = async (type, payload) => {
    eventIndex += 1;
    return recordWorkflowTransition(initialized.runDir, {
      eventId: `evt-workflow-${eventIndex}-${runId}`,
      type,
      at: `2026-07-12T16:30:${String(eventIndex).padStart(2, '0')}.000Z`,
      actor: 'agent',
      payload,
    });
  };
  const reviewStage = async (
    stage,
    artifactId,
    relativePath,
    contents,
    attempt = 1,
  ) => {
    await writeFile(path.join(projectRoot, relativePath), contents);
    const artifact = await addArtifact({
      runDir: initialized.runDir,
      artifactId,
      artifactPath: relativePath,
      producer: stage,
      createdAt: `2026-07-12T16:31:${String(eventIndex).padStart(2, '0')}.000Z`,
    });
    const revision = artifact.artifact.revision;
    const reviewPath = `reviews/${stage}/attempt-${attempt}/round-1--${artifactId}-r${revision}.md`;
    await mkdir(path.dirname(path.join(initialized.runDir, reviewPath)), {
      recursive: true,
    });
    await writeFile(path.join(initialized.runDir, reviewPath), `# ${stage} review\n`);
    const review = await recordReview({
      runDir: initialized.runDir,
      stage,
      attempt,
      kind: 'subjective',
      round: 1,
      recheck: null,
      reviewer: 'independent-reviewer',
      independence: { independent: true, limitation: null },
      rubricRef: `web-flow-benchmark/references/rubrics.md#${stage}`,
      reviewPath,
      artifactRef: `${artifactId}@${revision}`,
      mustPass: 'passed',
      decision: 'pass',
      weightedScore: 4,
      metadata: {
        eventId: `evt-review-${stage}-${attempt}-${runId}`,
        at: `2026-07-12T16:32:${String(eventIndex).padStart(2, '0')}.000Z`,
        actor: 'independent-reviewer',
      },
    });
    return { artifact: artifact.artifact, reviewPath, review };
  };
  const gate = async (gateName, decision = 'approved', decisionNumber = 1) => {
    const decisionPath = `gates/${gateName}/decision-${decisionNumber}.md`;
    await mkdir(path.dirname(path.join(initialized.runDir, decisionPath)), {
      recursive: true,
    });
    await writeFile(path.join(initialized.runDir, decisionPath), `# ${gateName}\n`);
    const result = await recordGateDecision({
      runDir: initialized.runDir,
      gate: gateName,
      decision,
      decisionPath,
      metadata: {
        eventId: `evt-${gateName}-${decisionNumber}-${runId}`,
        at: `2026-07-12T16:33:${gateName === 'G1' ? '01' : '03'}.000Z`,
        actor: 'user',
      },
    });
    return { decisionPath, result };
  };

  await transition('stage_transition', { stage: 'research', to: 'running' });
  await reviewStage('research', 'research.spec', 'site/research.md', '# research\n');
  await transition('stage_transition', { stage: 'research', to: 'completed' });
  await transition('stage_transition', { stage: 'wireframe', to: 'running' });
  const wireframe = await reviewStage(
    'wireframe',
    'wireframe.preview',
    'site/wireframe.html',
    '<main>wireframe</main>',
  );
  await transition('stage_transition', { stage: 'wireframe', to: 'awaiting_gate' });
  const g1 = await gate('G1', 'revise', 1);
  await reviewStage(
    'wireframe',
    'wireframe.preview',
    'site/wireframe.html',
    '<main>wireframe revised</main>',
    2,
  );
  await transition('stage_transition', { stage: 'wireframe', to: 'awaiting_gate' });
  await gate('G1', 'approved', 2);
  await transition('profile_locked', { resolved: 'fast' });
  await transition('stage_transition', { stage: 'design', to: 'running' });
  await reviewStage('design', 'design.contract', 'site/design.css', ':root{}\n');
  await transition('stage_transition', { stage: 'design', to: 'completed' });
  await transition('stage_transition', { stage: 'build', to: 'running' });
  const build = await reviewStage(
    'build',
    'build.preview',
    'site/index.html',
    '<main>production</main>',
  );
  await transition('stage_transition', { stage: 'build', to: 'awaiting_gate' });
  const g3 = await gate('G3');
  await transition('stage_transition', { stage: 'deploy', to: 'running' });
  await mkdir(path.join(initialized.runDir, 'preflight'), { recursive: true });
  await mkdir(path.join(initialized.runDir, 'deploy'), { recursive: true });
  await writeFile(
    path.join(initialized.runDir, 'preflight', 'deployment-readiness.md'),
    '# ready\n',
  );
  await recordDeploymentPreflight({
    runDir: initialized.runDir,
    provider: 'cloudflare-pages',
    status: 'passed',
    checks: { cli: 'passed', identity: 'passed', project: 'passed' },
    metadata: {
      eventId: `evt-preflight-${runId}`,
      at: '2026-07-12T16:34:00.000Z',
      actor: 'web-flow-runtime',
    },
  });
  await writeFile(
    path.join(initialized.runDir, 'deploy', 'deployment-evidence.md'),
    '# deployed\n',
  );
  await recordDeploymentPublish({
    runDir: initialized.runDir,
    provider: 'cloudflare-pages',
    latePreflight: {
      rechecked: true,
      status: 'passed',
      at: '2026-07-12T16:34:01.000Z',
    },
    facts: { http: 'passed', browser: 'passed', console: 'passed' },
    productionUrl: 'https://example.test',
    status: 'success',
    metadata: {
      eventId: `evt-publish-${runId}`,
      at: '2026-07-12T16:34:02.000Z',
      actor: 'web-flow-runtime',
    },
  });
  await writeFile(
    path.join(projectRoot, 'site', 'deployment-result.md'),
    '# deployment result\n',
  );
  await addArtifact({
    runDir: initialized.runDir,
    artifactId: 'deploy.result',
    artifactPath: 'site/deployment-result.md',
    producer: 'deploy',
    createdAt: '2026-07-12T16:34:03.000Z',
  });
  const deployReviewPath =
    'reviews/deploy/attempt-1/round-1--deploy.result-r1.md';
  await mkdir(path.dirname(path.join(initialized.runDir, deployReviewPath)), {
    recursive: true,
  });
  await writeFile(
    path.join(initialized.runDir, deployReviewPath),
    '# deploy review\n',
  );
  await recordReview({
    runDir: initialized.runDir,
    stage: 'deploy',
    attempt: 1,
    kind: 'subjective',
    round: 1,
    recheck: null,
    reviewer: 'independent-reviewer',
    independence: { independent: true, limitation: null },
    rubricRef: 'web-flow-benchmark/references/rubrics.md#deploy',
    reviewPath: deployReviewPath,
    artifactRef: 'deploy.result@1',
    mustPass: 'passed',
    decision: 'pass',
    weightedScore: 4,
    metadata: {
      eventId: `evt-review-deploy-${runId}`,
      at: '2026-07-12T16:34:04.000Z',
      actor: 'independent-reviewer',
    },
  });
  await transition('stage_transition', { stage: 'deploy', to: 'completed' });
  return { projectRoot, runDir: initialized.runDir, wireframe, build, g1, g3 };
}

async function createTemporaryRubricPackage(projectRoot) {
  const packageRoot = path.join(projectRoot, 'rubric-package');
  const rubricPath = path.join(
    packageRoot,
    'web-flow-benchmark',
    'references',
    'rubrics.md',
  );
  const canonical = await readCanonicalRubricBinding();
  await mkdir(path.dirname(rubricPath), { recursive: true });
  await writeFile(rubricPath, canonical.contents);
  return { packageRoot, rubricPath };
}

test('validate-run rehashes the canonical rubric document on every call', async () => {
  const context = await setupBoundRun('20260712T163500Z-v2c2');
  try {
    const rubric = await createTemporaryRubricPackage(context.projectRoot);
    assert.equal(
      (await validateRun(context.runDir, { packageRoot: rubric.packageRoot })).valid,
      true,
    );
    await writeFile(rubric.rubricPath, '# drifted rubrics\n');
    await assert.rejects(
      () => validateRun(context.runDir, { packageRoot: rubric.packageRoot }),
      /rubric|rubrics\.md|hash|漂移/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('finalize rehashes the canonical rubric document before terminal append', async () => {
  const context = await setupBoundRun('20260712T163600Z-v2d2');
  try {
    const rubric = await createTemporaryRubricPackage(context.projectRoot);
    await writeFile(path.join(context.runDir, 'skill-usage.md'), '# usage\n');
    await writeFile(path.join(context.runDir, 'retrospective.md'), '# retro\n');
    await writeFile(rubric.rubricPath, '# drifted rubrics\n');
    await assert.rejects(
      () =>
        finalizeRun({
          runDir: context.runDir,
          status: 'success',
          reason: 'rubric drift must block finalization',
          supersededBy: null,
          metadata: {
            eventId: 'evt-finalize-rubric-drift',
            at: '2026-07-12T16:36:59.000Z',
            actor: 'web-flow-runtime',
          },
        }, { packageRoot: rubric.packageRoot }),
      /rubric|rubrics\.md|hash|漂移/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('validate-run rechecks current review, gate, deployment documents and live artifact bindings', async () => {
  const context = await setupBoundRun();
  try {
    assert.equal((await validateRun(context.runDir)).valid, true);

    await writeFile(
      path.join(context.runDir, context.wireframe.reviewPath),
      '# review drift\n',
    );
    await assert.rejects(
      () => validateRun(context.runDir),
      /review.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.runDir, context.wireframe.reviewPath),
      '# wireframe review\n',
    );

    await writeFile(
      path.join(context.runDir, context.g1.decisionPath),
      '# gate drift\n',
    );
    await assert.rejects(
      () => validateRun(context.runDir),
      /gate|decision.*漂移|hash/i,
    );
    await writeFile(path.join(context.runDir, context.g1.decisionPath), '# G1\n');

    await writeFile(
      path.join(context.projectRoot, 'site', 'index.html'),
      '<main>artifact drift</main>',
    );
    await assert.rejects(
      () => validateRun(context.runDir),
      /artifact|build.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.projectRoot, 'site', 'index.html'),
      '<main>production</main>',
    );

    await writeFile(
      path.join(context.runDir, 'deploy', 'deployment-evidence.md'),
      '# deployment drift\n',
    );
    await assert.rejects(
      () => validateRun(context.runDir),
      /deployment|evidence.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.runDir, 'deploy', 'deployment-evidence.md'),
      '# deployed\n',
    );

    await rm(path.join(context.runDir, context.wireframe.reviewPath));
    await assert.rejects(
      () => validateRun(context.runDir),
      /review|ENOENT|不存在|no such file/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

function runGit(projectRoot, args) {
  const result = spawnSync('git', args, { cwd: projectRoot, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
}

test('validate-run invokes source verification for update runs with a recorded plan', async () => {
  const projectRoot = await temporaryProject('web-flow-update-validator-');
  try {
    runGit(projectRoot, ['init', '-q']);
    runGit(projectRoot, ['config', 'user.name', 'Validator Test']);
    runGit(projectRoot, ['config', 'user.email', 'validator@example.test']);
    await mkdir(path.join(projectRoot, 'src'));
    await writeFile(path.join(projectRoot, 'src', 'allowed.txt'), 'base');
    await writeFile(path.join(projectRoot, '.gitignore'), '.web-flow/\n');
    runGit(projectRoot, ['add', '.']);
    runGit(projectRoot, ['commit', '-qm', 'baseline']);

    const initialized = await initializeRun({
      projectRoot,
      input: initInput('20260712T170000Z-v3c3', {
        source: { mode: 'update', dir: 'src' },
      }),
      metadata: {
        eventId: 'evt-update-validator-init',
        at: '2026-07-12T17:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await recordSourcePlan({
      runDir: initialized.runDir,
      allowlist: ['src/allowed.txt'],
      metadata: {
        eventId: 'evt-update-validator-plan',
        at: '2026-07-12T17:00:01.000Z',
        actor: 'agent',
      },
    });
    await writeFile(path.join(projectRoot, 'src', 'allowed.txt'), 'allowed');
    assert.equal((await validateRun(initialized.runDir)).valid, true);
    await writeFile(path.join(projectRoot, 'outside.txt'), 'outside');
    await assert.rejects(
      () => validateRun(initialized.runDir),
      /outside\.txt|allowlist|越界/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

function terminalPayload(status, overrides = {}) {
  return {
    status,
    reason: `${status} reason`,
    supersededBy: null,
    skillUsage: { path: 'skill-usage.md', sha256: 'e'.repeat(64) },
    retrospective: { path: 'retrospective.md', sha256: 'f'.repeat(64) },
    ...overrides,
  };
}

function terminalReadyState(overrides = {}) {
  const state = createRunInitialization(
    initInput('20260712T173000Z-t1a1', {
      deployment: { requested: false, authorized: false, provider: null },
    }),
    {
      eventId: 'evt-terminal-init',
      at: '2026-07-12T17:30:00.000Z',
      actor: 'web-flow-runtime',
    },
  ).state;
  return rehash({
    ...state,
    currentStage: null,
    stages: {
      ...state.stages,
      build: { ...state.stages.build, status: 'completed' },
    },
    gates: {
      ...state.gates,
      G3: {
        decision: 'approved',
        decisionCount: 1,
        latestDecision: {
          artifactRef: 'build.preview@1',
          artifactSha256: 'a'.repeat(64),
        },
      },
    },
    resume: null,
    ...overrides,
  });
}

test('terminal matrix distinguishes success, partial, failed, cancelled, deployment, and supersession requirements', () => {
  const ready = terminalReadyState();
  assert.doesNotThrow(() =>
    assertTerminalTransitionAllowed(ready, terminalPayload('success'), 'web-flow-runtime'),
  );
  assert.throws(
    () =>
      assertTerminalTransitionAllowed(
        terminalReadyState({
          deployment: {
            requested: true,
            authorized: false,
            provider: 'cloudflare-pages',
            preflight: null,
            latestResult: null,
          },
        }),
        terminalPayload('success'),
        'web-flow-runtime',
      ),
    /deployment|authorized|partial/i,
  );
  assert.throws(
    () =>
      assertTerminalTransitionAllowed(
        ready,
        terminalPayload('partial', { reason: '' }),
        'web-flow-runtime',
      ),
    /partial|reason|说明/i,
  );
  assert.doesNotThrow(() =>
    assertTerminalTransitionAllowed(
      initializedStateForTerminalFailure(),
      terminalPayload('failed'),
      'web-flow-runtime',
    ),
  );
  assert.doesNotThrow(() =>
    assertTerminalTransitionAllowed(
      initializedStateForTerminalFailure(),
      terminalPayload('cancelled'),
      'user',
    ),
  );
  assert.throws(
    () =>
      assertTerminalTransitionAllowed(
        initializedStateForTerminalFailure(),
        terminalPayload('cancelled'),
        'agent',
      ),
    /cancelled|actor=user|pendingTerminal/i,
  );
  assert.doesNotThrow(() =>
    assertTerminalTransitionAllowed(
      ready,
      terminalPayload('partial', {
        supersededBy: '20260712T180000Z-t2b2',
      }),
      'web-flow-runtime',
    ),
  );
  assert.throws(
    () =>
      assertTerminalTransitionAllowed(
        ready,
        terminalPayload('success', {
          supersededBy: '20260712T180000Z-t2b2',
        }),
        'web-flow-runtime',
      ),
    /supersededBy|partial|cancelled/i,
  );
});

function initializedStateForTerminalFailure() {
  return createRunInitialization(
    initInput('20260712T174000Z-t3c3'),
    {
      eventId: 'evt-terminal-failure-init',
      at: '2026-07-12T17:40:00.000Z',
      actor: 'web-flow-runtime',
    },
  ).state;
}

test('finalize appends one terminal event, validates fixed documents, and reconciles an event-ahead snapshot', async () => {
  const context = await setupBoundRun('20260712T180000Z-t4d4');
  try {
    await writeFile(path.join(context.runDir, 'skill-usage.md'), '# usage\n');
    await writeFile(
      path.join(context.runDir, 'retrospective.md'),
      '# retrospective\n',
    );
    const preFinalProjection = await readFile(
      path.join(context.runDir, 'run.json'),
      'utf8',
    );
    const finalized = await finalizeRun({
      runDir: context.runDir,
      status: 'success',
      reason: '授权范围已完成',
      supersededBy: null,
      metadata: {
        eventId: 'evt-finalize-success',
        at: '2026-07-12T18:00:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    assert.equal(finalized.state.status, 'success');
    assert.equal(finalized.state.currentStage, null);
    assert.equal(finalized.state.resume, null);
    assert.equal(finalized.state.pendingTerminal, undefined);
    assert.equal(finalized.event.type, 'run_finalized');
    assert.equal(finalized.state.finalization.skillUsage.path, 'skill-usage.md');
    assert.equal(
      (await validateRun(context.runDir, { requireTerminal: true })).valid,
      true,
    );
    await assert.rejects(
      () =>
        finalizeRun({
          runDir: context.runDir,
          status: 'success',
          reason: '重复 finalize',
          supersededBy: null,
          metadata: {
            eventId: 'evt-finalize-again',
            at: '2026-07-12T18:00:01.000Z',
            actor: 'web-flow-runtime',
          },
        }),
      /terminal|finalized|不可/i,
    );

    await writeFile(path.join(context.runDir, 'run.json'), preFinalProjection);
    const reconciled = await reconcileRun(context.runDir);
    assert.equal(reconciled.status, 'success');
    assert.equal(
      (await validateRun(context.runDir, { requireTerminal: true })).valid,
      true,
    );

    await writeFile(
      path.join(context.runDir, 'retrospective.md'),
      '# drifted retrospective\n',
    );
    await assert.rejects(
      () => validateRun(context.runDir, { requireTerminal: true }),
      /retrospective|finalization.*漂移|hash/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('finalize CLI supports failed without preview and runtime-cancelled gate rejection only', async () => {
  const projectRoot = await temporaryProject('web-flow-finalize-cli-');
  const inputPath = path.join(projectRoot, 'finalize-input.json');
  try {
    const initialized = await initializeRun({
      projectRoot,
      input: initInput('20260712T183000Z-t5e5'),
      metadata: {
        eventId: 'evt-finalize-cli-init',
        at: '2026-07-12T18:30:00.000Z',
        actor: 'web-flow-runtime',
      },
    });
    await writeFile(path.join(initialized.runDir, 'skill-usage.md'), '# usage\n');
    await writeFile(path.join(initialized.runDir, 'retrospective.md'), '# retro\n');
    await writeFile(
      inputPath,
      JSON.stringify({
        status: 'failed',
        reason: '没有可交付结果',
        supersededBy: null,
        metadata: {
          eventId: 'evt-finalize-failed',
          at: '2026-07-12T18:30:01.000Z',
          actor: 'web-flow-runtime',
        },
      }),
    );
    const result = spawnSync(
      process.execPath,
      [runtimeCli.pathname, 'finalize', initialized.runDir, '--input-file', inputPath],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).state.status, 'failed');
    assert.equal(
      (await validateRun(initialized.runDir, { requireTerminal: true })).valid,
      true,
    );

    const rejectedState = rehash({
      ...initializedStateForTerminalFailure(),
      status: 'blocked',
      pendingTerminal: 'cancelled',
      resume: { stage: 'wireframe', action: 'finalize_cancelled' },
    });
    assert.doesNotThrow(() =>
      createFinalizationEvent(
        rejectedState,
        terminalPayload('cancelled'),
        {
          eventId: 'evt-runtime-cancelled',
          at: '2026-07-12T18:31:00.000Z',
          actor: 'web-flow-runtime',
        },
      ),
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});
