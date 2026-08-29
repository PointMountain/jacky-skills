---
id: photo-illustration-diptych-coastline
version: 1.0.0
title_en: Coastline Watercolor Diptych
title_zh: 海岸水彩双联画
summary_en: Pair one truthful coastal photograph with a viewpoint-matched ink-and-watercolor study that preserves the shoreline, horizon, landmark order, and wave rhythm.
summary_zh: 将一张真实海岸照片与同视角墨线水彩习作配对，保留海岸线、地平线、地标顺序与浪带节奏。
category: editorial
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/photo-illustration-diptych-coastline.jpg
source_repository: wangjs-jacky/happy
source_revision: 532e49bb711283cbe2738439039298f9cea1ef7b
source_paths: packages/happy-app/sources/components/agents/photoIllustrationDiptychPrompt.ts,LICENSE
source_sha256s: fd78d07b3b36446e88c4b073e38d948642e40c4ffd3c8954b29b704f44909934,e251d0448ef3ce023c20ebac9b90a7d8642b1434825838247d6e457668eb3e00
source_license_spdx: MIT
source_license_url: https://github.com/wangjs-jacky/happy/blob/532e49bb711283cbe2738439039298f9cea1ef7b/LICENSE
source_license_notice: references/licenses/happy-coder-contributors-mit.txt
adaptation_notice: Specializes the original two-panel compiler for coastlines, sea caves, bridges, harbors, and open beaches while preserving its one-photo privacy boundary, scene correspondence, and host-native delivery.
preview_origin: Adapted from a project-owned, text-only image generation of a fictional waterside scene; not based on a real person, place, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: f4f5feb83d28dd60e310afbfaf1bdf79f9294884baec8f3b1b488b840a38382e
---

## 适用场景

Transform exactly one supplied beach, headland, harbor, sea cave, coastal bridge, shoreline-architecture, or open-water photograph into one calm vertical 3:5 warm-ivory diptych. Keep one truthful photographic rectangle above and one smaller, viewpoint-matched ink-and-watercolor study below. The result must read as the same observed coast expressed twice, never as a generic travel poster or before/after filter.

## 输入契约

Require exactly one JPEG or PNG attached to the current request. Never browse for replacement imagery or infer input from history, prior messages, or nearby files. Keep the source private, disclose no path, and retain no unnecessary copy.

Before generation, build a Scene Map and one normalized Framing Map. Record the horizon height, coastline direction, headland, cave opening, bridge span or harbor rhythm, landmark count and left-to-right order, building placement, wave-band rhythm, any single boat or human-scale anchor, source aspect ratio, and native color relationships. Apply one isotropic scale factor; use a proportional crop or warm-paper inset rather than stretching.

## 视觉编译规则

- Use a vertical 3:5 warm-ivory paper poster with generous quiet margins. Allocate roughly 42–50% to one clean upper photograph and 28–38% to the lower watercolor study, leaving broad breathing paper between them.
- Keep the upper photo truthful. Mild tonal harmonization may clarify it, but never replace the place, move a landmark, alter the weather logic, change subject count, or distort proportions.
- Reuse the same viewpoint and normalized Framing Map below. Preserve horizon height, coastline direction, landmark order, cave, bridge or headland silhouette, wave-band rhythm, building placement, and any single boat or human-scale anchor that identifies the scene.
- Rebuild the lower scene with fine ink contours, dry-brush edges, granulating watercolor washes, translucent overlaps, and intentional unpainted paper. It must look hand-rendered, not vectorized, filtered, or photorealistic.
- Use 4–6 source-derived colors plus neutral ink. Keep the native relationships among water, dusk sky, stone, vegetation, lights, and reflections; do not introduce arbitrary neon or a generic travel palette.
- For a sea cave or rock opening, preserve the dark framing mass and exact opening shape around the bright water view.
- For a bridge or night harbor, preserve the main arch, tower or pier rhythm and translate light into restrained watercolor blooms and reflections.
- For an open beach, preserve the headland profile and repeat the visible wave bands rather than inventing decorative waves.
- Typography is off by default. If the user supplies exact series title, sequence number, location, or date, reproduce only that supplied text as sparse editorial metadata in the lower-left or lower margin, with up to three small source-palette swatches nearby. Never infer a place, year, or issue number.

## 硬性禁止项

Never stretch the source, change the coastline, swap or invent a landmark, alter the cave, bridge, headland, boat, or person count, move the horizon, let watercolor spill into the photo, use a second unrelated scene, add faux travel stamps, map pins, marine icons, scrapbook decoration, gradients, generic tourism copy, phone or viewer chrome, logos, QR codes, signatures, or watermarks.

## 质量检查

Verify that one source produced one 3:5 poster; the source was scaled isotropically; the upper and lower regions share one Framing Map; the horizon, coastline direction, landmark order, defining cave, bridge or headland silhouette, and wave rhythm are immediately pairable; at least five major scene correspondences align; the lower scene reads as fine ink and translucent watercolor with intentional paper; the palette is source-derived; no metadata was invented; and the composition remains calm and legible at thumbnail size.

On a hard tool or fidelity failure, regenerate at most once with a correction limited to the observed viewpoint, correspondence, crop, proportion, palette, watercolor, or typography defect. Preserve the same maps and user-supplied copy.

## 交付要求

Return exactly one final image through the host's native delivery path, followed by a concise rationale naming the preserved coastal correspondences, watercolor treatment, and source-derived palette. Mention editorial metadata only when the user supplied it. Do not expose the source path or full prompt unless requested.
