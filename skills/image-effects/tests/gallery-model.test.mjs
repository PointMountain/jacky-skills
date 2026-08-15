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
    title: { en: titleEn, ...(titleZh === undefined ? {} : { zh: titleZh }) },
    summary: { en: summaryEn, ...(summaryZh === undefined ? {} : { zh: summaryZh }) },
    category,
    invocation: `Use $image-effects effect ${ref} on my uploaded image.`,
  };
}

const FIXTURE_LIBRARY = {
  schemaVersion: 1,
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
      titleEn: 'Paper Horizon',
      titleZh: '纸上地平线',
      summaryEn: 'A wide landscape in pale color.',
      summaryZh: '用淡彩绘制开阔风景。',
      category: 'landscape',
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
      () => assertLibrary({ schemaVersion: 2, effects: [] }),
      (error) => error instanceof Error && /schema.*2/i.test(error.message),
    );
  });

  await t.test('拒绝非数组 effects，并提供可展示消息', () => {
    assert.throws(
      () => assertLibrary({ schemaVersion: 1, effects: null }),
      (error) => error instanceof Error && /effects.*array/i.test(error.message),
    );
  });

  await t.test('拒绝缺少必要字段的 effect', () => {
    assert.throws(
      () => assertLibrary({ schemaVersion: 1, effects: [{ id: 'broken' }] }),
      (error) => error instanceof Error && /effect.*ref/i.test(error.message),
    );
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
  assert.equal(ready.library, FIXTURE_LIBRARY);
  assert.equal(ready.loadError, null);

  const failed = loadFailed(ready, new Error('网络暂时不可用'));
  assert.equal(failed.loadStatus, 'error');
  assert.equal(failed.loadError, '网络暂时不可用');
  assert.doesNotMatch(failed.loadError, /Error:|\n\s+at /);

  const retrying = retryLoad(failed);
  assert.equal(retrying.loadStatus, 'loading');
  assert.equal(retrying.loadError, null);
  assert.equal(retrying.loadAttempt, 2);
  assert.equal(retrying.language, 'zh');
  assert.equal(retrying.query, '墨色');
  assert.equal(retrying.category, 'portrait');
  assert.deepEqual(retrying.selectedRefs, ['midnight-ink@1.0.0']);
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
