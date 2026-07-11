import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { addArtifact } from '../scripts/lib/artifact-ledger.mjs';
import {
  createDeploymentEvent,
  deploymentEventReducer,
} from '../scripts/lib/deployment-contract.mjs';
import {
  recordDeploymentPreflight,
  recordDeploymentPublish,
} from '../scripts/lib/deployment-store.mjs';
import { recordGateDecision } from '../scripts/lib/gate-store.mjs';
import { recordReview } from '../scripts/lib/review-store.mjs';
import {
  assertProjectionMatchesEvents,
  initializeRun,
  recordWorkflowTransition,
} from '../scripts/lib/runtime-store.mjs';
import {
  computeStateHash,
  createRunInitialization,
} from '../scripts/lib/state-contract.mjs';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);
const SHA = 'a'.repeat(64);

function rehash(state) {
  const copy = structuredClone(state);
  copy.stateHash = computeStateHash(copy);
  return copy;
}

function initializationInput(overrides = {}) {
  return {
    runId: '20260712T150000Z-d1p1',
    intent: '部署站点',
    projectRoot: '.',
    source: { mode: 'create', dir: 'site' },
    interactionMode: 'attended',
    profile: { requested: 'fast' },
    deployment: {
      requested: true,
      authorized: true,
      provider: 'cloudflare-pages',
    },
    ...overrides,
  };
}

function initializedState(overrides = {}) {
  return createRunInitialization(initializationInput(overrides), {
    eventId: 'evt-deploy-init',
    at: '2026-07-12T15:00:00.000Z',
    actor: 'web-flow-runtime',
  }).state;
}

function deploymentReadyState(overrides = {}) {
  const state = initializedState();
  return rehash({
    ...state,
    currentStage: 'deploy',
    stages: {
      ...state.stages,
      build: { ...state.stages.build, status: 'completed' },
      deploy: { ...state.stages.deploy, status: 'running' },
    },
    gates: {
      ...state.gates,
      G3: {
        decision: 'approved',
        decisionCount: 1,
        latestDecision: {
          artifactRef: 'build.preview@1',
          artifactSha256: SHA,
        },
      },
    },
    resume: null,
    ...overrides,
  });
}

function eventMetadata(index = 1) {
  return {
    eventId: `evt-deployment-${index}`,
    at: `2026-07-12T15:00:0${index}.000Z`,
    actor: 'web-flow-runtime',
  };
}

function preflightPayload(overrides = {}) {
  return {
    provider: 'cloudflare-pages',
    evidencePath: 'preflight/deployment-readiness.md',
    evidenceSha256: SHA,
    status: 'passed',
    checks: { cli: 'passed', identity: 'passed', project: 'passed' },
    ...overrides,
  };
}

function publishPayload(overrides = {}) {
  return {
    provider: 'cloudflare-pages',
    evidencePath: 'deploy/deployment-evidence.md',
    evidenceSha256: SHA,
    buildRef: 'build.preview@1',
    buildSha256: SHA,
    latePreflight: {
      rechecked: true,
      status: 'passed',
      at: '2026-07-12T15:10:00.000Z',
    },
    facts: { http: 'passed', browser: 'passed', console: 'passed' },
    productionUrl: 'https://example.test',
    status: 'success',
    ...overrides,
  };
}

test('deploy preflight records one fixed evidence document only when deployment is requested and authorized', () => {
  const state = initializedState();
  const recorded = createDeploymentEvent(
    state,
    'preflight',
    preflightPayload(),
    eventMetadata(1),
  );
  assert.equal(recorded.event.type, 'deployment_preflight_recorded');
  assert.equal(recorded.state.deployment.preflight.status, 'passed');
  assert.equal(
    recorded.state.deployment.preflight.evidencePath,
    'preflight/deployment-readiness.md',
  );
  assert.throws(
    () =>
      createDeploymentEvent(
        recorded.state,
        'preflight',
        preflightPayload(),
        eventMetadata(2),
      ),
    /preflight.*一次|已登记|覆盖/i,
  );
  for (const invalid of [
    initializedState({
      deployment: { requested: false, authorized: false, provider: null },
    }),
    initializedState({
      deployment: {
        requested: true,
        authorized: false,
        provider: 'cloudflare-pages',
      },
    }),
  ]) {
    assert.throws(
      () =>
        createDeploymentEvent(
          invalid,
          'preflight',
          preflightPayload(),
          eventMetadata(3),
        ),
      /requested|authorized|授权/i,
    );
  }
  assert.throws(
    () =>
      createDeploymentEvent(
        state,
        'preflight',
        preflightPayload({
          provider: 'other-provider',
          checks: { cli: 'passed', identity: 'passed' },
        }),
        eventMetadata(4),
      ),
    /provider|project|checks/i,
  );
  for (const contradictory of [
    preflightPayload({
      status: 'passed',
      checks: { cli: 'failed', identity: 'passed', project: 'passed' },
    }),
    preflightPayload({
      status: 'failed',
      checks: { cli: 'passed', identity: 'passed', project: 'passed' },
    }),
  ]) {
    assert.throws(
      () =>
        createDeploymentEvent(
          state,
          'preflight',
          contradictory,
          eventMetadata(5),
        ),
      /preflight|checks|passed|failed/i,
    );
  }
});

