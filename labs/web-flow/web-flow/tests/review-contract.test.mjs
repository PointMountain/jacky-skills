import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { addArtifact } from '../scripts/lib/artifact-ledger.mjs';
import {
  createGateDecisionEvent,
  gateEventReducer,
} from '../scripts/lib/gate-contract.mjs';
import { recordGateDecision } from '../scripts/lib/gate-store.mjs';
import {
  createReviewEvent,
  reviewEventReducer,
} from '../scripts/lib/review-contract.mjs';
import { recordReview } from '../scripts/lib/review-store.mjs';
import {
  assertProjectionMatchesEvents,
  initializeRun,
  recordWorkflowTransition,
} from '../scripts/lib/runtime-store.mjs';
import {
  computeStateHash,
  createRunInitialization,
  replayEvents,
} from '../scripts/lib/state-contract.mjs';
import {
  createWorkflowEvent,
  workflowEventReducer,
} from '../scripts/lib/workflow-contract.mjs';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);
const HASH = 'a'.repeat(64);

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

function rehash(state) {
  const copy = structuredClone(state);
  copy.stateHash = computeStateHash(copy);
  return copy;
}

function reviewReadyState() {
  const { state } = createRunInitialization(
    {
      runId: '20260712T120000Z-r1v1',
      intent: '评审线框稿',
      projectRoot: '.',
      source: { mode: 'create', dir: 'site' },
      interactionMode: 'attended',
      profile: { requested: 'adaptive' },
      deployment: { requested: false, authorized: false, provider: null },
    },
    {
      eventId: 'evt-review-init',
      at: '2026-07-12T12:00:00.000Z',
      actor: 'web-flow-runtime',
    },
  );
  return rehash({
    ...state,
    currentStage: 'wireframe',
    stages: {
      ...state.stages,
      research: { ...state.stages.research, status: 'completed' },
      wireframe: { ...state.stages.wireframe, status: 'running' },
    },
    resume: null,
  });
}

function reviewPayload(overrides = {}) {
  return {
    stage: 'wireframe',
    attempt: 1,
    kind: 'subjective',
    round: 1,
    recheck: null,
    reviewer: 'independent-reviewer',
    independence: { independent: true, limitation: null },
    rubricRef: 'web-flow-rubrics#wireframe-v1',
    rubricSha256: HASH,
    reviewPath:
      'reviews/wireframe/attempt-1/round-1--wireframe.preview-r1.md',
    reviewSha256: HASH,
    artifactRef: 'wireframe.preview@1',
    artifactSha256: HASH,
    mustPass: 'passed',
    decision: 'pass',
    weightedScore: 4.2,
    ...overrides,
  };
}

function createReview(state, payload, index = 1) {
  return createReviewEvent(state, payload, {
    eventId: `evt-review-${index}`,
    at: `2026-07-12T12:00:0${index}.000Z`,
    actor: 'independent-reviewer',
  });
}

