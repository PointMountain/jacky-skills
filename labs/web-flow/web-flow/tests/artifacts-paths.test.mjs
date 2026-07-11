import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import {
  addArtifact,
  importArtifact,
  readArtifactLedger,
} from '../scripts/lib/artifact-ledger.mjs';
import {
  FIXED_HASH_EXCLUSIONS,
  hashArtifact,
  normalizeProjectRelativePath,
  resolveSourceDirectory,
} from '../scripts/lib/artifact-store.mjs';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);

async function temporaryDirectory(prefix) {
  return mkdtemp(path.join(tmpdir(), prefix));
}

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

async function createLedgerRun(projectRoot, runId) {
  const runDir = path.join(projectRoot, '.web-flow', 'runs', runId);
  await mkdir(runDir, { recursive: true });
  await writeFile(path.join(runDir, 'artifacts.jsonl'), '');
  return runDir;
}

test('safe paths persist POSIX project-relative paths and reject escapes', () => {
  assert.equal(
    normalizeProjectRelativePath('src\\nested\\index.html'),
    'src/nested/index.html',
  );
  assert.equal(
    normalizeProjectRelativePath('./src/./index.html'),
    'src/index.html',
  );

  for (const unsafePath of [
    '/tmp/site',
    'C:\\tmp\\site',
    '../site',
    'src/../../site',
    '',
  ]) {
    assert.throws(
      () => normalizeProjectRelativePath(unsafePath),
      /相对路径|绝对路径|\.\.|非空/i,
    );
  }
});

