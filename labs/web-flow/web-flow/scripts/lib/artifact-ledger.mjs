import { open, lstat, readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  SAFE_RUN_ID_PATTERN,
  canonicalJson,
} from './state-contract.mjs';
import {
  hashArtifact,
  normalizeProjectRelativePath,
} from './artifact-store.mjs';

const ARTIFACT_ID_PATTERN = /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

function requireArtifactId(value, label = 'artifactId') {
  if (typeof value !== 'string' || !ARTIFACT_ID_PATTERN.test(value)) {
    throw new Error(`${label} 格式无效`);
  }
}

function requireNonEmptyString(value, label) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`${label} 必须是非空字符串`);
  }
}

function requireSha256(value, label = 'sha256') {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    throw new Error(`${label} 必须是小写 SHA-256`);
  }
}

function parseArtifactRef(artifactRef) {
  if (typeof artifactRef !== 'string') {
    throw new Error('reusedFrom.artifactRef 格式无效');
  }
  const separator = artifactRef.lastIndexOf('@');
  const artifactId = artifactRef.slice(0, separator);
  const revisionText = artifactRef.slice(separator + 1);
  requireArtifactId(artifactId, 'reusedFrom.artifactRef');
  if (!/^[1-9]\d*$/u.test(revisionText)) {
    throw new Error('reusedFrom.artifactRef revision 格式无效');
  }
  return { artifactId, revision: Number(revisionText) };
}

function validateReusedFrom(reusedFrom) {
  if (!reusedFrom || typeof reusedFrom !== 'object' || Array.isArray(reusedFrom)) {
    throw new Error('reusedFrom 必须是对象');
  }
  if (
    typeof reusedFrom.runId !== 'string' ||
    !SAFE_RUN_ID_PATTERN.test(reusedFrom.runId)
  ) {
    throw new Error('reusedFrom.runId 格式无效');
  }
  parseArtifactRef(reusedFrom.artifactRef);
  requireSha256(reusedFrom.sha256, 'reusedFrom.sha256');
  if (Object.keys(reusedFrom).sort().join(',') !== 'artifactRef,runId,sha256') {
    throw new Error('reusedFrom 只能包含 runId、artifactRef、sha256');
  }
}

async function requirePlainPath(filePath, expectedKind, label) {
  const stats = await lstat(filePath);
  if (stats.isSymbolicLink()) throw new Error(`${label} 不能是符号链接`);
  if (expectedKind === 'directory' && !stats.isDirectory()) {
    throw new Error(`${label} 必须是目录`);
  }
  if (expectedKind === 'file' && !stats.isFile()) {
    throw new Error(`${label} 必须是普通文件`);
  }
}

async function deriveRunContext(runDir) {
  if (typeof runDir !== 'string' || runDir.length === 0) {
    throw new Error('runDir 必须是非空路径');
  }
  const absoluteRunDir = path.resolve(runDir);
  const runsDir = path.dirname(absoluteRunDir);
  const runtimeDir = path.dirname(runsDir);
  const runId = path.basename(absoluteRunDir);

  if (
    path.basename(runsDir) !== 'runs' ||
    path.basename(runtimeDir) !== '.web-flow' ||
    !SAFE_RUN_ID_PATTERN.test(runId)
  ) {
    throw new Error('runDir 必须匹配 <projectRoot>/.web-flow/runs/<runId>');
  }

  const ledgerPath = path.join(absoluteRunDir, 'artifacts.jsonl');
  await requirePlainPath(runtimeDir, 'directory', '.web-flow');
  await requirePlainPath(runsDir, 'directory', 'runs');
  await requirePlainPath(absoluteRunDir, 'directory', 'runDir');
  await requirePlainPath(ledgerPath, 'file', 'artifacts.jsonl');
  return {
    projectRoot: path.dirname(runtimeDir),
    runDir: absoluteRunDir,
    runId,
    ledgerPath,
  };
}

function validateLedgerRecord(record, expectedRevision, previousRef) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new Error('artifact ledger 记录必须是对象');
  }
  requireArtifactId(record.artifactId);
  if (record.revision !== expectedRevision) {
    throw new Error(`${record.artifactId} revision 必须单调连续`);
  }
  if (record.supersedes !== previousRef) {
    throw new Error(`${record.artifactId} supersedes 与上一 revision 不一致`);
  }
  if (record.kind !== 'file' && record.kind !== 'directory') {
    throw new Error('artifact kind 必须是 file 或 directory');
  }
  const normalizedPath = normalizeProjectRelativePath(record.path, {
    allowProjectRoot: true,
  });
  if (record.path !== normalizedPath) {
    throw new Error('artifact path 必须是项目相对 POSIX 路径');
  }
  requireSha256(record.sha256);
  requireNonEmptyString(record.producer, 'producer');
  requireNonEmptyString(record.createdAt, 'createdAt');
  if (record.reusedFrom !== undefined) validateReusedFrom(record.reusedFrom);
}

