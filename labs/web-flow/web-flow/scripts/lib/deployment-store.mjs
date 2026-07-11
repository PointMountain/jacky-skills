import { createDeploymentEvent } from './deployment-contract.mjs';
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

const EVIDENCE_PATHS = Object.freeze({
  preflight: 'preflight/deployment-readiness.md',
  publish: 'deploy/deployment-evidence.md',
});
const EVENT_TYPES = Object.freeze({
  preflight: 'deployment_preflight_recorded',
  publish: 'deployment_publish_recorded',
});

function findRegisteredEvidence(events, mode) {
  return events.find(
    (event) =>
      event.type === EVENT_TYPES[mode] &&
      event.payload?.evidencePath === EVIDENCE_PATHS[mode],
  );
}

async function storeDeploymentEvent({
  runDir,
  mode,
  state,
  payload,
  metadata,
}) {
  const events = await readRuntimeEvents(runDir);
  const registered = findRegisteredEvidence(events, mode);
  if (registered) {
    if (registered.payload.evidenceSha256 !== payload.evidenceSha256) {
      throw new Error('已登记 deployment evidence 发生漂移，禁止覆盖');
    }
    if (registered.eventId !== metadata?.eventId) {
      throw new Error('deployment evidence 已登记，不得覆盖');
    }
    if (canonicalJson(registered.payload) !== canonicalJson(payload)) {
      throw new Error('重复 eventId 的 deployment binding 不一致');
    }
    const stored = await appendRuntimeEvent(runDir, registered);
    return { ...stored, event: registered };
  }

  const { event } = createDeploymentEvent(state, mode, payload, metadata);
  const stored = await appendRuntimeEvent(runDir, event);
  return { ...stored, event };
}

export async function recordDeploymentPreflight({
  runDir,
  provider,
  status,
  checks,
  metadata,
}) {
  const { state } = await assertProjectionMatchesEvents(runDir);
  const evidence = await readRunFileBinding(
    runDir,
    EVIDENCE_PATHS.preflight,
    'deployment preflight evidence',
  );
  return storeDeploymentEvent({
    runDir,
    mode: 'preflight',
    state,
    metadata,
    payload: {
      provider,
      evidencePath: EVIDENCE_PATHS.preflight,
      evidenceSha256: evidence.sha256,
      status,
      checks,
    },
  });
}

export async function recordDeploymentPublish({
  runDir,
  provider,
  latePreflight,
  facts,
  productionUrl,
  status,
  metadata,
}) {
  const { state } = await assertProjectionMatchesEvents(runDir);
  const g3 = state.gates?.G3?.latestDecision;
  if (!g3) throw new Error('publish 缺少 G3 latestDecision');
  const liveBuild = await readLatestArtifactBinding(
    runDir,
    g3.artifactRef,
    'build',
  );
  if (liveBuild.artifactSha256 !== g3.artifactSha256) {
    throw new Error('G3 build artifact 实时 hash 发生漂移');
  }
  const evidence = await readRunFileBinding(
    runDir,
    EVIDENCE_PATHS.publish,
    'deployment publish evidence',
  );
  return storeDeploymentEvent({
    runDir,
    mode: 'publish',
    state,
    metadata,
    payload: {
      provider,
      evidencePath: EVIDENCE_PATHS.publish,
      evidenceSha256: evidence.sha256,
      buildRef: liveBuild.artifactRef,
      buildSha256: liveBuild.artifactSha256,
      latePreflight,
      facts,
      productionUrl,
      status,
    },
  });
}
