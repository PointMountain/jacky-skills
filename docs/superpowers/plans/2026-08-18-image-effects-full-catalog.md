# Image Effects Full Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the install-once `image-effects` Skill and public Gallery from one effect to the approved eight-effect catalog, with seven original previews, complete license provenance, executable host contracts, and a verified public Pages release.

**Architecture:** Markdown effect cards remain the behavior and provenance source of truth. Strict Node ESM parsers validate cards and license notices, a deterministic builder emits schema-2 Gallery artifacts with decoded preview dimensions, and the existing Git-tree exporter publishes only committed source outputs. Host image generation remains runtime-native; Editorial Echo adds an explicit capability-gated HTML/CSS layout stage without depending on another Skill.

**Tech Stack:** Markdown Agent Skill, Node.js ESM, `node:test`, `sharp@0.35.3`, native HTML/CSS/JavaScript, host-native image generation, browser screenshot composition, Git, GitHub CLI, GitHub Actions Pages.

**Spec:** `docs/superpowers/specs/2026-08-18-image-effects-full-catalog-design.md`

## Global Constraints

- The final refs are exactly: `healing-anime-scribble-v3@1.0.0`, `photo-illustration-editorial-echo@1.0.0`, `photo-illustration-diptych-lakeside@1.0.0`, `photo-illustration-diptych@1.0.0`, `scenes-gathered-zine-sea@1.0.0`, `scenes-gathered-zine@1.0.0`, `scene-distillation-zine@1.0.0`, and `minimal-zine-poster@1.0.0`.
- `grade-images` is excluded; no color-grading recipe, batch-processing, report, remote catalog, OSS/CDN, Happy App, OTA, or plugin-loader work is allowed.
- Six single-stage effects and Editorial Echo require exactly one current-request JPEG/PNG; Minimal Zine accepts either non-empty text with zero images or one current-request JPEG/PNG.
- Runtime execution must not require another Skill. Missing host image or layout capabilities cause the documented honest fallback.
- Public Library schema is `2`; every effect includes `executionKind`, `previewWidth`, and `previewHeight`.
- Source licenses are MIT; generated previews are authored by `wangjs-jacky` and published under CC-BY-4.0.
- Every preview is independently created from a fictional subject; do not use user attachments, historical Gallery images, real-person photos, brands, copyrighted characters, or third-party images.
- All behavior changes follow RED → verify failure → GREEN → verify pass. Generated preview assets get a missing-file/hash RED test before generation.
- Development stays in `/Users/jacky/jacky-github/jacky-skills--image-effects-full-catalog`; do not modify the dirty `/Users/jacky/jacky-github/jacky-skills` root worktree.
- Publish only after the source PR is merged. Export the public repository from the clean merged `jacky-skills/main` Git tree, never from this feature branch.

## File Structure and Responsibilities

- `skills/image-effects/SKILL.md`: effect resolution, input-mode validation, capability routing, fallback, privacy, and delivery protocol.
- `skills/image-effects/references/effects/*.md`: eight complete versioned effect compilers and provenance records.
- `skills/image-effects/references/licenses/*.txt`: four fixed upstream MIT notices whose bytes are covered by source SHA mappings.
- `skills/image-effects/assets/previews/*`: eight metadata-free licensed previews.
- `skills/image-effects/scripts/effect-library.mjs`: strict frontmatter parser, contract combinations, schema-2 model, invocations, and Notice rendering.
- `skills/image-effects/scripts/build-gallery.mjs`: preview decoding, dimension projection, license loading, deterministic artifacts, and atomic installation.
- `skills/image-effects/scripts/validate-effects.mjs`: fixed-revision source and license byte verification.
- `skills/image-effects/gallery/gallery-model.mjs`: schema-2 runtime validation and canonicalization.
- `skills/image-effects/gallery/app.js`: render intrinsic image dimensions and text-or-image input copy.
- `skills/image-effects/gallery/translations.js`: `portrait`, `editorial`, and `zine` labels plus text-or-image wording.
- `skills/image-effects/assets/public-repo/{README.md,README_CN.md}`: eight-effect installation, invocation, capability, privacy, and license documentation.
- `skills/image-effects/tests/*.test.mjs`: parser, asset, build, runtime, HTTP, exporter, and catalog regression coverage.

---

### Task 1: Extend the effect-card and Library schema

**Files:**
- Modify: `skills/image-effects/tests/effect-library.test.mjs`
- Modify: `skills/image-effects/scripts/effect-library.mjs`
- Modify: `skills/image-effects/references/effects/healing-anime-scribble-v3.md`
- Create: `skills/image-effects/references/licenses/conardli-garden-skills-mit.txt`

**Interfaces:**
- Consumes: existing `parseEffect(markdown, filePath)`, `buildLibrary(effects, generatedAt)`, and strict simple-scalar frontmatter.
- Produces: `buildLibrary(effects, generatedAt, previewMetadataByRef)`, schema-2 effects, `executionKind`, decoded dimensions, conditional invocations, and parsed `sourceLicenseNotice`.

- [ ] **Step 1: Add failing parser tests for the approved contract combinations**

Extend the valid-card helper with `source_license_notice: references/licenses/example-mit.txt`. Add table-driven tests with these exact accepted combinations:

```js
const accepted = [
  { category: 'portrait', execution_kind: 'host-image-generation', input_mode: 'image', input_min: '1', input_max: '1' },
  { category: 'editorial', execution_kind: 'host-image-generation', input_mode: 'image', input_min: '1', input_max: '1' },
  { category: 'zine', execution_kind: 'host-image-generation', input_mode: 'image', input_min: '1', input_max: '1' },
  { category: 'editorial', execution_kind: 'host-image-generation-and-layout', input_mode: 'image', input_min: '1', input_max: '1' },
  { category: 'zine', execution_kind: 'host-image-generation', input_mode: 'text-or-image', input_min: '0', input_max: '1' },
];
```

Reject `grade`, `local-script`, `image-required`, `text`, image `0..1`, text-or-image `1..1`, and any `source_license_notice` outside `references/licenses/`.

- [ ] **Step 2: Add failing schema-2 projection tests**

Change the expected Library to `schemaVersion: 2`, pass:

```js
const previewMetadataByRef = new Map([
  ['healing-anime-scribble-v3@1.0.0', { width: 1448, height: 1086 }],
]);
```

and assert the public effect contains:

```js
executionKind: 'host-image-generation',
previewWidth: 1448,
previewHeight: 1086,
invocation: 'Use $image-effects effect healing-anime-scribble-v3@1.0.0 on my uploaded image.',
```

Add a Minimal Zine fixture and assert its invocation is exactly:

```text
Use $image-effects effect minimal-zine-poster@1.0.0 with this idea or my uploaded image.
```

Reject missing metadata, zero, negative, fractional, or values above `20000`.
Update every direct `buildLibrary` test call to pass a metadata map containing one decoded-dimension entry per fixture ref; do not add an optional default that could emit incomplete schema-2 data.

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
node --test skills/image-effects/tests/effect-library.test.mjs
```

Expected: FAIL because the parser still accepts only `portrait`/image and `buildLibrary` still emits schema 1 without execution or dimensions.

- [ ] **Step 4: Implement the minimal strict contract matrix**

Add `source_license_notice` to required fields. Parse positive integers without coercion and validate with explicit sets:

```js
const CATEGORIES = new Set(['portrait', 'editorial', 'zine']);
const EXECUTION_KINDS = new Set([
  'host-image-generation',
  'host-image-generation-and-layout',
]);
const INPUT_CONTRACTS = new Map([
  ['image', { min: 1, max: 1 }],
  ['text-or-image', { min: 0, max: 1 }],
]);
```

Require `host-image-generation-and-layout` to pair with `category: editorial` and `input_mode: image`. Return `sourceLicenseNotice` on the internal effect model.

- [ ] **Step 5: Bring the existing Healing card into the new license contract**

Copy the exact ConardLi MIT notice from `ConardLi/garden-skills@aaf9a82f5efd73e87cc0998edc398e75bfc35901` to `references/licenses/conardli-garden-skills-mit.txt`. Its SHA-256 must be `1126322e2cc8d165adc4c792eeb195717de2bcc7b39be1ce77959d78e87ef685`. Add `LICENSE` plus that hash to Healing’s source mapping and set:

```yaml
source_license_notice: references/licenses/conardli-garden-skills-mit.txt
```

- [ ] **Step 6: Implement schema-2 projection**

Change the signature to:

```js
export function buildLibrary(effects, generatedAt, previewMetadataByRef)
```

Require a `{ width, height }` entry for every ref, emit schema 2, `executionKind`, `previewWidth`, and `previewHeight`, and select the invocation from `effect.input.mode`. Do not mutate `effects` or the metadata map.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run:

```bash
node --test skills/image-effects/tests/effect-library.test.mjs
```

Expected: PASS with zero failed tests and no warnings.

- [ ] **Step 8: Commit the schema contract**

```bash
git add skills/image-effects/scripts/effect-library.mjs skills/image-effects/tests/effect-library.test.mjs skills/image-effects/references
git commit -m "feat: extend image effects catalog schema"
```

### Task 2: Upgrade Gallery runtime validation and rendering

**Files:**
- Modify: `skills/image-effects/tests/gallery-model.test.mjs`
- Modify: `skills/image-effects/tests/gallery-assets.test.mjs`
- Modify: `skills/image-effects/gallery/gallery-model.mjs`
- Modify: `skills/image-effects/gallery/app.js`
- Modify: `skills/image-effects/gallery/translations.js`

**Interfaces:**
- Consumes: schema-2 effects from Task 1.
- Produces: `assertLibrary(library)` accepting only schema 2, immutable canonical effects with execution/dimensions, correct intrinsic image sizing, category translations, and text-or-image input copy.

- [ ] **Step 1: Change Gallery fixtures and add failing schema tests**

Set fixture `schemaVersion` to `2` and add these effect fields:

```js
executionKind: 'host-image-generation',
previewWidth: 1024,
previewHeight: 1536,
```

Require all three fields as own properties. Reject schema 1, unknown execution kinds, dimensions outside `1..20000`, and `text-or-image` contracts other than `0..1` JPEG/PNG.

- [ ] **Step 2: Add failing rendering-source assertions**

In `gallery-assets.test.mjs`, assert:

```js
assert.deepEqual(translations.en.categories, {
  portrait: 'Portrait',
  editorial: 'Editorial',
  zine: 'Zine',
});
assert.deepEqual(translations.zh.categories, {
  portrait: '人物',
  editorial: '编辑设计',
  zine: '纸本杂志',
});
```

Read `gallery/app.js` and assert it uses `effect.previewWidth`, `effect.previewHeight`, and a dedicated `textOrImageInput` translation rather than literal `1448`/`1086`.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
node --test skills/image-effects/tests/gallery-model.test.mjs skills/image-effects/tests/gallery-assets.test.mjs
```