test('safe paths reject runtime source, non-empty create targets, and implicit project root', async () => {
  const projectRoot = await temporaryDirectory('web-flow-safe-source-');

  try {
    await mkdir(path.join(projectRoot, 'empty'));
    await mkdir(path.join(projectRoot, 'occupied'));
    await writeFile(path.join(projectRoot, 'occupied', 'keep.txt'), 'keep');

    await assert.rejects(
      () =>
        resolveSourceDirectory({
          projectRoot,
          sourceDir: '.web-flow/site',
          mode: 'create',
        }),
      /\.web-flow/i,
    );
    await assert.rejects(
      () =>
        resolveSourceDirectory({
          projectRoot,
          sourceDir: 'occupied',
          mode: 'create',
        }),
      /非空|update/i,
    );
    await assert.rejects(
      () =>
        resolveSourceDirectory({
          projectRoot,
          sourceDir: '.',
          mode: 'update',
        }),
      /项目根|显式/i,
    );

    const absent = await resolveSourceDirectory({
      projectRoot,
      sourceDir: 'new-site',
      mode: 'create',
    });
    const empty = await resolveSourceDirectory({
      projectRoot,
      sourceDir: 'empty',
      mode: 'create',
    });
    const explicitRoot = await resolveSourceDirectory({
      projectRoot,
      sourceDir: '.',
      mode: 'update',
      allowProjectRoot: true,
    });

    assert.equal(absent.relativePath, 'new-site');
    assert.equal(absent.absolutePath, path.join(projectRoot, 'new-site'));
    assert.equal(empty.relativePath, 'empty');
    assert.equal(explicitRoot.relativePath, '.');
    assert.equal(explicitRoot.absolutePath, projectRoot);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('safe paths reject an existing symlink parent that escapes project root', async () => {
  const sandbox = await temporaryDirectory('web-flow-safe-realpath-');
  const projectRoot = path.join(sandbox, 'project');
  const outside = path.join(sandbox, 'outside');

  try {
    await mkdir(projectRoot);
    await mkdir(outside);
    await symlink(outside, path.join(projectRoot, 'escape'));

    await assert.rejects(
      () =>
        resolveSourceDirectory({
          projectRoot,
          sourceDir: 'escape/site',
          mode: 'update',
        }),
      /项目根|逃逸|符号链接/i,
    );
  } finally {
    await rm(sandbox, { recursive: true, force: true });
  }
});

test('safe paths require an existing source directory in update mode', async () => {
  const projectRoot = await temporaryDirectory('web-flow-safe-update-');

  try {
    await assert.rejects(
      () =>
        resolveSourceDirectory({
          projectRoot,
          sourceDir: 'missing-site',
          mode: 'update',
        }),
      /update.*存在|不存在/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact hash uses raw file bytes and a stable POSIX-sorted directory manifest', async () => {
  const projectRoot = await temporaryDirectory('web-flow-hash-stable-');
  const artifactRoot = path.join(projectRoot, 'artifact');

  try {
    await mkdir(path.join(artifactRoot, 'nested'), { recursive: true });
    await writeFile(path.join(artifactRoot, 'z.txt'), 'z');
    await writeFile(path.join(artifactRoot, 'nested', 'a.txt'), 'a');

    const fileResult = await hashArtifact({
      projectRoot,
      artifactPath: 'artifact/z.txt',
    });
    const first = await hashArtifact({ projectRoot, artifactPath: 'artifact' });
    const second = await hashArtifact({ projectRoot, artifactPath: 'artifact' });
    const expectedManifest = [
      { path: 'nested/a.txt', sha256: sha256('a') },
      { path: 'z.txt', sha256: sha256('z') },
    ];

    assert.deepEqual(fileResult, {
      kind: 'file',
      path: 'artifact/z.txt',
      sha256: sha256('z'),
    });
    assert.deepEqual(first.manifest, expectedManifest);
    assert.equal(first.path, 'artifact');
    assert.equal(first.kind, 'directory');
    assert.equal(first.sha256, sha256(JSON.stringify(expectedManifest)));
    assert.deepEqual(second, first);
    assert.ok(first.manifest.every((entry) => !entry.path.includes('\\')));
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact hash has exactly seven fixed directory exclusions and detects ordinary drift', async () => {
  const projectRoot = await temporaryDirectory('web-flow-hash-exclusions-');
  const artifactRoot = path.join(projectRoot, 'artifact');
  const excludedDirectories = [
    '.git',
    '.web-flow',
    'node_modules',
    '.next/cache',
    '.cache',
    '.turbo',
    'coverage',
  ];

  try {
    assert.deepEqual(FIXED_HASH_EXCLUSIONS, excludedDirectories);
    await mkdir(artifactRoot);
    await writeFile(path.join(artifactRoot, 'index.html'), 'v1');

    for (const excludedDirectory of excludedDirectories) {
      const directory = path.join(
        artifactRoot,
        ...excludedDirectory.split('/'),
      );
      await mkdir(directory, { recursive: true });
      await writeFile(path.join(directory, 'ignored.txt'), 'before');
    }

    const before = await hashArtifact({ projectRoot, artifactPath: 'artifact' });
    for (const excludedDirectory of excludedDirectories) {
      await writeFile(
        path.join(
          artifactRoot,
          ...excludedDirectory.split('/'),
          'ignored.txt',
        ),
        'after',
      );
    }
    const afterExcludedChanges = await hashArtifact({
      projectRoot,
      artifactPath: 'artifact',
    });
    await writeFile(path.join(artifactRoot, 'index.html'), 'v2');
    const afterOrdinaryChange = await hashArtifact({
      projectRoot,
      artifactPath: 'artifact',
    });

    assert.equal(afterExcludedChanges.sha256, before.sha256);
    assert.notEqual(afterOrdinaryChange.sha256, before.sha256);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact hash rejects every non-excluded symlink but ignores excluded paths', async () => {
  const projectRoot = await temporaryDirectory('web-flow-hash-symlink-');
  const artifactRoot = path.join(projectRoot, 'artifact');

  try {
    await mkdir(path.join(artifactRoot, 'node_modules'), { recursive: true });
    await writeFile(path.join(artifactRoot, 'target.txt'), 'target');
    await symlink(
      path.join(artifactRoot, 'target.txt'),
      path.join(artifactRoot, 'node_modules', 'ignored-link'),
    );

    await hashArtifact({ projectRoot, artifactPath: 'artifact' });

    await symlink(
      path.join(artifactRoot, 'target.txt'),
      path.join(artifactRoot, 'visible-link'),
    );
    await assert.rejects(
      () => hashArtifact({ projectRoot, artifactPath: 'artifact' }),
      /符号链接|symlink/i,
    );
    await assert.rejects(
      () =>
        hashArtifact({
          projectRoot,
          artifactPath: 'artifact/visible-link',
        }),
      /符号链接|symlink/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact hash rejects a symlink in any existing path component even when it stays inside the project', async () => {
  const projectRoot = await temporaryDirectory('web-flow-hash-parent-link-');
  const realDirectory = path.join(projectRoot, 'real');

  try {
    await mkdir(realDirectory);
    await writeFile(path.join(realDirectory, 'index.txt'), 'content');
    await symlink(realDirectory, path.join(projectRoot, 'alias'));

    await assert.rejects(
      () =>
        hashArtifact({
          projectRoot,
          artifactPath: 'alias/index.txt',
        }),
      /符号链接|symlink/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact ledger appends monotonic revisions without overwriting and deduplicates the current content', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-revisions-');
  const runDir = await createLedgerRun(
    projectRoot,
    '20260712T010000Z-a1b2',
  );
  const site = path.join(projectRoot, 'site');

  try {
    await mkdir(site);
    await writeFile(path.join(site, 'index.html'), 'v1');

    const first = await addArtifact({
      runDir,
      artifactId: 'build.preview',
      artifactPath: 'site',
      producer: 'build',
      createdAt: '2026-07-12T01:00:00.000Z',
    });
    const ledgerAfterFirst = await readFile(
      path.join(runDir, 'artifacts.jsonl'),
      'utf8',
    );
    const duplicate = await addArtifact({
      runDir,
      artifactId: 'build.preview',
      artifactPath: 'site',
      producer: 'build',
      createdAt: '2026-07-12T01:00:01.000Z',
    });

    assert.equal(first.appended, true);
    assert.equal(first.artifact.revision, 1);
    assert.equal(first.artifact.supersedes, null);
    assert.equal(first.artifact.path, 'site');
    assert.equal(duplicate.appended, false);
    assert.deepEqual(duplicate.artifact, first.artifact);
    assert.equal(
      await readFile(path.join(runDir, 'artifacts.jsonl'), 'utf8'),
      ledgerAfterFirst,
    );

    await writeFile(path.join(site, 'index.html'), 'v2');
    const second = await addArtifact({
      runDir,
      artifactId: 'build.preview',
      artifactPath: 'site',
      producer: 'build',
      createdAt: '2026-07-12T01:00:02.000Z',
    });
    const anotherId = await addArtifact({
      runDir,
      artifactId: 'build.source',
      artifactPath: 'site',
      producer: 'build',
      createdAt: '2026-07-12T01:00:03.000Z',
    });
    const ledger = await readArtifactLedger(runDir);

    assert.equal(second.appended, true);
    assert.equal(second.artifact.revision, 2);
    assert.equal(second.artifact.supersedes, 'build.preview@1');
    assert.notEqual(second.artifact.sha256, first.artifact.sha256);
    assert.equal(anotherId.artifact.revision, 1);
    assert.equal(anotherId.artifact.supersedes, null);
    assert.deepEqual(ledger, [
      first.artifact,
      second.artifact,
      anotherId.artifact,
    ]);
    assert.ok(
      (await readFile(path.join(runDir, 'artifacts.jsonl'), 'utf8')).startsWith(
        ledgerAfterFirst,
      ),
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact import validates cross-run reusedFrom provenance and current bytes', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-import-');
  const sourceRunId = '20260712T020000Z-b2c3';
  const targetRunId = '20260712T020001Z-c3d4';
  const sourceRun = await createLedgerRun(projectRoot, sourceRunId);
  const targetRun = await createLedgerRun(projectRoot, targetRunId);
  const shared = path.join(projectRoot, 'shared');

  try {
    await mkdir(shared);
    await writeFile(path.join(shared, 'prototype.html'), 'approved');
    const source = await addArtifact({
      runDir: sourceRun,
      artifactId: 'prototype.page',
      artifactPath: 'shared',
      producer: 'prototype',
      createdAt: '2026-07-12T02:00:00.000Z',
    });
    const reusedFrom = {
      runId: sourceRunId,
      artifactRef: 'prototype.page@1',
      sha256: source.artifact.sha256,
    };
    const imported = await importArtifact({
      runDir: targetRun,
      artifactId: 'prototype.reused',
      artifactPath: 'shared',
      producer: 'prototype',
      createdAt: '2026-07-12T02:00:01.000Z',
      reusedFrom,
    });

    assert.equal(imported.appended, true);
    assert.equal(imported.artifact.revision, 1);
    assert.deepEqual(imported.artifact.reusedFrom, reusedFrom);

    for (const invalidProvenance of [
      { ...reusedFrom, runId: '../escape' },
      { ...reusedFrom, artifactRef: 'prototype.page@99' },
      { ...reusedFrom, sha256: '0'.repeat(64) },
    ]) {
      await assert.rejects(
        () =>
          importArtifact({
            runDir: targetRun,
            artifactId: 'prototype.invalid',
            artifactPath: 'shared',
            producer: 'prototype',
            createdAt: '2026-07-12T02:00:02.000Z',
            reusedFrom: invalidProvenance,
          }),
        /reusedFrom|来源|artifactRef|sha256|runId/i,
      );
    }

    await writeFile(path.join(shared, 'prototype.html'), 'drifted');
    await assert.rejects(
      () =>
        importArtifact({
          runDir: targetRun,
          artifactId: 'prototype.drifted',
          artifactPath: 'shared',
          producer: 'prototype',
          createdAt: '2026-07-12T02:00:03.000Z',
          reusedFrom,
        }),
      /sha256|漂移|来源/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact import idempotency ignores reusedFrom object key insertion order', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-order-');
  const sourceRunId = '20260712T021000Z-f6a7';
  const sourceRun = await createLedgerRun(projectRoot, sourceRunId);
  const targetRun = await createLedgerRun(
    projectRoot,
    '20260712T021001Z-a7b8',
  );

  try {
    await mkdir(path.join(projectRoot, 'shared'));
    await writeFile(path.join(projectRoot, 'shared', 'index.html'), 'same');
    const source = await addArtifact({
      runDir: sourceRun,
      artifactId: 'design.page',
      artifactPath: 'shared',
      producer: 'design',
      createdAt: '2026-07-12T02:10:00.000Z',
    });
    const first = await importArtifact({
      runDir: targetRun,
      artifactId: 'design.reused',
      artifactPath: 'shared',
      producer: 'design',
      createdAt: '2026-07-12T02:10:01.000Z',
      reusedFrom: {
        runId: sourceRunId,
        artifactRef: 'design.page@1',
        sha256: source.artifact.sha256,
      },
    });
    const duplicate = await importArtifact({
      runDir: targetRun,
      artifactId: 'design.reused',
      artifactPath: 'shared',
      producer: 'design',
      createdAt: '2026-07-12T02:10:02.000Z',
      reusedFrom: {
        sha256: source.artifact.sha256,
        artifactRef: 'design.page@1',
        runId: sourceRunId,
      },
    });

    assert.equal(first.appended, true);
    assert.equal(duplicate.appended, false);
    assert.deepEqual(duplicate.artifact, first.artifact);
    assert.equal((await readArtifactLedger(targetRun)).length, 1);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact ledger rejects a non-empty JSONL file without a trailing newline before append', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-newline-');
  const runDir = await createLedgerRun(
    projectRoot,
    '20260712T022000Z-b8c9',
  );

  try {
    await mkdir(path.join(projectRoot, 'site'));
    await writeFile(path.join(projectRoot, 'site', 'index.html'), 'v1');
    await addArtifact({
      runDir,
      artifactId: 'build.preview',
      artifactPath: 'site',
      producer: 'build',
      createdAt: '2026-07-12T02:20:00.000Z',
    });
    const ledgerPath = path.join(runDir, 'artifacts.jsonl');
    const validLedger = await readFile(ledgerPath, 'utf8');
    await writeFile(ledgerPath, validLedger.trimEnd(), 'utf8');
    await writeFile(path.join(projectRoot, 'site', 'index.html'), 'v2');

    await assert.rejects(
      () =>
        addArtifact({
          runDir,
          artifactId: 'build.preview',
          artifactPath: 'site',
          producer: 'build',
          createdAt: '2026-07-12T02:20:01.000Z',
        }),
      /末尾换行|损坏|JSONL/i,
    );
    assert.equal(await readFile(ledgerPath, 'utf8'), validLedger.trimEnd());
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('artifact ledger derives projectRoot only from a validated .web-flow/runs/runId structure', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-structure-');
  const invalidRunDir = path.join(projectRoot, 'runs', 'not-a-run');

  try {
    await mkdir(invalidRunDir, { recursive: true });
    await writeFile(path.join(invalidRunDir, 'artifacts.jsonl'), '');
    await mkdir(path.join(projectRoot, 'site'));
    await writeFile(path.join(projectRoot, 'site', 'index.html'), 'content');

    await assert.rejects(
      () =>
        addArtifact({
          runDir: invalidRunDir,
          artifactId: 'build.preview',
          artifactPath: 'site',
          producer: 'build',
          createdAt: '2026-07-12T03:00:00.000Z',
        }),
      /\.web-flow\/runs|runDir|runId/i,
    );
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});

test('runtime CLI routes artifact add and import with only project-relative persisted paths', async () => {
  const projectRoot = await temporaryDirectory('web-flow-ledger-cli-');
  const sourceRunId = '20260712T040000Z-d4e5';
  const targetRunId = '20260712T040001Z-e5f6';
  const sourceRun = await createLedgerRun(projectRoot, sourceRunId);
  const targetRun = await createLedgerRun(projectRoot, targetRunId);

  try {
    await mkdir(path.join(projectRoot, 'site'));
    await writeFile(path.join(projectRoot, 'site', 'index.html'), 'cli');
    const addResult = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'artifact',
        'add',
        sourceRun,
        '--artifact-id',
        'build.preview',
        '--path',
        'site',
        '--producer',
        'build',
        '--created-at',
        '2026-07-12T04:00:00.000Z',
      ],
      { encoding: 'utf8' },
    );

    assert.equal(addResult.status, 0, addResult.stderr);
    const added = JSON.parse(addResult.stdout);
    assert.equal(added.artifact.path, 'site');

    const importResult = spawnSync(
      process.execPath,
      [
        runtimeCli.pathname,
        'artifact',
        'import',
        targetRun,
        '--artifact-id',
        'build.reused',
        '--path',
        'site',
        '--producer',
        'build',
        '--created-at',
        '2026-07-12T04:00:01.000Z',
        '--reused-from-run',
        sourceRunId,
        '--reused-from-artifact',
        'build.preview@1',
        '--reused-from-sha256',
        added.artifact.sha256,
      ],
      { encoding: 'utf8' },
    );

    assert.equal(importResult.status, 0, importResult.stderr);
    const imported = JSON.parse(importResult.stdout);
    assert.equal(imported.artifact.path, 'site');
    assert.deepEqual(imported.artifact.reusedFrom, {
      runId: sourceRunId,
      artifactRef: 'build.preview@1',
      sha256: added.artifact.sha256,
    });
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});
