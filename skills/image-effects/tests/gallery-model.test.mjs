import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  assertLibrary,
  clearSelection,
  createGalleryState,
  getSelectedInvocations,
  getVisibleEffects,
  loadFailed,
  loadSucceeded,
  localizeEffect,
  retryLoad,
  startLoading,
  toggleSelection,
} from '../gallery/gallery-model.mjs';
import { PUBLIC_MEDIA_BASE_URL } from '../gallery/gallery-config.mjs';

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function effect({
  id,
  version = '1.0.0',
  titleEn,
  titleZh,
  summaryEn,
  summaryZh,
  category,
}) {
  const ref = `${id}@${version}`;
  return {
    ref,
    id,
    version,
    executionKind: 'host-image-generation',
    previewWidth: 1024,
    previewHeight: 1536,
    title: { en: titleEn, ...(titleZh === undefined ? {} : { zh: titleZh }) },
    summary: { en: summaryEn, ...(summaryZh === undefined ? {} : { zh: summaryZh }) },
    category,
    input: { mode: 'image', min: 1, max: 1, formats: ['jpeg', 'png'] },
    outputCount: 1,
    previewUrl: `./media/${ref}.jpg`,
    sourceUrl: `./source/${ref}.md`,
    provenance: {
      repository: 'example/effects',
      revision: 'a'.repeat(40),
      license: { spdx: 'MIT', url: 'https://example.com/license' },
      preview: {
        origin: 'Generated fictional preview.',
        author: 'Example author',
        licenseSpdx: 'CC-BY-4.0',
      },
    },
    invocation: `Use $image-effects effect ${ref} on my uploaded image.`,
  };
}

const FIXTURE_LIBRARY = {
  schemaVersion: 2,
  generatedAt: '2026-08-16T00:00:00.000Z',
  effects: [
    effect({
      id: 'midnight-ink',
      titleEn: 'Midnight Ink',
      titleZh: '午夜墨色',
      summaryEn: 'A quiet PORTRAIT drawn in ink.',
      summaryZh: '以墨线绘制安静的人像。',
      category: 'portrait',
    }),
    effect({
      id: 'paper-horizon',
      version: '2.1.0',
      titleEn: 'Café Paper Horizon',
      titleZh: '纸上地平线',
      summaryEn: 'A wide landscape in pale color.',
      summaryZh: '用淡彩绘制开阔风景。',
      category: 'editorial',
    }),
    effect({
      id: 'neon-face',
      version: '3.0.0',
      titleEn: 'Neon Face',
      titleZh: '霓虹面孔',
      summaryEn: 'Electric profile lighting.',
      summaryZh: '带有电光轮廓的人像。',
      category: 'portrait',
    }),
  ],
};

function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  for (const child of Object.values(value)) deepFreeze(child);
  return Object.freeze(value);
}

test('assertLibrary 接受真实生成的 Library，并拒绝版本错误或无效 effects', async (t) => {
  const realLibrary = JSON.parse(
    await readFile(path.join(SKILL_ROOT, 'gallery/api/library.json'), 'utf8'),
  );
  assert.equal(assertLibrary(realLibrary), realLibrary);

  await t.test('拒绝不支持的 schemaVersion，并提供可展示消息', () => {
    assert.throws(
      () =>
        assertLibrary({
          schemaVersion: 1,
          generatedAt: '2026-08-16T00:00:00.000Z',
          effects: [],
        }),
      (error) => error instanceof Error && /schema.*1/i.test(error.message),
    );
  });

  await t.test('拒绝非数组 effects，并提供可展示消息', () => {
    assert.throws(
      () =>
        assertLibrary({
          schemaVersion: 2,
          generatedAt: '2026-08-16T00:00:00.000Z',
          effects: null,
        }),
      (error) => error instanceof Error && /effects.*array/i.test(error.message),
    );
  });

  await t.test('拒绝缺少必要字段的 effect', () => {
    assert.throws(
      () =>
        assertLibrary({
          schemaVersion: 2,
          generatedAt: '2026-08-16T00:00:00.000Z',
          effects: [{ id: 'broken' }],
        }),
      (error) => error instanceof Error && /effect.*ref/i.test(error.message),
    );
  });
});

