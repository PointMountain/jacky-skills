import { canonicalJson, computeStateHash } from './state-contract.mjs';

const REVIEW_EVENT_TYPE = 'review_recorded';
const REVIEW_KINDS = new Set(['subjective', 'must_pass_recheck']);
const PASSED_DECISIONS = new Set([
  'pass',
  'revise_once',
  'proceed_with_residual',
]);
const MUST_PASS_RESULTS = new Set(['passed', 'failed']);
const TERMINAL_RUN_STATES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);
const ARTIFACT_REF_PATTERN =
  /^([a-z0-9]+(?:[._-][a-z0-9]+)*)@([1-9]\d*)$/u;
const SHA256_PATTERN = /^[a-f0-9]{64}$/u;
export const CANONICAL_RUBRIC_DOCUMENT_REF =
  'web-flow-benchmark/references/rubrics.md';

export function canonicalRubricRef(stage) {
  requireNonEmptyString(stage, 'stage');
  return `${CANONICAL_RUBRIC_DOCUMENT_REF}#${stage}`;
}

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
    throw new Error(`terminal run ${state.status} 不可登记 review`);
  }
}

function parseArtifactRef(artifactRef) {
  const match = ARTIFACT_REF_PATTERN.exec(artifactRef ?? '');
  if (!match) throw new Error('artifactRef 必须是 artifactId@revision');
  return { artifactId: match[1], revision: Number(match[2]) };
}

function expectedReviewPath(payload) {
  const { artifactId, revision } = parseArtifactRef(payload.artifactRef);
  const slot =
    payload.kind === 'subjective'
      ? `round-${payload.round}`
      : `must-pass-recheck-${payload.recheck}`;
  return `reviews/${payload.stage}/attempt-${payload.attempt}/${slot}--${artifactId}-r${revision}.md`;
}

function assertIndependence(independence) {
  if (
    !independence ||
    typeof independence !== 'object' ||
    Array.isArray(independence) ||
    typeof independence.independent !== 'boolean'
  ) {
    throw new Error('independence 必须明确 independent boolean');
  }
  if (independence.independent && independence.limitation !== null) {
    throw new Error('独立 reviewer 的 independence.limitation 必须为 null');
  }
  if (!independence.independent) {
    requireNonEmptyString(independence.limitation, 'independence.limitation');
  }
}

function assertReviewIdentity(state, payload) {
  requireNonEmptyString(payload.stage, 'stage');
  const stageState = state.stages?.[payload.stage];
  if (!stageState) throw new Error(`未知 review stage：${payload.stage}`);
  if (state.currentStage !== payload.stage) {
    throw new Error(`review stage 必须匹配 currentStage ${state.currentStage}`);
  }
  if (payload.attempt !== stageState.attempt) {
    throw new Error(`review attempt 必须是当前 attempt ${stageState.attempt}`);
  }
  if (!REVIEW_KINDS.has(payload.kind)) {
    throw new Error('review kind 必须是 subjective 或 must_pass_recheck');
  }

  if (payload.kind === 'subjective') {
    if (stageState.status !== 'running') {
      throw new Error('subjective review 只允许 stage.status=running');
    }
    if (payload.round !== stageState.subjectiveRound + 1) {
      throw new Error('subjective round 必须连续且只能为 1 或 2');
    }
    if (payload.round !== 1 && payload.round !== 2) {
      throw new Error('subjective round 只能为 1 或 2');
    }
    if (payload.recheck !== null) {
      throw new Error('subjective review 的 recheck 必须为 null');
    }
    if (state.status === 'blocked') {
      throw new Error('blocked review 必须使用 must_pass_recheck');
    }
  } else {
    if (!Number.isInteger(payload.recheck) || payload.recheck <= 0) {
      throw new Error('must-pass recheck 必须是正整数');
    }
    if (payload.recheck !== stageState.recheckCount + 1) {
      throw new Error('must-pass recheck 必须连续递增');
    }
    if (payload.round !== null) {
      throw new Error('must-pass recheck 的 round 必须为 null');
    }
    if (state.status !== 'blocked' || stageState.status !== 'blocked') {
      throw new Error('must-pass recheck 只允许恢复 blocked review');
    }
  }
}

