import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  buildLibrary,
  loadEffects,
  parseEffect,
  renderThirdPartyNotices,
} from '../scripts/effect-library.mjs';

const SOURCE_SHA = '67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461';
const PREVIEW_SHA = '0'.repeat(64);
const REVISION = 'aaf9a82f5efd73e87cc0998edc398e75bfc35901';

const REQUIRED_FIELDS = {
  id: 'healing-anime-scribble-v3',
  version: '1.0.0',
  title_en: 'Healing anime scribble',
  title_zh: '治愈系动漫涂鸦',
  summary_en: 'Turn a portrait into a gentle hand-drawn scene.',
  summary_zh: '将人像转换为温柔的手绘场景。',
  category: 'portrait',
  execution_kind: 'host-image-generation',
  input_mode: 'image',
  input_min: '1',
  input_max: '1',
  input_formats: 'jpeg,png',
  output_count: '1',
  preview: 'assets/previews/healing-anime-scribble-v3.jpg',
  source_repository: 'ConardLi/garden-skills',
  source_revision: REVISION,
  source_paths: 'skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md',
  source_sha256s: SOURCE_SHA,
  source_license_spdx: 'MIT',
  source_license_url: `https://github.com/ConardLi/garden-skills/blob/${REVISION}/LICENSE`,
  adaptation_notice: 'Adapted into a versioned image-effect card.',
  preview_origin: 'Generated fictional portrait.',
  preview_author: 'Example author',
  preview_license_spdx: 'CC-BY-4.0',
  preview_sha256: PREVIEW_SHA,
};

function card(overrides = {}, omitted = []) {
  const fields = { ...REQUIRED_FIELDS, ...overrides };
  const lines = Object.entries(fields)
    .filter(([key]) => !omitted.includes(key))
    .map(([key, value]) => `${key}: ${value}`);

  return `---\n${lines.join('\n')}\n---\n\n## 适用场景\n\nFixture body.\n`;
}

test('parseEffect parses valid simple scalar frontmatter and normalizes sources', () => {
  const effect = parseEffect(card(), 'references/effects/healing-anime-scribble-v3.md');

  assert.equal(effect.ref, 'healing-anime-scribble-v3@1.0.0');
  assert.deepEqual(effect.sources, [
    {
      path: 'skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md',
      sha256: SOURCE_SHA,
    },
  ]);
  assert.equal(effect.input.min, 1);
  assert.deepEqual(effect.input.formats, ['jpeg', 'png']);
  assert.equal(effect.outputCount, 1);
  assert.equal(effect.body, '## 适用场景\n\nFixture body.');
});

test('parseEffect rejects duplicate keys', () => {
  const markdown = card().replace('version: 1.0.0', 'version: 1.0.0\nversion: 1.0.1');
  assert.throws(() => parseEffect(markdown), /duplicate/i);
});

test('parseEffect rejects unknown, missing, and empty fields', async (t) => {
  await t.test('unknown field', () => {
    const markdown = card().replace('version: 1.0.0', 'version: 1.0.0\nunsupported: value');
    assert.throws(() => parseEffect(markdown), /unknown/i);
  });

  await t.test('missing field', () => {
    assert.throws(() => parseEffect(card({}, ['summary_zh'])), /missing.*summary_zh/i);
  });

  await t.test('empty key', () => {
    const markdown = card().replace('version: 1.0.0', 'version: 1.0.0\n: value');
    assert.throws(() => parseEffect(markdown), /empty key/i);
  });

  await t.test('empty value', () => {
    assert.throws(() => parseEffect(card({ title_en: '' })), /empty.*title_en/i);
  });

  await t.test('multiline YAML', () => {
    const markdown = card().replace(
      'summary_en: Turn a portrait into a gentle hand-drawn scene.',
      'summary_en: |\n  Turn a portrait into a gentle hand-drawn scene.',
    );
    assert.throws(() => parseEffect(markdown), /simple single-line scalar/i);
  });
});

test('parseEffect rejects absolute paths and traversal segments', async (t) => {
  await t.test('absolute preview path', () => {
    assert.throws(() => parseEffect(card({ preview: '/tmp/preview.jpg' })), /relative path/i);
  });

  await t.test('preview traversal', () => {
    assert.throws(() => parseEffect(card({ preview: 'assets/../private.jpg' })), /\.\./i);
  });

  await t.test('source traversal', () => {
    assert.throws(() => parseEffect(card({ source_paths: '../source.md' })), /\.\./i);
  });
});

test('parseEffect rejects invalid identifiers, versions, and hashes', async (t) => {
  await t.test('id', () => {
    assert.throws(() => parseEffect(card({ id: 'Healing_Effect' })), /invalid id/i);
  });

  await t.test('SemVer', () => {
    assert.throws(() => parseEffect(card({ version: 'v1.0' })), /SemVer/i);
  });

  await t.test('source revision', () => {
    assert.throws(() => parseEffect(card({ source_revision: 'abc123' })), /source_revision/i);
  });

  await t.test('source SHA-256', () => {
    assert.throws(() => parseEffect(card({ source_sha256s: 'not-a-sha' })), /source_sha256s/i);
  });

  await t.test('preview SHA-256', () => {
    assert.throws(() => parseEffect(card({ preview_sha256: 'not-a-sha' })), /preview_sha256/i);
  });
});

