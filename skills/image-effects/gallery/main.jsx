import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

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
} from './gallery-model.mjs';
import { copyText, effectTitleId, readLocationFilters, syncLocationFilters } from './gallery-runtime.mjs';
import { translations } from './translations.js';
import { BlurText } from './react-bits/BlurText.jsx';
import { ClickSpark } from './react-bits/ClickSpark.jsx';
import { Magnet } from './react-bits/Magnet.jsx';
import { SpotlightCard } from './react-bits/SpotlightCard.jsx';
import './styles.css';

const INSTALL_COMMAND = 'npx skills add wangjs-jacky/image-effects';
const THEME_ORDER = Object.freeze(['system', 'dark', 'light']);

function readPreference(key, allowed, fallback) {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

function persist(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The current view still works when storage is unavailable.
  }
}

function withTokens(template, values = {}) {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

function useSystemReducedMotion() {
  const [reduced, setReduced] = useState(
    () => matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  useEffect(() => {
    const query = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  return reduced;
}

function categoryLabel(category, t) {
  return t.categories[category] ?? category;
}

function Fact({ label, value }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function Header({ language, motionEnabled, onLanguage, onMotion, onTheme, theme, t }) {
  const currentTheme = t[`theme${theme[0].toUpperCase()}${theme.slice(1)}`];
  return (
    <header className="site-header">
      <div className="brand-lockup">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">{t.brand}</span>
        <span className="edition">{t.edition}</span>
      </div>
      <nav className="utilities" aria-label={t.archiveLabel}>
        <button
          className="utility-button language-button"
          type="button"
          aria-label={t.languageLabel}
          data-testid="language-toggle"
          onClick={onLanguage}
        >
          {language === 'en' ? '中文' : 'EN'}
        </button>
        <button
          className="utility-button motion-button"
          type="button"
          aria-label={t.motionLabel}
          aria-pressed={motionEnabled}
          onClick={onMotion}
        >
          {withTokens(t.motionValue, { motion: motionEnabled ? t.motionOn : t.motionOff })}
        </button>
        <button
          className="utility-button theme-button"
          type="button"
          aria-label={t.themeLabel}
          data-testid="theme-toggle"
          onClick={onTheme}
        >
          {withTokens(t.themeValue, { theme: currentTheme })}
        </button>
      </nav>
    </header>
  );
}

function Intro({ library, motionActive, language, t }) {
  const count = library?.effects.length ?? 0;
  const stats = library
    ? [
        withTokens(count === 1 ? t.effectCount : t.effectCountPlural, { count }),
        withTokens(t.schemaLabel, { version: library.schemaVersion }),
        withTokens(t.updatedLabel, {
          date: new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(
            new Date(library.generatedAt),
          ),
        }),
      ]
    : [];
  return (
    <section className="intro" aria-labelledby="page-title">
      <div className="intro-copy">
        <p className="eyebrow">{t.heroEyebrow}</p>
        <BlurText
          as="h1"
          className="hero-title"
          disabled={!motionActive}
          text={t.heroTitle}
        />
        <p className="intro-body">{t.heroBody}</p>
      </div>
      <aside className="archive-status" aria-label={t.archiveLabel}>
        <p className="micro-label">{t.archiveLabel}</p>
        {stats.map((value, index) => (
          <p className={index === 0 ? 'status-primary' : 'status-line'} key={value}>
            {value}
          </p>
        ))}
      </aside>
    </section>
  );
}

function InstallStrip({ motionActive, onCopy, t }) {
  return (
    <section className="install-strip" aria-label={t.installLabel}>
      <div className="install-copy">
        <span className="micro-label">{t.installLabel}</span>
        <code data-testid="install-command">{INSTALL_COMMAND}</code>
      </div>
      <Magnet disabled={!motionActive}>
        <ClickSpark disabled={!motionActive}>
          <button className="copy-button" type="button" data-action="copy-install" onClick={onCopy}>
            {t.copyInstall}
          </button>
        </ClickSpark>
      </Magnet>
    </section>
  );
}

function Filters({ categories, category, onCategory, onQuery, query, total, visible, t }) {
  return (
    <section className="filters" aria-label={t.searchLabel}>
      <div className="field search-field">
        <label htmlFor="effect-search">{t.searchLabel}</label>
        <input
          className="search-input"
          id="effect-search"
          type="search"
          value={query}
          placeholder={t.searchPlaceholder}
          autoComplete="off"
          data-testid="search-input"
          onChange={(event) => onQuery(event.currentTarget.value)}
        />
      </div>
      <div className="field category-field">
        <label htmlFor="category-filter">{t.categoryLabel}</label>
        <select
          className="category-filter"
          id="category-filter"
          value={category}
          data-testid="category-filter"
          onChange={(event) => onCategory(event.currentTarget.value)}
        >
          <option value="all">{t.categoryAll}</option>
          {categories.map((value) => (
            <option value={value} key={value}>{categoryLabel(value, t)}</option>
          ))}
        </select>
      </div>
      <p className="result-count" aria-live="polite">
        {withTokens(t.resultsLabel, { visible, total })}
      </p>
    </section>
  );
}

function EffectCard({ effect, index, motionActive, onToggle, selected, t }) {
  const titleId = effectTitleId(effect.ref);
  const inputValue = withTokens(
    effect.input.mode === 'text-or-image'
      ? t.textOrImageInput
      : effect.input.min === effect.input.max && effect.input.min === 1
        ? t.imageInput
        : t.imageInputPlural,
    { min: effect.input.min, max: effect.input.max, formats: effect.input.formats.join(' / ') },
  );
  const outputKey = effect.outputCount === 1 ? 'outputCount' : 'outputCountPlural';

  return (
    <SpotlightCard
      as="article"
      className={`effect-card ${selected ? 'is-selected' : ''}`}
      disabled={!motionActive}
      aria-labelledby={titleId}
      data-testid="effect-card"
      style={{ '--card-index': Math.min(index, 10) }}
    >
      <figure className="preview-frame">
        <img
          src={effect.previewUrl}
          alt={withTokens(t.imageAlt, { title: effect.title })}
          loading="lazy"
          decoding="async"
          width={effect.previewWidth}
          height={effect.previewHeight}
        />
        <figcaption className="preview-caption">
          <span>{withTokens(t.previewCreditValue, {
            author: effect.provenance.preview.author,
            license: effect.provenance.preview.licenseSpdx,
          })}</span>
        </figcaption>
      </figure>
      <div className="effect-content">
        <div className="effect-topline">
          <span className="category-chip">{categoryLabel(effect.category, t)}</span>
          <label className="selection-control">
            <input
              className="effect-checkbox"
              type="checkbox"
              checked={selected}
              aria-label={withTokens(t.selectEffect, { title: effect.title })}
              data-testid="effect-select"
              onChange={() => onToggle(effect.ref)}
            />
            <span>{selected ? t.selected : t.notSelected}</span>
          </label>
        </div>
        <div className="effect-heading">
          <p className="version-ref">{effect.ref}</p>
          <h2 id={titleId}>{effect.title}</h2>
          <p className="effect-summary">{effect.summary}</p>
        </div>
        <dl className="facts card-facts">
          <Fact label={t.input} value={inputValue} />
          <Fact label={t.output} value={withTokens(t[outputKey], { count: effect.outputCount })} />
        </dl>
        <details className="card-details">
          <summary>{t.cardDetails}</summary>
          <div className="card-details-content">
            <div className="invocation">
              <span className="micro-label">{t.recipeLabel}</span>
              <code>{effect.invocation}</code>
            </div>
            <div className="source-block">
              <p className="micro-label">{t.provenanceLabel}</p>
              <dl className="provenance-list">
                <Fact label={t.repository} value={effect.provenance.repository} />
                <Fact label={t.revision} value={effect.provenance.revision} />
                <Fact label={t.previewCredit} value={withTokens(t.previewCreditValue, {
                  author: effect.provenance.preview.author,
                  license: effect.provenance.preview.licenseSpdx,
                })} />
              </dl>
              <p className="preview-origin">{effect.provenance.preview.origin}</p>
              <div className="source-actions">
                <a className="text-link" href={effect.sourceUrl} target="_blank" rel="noopener noreferrer" data-testid="source-link">
                  {t.source}
                </a>
                <a className="text-link" href={effect.provenance.license.url} target="_blank" rel="noopener noreferrer" data-testid="source-license">
                  {withTokens(t.license, { spdx: effect.provenance.license.spdx })}
                </a>
              </div>
            </div>
          </div>
        </details>
      </div>
    </SpotlightCard>
  );
}

function SelectionBar({ motionActive, onClear, onCopy, selectedEffects, t }) {
  const names = selectedEffects.map((effect) => effect.title).join(', ');
  const count = selectedEffects.length;
  return (
    <section className={`selection-bar ${count ? 'has-selection' : ''}`} aria-label={count ? withTokens(t.selectionCount, { count }) : t.selectionNone}>
      <div className="selection-summary">
        <strong>{count ? withTokens(t.selectionCount, { count }) : t.selectionNone}</strong>
        <span>{count ? withTokens(t.selectionNames, { names }) : ''}</span>
      </div>
      <div className="selection-actions">
        <button className="secondary-button" type="button" disabled={!count} onClick={onClear}>
          {t.clearSelection}
        </button>
        <Magnet disabled={!motionActive || !count}>
          <ClickSpark disabled={!motionActive || !count}>
            <button className="primary-button" type="button" disabled={!count} data-testid="copy-selected" onClick={onCopy}>
              {t.copySelected}
            </button>
          </ClickSpark>
        </Magnet>
      </div>
    </section>
  );
}

function StatePanel({ kind, onAction, t }) {
  if (kind === 'error') {
    return (
      <section className="state-panel error-panel" role="alert" data-testid="load-error">
        <p className="eyebrow">{t.loadErrorCode}</p>
        <h2>{t.loadErrorTitle}</h2>
        <button className="primary-button" type="button" onClick={onAction}>{t.retry}</button>
      </section>
    );
  }
  if (kind === 'empty') {
    return (
      <section className="state-panel empty-panel">
        <p className="eyebrow">{t.emptyCode}</p>
        <h2>{t.emptyTitle}</h2>
        <p>{t.emptyBody}</p>
        <button className="primary-button" type="button" onClick={onAction}>{t.resetFilters}</button>
      </section>
    );
  }
  return (
    <section className="state-panel loading-panel" aria-live="polite">
      <span className="loading-line" aria-hidden="true" />
      <p>{t.loading}</p>
    </section>
  );
}

function App() {
  const [language, setLanguage] = useState(
    () => readPreference('image-effects-language', ['en', 'zh'], 'en'),
  );
  const [theme, setTheme] = useState(
    () => readPreference('image-effects-theme', THEME_ORDER, 'dark'),
  );
  const [motionEnabled, setMotionEnabled] = useState(
    () => readPreference('image-effects-motion', ['on', 'off'], 'on') === 'on',
  );
  const [galleryState, setGalleryState] = useState(() =>
    createGalleryState({ language, ...readLocationFilters() }),
  );
  const [announcement, setAnnouncement] = useState('');
  const loadSequence = useRef(0);
  const systemReducedMotion = useSystemReducedMotion();
  const motionActive = motionEnabled && !systemReducedMotion;
  const t = translations[language];

  const visibleEffects = useMemo(
    () => galleryState.loadStatus === 'ready' ? getVisibleEffects(galleryState) : [],
    [galleryState],
  );
  const categories = useMemo(
    () => [...new Set((galleryState.library?.effects ?? []).map((effect) => effect.category))].sort(),
    [galleryState.library],
  );
  const selectedEffects = useMemo(
    () => (galleryState.library?.effects ?? [])
      .filter((effect) => galleryState.selectedRefs.includes(effect.ref))
      .map((effect) => localizeEffect(effect, language)),
    [galleryState.library, galleryState.selectedRefs, language],
  );

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.motion = motionActive ? 'on' : 'off';
    document.title = t.pageTitle;
    const light = theme === 'light'
      || (theme === 'system' && matchMedia('(prefers-color-scheme: light)').matches);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', light ? '#eeeee9' : '#0a0a0b');
  }, [language, motionActive, t.pageTitle, theme]);

  useEffect(() => {
    const handlePopState = () => {
      const filters = readLocationFilters();
      setGalleryState((current) => ({ ...current, ...filters }));
    };
    addEventListener('popstate', handlePopState);
    return () => removeEventListener('popstate', handlePopState);
  }, []);

  const loadLibrary = useCallback(async (retry = false) => {
    const sequence = ++loadSequence.current;
    setGalleryState((current) => retry ? retryLoad(current) : startLoading(current));
    try {
      const response = await fetch('./api/library.json', { headers: { accept: 'application/json' } });
      if (!response.ok) throw new Error(`Library request failed with ${response.status}`);
      const library = await response.json();
      assertLibrary(library);
      if (loadSequence.current !== sequence) return;
      setGalleryState((current) => {
        const loaded = loadSucceeded(current, library);
        const validCategory = loaded.category === 'all'
          || loaded.library.effects.some((effect) => effect.category === loaded.category);
        const next = validCategory ? loaded : { ...loaded, category: 'all' };
        syncLocationFilters(next);
        return next;
      });
    } catch (error) {
      if (loadSequence.current === sequence) {
        setGalleryState((current) => loadFailed(current, error));
      }
    }
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  function announce(message) {
    setAnnouncement('');
    requestAnimationFrame(() => setAnnouncement(message));
  }

  async function copyWithFeedback(value, successMessage) {
    try {
      await copyText(value);
      announce(successMessage);
    } catch {
      announce(t.copyFailed);
    }
  }

  function updateFilter(field, value) {
    setGalleryState((current) => {
      const next = { ...current, [field]: value };
      syncLocationFilters(next);
      return next;
    });
  }

  function resetFilters() {
    setGalleryState((current) => {
      const next = { ...current, query: '', category: 'all' };
      syncLocationFilters(next);
      return next;
    });
  }

  function toggleTheme() {
    const next = THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length];
    persist('image-effects-theme', next);
    setTheme(next);
  }

  function toggleLanguage() {
    const next = language === 'en' ? 'zh' : 'en';
    persist('image-effects-language', next);
    setLanguage(next);
    setGalleryState((current) => ({ ...current, language: next }));
  }

  function toggleMotion() {
    const next = !motionEnabled;
    persist('image-effects-motion', next ? 'on' : 'off');
    setMotionEnabled(next);
  }

  return (
    <>
      <a className="skip-link" href="#main-content">{t.skipToContent}</a>
      <div className="site-shell">
        <Header
          language={language}
          motionEnabled={motionEnabled}
          onLanguage={toggleLanguage}
          onMotion={toggleMotion}
          onTheme={toggleTheme}
          theme={theme}
          t={t}
        />
        <main id="main-content" tabIndex="-1">
          <Intro library={galleryState.library} motionActive={motionActive} language={language} t={t} />
          <InstallStrip motionActive={motionActive} onCopy={() => copyWithFeedback(INSTALL_COMMAND, t.copiedInstall)} t={t} />
          {galleryState.loadStatus === 'ready' ? (
            <>
              <Filters
                categories={categories}
                category={galleryState.category}
                onCategory={(value) => updateFilter('category', value)}
                onQuery={(value) => updateFilter('query', value)}
                query={galleryState.query}
                total={galleryState.library.effects.length}
                visible={visibleEffects.length}
                t={t}
              />
              {visibleEffects.length ? (
                <section className="effect-list" aria-label={t.archiveLabel}>
                  {visibleEffects.map((effect, index) => (
                    <EffectCard
                      effect={effect}
                      index={index}
                      key={effect.ref}
                      motionActive={motionActive}
                      onToggle={(ref) => setGalleryState((current) => toggleSelection(current, ref))}
                      selected={galleryState.selectedRefs.includes(effect.ref)}
                      t={t}
                    />
                  ))}
                </section>
              ) : <StatePanel kind="empty" onAction={resetFilters} t={t} />}
              <SelectionBar
                motionActive={motionActive}
                onClear={() => setGalleryState((current) => clearSelection(current))}
                onCopy={() => copyWithFeedback(getSelectedInvocations(galleryState).join('\n'), t.copiedSelected)}
                selectedEffects={selectedEffects}
                t={t}
              />
            </>
          ) : (
            <StatePanel
              kind={galleryState.loadStatus === 'error' ? 'error' : 'loading'}
              onAction={() => loadLibrary(true)}
              t={t}
            />
          )}
        </main>
        <footer className="site-footer">
          <span className="footer-rule" aria-hidden="true" />
          <p>{t.footer}</p>
        </footer>
      </div>
      <p className="sr-only" aria-live="polite">{announcement}</p>
    </>
  );
}

createRoot(document.querySelector('#app')).render(<App />);
