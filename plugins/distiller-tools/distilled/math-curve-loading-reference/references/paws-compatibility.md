# Paws Compatibility Case Study

## Context

Paws replaced a generic first-paint spinner and loading copy with a theme-aware 36-particle Lissajous trail. The placeholder is injected into exported HTML so it appears before the React application bundle mounts.

Relevant implementation:

- `packages/happy-app/sources/scripts/injectWebLoading.ts`
- `packages/happy-app/sources/scripts/injectWebLoading.test.ts`
- PR #327: initial Lissajous loader
- PR #328: first SVG path compatibility fix
- PR #330: final RAF implementation

## Compatibility progression

### Attempt 1: `animateMotion` plus `mpath href`

Desktop validation looked correct, but the user's renderer resolved the referenced path incorrectly. Particles collapsed at the SVG origin and appeared as a detached dot.

Lesson: SVG reference indirection is not a safe first-paint dependency across all embedded renderers.

### Attempt 2: inline `animateMotion path`

Removing `mpath` avoided one reference edge, but the user still saw abnormal output. This isolated the remaining risk to SVG SMIL support itself.

Lesson: changing SMIL syntax does not remove the underlying runtime compatibility dependency.

### Final: static circles plus RAF

The final implementation:

- emits 36 circles with distinct static `cx/cy` values in HTML;
- samples an SVG path with `getPointAtLength()` inside one `requestAnimationFrame` loop;
- updates each circle's position with a phase offset;
- stops scheduling frames once React adds children to `#root`;
- avoids starting RAF under `prefers-reduced-motion`;
- keeps the static trail visible if RAF or SVG length APIs fail.

This removes `animateMotion`, `mpath`, `use`, and `href` indirection from the critical loading path.

## Recommended implementation contract

1. Generate the curve and all static particle positions at build time.
2. Include one inline bootstrap before the application bundle executes.
3. Read persisted theme preference defensively; fall back to system light/dark.
4. Query the root, path, and exact expected particle count before animating.
5. Guard `requestAnimationFrame`, `getTotalLength()`, and `getPointAtLength()`.
6. Stop when the application root becomes non-empty.
7. Hide the placeholder with a structural CSS selector after application mount.
8. Keep injection idempotent and fail loudly if the root anchor is absent.

## Test contract

Static tests should assert:

- exact particle count;
- unique static positions;
- no `animateMotion`, `mpath`, `use`, or loader `href` references;
- one bootstrap script;
- theme mappings and fallback behavior;
- reduced-motion CSS and behavior;
- idempotent injection and missing-anchor failure.

Execute the inline bootstrap in a DOM test with mocked path APIs and RAF. Assert that every particle moves and that no new frame is scheduled after the root mounts.

Browser validation should block the hashed main application bundle and assert:

- `#root` has no children;
- all particles exist and have unique positions;
- the leading coordinate changes after 500-700 ms;
- particles remain near the orbit;
- no service worker masks network blocking.

Then remove the block and assert:

- the application mounts;
- the loader becomes hidden;
- console and page errors are empty;
- runtime build SHA matches the deployed revision.

## Deployment lesson

For a content-hashed Web export, upload assets before switching the HTML entry. Fetch every new JS/CSS entry reference through the production origin and byte-compare it with the local export. Replace `index.html` only after all referenced resources are available, and retain a rollback directory.
