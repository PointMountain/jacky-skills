---
id: photo-illustration-diptych
version: 1.0.0
title_en: Photo–Illustration Diptych
title_zh: 摄影插画双联画
summary_en: Express one observed scene twice as a truthful upper photograph and a composition-matched editorial illustration below.
summary_zh: 以真实上部照片和构图对应的下部编辑插画，对同一观察场景做双重表达。
category: editorial
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/photo-illustration-diptych.png
source_repository: wangjs-jacky/happy
source_revision: 532e49bb711283cbe2738439039298f9cea1ef7b
source_paths: packages/happy-app/sources/components/agents/photoIllustrationDiptychPrompt.ts,LICENSE
source_sha256s: fd78d07b3b36446e88c4b073e38d948642e40c4ffd3c8954b29b704f44909934,e251d0448ef3ce023c20ebac9b90a7d8642b1434825838247d6e457668eb3e00
source_license_spdx: MIT
source_license_url: https://github.com/wangjs-jacky/happy/blob/532e49bb711283cbe2738439039298f9cea1ef7b/LICENSE
source_license_notice: references/licenses/happy-coder-contributors-mit.txt
adaptation_notice: Preserves the original two-panel visual compiler and source-driven medium choice while making privacy, native delivery, and targeted correction host-neutral.
preview_origin: Text-only image generation of a fictional scene; not based on a real person, place, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: 38fd7df64d4e8a4bc0483cc0be36a0c1324defe123802fe1e1b3c82f2d4ce46f
---

## 适用场景

Transform exactly one real-world photo into one calm vertical 3:5 paper poster that expresses the observed scene twice. Keep one truthful photographic anchor above and one materially distinct, composition-matched editorial illustration below. The pairing must read as a single Scene Map, never as a generic before/after filter.

## 输入契约

Require exactly one JPEG or PNG attached to this request. Never browse for replacement imagery or infer input from history or nearby files. Use the source only for this task, disclose no private path, and do not commit, redistribute, or retain extra copies.

Build a Scene Map containing primary subject, 1–3 secondary anchors, horizon or ground line, dominant silhouette, subject and landmark counts, left-to-right order, relative scale, viewing direction, movement, native color atmosphere, and minimum identity-bearing detail. Build one normalized Framing Map from the chosen upper crop, including content-space centers, axes, relative scale, horizon, and geometry.

## 视觉编译规则

- Use a 3:5 warm-ivory page with quiet margins. Give roughly 40–47% to a single upper photo and 45–52% to a coherent lower illustration, separated by breathing paper or a subtle handoff.
- Keep the upper panel photographic and truthful. Preserve subject, landmark count, perspective, spatial order, time-of-day logic, and native character. Use isotropic scaling, a proportional crop, or an inset; never stretch.
- Reuse the exact crop window and content coordinate map below. Preserve counts, proportions, horizon, dominant silhouette, movement, and spatial order. Keep faces, bodies, glasses, architectural verticals, repeated spacing, and wheel, fan, or pulley circles geometrically sound.
- Simplify constructed forms by roughly 65–85% and organic or repetitive texture by roughly 80–95%, while preserving semantic geometry.
- Choose one lower medium from the source. Use fine ink with diluted watercolor for quiet landscapes, coasts, mountains, or architecture; flat cut-paper shapes and restrained outlines for heritage, villages, watermills, trees, or walking groups; geometric blocks for modern skylines; or restrained Art Deco geometry for dramatic night architecture. Do not force one style across all scenes.
- Use 4–7 source-derived colors plus warm paper and neutral ink, broad value grouping, quiet space, and at most one muted source-derived accent.
- Typography is opt-in. Reproduce only exact user wording as one short title and at most one subtitle; never invent place names or tourism copy. Omit text if reliable rendering is unavailable.

## 硬性禁止项

Reject non-uniform scaling, crop mismatch, proportion drift, ovalized circles, changed subject or landmark counts, scene replacement, photorealistic lower rendering, literal tracing, generic stock vector art, unrelated motifs, arbitrary neon accents, full-scene filtering, UI, before/after labels, collage grids, scrapbook clutter, heavy grain, glossy 3D, anime treatment, malformed people, dense typography, pseudo-text, logos, QR codes, signatures, or watermarks.

## 质量检查

Confirm one input produced one 3:5 poster; panel bounds are level and balanced; the source used isotropic scale; both panels share the exact Framing Map; at least five major forms align; subject and landmark counts and left-to-right order are unchanged; source proportions, circles, and axes survive; the upper remains photographic; the lower is unmistakably illustrated in a subject-appropriate medium; the palette is source-derived; people and optional exact text are valid; and no UI or private path appears.

If crop, scale, correspondence, anatomy, or geometry fails, regenerate at most once with a correction limited to that defect while preserving the Scene Map and Framing Map.

## 交付要求

Deliver exactly one final poster using the host's native image path and add a short rationale naming key cross-panel correspondences, chosen medium, and palette. Do not reveal private paths or the full prompt unless asked.
