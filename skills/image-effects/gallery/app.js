import { assertLibrary, clearSelection, createGalleryState, getSelectedInvocations, getVisibleEffects, loadFailed, loadSucceeded, localizeEffect, retryLoad, startLoading, toggleSelection } from './gallery-model.mjs';
import { translations } from './translations.js';
import { captureFocus, copyText, effectTitleId, readLocationFilters, restoreFocus, syncLocationFilters } from './gallery-runtime.mjs';
const INSTALL_COMMAND = 'npx skills add wangjs-jacky/image-effects';
const THEME_ORDER = Object.freeze(['system', 'dark', 'light']);
const app = document.querySelector('#app');
const liveRegion = document.querySelector('#app-status');
const themeColor = document.querySelector('meta[name="theme-color"]');
let searchFrame = 0;
let pendingQuery = '';
let composing = false;
function readPreference(key, allowed, fallback) {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value) ? value : fallback;
  } catch {
    return fallback;
  }
}
let state = Object.freeze(
  createGalleryState({
    language: readPreference('image-effects-language', ['en', 'zh'], 'en'),
    ...readLocationFilters(),
  }),
);
let view = Object.freeze({ theme: readPreference('image-effects-theme', THEME_ORDER, 'dark') });
function withTokens(template, values = {}) {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}
function persist(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 存储不可用时，当前页面中的偏好仍然有效。
  }
}
function node(tag, options = {}, children = []) {
  const element = document.createElement(tag);
  if (options.className) element.className = options.className;
  if (options.text !== undefined) element.textContent = options.text;
  for (const [name, value] of Object.entries(options.attrs ?? {})) {
    if (value !== undefined && value !== null) element.setAttribute(name, String(value));
  }
  for (const [name, value] of Object.entries(options.dataset ?? {})) {
    element.dataset[name] = value;
  }
  element.append(...children.filter(Boolean));
  return element;
}
function button(text, options = {}) {
  const element = node('button', {
    className: options.className,
    text,
    attrs: { type: 'button', ...options.attrs },
    dataset: options.dataset,
  });
  if (options.onClick) element.addEventListener('click', options.onClick);
  return element;
}
function externalLink(text, href, options = {}) {
  return node('a', {
    className: options.className,
    text,
    attrs: {
      href,
      target: '_blank',
      rel: 'noopener noreferrer',
      ...options.attrs,
    },
    dataset: options.dataset,
  });
}
function announce(message) {
  liveRegion.textContent = '';
  requestAnimationFrame(() => { liveRegion.textContent = message; });
}
async function copyWithFeedback(value, successMessage) {
  const t = translations[state.language];
  try {
    await copyText(value);
    announce(successMessage);
  } catch {
    announce(t.copyFailed);
  }
}
function setState(nextState, renderOptions) {
  state = Object.freeze(nextState);
  render(renderOptions);
}
function validCategory(nextState) {
  const effects = nextState.library?.effects;
  if (!effects || nextState.category === 'all') return nextState;
  return effects.some((effect) => effect.category === nextState.category)
    ? nextState
    : { ...nextState, category: 'all' };
}
function makeHeader(t) {
  const languageToggle = button(t.languageAction, {
    className: 'utility-button language-button',
    attrs: { 'aria-label': t.languageLabel },
    dataset: { testid: 'language-toggle', focusKey: 'language-toggle' },
    onClick: () => {
      const language = state.language === 'en' ? 'zh' : 'en';
      persist('image-effects-language', language);
      setState({ ...state, language });
    },
  });
  const currentTheme = t[`theme${view.theme[0].toUpperCase()}${view.theme.slice(1)}`];
  const themeToggle = button(withTokens(t.themeValue, { theme: currentTheme }), {
    className: 'utility-button theme-button',
    attrs: { 'aria-label': t.themeLabel },
    dataset: { testid: 'theme-toggle', focusKey: 'theme-toggle' },
    onClick: () => {
      const nextIndex = (THEME_ORDER.indexOf(view.theme) + 1) % THEME_ORDER.length;
      view = Object.freeze({ ...view, theme: THEME_ORDER[nextIndex] });
      persist('image-effects-theme', view.theme);
      render();
    },
  });
  return node('header', { className: 'site-header' }, [
    node('div', { className: 'brand-lockup' }, [
      node('span', { className: 'brand-mark', attrs: { 'aria-hidden': 'true' } }),
      node('span', { className: 'brand-name', text: t.brand }),
      node('span', { className: 'edition', text: t.edition }),
    ]),
    node('nav', { className: 'utilities', attrs: { 'aria-label': t.archiveLabel } }, [
      languageToggle,
      themeToggle,
    ]),
  ]);
}
function makeIntro(t) {
  const effects = state.library?.effects ?? [];
  const countKey = effects.length === 1 ? 'effectCount' : 'effectCountPlural';
  const stats = state.library
    ? [
        withTokens(t[countKey], { count: effects.length }),
        withTokens(t.schemaLabel, { version: state.library.schemaVersion }),
        withTokens(t.updatedLabel, {
          date: new Intl.DateTimeFormat(state.language, { dateStyle: 'medium' }).format(
            new Date(state.library.generatedAt),
          ),
        }),
      ]
    : [];
  return node('section', { className: 'intro', attrs: { 'aria-labelledby': 'page-title' } }, [
    node('div', { className: 'intro-copy' }, [
      node('p', { className: 'eyebrow', text: t.heroEyebrow }),
      node('h1', { text: t.heroTitle, attrs: { id: 'page-title' } }),
      node('p', { className: 'intro-body', text: t.heroBody }),
    ]),
    node('aside', { className: 'archive-status', attrs: { 'aria-label': t.archiveLabel } }, [
      node('p', { className: 'micro-label', text: t.archiveLabel }),
      ...stats.map((value, index) =>
        node('p', { className: index === 0 ? 'status-primary' : 'status-line', text: value }),
      ),
    ]),
  ]);
}
function makeInstall(t) {
  return node('section', { className: 'install-strip', attrs: { 'aria-label': t.installLabel } }, [
    node('div', { className: 'install-copy' }, [
      node('span', { className: 'micro-label', text: t.installLabel }),
      node('code', { text: INSTALL_COMMAND, dataset: { testid: 'install-command' } }),
    ]),
    button(t.copyInstall, {
      className: 'copy-button',
      dataset: { action: 'copy-install', focusKey: 'copy-install' },
      onClick: () => copyWithFeedback(INSTALL_COMMAND, t.copiedInstall),
    }),
  ]);
}
function updateFilter(field, value) {
  const nextState = { ...state, [field]: value };
  syncLocationFilters(nextState);
  setState(nextState);
}
function scheduleQuery(value) {
  pendingQuery = value;
  if (searchFrame) return;
  searchFrame = requestAnimationFrame(() => {
    searchFrame = 0;
    updateFilter('query', pendingQuery);
  });
}
function makeFilters(t, visibleCount, totalCount) {
  const categories = [...new Set(state.library.effects.map((effect) => effect.category))]
    .sort((left, right) => (left < right ? -1 : left > right ? 1 : 0));
  const search = node('input', {
    className: 'search-input',
    attrs: {
      id: 'effect-search',
      type: 'search',
      value: state.query,
      placeholder: t.searchPlaceholder,
      autocomplete: 'off',
    },
    dataset: { testid: 'search-input', focusKey: 'search-input' },
  });
  search.addEventListener('compositionstart', () => {
    composing = true;
    if (searchFrame) cancelAnimationFrame(searchFrame);
    searchFrame = 0;
  });
  search.addEventListener('compositionend', (event) => {
    composing = false;
    scheduleQuery(event.currentTarget.value);
  });
  search.addEventListener('input', (event) => {
    if (!composing && !event.isComposing) scheduleQuery(event.currentTarget.value);
  });
  const category = node('select', {
    className: 'category-filter',
    attrs: { id: 'category-filter' },
    dataset: { testid: 'category-filter', focusKey: 'category-filter' },
  }, [
    node('option', { text: t.categoryAll, attrs: { value: 'all' } }),
    ...categories.map((value) =>
      node('option', { text: categoryLabel(value, t), attrs: { value } }),
    ),
  ]);
  category.value = state.category;
  category.addEventListener('change', (event) => updateFilter('category', event.currentTarget.value));

  return node('section', { className: 'filters', attrs: { 'aria-label': t.searchLabel } }, [
    node('div', { className: 'field search-field' }, [
      node('label', { text: t.searchLabel, attrs: { for: 'effect-search' } }),
      search,
    ]),
    node('div', { className: 'field category-field' }, [
      node('label', { text: t.categoryLabel, attrs: { for: 'category-filter' } }),
      category,
    ]),
    node('p', {
      className: 'result-count',
      text: withTokens(t.resultsLabel, { visible: visibleCount, total: totalCount }),
      attrs: { 'aria-live': 'polite' },
    }),
  ]);
}
function makeFact(label, value) {
  return node('div', { className: 'fact' }, [
    node('dt', { text: label }),
    node('dd', { text: value }),
  ]);
}
function categoryLabel(category, t) {
  return t.categories[category] ?? category;
}
function makeEffectCard(effect, t) {
  const selected = state.selectedRefs.includes(effect.ref);
  const titleId = effectTitleId(effect.ref);
  const checkbox = node('input', {
    className: 'effect-checkbox',
    attrs: {
      type: 'checkbox',
      checked: selected ? '' : undefined,
      'aria-label': withTokens(t.selectEffect, { title: effect.title }),
    },
    dataset: { testid: 'effect-select', focusKey: `effect-select:${effect.ref}` },
  });
  checkbox.checked = selected;
  checkbox.addEventListener('change', () => setState(toggleSelection(state, effect.ref)));

  const image = node('img', {
    attrs: {
      src: effect.previewUrl,
      alt: withTokens(t.imageAlt, { title: effect.title }),
      loading: 'lazy',
      decoding: 'async',
      width: effect.previewWidth,
      height: effect.previewHeight,
    },
  });

  const inputValue = withTokens(
    effect.input.mode === 'text-or-image'
      ? t.textOrImageInput
      : effect.input.min === effect.input.max && effect.input.min === 1
        ? t.imageInput
        : t.imageInputPlural,
    { min: effect.input.min, max: effect.input.max, formats: effect.input.formats.join(' / ') },
  );
  const outputKey = effect.outputCount === 1 ? 'outputCount' : 'outputCountPlural';

  return node('article', {
    className: `effect-card${selected ? ' is-selected' : ''}`,
    attrs: { 'aria-labelledby': titleId },
    dataset: { testid: 'effect-card' },
  }, [
    node('figure', { className: 'preview-frame' }, [
      image,
      node('figcaption', { className: 'preview-caption' }, [
        node('span', { text: effect.provenance.preview.origin }),
        node('span', {
          text: withTokens(t.previewCreditValue, {
            author: effect.provenance.preview.author,
            license: effect.provenance.preview.licenseSpdx,
          }),
        }),
      ]),
    ]),
    node('div', { className: 'effect-content' }, [
      node('div', { className: 'effect-topline' }, [
        node('span', { className: 'category-chip', text: categoryLabel(effect.category, t) }),
        node('label', { className: 'selection-control' }, [
          checkbox,
          node('span', { text: selected ? t.selected : t.notSelected }),
        ]),
      ]),
      node('div', { className: 'effect-heading' }, [
        node('p', { className: 'version-ref', text: effect.ref }),
        node('h2', { text: effect.title, attrs: { id: titleId } }),
        node('p', { className: 'effect-summary', text: effect.summary }),
      ]),
      node('dl', { className: 'facts' }, [
        makeFact(t.version, effect.version),
        makeFact(t.category, categoryLabel(effect.category, t)),
        makeFact(t.input, inputValue),
        makeFact(t.output, withTokens(t[outputKey], { count: effect.outputCount })),
      ]),
      node('div', { className: 'invocation' }, [
        node('span', { className: 'micro-label', text: t.recipeLabel }),
        node('code', { text: effect.invocation }),
      ]),
      node('div', { className: 'source-block' }, [
        node('p', { className: 'micro-label', text: t.provenanceLabel }),
        node('dl', { className: 'provenance-list' }, [
          makeFact(t.repository, effect.provenance.repository),
          makeFact(t.revision, effect.provenance.revision),
          makeFact(
            t.previewCredit,
            withTokens(t.previewCreditValue, {
              author: effect.provenance.preview.author,
              license: effect.provenance.preview.licenseSpdx,
            }),
          ),
        ]),
        node('div', { className: 'source-actions' }, [
          externalLink(t.source, effect.sourceUrl, {
            className: 'text-link',
            dataset: { testid: 'source-link' },
          }),
          externalLink(withTokens(t.license, { spdx: effect.provenance.license.spdx }), effect.provenance.license.url, {
            className: 'text-link',
            dataset: { testid: 'source-license' },
          }),
        ]),
      ]),
    ]),
  ]);
}
function makeSelectionBar(t) {
  const invocations = getSelectedInvocations(state);
  const selectedEffects = (state.library?.effects ?? [])
    .filter((effect) => state.selectedRefs.includes(effect.ref))
    .map((effect) => localizeEffect(effect, state.language));
  const summary = invocations.length
    ? withTokens(t.selectionCount, { count: invocations.length })
    : t.selectionNone;
  const names = selectedEffects.length
    ? withTokens(t.selectionNames, { names: selectedEffects.map((effect) => effect.title).join(', ') })
    : '';

  return node('section', {
    className: 'selection-bar',
    attrs: { 'aria-label': summary },
  }, [
    node('div', { className: 'selection-summary' }, [
      node('strong', { text: summary }),
      node('span', { text: names }),
    ]),
    node('div', { className: 'selection-actions' }, [
      button(t.clearSelection, {
        className: 'secondary-button',
        attrs: { 'aria-disabled': invocations.length ? 'false' : 'true' },
        dataset: { action: 'clear-selection', focusKey: 'clear-selection' },
        onClick: () => invocations.length && setState(clearSelection(state)),
      }),
      button(t.copySelected, {
        className: 'primary-button',
        attrs: { 'aria-disabled': invocations.length ? 'false' : 'true' },
        dataset: { testid: 'copy-selected', focusKey: 'copy-selected' },
        onClick: () => invocations.length
          && copyWithFeedback(invocations.join('\n'), t.copiedSelected),
      }),
    ]),
  ]);
}
function makeLoadState(t) {
  if (state.loadStatus === 'error') {
    return node('section', {
      className: 'state-panel error-panel',
      attrs: { role: 'alert' },
      dataset: { testid: 'load-error' },
    }, [
      node('p', { className: 'eyebrow', text: t.loadErrorCode }),
      node('h2', { text: t.loadErrorTitle }),
      node('p', { text: state.loadError }),
      button(t.retry, {
        className: 'primary-button',
        dataset: { testid: 'retry-load', focusKey: 'retry-load' },
        onClick: () => loadLibrary(true),
      }),
    ]);
  }
  return node('section', {
    className: 'state-panel loading-panel',
    attrs: { 'aria-live': 'polite', tabindex: '-1' },
    dataset: { action: 'retry-load', focusKey: 'retry-load' },
  }, [
    node('span', { className: 'loading-line', attrs: { 'aria-hidden': 'true' } }),
    node('p', { text: t.loading }),
  ]);
}

