#!/usr/bin/env node

import {
  link,
  lstat,
  mkdir,
  mkdtemp,
  open,
  readFile,
  rename,
  rm,
  rmdir,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
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
      `| \`${effect.ref}\` | ${effect.category} | ${effect.title.en} | ${effect.title.zh} | ${effect.summary.en} | ${effect.summary.zh} |`,
    );
  }
  return `${lines.join('\n')}\n`;
}

async function pathExists(filePath) {
  try {
    await lstat(filePath);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

function localPath(root, relativePath) {
  return path.join(root, ...relativePath.split('/'));
}

function oldGeneratedPath(url, kind) {
  if (typeof url !== 'string') return null;
  const prefix = `./${kind}/`;
  if (!url.startsWith(prefix)) return null;
  const name = url.slice(prefix.length);
  const extensionPattern = kind === 'media' ? /\.(?:jpe?g|png)$/ : /\.md$/;
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

async function existingGeneratedPaths(outputRoot) {
  const libraryPath = localPath(outputRoot, 'gallery/api/library.json');
  let library;
  try {
    library = JSON.parse(await readFile(libraryPath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return [];
    throw new Error('Existing gallery library is not valid JSON');
  }
  if (!Array.isArray(library.effects)) {
    throw new Error('Existing gallery library has an invalid effects collection');
  }
  return library.effects.flatMap((effect) =>
    [oldGeneratedPath(effect.previewUrl, 'media'), oldGeneratedPath(effect.sourceUrl, 'source')].filter(
      Boolean,
    ),
  );
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
    const extension = path.posix.extname(effect.preview);
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

async function installArtifacts(
  outputRoot,
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
      const target = localPath(outputRoot, relativePath);
      const staged = localPath(stageRoot, relativePath);
      const backup = localPath(backupRoot, relativePath);
      await mkdir(path.dirname(target), { recursive: true });
      const temporary = path.join(
        path.dirname(target),
        `.${path.basename(target)}.image-effects-${randomUUID()}.tmp`,
      );
      await link(staged, temporary);
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
      change.hadPrevious = await pathExists(target);
      if (change.hadPrevious) {
        await mkdir(path.dirname(backup), { recursive: true });
        await link(target, backup);
      }
    }

    for (const change of changes) {
      await transactionHooks.beforeExchange?.({
        relativePath: change.relativePath,
        targetPath: change.target,
      });
      await rename(change.temporary, change.target);
      change.installed = true;
    }

    for (const relativePath of stalePaths) {
      const target = localPath(outputRoot, relativePath);
      if (!(await pathExists(target))) continue;
      const backup = localPath(path.join(stageRoot, '.stale-backup'), relativePath);
      await mkdir(path.dirname(backup), { recursive: true });
      await link(target, backup);
      await unlink(target);
      staleChanges.push({ target, backup });
    }

    const staleDirectories = [...new Set(stalePaths.map((relativePath) => path.dirname(relativePath)))]
      .sort((left, right) => right.length - left.length || compareAscii(left, right));
    for (const relativePath of staleDirectories) {
      try {
        await rmdir(localPath(outputRoot, relativePath));
      } catch (error) {
        if (error.code !== 'ENOENT' && error.code !== 'ENOTEMPTY') throw error;
      }
    }
  } catch (error) {
    let rollbackError;
    for (const change of staleChanges.reverse()) {
      try {
        await mkdir(path.dirname(change.target), { recursive: true });
        await rename(change.backup, change.target);
      } catch (cause) {
        rollbackError ??= cause;
      }
    }
    for (const change of changes.reverse()) {
      if (!change.installed) continue;
      try {
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
    const extension = path.posix.extname(effect.preview);
    artifacts.set(
      `gallery/source/${effect.ref}.md`,
      await readFile(effect.filePath),
    );
    artifacts.set(
      `gallery/media/${effect.ref}${extension}`,
      await readFile(localPath(sourceRoot, effect.preview)),
    );
  }

  await mkdir(outputRoot, { recursive: true });
  const staleCandidates = await existingGeneratedPaths(outputRoot);
  const artifactPaths = [...artifacts.keys()].sort(compareAscii);
  const artifactPathSet = new Set(artifactPaths);
  const stalePaths = [...new Set(staleCandidates)]
    .filter((relativePath) => !artifactPathSet.has(relativePath))
    .sort(compareAscii);
  const stageRoot = await mkdtemp(path.join(outputRoot, '.image-effects-build-'));

  try {
    await writeStagedArtifacts(stageRoot, artifacts);
    await validateStagedArtifacts(stageRoot, artifacts, effects, library);
    await installArtifacts(
      outputRoot,
      stageRoot,
      artifactPaths,
      stalePaths,
      transactionHooks,
    );
  } finally {
    await rm(stageRoot, { recursive: true, force: true });
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
