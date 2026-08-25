import { assertSupersessionAllowed } from './workflow-contract.mjs';

const TERMINAL_STATUSES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);
const G3_APPROVALS = new Set(['approved', 'auto_approved']);

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new TypeError(`${label} 必须是非空字符串`);
  }
}

function assertCurrentPreview(state, status) {
  const g3 = state.gates?.G3;
  if (
    state.stages?.build?.status !== 'completed' ||
    !G3_APPROVALS.has(g3?.decision) ||
    !g3.latestDecision?.artifactRef ||
    !g3.latestDecision?.artifactSha256
  ) {
    throw new Error(`${status} 要求 build completed、G3 approved 和当前 preview binding`);
  }
  return g3.latestDecision;
}

function assertDeploymentSuccess(state, g3) {
  if (!state.deployment.requested) return;
  const result = state.deployment.latestResult;
  if (
    !state.deployment.authorized ||
    result?.status !== 'success' ||
    state.stages?.deploy?.status !== 'completed'
  ) {
    throw new Error('deployment requested 的 success 要求 authorized、成功结果和 deploy completed；否则只能 partial');
  }
  if (
    result.buildRef !== g3.artifactRef ||
    result.buildSha256 !== g3.artifactSha256
  ) {
    throw new Error('deployment success build hash 必须匹配当前 G3 preview');
  }
}

function assertCancelledActor(state, actor) {
  if (actor === 'user') return;
  if (actor === 'web-flow-runtime' && state.pendingTerminal === 'cancelled') {
    return;
  }
  throw new Error('cancelled 必须由 actor=user 主动提交，或由 pendingTerminal gate rejection 的 runtime finalize');
}

export function assertTerminalTransitionAllowed(state, payload, actor) {
  if (!TERMINAL_STATUSES.has(payload?.status)) {
    throw new Error('terminal status 必须是 success、partial、failed 或 cancelled');
  }
  requireNonEmptyString(payload.reason, `${payload.status}.reason`);

  if (payload.status === 'success' || payload.status === 'partial') {
    const g3 = assertCurrentPreview(state, payload.status);
    if (payload.status === 'success') assertDeploymentSuccess(state, g3);
  }
  if (payload.status === 'cancelled') assertCancelledActor(state, actor);

  if (payload.supersededBy !== null) {
    if (payload.status !== 'cancelled' && payload.status !== 'partial') {
      throw new Error('supersededBy 只允许 cancelled 或 partial');
    }
    assertSupersessionAllowed(
      state,
      payload.status,
      payload.supersededBy,
    );
  }
  return true;
}
