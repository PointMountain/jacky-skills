import { canonicalJson, computeStateHash } from './state-contract.mjs';
import { assertTerminalTransitionAllowed } from './terminal-validator.mjs';

const FINALIZE_EVENT_TYPE = 'run_finalized';
const TERMINAL_STATUSES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/u;

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
  if (TERMINAL_STATUSES.has(state.status) || state.finalization) {
    throw new Error('terminal/finalized run 不可再次写入');
  }
}

function assertDocumentBinding(binding, expectedPath, label) {
  if (!binding || binding.path !== expectedPath) {
    throw new Error(`${label}.path 必须是 ${expectedPath}`);
  }
  if (
    typeof binding.sha256 !== 'string' ||
    !SHA256_PATTERN.test(binding.sha256)
  ) {
    throw new Error(`${label}.sha256 必须是小写 SHA-256`);
  }
}

function assertFinalizePayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new TypeError('finalize payload 必须是对象');
  }
  assertDocumentBinding(payload.skillUsage, 'skill-usage.md', 'skillUsage');
  assertDocumentBinding(
    payload.retrospective,
    'retrospective.md',
    'retrospective',
  );
  if (
    payload.supersededBy !== null &&
    typeof payload.supersededBy !== 'string'
  ) {
    throw new Error('supersededBy 必须是 null 或安全 runId');
  }
}

function applyFinalization(state, event) {
  const { pendingTerminal: _pendingTerminal, ...base } = state;
  const next = {
    ...base,
    status: event.payload.status,
    currentStage: null,
    resume: null,
    terminalReason: event.payload.reason,
    supersededBy: event.payload.supersededBy,
    finalization: {
      skillUsage: cloneJson(event.payload.skillUsage),
      retrospective: cloneJson(event.payload.retrospective),
      eventId: event.eventId,
      at: event.at,
      actor: event.actor,
    },
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

export function finalizationEventReducer(state, event) {
  if (event.type !== FINALIZE_EVENT_TYPE) return null;
  assertStateIntegrity(state);
  if (event.beforeStateHash !== state.stateHash) {
    throw new Error('run_finalized.beforeStateHash 不一致');
  }
  assertFinalizePayload(event.payload);
  assertTerminalTransitionAllowed(state, event.payload, event.actor);
  return applyFinalization(state, event);
}

export function createFinalizationEvent(state, payload, metadata) {
  assertStateIntegrity(state);
  requireNonEmptyString(metadata?.eventId, 'eventId');
  requireNonEmptyString(metadata?.at, 'at');
  requireNonEmptyString(metadata?.actor, 'actor');
  const event = {
    sequence: state.eventSequence + 1,
    eventId: metadata.eventId,
    type: FINALIZE_EVENT_TYPE,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(payload),
    afterStateHash: null,
  };
  const nextState = finalizationEventReducer(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}