test('deploy publish validates late preflight, three facts, HTTPS URL, and records success or blocked failure', () => {
  const state = deploymentReadyState();
  const success = createDeploymentEvent(
    state,
    'publish',
    publishPayload(),
    eventMetadata(1),
  );
  assert.equal(success.state.deployment.latestResult.status, 'success');
  assert.equal(success.state.stages.deploy.status, 'running');
  assert.equal(success.state.status, 'running');

  const failure = createDeploymentEvent(
    state,
    'publish',
    publishPayload({
      status: 'failed',
      productionUrl: null,
      facts: { http: 'failed', browser: 'passed', console: 'passed' },
    }),
    eventMetadata(2),
  );
  assert.equal(failure.state.deployment.latestResult.status, 'failed');
  assert.equal(failure.state.stages.deploy.status, 'blocked');
  assert.equal(failure.state.status, 'blocked');
  assert.deepEqual(failure.state.resume, {
    stage: 'deploy',
    action: 'finalize_partial',
  });

  const invalidPayloads = [
    publishPayload({
      facts: { http: 'passed', browser: 'failed', console: 'passed' },
    }),
    publishPayload({ productionUrl: 'http://example.test' }),
    publishPayload({ latePreflight: { rechecked: false, status: 'passed', at: 'x' } }),
    publishPayload({
      status: 'failed',
      productionUrl: null,
      facts: { http: 'passed', browser: 'passed', console: 'passed' },
    }),
  ];
  for (const payload of invalidPayloads) {
    assert.throws(
      () => createDeploymentEvent(state, 'publish', payload, eventMetadata(3)),
      /facts|passed|https|latePreflight|failed/i,
    );
  }
});

async function setupPublishRun(runId = '20260712T153000Z-d2p2') {
  const projectRoot = await mkdtemp(path.join(tmpdir(), 'web-flow-deploy-'));
  const initialized = await initializeRun({
    projectRoot,
    input: initializationInput({ runId }),
    metadata: {
      eventId: `evt-init-${runId}`,
      at: '2026-07-12T15:30:00.000Z',
      actor: 'web-flow-runtime',
    },
  });
  await mkdir(path.join(projectRoot, 'site'), { recursive: true });
  let sequence = 0;

  const transition = async (type, payload) => {
    sequence += 1;
    return recordWorkflowTransition(initialized.runDir, {
      eventId: `evt-workflow-${sequence}-${runId}`,
      type,
      at: `2026-07-12T15:30:${String(sequence).padStart(2, '0')}.000Z`,
      actor: 'agent',
      payload,
    });
  };
  const reviewStage = async (stage, artifactId, relativePath, contents) => {
    await writeFile(path.join(projectRoot, relativePath), contents);
    const artifact = await addArtifact({
      runDir: initialized.runDir,
      artifactId,
      artifactPath: relativePath,
      producer: stage,
      createdAt: `2026-07-12T15:31:${String(sequence).padStart(2, '0')}.000Z`,
    });
    const reviewPath = `reviews/${stage}/attempt-1/round-1--${artifactId}-r${artifact.artifact.revision}.md`;
    await mkdir(path.dirname(path.join(initialized.runDir, reviewPath)), {
      recursive: true,
    });
    await writeFile(path.join(initialized.runDir, reviewPath), `# ${stage} review\n`);
    await recordReview({
      runDir: initialized.runDir,
      stage,
      attempt: 1,
      kind: 'subjective',
      round: 1,
      recheck: null,
      reviewer: 'independent-reviewer',
      independence: { independent: true, limitation: null },
      rubricRef: `web-flow-benchmark/references/rubrics.md#${stage}`,
      reviewPath,
      artifactRef: `${artifactId}@${artifact.artifact.revision}`,
      mustPass: 'passed',
      decision: 'pass',
      weightedScore: 4,
      metadata: {
        eventId: `evt-review-${stage}-${runId}`,
        at: `2026-07-12T15:32:${String(sequence).padStart(2, '0')}.000Z`,
        actor: 'independent-reviewer',
      },
    });
    return artifact.artifact;
  };
  const decideGate = async (gate, stage) => {
    const decisionPath = `gates/${gate}/decision-1.md`;
    await mkdir(path.dirname(path.join(initialized.runDir, decisionPath)), {
      recursive: true,
    });
    await writeFile(path.join(initialized.runDir, decisionPath), `# ${gate}\n`);
    return recordGateDecision({
      runDir: initialized.runDir,
      gate,
      decision: 'approved',
      decisionPath,
      metadata: {
        eventId: `evt-${gate}-${runId}`,
        at: `2026-07-12T15:33:${stage === 'wireframe' ? '01' : '02'}.000Z`,
        actor: 'user',
      },
    });
  };

  await transition('stage_transition', { stage: 'research', to: 'running' });
  await reviewStage('research', 'research.spec', 'site/research.md', '# Research\n');
  await transition('stage_transition', { stage: 'research', to: 'completed' });
  await transition('stage_transition', { stage: 'wireframe', to: 'running' });
  await reviewStage(
    'wireframe',
    'wireframe.preview',
    'site/wireframe.html',
    '<main>wireframe</main>',
  );
  await transition('stage_transition', { stage: 'wireframe', to: 'awaiting_gate' });
  await decideGate('G1', 'wireframe');
  await transition('profile_locked', { resolved: 'fast' });
  await transition('stage_transition', { stage: 'design', to: 'running' });
  await reviewStage('design', 'design.contract', 'site/design.css', ':root{}\n');
  await transition('stage_transition', { stage: 'design', to: 'completed' });
  await transition('stage_transition', { stage: 'build', to: 'running' });
  const buildArtifact = await reviewStage(
    'build',
    'build.preview',
    'site/index.html',
    '<main>production</main>',
  );
  await transition('stage_transition', { stage: 'build', to: 'awaiting_gate' });
  await decideGate('G3', 'build');
  await transition('stage_transition', { stage: 'deploy', to: 'running' });
  return { projectRoot, runDir: initialized.runDir, buildArtifact };
}