Expected: FAIL on unsupported schema 2 and missing public fields/translations.

- [ ] **Step 4: Implement schema-2 validation and canonicalization**

Add `executionKind`, `previewWidth`, and `previewHeight` to `requireOwnFields`, validate execution against the two exact enum values, validate dimensions as integers `1..20000`, and retain them in both `canonicalizeEffect` and `localizeEffect`.

- [ ] **Step 5: Render real dimensions and input wording**

Replace fixed image attributes with:

```js
width: effect.previewWidth,
height: effect.previewHeight,
```

For `text-or-image`, render `t.textOrImageInput` with formats; for image input retain singular/plural behavior. Add the exact category objects from Step 2 and these strings:

```js
// en
textOrImageInput: 'Text or up to {max} image · {formats}',
// zh
textOrImageInput: '文字或最多 {max} 张图片 · {formats}',
```

Update hero copy from “One tested recipe” to “Eight tested recipes” in both languages.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
node --test skills/image-effects/tests/gallery-model.test.mjs skills/image-effects/tests/gallery-assets.test.mjs
```

Expected: PASS with zero failures.

- [ ] **Step 7: Commit Gallery schema support**

```bash
git add skills/image-effects/gallery skills/image-effects/tests/gallery-model.test.mjs skills/image-effects/tests/gallery-assets.test.mjs
git commit -m "feat: support full catalog in image gallery"
```

### Task 3: Vendor remaining licenses and define standalone runtime routing

**Files:**
- Create: `skills/image-effects/references/licenses/happy-coder-contributors-mit.txt`
- Create: `skills/image-effects/references/licenses/gathered-scenes-zine-contributors-mit.txt`
- Create: `skills/image-effects/references/licenses/liamgvchi-mit.txt`
- Modify: `skills/image-effects/SKILL.md`
- Modify: `skills/image-effects/tests/effect-assets.test.mjs`

**Interfaces:**
- Consumes: Task 1 `sourceLicenseNotice` contract and the approved execution matrix.
- Produces: four byte-fixed license files in total and a Skill router that needs no external Skill.

- [ ] **Step 1: Add failing license-byte tests**

Assert the complete license directory has exactly these SHA-256 values:

```js
const licenseHashes = {
  'conardli-garden-skills-mit.txt': '1126322e2cc8d165adc4c792eeb195717de2bcc7b39be1ce77959d78e87ef685',
  'happy-coder-contributors-mit.txt': 'e251d0448ef3ce023c20ebac9b90a7d8642b1434825838247d6e457668eb3e00',
  'gathered-scenes-zine-contributors-mit.txt': '7d063a2fe4a45ac0adf349ab8d568de5bc93206aaa3982a243dd8d067a3e2f4a',
  'liamgvchi-mit.txt': 'd15c81ae8fa9a0b4b1db46c66e4490cc92e4898fb1f55e030559fbd2a2e2a232',
};
```

- [ ] **Step 2: Run the asset test and verify RED**

```bash
node --test skills/image-effects/tests/effect-assets.test.mjs
```

Expected: FAIL because the Happy, Gathered Scenes, and LiamGvchi notices do not exist.

- [ ] **Step 3: Copy the remaining exact MIT notices**

Read Happy Coder Contributors from local `wangjs-jacky/happy@e8716a0a0c949f8e2b45e1e3d7c8d36ad7bba17c:LICENSE`; read Gathered Scenes and LiamGvchi with authenticated `gh api` at the revisions in the spec. Add the exact decoded text using `apply_patch`, then verify all four hashes with `shasum -a 256`.

- [ ] **Step 4: Rewrite Skill input and execution routing**

Keep exact ref resolution and privacy rules. Add explicit input branches for `image` and `text-or-image`; add execution branches for `host-image-generation` and `host-image-generation-and-layout`. For the layout branch, preflight image generation plus HTML/CSS screenshot capability before Stage A; when either is missing, return motif prompt, Copy Map, dimensions, composition plan, and missing-capability statement without producing a partial image.

- [ ] **Step 5: Run asset and official Skill validation**

```bash
node --test skills/image-effects/tests/effect-assets.test.mjs
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skills/image-effects
```

Expected: license hashes pass and official Skill validation exits 0.

- [ ] **Step 6: Commit licenses and routing**

```bash
git add skills/image-effects/SKILL.md skills/image-effects/references/licenses skills/image-effects/tests/effect-assets.test.mjs
git commit -m "feat: define standalone image effect routing"
```

### Task 4: Generate and sanitize seven independent previews

**Files:**
- Create: `skills/image-effects/assets/previews/photo-illustration-editorial-echo.png`
- Create: `skills/image-effects/assets/previews/photo-illustration-diptych-lakeside.png`
- Create: `skills/image-effects/assets/previews/photo-illustration-diptych.png`
- Create: `skills/image-effects/assets/previews/scenes-gathered-zine-sea.png`
- Create: `skills/image-effects/assets/previews/scenes-gathered-zine.png`
- Create: `skills/image-effects/assets/previews/scene-distillation-zine.png`
- Create: `skills/image-effects/assets/previews/minimal-zine-poster.png`
- Modify: `skills/image-effects/tests/effect-assets.test.mjs`

**Interfaces:**
- Consumes: the approved preview briefs and the host-native image generation tool.
- Produces: seven independent metadata-free final previews whose decoded dimensions and SHA-256 values are available to Task 5.

- [ ] **Step 1: Read the `imagegen` Skill and add missing-asset RED tests**

Before any generation, read the full current `imagegen/SKILL.md`. Add an exact map of the seven preview paths to expected orientation (`3:5` except Sea `5:3`) and assert each file exists, fully decodes, contains no forbidden metadata, and returns a 64-character lowercase SHA-256. The existing Healing preview remains in the same test.

- [ ] **Step 2: Run asset tests and verify RED**

```bash
node --test skills/image-effects/tests/effect-assets.test.mjs
```

Expected: FAIL because `photo-illustration-editorial-echo.png` and the other six new assets do not exist.

- [ ] **Step 3: Generate Editorial Echo working assets and compose the final preview**

Generate a fictional, brandless analog camera beside a window with diagonal late-afternoon shadow as the photo anchor. Edit that generated anchor into a separate isolated ink-and-watercolor camera motif on ivory paper. Compose the two generated assets locally in a 1024×1536 HTML/CSS poster with real text `LIGHT ENTERS TWICE`, `01 / WINDOW STUDY`, and `A quiet machine holds the returning light.`; use square geometry, one thin blue-gray rule, and three source-derived swatches. Capture only the poster canvas. Do not publish either working asset.

- [ ] **Step 4: Generate the six standalone previews with exact prompts**

Use one fresh text-only image-generation call per effect:

```text
Lakeside Minimal Diptych — 1024×1536 paper poster, upper truthful fictional photograph of an empty curved timber boardwalk beside a still lake with one tiny unbranded rowboat, fixed shoreline/horizon/mountain profile; lower radically simplified geometric echo preserving those correspondences; warm ivory, lake blue, pine green, blue-gray, one restrained coral accent; no people, text, logos, brands, watermarks, UI, or copyrighted location.

