import { canonicalJson, computeStateHash } from './state-contract.mjs';

const PREFLIGHT_EVENT = 'deployment_preflight_recorded';
const PUBLISH_EVENT = 'deployment_publish_recorded';
const FACT_RESULTS = new Set(['passed', 'failed']);
const G3_APPROVALS = new Set(['approved', 'auto_approved']);
const SHA256_PATTERN = /^[a-f0-9]{64}$/u;
const ARTIFACT_REF_PATTERN =
  /^[a-z0-9]+(?:[._-][a-z0-9]+)*@[1-9]\d*$/u;
const TERMINAL_RUN_STATES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);

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
    throw new Error(`terminal run ${state.status} 不可登记 deployment evidence`);
  }
}

function assertDeploymentAuthorized(state, payload) {
  if (!state.deployment?.requested || !state.deployment?.authorized) {
    throw new Error('deployment 必须 requested 且 authorized');
  }
  requireNonEmptyString(payload.provider, 'provider');
  if (payload.provider !== state.deployment.provider) {
    throw new Error('deployment provider 必须匹配 run state');
  }
}

function assertEvidence(payload, expectedPath) {
  if (payload.evidencePath !== expectedPath) {
    throw new Error(`evidencePath 必须是 ${expectedPath}`);
  }
  requireSha256(payload.evidenceSha256, 'evidenceSha256');
}

function assertFacts(facts, labels) {
  if (!facts || typeof facts !== 'object' || Array.isArray(facts)) {
    throw new Error('facts/checks 必须是对象');
  }
  for (const label of labels) {
    if (!FACT_RESULTS.has(facts[label])) {
      throw new Error(`${label} 必须是 passed 或 failed`);
    }
  }
}

function withDeploymentResult(state, event, deployment, changes = {}) {
  const next = {
    ...state,
    ...changes,
    deployment,
    eventSequence: event.sequence,
    updatedAt: event.at,
  };
  return { ...next, stateHash: computeStateHash(next) };
}

function applyPreflight(state, event) {
  const payload = event.payload;
  assertDeploymentAuthorized(state, payload);
  if (state.deployment.preflight) {
    throw new Error('deployment preflight 只能登记一次，禁止覆盖');
  }
  assertEvidence(payload, 'preflight/deployment-readiness.md');
  if (!FACT_RESULTS.has(payload.status)) {
    throw new Error('preflight status 必须是 passed 或 failed');
  }
  assertFacts(payload.checks, ['cli', 'identity', 'project']);
  const checkResults = ['cli', 'identity', 'project'].map(
    (key) => payload.checks[key],
  );
  if (
    (payload.status === 'passed' &&
      checkResults.some((result) => result !== 'passed')) ||
    (payload.status === 'failed' && !checkResults.includes('failed'))
  ) {
    throw new Error('preflight status 必须与 checks passed/failed 一致');
  }
  return withDeploymentResult(state, event, {
    ...state.deployment,
    preflight: { ...cloneJson(payload), eventId: event.eventId, at: event.at },
  });
}

function requireHttpsUrl(value, label) {
  requireNonEmptyString(value, label);
  let parsed;
  try {
    parsed = new URL(value);
  } catch (error) {
    throw new Error(`${label} 必须是合法 HTTPS URL`, { cause: error });
  }
  if (parsed.protocol !== 'https:') {
    throw new Error(`${label} 必须是 HTTPS URL`);
  }
}