test('deploy publish store rehashes the G3 build binding and rejects evidence overwrite or drift', async () => {
  const context = await setupPublishRun();
  const evidencePath = path.join(context.runDir, 'deploy', 'deployment-evidence.md');
  try {
    await mkdir(path.dirname(evidencePath), { recursive: true });
    await writeFile(evidencePath, '# Deployment evidence\n');
    await writeFile(
      path.join(context.projectRoot, 'site', 'index.html'),
      '<main>drift</main>',
    );
    await assert.rejects(
      () =>
        recordDeploymentPublish({
          runDir: context.runDir,
          ...publishPayload(),
          metadata: eventMetadata(5),
        }),
      /build|artifact.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.projectRoot, 'site', 'index.html'),
      '<main>production</main>',
    );
    const recorded = await recordDeploymentPublish({
      runDir: context.runDir,
      ...publishPayload(),
      metadata: eventMetadata(6),
    });
    assert.equal(recorded.event.payload.buildRef, 'build.preview@1');
    assert.equal(recorded.event.payload.buildSha256, context.buildArtifact.sha256);
    assert.equal(recorded.state.stages.deploy.status, 'running');

    await writeFile(evidencePath, '# overwritten\n');
    await assert.rejects(
      () =>
        recordDeploymentPublish({
          runDir: context.runDir,
          ...publishPayload(),
          metadata: eventMetadata(7),
        }),
      /evidence.*漂移|覆盖|已登记/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('deploy record CLI routes preflight and publish without performing external actions', async () => {
  const context = await setupPublishRun('20260712T154000Z-d3p3');
  const preflightInput = path.join(context.projectRoot, 'preflight-input.json');
  const publishInput = path.join(context.projectRoot, 'publish-input.json');
  try {
    await mkdir(path.join(context.runDir, 'preflight'), { recursive: true });
    await mkdir(path.join(context.runDir, 'deploy'), { recursive: true });
    await writeFile(
      path.join(context.runDir, 'preflight', 'deployment-readiness.md'),
      '# ready\n',
    );
    await writeFile(
      path.join(context.runDir, 'deploy', 'deployment-evidence.md'),
      '# published\n',
    );
    await writeFile(
      preflightInput,
      JSON.stringify({
        provider: 'cloudflare-pages',
        status: 'passed',
        checks: { cli: 'passed', identity: 'passed', project: 'passed' },
        metadata: eventMetadata(8),
      }),
    );
    await writeFile(
      publishInput,
      JSON.stringify({ ...publishPayload(), metadata: eventMetadata(9) }),
    );
    const preflight = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'deploy',
        'record',
        context.runDir,
        '--mode',
        'preflight',
        '--input-file',
        preflightInput,
      ],
      { encoding: 'utf8' },
    );
    assert.equal(preflight.status, 0, preflight.stderr);
    const publish = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'deploy',
        'record',
        context.runDir,
        '--mode',
        'publish',
        '--input-file',
        publishInput,
      ],
      { encoding: 'utf8' },
    );
    assert.equal(publish.status, 0, publish.stderr);
    const state = (await assertProjectionMatchesEvents(context.runDir)).state;
    assert.equal(state.deployment.preflight.status, 'passed');
    assert.equal(state.deployment.latestResult.status, 'success');
    assert.equal(state.stages.deploy.status, 'running');
    assert.equal(
      (await readFile(path.join(context.projectRoot, 'site', 'index.html'), 'utf8')),
      '<main>production</main>',
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});
