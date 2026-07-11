import { createGateDecisionEvent } from './gate-contract.mjs';
import {
  readLatestArtifactBinding,
  readRunFileBinding,
} from './review-store.mjs';
import {
  appendRuntimeEvent,
  assertProjectionMatchesEvents,
  readRuntimeEvents,
} from './runtime-store.mjs';
import { canonicalJson } from './state-contract.mjs';

const GATE_STAGES = Object.freeze({
  G1: 'wireframe',
  G2: 'prototype',
  G3: 'build',
});

function findRegisteredDecision(events, decisionPath) {
  return events.find(
    (event) =>
      event.type === 'gate_decided' &&
      event.payload?.decisionPath === decisionPath,
  );
}

export async function recordGateDecision({
  runDir,
  gate,
  decision,
  decisionPath,
  metadata,
}) {
  const { state } = await assertProjectionMatchesEvents(runDir);
  const stageName = GATE_STAGES[gate];
  if (!stageName) throw new Error(`未知 gate：${String(gate)}`);
  const review = state.stages?.[stageName]?.latestReview;
  if (!review) throw new Error(`${gate} 缺少 latestReview`);

  const liveReview = await readRunFileBinding(
    runDir,
    review.reviewPath,
    'review Markdown',
  );
  if (liveReview.sha256 !== review.reviewSha256) {
    throw new Error('latestReview Markdown hash 发生漂移');
  }
  const liveArtifact = await readLatestArtifactBinding(
    runDir,
    review.artifactRef,
    stageName,
  );
  if (liveArtifact.artifactSha256 !== review.artifactSha256) {
    throw new Error('latestReview artifact hash binding 不一致');
  }
  const decisionDocument = await readRunFileBinding(
    runDir,
    decisionPath,
    'gate decision Markdown',
  );
  const decisionNumber = (state.gates?.[gate]?.decisionCount ?? 0) + 1;
  const payload = {
    gate,
    decision,
    decisionNumber,
    decisionPath,
    decisionSha256: decisionDocument.sha256,
    reviewPath: review.reviewPath,
    reviewSha256: liveReview.sha256,
    reviewEventId: review.eventId,
    ...liveArtifact,
  };

  const events = await readRuntimeEvents(runDir);
  const registered = findRegisteredDecision(events, decisionPath);
  if (registered) {
    if (registered.payload.decisionSha256 !== payload.decisionSha256) {
      throw new Error('已登记 gate decision Markdown 发生漂移，禁止覆盖');
    }
    if (registered.eventId !== metadata?.eventId) {
      throw new Error('decisionPath 已登记，必须创建下一版本路径');
    }
    if (canonicalJson(registered.payload) !== canonicalJson(payload)) {
      throw new Error('重复 eventId 的 gate binding 不一致');
    }
    const stored = await appendRuntimeEvent(runDir, registered);
    return { ...stored, event: registered };
  }

  const { event } = createGateDecisionEvent(state, payload, metadata);
  const stored = await appendRuntimeEvent(runDir, event);
  return { ...stored, event };
}
