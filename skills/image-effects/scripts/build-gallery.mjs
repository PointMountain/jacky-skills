#!/usr/bin/env node

import {
  copyFile,
  link,
  lstat,
  mkdir,
  mkdtemp,
  open,
  readFile,
  realpath,
  rename,
  rm,
  rmdir,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { constants as fsConstants } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildLibrary,
  parseEffect,
  renderThirdPartyNotices,
} from './effect-library.mjs';
import { assertMetadataFreeImage } from './image-metadata.mjs';
import { validateEffects } from './validate-effects.mjs';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_SKILL_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');
const FIXED_ARTIFACTS = [
  'assets/public-repo/THIRD_PARTY_NOTICES.md',
  'gallery/api/library.json',
  'references/INDEX.md',
];
const MANAGED_DIRECTORIES = [
  'assets',
  'assets/public-repo',
  'gallery',
  'gallery/api',
  'gallery/media',
  'gallery/source',
  'references',
];
// This lock serializes gallery artifact maintenance only; it is unrelated to image generation.
const BUILD_LOCK_NAME = '.image-effects-build.lock';
const VERSIONED_REF_PATTERN =
  /^[a-z0-9]+(?:-[a-z0-9]+)*@(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

function compareAscii(left, right) {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

function previewFormat(previewPath) {
  const extension = path.posix.extname(previewPath).toLowerCase();
  if (extension === '.jpg' || extension === '.jpeg') return 'jpeg';
  if (extension === '.png') return 'png';
  throw new Error(`Unsupported preview extension for ${previewPath}`);
}

function publicPreviewExtension(previewPath) {
  return path.posix.extname(previewPath).toLowerCase();
}

function generatedTimestamp(generatedAt) {
  let date;
  if (generatedAt !== undefined) {
    date = new Date(generatedAt);
  } else if (process.env.SOURCE_DATE_EPOCH !== undefined) {
    if (!/^(?:0|[1-9]\d*)$/.test(process.env.SOURCE_DATE_EPOCH)) {
      throw new Error('SOURCE_DATE_EPOCH must be a non-negative integer number of seconds');
    }
    date = new Date(Number(process.env.SOURCE_DATE_EPOCH) * 1000);
  } else {
    date = new Date();
  }
  if (!Number.isFinite(date.getTime())) throw new Error('Invalid generatedAt timestamp');
  return date.toISOString();
}

function renderIndex(effects) {
  const lines = [
    '# Image Effects Index',
    '',
    'Use this compact index to choose up to five candidates, then open only the selected versioned effect card.',
    '',
    '| Ref | Category | English | 中文 | Summary | 摘要 |',
    '| --- | --- | --- | --- | --- | --- |',
  ];
  for (const effect of effects) {
    lines.push(
      `| \`${effect.ref}\` | ${escapeTableCell(effect.category)} | ${escapeTableCell(effect.title.en)} | ${escapeTableCell(effect.title.zh)} | ${escapeTableCell(effect.summary.en)} | ${escapeTableCell(effect.summary.zh)} |`,
    );
  }
  return `${lines.join('\n')}\n`;
}

function escapeTableCell(value) {
  return value.replaceAll('\\', '\\\\').replaceAll('|', '\\|');
}

function isInsideRoot(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

function safePathError(relativePath, reason) {
  return new Error(`Unsafe managed output path ${relativePath}: ${reason}`);
}

async function createOutputContext(outputRoot) {
  const resolvedRoot = path.resolve(outputRoot);
  let rootStats;
  try {
    rootStats = await lstat(resolvedRoot);
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error('Output root must already exist as a real directory');
    }
    throw error;
  }
  if (rootStats.isSymbolicLink()) {
    throw new Error('Output root must not be a symbolic link');
  }
  if (!rootStats.isDirectory()) {
    throw new Error('Output root must be a directory');
  }
  return {
    outputRoot: resolvedRoot,
    canonicalRoot: await realpath(resolvedRoot),
    createdDirectories: [],
  };
}

async function assertOutputRootStable(context) {
  const stats = await lstat(context.outputRoot);
  if (stats.isSymbolicLink() || !stats.isDirectory()) {
    throw new Error('Output root must remain a real directory');
  }
  if ((await realpath(context.outputRoot)) !== context.canonicalRoot) {
    throw new Error('Output root changed during the build');
  }
}

async function inspectManagedPath(context, relativePath, expectedLeaf = 'any') {
  await assertOutputRootStable(context);
  const segments = relativePath.split('/');
  let current = context.outputRoot;
  for (let index = 0; index < segments.length; index += 1) {
    current = path.join(current, segments[index]);
    let stats;
    try {
      stats = await lstat(current);
    } catch (error) {
      if (error.code === 'ENOENT') return { exists: false, path: current };
      if (error.code === 'ENOTDIR') {
        throw safePathError(relativePath, 'a parent component is not a directory');
      }
      throw error;
    }
    if (stats.isSymbolicLink()) {
      throw safePathError(relativePath, 'symbolic links are not allowed');
    }
    const canonicalPath = await realpath(current);
    if (!isInsideRoot(context.canonicalRoot, canonicalPath)) {
      throw safePathError(relativePath, 'resolved outside the canonical output root');
    }
    const isLeaf = index === segments.length - 1;
    if (!isLeaf && !stats.isDirectory()) {
      throw safePathError(relativePath, 'a parent component is not a directory');
    }
    if (isLeaf && expectedLeaf === 'directory' && !stats.isDirectory()) {
      throw safePathError(relativePath, 'the existing path is not a directory');
    }
    if (isLeaf && expectedLeaf === 'file' && !stats.isFile()) {
      throw safePathError(relativePath, 'expected a regular file');
    }
  }
  return { exists: true, path: current };
}

async function ensureManagedDirectory(context, relativePath, { recordCreation = true } = {}) {
  let current = context.outputRoot;
  let currentRelative = '';
  for (const segment of relativePath.split('/')) {
    currentRelative = currentRelative ? `${currentRelative}/${segment}` : segment;
    current = path.join(current, segment);
    const inspection = await inspectManagedPath(context, currentRelative, 'directory');
    if (inspection.exists) continue;
    try {
      await mkdir(current);
      if (recordCreation) {
        context.createdDirectories.push({ path: current, relativePath: currentRelative });
      }
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
    await inspectManagedPath(context, currentRelative, 'directory');
  }
}

async function rollbackCreatedDirectories(context) {
  let rollbackError;
  for (const directory of [...context.createdDirectories].reverse()) {
    try {
      await inspectManagedPath(context, directory.relativePath, 'directory');
      await rmdir(directory.path);
    } catch (error) {
      if (error.code !== 'ENOENT') rollbackError ??= error;
    }
  }
  if (rollbackError) throw rollbackError;
}

async function acquireBuildLock(context) {
  await assertOutputRootStable(context);
  const lockPath = path.join(context.canonicalRoot, BUILD_LOCK_NAME);
  try {
    await mkdir(lockPath);
  } catch (error) {
    if (error.code === 'EEXIST') {
      throw new Error('Image effects build lock already exists; another build is in progress');
    }
    throw error;
  }
  try {
    await assertOutputRootStable(context);
  } catch (error) {
    await rmdir(lockPath);
    throw error;
  }
  return async () => {
    await rmdir(lockPath);
  };
}

function localPath(root, relativePath) {
  return path.join(root, ...relativePath.split('/'));
}

function oldGeneratedPath(url, kind) {
  if (typeof url !== 'string') return null;
  const prefix = `./${kind}/`;
  if (!url.startsWith(prefix)) return null;
  const name = url.slice(prefix.length);
  const extensionPattern = kind === 'media' ? /\.(?:jpe?g|png)$/i : /\.md$/;
  const extension = name.match(extensionPattern)?.[0];
  const ref = extension ? name.slice(0, -extension.length) : '';
  if (
    name.length === 0 ||
    name.includes('/') ||
    name.includes('\\') ||
    /[%?#\u0000-\u001f\u007f]/.test(name) ||
    !extension ||
    !VERSIONED_REF_PATTERN.test(ref)
  ) {
    return null;
  }
  return `gallery/${kind}/${name}`;
}

async function existingGeneratedPaths(context) {
  const relativeLibraryPath = 'gallery/api/library.json';
  const inspection = await inspectManagedPath(context, relativeLibraryPath, 'file');
  if (!inspection.exists) return [];
  const libraryPath = localPath(context.outputRoot, relativeLibraryPath);
  let library;
  try {
    library = JSON.parse(await readFile(libraryPath, 'utf8'));
  } catch (error) {
    throw new Error('Existing gallery library is not valid JSON');
  }
  if (!Array.isArray(library.effects)) {
    throw new Error('Existing gallery library has an invalid effects collection');
  }
  const paths = library.effects.flatMap((effect) =>
    [oldGeneratedPath(effect.previewUrl, 'media'), oldGeneratedPath(effect.sourceUrl, 'source')].filter(
      Boolean,
    ),
  );
  for (const relativePath of paths) {
    await inspectManagedPath(context, relativePath, 'file');
  }
  return paths;
}

async function writeStagedArtifacts(stageRoot, artifacts) {
  for (const [relativePath, bytes] of artifacts) {
    const target = localPath(stageRoot, relativePath);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, bytes);
  }
}

async function validateStagedArtifacts(stageRoot, artifacts, effects, library) {
  const expectedPaths = [...artifacts.keys()].sort(compareAscii);
  for (const relativePath of expectedPaths) {
    const expected = artifacts.get(relativePath);
    const actual = await readFile(localPath(stageRoot, relativePath));
    if (!actual.equals(Buffer.isBuffer(expected) ? expected : Buffer.from(expected))) {
      throw new Error(`Staged artifact changed while writing: ${relativePath}`);
    }
  }

  const stagedLibrary = JSON.parse(
    await readFile(localPath(stageRoot, 'gallery/api/library.json'), 'utf8'),
  );
  if (JSON.stringify(stagedLibrary) !== JSON.stringify(library)) {
    throw new Error('Staged gallery library failed validation');
  }

  for (const effect of effects) {
    const extension = publicPreviewExtension(effect.preview);
    const preview = await readFile(localPath(stageRoot, `gallery/media/${effect.ref}${extension}`));
    await assertMetadataFreeImage(preview, previewFormat(effect.preview));
    const markdown = await readFile(localPath(stageRoot, `gallery/source/${effect.ref}.md`), 'utf8');
    if (parseEffect(markdown).ref !== effect.ref) {
      throw new Error(`Staged effect card reference mismatch for ${effect.ref}`);
    }
  }
}

async function syncFile(filePath) {
  const handle = await open(filePath, 'r');
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

const LINK_FALLBACK_CODES = new Set(['EXDEV', 'ENOTSUP', 'EOPNOTSUPP', 'EPERM']);

export async function materializeFile(
  source,
  destination,
  { linkFile = link, copy = copyFile } = {},
) {
  try {
    await linkFile(source, destination);
  } catch (error) {
    if (!LINK_FALLBACK_CODES.has(error.code)) throw error;
    // Some platforms or filesystems reject hardlinks. Both paths are on the output filesystem,
    // so an exclusive copy preserves preparation semantics and the caller fsyncs before exchange.
    try {
      await copy(source, destination, fsConstants.COPYFILE_EXCL);
    } catch (copyError) {
      await rm(destination, { force: true });
      throw copyError;
    }
  }
}

async function installArtifacts(
  context,
  stageRoot,
  artifactPaths,
  stalePaths,
  transactionHooks = {},
) {
  const backupRoot = path.join(stageRoot, '.backup');
  const changes = [];
  const staleChanges = [];

  try {
    // POSIX does not provide an atomic transaction across multiple paths. Each visible file is
    // replaced with one atomic rename, while ordinary in-process failures roll back prior swaps.
    // A process crash may expose a mix of old and new files, but never a missing existing target.
    for (const relativePath of artifactPaths) {
      const target = localPath(context.outputRoot, relativePath);
      const staged = localPath(stageRoot, relativePath);
      const backup = localPath(backupRoot, relativePath);
      await ensureManagedDirectory(context, path.posix.dirname(relativePath));
      await inspectManagedPath(context, relativePath, 'file');
      const temporary = path.join(
        path.dirname(target),
        `.${path.basename(target)}.image-effects-${randomUUID()}.tmp`,
      );
      await materializeFile(staged, temporary);
      const change = {
        relativePath,
        target,
        temporary,
        backup,
        hadPrevious: false,
        installed: false,
      };
      changes.push(change);
      await syncFile(temporary);
      change.hadPrevious = (await inspectManagedPath(context, relativePath, 'file')).exists;
      if (change.hadPrevious) {
        await mkdir(path.dirname(backup), { recursive: true });
        await materializeFile(target, backup);
      }
    }

    await transactionHooks.afterPrepare?.();

    for (const [index, change] of changes.entries()) {
      await transactionHooks.beforeExchange?.({
        index,
        relativePath: change.relativePath,
        targetPath: change.target,
      });
      await inspectManagedPath(context, change.relativePath, 'file');
      await rename(change.temporary, change.target);
      change.installed = true;
    }

    for (const relativePath of stalePaths) {
      const target = localPath(context.outputRoot, relativePath);
      const inspection = await inspectManagedPath(context, relativePath, 'file');
      if (!inspection.exists) continue;
      const backup = localPath(path.join(stageRoot, '.stale-backup'), relativePath);
      await mkdir(path.dirname(backup), { recursive: true });
      await materializeFile(target, backup);
      const staleChange = { relativePath, target, backup, deleted: false };
      staleChanges.push(staleChange);
      await inspectManagedPath(context, relativePath, 'file');
      await unlink(target);
      staleChange.deleted = true;
      await transactionHooks.afterStaleDelete?.({ relativePath, targetPath: target });
    }

    const staleDirectories = [...new Set(stalePaths.map((relativePath) => path.dirname(relativePath)))]
      .sort((left, right) => right.length - left.length || compareAscii(left, right));
    for (const relativePath of staleDirectories) {
      try {
        await inspectManagedPath(context, relativePath, 'directory');
        await rmdir(localPath(context.outputRoot, relativePath));
      } catch (error) {
        if (error.code !== 'ENOENT' && error.code !== 'ENOTEMPTY') throw error;
      }
    }
  } catch (error) {
    let rollbackError;
    for (const change of staleChanges.reverse()) {
      if (!change.deleted) continue;
      try {
        await ensureManagedDirectory(context, path.posix.dirname(change.relativePath), {
          recordCreation: false,
        });
        await inspectManagedPath(context, change.relativePath, 'file');
        await rename(change.backup, change.target);
      } catch (cause) {
        rollbackError ??= cause;
      }
    }
    for (const change of changes.reverse()) {
      if (!change.installed) continue;
      try {
        await inspectManagedPath(context, change.relativePath, 'file');
        if (change.hadPrevious) {
          await rename(change.backup, change.target);
        } else {
          await unlink(change.target);
        }
      } catch (cause) {
        rollbackError ??= cause;
      }
    }
    if (rollbackError) {
      throw new AggregateError(
        [error, rollbackError],
        `Artifact installation failed and rollback was incomplete: ${error.message}`,
      );
    }
    throw error;
  } finally {
    for (const change of changes) {
      await inspectManagedPath(context, path.posix.dirname(change.relativePath), 'directory');
      await rm(change.temporary, { force: true });
    }
  }
}

export async function buildGallery({
  sourceRoot = DEFAULT_SKILL_ROOT,
  outputRoot = DEFAULT_SKILL_ROOT,
  generatedAt,
  transactionHooks,
} = {}) {
  const effects = await validateEffects({ sourceRoot });
  const timestamp = generatedTimestamp(generatedAt);
  const header = await readFile(
    localPath(sourceRoot, 'assets/public-repo/THIRD_PARTY_NOTICES.header.md'),
    'utf8',
  );
  const library = buildLibrary(effects, timestamp);
  const artifacts = new Map([
    ['references/INDEX.md', renderIndex(effects)],
    ['assets/public-repo/THIRD_PARTY_NOTICES.md', renderThirdPartyNotices(effects, header)],
    ['gallery/api/library.json', `${JSON.stringify(library, null, 2)}\n`],
  ]);

  for (const effect of effects) {
    const extension = publicPreviewExtension(effect.preview);
    artifacts.set(
      `gallery/source/${effect.ref}.md`,
      await readFile(effect.filePath),
    );
    artifacts.set(
      `gallery/media/${effect.ref}${extension}`,
      await readFile(localPath(sourceRoot, effect.preview)),
    );
  }

  const artifactPaths = [...artifacts.keys()].sort(compareAscii);
  const context = await createOutputContext(outputRoot);
  const releaseLock = await acquireBuildLock(context);
  let stageRoot;

  try {
    for (const relativePath of MANAGED_DIRECTORIES) {
      await inspectManagedPath(context, relativePath, 'directory');
    }
    for (const relativePath of artifactPaths) {
      await inspectManagedPath(context, relativePath, 'file');
    }
    await transactionHooks?.afterPreflight?.();
    const staleCandidates = await existingGeneratedPaths(context);
    const artifactPathSet = new Set(artifactPaths);
    const stalePaths = [...new Set(staleCandidates)]
      .filter((relativePath) => !artifactPathSet.has(relativePath))
      .sort(compareAscii);
    for (const relativePath of stalePaths) {
      await inspectManagedPath(context, relativePath, 'file');
    }
    stageRoot = await mkdtemp(path.join(context.outputRoot, '.image-effects-build-'));
    await writeStagedArtifacts(stageRoot, artifacts);
    await validateStagedArtifacts(stageRoot, artifacts, effects, library);
    await installArtifacts(
      context,
      stageRoot,
      artifactPaths,
      stalePaths,
      transactionHooks,
    );
  } catch (error) {
    try {
      await rollbackCreatedDirectories(context);
    } catch (rollbackError) {
      throw new AggregateError(
        [error, rollbackError],
        `Build failed and directory rollback was incomplete: ${error.message}`,
      );
    }
    throw error;
  } finally {
    try {
      if (stageRoot) await rm(stageRoot, { recursive: true, force: true });
    } finally {
      await releaseLock();
    }
  }

  const paths = [
    ...FIXED_ARTIFACTS,
    ...artifactPaths.filter((item) => !FIXED_ARTIFACTS.includes(item)),
  ].sort(compareAscii);
  return { library, paths };
}

async function main() {
  if (process.argv.length !== 2) {
    throw new Error('Usage: node scripts/build-gallery.mjs');
  }
  const { library } = await buildGallery();
  process.stdout.write(
    `Generated ${library.effects.length} effect${library.effects.length === 1 ? '' : 's'}.\n`,
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