test('assertLibrary 要求顶层字段为 own property、合法 ISO 时间且 effects 不超过 1000', async (t) => {
  await t.test('拒绝从 prototype 继承的顶层字段', () => {
    const inherited = Object.create(FIXTURE_LIBRARY);
    assert.throws(() => assertLibrary(inherited), /schemaVersion|own/i);
  });

  await t.test('拒绝缺失或非法 generatedAt', () => {
    const missing = structuredClone(FIXTURE_LIBRARY);
    delete missing.generatedAt;
    assert.throws(() => assertLibrary(missing), /generatedAt/i);

    const invalid = structuredClone(FIXTURE_LIBRARY);
    invalid.generatedAt = 'not-a-date';
    assert.throws(() => assertLibrary(invalid), /generatedAt/i);
  });

  await t.test('拒绝超过 1000 个 effects', () => {
    const oversized = structuredClone(FIXTURE_LIBRARY);
    oversized.effects = Array.from({ length: 1001 }, (_, index) =>
      effect({
        id: `effect-${index}`,
        titleEn: `Effect ${index}`,
        titleZh: `效果 ${index}`,
        summaryEn: 'Summary',
        summaryZh: '摘要',
        category: 'portrait',
      }),
    );
    assert.throws(() => assertLibrary(oversized), /1000|effects/i);
  });
});

test('assertLibrary 要求 effect 完整公共 schema 且拒绝继承字段', async (t) => {
  const requiredFields = [
    'ref',
    'id',
    'version',
    'executionKind',
    'previewWidth',
    'previewHeight',
    'title',
    'summary',
    'category',
    'input',
    'outputCount',
    'previewUrl',
    'sourceUrl',
    'provenance',
    'invocation',
  ];

  for (const field of requiredFields) {
    await t.test(`缺少 ${field}`, () => {
      const library = structuredClone(FIXTURE_LIBRARY);
      delete library.effects[0][field];
      assert.throws(() => assertLibrary(library), new RegExp(field, 'i'));
    });
  }

  await t.test('拒绝全部字段仅来自 prototype 的 effect', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0] = Object.create(library.effects[0]);
    assert.throws(() => assertLibrary(library), /effect|own/i);
  });
});

test('assertLibrary 拒绝重复或不规范版本引用、非法本地化及超长字符串', async (t) => {
  await t.test('重复 ref', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects.push(structuredClone(library.effects[0]));
    assert.throws(() => assertLibrary(library), /duplicate|ref/i);
  });

  await t.test('ref 与 id@version 不一致', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].ref = 'midnight-ink@9.9.9';
    assert.throws(() => assertLibrary(library), /ref/i);
  });

  const invalidIdentityCases = [
    ['id', 'Not Kebab'],
    ['version', 'v1.0'],
  ];
  for (const [field, value] of invalidIdentityCases) {
    await t.test(`非法 ${field}`, () => {
      const library = structuredClone(FIXTURE_LIBRARY);
      library.effects[0][field] = value;
      assert.throws(() => assertLibrary(library), new RegExp(field, 'i'));
    });
  }

  await t.test('本地化字段必须 own en/zh 且非空', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].title = Object.create({ en: 'Inherited', zh: '继承值' });
    assert.throws(() => assertLibrary(library), /title/i);

    const missingZh = structuredClone(FIXTURE_LIBRARY);
    delete missingZh.effects[0].summary.zh;
    assert.throws(() => assertLibrary(missingZh), /summary.*zh/i);

    const emptyEn = structuredClone(FIXTURE_LIBRARY);
    emptyEn.effects[0].title.en = '   ';
    assert.throws(() => assertLibrary(emptyEn), /title.*en/i);
  });

  await t.test('拒绝超长用户可控字符串', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].summary.en = 'x'.repeat(10_000);
    assert.throws(() => assertLibrary(library), /summary/i);
  });
});

