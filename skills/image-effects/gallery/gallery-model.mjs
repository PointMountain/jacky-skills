const SUPPORTED_SCHEMA_VERSION = 1;
const DEFAULT_LOAD_ERROR = 'Unable to load the effect library.';

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function libraryError(message) {
  return new Error(`Invalid effect library: ${message}`);
}

function assertLocalizedField(effect, field, index) {
  const localized = effect[field];
  if (!isRecord(localized) || !isNonEmptyString(localized.en)) {
    throw libraryError(`effect at index ${index} must have a non-empty ${field}.en.`);
  }
  if ('zh' in localized && !isNonEmptyString(localized.zh)) {
    throw libraryError(`effect at index ${index} has an invalid ${field}.zh.`);
  }
}

function normalizeLanguage(language) {
  return language === 'zh' ? 'zh' : 'en';
}

function normalizeQuery(query) {
  return typeof query === 'string' ? query.trim() : '';
}

function normalizeCategory(category) {
  return isNonEmptyString(category) ? category.trim() : 'all';
}

function immutableRefs(refs) {
  if (!Array.isArray(refs)) return Object.freeze([]);
  const normalized = refs.filter(isNonEmptyString).map((ref) => ref.trim());
  return Object.freeze([...new Set(normalized)]);
}

function effectsOf(state) {
  return state?.library?.effects ?? [];
}

export function assertLibrary(library) {
  if (!isRecord(library)) throw libraryError('expected an object.');
  if (library.schemaVersion !== SUPPORTED_SCHEMA_VERSION) {
    throw libraryError(`unsupported schema version ${String(library.schemaVersion)}.`);
  }
  if (!Array.isArray(library.effects)) {
    throw libraryError('effects must be an array.');
  }

  const seenRefs = new Set();
  library.effects.forEach((effect, index) => {
    if (!isRecord(effect)) throw libraryError(`effect at index ${index} must be an object.`);

    for (const field of ['ref', 'id', 'version', 'category', 'invocation']) {
      if (!isNonEmptyString(effect[field])) {
        throw libraryError(`effect at index ${index} must have a non-empty ${field}.`);
      }
    }
    assertLocalizedField(effect, 'title', index);
    assertLocalizedField(effect, 'summary', index);

    const expectedRef = `${effect.id}@${effect.version}`;
    if (effect.ref !== expectedRef) {
      throw libraryError(`effect at index ${index} ref must equal ${expectedRef}.`);
    }
    if (!effect.invocation.includes(effect.ref)) {
      throw libraryError(`effect at index ${index} invocation must include its versioned ref.`);
    }
    if (seenRefs.has(effect.ref)) {
      throw libraryError(`duplicate effect ref ${effect.ref}.`);
    }
    seenRefs.add(effect.ref);
  });

  return library;
}

export function createGalleryState(preferences = {}) {
  const source = isRecord(preferences) ? preferences : {};
  return {
    library: null,
    language: normalizeLanguage(source.language),
    query: normalizeQuery(source.query),
    category: normalizeCategory(source.category),
    selectedRefs: immutableRefs(source.selectedRefs),
    loadStatus: 'idle',
    loadError: null,
    loadAttempt: 0,
  };
}

export function startLoading(state) {
  return {
    ...state,
    selectedRefs: immutableRefs(state.selectedRefs),
    loadStatus: 'loading',
    loadError: null,
    loadAttempt: (Number.isInteger(state.loadAttempt) ? state.loadAttempt : 0) + 1,
  };
}

export function loadSucceeded(state, library) {
  assertLibrary(library);
  return {
    ...state,
    library,
    selectedRefs: immutableRefs(state.selectedRefs),
    loadStatus: 'ready',
    loadError: null,
  };
}

export function loadFailed(state, error) {
  const message =
    error instanceof Error
      ? normalizeQuery(error.message) || DEFAULT_LOAD_ERROR
      : normalizeQuery(error) || DEFAULT_LOAD_ERROR;
  return {
    ...state,
    selectedRefs: immutableRefs(state.selectedRefs),
    loadStatus: 'error',
    loadError: message,
  };
}

export function retryLoad(state) {
  return startLoading(state);
}

export function localizeEffect(effect, language) {
  const selectedLanguage = normalizeLanguage(language);
  return {
    ...effect,
    title: effect.title[selectedLanguage] || effect.title.en,
    summary: effect.summary[selectedLanguage] || effect.summary.en,
  };
}

export function getVisibleEffects(state) {
  const query = normalizeQuery(state.query).toLocaleLowerCase();
  const category = normalizeCategory(state.category);
  const language = normalizeLanguage(state.language);

  return effectsOf(state)
    .filter((effect) => category === 'all' || effect.category === category)
    .filter((effect) => {
      if (!query) return true;
      const localized = localizeEffect(effect, language);
      return [effect.id, effect.ref, localized.title, localized.summary].some((value) =>
        value.toLocaleLowerCase().includes(query),
      );
    })
    .map((effect) => localizeEffect(effect, language));
}

export function toggleSelection(state, ref) {
  if (!effectsOf(state).some((effect) => effect.ref === ref)) return state;

  const selected = new Set(state.selectedRefs);
  if (selected.has(ref)) selected.delete(ref);
  else selected.add(ref);
  return { ...state, selectedRefs: immutableRefs([...selected]) };
}

export function clearSelection(state) {
  return { ...state, selectedRefs: immutableRefs([]) };
}

export function getSelectedInvocations(state) {
  const selected = new Set(state.selectedRefs);
  return effectsOf(state)
    .filter((effect) => selected.has(effect.ref))
    .map((effect) => effect.invocation);
}
