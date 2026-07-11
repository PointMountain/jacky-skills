import {
  SAFE_RUN_ID_PATTERN,
  canonicalJson,
  computeStateHash,
} from './state-contract.mjs';

const STAGES = new Set([
  'research',
  'wireframe',
  'prototype',
  'design',
  'build',
  'deploy',
]);
const GATED_STAGES = new Set(['wireframe', 'prototype', 'build']);
const TERMINAL_RUN_STATES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);
const WORKFLOW_EVENT_TYPES = new Set([
  'stage_transition',
  'profile_locked',
  'deployment_authorization_changed',
]);
const LEGAL_STAGE_TRANSITIONS = new Map([
  ['not_started', new Set(['running'])],
  [
    'running',
    new Set(['awaiting_gate', 'completed', 'blocked', 'failed', 'cancelled']),
  ],
  [
    'awaiting_gate',
    new Set(['running', 'completed', 'blocked', 'cancelled']),
  ],
  ['blocked', new Set(['running', 'failed', 'cancelled'])],
]);
const APPROVED_DECISIONS = new Set(['approved', 'auto_approved']);

function cloneJson(value) {
  return JSON.parse(canonicalJson(value));
}

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new TypeError(`${label} 必须是非空字符串`);
  }
}

function assertStateIntegrity(state) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new TypeError('state 必须是对象');
  }
  if (computeStateHash(state) !== state.stateHash) {
    throw new Error('当前 stateHash 不一致');
  }
}

function assertMutableRun(state) {
  if (TERMINAL_RUN_STATES.has(state.status)) {
    throw new Error(`terminal run ${state.status} 不可原地继续`);
  }
  if (state.status === 'blocked' && !state.resume) {
    throw new Error('blocked run 必须包含 resume');
  }
}

