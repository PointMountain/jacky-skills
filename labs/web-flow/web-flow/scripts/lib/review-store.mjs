import { createHash } from 'node:crypto';
import { lstat, readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  readArtifactLedger,
} from './artifact-ledger.mjs';
import {
  hashArtifact,
  normalizeProjectRelativePath,
} from './artifact-store.mjs';
import { createReviewEvent } from './review-contract.mjs';
import {
  appendRuntimeEvent,
  assertProjectionMatchesEvents,
  readRuntimeEvents,
} from './runtime-store.mjs';
import { projectRootFromRunDir } from './source-safety.mjs';
import { canonicalJson } from './state-contract.mjs';

const ARTIFACT_REF_PATTERN =
  /^([a-z0-9]+(?:[._-][a-z0-9]+)*)@([1-9]\d*)$/u;

function rawSha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

function parseArtifactRef(artifactRef) {
  const match = ARTIFACT_REF_PATTERN.exec(artifactRef ?? '');
  if (!match) throw new Error('artifactRef 必须是 artifactId@revision');
  return { artifactId: match[1], revision: Number(match[2]) };
}

async function readPlainFile(filePath, label) {
  const stats = await lstat(filePath);
  if (stats.isSymbolicLink()) throw new Error(`${label} 不能是符号链接`);
  if (!stats.isFile()) throw new Error(`${label} 必须是普通文件`);
  return readFile(filePath);
}

async function readRunRelativeFile(runDir, relativePath, label) {
  const normalized = normalizeProjectRelativePath(relativePath);
  if (normalized !== relativePath) {
    throw new Error(`${label} 必须是规范的 run 相对 POSIX 路径`);
  }

  let current = path.resolve(runDir);
  for (const segment of normalized.split('/')) {
    current = path.join(current, segment);
    const stats = await lstat(current);
    if (stats.isSymbolicLink()) {
      throw new Error(`${label} 路径不能包含符号链接`);
    }
  }
  return readPlainFile(current, label);
}

export async function readRunFileBinding(runDir, relativePath, label) {
  const contents = await readRunRelativeFile(runDir, relativePath, label);
  return { contents, sha256: rawSha256(contents) };
}

export async function readLatestArtifactBinding(runDir, artifactRef, stage) {
  const { artifactId, revision } = parseArtifactRef(artifactRef);
  const ledger = await readArtifactLedger(runDir);
  const latest = ledger
    .filter((record) => record.artifactId === artifactId)
    .at(-1);
  if (!latest) throw new Error(`artifact ${artifactId} 不存在`);
  if (latest.revision !== revision) {
    throw new Error(`artifactRef 必须引用最新 revision ${latest.revision}`);
  }
  if (latest.producer !== stage) {
    throw new Error(`artifact producer ${latest.producer} 必须匹配 review stage ${stage}`);
  }

  const projectRoot = await projectRootFromRunDir(runDir);
  const live = await hashArtifact({
    projectRoot,
    artifactPath: latest.path,
  });
  if (live.sha256 !== latest.sha256) {
    throw new Error('artifact 实时 hash 与 ledger 发生漂移');
  }
  return { artifactRef, artifactSha256: live.sha256 };
}

function findRegisteredReview(events, reviewPath) {
  return events.find(
    (event) =>
      event.type === 'review_recorded' &&
      event.payload?.reviewPath === reviewPath,
  );
}

export async function recordReview({
  runDir,
  stage,
  attempt,
  kind,
  round,
  recheck,
  reviewer,
  independence,
  rubricRef,
  rubricPath,
  reviewPath,
  artifactRef,
  mustPass,
  decision,
  weightedScore,
  metadata,
}) {
  const { state } = await assertProjectionMatchesEvents(runDir);
  const review = await readRunFileBinding(
    runDir,
    reviewPath,
    'review Markdown',
  );
  const rubricContents = await readPlainFile(rubricPath, 'rubric Markdown');
  const artifact = await readLatestArtifactBinding(runDir, artifactRef, stage);
  const payload = {
    stage,
    attempt,
    kind,
    round,
    recheck,
    reviewer,
    independence,
    rubricRef,
    rubricSha256: rawSha256(rubricContents),
    reviewPath,
    reviewSha256: review.sha256,
    ...artifact,
    mustPass,
    decision,
    weightedScore,
  };

  const events = await readRuntimeEvents(runDir);
  const registered = findRegisteredReview(events, reviewPath);
  if (registered) {
    if (registered.payload.reviewSha256 !== payload.reviewSha256) {
      throw new Error('已登记 review Markdown 发生漂移，禁止覆盖');
    }
    if (registered.eventId !== metadata?.eventId) {
      throw new Error('reviewPath 已登记，必须创建下一版本路径');
    }
    if (canonicalJson(registered.payload) !== canonicalJson(payload)) {
      throw new Error('重复 eventId 的 review binding 不一致');
    }
    const stored = await appendRuntimeEvent(runDir, registered);
    return { ...stored, event: registered };
  }

  const { event } = createReviewEvent(state, payload, metadata);
  const stored = await appendRuntimeEvent(runDir, event);
  return { ...stored, event };
}