async function setupReviewRun(runId = '20260712T130000Z-r2v2') {
  const projectRoot = await mkdtemp(path.join(tmpdir(), 'web-flow-review-'));
  const initialized = await initializeRun({
    projectRoot,
    input: {
      runId,
      intent: '评审线框稿',
      projectRoot: '.',
      source: { mode: 'create', dir: 'site' },
      interactionMode: 'attended',
      profile: { requested: 'adaptive' },
      deployment: { requested: false, authorized: false, provider: null },
    },
    metadata: {
      eventId: `evt-init-${runId}`,
      at: '2026-07-12T13:00:00.000Z',
      actor: 'web-flow-runtime',
    },
  });
  let eventIndex = 0;
  const transition = async (stage, to) => {
    eventIndex += 1;
    return recordWorkflowTransition(initialized.runDir, {
      eventId: `evt-stage-${eventIndex}-${runId}`,
      type: 'stage_transition',
      at: `2026-07-12T13:00:0${eventIndex}.000Z`,
      actor: 'agent',
      payload: { stage, to },
    });
  };
  await transition('research', 'running');
  await mkdir(path.join(projectRoot, 'site'), { recursive: true });
  const rubricPath = path.join(projectRoot, 'rubrics.md');
  await writeFile(rubricPath, '# Rubric\n原始字节\n');
  await writeFile(path.join(projectRoot, 'site', 'research.md'), '# Research\n');
  const researchArtifact = await addArtifact({
    runDir: initialized.runDir,
    artifactId: 'research.spec',
    artifactPath: 'site/research.md',
    producer: 'research',
    createdAt: '2026-07-12T13:00:02.000Z',
  });
  const researchReviewPath =
    'reviews/research/attempt-1/round-1--research.spec-r1.md';
  await mkdir(path.dirname(path.join(initialized.runDir, researchReviewPath)), {
    recursive: true,
  });
  await writeFile(
    path.join(initialized.runDir, researchReviewPath),
    '# Research Review\n',
  );
  await recordReview({
    runDir: initialized.runDir,
    stage: 'research',
    attempt: 1,
    kind: 'subjective',
    round: 1,
    recheck: null,
    reviewer: 'independent-reviewer',
    independence: { independent: true, limitation: null },
    rubricRef: 'web-flow-rubrics#research-v1',
    rubricPath,
    reviewPath: researchReviewPath,
    artifactRef: `${researchArtifact.artifact.artifactId}@${researchArtifact.artifact.revision}`,
    mustPass: 'passed',
    decision: 'pass',
    weightedScore: 4.2,
    metadata: {
      eventId: `evt-research-review-${runId}`,
      at: '2026-07-12T13:00:03.000Z',
      actor: 'independent-reviewer',
    },
  });
  await transition('research', 'completed');
  await transition('wireframe', 'running');

  await writeFile(path.join(projectRoot, 'site', 'wireframe.html'), '<main>A</main>');
  const artifact = await addArtifact({
    runDir: initialized.runDir,
    artifactId: 'wireframe.preview',
    artifactPath: 'site/wireframe.html',
    producer: 'wireframe',
    createdAt: '2026-07-12T13:00:05.000Z',
  });
  return {
    projectRoot,
    runDir: initialized.runDir,
    artifact: artifact.artifact,
    rubricPath,
  };
}

function reviewRecordInput(context, overrides = {}) {
  const artifact = context.artifact;
  const slot = overrides.slot ?? 'round-1';
  const reviewPath = `reviews/wireframe/attempt-1/${slot}--${artifact.artifactId}-r${artifact.revision}.md`;
  return {
    stage: 'wireframe',
    attempt: 1,
    kind: 'subjective',
    round: 1,
    recheck: null,
    reviewer: 'independent-reviewer',
    independence: { independent: true, limitation: null },
    rubricRef: 'web-flow-rubrics#wireframe-v1',
    rubricPath: context.rubricPath,
    reviewPath,
    artifactRef: `${artifact.artifactId}@${artifact.revision}`,
    mustPass: 'passed',
    decision: 'pass',
    weightedScore: 4.2,
    metadata: {
      eventId: overrides.eventId ?? 'evt-record-review-1',
      at: overrides.at ?? '2026-07-12T13:00:06.000Z',
      actor: 'independent-reviewer',
    },
    ...overrides,
    slot: undefined,
    eventId: undefined,
    at: undefined,
  };
}