function assertPublishPreconditions(state, payload) {
  assertDeploymentAuthorized(state, payload);
  if (state.deployment.latestResult) {
    throw new Error('deployment publish evidence 已登记，禁止覆盖');
  }
  if (
    state.currentStage !== 'deploy' ||
    state.stages?.deploy?.status !== 'running'
  ) {
    throw new Error('publish 要求 deploy stage running');
  }
  const g3 = state.gates?.G3;
  if (!G3_APPROVALS.has(g3?.decision) || !g3.latestDecision) {
    throw new Error('publish 要求 G3 approved');
  }
  if (
    payload.buildRef !== g3.latestDecision.artifactRef ||
    payload.buildSha256 !== g3.latestDecision.artifactSha256
  ) {
    throw new Error('publish build binding 必须匹配 G3 latestDecision');
  }
  if (!ARTIFACT_REF_PATTERN.test(payload.buildRef ?? '')) {
    throw new Error('buildRef 必须是 artifactId@revision');
  }
  requireSha256(payload.buildSha256, 'buildSha256');
}

function assertLatePreflight(latePreflight) {
  if (
    !latePreflight ||
    latePreflight.rechecked !== true ||
    latePreflight.status !== 'passed'
  ) {
    throw new Error('latePreflight 必须 rechecked=true 且 status=passed');
  }
  requireNonEmptyString(latePreflight.at, 'latePreflight.at');
}

function assertPublishResult(payload) {
  assertFacts(payload.facts, ['http', 'browser', 'console']);
  if (payload.status !== 'success' && payload.status !== 'failed') {
    throw new Error('publish status 必须是 success 或 failed');
  }
  const results = ['http', 'browser', 'console'].map(
    (key) => payload.facts[key],
  );
  if (payload.status === 'success') {
    if (results.some((result) => result !== 'passed')) {
      throw new Error('publish success 要求三项 facts 全部 passed');
    }
    requireHttpsUrl(payload.productionUrl, 'productionUrl');
    return;
  }
  if (!results.includes('failed')) {
    throw new Error('publish failed 要求至少一项 fact failed');
  }
  if (payload.productionUrl !== null) {
    requireHttpsUrl(payload.productionUrl, 'productionUrl');
  }
}

function applyPublish(state, event) {
  const payload = event.payload;
  assertPublishPreconditions(state, payload);
  assertEvidence(payload, 'deploy/deployment-evidence.md');
  assertLatePreflight(payload.latePreflight);
  assertPublishResult(payload);
  const latestResult = {
    ...cloneJson(payload),
    eventId: event.eventId,
    at: event.at,
  };
  const deployment = { ...state.deployment, latestResult };
  if (payload.status === 'success') {
    return withDeploymentResult(state, event, deployment);
  }
  return withDeploymentResult(
    state,
    event,
    deployment,
    {
      status: 'blocked',
      stages: {
        ...state.stages,
        deploy: { ...state.stages.deploy, status: 'blocked' },
      },
      resume: { stage: 'deploy', action: 'finalize_partial' },
    },
  );
}

export function deploymentEventReducer(state, event) {
  if (event.type !== PREFLIGHT_EVENT && event.type !== PUBLISH_EVENT) {
    return null;
  }
  assertStateIntegrity(state);
  if (event.beforeStateHash !== state.stateHash) {
    throw new Error(`${event.type}.beforeStateHash 不一致`);
  }
  return event.type === PREFLIGHT_EVENT
    ? applyPreflight(state, event)
    : applyPublish(state, event);
}

export function createDeploymentEvent(state, mode, payload, metadata) {
  assertStateIntegrity(state);
  if (mode !== 'preflight' && mode !== 'publish') {
    throw new Error('deployment mode 必须是 preflight 或 publish');
  }
  requireNonEmptyString(metadata?.eventId, 'eventId');
  requireNonEmptyString(metadata?.at, 'at');
  requireNonEmptyString(metadata?.actor, 'actor');
  const event = {
    sequence: state.eventSequence + 1,
    eventId: metadata.eventId,
    type: mode === 'preflight' ? PREFLIGHT_EVENT : PUBLISH_EVENT,
    at: metadata.at,
    actor: metadata.actor,
    beforeStateHash: state.stateHash,
    payload: cloneJson(payload),
    afterStateHash: null,
  };
  const nextState = deploymentEventReducer(state, event);
  event.afterStateHash = nextState.stateHash;
  return { event, state: nextState };
}