function assertReviewBinding(payload) {
  requireNonEmptyString(payload.reviewer, 'reviewer');
  assertIndependence(payload.independence);
  if (payload.rubricRef !== canonicalRubricRef(payload.stage)) {
    throw new Error(
      `rubricRef 必须是 canonical binding ${canonicalRubricRef(payload.stage)}`,
    );
  }
  requireSha256(payload.rubricSha256, 'rubricSha256');
  requireSha256(payload.reviewSha256, 'reviewSha256');
  requireSha256(payload.artifactSha256, 'artifactSha256');
  parseArtifactRef(payload.artifactRef);
  if (payload.reviewPath !== expectedReviewPath(payload)) {
    throw new Error(`reviewPath 必须是 ${expectedReviewPath(payload)}`);
  }
  if (payload.rubricPath !== undefined) {
    throw new Error('review event 不得持久化 rubricPath');
  }
}

function assertReviewResult(payload) {
  if (!MUST_PASS_RESULTS.has(payload.mustPass)) {
    throw new Error('mustPass 必须是 passed 或 failed');
  }
  if (payload.mustPass === 'failed') {
    if (payload.decision !== 'blocked') {
      throw new Error('mustPass failed 的 decision 必须是 blocked');
    }
    if (payload.weightedScore !== null) {
      throw new Error('mustPass failed 的 weightedScore 必须为 null');
    }
    return;
  }
  if (payload.kind === 'must_pass_recheck') {
    if (payload.weightedScore !== null) {
      throw new Error('must-pass recheck 的 weightedScore 必须为 null');
    }
  } else if (
    typeof payload.weightedScore !== 'number' ||
    !Number.isFinite(payload.weightedScore) ||
    payload.weightedScore < 0 ||
    payload.weightedScore > 5
  ) {
    throw new Error('subjective weightedScore 必须是 0 到 5 的有限数字');
  }
  if (!PASSED_DECISIONS.has(payload.decision)) {
    throw new Error('passed review decision 无效');
  }
  if (
    payload.kind === 'subjective' &&
    payload.round === 2 &&
    payload.decision === 'revise_once'
  ) {
    throw new Error('subjective round 2 禁止 revise_once');
  }
}

function updateReviewProjection(state, event) {
  const payload = event.payload;
  const previousStage = state.stages[payload.stage];
  const stage = {
    ...previousStage,
    latestReview: { ...cloneJson(payload), eventId: event.eventId, at: event.at },
    subjectiveRound:
      payload.kind === 'subjective' && payload.mustPass === 'passed'
        ? payload.round
        : previousStage.subjectiveRound,
    recheckCount:
      payload.kind === 'must_pass_recheck'
        ? payload.recheck
        : previousStage.recheckCount,
  };
  const changes = {};

  if (payload.mustPass === 'failed') {
    stage.status = 'blocked';
    changes.status = 'blocked';
    changes.resume = { stage: payload.stage, action: 'must_pass_recheck' };
  } else if (payload.kind === 'must_pass_recheck') {
    stage.status = 'running';
    changes.status = 'running';
    changes.resume = null;
  } else if (payload.kind === 'subjective') {
    stage.status = 'running';
    changes.status = 'running';
    changes.resume =
      payload.decision === 'revise_once'
        ? { stage: payload.stage, action: 'revise_once' }
        : null;
  }

  const next = {
    ...state,
    ...changes,
    stages: { ...state.stages, [payload.stage]: stage },
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

export function reviewEventReducer(state, event) {
  if (event.type !== REVIEW_EVENT_TYPE) return null;
  assertStateIntegrity(state);
  if (event.beforeStateHash !== state.stateHash) {
    throw new Error('review_recorded.beforeStateHash 不一致');
  }
  assertReviewIdentity(state, event.payload ?? {});
  assertReviewBinding(event.payload);
  assertReviewResult(event.payload);
  if (event.actor !== event.payload.reviewer) {
    throw new Error('review event actor 必须等于 reviewer');
  }
  return updateReviewProjection(state, event);
}

export function createReviewEvent(state, payload, metadata) {
  assertStateIntegrity(state);
  requireNonEmptyString(metadata?.eventId, 'eventId');
  requireNonEmptyString(metadata?.at, 'at');
  requireNonEmptyString(metadata?.actor, 'actor');
  const event = {
    sequence: state.eventSequence + 1,
    eventId: metadata.eventId,
    type: REVIEW_EVENT_TYPE,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(payload),
    afterStateHash: null,
  };
  const nextState = reviewEventReducer(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}