async function readLedger(context) {
  const text = await readFile(context.ledgerPath, 'utf8');
  if (text === '') return [];
  if (!text.endsWith('\n')) {
    throw new Error('artifacts.jsonl 损坏：非空文件必须以末尾换行结束');
  }
  const lines = text.slice(0, -1).split('\n');
  if (lines.some((line) => line.length === 0)) {
    throw new Error('artifacts.jsonl 包含空行');
  }

  const revisions = new Map();
  return lines.map((line, index) => {
    let record;
    try {
      record = JSON.parse(line);
    } catch (error) {
      throw new Error(`artifacts.jsonl 第 ${index + 1} 行不是合法 JSON`, {
        cause: error,
      });
    }
    const previousRevision = revisions.get(record.artifactId) ?? 0;
    const previousRef = previousRevision
      ? `${record.artifactId}@${previousRevision}`
      : null;
    validateLedgerRecord(record, previousRevision + 1, previousRef);
    revisions.set(record.artifactId, record.revision);
    return record;
  });
}

function semanticallyEqual(record, candidate) {
  return (
    record.artifactId === candidate.artifactId &&
    record.kind === candidate.kind &&
    record.path === candidate.path &&
    record.sha256 === candidate.sha256 &&
    record.producer === candidate.producer &&
    canonicalJson(record.reusedFrom ?? null) ===
      canonicalJson(candidate.reusedFrom ?? null)
  );
}

async function appendRecord(context, record) {
  const handle = await open(context.ledgerPath, 'a');
  try {
    await handle.writeFile(`${JSON.stringify(record)}\n`, 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function registerArtifact({
  context,
  artifactId,
  artifactPath,
  producer,
  createdAt,
  reusedFrom,
}) {
  requireArtifactId(artifactId);
  requireNonEmptyString(producer, 'producer');
  requireNonEmptyString(createdAt, 'createdAt');
  const hash = await hashArtifact({
    projectRoot: context.projectRoot,
    artifactPath,
  });
  const ledger = await readLedger(context);
  const previous = ledger.filter((item) => item.artifactId === artifactId).at(-1);
  const candidate = {
    artifactId,
    kind: hash.kind,
    path: hash.path,
    sha256: hash.sha256,
    producer,
    ...(reusedFrom ? { reusedFrom } : {}),
  };

  if (previous && semanticallyEqual(previous, candidate)) {
    return { appended: false, artifact: previous };
  }

  const artifact = {
    artifactId,
    revision: (previous?.revision ?? 0) + 1,
    kind: hash.kind,
    path: hash.path,
    sha256: hash.sha256,
    producer,
    createdAt,
    supersedes: previous
      ? `${previous.artifactId}@${previous.revision}`
      : null,
    ...(reusedFrom ? { reusedFrom } : {}),
  };
  await appendRecord(context, artifact);
  return { appended: true, artifact };
}

export async function readArtifactLedger(runDir) {
  return readLedger(await deriveRunContext(runDir));
}

export async function addArtifact(options) {
  const context = await deriveRunContext(options.runDir);
  return registerArtifact({
    ...options,
    context,
    createdAt: options.createdAt ?? new Date().toISOString(),
  });
}

export async function importArtifact(options) {
  const context = await deriveRunContext(options.runDir);
  validateReusedFrom(options.reusedFrom);
  if (options.reusedFrom.runId === context.runId) {
    throw new Error('reusedFrom 必须引用其他 runId');
  }

  const sourceRunDir = path.join(
    context.projectRoot,
    '.web-flow',
    'runs',
    options.reusedFrom.runId,
  );
  const sourceLedger = await readArtifactLedger(sourceRunDir);
  const sourceRef = parseArtifactRef(options.reusedFrom.artifactRef);
  const sourceArtifact = sourceLedger.find(
    (record) =>
      record.artifactId === sourceRef.artifactId &&
      record.revision === sourceRef.revision,
  );
  if (!sourceArtifact) throw new Error('reusedFrom.artifactRef 来源不存在');
  if (sourceArtifact.sha256 !== options.reusedFrom.sha256) {
    throw new Error('reusedFrom.sha256 与来源 artifact 不一致');
  }

  const currentHash = await hashArtifact({
    projectRoot: context.projectRoot,
    artifactPath: options.artifactPath,
  });
  if (currentHash.sha256 !== options.reusedFrom.sha256) {
    throw new Error('当前 artifact sha256 与 reusedFrom 来源发生漂移');
  }

  return registerArtifact({
    ...options,
    context,
    createdAt: options.createdAt ?? new Date().toISOString(),
  });
}
