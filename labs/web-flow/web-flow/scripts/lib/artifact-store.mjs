import { createHash } from 'node:crypto';
import {
  lstat,
  readFile,
  readdir,
  realpath,
} from 'node:fs/promises';
import path from 'node:path';

export const FIXED_HASH_EXCLUSIONS = Object.freeze([
  '.git',
  '.web-flow',
  'node_modules',
  '.next/cache',
  '.cache',
  '.turbo',
  'coverage',
]);

function isMissing(error) {
  return error?.code === 'ENOENT';
}

function compareText(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return (
    relative === '' ||
    (relative !== '..' &&
      !relative.startsWith(`..${path.sep}`) &&
      !path.isAbsolute(relative))
  );
}

function assertInsideProject(root, candidate, label) {
  if (!isWithin(root, candidate)) {
    throw new Error(`${label} 解析符号链接后逃逸项目根`);
  }
}

async function findResolvedCandidate(absolutePath) {
  const missingSegments = [];
  let current = absolutePath;

  while (true) {
    try {
      const resolved = await realpath(current);
      return path.resolve(resolved, ...missingSegments);
    } catch (error) {
      if (!isMissing(error)) throw error;
      const parent = path.dirname(current);
      if (parent === current) throw error;
      missingSegments.unshift(path.basename(current));
      current = parent;
    }
  }
}

async function optionalStat(filePath) {
  try {
    return await lstat(filePath);
  } catch (error) {
    if (isMissing(error)) return null;
    throw error;
  }
}

async function assertNoSymlinkComponents(projectRoot, relativePath) {
  let current = projectRoot;
  for (const segment of relativePath.split('/')) {
    if (segment === '.') continue;
    current = path.join(current, segment);
    const componentStat = await optionalStat(current);
    if (!componentStat) return;
    if (componentStat.isSymbolicLink()) {
      throw new Error(`artifact 路径包含符号链接：${relativePath}`);
    }
  }
}