test('assertLibrary 验证 input、outputCount、受管路径与 provenance', async (t) => {
  await t.test('接受生产构建使用的固定 OSS 图片地址', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    const item = library.effects[0];
    item.previewUrl = `${PUBLIC_MEDIA_BASE_URL}${item.ref}.jpg`;
    assert.equal(assertLibrary(library), library);
  });

  const missingNestedCases = [
    ['input.mode', (item) => delete item.input.mode],
    ['input.min', (item) => delete item.input.min],
    ['input.max', (item) => delete item.input.max],
    ['input.formats', (item) => delete item.input.formats],
    ['provenance.repository', (item) => delete item.provenance.repository],
    ['provenance.revision', (item) => delete item.provenance.revision],
    ['provenance.license', (item) => delete item.provenance.license],
    ['license.spdx', (item) => delete item.provenance.license.spdx],
    ['license.url', (item) => delete item.provenance.license.url],
    ['provenance.preview', (item) => delete item.provenance.preview],
    ['preview.origin', (item) => delete item.provenance.preview.origin],
    ['preview.author', (item) => delete item.provenance.preview.author],
    ['preview.licenseSpdx', (item) => delete item.provenance.preview.licenseSpdx],
  ];
  for (const [name, mutate] of missingNestedCases) {
    await t.test(`缺少 ${name}`, () => {
      const library = structuredClone(FIXTURE_LIBRARY);
      mutate(library.effects[0]);
      assert.throws(() => assertLibrary(library), new RegExp(name.split('.')[0], 'i'));
    });
  }

  const invalidCases = [
    ['executionKind', (item) => (item.executionKind = 'browser-canvas')],
    ['previewWidth', (item) => (item.previewWidth = 0)],
    ['previewWidth maximum', (item) => (item.previewWidth = 20_001)],
    ['previewHeight', (item) => (item.previewHeight = 1.5)],
    ['previewHeight maximum', (item) => (item.previewHeight = 20_001)],
    ['input.mode', (item) => (item.input.mode = 'video')],
    ['input.min', (item) => (item.input.min = -1)],
    ['input.max', (item) => (item.input.max = 0)],
    ['input.formats', (item) => (item.input.formats = ['jpeg', '../raw'])],
    ['outputCount', (item) => (item.outputCount = 0)],
    ['previewUrl filename', (item) => (item.previewUrl = './media/other@1.0.0.jpg')],
    ['previewUrl traversal', (item) => (item.previewUrl = './media/../secret.jpg')],
    ['previewUrl query', (item) => (item.previewUrl += '?token=secret')],
    ['previewUrl extension', (item) => (item.previewUrl = `./media/${item.ref}.gif`)],
    ['previewUrl remote host', (item) => (item.previewUrl = `https://example.com/media/${item.ref}.jpg`)],
    ['previewUrl remote query', (item) => (item.previewUrl = `${PUBLIC_MEDIA_BASE_URL}${item.ref}.jpg?token=secret`)],
    ['previewUrl remote filename', (item) => (item.previewUrl = `${PUBLIC_MEDIA_BASE_URL}other@1.0.0.jpg`)],
    ['sourceUrl filename', (item) => (item.sourceUrl = './source/other@1.0.0.md')],
    ['sourceUrl fragment', (item) => (item.sourceUrl += '#private')],
    ['repository', (item) => (item.provenance.repository = '../private')],
    ['revision', (item) => (item.provenance.revision = 'main')],
    ['license.spdx', (item) => (item.provenance.license.spdx = '')],
    ['license.url', (item) => (item.provenance.license.url = 'file:///private')],
    ['preview.origin', (item) => (item.provenance.preview.origin = '')],
    ['preview.author', (item) => (item.provenance.preview.author = '')],
    ['preview.licenseSpdx', (item) => (item.provenance.preview.licenseSpdx = '')],
  ];

  for (const [name, mutate] of invalidCases) {
    await t.test(name, () => {
      const library = structuredClone(FIXTURE_LIBRARY);
      mutate(library.effects[0]);
      assert.throws(() => assertLibrary(library), new RegExp(name.split(/[ .]/)[0], 'i'));
    });
  }

  await t.test('拒绝从 prototype 继承的 input 字段', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].input = Object.create(library.effects[0].input);
    assert.throws(() => assertLibrary(library), /input/i);
  });

  await t.test('image 拒绝 1..2 输入范围', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].input.max = 2;
    assert.throws(() => assertLibrary(library), /input/i);
  });

  await t.test("image 拒绝语法合法但不受支持的 ['webp'] 格式", () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].input.formats = ['webp'];
    assert.throws(() => assertLibrary(library), /input/i);
  });

  await t.test('text-or-image 仅接受 0..1 JPEG/PNG 契约', () => {
    const valid = structuredClone(FIXTURE_LIBRARY);
    valid.effects[0].input = {
      mode: 'text-or-image',
      min: 0,
      max: 1,
      formats: ['jpeg', 'png'],
    };
    assert.equal(assertLibrary(valid), valid);

    const invalidContracts = [
      (input) => (input.min = 1),
      (input) => (input.max = 0),
      (input) => (input.formats = ['jpeg']),
      (input) => (input.formats = ['png', 'jpeg']),
    ];
    for (const mutate of invalidContracts) {
      const library = structuredClone(valid);
      mutate(library.effects[0].input);
      assert.throws(() => assertLibrary(library), /input/i);
    }
  });
});