Photo–Illustration Diptych — 1024×1536 calm paper poster, upper fictional documentary photograph of an old mountain waterwheel and winding footpath, lower composition-matched editorial cut-paper and fine-ink illustration preserving wheel circle, path movement, building count, horizon, and spatial order; warm paper and source-derived muted colors; no people, text, logos, brands, watermarks, or known landmark.

Gathered Scenes Zine · Sea — 1536×1024 tactile editorial zine, fictional empty coastal railing with a distant generic ferry, truthful photo anchor transitioning through a visible fibrous torn edge into broad quiet paper and compressed source-derived print marks, one structural cobalt hue, tiny non-readable texture marks only; no people, names, logos, brands, watermarks, UI, or real location.

Gathered Scenes Zine — 1024×1536 tactile paper zine, fictional empty greenhouse with one wooden bench and climbing vines, small truthful photo anchor plus expansive abstract field, 60%–80% detail removed, one cut-paper primary grammar, one structural vermilion hue derived from a flower, one tiny phrase GREENHOUSE PAUSE, broad quiet paper; no people, brands, logos, watermarks, UI, or known building.

Scene Distillation Zine — 1024×1536 original paper-zine illustration of a fictional rainy bus shelter with one abandoned umbrella and reflected amber light, no retained photographic pixels, 70% quiet paper, one tension of shelter versus exposure, one umbrella-as-threshold metaphor, torn-fiber edge and one vivid amber accent, restrained authorial typography, flat scanned texture; no people, transport logos, place names, brands, watermarks, or UI.

