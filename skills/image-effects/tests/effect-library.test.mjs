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

test('parseEffect rejects YAML values outside strict simple scalars', async (t) => {
  const invalidValues = [
    ['double-quoted empty string', '""'],
    ['single-quoted empty string', "''"],
    ['null keyword', 'null'],
    ['null shorthand', '~'],
    ['flow sequence', '[]'],
    ['flow mapping', '{}'],
    ['literal block', '|'],
    ['folded block', '>'],
    ['explicit tag', '!!map {foo: bar}'],
    ['anchor', '&shared value'],
    ['alias', '*shared'],
    ['quoted scalar', '"Portrait"'],
    ['sequence entry', '- item'],
    ['explicit key', '? key'],
    ['mapping value', ': value'],
    ['reserved at sign', '@reserved'],
    ['reserved backtick', '`reserved`'],
    ['mapping pair', 'foo: bar'],
  ];

  for (const [name, value] of invalidValues) {
    await t.test(name, () => {
      assert.throws(
        () => parseEffect(card({ title_en: value })),
        /simple single-line scalar|empty/i,
      );
    });
  }
});

test('parseEffect rejects unsupported YAML comment syntax', async (t) => {
  const invalidValues = [
    ['comment-only value', '# comment'],
    ['quoted empty value with comment', '"" # comment'],
    ['null value with comment', 'null # comment'],
  ];

  for (const [name, value] of invalidValues) {
    await t.test(name, () => {
      assert.throws(() => parseEffect(card({ title_en: value })), /simple single-line scalar/i);
    });
  }
});

test('parseEffect does not treat null-like plain text as YAML null', () => {
  assert.equal(parseEffect(card({ title_en: 'Nullable portrait' })).title.en, 'Nullable portrait');
  assert.equal(parseEffect(card({ title_en: '~decorative title' })).title.en, '~decorative title');
  assert.equal(parseEffect(card({ title_en: 'C# portrait' })).title.en, 'C# portrait');
  assert.equal(parseEffect(card({ title_en: 'hash#tag portrait' })).title.en, 'hash#tag portrait');
});