test('assertLibrary 只接受发布分类和合法 execution/category/input 组合', async (t) => {
  await t.test('拒绝 grade 等未发布分类', () => {
    const library = structuredClone(FIXTURE_LIBRARY);
    library.effects[0].category = 'grade';
    assert.throws(() => assertLibrary(library), /category/i);
  });

  await t.test('layout 只接受 editorial image 1..1', () => {
    const valid = structuredClone(FIXTURE_LIBRARY);
    valid.effects[1].executionKind = 'host-image-generation-and-layout';
    assert.equal(assertLibrary(valid), valid);

    const wrongCategory = structuredClone(valid);
    wrongCategory.effects[1].category = 'zine';
    assert.throws(() => assertLibrary(wrongCategory), /executionKind|category|input/i);

    const wrongInput = structuredClone(valid);
    wrongInput.effects[1].input = {
      mode: 'text-or-image',
      min: 0,
      max: 1,
      formats: ['jpeg', 'png'],
    };
    assert.throws(() => assertLibrary(wrongInput), /executionKind|category|input/i);
  });

  await t.test('拒绝被篡改为 layout 的真实 Minimal Zine 条目', async () => {
    const library = JSON.parse(
      await readFile(path.join(SKILL_ROOT, 'gallery/api/library.json'), 'utf8'),
    );
    const minimal = library.effects.find(({ ref }) => ref === 'minimal-zine-poster@1.0.0');
    assert.ok(minimal, 'missing Minimal Zine entry');
    minimal.executionKind = 'host-image-generation-and-layout';
    assert.throws(() => assertLibrary(library), /executionKind|category|input/i);
  });

  await t.test('保留其余已批准的单阶段组合', () => {
    const approved = [
      ['portrait', 'image'],
      ['editorial', 'image'],
      ['zine', 'image'],
      ['zine', 'text-or-image'],
    ];
    for (const [category, mode] of approved) {
      const library = structuredClone(FIXTURE_LIBRARY);
      library.effects[0].category = category;
      library.effects[0].input = {
        mode,
        min: mode === 'text-or-image' ? 0 : 1,
        max: 1,
        formats: ['jpeg', 'png'],
      };
      assert.equal(assertLibrary(library), library, `${category}/${mode}`);
    }
  });
});