test('parseEffect rejects invalid source mappings', async (t) => {
  await t.test('mismatched paths and hashes', () => {
    assert.throws(
      () => parseEffect(card({ source_paths: 'one.md,two.md' })),
      /same length/i,
    );
  });

  await t.test('duplicate source path', () => {
    assert.throws(
      () =>
        parseEffect(
          card({
            source_paths: 'same.md,same.md',
            source_sha256s: `${SOURCE_SHA},${'1'.repeat(64)}`,
          }),
        ),
      /duplicate source path/i,
    );
  });

  await t.test('empty CSV item', () => {
    assert.throws(
      () => parseEffect(card({ source_paths: 'one.md,,two.md' })),
      /empty.*source_paths/i,
    );
  });
});

test('parseEffect enforces the MVP input, output, and license contract', async (t) => {
  const invalidCases = [
    ['category', 'landscape', /category/i],
    ['execution_kind', 'local-script', /execution_kind/i],
    ['input_mode', 'text', /input_mode/i],
    ['input_min', '0', /input_min/i],
    ['input_max', '2', /input_max/i],
    ['input_formats', 'png,jpeg', /input_formats/i],
    ['output_count', '2', /output_count/i],
    ['source_license_spdx', 'Apache-2.0', /source_license_spdx/i],
    ['preview_license_spdx', 'MIT', /preview_license_spdx/i],
  ];

  for (const [field, value, pattern] of invalidCases) {
    await t.test(field, () => {
      assert.throws(() => parseEffect(card({ [field]: value })), pattern);
    });
  }
});

test('loadEffects reads Markdown cards and returns stable ID and SemVer order', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'image-effects-'));

  try {
    await Promise.all([
      writeFile(path.join(root, 'z.md'), card({ id: 'z-effect', version: '1.0.0' })),
      writeFile(path.join(root, 'a-new.md'), card({ id: 'a-effect', version: '1.10.0' })),
      writeFile(path.join(root, 'a-old.md'), card({ id: 'a-effect', version: '1.2.0' })),
      writeFile(path.join(root, 'ignored.txt'), 'not an effect card'),
    ]);

    const effects = await loadEffects(root);
    assert.deepEqual(
      effects.map((effect) => effect.ref),
      ['a-effect@1.2.0', 'a-effect@1.10.0', 'z-effect@1.0.0'],
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('buildLibrary projects the public schema with versioned invocations', () => {
  const effect = parseEffect(card(), 'references/effects/healing-anime-scribble-v3.md');
  const generatedAt = '2026-08-16T00:00:00.000Z';

  assert.deepEqual(buildLibrary([effect], generatedAt), {
    schemaVersion: 1,
    generatedAt,
    effects: [
      {
        ref: 'healing-anime-scribble-v3@1.0.0',
        id: 'healing-anime-scribble-v3',
        version: '1.0.0',
        title: { en: 'Healing anime scribble', zh: '治愈系动漫涂鸦' },
        summary: {
          en: 'Turn a portrait into a gentle hand-drawn scene.',
          zh: '将人像转换为温柔的手绘场景。',
        },
        category: 'portrait',
        input: { mode: 'image', min: 1, max: 1, formats: ['jpeg', 'png'] },
        outputCount: 1,
        previewUrl: './media/healing-anime-scribble-v3.jpg',
        sourceUrl: './source/healing-anime-scribble-v3.md',
        provenance: {
          repository: 'ConardLi/garden-skills',
          revision: REVISION,
          license: {
            spdx: 'MIT',
            url: `https://github.com/ConardLi/garden-skills/blob/${REVISION}/LICENSE`,
          },
          preview: {
            origin: 'Generated fictional portrait.',
            author: 'Example author',
            licenseSpdx: 'CC-BY-4.0',
          },
        },
        invocation:
          'Use $image-effects effect healing-anime-scribble-v3@1.0.0 on my uploaded image.',
      },
    ],
  });
});

test('renderThirdPartyNotices deterministically appends source facts to the supplied header', () => {
  const first = parseEffect(card(), 'references/effects/healing-anime-scribble-v3.md');
  const second = parseEffect(
    card({
      id: 'another-effect',
      title_en: 'Another effect',
      source_paths: 'upstream/one.md,upstream/two.md',
      source_sha256s: `${'1'.repeat(64)},${'2'.repeat(64)}`,
    }),
    'references/effects/another-effect.md',
  );

  const notice = renderThirdPartyNotices([first, second], '# Third-party notices\n');

  assert.ok(notice.startsWith('# Third-party notices\n'));
  assert.ok(notice.indexOf('another-effect@1.0.0') < notice.indexOf('healing-anime-scribble-v3@1.0.0'));
  assert.match(notice, /ConardLi\/garden-skills/);
  assert.match(notice, new RegExp(REVISION));
  assert.match(notice, /upstream\/one\.md/);
  assert.match(notice, new RegExp('1'.repeat(64)));
  assert.match(notice, /MIT/);
  assert.match(notice, /https:\/\/github\.com\/ConardLi\/garden-skills/);
  assert.match(notice, /Adapted into a versioned image-effect card\./);
});
