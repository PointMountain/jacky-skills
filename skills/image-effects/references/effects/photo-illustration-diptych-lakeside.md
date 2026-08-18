---
id: photo-illustration-diptych-lakeside
version: 1.0.0
title_en: Lakeside Minimal Diptych
title_zh: 湖畔极简双联画
summary_en: Pair a truthful waterside photo with a radically reduced geometric echo that preserves its path, horizon, vessel, and landform.
summary_zh: 将真实水岸照片与极度简化的几何回声配对，保留路径、地平线、船只和远端地貌。
category: editorial
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/photo-illustration-diptych-lakeside.png
source_repository: wangjs-jacky/happy
source_revision: fa6c30497d01b077d7d4d58e1a4c00bca4c38fcd
source_paths: packages/happy-app/sources/components/agents/photoIllustrationDiptychPrompt.ts,packages/happy-app/sources/components/agents/photoIllustrationDiptychLakesidePrompt.ts,LICENSE
source_sha256s: 630058159d094f6db71e7679b2d5b3f471bcb6e8f3dbccd38fa47841ec900a00,040de02ecfb6658a8276cc96c3127078810da4b16c230c167951e09394d5b8d8,e251d0448ef3ce023c20ebac9b90a7d8642b1434825838247d6e457668eb3e00
source_license_spdx: MIT
source_license_url: https://github.com/wangjs-jacky/happy/blob/fa6c30497d01b077d7d4d58e1a4c00bca4c38fcd/LICENSE
source_license_notice: references/licenses/happy-coder-contributors-mit.txt
adaptation_notice: Combines the lakeside specialization with its base diptych compiler at the first revision containing both, while preserving the base source identity at revision 532e49bb711283cbe2738439039298f9cea1ef7b.
preview_origin: Text-only image generation of a fictional scene; not based on a real person, place, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: e6b830bd342c43ca435022385cfd5b1ea3720de7216d3599e27c3dd205d9b67a
---

## 适用场景

Transform exactly one supplied lake, coast, river, reservoir, or calm waterside photo into one vertical 3:5 warm-ivory diptych. The upper region is a truthful photographic anchor; the lower region is a radically reduced geometric interpretation. Use this specialization only when scene identity depends on a leading path or boardwalk, dock or pier rhythm, one small vessel or compact focal object, shoreline, clear horizon, and distant landform.

## 输入契约

Require exactly one current-request JPEG or PNG. Do not browse, search, or infer a substitute from history or the filesystem. Keep the source private, send only the required image and compiled instructions to the native image tool, disclose no path, and retain no unnecessary copy.

Build a Scene Map and Framing Map before generation. Record the boardwalk or path curve, dock-post rhythm, vessel count and position, shoreline, horizon height, mountain or island profile, relative scale, source aspect ratio, native palette, and landmark order. Apply one isotropic scale factor to the source; use a proportional crop or warm-paper inset rather than stretching.

## 视觉编译规则

- Use a 3:5 warm-ivory page with balanced margins. Allocate roughly 40–47% to one level photographic panel and 45–52% to the illustration, with breathing paper between them.
- Keep the upper photo truthful. Mild tonal harmonization may clarify it, but never move the vessel, invent structures, replace the place, distort proportions, or abandon the shared crop.
- Reuse the same-aspect-ratio content rectangle and normalized Framing Map below. Align path curve, dock rhythm, vessel, shoreline, horizon, and distant landform across the divide.
- Reduce the lower field to simple geometric shapes, flat source-derived color fields, and a few precise hairline contours. Remove roughly 85–95% of water texture, grass, cloud, reflection, railing, foliage, surface noise, and architectural detail.
- Limit the lower palette to 3–6 source-derived colors plus warm ivory: lake or sky blue, vegetation green, blue-gray landform, white structures, and at most one small coral, rust, or warm accent that exists in the source.
- Use broad negative space. Sparse horizontal rules or texture marks may clarify shoreline and atmosphere only when tied to source geometry.
- Keep typography off by default. If the user supplies exact wording or explicitly asks for copy, reproduce only one short title and optional short subtitle; otherwise remain text-free.

## 硬性禁止项

Never stretch the source, trace the lower panel, render the lower panel photorealistically, change vessel or landmark count, move the shoreline or horizon, turn circles into ovals, introduce arbitrary neon color, tourism copy, generic labels, gradients, stock icons, decorative symbols, comparison UI, phones, viewer chrome, logos, QR codes, signatures, watermarks, unrelated scenes, or dense decoration.

## 质量检查

Verify one source produced one 3:5 poster; the source was scaled isotropically; upper and lower regions share one Framing Map; the path curve, dock cadence, vessel, shoreline, horizon, and landform are immediately pairable; proportions and circles remain valid; at least five major correspondences align; the lower scene removes 85–95% of incidental detail; the blue, green, blue-gray, ivory, and optional coral palette comes from the source; and the result remains calm and legible at thumbnail size.

On a hard tool or fidelity failure, regenerate at most once with a correction limited to the observed correspondence, crop, scale, proportion, or palette defect. Preserve the same maps.

## 交付要求

Return exactly one final image through the host's native delivery path, followed by a concise rationale naming the preserved waterside correspondences and geometric reduction. Do not expose the source path or full prompt unless requested.