function withEventMetadata(state, event, changes) {
  const next = {
    ...state,
    ...changes,
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

function nextStageAfter(stage) {
  if (stage === 'research') return 'wireframe';
  if (stage === 'design') return 'build';
  if (stage === 'deploy') return null;
  return stage;
}

function assertResume(resume, stage) {
  if (!resume || resume.stage !== stage) {
    throw new Error('blocked transition 必须提供当前 stage 的 resume');
  }
  requireNonEmptyString(resume.action, 'resume.action');
}

function assertLatestReviewAllowsAdvance(stageState) {
  const review = stageState.latestReview;
  if (
    !review ||
    review.kind !== 'subjective' ||
    stageState.subjectiveRound < 1 ||
    review.attempt !== stageState.attempt ||
    review.mustPass !== 'passed' ||
    (review.decision !== 'pass' &&
      review.decision !== 'proceed_with_residual')
  ) {
    throw new Error('stage advance 要求当前 attempt 的 latestReview mustPass passed 且 decision pass/proceed_with_residual');
  }
}

function applyStageTransition(state, event) {
  const { stage, to, resume } = event.payload ?? {};
  if (!STAGES.has(stage)) throw new Error(`未知 stage：${String(stage)}`);
  if (stage !== state.currentStage) {
    throw new Error(`只能迁移 currentStage ${state.currentStage}`);
  }

  const from = state.stages?.[stage]?.status;
  const allowed = LEGAL_STAGE_TRANSITIONS.get(from);
  if (!allowed?.has(to)) {
    throw new Error(`stage ${stage} 不允许从 ${from} 迁移到 ${String(to)}`);
  }
  if (GATED_STAGES.has(stage) && to === 'completed') {
    throw new Error(`${stage} 必须先进入 awaiting_gate，由 gate event 完成`);
  }
  if (!GATED_STAGES.has(stage) && to === 'awaiting_gate') {
    throw new Error(`${stage} 没有关联 gate`);
  }
  if (
    to === 'awaiting_gate' ||
    (to === 'completed' && !GATED_STAGES.has(stage))
  ) {
    assertLatestReviewAllowsAdvance(state.stages[stage]);
  }
  if (to === 'blocked') assertResume(resume, stage);
  if (from === 'blocked') assertResume(state.resume, stage);

  const stages = {
    ...state.stages,
    [stage]: { ...state.stages[stage], status: to },
  };
  const changes = { stages };

  if (to === 'blocked') {
    changes.status = 'blocked';
    changes.resume = cloneJson(resume);
  } else if (from === 'blocked' && to === 'running') {
    changes.status = 'running';
    changes.resume = null;
  } else if (to === 'completed' || to === 'skipped') {
    changes.currentStage = nextStageAfter(stage);
    changes.resume = changes.currentStage
      ? { stage: changes.currentStage, action: 'start' }
      : null;
  } else if (to === 'running') {
    changes.resume = null;
  }

  return withEventMetadata(state, event, changes);
}

function applyProfileLock(state, event) {
  const resolved = event.payload?.resolved;
  if (resolved !== 'fast' && resolved !== 'full') {
    throw new Error('profile.resolved 必须是 fast 或 full');
  }
  if (state.profile?.resolved !== null || state.profile?.lockedAt !== null) {
    throw new Error('profile 已锁定');
  }
  if (
    state.stages?.wireframe?.status !== 'completed' ||
    !APPROVED_DECISIONS.has(state.gates?.G1?.decision)
  ) {
    throw new Error('profile 只能在 wireframe completed 且 G1 approved 后锁定');
  }
  if (
    state.currentStage !== 'wireframe' ||
    state.stages?.design?.status !== 'not_started'
  ) {
    throw new Error('profile 必须在进入 design 前锁定');
  }
  if (
    state.profile.requested !== 'adaptive' &&
    state.profile.requested !== resolved
  ) {
    throw new Error(`resolved 必须匹配 requested ${state.profile.requested}`);
  }

  const isFast = resolved === 'fast';
  const currentStage = isFast ? 'design' : 'prototype';
  return withEventMetadata(state, event, {
    profile: { ...state.profile, resolved, lockedAt: event.at },
    stages: isFast
      ? {
          ...state.stages,
          prototype: { ...state.stages.prototype, status: 'skipped' },
        }
      : state.stages,
    gates: isFast
      ? {
          ...state.gates,
          G2: { ...state.gates.G2, decision: 'not_applicable' },
        }
      : state.gates,
    currentStage,
    resume: { stage: currentStage, action: 'start' },
  });
}

function applyDeploymentAuthorization(state, event) {
  const { authorized, provider } = event.payload ?? {};
  if (event.actor !== 'user') {
    throw new Error('deployment authorization 必须由 actor=user 明确提交');
  }
  if (typeof authorized !== 'boolean') {
    throw new TypeError('authorized 必须是 boolean');
  }
  if (!state.deployment?.requested) {
    throw new Error('未请求 deployment，不能变更授权');
  }
  if (authorized) {
    if (
      state.stages?.build?.status !== 'completed' ||
      !APPROVED_DECISIONS.has(state.gates?.G3?.decision)
    ) {
      throw new Error('deployment authorization 要求 build completed 且 G3 approved');
    }
    requireNonEmptyString(provider, 'provider');
  }

  const changes = {
    deployment: {
      ...state.deployment,
      authorized,
      provider: authorized ? provider : state.deployment.provider,
    },
  };
  if (authorized) {
    changes.status = 'running';
    changes.currentStage = 'deploy';
    changes.resume = { stage: 'deploy', action: 'start' };
  }
  return withEventMetadata(state, event, changes);
}

export function workflowEventReducer(state, event) {
  if (!WORKFLOW_EVENT_TYPES.has(event.type)) return null;
  assertStateIntegrity(state);
  assertMutableRun(state);
  if (event.beforeStateHash !== state.stateHash) {
    throw new Error(`${event.type}.beforeStateHash 不一致`);
  }

  if (event.type === 'stage_transition') {
    return applyStageTransition(state, event);
  }
  if (event.type === 'profile_locked') return applyProfileLock(state, event);
  return applyDeploymentAuthorization(state, event);
}

export function createWorkflowEvent(state, input) {
  assertStateIntegrity(state);
  requireNonEmptyString(input?.eventId, 'eventId');
  requireNonEmptyString(input?.type, 'type');
  requireNonEmptyString(input?.at, 'at');
  requireNonEmptyString(input?.actor, 'actor');
  if (!WORKFLOW_EVENT_TYPES.has(input.type)) {
    throw new Error(`Unknown workflow event type: ${input.type}`);
  }

  const event = {
    sequence: state.eventSequence + 1,
    eventId: input.eventId,
    type: input.type,
    at: input.at,
    actor: input.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(input.payload ?? {}),
    afterStateHash: null,
  };
  const nextState = workflowEventReducer(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}

export function assertSupersessionAllowed(state, status, supersededBy) {
  assertStateIntegrity(state);
  if (status !== 'cancelled' && status !== 'partial') {
    throw new Error('supersession status 只能是 cancelled 或 partial');
  }
  if (
    typeof supersededBy !== 'string' ||
    !SAFE_RUN_ID_PATTERN.test(supersededBy)
  ) {
    throw new Error('supersededBy run id 不安全');
  }
  if (supersededBy === state.runId) {
    throw new Error('supersededBy 不能指向自身 runId');
  }
  if (
    status === 'partial' &&
    (state.stages?.build?.status !== 'completed' ||
      !APPROVED_DECISIONS.has(state.gates?.G3?.decision))
  ) {
    throw new Error('partial supersession 要求 completed build 和 approved G3 preview');
  }
  return true;
}