test('localizeEffect 投影中英文并在缺少翻译时回退英文，同时保留其他字段', () => {
  const source = FIXTURE_LIBRARY.effects[0];
  const en = localizeEffect(source, 'en');
  const zh = localizeEffect(source, 'zh');
  const fallbackSource = effect({
    id: 'english-only',
    titleEn: 'English only',
    summaryEn: 'Fallback summary',
    category: 'portrait',
  });

  assert.equal(en.title, 'Midnight Ink');
  assert.equal(en.summary, 'A quiet PORTRAIT drawn in ink.');
  assert.equal(zh.title, '午夜墨色');
  assert.equal(zh.summary, '以墨线绘制安静的人像。');
  assert.equal(zh.ref, source.ref);
  assert.equal(zh.category, source.category);
  assert.equal(zh.executionKind, source.executionKind);
  assert.equal(zh.previewWidth, source.previewWidth);
  assert.equal(zh.previewHeight, source.previewHeight);
  assert.equal(localizeEffect(fallbackSource, 'zh').title, 'English only');
  assert.equal(localizeEffect(fallbackSource, 'zh').summary, 'Fallback summary');
  assert.notEqual(zh, source);
  assert.deepEqual(source.title, { en: 'Midnight Ink', zh: '午夜墨色' });
});

test('搜索 id、ref 和当前语言标题摘要时忽略大小写，纯空白等价于空查询', async (t) => {
  const cases = [
    ['id', 'MIDNIGHT-INK', ['midnight-ink']],
    ['ref', 'PAPER-HORIZON@2.1.0', ['paper-horizon']],
    ['英文标题', 'nEoN fAcE', ['neon-face']],
    ['英文摘要', 'portrait DRAWN', ['midnight-ink']],
  ];

  for (const [name, query, expected] of cases) {
    await t.test(name, () => {
      const state = loadSucceeded(createGalleryState({ language: 'en', query }), FIXTURE_LIBRARY);
      assert.deepEqual(getVisibleEffects(state).map(({ id }) => id), expected);
    });
  }

  const chinese = loadSucceeded(
    createGalleryState({ language: 'zh', query: '电光轮廓' }),
    FIXTURE_LIBRARY,
  );
  assert.deepEqual(getVisibleEffects(chinese).map(({ id }) => id), ['neon-face']);

  const currentLanguageOnly = loadSucceeded(
    createGalleryState({ language: 'zh', query: 'Electric profile' }),
    FIXTURE_LIBRARY,
  );
  assert.deepEqual(getVisibleEffects(currentLanguageOnly), []);

  const normalizedUnicode = loadSucceeded(
    createGalleryState({ language: 'en', query: 'CAFE\u0301' }),
    FIXTURE_LIBRARY,
  );
  assert.deepEqual(getVisibleEffects(normalizedUnicode).map(({ id }) => id), ['paper-horizon']);

  const whitespace = loadSucceeded(
    createGalleryState({ language: 'en', query: ' \n\t ' }),
    FIXTURE_LIBRARY,
  );
  assert.deepEqual(
    getVisibleEffects(whitespace).map(({ id }) => id),
    FIXTURE_LIBRARY.effects.map(({ id }) => id),
  );
});

test('category 支持 all、单分类以及与搜索条件组合', () => {
  const all = loadSucceeded(createGalleryState({ category: 'all' }), FIXTURE_LIBRARY);
  const portrait = loadSucceeded(
    createGalleryState({ category: 'portrait' }),
    FIXTURE_LIBRARY,
  );
  const combined = loadSucceeded(
    createGalleryState({ category: 'portrait', query: 'neon' }),
    FIXTURE_LIBRARY,
  );

  assert.deepEqual(getVisibleEffects(all).map(({ id }) => id), [
    'midnight-ink',
    'paper-horizon',
    'neon-face',
  ]);
  assert.deepEqual(getVisibleEffects(portrait).map(({ id }) => id), [
    'midnight-ink',
    'neon-face',
  ]);
  assert.deepEqual(getVisibleEffects(combined).map(({ id }) => id), ['neon-face']);
});

test('选择可切换、忽略未知 ref、可清空，并始终按 Library 顺序输出版本化 invocation', () => {
  let state = loadSucceeded(createGalleryState(), FIXTURE_LIBRARY);
  state = toggleSelection(state, 'neon-face@3.0.0');
  state = toggleSelection(state, 'missing@1.0.0');
  state = toggleSelection(state, 'midnight-ink@1.0.0');

  assert.deepEqual(state.selectedRefs, ['neon-face@3.0.0', 'midnight-ink@1.0.0']);
  assert.ok(Array.isArray(state.selectedRefs));
  assert.ok(Object.isFrozen(state.selectedRefs));
  assert.deepEqual(getSelectedInvocations(state), [
    'Use $image-effects effect midnight-ink@1.0.0 on my uploaded image.',
    'Use $image-effects effect neon-face@3.0.0 on my uploaded image.',
  ]);

  state = toggleSelection(state, 'neon-face@3.0.0');
  assert.deepEqual(state.selectedRefs, ['midnight-ink@1.0.0']);
  assert.deepEqual(clearSelection(state).selectedRefs, []);
});