function digest(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

function containsPathPattern(candidate, pattern) {
  const candidateSegments = candidate.split('/');
  const patternSegments = pattern.split('/');

  for (
    let start = 0;
    start <= candidateSegments.length - patternSegments.length;
    start += 1
  ) {
    if (
      patternSegments.every(
        (segment, offset) => candidateSegments[start + offset] === segment,
      )
    ) {
      return true;
    }
  }
  return false;
}

function isExcludedDirectory(relativePath) {
  return FIXED_HASH_EXCLUSIONS.some((pattern) =>
    containsPathPattern(relativePath, pattern),
  );
}

function toPosixChildPath(parent, name) {
  if (name.includes('\\')) {
    throw new Error(`artifact 文件名不能包含反斜杠：${name}`);
  }
  return parent.length === 0 ? name : `${parent}/${name}`;
}

async function collectManifest(directory, relativeParent = '') {
  const manifest = [];
  const directoryBefore = await lstat(directory);
  if (directoryBefore.isSymbolicLink()) {
    throw new Error(`artifact 包含符号链接：${relativeParent || '.'}`);
  }
  if (!directoryBefore.isDirectory()) {
    throw new Error(`artifact 遍历目标不再是目录：${relativeParent || '.'}`);
  }
  const entries = await readdir(directory);
  entries.sort(compareText);

  for (const entry of entries) {
    const relativePath = toPosixChildPath(relativeParent, entry);
    const absolutePath = path.join(directory, entry);
    const entryBefore = await lstat(absolutePath);

    if (
      isExcludedDirectory(relativePath) &&
      (entryBefore.isDirectory() || entryBefore.isSymbolicLink())
    ) {
      continue;
    }
    if (entryBefore.isSymbolicLink()) {
      throw new Error(`artifact 包含非排除的符号链接：${relativePath}`);
    }
    if (entryBefore.isDirectory()) {
      manifest.push(...(await collectManifest(absolutePath, relativePath)));
    } else if (entryBefore.isFile()) {
      const contents = await readFile(absolutePath);
      const entryAfter = await lstat(absolutePath);
      if (entryAfter.isSymbolicLink()) {
        throw new Error(`artifact 包含非排除的符号链接：${relativePath}`);
      }
      if (!entryAfter.isFile()) {
        throw new Error(`artifact 文件类型在读取期间改变：${relativePath}`);
      }
      manifest.push({ path: relativePath, sha256: digest(contents) });
    } else {
      throw new Error(`artifact 包含不支持的文件类型：${relativePath}`);
    }
  }

  const directoryAfter = await lstat(directory);
  if (directoryAfter.isSymbolicLink() || !directoryAfter.isDirectory()) {
    throw new Error(`artifact 目录类型在遍历期间改变：${relativeParent || '.'}`);
  }
  return manifest;
}

export function normalizeProjectRelativePath(
  candidate,
  { allowProjectRoot = false } = {},
) {
  if (typeof candidate !== 'string' || candidate.length === 0) {
    throw new TypeError('项目相对路径必须是非空字符串');
  }
  if (candidate.includes('\0')) {
    throw new Error('项目相对路径不能包含 NUL');
  }
  if (path.posix.isAbsolute(candidate) || path.win32.isAbsolute(candidate)) {
    throw new Error('项目路径不能是绝对路径');
  }

  const posixCandidate = candidate.replaceAll('\\', '/');
  const segments = posixCandidate.split('/');
  if (segments.includes('..')) {
    throw new Error('项目相对路径不能包含 .. 跳转');
  }

  const normalized = path.posix.normalize(posixCandidate);
  if (normalized === '.') {
    if (!allowProjectRoot) {
      throw new Error('项目根必须显式允许');
    }
    return normalized;
  }
  if (normalized.startsWith('../') || normalized === '..') {
    throw new Error('项目相对路径不能包含 .. 跳转');
  }
  return normalized.startsWith('./') ? normalized.slice(2) : normalized;
}

export async function resolveSourceDirectory({
  projectRoot,
  sourceDir,
  mode,
  allowProjectRoot = false,
}) {
  if (mode !== 'create' && mode !== 'update') {
    throw new Error('source mode 必须是 create 或 update');
  }

  const relativePath = normalizeProjectRelativePath(sourceDir, {
    allowProjectRoot,
  });
  if (
    relativePath === '.web-flow' ||
    relativePath.startsWith('.web-flow/')
  ) {
    throw new Error('sourceDir 不得位于 .web-flow 内');
  }

  const absoluteProjectRoot = path.resolve(projectRoot);
  const resolvedProjectRoot = await realpath(absoluteProjectRoot);
  const absolutePath = path.resolve(
    absoluteProjectRoot,
    ...relativePath.split('/'),
  );
  const resolvedCandidate = await findResolvedCandidate(absolutePath);
  assertInsideProject(resolvedProjectRoot, resolvedCandidate, 'sourceDir');

  const targetStat = await optionalStat(absolutePath);
  if (mode === 'update' && !targetStat) {
    throw new Error('update 模式要求 sourceDir 已存在');
  }
  if (targetStat && !targetStat.isDirectory() && !targetStat.isSymbolicLink()) {
    throw new Error('sourceDir 已存在且不是目录');
  }
  if (mode === 'create' && targetStat) {
    const entries = await readdir(absolutePath);
    if (entries.length > 0) {
      throw new Error('create 模式拒绝非空 sourceDir；请改用 update');
    }
  }

  return { relativePath, absolutePath };
}

export async function hashArtifact({ projectRoot, artifactPath }) {
  const relativePath = normalizeProjectRelativePath(artifactPath, {
    allowProjectRoot: true,
  });
  const absoluteProjectRoot = path.resolve(projectRoot);
  const resolvedProjectRoot = await realpath(absoluteProjectRoot);
  const absolutePath = path.resolve(
    absoluteProjectRoot,
    ...relativePath.split('/'),
  );
  await assertNoSymlinkComponents(absoluteProjectRoot, relativePath);
  const artifactStat = await lstat(absolutePath);

  if (artifactStat.isSymbolicLink()) {
    throw new Error(`artifact 是符号链接：${relativePath}`);
  }
  const resolvedArtifact = await realpath(absolutePath);
  assertInsideProject(resolvedProjectRoot, resolvedArtifact, 'artifact');

  if (artifactStat.isFile()) {
    const result = {
      kind: 'file',
      path: relativePath,
      sha256: digest(await readFile(absolutePath)),
    };
    await assertNoSymlinkComponents(absoluteProjectRoot, relativePath);
    return result;
  }
  if (!artifactStat.isDirectory()) {
    throw new Error(`artifact 不是普通文件或目录：${relativePath}`);
  }

  const manifest = await collectManifest(absolutePath);
  await assertNoSymlinkComponents(absoluteProjectRoot, relativePath);
  manifest.sort((left, right) => compareText(left.path, right.path));
  return {
    kind: 'directory',
    path: relativePath,
    sha256: digest(JSON.stringify(manifest)),
    manifest,
  };
}