function makeEmptyState(t) {
  return node('section', { className: 'state-panel empty-panel' }, [
    node('p', { className: 'eyebrow', text: t.emptyCode }),
    node('h2', { text: t.emptyTitle }),
    node('p', { text: t.emptyBody }),
    button(t.resetFilters, {
      className: 'primary-button',
      dataset: { action: 'reset-filters', focusKey: 'reset-filters' },
      onClick: () => {
        const nextState = { ...state, query: '', category: 'all' };
        syncLocationFilters(nextState);
        setState(nextState, { focus: { key: 'search-input', selection: [0, 0] } });
      },
    }),
  ]);
}

function render(renderOptions = {}) {
  const focus = renderOptions.focus ?? captureFocus();
  const t = translations[state.language];
  const visibleEffects = state.loadStatus === 'ready' ? getVisibleEffects(state) : [];
  const totalEffects = state.library?.effects.length ?? 0;
  document.documentElement.lang = state.language;
  document.documentElement.dataset.theme = view.theme;
  const isLight = view.theme === 'light'
    || (view.theme === 'system' && matchMedia('(prefers-color-scheme: light)').matches);
  themeColor.setAttribute('content', isLight ? '#eeeee9' : '#0a0a0b');
  document.title = t.pageTitle;

  const mainChildren = [makeIntro(t), makeInstall(t)];
  if (state.loadStatus === 'ready') {
    mainChildren.push(makeFilters(t, visibleEffects.length, totalEffects));
    mainChildren.push(
      visibleEffects.length
        ? node('section', { className: 'effect-list', attrs: { 'aria-label': t.archiveLabel } },
            visibleEffects.map((effect) => makeEffectCard(effect, t)))
        : makeEmptyState(t),
    );
    mainChildren.push(makeSelectionBar(t));
  } else {
    mainChildren.push(makeLoadState(t));
  }

  app.replaceChildren(
    node('a', { className: 'skip-link', text: t.skipToContent, attrs: { href: '#main-content' } }),
    node('div', { className: 'site-shell' }, [
      makeHeader(t),
      node('main', { attrs: { id: 'main-content', tabindex: '-1' } }, mainChildren),
      node('footer', { className: 'site-footer' }, [
        node('span', { className: 'footer-rule', attrs: { 'aria-hidden': 'true' } }),
        node('p', { text: t.footer }),
      ]),
    ]),
  );

  restoreFocus(focus);
}

async function loadLibrary(isRetry = false) {
  setState(isRetry ? retryLoad(state) : startLoading(state));
  const attempt = state.loadAttempt;
  try {
    const response = await fetch('./api/library.json', { headers: { accept: 'application/json' } });
    if (!response.ok) throw new Error(`Library request failed with ${response.status}`);
    const rawLibrary = await response.json();
    assertLibrary(rawLibrary);
    if (state.loadAttempt === attempt) {
      const nextState = validCategory(loadSucceeded(state, rawLibrary));
      syncLocationFilters(nextState);
      setState(nextState);
    }
  } catch (error) {
    if (state.loadAttempt === attempt) setState(loadFailed(state, error));
  }
}

addEventListener('popstate', () => {
  if (searchFrame) cancelAnimationFrame(searchFrame);
  searchFrame = 0;
  setState(validCategory({ ...state, ...readLocationFilters() }));
});
render();
loadLibrary();
