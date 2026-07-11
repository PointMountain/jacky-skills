import { canonicalJson, computeStateHash } from './state-contract.mjs';

const GATE_EVENT_TYPE = 'gate_decided';
const GATE_STAGES = Object.freeze({
  G1: 'wireframe',
  G2: 'prototype',
  G3: 'build',
});
const ATTENDED_DECISIONS = new Set([
  'approved',
  'revise',
  'rejected',
  'deferred',
]);
const TERMINAL_RUN_STATES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/u;
const ARTIFACT_REF_PATTERN =
  /^[a-z0-9]+(?:[._-][a-z0-9]+)*@[1-9]\d*$/u;

function cloneJson(value) {
  return JSON.parse(canonicalJson(value));
}

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new TypeError(`${label} 必须是非空字符串`);
  }
}

function requireSha256(value, label) {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    throw new Error(`${label} 必须是小写 SHA-256`);
  }
}

function assertStateIntegrity(state) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new TypeError('state 必须是对象');
  }
  if (computeStateHash(state) !== state.stateHash) {
    throw new Error('当前 stateHash 不一致');
  }
  if (TERMINAL_RUN_STATES.has(state.status)) {
    throw new Error(`terminal run ${state.status} 不可决定 gate`);
  }
}

function assertGatePreconditions(state, payload) {
  const stageName = GATE_STAGES[payload.gate];
  if (!stageName) throw new Error(`未知 gate：${String(payload.gate)}`);
  const stage = state.stages?.[stageName];
  if (!stage || stage.status !== 'awaiting_gate') {
    throw new Error(`${payload.gate} 要求 ${stageName} stage awaiting_gate`);
  }
  if (state.currentStage !== stageName) {
    throw new Error(`${payload.gate} stage 必须匹配 currentStage`);
  }

  const review = stage.latestReview;
  if (
    !review ||
    review.kind !== 'subjective' ||
    review.attempt !== stage.attempt ||
    review.mustPass !== 'passed' ||
    (review.decision !== 'pass' &&
      review.decision !== 'proceed_with_residual')
  ) {
    throw new Error('gate 要求当前 attempt 的 passed subjective latestReview');
  }
  for (const field of [
    'reviewPath',
    'reviewSha256',
    'artifactRef',
    'artifactSha256',
  ]) {
    if (payload[field] !== review[field]) {
      throw new Error(`gate ${field} 必须精确绑定 latestReview`);
    }
  }
  if (payload.reviewEventId !== review.eventId) {
    throw new Error('gate reviewEventId 必须精确绑定 latestReview.eventId');
  }
  return { stageName, stage };
}

function assertDecisionVersion(state, payload) {
  const gateState = state.gates?.[payload.gate];
  const expectedNumber = (gateState?.decisionCount ?? 0) + 1;
  if (payload.decisionNumber !== expectedNumber) {
    throw new Error(`decisionNumber 必须连续递增为 ${expectedNumber}`);
  }
  const expectedPath = `gates/${payload.gate}/decision-${expectedNumber}.md`;
  if (payload.decisionPath !== expectedPath) {
    throw new Error(`decisionPath 必须是 ${expectedPath}`);
  }
  requireSha256(payload.decisionSha256, 'decisionSha256');
  requireSha256(payload.reviewSha256, 'reviewSha256');
  requireSha256(payload.artifactSha256, 'artifactSha256');
  requireNonEmptyString(payload.reviewPath, 'reviewPath');
  requireNonEmptyString(payload.reviewEventId, 'reviewEventId');
  if (!ARTIFACT_REF_PATTERN.test(payload.artifactRef ?? '')) {
    throw new Error('artifactRef 必须是 artifactId@revision');
  }
}