Minimal Zine Poster — 1024×1536 aged matte paper poster from the theme 留一小段安静, 80% plain paper, one small torn-paper moon-phase cluster, one saturated ultramarine ink anchor occupying about 1.5% of the canvas, sparse typewriter Chinese text 留一小段安静, xerox softness and paper fibers, flat orthographic scan; no people, brands, logos, QR codes, watermarks, UI, glossy lighting, or extra colors.
```

- [ ] **Step 5: Normalize every final preview**

Use the existing locked `sharp@0.35.3` to rotate according to pixels, strip metadata, flatten alpha on warm ivory when required, and write canonical PNGs. Do not use Python for image editing. Delete Editorial Echo working assets after the final poster passes inspection.

- [ ] **Step 6: Print decoded dimensions and SHA values for Task 5**

Run a Node script that imports `inspectImage`, reads each preview, prints `path`, `width`, `height`, and SHA-256, and verifies orientation. Keep that exact output in the execution evidence; Task 5 copies the values into the cards. Use these origins in Task 5:

```text
Text-only image generation of a fictional scene; not based on a real person, place, brand, or third-party image.
```

For Editorial Echo use:

```text
Locally composed from two text-only generated fictional assets; not based on a real person, place, brand, or third-party image.
```

- [ ] **Step 7: Run asset tests and verify GREEN**

```bash
node --test skills/image-effects/tests/effect-assets.test.mjs
```

Expected: all eight previews fully decode, dimensions/orientations match, every digest is canonical SHA-256 text, and forbidden metadata is absent.

- [ ] **Step 8: Visually inspect the seven final previews**

Open each final PNG with the local image viewer, checking source-risk rules, effect distinctness, typography, orientation, anatomy/object geometry, crop, and absence of brands/watermarks. If a generated preview violates a hard rule, make at most one targeted regeneration for that effect and repeat Steps 5–7.

- [ ] **Step 9: Commit preview assets**

```bash
git add skills/image-effects/assets/previews skills/image-effects/tests/effect-assets.test.mjs
git commit -m "feat: add independent effect previews"
```

### Task 5: Add the seven complete effect cards with real preview hashes

**Files:**
- Create: `skills/image-effects/references/effects/photo-illustration-editorial-echo.md`
- Create: `skills/image-effects/references/effects/photo-illustration-diptych-lakeside.md`
- Create: `skills/image-effects/references/effects/photo-illustration-diptych.md`
- Create: `skills/image-effects/references/effects/scenes-gathered-zine-sea.md`
- Create: `skills/image-effects/references/effects/scenes-gathered-zine.md`
- Create: `skills/image-effects/references/effects/scene-distillation-zine.md`
- Create: `skills/image-effects/references/effects/minimal-zine-poster.md`
- Modify: `skills/image-effects/tests/effect-library.test.mjs`
- Modify: `skills/image-effects/tests/effect-assets.test.mjs`

**Interfaces:**
- Consumes: Task 1 schema, Task 3 notices, Task 4 final preview digests, and fixed behavior sources from the approved spec.
- Produces: exactly eight loadable versioned cards with complete standalone behavior and true preview provenance.

- [ ] **Step 1: Add a failing exact-catalog test**

Load `references/effects/` and assert refs exactly equal this ASCII-sorted list:

```js
[
  'healing-anime-scribble-v3@1.0.0',
  'minimal-zine-poster@1.0.0',
  'photo-illustration-diptych-lakeside@1.0.0',
  'photo-illustration-diptych@1.0.0',
  'photo-illustration-editorial-echo@1.0.0',
  'scene-distillation-zine@1.0.0',
  'scenes-gathered-zine-sea@1.0.0',
  'scenes-gathered-zine@1.0.0',
]
```

Assert no ref or card body contains `grade-images`, every card contains the six required `##` protocol headings, every `source_paths` includes `LICENSE`, the matching source SHA equals the referenced local notice hash, and each card’s preview SHA equals its final asset bytes.

- [ ] **Step 2: Run catalog tests and verify RED**

```bash
node --test skills/image-effects/tests/effect-library.test.mjs skills/image-effects/tests/effect-assets.test.mjs
```

Expected: FAIL because the seven new card files do not exist.

- [ ] **Step 3: Create exact frontmatter using final preview hashes**

Use this complete source contract; append `LICENSE` and its notice hash to every behavior mapping:

| id | category | execution | input | source repo@revision | behavior paths |
|---|---|---|---|---|---|
| `photo-illustration-editorial-echo` | editorial | host-image-generation-and-layout | image 1..1 | `wangjs-jacky/happy@e8716a0a0c949f8e2b45e1e3d7c8d36ad7bba17c` | `packages/happy-app/sources/components/agents/photoIllustrationEditorialEchoPrompt.ts` = `66a172d31b3af5c54a22e28adb15432ea25a2fe895d87b6e443451516ad749a3` |
| `photo-illustration-diptych-lakeside` | editorial | host-image-generation | image 1..1 | `wangjs-jacky/happy@fa6c30497d01b077d7d4d58e1a4c00bca4c38fcd` | base = `630058159d094f6db71e7679b2d5b3f471bcb6e8f3dbccd38fa47841ec900a00`; lakeside = `040de02ecfb6658a8276cc96c3127078810da4b16c230c167951e09394d5b8d8` |
| `photo-illustration-diptych` | editorial | host-image-generation | image 1..1 | `wangjs-jacky/happy@532e49bb711283cbe2738439039298f9cea1ef7b` | `photoIllustrationDiptychPrompt.ts` = `fd78d07b3b36446e88c4b073e38d948642e40c4ffd3c8954b29b704f44909934` |
| `scenes-gathered-zine-sea` | zine | host-image-generation | image 1..1 | `Zeejay0/gathered-scenes-zine-skill@e764b7fd243d7cc501723b9d325279bf6dd852c2` | `skills/scenes-gathered-zine-v1-3/SKILL.md` = `665b4be2cc54830f4ef489f0290e21f0eb123b70b1922bca4cdddf9e5b2eb670` |
| `scenes-gathered-zine` | zine | host-image-generation | image 1..1 | `Zeejay0/gathered-scenes-zine-skill@e764b7fd243d7cc501723b9d325279bf6dd852c2` | `skills/scenes-gathered-zine-v1-3/SKILL.md` = `665b4be2cc54830f4ef489f0290e21f0eb123b70b1922bca4cdddf9e5b2eb670` |
| `scene-distillation-zine` | zine | host-image-generation | image 1..1 | mirror `Zeejay0/gathered-scenes-zine-skill@e764b7fd243d7cc501723b9d325279bf6dd852c2` | `skills/scene-distillation-zine-v1-3/SKILL.md` = `088116c2bbf70b4891e5ece8191ed729d6e8074555895df2c16780ebd5800fbc` |
| `minimal-zine-poster` | zine | host-image-generation | text-or-image 0..1 | `LiamGvchi/gc-minimal-zine-poster@4cb0396ad4e834019f753b37e1c4f415f5e02026` | `SKILL.md` = `d4e1199623ee4d98e948189308eedc601f83ab0ae923568c6e9240f89c783b8b` |

