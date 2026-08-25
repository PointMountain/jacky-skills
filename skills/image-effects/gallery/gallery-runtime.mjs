export function readLocationFilters(search = location.search) {
  const params = new URLSearchParams(search);
  return { query: params.get('q') ?? '', category: params.get('category') ?? 'all' };
}

export function syncLocationFilters(nextState, windowObject = window) {
  const url = new URL(windowObject.location.href);
  if (nextState.query) url.searchParams.set('q', nextState.query);
  else url.searchParams.delete('q');
  if (nextState.category !== 'all') url.searchParams.set('category', nextState.category);
  else url.searchParams.delete('category');
  windowObject.history.replaceState(windowObject.history.state, '', url);
}

export function captureFocus(documentObject = document) {
  const element = documentObject.activeElement;
  const HTMLElementClass = documentObject.defaultView?.HTMLElement;
  if (!HTMLElementClass || !(element instanceof HTMLElementClass) || !element.dataset.focusKey) {
    return null;
  }
  const selection = element.dataset.testid === 'search-input'
    ? [element.selectionStart, element.selectionEnd]
    : null;
  return { key: element.dataset.focusKey, selection };
}

export function restoreFocus(identity, documentObject = document) {
  if (!identity) return;
  const target = documentObject.querySelector(`[data-focus-key="${identity.key}"]`)
    ?? documentObject.querySelector('#main-content');
  const HTMLElementClass = documentObject.defaultView?.HTMLElement;
  if (!HTMLElementClass || !(target instanceof HTMLElementClass)) return;
  target.focus({ preventScroll: true });
  if (target.dataset.testid === 'search-input' && identity.selection) {
    target.setSelectionRange(...identity.selection);
  }
}

export async function copyText(text, documentObject = document, navigatorObject = navigator) {
  const HTMLElementClass = documentObject.defaultView?.HTMLElement;
  const activeElement = documentObject.activeElement;
  const trigger = HTMLElementClass && activeElement instanceof HTMLElementClass ? activeElement : null;
  if (navigatorObject.clipboard?.writeText) {
    try {
      await navigatorObject.clipboard.writeText(text);
      return;
    } catch {
      // 原生剪贴板被拒绝时继续使用同页回退路径。
    }
  }

  const field = documentObject.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.className = 'clipboard-fallback';
  let copied = false;
  try {
    documentObject.body.append(field);
    field.select();
    copied = documentObject.execCommand('copy');
  } finally {
    field.remove();
    trigger?.focus({ preventScroll: true });
  }
  if (!copied) throw new Error('Copy failed');
}

export function effectTitleId(ref) {
  return `effect-title-${[...ref].map((character) =>
    /[a-z0-9-]/i.test(character) ? character : `_${character.codePointAt(0).toString(16)}_`,
  ).join('')}`;
}