test('review record binds raw review/rubric bytes, independent reviewer, and the latest live artifact', async () => {
  const context = await setupReviewRun();
  const input = reviewRecordInput(context);
  const reviewAbsolutePath = path.join(context.runDir, input.reviewPath);
  const reviewContents = '# Review\n独立评审原文\n';

  try {
    await mkdir(path.dirname(reviewAbsolutePath), { recursive: true });
    await writeFile(reviewAbsolutePath, reviewContents);
    await assert.rejects(
      () =>
        recordReview({
          runDir: context.runDir,
          ...input,
          metadata: { ...input.metadata, actor: 'different-agent' },
        }),
      /actor|reviewer/i,
    );
    const recorded = await recordReview({ runDir: context.runDir, ...input });
    const rubricContents = await readFile(context.rubricPath);

    assert.equal(recorded.event.type, 'review_recorded');
    assert.equal(recorded.event.payload.reviewSha256, sha256(reviewContents));
    assert.equal(recorded.event.payload.rubricSha256, sha256(rubricContents));
    assert.equal(recorded.event.payload.rubricPath, undefined);
    assert.equal(recorded.event.payload.artifactRef, 'wireframe.preview@1');
    assert.equal(
      recorded.event.payload.artifactSha256,
      context.artifact.sha256,
    );
    assert.equal(recorded.state.stages.wireframe.subjectiveRound, 1);
    assert.equal(recorded.state.stages.wireframe.recheckCount, 0);
    assert.equal(recorded.state.stages.wireframe.status, 'running');
    assert.equal(
      recorded.state.stages.wireframe.latestReview.reviewPath,
      input.reviewPath,
    );
    assert.deepEqual(recorded.event.payload.independence, {
      independent: true,
      limitation: null,
    });

    await writeFile(reviewAbsolutePath, '# Review\n被覆盖\n');
    await assert.rejects(
      () =>
        recordReview({
          runDir: context.runDir,
          ...input,
          metadata: { ...input.metadata, eventId: 'evt-overwrite' },
        }),
      /review.*漂移|覆盖|已登记/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('review record limits subjective rounds to 1/2, reserves exact versioned paths, and rejects stale artifacts', async () => {
  const state = reviewReadyState();
  const round1 = createReview(state, reviewPayload({ decision: 'revise_once' }), 1);
  assert.equal(round1.state.stages.wireframe.status, 'running');
  const round2Payload = reviewPayload({
    round: 2,
    reviewPath:
      'reviews/wireframe/attempt-1/round-2--wireframe.preview-r2.md',
    artifactRef: 'wireframe.preview@2',
  });
  const round2 = createReview(round1.state, round2Payload, 2);

  assert.equal(round2.state.stages.wireframe.subjectiveRound, 2);
  assert.equal(round2.state.resume, null);
  assert.throws(
    () =>
      createReview(round1.state, { ...round2Payload, decision: 'revise_once' }, 3),
    /round 2|revise_once/i,
  );
  assert.throws(
    () =>
      createReview(round2.state, {
        ...round2Payload,
        round: 3,
        reviewPath:
          'reviews/wireframe/attempt-1/round-3--wireframe.preview-r3.md',
        artifactRef: 'wireframe.preview@3',
      }, 4),
    /round|1|2/i,
  );
  assert.throws(
    () =>
      createReview(state, reviewPayload({ reviewPath: 'reviews/wrong.md' }), 5),
    /reviewPath|reviews\/wireframe\/attempt-1/i,
  );
  const awaitingGate = rehash({
    ...state,
    stages: {
      ...state.stages,
      wireframe: { ...state.stages.wireframe, status: 'awaiting_gate' },
    },
  });
  assert.throws(
    () => createReview(awaitingGate, reviewPayload(), 6),
    /subjective.*running|stage.*running/i,
  );
  assert.throws(
    () =>
      createReview(
        state,
        reviewPayload({ weightedScore: null }),
        7,
      ),
    /weightedScore|number|数字/i,
  );

  const context = await setupReviewRun('20260712T131000Z-r3v3');
  try {
    const input = reviewRecordInput(context);
    await mkdir(path.dirname(path.join(context.runDir, input.reviewPath)), {
      recursive: true,
    });
    await writeFile(path.join(context.runDir, input.reviewPath), '# Review\n');
    await writeFile(
      path.join(context.projectRoot, 'site', 'wireframe.html'),
      '<main>drift</main>',
    );
    await assert.rejects(
      () => recordReview({ runDir: context.runDir, ...input }),
      /artifact.*漂移|sha256|最新/i,
    );

    await writeFile(
      path.join(context.projectRoot, 'site', 'wireframe.html'),
      '<main>A</main>',
    );
    const wrongProducer = await addArtifact({
      runDir: context.runDir,
      artifactId: 'foreign.preview',
      artifactPath: 'site/wireframe.html',
      producer: 'research',
      createdAt: '2026-07-12T13:10:08.000Z',
    });
    const foreignPath =
      'reviews/wireframe/attempt-1/round-1--foreign.preview-r1.md';
    await writeFile(path.join(context.runDir, foreignPath), '# Foreign\n');
    await assert.rejects(
      () =>
        recordReview({
          runDir: context.runDir,
          ...input,
          reviewPath: foreignPath,
          artifactRef: `${wrongProducer.artifact.artifactId}@${wrongProducer.artifact.revision}`,
          metadata: { ...input.metadata, eventId: 'evt-wrong-producer' },
        }),
      /producer|stage|wireframe/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('must-pass rechecks are independent of subjective rounds and recover a blocked run only after passing', () => {
  const state = reviewReadyState();
  const failed = createReview(
    state,
    reviewPayload({
      mustPass: 'failed',
      decision: 'blocked',
      weightedScore: null,
    }),
    1,
  );
  assert.equal(failed.state.status, 'blocked');
  assert.equal(failed.state.stages.wireframe.status, 'blocked');
  assert.equal(failed.state.stages.wireframe.subjectiveRound, 0);
  assert.throws(
    () =>
      createReview(
        state,
        reviewPayload({ mustPass: 'failed', decision: 'blocked' }),
        5,
      ),
    /weightedScore|null/i,
  );

  const recheck1 = createReview(
    failed.state,
    reviewPayload({
      kind: 'must_pass_recheck',
      round: null,
      recheck: 1,
      reviewPath:
        'reviews/wireframe/attempt-1/must-pass-recheck-1--wireframe.preview-r1.md',
      mustPass: 'failed',
      decision: 'blocked',
      weightedScore: null,
      independence: {
        independent: false,
        limitation: '仅能使用干净上下文复核',
      },
    }),
    2,
  );
  assert.equal(recheck1.state.status, 'blocked');
  assert.equal(recheck1.state.stages.wireframe.subjectiveRound, 0);
  assert.equal(recheck1.state.stages.wireframe.recheckCount, 1);

  const recheck2 = createReview(
    recheck1.state,
    reviewPayload({
      kind: 'must_pass_recheck',
      round: null,
      recheck: 2,
      reviewPath:
        'reviews/wireframe/attempt-1/must-pass-recheck-2--wireframe.preview-r1.md',
      weightedScore: null,
    }),
    3,
  );
  assert.equal(recheck2.state.status, 'running');
  assert.equal(recheck2.state.stages.wireframe.status, 'running');
  assert.equal(recheck2.state.stages.wireframe.subjectiveRound, 0);
  assert.equal(recheck2.state.stages.wireframe.recheckCount, 2);
  assert.equal(recheck2.state.resume, null);
  assert.throws(
    () =>
      createWorkflowEvent(recheck2.state, {
        eventId: 'evt-awaiting-before-subjective',
        type: 'stage_transition',
        at: '2026-07-12T12:00:08.000Z',
        actor: 'agent',
        payload: { stage: 'wireframe', to: 'awaiting_gate' },
      }),
    /subjective|latestReview|review/i,
  );
  assert.throws(
    () =>
      createReview(
        failed.state,
        reviewPayload({
          kind: 'must_pass_recheck',
          round: null,
          recheck: 1,
          reviewPath:
            'reviews/wireframe/attempt-1/must-pass-recheck-1--wireframe.preview-r1.md',
        }),
        6,
      ),
    /weightedScore|null/i,
  );

  const actualRound1 = createReview(
    recheck2.state,
    reviewPayload({
      artifactRef: 'wireframe.preview@2',
      reviewPath:
        'reviews/wireframe/attempt-1/round-1--wireframe.preview-r2.md',
    }),
    7,
  );
  assert.equal(actualRound1.state.stages.wireframe.status, 'running');
  assert.equal(actualRound1.state.stages.wireframe.subjectiveRound, 1);
  assert.equal(
    createWorkflowEvent(actualRound1.state, {
      eventId: 'evt-awaiting-after-subjective',
      type: 'stage_transition',
      at: '2026-07-12T12:00:09.000Z',
      actor: 'agent',
      payload: { stage: 'wireframe', to: 'awaiting_gate' },
    }).state.stages.wireframe.status,
    'awaiting_gate',
  );
  assert.throws(
    () =>
      createReview(
        failed.state,
        reviewPayload({
          kind: 'must_pass_recheck',
          round: null,
          recheck: 0,
          reviewPath:
            'reviews/wireframe/attempt-1/must-pass-recheck-0--wireframe.preview-r1.md',
          weightedScore: null,
        }),
        4,
      ),
    /recheck|正整数/i,
  );
});

test('review record CLI is a narrow route and replay composes workflow plus review reducers', async () => {
  const context = await setupReviewRun('20260712T132000Z-r4v4');
  const input = reviewRecordInput(context, {
    eventId: 'evt-cli-review',
    at: '2026-07-12T13:20:06.000Z',
  });
  const inputPath = path.join(context.projectRoot, 'review-input.json');

  try {
    await mkdir(path.dirname(path.join(context.runDir, input.reviewPath)), {
      recursive: true,
    });
    await writeFile(path.join(context.runDir, input.reviewPath), '# CLI Review\n');
    await writeFile(inputPath, JSON.stringify(input), 'utf8');
    const result = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'review',
        'record',
        context.runDir,
        '--input-file',
        inputPath,
      ],
      { encoding: 'utf8' },
    );

    assert.equal(result.status, 0, result.stderr);
    const projection = (await assertProjectionMatchesEvents(context.runDir)).state;
    assert.equal(projection.stages.wireframe.subjectiveRound, 1);
    assert.equal(projection.stages.wireframe.latestReview.decision, 'pass');
    const awaitingGate = await recordWorkflowTransition(context.runDir, {
      eventId: 'evt-cli-wireframe-awaiting-gate',
      type: 'stage_transition',
      at: '2026-07-12T13:20:07.000Z',
      actor: 'agent',
      payload: { stage: 'wireframe', to: 'awaiting_gate' },
    });
    assert.equal(awaitingGate.state.stages.wireframe.status, 'awaiting_gate');

    const eventsText = await readFile(path.join(context.runDir, 'events.jsonl'), 'utf8');
    const events = eventsText
      .trimEnd()
      .split('\n')
      .map((line) => JSON.parse(line));
    const composedReducer = (state, event) =>
      workflowEventReducer(state, event) ?? reviewEventReducer(state, event);
    assert.deepEqual(replayEvents(events, composedReducer), awaitingGate.state);
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

async function prepareGateRun(runId = '20260712T140000Z-g1a1') {
  const context = await setupReviewRun(runId);
  const reviewInput = reviewRecordInput(context, {
    eventId: `evt-wireframe-review-${runId}`,
    at: '2026-07-12T14:00:01.000Z',
  });
  await mkdir(path.dirname(path.join(context.runDir, reviewInput.reviewPath)), {
    recursive: true,
  });
  await writeFile(
    path.join(context.runDir, reviewInput.reviewPath),
    '# Wireframe Review\n',
  );
  await recordReview({ runDir: context.runDir, ...reviewInput });
  await recordWorkflowTransition(context.runDir, {
    eventId: `evt-wireframe-awaiting-${runId}`,
    type: 'stage_transition',
    at: '2026-07-12T14:00:02.000Z',
    actor: 'agent',
    payload: { stage: 'wireframe', to: 'awaiting_gate' },
  });
  return { ...context, reviewInput };
}

function gateReadyState({
  gate = 'G1',
  interactionMode = 'attended',
  authorized = false,
} = {}) {
  const mapping = { G1: 'wireframe', G2: 'prototype', G3: 'build' };
  const stage = mapping[gate];
  const state = createRunInitialization(
    {
      runId: '20260712T141000Z-g2b2',
      intent: 'Gate 决策',
      projectRoot: '.',
      source: { mode: 'create', dir: 'site' },
      interactionMode,
      profile: { requested: 'full' },
      deployment: {
        requested: gate === 'G3',
        authorized,
        provider: authorized ? 'cloudflare-pages' : null,
      },
    },
    {
      eventId: 'evt-gate-init',
      at: '2026-07-12T14:10:00.000Z',
      actor: 'web-flow-runtime',
    },
  ).state;
  const latestReview = {
    stage,
    attempt: 1,
    kind: 'subjective',
    round: 1,
    mustPass: 'passed',
    decision: 'pass',
    reviewPath: `reviews/${stage}/attempt-1/round-1--${stage}.preview-r1.md`,
    reviewSha256: 'b'.repeat(64),
    artifactRef: `${stage}.preview@1`,
    artifactSha256: 'c'.repeat(64),
    eventId: `evt-${stage}-review`,
  };
  return rehash({
    ...state,
    currentStage: stage,
    stages: {
      ...state.stages,
      [stage]: {
        ...state.stages[stage],
        status: 'awaiting_gate',
        subjectiveRound: 1,
        latestReview,
      },
    },
    resume: null,
  });
}

function gatePayload(state, gate, decision, decisionNumber = 1) {
  const stage = { G1: 'wireframe', G2: 'prototype', G3: 'build' }[gate];
  const review = state.stages[stage].latestReview;
  return {
    gate,
    decision,
    decisionNumber,
    decisionPath: `gates/${gate}/decision-${decisionNumber}.md`,
    decisionSha256: 'd'.repeat(64),
    reviewPath: review.reviewPath,
    reviewSha256: review.reviewSha256,
    reviewEventId: review.eventId,
    artifactRef: review.artifactRef,
    artifactSha256: review.artifactSha256,
  };
}

function createGate(state, payload, actor = 'user', index = 1) {
  return createGateDecisionEvent(state, payload, {
    eventId: `evt-gate-${index}`,
    at: `2026-07-12T14:10:0${index}.000Z`,
    actor,
  });
}

test('gate decisions require live review/artifact bindings and persist an immutable versioned decision document', async () => {
  const context = await prepareGateRun();
  const decisionPath = 'gates/G1/decision-1.md';
  const decisionAbsolutePath = path.join(context.runDir, decisionPath);

  try {
    await mkdir(path.dirname(decisionAbsolutePath), { recursive: true });
    await writeFile(decisionAbsolutePath, '# G1 approved\n');
    await writeFile(
      path.join(context.runDir, context.reviewInput.reviewPath),
      '# Review drift\n',
    );
    await assert.rejects(
      () =>
        recordGateDecision({
          runDir: context.runDir,
          gate: 'G1',
          decision: 'approved',
          decisionPath,
          metadata: {
            eventId: 'evt-g1-drift',
            at: '2026-07-12T14:00:03.000Z',
            actor: 'user',
          },
        }),
      /review.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.runDir, context.reviewInput.reviewPath),
      '# Wireframe Review\n',
    );
    await writeFile(
      path.join(context.projectRoot, 'site', 'wireframe.html'),
      '<main>gate drift</main>',
    );
    await assert.rejects(
      () =>
        recordGateDecision({
          runDir: context.runDir,
          gate: 'G1',
          decision: 'approved',
          decisionPath,
          metadata: {
            eventId: 'evt-g1-artifact-drift',
            at: '2026-07-12T14:00:03.500Z',
            actor: 'user',
          },
        }),
      /artifact.*漂移|hash/i,
    );
    await writeFile(
      path.join(context.projectRoot, 'site', 'wireframe.html'),
      '<main>A</main>',
    );
    const recorded = await recordGateDecision({
      runDir: context.runDir,
      gate: 'G1',
      decision: 'approved',
      decisionPath,
      metadata: {
        eventId: 'evt-g1-approved',
        at: '2026-07-12T14:00:04.000Z',
        actor: 'user',
      },
    });

    assert.equal(recorded.event.payload.reviewPath, context.reviewInput.reviewPath);
    assert.equal(
      recorded.event.payload.reviewEventId,
      context.reviewInput.metadata.eventId,
    );
    assert.equal(recorded.event.payload.artifactRef, 'wireframe.preview@1');
    assert.equal(recorded.event.payload.decisionSha256, sha256('# G1 approved\n'));
    assert.equal(recorded.state.gates.G1.decisionCount, 1);
    assert.equal(recorded.state.gates.G1.latestDecision.path, decisionPath);
    assert.equal(
      recorded.state.gates.G1.latestDecision.reviewEventId,
      context.reviewInput.metadata.eventId,
    );
    assert.equal(recorded.state.stages.wireframe.status, 'completed');
    assert.equal(recorded.state.currentStage, 'wireframe');
    assert.deepEqual(recorded.state.resume, {
      stage: 'wireframe',
      action: 'profile_lock',
    });

    await writeFile(decisionAbsolutePath, '# overwritten\n');
    await assert.rejects(
      () =>
        recordGateDecision({
          runDir: context.runDir,
          gate: 'G1',
          decision: 'approved',
          decisionPath,
          metadata: {
            eventId: 'evt-g1-overwrite',
            at: '2026-07-12T14:00:05.000Z',
            actor: 'user',
          },
        }),
      /decision.*漂移|覆盖|已登记/i,
    );
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});

test('gate decisions implement attended revise, deferred, rejected, and monotonic decision numbers', () => {
  const ready = gateReadyState();
  const revised = createGate(ready, gatePayload(ready, 'G1', 'revise'));
  assert.equal(revised.state.stages.wireframe.status, 'running');
  assert.equal(revised.state.stages.wireframe.attempt, 2);
  assert.equal(revised.state.stages.wireframe.latestReview, null);
  assert.equal(revised.state.stages.wireframe.subjectiveRound, 0);
  assert.equal(revised.state.stages.wireframe.recheckCount, 0);
  assert.equal(revised.state.gates.G1.decisionCount, 1);
  assert.throws(
    () =>
      createGate(
        ready,
        { ...gatePayload(ready, 'G1', 'approved'), reviewEventId: 'forged' },
      ),
    /reviewEventId|latestReview/i,
  );

  const secondReady = rehash({
    ...revised.state,
    stages: {
      ...revised.state.stages,
      wireframe: {
        ...revised.state.stages.wireframe,
        status: 'awaiting_gate',
        subjectiveRound: 1,
        latestReview: {
          ...ready.stages.wireframe.latestReview,
          attempt: 2,
          reviewPath:
            'reviews/wireframe/attempt-2/round-1--wireframe.preview-r2.md',
          artifactRef: 'wireframe.preview@2',
        },
      },
    },
    resume: null,
  });
  const approvedSecond = createGate(
    secondReady,
    gatePayload(secondReady, 'G1', 'approved', 2),
    'user',
    2,
  );
  assert.equal(approvedSecond.state.gates.G1.decisionCount, 2);

  const deferred = createGate(
    ready,
    gatePayload(ready, 'G1', 'deferred'),
  );
  assert.equal(deferred.state.status, 'blocked');
  assert.equal(deferred.state.stages.wireframe.status, 'blocked');
  assert.equal(deferred.state.resume.action, 'gate_decision');

  const rejected = createGate(
    ready,
    gatePayload(ready, 'G1', 'rejected'),
  );
  assert.equal(rejected.state.status, 'blocked');
  assert.equal(rejected.state.pendingTerminal, 'cancelled');
  assert.equal(rejected.state.resume.action, 'finalize_cancelled');
  assert.throws(
    () => createGate(ready, gatePayload(ready, 'G1', 'approved'), 'agent'),
    /actor=user|attended|用户/i,
  );
});

test('gate decisions restrict unattended runs to runtime auto approval and map G2/G3 destinations', () => {
  const unattendedG2 = gateReadyState({
    gate: 'G2',
    interactionMode: 'unattended',
  });
  const g2 = createGate(
    unattendedG2,
    gatePayload(unattendedG2, 'G2', 'auto_approved'),
    'web-flow-runtime',
  );
  assert.equal(g2.state.stages.prototype.status, 'completed');
  assert.equal(g2.state.currentStage, 'design');
  assert.throws(
    () =>
      createGate(
        unattendedG2,
        gatePayload(unattendedG2, 'G2', 'approved'),
        'web-flow-runtime',
      ),
    /auto_approved|unattended/i,
  );
  assert.throws(
    () =>
      createGate(
        unattendedG2,
        gatePayload(unattendedG2, 'G2', 'auto_approved'),
        'user',
      ),
    /runtime|actor/i,
  );
  assert.throws(
    () => createGate(gateReadyState(), gatePayload(gateReadyState(), 'G1', 'auto_approved')),
    /attended|auto_approved/i,
  );
  assert.throws(
    () => createGate(gateReadyState(), gatePayload(gateReadyState(), 'G1', 'not_applicable')),
    /not_applicable|decision/i,
  );

  const g3Unauthorized = gateReadyState({ gate: 'G3', authorized: false });
  assert.equal(
    createGate(
      g3Unauthorized,
      gatePayload(g3Unauthorized, 'G3', 'approved'),
    ).state.currentStage,
    null,
  );
  const g3Authorized = gateReadyState({ gate: 'G3', authorized: true });
  assert.equal(
    createGate(
      g3Authorized,
      gatePayload(g3Authorized, 'G3', 'approved'),
    ).state.currentStage,
    'deploy',
  );
});

test('gate decide CLI is narrow and persists the composed gate projection', async () => {
  const context = await prepareGateRun('20260712T142000Z-g3c3');
  const decisionPath = 'gates/G1/decision-1.md';
  const inputPath = path.join(context.projectRoot, 'gate-input.json');

  try {
    await mkdir(path.dirname(path.join(context.runDir, decisionPath)), {
      recursive: true,
    });
    await writeFile(path.join(context.runDir, decisionPath), '# approve\n');
    await writeFile(
      inputPath,
      JSON.stringify({
        gate: 'G1',
        decision: 'approved',
        decisionPath,
        metadata: {
          eventId: 'evt-cli-g1-approved',
          at: '2026-07-12T14:20:03.000Z',
          actor: 'user',
        },
      }),
    );
    const result = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'gate',
        'decide',
        context.runDir,
        '--input-file',
        inputPath,
      ],
      { encoding: 'utf8' },
    );
    assert.equal(result.status, 0, result.stderr);
    const state = (await assertProjectionMatchesEvents(context.runDir)).state;
    assert.equal(state.gates.G1.decision, 'approved');
    assert.equal(state.gates.G1.decisionCount, 1);
    assert.equal(state.stages.wireframe.status, 'completed');
  } finally {
    await rm(context.projectRoot, { recursive: true, force: true });
  }
});
