import { readArtifactLedger } from './artifact-ledger.mjs';
import {
  readCanonicalRubricBinding,
  readLatestArtifactBinding,
  readRunFileBinding,
} from './review-store.mjs';
import { canonicalRubricRef } from './review-contract.mjs';
import {
  assertProjectionMatchesEvents,
  verifySourceChanges,
} from './runtime-store.mjs';
import { scanRunSensitiveFiles } from './sensitive-scan.mjs';

const GATE_STAGES = Object.freeze({
  G1: 'wireframe',
  G2: 'prototype',
  G3: 'build',
});
const TERMINAL_STATUSES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);

function assertEqualBinding(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`${label} binding/hash 发生漂移`);
  }
}

function findLedgerArtifact(artifacts, artifactRef, label) {
  const separator = artifactRef?.lastIndexOf('@') ?? -1;
  const artifactId = artifactRef?.slice(0, separator);
  const revision = Number(artifactRef?.slice(separator + 1));
  const artifact = artifacts.find(
    (candidate) =>
      candidate.artifactId === artifactId && candidate.revision === revision,
  );
  if (!artifact) throw new Error(`${label} artifact ledger ref 不存在`);
  return artifact;
}

function validateHistoricalArtifact(artifacts, payload, label, stageName) {
  const artifact = findLedgerArtifact(artifacts, payload.artifactRef, label);
  assertEqualBinding(artifact.sha256, payload.artifactSha256, `${label} artifact`);
  if (artifact.producer !== stageName) {
    throw new Error(`${label} artifact producer 与 stage 不一致`);
  }
}

function validateHistoricalRubric(payload, canonicalRubric, label) {
  assertEqualBinding(
    payload.rubricRef,
    canonicalRubricRef(payload.stage),
    `${label} rubric ref`,
  );
  assertEqualBinding(
    payload.rubricSha256,
    canonicalRubric.sha256,
    `${label} rubric`,
  );
}

async function validateHistoricalBindings(
  runDir,
  events,
  artifacts,
  canonicalRubric,
) {
  for (const event of events) {
    if (event.type === 'review_recorded') {
      validateHistoricalRubric(
        event.payload,
        canonicalRubric,
        `historical review ${event.eventId}`,
      );
      const review = await readRunFileBinding(
        runDir,
        event.payload.reviewPath,
        `historical review ${event.eventId}`,
      );
      assertEqualBinding(
        review.sha256,
        event.payload.reviewSha256,
        `historical review ${event.eventId}`,
      );
      validateHistoricalArtifact(
        artifacts,
        event.payload,
        `historical review ${event.eventId}`,
        event.payload.stage,
      );
    }
    if (event.type === 'gate_decided') {
      const decision = await readRunFileBinding(
        runDir,
        event.payload.decisionPath,
        `historical gate ${event.eventId}`,
      );
      assertEqualBinding(
        decision.sha256,
        event.payload.decisionSha256,
        `historical gate ${event.eventId}`,
      );
      const reviewEvent = requireReviewEvent(
        events,
        event.payload,
        `historical gate ${event.eventId}`,
      );
      const review = await readRunFileBinding(
        runDir,
        event.payload.reviewPath,
        `historical gate review ${event.eventId}`,
      );
      assertEqualBinding(
        review.sha256,
        event.payload.reviewSha256,
        `historical gate review ${event.eventId}`,
      );
      validateHistoricalArtifact(
        artifacts,
        event.payload,
        `historical gate ${event.eventId}`,
        reviewEvent.payload.stage,
      );
    }
  }
}

async function validateReviewBinding(runDir, stageName, review) {
  const reviewFile = await readRunFileBinding(
    runDir,
    review.reviewPath,
    `${stageName} review Markdown`,
  );
  assertEqualBinding(
    reviewFile.sha256,
    review.reviewSha256,
    `${stageName} review`,
  );
  const artifact = await readLatestArtifactBinding(
    runDir,
    review.artifactRef,
    stageName,
  );
  assertEqualBinding(
    artifact.artifactSha256,
    review.artifactSha256,
    `${stageName} artifact`,
  );
}

async function validateCurrentReviews(runDir, state) {
  for (const [stageName, stage] of Object.entries(state.stages)) {
    if (!stage.latestReview) continue;
    await validateReviewBinding(runDir, stageName, stage.latestReview);
  }
}

function requireReviewEvent(events, decision, gateName) {
  const event = events.find(
    (candidate) =>
      candidate.eventId === decision.reviewEventId &&
      candidate.type === 'review_recorded',
  );
  if (!event) throw new Error(`${gateName} reviewEventId 不存在`);
  for (const field of [
    'reviewPath',
    'reviewSha256',
    'artifactRef',
    'artifactSha256',
  ]) {
    assertEqualBinding(
      event.payload?.[field],
      decision[field],
      `${gateName} ${field}`,
    );
  }
  return event;
}