function assertDecisionActor(state, event) {
  if (state.interactionMode === 'attended') {
    if (!ATTENDED_DECISIONS.has(event.payload.decision)) {
      throw new Error('attended gate decision 无效，禁止 auto_approved/not_applicable');
    }
    if (event.actor !== 'user') {
      throw new Error('attended gate decision 必须由 actor=user 提交');
    }
    return;
  }
  if (event.payload.decision !== 'auto_approved') {
    throw new Error('unattended gate 仅允许 auto_approved');
  }
  if (event.actor !== 'web-flow-runtime') {
    throw new Error('unattended auto_approved 必须由 runtime actor 提交');
  }
}

function approvedDestination(state, gate) {
  if (gate === 'G1') {
    return {
      currentStage: 'wireframe',
      resume: { stage: 'wireframe', action: 'profile_lock' },
    };
  }
  if (gate === 'G2') {
    return {
      currentStage: 'design',
      resume: { stage: 'design', action: 'start' },
    };
  }
  if (state.deployment.authorized) {
    return {
      currentStage: 'deploy',
      resume: { stage: 'deploy', action: 'start' },
    };
  }
  return { currentStage: null, resume: null };
}

function updateGateProjection(state, event, stageName, previousStage) {
  const payload = event.payload;
  const latestDecision = {
    number: payload.decisionNumber,
    path: payload.decisionPath,
    sha256: payload.decisionSha256,
    artifactRef: payload.artifactRef,
    artifactSha256: payload.artifactSha256,
    reviewPath: payload.reviewPath,
    reviewSha256: payload.reviewSha256,
    reviewEventId: payload.reviewEventId,
    eventId: event.eventId,
    at: event.at,
    actor: event.actor,
  };
  const gate = {
    ...state.gates[payload.gate],
    decision: payload.decision,
    decisionCount: payload.decisionNumber,
    latestDecision,
  };
  let stage = { ...previousStage };
  let changes = { status: 'running' };

  if (payload.decision === 'approved' || payload.decision === 'auto_approved') {
    stage.status = 'completed';
    changes = { ...changes, ...approvedDestination(state, payload.gate) };
  } else if (payload.decision === 'revise') {
    stage = {
      ...stage,
      status: 'running',
      attempt: stage.attempt + 1,
      latestReview: null,
      subjectiveRound: 0,
      recheckCount: 0,
    };
    changes.currentStage = stageName;
    changes.resume = { stage: stageName, action: 'revise' };
  } else if (payload.decision === 'deferred') {
    stage.status = 'blocked';
    changes.status = 'blocked';
    changes.currentStage = stageName;
    changes.resume = { stage: stageName, action: 'gate_decision' };
  } else {
    stage.status = 'blocked';
    changes.status = 'blocked';
    changes.currentStage = stageName;
    changes.pendingTerminal = 'cancelled';
    changes.resume = { stage: stageName, action: 'finalize_cancelled' };
  }

  const next = {
    ...state,
    ...changes,
    stages: { ...state.stages, [stageName]: stage },
    gates: { ...state.gates, [payload.gate]: gate },
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

export function gateEventReducer(state, event) {
  if (event.type !== GATE_EVENT_TYPE) return null;
  assertStateIntegrity(state);
  if (event.beforeStateHash !== state.stateHash) {
    throw new Error('gate_decided.beforeStateHash 不一致');
  }
  assertDecisionActor(state, event);
  const { stageName, stage } = assertGatePreconditions(state, event.payload);
  assertDecisionVersion(state, event.payload);
  return updateGateProjection(state, event, stageName, stage);
}

export function createGateDecisionEvent(state, payload, metadata) {
  assertStateIntegrity(state);
  requireNonEmptyString(metadata?.eventId, 'eventId');
  requireNonEmptyString(metadata?.at, 'at');
  requireNonEmptyString(metadata?.actor, 'actor');
  const event = {
    sequence: state.eventSequence + 1,
    eventId: metadata.eventId,
    type: GATE_EVENT_TYPE,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(payload),
    afterStateHash: null,
  };
  const nextState = gateEventReducer(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}
