import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  cp,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildGallery } from '../scripts/build-gallery.mjs';
import {
  fetchGitHubContent,
  validateEffects,
  validateOnlineSources,
} from '../scripts/validate-effects.mjs';

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EFFECT_REF = 'healing-anime-scribble-v3@1.0.0';
const REVISION = 'aaf9a82f5efd73e87cc0998edc398e75bfc35901';
const SOURCE_PATH =
  'skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md';
const SOURCE_BYTES = Buffer.from('fixed upstream bytes\n');
const SOURCE_SHA = createHash('sha256').update(SOURCE_BYTES).digest('hex');
const MANAGED_PATHS = [
  'assets/public-repo/THIRD_PARTY_NOTICES.md',
  'gallery/api/library.json',
  `gallery/media/${EFFECT_REF}.jpg`,
  `gallery/source/${EFFECT_REF}.md`,
  'references/INDEX.md',
];

async function makeFixtureSource(root, sourceSha = SOURCE_SHA) {
  await Promise.all([
    mkdir(path.join(root, 'references/effects'), { recursive: true }),
    mkdir(path.join(root, 'assets/previews'), { recursive: true }),
    mkdir(path.join(root, 'assets/public-repo'), { recursive: true }),
  ]);

  const card = (
    await readFile(
      path.join(SKILL_ROOT, 'references/effects/healing-anime-scribble-v3.md'),
      'utf8',
    )
  ).replace(
    /^source_sha256s: .*$/m,
    `source_sha256s: ${sourceSha}`,
  );
  await Promise.all([
    writeFile(path.join(root, 'references/effects/healing-anime-scribble-v3.md'), card),
    cp(
      path.join(SKILL_ROOT, 'assets/previews/healing-anime-scribble-v3.jpg'),
      path.join(root, 'assets/previews/healing-anime-scribble-v3.jpg'),
    ),
    writeFile(
      path.join(root, 'assets/public-repo/THIRD_PARTY_NOTICES.header.md'),
      '# Fixture notice header\n\nFixture license text.\n',
    ),
  ]);
}

async function fileTree(root) {
  const entries = [];
  async function visit(directory, prefix = '') {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const relative = path.posix.join(prefix, entry.name);
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) await visit(absolute, relative);
      else if (entry.isFile()) {
        const bytes = await readFile(absolute);
        entries.push([relative, createHash('sha256').update(bytes).digest('hex')]);
      }
    }
  }
  await visit(root);
  return entries.sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0));
}

test('固定 epoch 在两个独立输出目录生成逐字节相同的完整受管树', async () => {
  const fixtureRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const outputOne = await mkdtemp(path.join(tmpdir(), 'image-effects-output-one-'));
  const outputTwo = await mkdtemp(path.join(tmpdir(), 'image-effects-output-two-'));
  const previousEpoch = process.env.SOURCE_DATE_EPOCH;
  process.env.SOURCE_DATE_EPOCH = '1786809600';

  try {
    await makeFixtureSource(fixtureRoot);
    await buildGallery({ sourceRoot: fixtureRoot, outputRoot: outputOne });
    await buildGallery({ sourceRoot: fixtureRoot, outputRoot: outputTwo });

    const firstTree = await fileTree(outputOne);
    const secondTree = await fileTree(outputTwo);
    assert.deepEqual(firstTree, secondTree);
    assert.deepEqual(firstTree.map(([name]) => name), MANAGED_PATHS);

    const library = JSON.parse(
      await readFile(path.join(outputOne, 'gallery/api/library.json'), 'utf8'),
    );
    assert.equal(library.generatedAt, '2026-08-15T16:00:00.000Z');
    assert.deepEqual(library.effects[0].provenance, {
      repository: 'ConardLi/garden-skills',
      revision: REVISION,
      license: {
        spdx: 'MIT',
        url: `https://github.com/ConardLi/garden-skills/blob/${REVISION}/LICENSE`,
      },
      preview: {
        origin:
          'Text-only image generation of a fictional young adult with glasses, not based on a real person.',
        author: 'wangjs-jacky',
        licenseSpdx: 'CC-BY-4.0',
      },
    });
    assert.equal(library.effects[0].previewUrl, `./media/${EFFECT_REF}.jpg`);
    assert.equal(library.effects[0].sourceUrl, `./source/${EFFECT_REF}.md`);

    const copiedCard = await readFile(
      path.join(outputOne, `gallery/source/${EFFECT_REF}.md`),
      'utf8',
    );
    const originalCard = await readFile(
      path.join(fixtureRoot, 'references/effects/healing-anime-scribble-v3.md'),
      'utf8',
    );
    assert.equal(copiedCard, originalCard);
    assert.match(
      await readFile(path.join(outputOne, 'references/INDEX.md'), 'utf8'),
      /healing-anime-scribble-v3@1\.0\.0/,
    );
  } finally {
    if (previousEpoch === undefined) delete process.env.SOURCE_DATE_EPOCH;
    else process.env.SOURCE_DATE_EPOCH = previousEpoch;
    await Promise.all([
      rm(fixtureRoot, { recursive: true, force: true }),
      rm(outputOne, { recursive: true, force: true }),
      rm(outputTwo, { recursive: true, force: true }),
    ]);
  }
});