async function validateGateBindings(runDir, state, events) {
  for (const [gateName, stageName] of Object.entries(GATE_STAGES)) {
    const decision = state.gates?.[gateName]?.latestDecision;
    if (!decision) continue;
    const decisionFile = await readRunFileBinding(
      runDir,
      decision.path,
      `${gateName} decision Markdown`,
    );
    assertEqualBinding(
      decisionFile.sha256,
      decision.sha256,
      `${gateName} decision`,
    );
    const reviewEvent = requireReviewEvent(events, decision, gateName);
    const reviewFile = await readRunFileBinding(
      runDir,
      decision.reviewPath,
      `${gateName} review Markdown`,
    );
    assertEqualBinding(
      reviewFile.sha256,
      decision.reviewSha256,
      `${gateName} review`,
    );
    await validateReviewBinding(runDir, stageName, reviewEvent.payload);
  }
}

async function validateDeploymentBindings(runDir, state) {
  const preflight = state.deployment.preflight;
  if (preflight) {
    const evidence = await readRunFileBinding(
      runDir,
      preflight.evidencePath,
      'deployment preflight evidence',
    );
    assertEqualBinding(
      evidence.sha256,
      preflight.evidenceSha256,
      'deployment preflight evidence',
    );
  }

  const result = state.deployment.latestResult;
  if (!result) return;
  const evidence = await readRunFileBinding(
    runDir,
    result.evidencePath,
    'deployment publish evidence',
  );
  assertEqualBinding(
    evidence.sha256,
    result.evidenceSha256,
    'deployment publish evidence',
  );
  const build = await readLatestArtifactBinding(
    runDir,
    result.buildRef,
    'build',
  );
  assertEqualBinding(
    build.artifactSha256,
    result.buildSha256,
    'deployment build artifact',
  );
  const g3 = state.gates.G3.latestDecision;
  if (!g3) throw new Error('deployment result 缺少 G3 binding');
  assertEqualBinding(result.buildRef, g3.artifactRef, 'deployment G3 ref');
  assertEqualBinding(
    result.buildSha256,
    g3.artifactSha256,
    'deployment G3 hash',
  );
}

async function validateTerminalFinalization(runDir, state, events) {
  const lastEvent = events.at(-1);
  if (
    !lastEvent ||
    lastEvent.type !== 'run_finalized' ||
    state.status !== lastEvent.payload?.status ||
    state.eventSequence !== lastEvent.sequence
  ) {
    throw new Error('terminal projection 必须匹配最后一个 run_finalized event');
  }
  if (
    !state.finalization ||
    state.finalization.eventId !== lastEvent.eventId
  ) {
    throw new Error('terminal projection 缺少匹配的 finalization binding');
  }
  for (const [field, label] of [
    ['skillUsage', 'skill usage'],
    ['retrospective', 'retrospective'],
  ]) {
    const expected = lastEvent.payload[field];
    const projected = state.finalization[field];
    if (
      !expected ||
      projected?.path !== expected.path ||
      projected?.sha256 !== expected.sha256
    ) {
      throw new Error(`${label} finalization binding 不一致`);
    }
    const document = await readRunFileBinding(
      runDir,
      expected.path,
      label,
    );
    assertEqualBinding(
      document.sha256,
      expected.sha256,
      `${label} finalization`,
    );
  }
}

export async function validateRun(
  runDir,
  { requireTerminal = false, packageRoot } = {},
) {
  const { events, state } = await assertProjectionMatchesEvents(runDir);
  const artifacts = await readArtifactLedger(runDir);
  const canonicalRubric = await readCanonicalRubricBinding({ packageRoot });
  await validateHistoricalBindings(
    runDir,
    events,
    artifacts,
    canonicalRubric,
  );
  await validateCurrentReviews(runDir, state);
  await validateGateBindings(runDir, state, events);
  await validateDeploymentBindings(runDir, state);
  if (state.source.mode === 'update' && state.source.plan) {
    await verifySourceChanges(runDir);
  }
  const scan = await scanRunSensitiveFiles(runDir);

  if (requireTerminal) {
    if (!TERMINAL_STATUSES.has(state.status)) {
      throw new Error('require-terminal 需要 finalize 后的 terminal status');
    }
    await validateTerminalFinalization(runDir, state, events);
  }
  return {
    valid: true,
    runId: state.runId,
    status: state.status,
    eventCount: events.length,
    artifactCount: artifacts.length,
    scannedFiles: scan.scanned,
  };
}
