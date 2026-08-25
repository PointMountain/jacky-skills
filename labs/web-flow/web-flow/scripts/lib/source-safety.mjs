import { spawnSync } from 'node:child_process';
import { lstat } from 'node:fs/promises';
import path from 'node:path';

import { SAFE_RUN_ID_PATTERN } from './state-contract.mjs';
import {
  hashArtifact,
  normalizeProjectRelativePath,
} from './artifact-store.mjs';

function compareText(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function runGitStatus(projectRoot) {
  const result = spawnSync(
    'git',
    ['status', '--porcelain=v1', '-z', '--untracked-files=all'],
    { cwd: path.resolve(projectRoot), encoding: 'utf8' },
  );
  if (result.error) {
    throw new Error(`Git status 执行失败：${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(`update 模式要求 Git 仓库：${result.stderr.trim()}`);
  }
  return result.stdout;
}

function parseStatusOutput(output) {
  if (output === '') return [];
  const records = output.split('\0');
  if (records.at(-1) !== '') {
    throw new Error('Git porcelain -z 输出缺少终止 NUL');
  }
  records.pop();

  return records.map((record) => {
    if (record.length < 4 || record[2] !== ' ') {
      throw new Error('Git porcelain 记录格式无效');
    }
    const status = record.slice(0, 2);
    if (/[RC]/u.test(status)) {
      throw new Error('update baseline 暂不支持 Git rename/copy 状态');
    }
    const rawPath = record.slice(3);
    if (rawPath.includes('\\')) {
      throw new Error('Git dirty path 含无法安全持久化的反斜杠');
    }
    const relativePath = normalizeProjectRelativePath(rawPath);
    return { path: relativePath, status };
  });
}

async function snapshotStatusEntries(projectRoot) {
  const statusEntries = parseStatusOutput(runGitStatus(projectRoot));
  const snapshots = [];
  for (const entry of statusEntries) {
    let sha256;
    try {
      sha256 = (
        await hashArtifact({ projectRoot, artifactPath: entry.path })
      ).sha256;
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
      sha256 = null;
    }
    snapshots.push({ ...entry, sha256 });
  }
  snapshots.sort((left, right) => compareText(left.path, right.path));
  return snapshots;
}

function canonicalPaths(paths, label) {
  if (!Array.isArray(paths) || paths.length === 0) {
    if (label === 'confirmedDirtyPaths' && Array.isArray(paths)) return [];
    throw new Error(`${label} 必须是非空路径数组`);
  }
  const normalized = paths.map((candidate) => {
    const relativePath = normalizeProjectRelativePath(candidate);
    if (
      relativePath === '.web-flow' ||
      relativePath.startsWith('.web-flow/')
    ) {
      throw new Error(`${label} 不得包含 .web-flow`);
    }
    return relativePath;
  });
  return [...new Set(normalized)].sort(compareText);
}

function pathCovers(allowedPath, changedPath) {
  return (
    allowedPath === changedPath || changedPath.startsWith(`${allowedPath}/`)
  );
}

function pathsOverlap(left, right) {
  return pathCovers(left, right) || pathCovers(right, left);
}

function sameSnapshot(left, right) {
  return (
    left?.path === right?.path &&
    left?.status === right?.status &&
    left?.sha256 === right?.sha256
  );
}

function markdownCell(value) {
  return String(value).replaceAll('\\', '\\\\').replaceAll('|', '\\|').replaceAll('\n', '\\n');
}

async function requirePlainDirectory(directory, label) {
  const stats = await lstat(directory);
  if (stats.isSymbolicLink() || !stats.isDirectory()) {
    throw new Error(`${label} 必须是非符号链接目录`);
  }
}

export async function projectRootFromRunDir(runDir) {
  const absoluteRunDir = path.resolve(runDir);
  const runsDir = path.dirname(absoluteRunDir);
  const runtimeDir = path.dirname(runsDir);
  if (
    path.basename(runsDir) !== 'runs' ||
    path.basename(runtimeDir) !== '.web-flow' ||
    !SAFE_RUN_ID_PATTERN.test(path.basename(absoluteRunDir))
  ) {
    throw new Error('runDir 必须匹配 <projectRoot>/.web-flow/runs/<runId>');
  }
  await requirePlainDirectory(runtimeDir, '.web-flow');
  await requirePlainDirectory(runsDir, 'runs');
  await requirePlainDirectory(absoluteRunDir, 'runDir');
  return path.dirname(runtimeDir);
}

export async function captureGitBaseline(projectRoot) {
  return { dirty: await snapshotStatusEntries(projectRoot), managed: [] };
}

export async function captureManagedPath(projectRoot, managedPath) {
  const relativePath = normalizeProjectRelativePath(managedPath);
  const current = await snapshotStatusEntries(projectRoot);
  const entry = current.find((candidate) => candidate.path === relativePath);
  if (!entry) throw new Error(`runtime managed path 未出现在 Git change set：${relativePath}`);
  return entry;
}

export function renderPreexistingState(baseline) {
  const rows = baseline.dirty.map(
    (entry) =>
      `| ${markdownCell(entry.status)} | ${markdownCell(entry.path)} | ${entry.sha256 ?? 'null'} |`,
  );
  return [
    '# Preexisting State',
    '',
    '> 本文件记录 WebFlow 初始化前已经存在的 Git 改动；路径均相对项目根。',
    '',
    '| Status | Path | SHA-256 |',
    '| --- | --- | --- |',
    ...(rows.length > 0 ? rows : ['| clean | — | — |']),
    '',
  ].join('\n');
}

export function prepareSourcePlan({
  source,
  allowlist,
  confirmedDirtyPaths = [],
  actor,
}) {
  if (source?.mode !== 'update' || !source.baseline) {
    throw new Error('source plan 仅适用于含 baseline 的 update run');
  }
  if (source.plan) throw new Error('source plan 已记录，不得覆盖');
  const canonicalAllowlist = canonicalPaths(allowlist, 'allowlist');
  const sourceDir = normalizeProjectRelativePath(source.dir, {
    allowProjectRoot: true,
  });
  if (source.dir !== sourceDir) {
    throw new Error('sourceDir 必须是规范的项目相对 POSIX 路径');
  }
  if (
    sourceDir !== '.' &&
    canonicalAllowlist.some((allowed) => !pathCovers(sourceDir, allowed))
  ) {
    throw new Error('allowlist 不得越出 sourceDir 源码目录');
  }
  const canonicalConfirmed = canonicalPaths(
    confirmedDirtyPaths,
    'confirmedDirtyPaths',
  );
  const overlaps = source.baseline.dirty
    .filter((dirty) =>
      canonicalAllowlist.some((allowed) => pathsOverlap(allowed, dirty.path)),
    )
    .map((dirty) => dirty.path)
    .sort(compareText);

  if (overlaps.length > 0 && actor !== 'user') {
    throw new Error('allowlist 与 dirty path 冲突，只有 actor=user 可确认');
  }
  if (JSON.stringify(canonicalConfirmed) !== JSON.stringify(overlaps)) {
    throw new Error('confirmedDirtyPaths 必须精确列出 allowlist 冲突的 dirty path');
  }
  return {
    allowlist: canonicalAllowlist,
    confirmedDirtyPaths: canonicalConfirmed,
  };
}

export async function verifySourceState({ projectRoot, source }) {
  if (source?.mode !== 'update' || !source.baseline || !source.plan) {
    throw new Error('source verify 要求已记录 plan 的 update run');
  }
  const current = await snapshotStatusEntries(projectRoot);
  const currentByPath = new Map(current.map((entry) => [entry.path, entry]));
  const baselineByPath = new Map(
    source.baseline.dirty.map((entry) => [entry.path, entry]),
  );
  const managedByPath = new Map(
    source.baseline.managed.map((entry) => [entry.path, entry]),
  );
  const confirmed = new Set(source.plan.confirmedDirtyPaths);
  const isAllowed = (changedPath) =>
    source.plan.allowlist.some((allowed) => pathCovers(allowed, changedPath));
  const violations = [];

  for (const baselineEntry of source.baseline.dirty) {
    const currentEntry = currentByPath.get(baselineEntry.path);
    const expectedEntry = managedByPath.get(baselineEntry.path) ?? baselineEntry;
    if (!sameSnapshot(expectedEntry, currentEntry) && !confirmed.has(baselineEntry.path)) {
      violations.push(`未确认 dirty path 发生 hash/status 变化或恢复：${baselineEntry.path}`);
    }
  }
  for (const currentEntry of current) {
    if (baselineByPath.has(currentEntry.path)) continue;
    const managed = managedByPath.get(currentEntry.path);
    if (sameSnapshot(managed, currentEntry) || isAllowed(currentEntry.path)) continue;
    violations.push(`新变化越界 allowlist：${currentEntry.path}`);
  }
  for (const managed of source.baseline.managed) {
    if (!currentByPath.has(managed.path) && !isAllowed(managed.path)) {
      violations.push(`runtime managed path 被恢复或删除：${managed.path}`);
    }
  }

  if (violations.length > 0) throw new Error(violations.join('; '));
  return { valid: true, changes: current };
}