test('重建删除旧清单拥有的陈旧产物并保留非受管文件', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const outputRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-output-'));
  const staleRef = 'retired-effect@9.9.9';

  try {
    await makeFixtureSource(sourceRoot);
    await Promise.all([
      mkdir(path.join(outputRoot, 'gallery/api'), { recursive: true }),
      mkdir(path.join(outputRoot, 'gallery/media'), { recursive: true }),
      mkdir(path.join(outputRoot, 'gallery/source'), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(
        path.join(outputRoot, 'gallery/api/library.json'),
        JSON.stringify({
          schemaVersion: 1,
          effects: [
            {
              previewUrl: `./media/${staleRef}.jpg`,
              sourceUrl: `./source/${staleRef}.md`,
            },
          ],
        }),
      ),
      writeFile(path.join(outputRoot, `gallery/media/${staleRef}.jpg`), 'stale'),
      writeFile(path.join(outputRoot, `gallery/source/${staleRef}.md`), 'stale'),
      writeFile(path.join(outputRoot, 'gallery/media/manual-note.txt'), 'keep'),
      writeFile(path.join(outputRoot, 'gallery/api/custom.json'), 'keep'),
    ]);

    await buildGallery({
      sourceRoot,
      outputRoot,
      generatedAt: '2026-08-16T00:00:00.000Z',
    });

    await assert.rejects(
      () => stat(path.join(outputRoot, `gallery/media/${staleRef}.jpg`)),
      /ENOENT/,
    );
    await assert.rejects(
      () => stat(path.join(outputRoot, `gallery/source/${staleRef}.md`)),
      /ENOENT/,
    );
    assert.equal(await readFile(path.join(outputRoot, 'gallery/media/manual-note.txt'), 'utf8'), 'keep');
    assert.equal(await readFile(path.join(outputRoot, 'gallery/api/custom.json'), 'utf8'), 'keep');
  } finally {
    await Promise.all([
      rm(sourceRoot, { recursive: true, force: true }),
      rm(outputRoot, { recursive: true, force: true }),
    ]);
  }
});

test('每个可见产物交换前旧目标始终可读，成功后不残留事务文件', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const outputRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-output-'));

  try {
    await makeFixtureSource(sourceRoot);
    await buildGallery({
      sourceRoot,
      outputRoot,
      generatedAt: '2026-08-15T00:00:00.000Z',
    });
    const oldTree = new Map(await fileTree(outputRoot));
    const exchanges = [];

    await buildGallery({
      sourceRoot,
      outputRoot,
      generatedAt: '2026-08-16T00:00:00.000Z',
      transactionHooks: {
        beforeExchange: async ({ relativePath, targetPath }) => {
          const bytes = await readFile(targetPath);
          assert.equal(createHash('sha256').update(bytes).digest('hex'), oldTree.get(relativePath));
          exchanges.push(relativePath);
        },
      },
    });

    assert.deepEqual(exchanges, MANAGED_PATHS);
    const finalPaths = (await fileTree(outputRoot)).map(([relativePath]) => relativePath);
    assert.deepEqual(finalPaths, MANAGED_PATHS);
    assert.equal(
      finalPaths.some((relativePath) =>
        /(?:^|\/)(?:\.image-effects-build-|\.image-effects-.*\.(?:tmp|backup)$)/.test(
          relativePath,
        ),
      ),
      false,
    );
  } finally {
    await Promise.all([
      rm(sourceRoot, { recursive: true, force: true }),
      rm(outputRoot, { recursive: true, force: true }),
    ]);
  }
});

test('中途交换失败后旧输出树的路径与逐文件 SHA 完全不变', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const outputRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-output-'));

  try {
    await makeFixtureSource(sourceRoot);
    await buildGallery({
      sourceRoot,
      outputRoot,
      generatedAt: '2026-08-15T00:00:00.000Z',
    });
    const oldTree = await fileTree(outputRoot);
    let exchanges = 0;

    await assert.rejects(
      () =>
        buildGallery({
          sourceRoot,
          outputRoot,
          generatedAt: '2026-08-16T00:00:00.000Z',
          transactionHooks: {
            beforeExchange: async ({ targetPath }) => {
              await readFile(targetPath);
              exchanges += 1;
              if (exchanges === 3) throw new Error('injected exchange failure');
            },
          },
        }),
      /injected exchange failure/,
    );

    assert.equal(exchanges, 3);
    assert.deepEqual(await fileTree(outputRoot), oldTree);
  } finally {
    await Promise.all([
      rm(sourceRoot, { recursive: true, force: true }),
      rm(outputRoot, { recursive: true, force: true }),
    ]);
  }
});

