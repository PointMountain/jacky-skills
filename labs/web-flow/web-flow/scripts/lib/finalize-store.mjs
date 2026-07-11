import { createFinalizationEvent } from './finalize-contract.mjs';
import { readRunFileBinding } from './review-store.mjs';
import {
  appendRuntimeEvent,
  assertProjectionMatchesEvents,
} from './runtime-store.mjs';
import { validateRun } from './validators.mjs';

const TERMINAL_STATUSES = new Set([
  'success',
  'partial',
  'failed',
  'cancelled',
]);

export async function finalizeRun({
  runDir,
  status,
  reason,
  supersededBy = null,
  metadata,
}, dependencies = {}) {
  await validateRun(runDir, dependencies);
  const { state } = await assertProjectionMatchesEvents(runDir);
  if (TERMINAL_STATUSES.has(state.status) || state.finalization) {
    throw new Error('terminal/finalized run 不可再次 finalize');
  }

  const skillUsage = await readRunFileBinding(
    runDir,
    'skill-usage.md',
    'skill usage',
  );
  const retrospective = await readRunFileBinding(
    runDir,
    'retrospective.md',
    'retrospective',
  );
  const payload = {
    status,
    reason,
    supersededBy,
    skillUsage: { path: 'skill-usage.md', sha256: skillUsage.sha256 },
    retrospective: {
      path: 'retrospective.md',
      sha256: retrospective.sha256,
    },
  };
  const { event } = createFinalizationEvent(state, payload, metadata);
  const stored = await appendRuntimeEvent(runDir, event);
  const validation = await validateRun(runDir, {
    ...dependencies,
    requireTerminal: true,
  });
  return { ...stored, event, validation };
}
