import { createHash } from 'node:crypto';

export const SCHEMA_VERSION = 3;
export const SAFE_RUN_ID_PATTERN = /^\d{8}T\d{6}Z-[a-z0-9]{4,12}$/;

const INITIAL_EVENT_TYPE = 'run_initialized';
const SOURCE_PLAN_EVENT_TYPE = 'source_plan_recorded';
const SOURCE_MODES = new Set(['create', 'update']);
const INTERACTION_MODES = new Set(['attended', 'unattended']);
const PROFILE_REQUESTS = new Set(['fast', 'full', 'adaptive']);

function assertJsonValue(value, path = '$') {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'boolean'
  ) {
    return;
  }

  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new TypeError(`${path} 必须是有限数字`);
    }
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item, index) => assertJsonValue(item, `${path}[${index}]`));
    return;
  }

  if (typeof value === 'object') {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new TypeError(`${path} 不是合法 JSON 对象`);
    }
    for (const [key, item] of Object.entries(value)) {
      if (item === undefined) {
        throw new TypeError(`${path}.${key} 不能是 undefined`);
      }
      assertJsonValue(item, `${path}.${key}`);
    }
    return;
  }

  throw new TypeError(`${path} 不是合法 JSON 值`);
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }

  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonicalize(value[key])]),
    );
  }

  return value;
}

function cloneJson(value) {
  return JSON.parse(canonicalJson(value));
}

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new TypeError(`${label} 必须是非空字符串`);
  }
}

function requireAllowedValue(value, allowedValues, label) {
  if (!allowedValues.has(value)) {
    throw new TypeError(
      `${label} 必须是 ${[...allowedValues].join('、')} 之一`,
    );
  }
}

function assertInitializationInput(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new TypeError('初始化输入必须是对象');
  }
  if (
    typeof input.runId !== 'string' ||
    !SAFE_RUN_ID_PATTERN.test(input.runId)
  ) {
    throw new Error('run id 不安全');
  }

  requireNonEmptyString(input.intent, 'intent');
  requireNonEmptyString(input.projectRoot, 'projectRoot');
  requireNonEmptyString(input.source?.dir, 'source.dir');
  requireAllowedValue(input.source?.mode, SOURCE_MODES, 'source.mode');
  requireAllowedValue(
    input.interactionMode,
    INTERACTION_MODES,
    'interactionMode',
  );
  requireAllowedValue(
    input.profile?.requested,
    PROFILE_REQUESTS,
    'profile.requested',
  );

  if (!input.deployment || typeof input.deployment !== 'object') {
    throw new TypeError('deployment 必须是对象');
  }
  if (typeof input.deployment.requested !== 'boolean') {
    throw new TypeError('deployment.requested 必须是 boolean');
  }
  if (typeof input.deployment.authorized !== 'boolean') {
    throw new TypeError('deployment.authorized 必须是 boolean');
  }
  if (
    input.deployment.provider !== null &&
    (typeof input.deployment.provider !== 'string' ||
      input.deployment.provider.length === 0)
  ) {
    throw new TypeError('deployment.provider 必须是 null 或非空字符串');
  }
  if (input.deployment.authorized && !input.deployment.requested) {
    throw new Error('deployment.authorized 不能在 requested=false 时为 true');
  }
  assertJsonValue(input);
}

function assertEventMetadata(metadata) {
  if (!metadata || typeof metadata !== 'object') {
    throw new TypeError('事件元数据必须是对象');
  }
  requireNonEmptyString(metadata.eventId, 'eventId');
  requireNonEmptyString(metadata.at, 'at');
  requireNonEmptyString(metadata.actor, 'actor');
}

function assertReplayEvent(event) {
  try {
    assertJsonValue(event, 'event');
  } catch (error) {
    throw new TypeError(`event 不是合法 JSON 结构：${error.message}`, {
      cause: error,
    });
  }

  requireNonEmptyString(event.eventId, 'event.eventId');
  requireNonEmptyString(event.at, 'event.at');
  requireNonEmptyString(event.actor, 'event.actor');
}

function assertCanonicalPaths(paths, label, allowEmpty = false) {
  if (!Array.isArray(paths) || (!allowEmpty && paths.length === 0)) {
    throw new Error(`${label} 必须是${allowEmpty ? '' : '非空'}数组`);
  }
  for (const candidate of paths) {
    if (
      typeof candidate !== 'string' ||
      candidate === '.' ||
      candidate.startsWith('/') ||
      candidate.includes('\\') ||
      candidate.split('/').some((segment) => !segment || segment === '.' || segment === '..') ||
      candidate === '.web-flow' ||
      candidate.startsWith('.web-flow/')
    ) {
      throw new Error(`${label} 必须是规范的项目相对路径`);
    }
  }
  const canonical = [...new Set(paths)].sort();
  if (canonical.length !== paths.length || canonical.some((item, index) => item !== paths[index])) {
    throw new Error(`${label} 必须排序且无重复`);
  }
}