test('选择偏好只接受至多 1000 个规范 ref，加载后清除未知或过期项', () => {
  const oversized = Array.from({ length: 100_000 }, (_, index) => `effect-${index}@1.0.0`);
  const capped = createGalleryState({ selectedRefs: oversized });
  assert.equal(capped.selectedRefs.length, 1000);

  const initial = createGalleryState({
    selectedRefs: [
      'midnight-ink@1.0.0',
      'retired-effect@4.0.0',
      'not-versioned',
      ' bad@1.0.0 ',
      42,
    ],
  });

  assert.deepEqual(initial.selectedRefs, [
    'midnight-ink@1.0.0',
    'retired-effect@4.0.0',
    'bad@1.0.0',
  ]);

  const ready = loadSucceeded(initial, FIXTURE_LIBRARY);
  assert.deepEqual(ready.selectedRefs, ['midnight-ink@1.0.0']);
  assert.ok(ready.selectedRefs.length <= ready.library.effects.length);
  assert.ok(toggleSelection(ready, 'neon-face@3.0.0').selectedRefs.length <= 3);
});

test('loadSucceeded 保存深冻结 canonical snapshot，localizeEffect 不产生嵌套别名', () => {
  const inputLibrary = structuredClone(FIXTURE_LIBRARY);
  const ready = loadSucceeded(createGalleryState(), inputLibrary);

  assert.notEqual(ready.library, inputLibrary);
  assert.notEqual(ready.library.effects, inputLibrary.effects);
  assert.notEqual(ready.library.effects[0].input, inputLibrary.effects[0].input);
  assert.notEqual(
    ready.library.effects[0].provenance.license,
    inputLibrary.effects[0].provenance.license,
  );
  assert.ok(Object.isFrozen(ready.library));
  assert.ok(Object.isFrozen(ready.library.effects));
  assert.ok(Object.isFrozen(ready.library.effects[0].title));
  assert.ok(Object.isFrozen(ready.library.effects[0].summary));
  assert.ok(Object.isFrozen(ready.library.effects[0].input.formats));
  assert.ok(Object.isFrozen(ready.library.effects[0].provenance.license));
  assert.ok(Object.isFrozen(ready.library.effects[0].provenance.preview));
  assert.equal(ready.library.effects[0].executionKind, 'host-image-generation');
  assert.equal(ready.library.effects[0].previewWidth, 1024);
  assert.equal(ready.library.effects[0].previewHeight, 1536);

  inputLibrary.effects[0].title.en = 'Mutated title';
  inputLibrary.effects[0].input.formats.push('gif');
  inputLibrary.effects[0].provenance.preview.author = 'Mutated author';
  assert.equal(ready.library.effects[0].title.en, 'Midnight Ink');
  assert.deepEqual(ready.library.effects[0].input.formats, ['jpeg', 'png']);
  assert.equal(ready.library.effects[0].provenance.preview.author, 'Example author');

  const projection = localizeEffect(ready.library.effects[0], 'en');
  assert.notEqual(projection.input, ready.library.effects[0].input);
  assert.notEqual(projection.provenance, ready.library.effects[0].provenance);
  assert.ok(Object.isFrozen(projection.input.formats));
  assert.ok(Object.isFrozen(projection.provenance.preview));
  assert.throws(() => projection.input.formats.push('gif'), TypeError);
  assert.throws(() => {
    projection.provenance.preview.author = 'Changed';
  }, TypeError);
  assert.equal(ready.library.effects[0].provenance.preview.author, 'Example author');
});