Set version `1.0.0`, formats `jpeg,png`, output count `1`, preview path `assets/previews/<id>.png`, author `wangjs-jacky`, license `CC-BY-4.0`, and the exact SHA printed in Task 4. Use the fictional-scene origin sentence from Task 4, with the separate local-composition origin for Editorial Echo.

- [ ] **Step 4: Write each complete six-section body**

Transcribe all observable compiler constraints from the fixed source into 适用场景、输入契约、视觉编译规则、硬性禁止项、质量检查、交付要求. Remove Happy-specific paths/calls but preserve these exact behavioral cores:

- Editorial Echo: capability preflight before Stage A; isolated motif; fixed-dimension HTML/CSS with original photo and real text; Copy Map; layout-only retry; complete no-layout fallback.
- Lakeside: boardwalk/path curve, dock rhythm, vessel, shoreline, horizon, landform, geometric reduction, and blue/green/coral/ivory source palette.
- Base Diptych: truthful upper photo; lower composition-matched ink wash, cut-paper, geometric, or Art Deco illustration chosen from source; preserve counts, proportions, spatial order, and circles.
- Gathered Sea: truthful coastal photo anchor, fibrous torn handoff, compressed print field, one structural hue, and restrained micro-text.
- Gathered base: source-driven layout, 60%–80% detail removal, one primary plus at most one support grammar, one structural high-chroma hue, and one micro-text element.
- Scene Distillation: remove 65%–90% detail and all photo pixels; one proposition/tension/metaphor; 68%–85% quiet paper; standard accent or exact `单色块模式`; authorial typography. Preserve original identity `Zeejay0/scene-distillation-zine-v1-3@921390baac518c85d60a6d98709f1dd657eec720` in `adaptation_notice` while verifying the same-author mirror.
- Minimal Zine: 3:5, 70%–90% paper, 8%–25% cluster, one imageable metaphor, one visible saturated ink anchor, and text-only or one-image input.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
node --test skills/image-effects/tests/effect-library.test.mjs skills/image-effects/tests/effect-assets.test.mjs
```

Expected: exact catalog, parser, body structure, license mapping, image decoding, metadata, and preview hashes all pass.

- [ ] **Step 6: Commit the cards**

```bash
git add skills/image-effects/references/effects skills/image-effects/tests
git commit -m "feat: add complete image effects catalog"
```

### Task 6: Generate deterministic artifacts and complete license notices

**Files:**
- Modify: `skills/image-effects/tests/build-gallery.test.mjs`
- Modify: `skills/image-effects/tests/export-public-repo.test.mjs`
- Modify: `skills/image-effects/scripts/build-gallery.mjs`
- Modify: `skills/image-effects/scripts/effect-library.mjs`
- Generate: `skills/image-effects/references/INDEX.md`
- Generate: `skills/image-effects/assets/public-repo/THIRD_PARTY_NOTICES.md`
- Generate: `skills/image-effects/gallery/api/library.json`
- Generate: `skills/image-effects/gallery/media/*`
- Generate: `skills/image-effects/gallery/source/*`

**Interfaces:**
- Consumes: eight validated cards, four license notices, and eight final previews.
- Produces: deterministic schema-2 Library, intrinsic dimensions, deduplicated complete MIT notices, and exact eight-effect generated trees.

- [ ] **Step 1: Add failing build tests**

Assert a fixed-epoch build emits exactly eight source cards and eight media files, schema 2, every fixed ref, real decoded dimensions, and four unique full MIT notice blocks. Assert each notice includes its copyright line and that Scene Distillation includes both original coordinates and verifiable mirror coordinates.

- [ ] **Step 2: Add failing deterministic-export assertions**

Build into two independent output roots with `generatedAt: '2026-08-18T00:00:00.000Z'`, compare sorted paths and every byte hash, then assert public export includes `references/licenses/` and all 16 versioned Gallery artifacts.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
node --test skills/image-effects/tests/build-gallery.test.mjs skills/image-effects/tests/export-public-repo.test.mjs
```

Expected: FAIL because `buildGallery` does not pass preview metadata, Notice rendering does not load license files, and generated artifacts are stale.

- [ ] **Step 4: Decode preview metadata before Library projection**

In `buildGallery`, read each source preview once, call `assertMetadataFreeImage`, capture its `{ width, height }`, and pass a `Map<ref, {width,height}>` to `buildLibrary`. Reuse the validated bytes for Gallery media artifacts; do not re-read or re-encode them during the same build.

- [ ] **Step 5: Render complete deduplicated notices**

Change the pure interface to:

```js
export function renderThirdPartyNotices(effects, header, licenseNoticesByPath)
```

Require one notice for every effect, verify the local notice SHA matches the `LICENSE` source mapping, output the existing per-effect provenance sections, then append each unique full notice once in ASCII path order.

- [ ] **Step 6: Rebuild from a fixed epoch**

```bash
SOURCE_DATE_EPOCH=1787011200 node skills/image-effects/scripts/build-gallery.mjs
```

Expected: INDEX, Notice, Library, eight media files, and eight source files update atomically.

- [ ] **Step 7: Run focused tests and verify GREEN**

```bash
node --test skills/image-effects/tests/build-gallery.test.mjs skills/image-effects/tests/export-public-repo.test.mjs
```

Expected: PASS, including deterministic-tree and exporter coverage.

- [ ] **Step 8: Commit generated artifacts and builder changes**

```bash
git add skills/image-effects
git commit -m "feat: build full image effects gallery"
```

### Task 7: Update public documentation and validate the Gallery experience

**Files:**
- Modify: `skills/image-effects/assets/public-repo/README.md`
- Modify: `skills/image-effects/assets/public-repo/README_CN.md`
- Modify: `skills/image-effects/tests/gallery-assets.test.mjs`
- Modify if required by browser evidence: `skills/image-effects/gallery/styles.css`

**Interfaces:**
- Consumes: generated eight-effect Gallery from Task 6.
- Produces: accurate install/use/capability docs and verified desktop/mobile static Gallery behavior.

- [ ] **Step 1: Add failing public-contract tests**

Assert both READMEs state eight effects, show an image-input invocation and the Minimal Zine text-or-image invocation, explain Editorial Echo’s two-stage layout requirement/fallback, state no extra Skill dependency, exclude `grade-images`, and link Gallery plus `THIRD_PARTY_NOTICES.md`.

- [ ] **Step 2: Run the documentation and HTTP tests to verify RED**

```bash
node --test skills/image-effects/tests/gallery-assets.test.mjs
```

Expected: FAIL on stale “1 effect” copy and missing capability documentation.

- [ ] **Step 3: Rewrite English and Chinese public documentation**

Document the exact eight refs, `npx skills add wangjs-jacky/image-effects`, both invocation forms, image privacy, host-native generation, Editorial Echo capability preflight, Minimal Zine input choices, version stability, generated preview licensing, and full upstream notices. Do not advertise App integration, remote loading, grading, or online generation.

- [ ] **Step 4: Run tests and verify GREEN**

```bash
node --test skills/image-effects/tests/gallery-assets.test.mjs
```

Expected: PASS with all relative resources and documentation contracts valid.

- [ ] **Step 5: Start a temporary static HTTP server and crawl all assets**

Use a disposable local server rooted at `skills/image-effects/gallery` and verify `/`, `api/library.json`, eight media URLs, and eight source URLs return HTTP 200 with correct MIME. Stop the server after browser validation.

- [ ] **Step 6: Validate desktop and mobile in a browser**

At 1440×1000 and 390×844, verify eight cards render, portrait and landscape previews keep their intrinsic ratio, search finds `minimal-zine`, each category filter works, language/theme controls work, selection copies versioned invocations, source/license links are correct, and no horizontal overflow, clipped text, or overlapping controls appears.

- [ ] **Step 7: Fix only browser-observed CSS defects and re-run evidence**

For each defect, add a failing structural/runtime assertion when automatable, then make the smallest CSS/JS correction and repeat Steps 4–6. Do not redesign the approved Gallery.

- [ ] **Step 8: Commit documentation and any verified UI correction**

```bash
git add skills/image-effects/assets/public-repo skills/image-effects/gallery skills/image-effects/tests/gallery-assets.test.mjs
git commit -m "docs: document full image effects catalog"
```

### Task 8: Run source-repository gates, open the PR, and merge

**Files:**
- Verify: all branch changes
- Create externally: GitHub pull request against `wangjs-jacky/jacky-skills:main`

**Interfaces:**
- Consumes: complete feature branch from Tasks 1–7.
- Produces: reviewed and merged source PR with a clean `origin/main` commit suitable for export.

- [ ] **Step 1: Run Skill-specific validation from fresh state**

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skills/image-effects
node --test skills/image-effects/tests/*.test.mjs
node skills/image-effects/scripts/validate-effects.mjs --online
SOURCE_DATE_EPOCH=1787011200 node skills/image-effects/scripts/build-gallery.mjs
git diff --exit-code -- skills/image-effects
git ls-files --others --exclude-standard -- skills/image-effects
```

Expected: quick validation passes; all Node tests pass with zero failures; online fixed-source hashes pass; rebuild produces no diff; untracked listing is empty.

- [ ] **Step 2: Run repository-wide required gates**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/audit_skills.py --scan-shared-content
bash -n install.sh
claude plugin validate --strict .
```

Expected: every command exits 0. Record exact test counts and warnings rather than summarizing them away.

- [ ] **Step 3: Review the complete branch diff and history**

```bash
git status --short
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected: clean worktree; no whitespace error; only approved spec, plan, image-effects source/assets/generated outputs, and tests are present.

- [ ] **Step 4: Push the branch and open a PR**

```bash
git push -u origin image-effects-full-catalog
gh pr create --base main --head image-effects-full-catalog \
  --title "feat: complete image effects catalog" \
  --body $'## Summary\n- publish the approved eight-effect image-effects catalog\n- add seven independently generated CC-BY-4.0 previews\n- preserve fixed MIT provenance and complete notices\n- upgrade Gallery data to schema 2 with real preview dimensions\n\n## Scope\n- excludes grade-images, Happy App changes, remote catalogs, OSS/CDN, and OTA\n- Editorial Echo uses capability-gated image generation plus HTML/CSS layout\n- Minimal Zine accepts text or one uploaded image\n\n## Validation\n- Skill-specific Node tests and online source hashes\n- deterministic rebuild and export checks\n- repository-wide audit and plugin validation\n- local HTTP plus desktop/mobile browser review\n\n## Release\nAfter merge, export from the merged main Git tree to wangjs-jacky/image-effects and verify GitHub Pages.'
```

The inline body records scope, excluded `grade-images`, license provenance, preview policy, schema 2, validation evidence, and the post-merge release plan. Add exact test counts to the PR in a follow-up comment after the full gates finish.

- [ ] **Step 5: Review PR state and checks**

```bash
gh pr view --json url,state,mergeable,reviewDecision,statusCheckRollup,commits,files
gh pr checks --watch
```

Expected: PR is open and mergeable; all required checks complete successfully. Inspect GitHub’s changed-file list and compare it with local `origin/main...HEAD`.

- [ ] **Step 6: Merge the approved PR and verify source main**

The user has already authorized merge after acceptance. Merge only after all gates above pass:

```bash
gh pr merge --merge --delete-branch
git fetch origin main
gh pr view --json url,state,mergedAt,mergeCommit
```

Expected: state `MERGED`, a non-null merge commit, and `origin/main` contains the exact feature commits.

### Task 9: Export merged source, publish the public repository, and verify Pages

**Files:**
- Generate in a disposable clean worktree: public `wangjs-jacky/image-effects` managed files
- Create externally: public repository commit and Pages deployment

**Interfaces:**
- Consumes: merged `jacky-skills/origin/main` from Task 8 and the existing public `wangjs-jacky/image-effects` repository.
- Produces: clean public main commit, successful Pages deployment, and verified public eight-effect Gallery.

- [ ] **Step 1: Create a clean post-merge source worktree**

Create `/Users/jacky/jacky-github/jacky-skills--image-effects-release` as a temporary sibling worktree detached at the exact merge commit. Confirm `git status --short` is empty and `HEAD == origin/main`. Install `skills/image-effects` maintenance dependencies with `npm ci --prefix skills/image-effects`.

- [ ] **Step 2: Inspect and prepare the existing public repository**

Use `gh repo view wangjs-jacky/image-effects` and clone it to `/Users/jacky/jacky-github/image-effects--release`. Fetch `main`, require a clean worktree, and confirm the current `.image-effects-export.json` source commit matches the previous source release. Do not overwrite a dirty or unexpected target.

- [ ] **Step 3: Export only from merged Git objects**

From the clean source worktree run:

```bash
node skills/image-effects/scripts/export-public-repo.mjs --target /Users/jacky/jacky-github/image-effects--release
node skills/image-effects/scripts/export-public-repo.mjs --target /Users/jacky/jacky-github/image-effects--release --check
```

Expected: export and `--check` pass; manifest `sourceCommit` equals the source merge commit; managed files include all eight cards, four licenses, eight previews, and Gallery artifacts.

- [ ] **Step 4: Validate the uncommitted public export**

In the public clone run `npm ci`, the full Node test suite, local static HTTP crawl, desktop/mobile browser checks, `git diff --check`, and a content scan for `/Users/`, attachment paths, private keys, tokens, and unintended files. Expected: all pass; only manifest-managed files differ.

- [ ] **Step 5: Commit and push public main**

```bash
git add --all
git commit -m "feat: publish full image effects catalog"
git push origin main
```

Do not force push. Record the public commit SHA.

- [ ] **Step 6: Wait for Pages deployment and verify online assets**

Use `gh run list`/`gh run watch` for the public repository’s Pages workflow. After success, request:

```text
https://wangjs-jacky.github.io/image-effects/
https://wangjs-jacky.github.io/image-effects/api/library.json
```

Verify HTTP 200, schema 2, exactly eight refs, eight preview URLs, eight source URLs, correct MIME, the install command, and no stale one-effect copy.

- [ ] **Step 7: Browser-check the public URL and report evidence**

Repeat the desktop/mobile interaction checks against the public URL. Final evidence must include source PR URL, source merge SHA, public commit SHA, Pages workflow URL, public Gallery URL, exact local/repository test counts, online-source validation, and any non-blocking warnings.