test('写入阶段失败会回滚，不替换已有产物', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const outputRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-output-'));

  try {
    await makeFixtureSource(sourceRoot);
    await Promise.all([
      mkdir(path.join(outputRoot, 'references'), { recursive: true }),
      mkdir(path.join(outputRoot, 'assets/public-repo'), { recursive: true }),
    ]);
    await Promise.all([
      writeFile(path.join(outputRoot, 'references/INDEX.md'), 'existing index\n'),
      writeFile(
        path.join(outputRoot, 'assets/public-repo/THIRD_PARTY_NOTICES.md'),
        'existing notice\n',
      ),
      writeFile(path.join(outputRoot, 'gallery'), 'blocks gallery directory'),
    ]);

    await assert.rejects(
      () =>
        buildGallery({
          sourceRoot,
          outputRoot,
          generatedAt: '2026-08-16T00:00:00.000Z',
        }),
      /ENOTDIR|not a directory/i,
    );
    assert.equal(
      await readFile(path.join(outputRoot, 'references/INDEX.md'), 'utf8'),
      'existing index\n',
    );
    assert.equal(
      await readFile(
        path.join(outputRoot, 'assets/public-repo/THIRD_PARTY_NOTICES.md'),
        'utf8',
      ),
      'existing notice\n',
    );
    assert.equal(await readFile(path.join(outputRoot, 'gallery'), 'utf8'), 'blocks gallery directory');
  } finally {
    await Promise.all([
      rm(sourceRoot, { recursive: true, force: true }),
      rm(outputRoot, { recursive: true, force: true }),
    ]);
  }
});

test('离线验证加载卡片并校验预览，完全不调用在线 fetcher', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  let calls = 0;
  try {
    await makeFixtureSource(sourceRoot);
    const effects = await validateEffects({
      sourceRoot,
      fetcher: async () => {
        calls += 1;
        throw new Error('must not run');
      },
    });
    assert.deepEqual(effects.map(({ ref }) => ref), [EFFECT_REF]);
    assert.equal(calls, 0);
  } finally {
    await rm(sourceRoot, { recursive: true, force: true });
  }
});

test('在线验证按固定仓库、revision、path 请求并校验 base64 内容 SHA', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-'));
  const requests = [];
  try {
    await makeFixtureSource(sourceRoot);
    const effects = await validateEffects({ sourceRoot });
    await validateOnlineSources(effects, {
      fetcher: async (request) => {
        requests.push(request);
        return { encoding: 'base64', content: SOURCE_BYTES.toString('base64') };
      },
    });
    assert.deepEqual(requests, [
      {
        repository: 'ConardLi/garden-skills',
        revision: REVISION,
        path: SOURCE_PATH,
      },
    ]);
  } finally {
    await rm(sourceRoot, { recursive: true, force: true });
  }
});

test('在线验证拒绝内容哈希不匹配，并且错误只标识固定远端来源', async () => {
  const sourceRoot = await mkdtemp(path.join(tmpdir(), 'image-effects-source-private-'));
  try {
    await makeFixtureSource(sourceRoot);
    const effects = await validateEffects({ sourceRoot });
    await assert.rejects(
      () =>
        validateOnlineSources(effects, {
          fetcher: async () => ({
            encoding: 'base64',
            content: Buffer.from('changed').toString('base64'),
          }),
        }),
      (error) => {
        assert.match(error.message, /SHA-256 mismatch/i);
        assert.match(error.message, /ConardLi\/garden-skills/);
        assert.match(error.message, new RegExp(REVISION));
        assert.match(error.message, /style-transfer-selfie\.md/);
        assert.doesNotMatch(error.message, new RegExp(sourceRoot));
        return true;
      },
    );
  } finally {
    await rm(sourceRoot, { recursive: true, force: true });
  }
});

test('GitHub fetcher 逐段编码路径并通过无 shell 的 gh api 获取 JSON', async () => {
  const invocations = [];
  const payload = { encoding: 'base64', content: SOURCE_BYTES.toString('base64') };
  const result = await fetchGitHubContent(
    {
      repository: 'owner/repo',
      revision: 'abc/def',
      path: 'folder name/file+.md',
    },
    {
      run: async (...args) => {
        invocations.push(args);
        return { stdout: JSON.stringify(payload) };
      },
    },
  );

  assert.deepEqual(result, payload);
  assert.deepEqual(invocations, [
    [
      'gh',
      [
        'api',
        'repos/owner/repo/contents/folder%20name/file%2B.md?ref=abc%2Fdef',
      ],
      { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 },
    ],
  ]);
});