function applySourcePlanEvent(state, event) {
  if (state.source?.mode !== 'update' || !state.source.baseline) {
    throw new Error('source_plan_recorded 仅适用于含 baseline 的 update run');
  }
  if (state.source.plan) throw new Error('source plan 不得覆盖');
  assertCanonicalPaths(event.payload?.allowlist, 'allowlist');
  assertCanonicalPaths(
    event.payload?.confirmedDirtyPaths,
    'confirmedDirtyPaths',
    true,
  );
  if (event.payload.confirmedDirtyPaths.length > 0 && event.actor !== 'user') {
    throw new Error('confirmedDirtyPaths 要求 actor=user');
  }
  const overlaps = state.source.baseline.dirty
    .filter((dirty) =>
      event.payload.allowlist.some(
        (allowed) =>
          allowed === dirty.path ||
          dirty.path.startsWith(`${allowed}/`) ||
          allowed.startsWith(`${dirty.path}/`),
      ),
    )
    .map((dirty) => dirty.path)
    .sort();
  if (canonicalJson(overlaps) !== canonicalJson(event.payload.confirmedDirtyPaths)) {
    throw new Error('confirmedDirtyPaths 必须精确列出 dirty overlap');
  }
  const next = {
    ...state,
    source: {
      ...state.source,
      plan: {
        allowlist: cloneJson(event.payload.allowlist),
        confirmedDirtyPaths: cloneJson(event.payload.confirmedDirtyPaths),
        recordedAt: event.at,
        recordedBy: event.actor,
      },
    },
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

function createInitialStage() {
  return { status: 'not_started', attempt: 1, latestReview: null,
    subjectiveRound: 0, recheckCount: 0 };
}

function createInitialProjection(payload, updatedAt) {
  assertInitializationInput(payload);

  const projection = {
    schemaVersion: SCHEMA_VERSION,
    runId: payload.runId,
    intent: payload.intent,
    projectRoot: payload.projectRoot,
    source: cloneJson(payload.source),
    interactionMode: payload.interactionMode,
    profile: {
      requested: payload.profile.requested,
      resolved: null,
      lockedAt: null,
    },
    deployment: cloneJson(payload.deployment),
    status: 'running',
    currentStage: 'research',
    stages: {
      research: createInitialStage(),
      wireframe: createInitialStage(),
      prototype: createInitialStage(),
      design: createInitialStage(),
      build: createInitialStage(),
      deploy: createInitialStage(),
    },
    gates: {
      G1: { decision: 'pending', decisionCount: 0, latestDecision: null },
      G2: { decision: 'pending', decisionCount: 0, latestDecision: null },
      G3: { decision: 'pending', decisionCount: 0, latestDecision: null },
    },
    resume: { stage: 'research', action: 'start' },
    eventSequence: 1,
    supersededBy: null,
    updatedAt,
  };

  return { ...projection, stateHash: computeStateHash(projection) };
}

export function canonicalJson(value) {
  assertJsonValue(value);
  return JSON.stringify(canonicalize(value));
}

export function computeStateHash(state) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new TypeError('state 必须是对象');
  }

  const { stateHash: _ignored, ...hashableState } = state;
  return createHash('sha256')
    .update(canonicalJson(hashableState))
    .digest('hex');
}

export function createRunInitialization(input, metadata) {
  assertInitializationInput(input);
  assertEventMetadata(metadata);

  const payload = cloneJson(input);
  const state = createInitialProjection(payload, metadata.at);
  const event = {
    sequence: 1,
    eventId: metadata.eventId,
    type: INITIAL_EVENT_TYPE,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: null,
    payload,
    afterStateHash: state.stateHash,
  };

  return { event, state };
}

export function createSourcePlanEvent(state, payload, metadata) {
  assertEventMetadata(metadata);
  if (computeStateHash(state) !== state.stateHash) {
    throw new Error('当前 stateHash 不一致');
  }
  const event = {
    sequence: state.eventSequence + 1,
    eventId: metadata.eventId,
    type: SOURCE_PLAN_EVENT_TYPE,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(payload),
    afterStateHash: null,
  };
  const nextState = applySourcePlanEvent(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}

export function replayEvents(events, externalReducer = null) {
  if (!Array.isArray(events) || events.length === 0) {
    throw new Error('events 必须包含 run_initialized 首事件');
  }

  const eventIds = new Set();
  let state = null;

  for (const [index, event] of events.entries()) {
    assertReplayEvent(event);
    const expectedSequence = index + 1;
    if (event?.sequence !== expectedSequence) {
      throw new Error(`event sequence 必须连续，预期 ${expectedSequence}`);
    }
    if (eventIds.has(event.eventId)) {
      throw new Error(`eventId 重复：${event.eventId}`);
    }
    eventIds.add(event.eventId);

    if (event.type === INITIAL_EVENT_TYPE) {
      if (state !== null || expectedSequence !== 1) {
        throw new Error('run_initialized 只能是首个事件');
      }
      if (event.beforeStateHash !== null) {
        throw new Error('run_initialized.beforeStateHash 必须为 null');
      }
      state = createInitialProjection(event.payload, event.at);
    } else if (event.type === SOURCE_PLAN_EVENT_TYPE && state !== null) {
      if (event.beforeStateHash !== state.stateHash) {
        throw new Error('source_plan_recorded.beforeStateHash 不一致');
      }
      state = applySourcePlanEvent(state, event);
    } else if (state !== null && externalReducer) {
      const reduced = externalReducer(state, event);
      if (reduced === null || reduced === undefined) {
        throw new Error(`Unknown event type: ${String(event.type)}`);
      }
      state = reduced;
    } else {
      throw new Error(`Unknown event type: ${String(event.type)}`);
    }
    if (event.afterStateHash !== state.stateHash) {
      throw new Error('事件 afterStateHash 与重放投影不一致');
    }
  }

  return state;
}