test('parseEffect preserves supported plain scalar punctuation and Unicode', () => {
  const values = ['https://example.com/effect', 'C# portrait', 'hash#tag', '治愈，v3。'];

  for (const value of values) {
    assert.equal(parseEffect(card({ title_en: value })).title.en, value);
  }
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

test('parseEffect rejects non-canonical or unsafe provenance fields', async (t) => {
  const invalidRepositories = [
    'https://github.com/owner/repo',
    'owner/repo/extra',
    '-owner/repo',
    'owner_/repo',
    'owner/repo](https://evil.example)',
  ];
  for (const source_repository of invalidRepositories) {
    await t.test(`repository ${source_repository}`, () => {
      assert.throws(() => parseEffect(card({ source_repository })), /source_repository/i);
    });
  }

  const invalidPaths = [
    'assets//preview.jpg',
    'assets/./preview.jpg',
    'assets/%2e%2e/preview.jpg',
    'assets\\preview.jpg',
    'assets/pre`view.jpg',
  ];
  for (const preview of invalidPaths) {
    await t.test(`path ${preview}`, () => {
      assert.throws(() => parseEffect(card({ preview })), /relative path|canonical path/i);
    });
  }

  await t.test('encoded source path traversal', () => {
    assert.throws(
      () => parseEffect(card({ source_paths: 'upstream/%2e%2e/secret.md' })),
      /relative path|canonical path/i,
    );
  });

  const urlUnsafeSourcePaths = [
    'src/a%2Fb.md',
    'src/file#fragment.md',
    'src/file?ref=main',
    'src/%ZZ.md',
  ];
  for (const source_paths of urlUnsafeSourcePaths) {
    await t.test(`URL-unsafe source path ${source_paths}`, () => {
      assert.throws(
        () => parseEffect(card({ source_paths })),
        /relative path|canonical path/i,
      );
    });
  }

  await t.test('URL-unsafe preview path', () => {
    assert.throws(
      () => parseEffect(card({ preview: 'assets/file?ref=main.jpg' })),
      /relative path|canonical path/i,
    );
  });

  await t.test('NUL in scalar', () => {
    assert.throws(
      () => parseEffect(card({ adaptation_notice: 'safe\0unsafe' })),
      /control character/i,
    );
  });

  await t.test('trailing Tab in scalar', () => {
    assert.throws(
      () => parseEffect(card({ adaptation_notice: 'unsafe\t' })),
      /control character/i,
    );
  });

  const invalidUrls = [
    'https://user:password@example.com/license',
    'https://@example.com/license',
    'https://example.com/license#fragment',
    'https://example.com/license#',
    'https://example.com/%0Alicense',
    'https://example.com/%250Alicense',
  ];
  for (const source_license_url of invalidUrls) {
    await t.test(`URL ${source_license_url}`, () => {
      assert.throws(() => parseEffect(card({ source_license_url })), /HTTPS URL/i);
    });
  }
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

test('loadEffects, buildLibrary, and notices reject duplicate versioned references', async () => {
  const effect = parseEffect(card());
  assert.throws(() => buildLibrary([effect, effect], '2026-08-16T00:00:00.000Z'), /duplicate.*ref/i);
  assert.throws(() => renderThirdPartyNotices([effect, effect], '# Header\n'), /duplicate.*ref/i);

  const root = await mkdtemp(path.join(tmpdir(), 'image-effects-duplicates-'));
  try {
    await writeFile(path.join(root, 'one.md'), card());
    await writeFile(path.join(root, 'two.md'), card());
    await assert.rejects(() => loadEffects(root), /duplicate.*ref/i);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('effect IDs use ASCII code-unit order without locale comparison', () => {
  const later = parseEffect(card({ id: 'z-effect' }));
  const earlier = parseEffect(card({ id: 'a-effect' }));
  const originalLocaleCompare = String.prototype.localeCompare;
  let ids;

  String.prototype.localeCompare = () => {
    throw new Error('localeCompare must not be used');
  };
  try {
    ids = buildLibrary([later, earlier], '2026-08-16T00:00:00.000Z').effects.map(
      (effect) => effect.id,
    );
  } finally {
    String.prototype.localeCompare = originalLocaleCompare;
  }

  assert.deepEqual(ids, ['a-effect', 'z-effect']);
});

test('SemVer sorting preserves numeric precedence beyond Number safe integers', () => {
  const larger = parseEffect(card({ version: '9007199254740993.0.0' }));
  const smaller = parseEffect(card({ version: '9007199254740992.0.0' }));

  const library = buildLibrary([larger, smaller], '2026-08-16T00:00:00.000Z');

  assert.deepEqual(
    library.effects.map((effect) => effect.version),
    ['9007199254740992.0.0', '9007199254740993.0.0'],
  );
});

test('SemVer prerelease text identifiers use ASCII code-unit order', () => {
  const lowercase = parseEffect(card({ version: '1.0.0-a' }));
  const uppercase = parseEffect(card({ version: '1.0.0-B' }));

  const library = buildLibrary([lowercase, uppercase], '2026-08-16T00:00:00.000Z');

  assert.deepEqual(
    library.effects.map((effect) => effect.version),
    ['1.0.0-B', '1.0.0-a'],
  );
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
        previewUrl: './media/healing-anime-scribble-v3@1.0.0.jpg',
        sourceUrl: './source/healing-anime-scribble-v3@1.0.0.md',
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

test('buildLibrary gives every effect version distinct versioned artifact URLs', () => {
  const first = parseEffect(card({ version: '1.0.0' }));
  const second = parseEffect(card({ version: '2.0.0' }));

  const library = buildLibrary([second, first], '2026-08-16T00:00:00.000Z');

  assert.deepEqual(
    library.effects.map(({ previewUrl, sourceUrl }) => ({ previewUrl, sourceUrl })),
    [
      {
        previewUrl: './media/healing-anime-scribble-v3@1.0.0.jpg',
        sourceUrl: './source/healing-anime-scribble-v3@1.0.0.md',
      },
      {
        previewUrl: './media/healing-anime-scribble-v3@2.0.0.jpg',
        sourceUrl: './source/healing-anime-scribble-v3@2.0.0.md',
      },
    ],
  );
});

test('renderThirdPartyNotices emits the exact escaped machine protocol', () => {
  const effect = parseEffect(
    card({
      source_paths: 'upstream/source_file.md',
      adaptation_notice: 'Adapted [guide](https://evil.example).',
    }),
    'references/effects/healing-anime-scribble-v3.md',
  );

  assert.equal(
    renderThirdPartyNotices([effect], '# Third-party notices\n'),
    `# Third-party notices

## healing-anime-scribble-v3@1.0.0

- Repository: \`ConardLi/garden-skills\`
- Revision: \`${REVISION}\`
- Source: \`upstream/source_file.md\` (SHA-256: \`${SOURCE_SHA}\`)
- License: [MIT](<https://github.com/ConardLi/garden-skills/blob/${REVISION}/LICENSE>)
- Adaptation: Adapted \\[guide\\]\\(https://evil.example\\).
`,
  );
});