test('加载状态支持成功、失败与重试，attempt 递增且保留偏好和选择', () => {
  const idle = createGalleryState({
    language: 'zh',
    query: '  墨色  ',
    category: 'portrait',
    selectedRefs: ['midnight-ink@1.0.0'],
  });
  assert.equal(idle.loadStatus, 'idle');
  assert.equal(idle.loadAttempt, 0);
  assert.equal(idle.query, '墨色');

  const loading = startLoading(idle);
  assert.equal(loading.loadStatus, 'loading');
  assert.equal(loading.loadAttempt, 1);
  assert.equal(loading.loadError, null);

  const ready = loadSucceeded(loading, FIXTURE_LIBRARY);
  assert.equal(ready.loadStatus, 'ready');
  assert.notEqual(ready.library, FIXTURE_LIBRARY);
  assert.deepEqual(ready.library, FIXTURE_LIBRARY);
  assert.equal(ready.loadError, null);

  const failed = loadFailed(ready, new Error('token=secret private/location.txt'));
  assert.equal(failed.loadStatus, 'error');
  assert.equal(failed.loadError, '无法加载效果库，请重试。');
  assert.doesNotMatch(failed.loadError, /secret|private|Error:|\n\s+at /);

  const retrying = retryLoad(failed);
  assert.equal(retrying.loadStatus, 'loading');
  assert.equal(retrying.loadError, null);
  assert.equal(retrying.loadAttempt, 2);
  assert.equal(retrying.language, 'zh');
  assert.equal(retrying.query, '墨色');
  assert.equal(retrying.category, 'portrait');
  assert.deepEqual(retrying.selectedRefs, ['midnight-ink@1.0.0']);
});

test('loadFailed 仅展示安全 Gallery 校验消息，其他错误按语言统一脱敏', () => {
  const invalidLibrary = structuredClone(FIXTURE_LIBRARY);
  invalidLibrary.effects[0].previewUrl = './media/secret.jpg?token=abc';
  let validationError;
  try {
    loadSucceeded(createGalleryState(), invalidLibrary);
  } catch (error) {
    validationError = error;
  }

  const validationFailure = loadFailed(createGalleryState({ language: 'en' }), validationError);
  assert.match(validationFailure.loadError, /effect library/i);
  assert.doesNotMatch(validationFailure.loadError, /secret|token|abc/);

  const ordinaryEn = loadFailed(
    createGalleryState({ language: 'en' }),
    new Error('Bearer private-token at private/location/key'),
  );
  assert.equal(ordinaryEn.loadError, 'Unable to load the effect library. Please try again.');
  assert.doesNotMatch(ordinaryEn.loadError, /private|token|Bearer/);

  const ordinaryZh = loadFailed(
    createGalleryState({ language: 'zh' }),
    'https://example.com/?token=private',
  );
  assert.equal(ordinaryZh.loadError, '无法加载效果库，请重试。');
  assert.doesNotMatch(ordinaryZh.loadError, /private|token|example/);
});

test('createGalleryState 规范化无效偏好，所有操作均不修改传入 state 或 library', () => {
  const defaults = createGalleryState({
    language: 'fr',
    query: 42,
    category: '  ',
    selectedRefs: ['midnight-ink@1.0.0', '', 'midnight-ink@1.0.0', 12],
  });
  assert.equal(defaults.language, 'en');
  assert.equal(defaults.query, '');
  assert.equal(defaults.category, 'all');
  assert.deepEqual(defaults.selectedRefs, ['midnight-ink@1.0.0']);

  const library = deepFreeze(structuredClone(FIXTURE_LIBRARY));
  const state = deepFreeze(loadSucceeded(defaults, library));
  const stateSnapshot = structuredClone(state);
  const librarySnapshot = structuredClone(library);

  getVisibleEffects(state);
  getSelectedInvocations(state);
  localizeEffect(library.effects[0], state.language);
  toggleSelection(state, 'paper-horizon@2.1.0');
  clearSelection(state);
  startLoading(state);
  retryLoad(state);
  loadSucceeded(state, library);
  loadFailed(state, '加载失败');

  assert.deepEqual(state, stateSnapshot);
  assert.deepEqual(library, librarySnapshot);
});
