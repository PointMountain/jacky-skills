---
id: minimal-zine-poster
version: 1.0.0
title_en: Minimal Zine Poster
title_zh: 极简纸刊海报
summary_en: Turn a short idea or one image into a sparse 3:5 paper poster with one imageable metaphor, a small cluster, and one saturated ink anchor.
summary_zh: 将短主题或一张图片转成稀疏的 3:5 纸面海报，以一个可成像隐喻、小型构图簇和一处饱和墨色锚点为核心。
category: zine
execution_kind: host-image-generation
input_mode: text-or-image
input_min: 0
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/minimal-zine-poster.png
source_repository: LiamGvchi/gc-minimal-zine-poster
source_revision: 4cb0396ad4e834019f753b37e1c4f415f5e02026
source_paths: SKILL.md,LICENSE
source_sha256s: d4e1199623ee4d98e948189308eedc601f83ab0ae923568c6e9240f89c783b8b,d15c81ae8fa9a0b4b1db46c66e4490cc92e4898fb1f55e030559fbd2a2e2a232
source_license_spdx: MIT
source_license_url: https://github.com/LiamGvchi/gc-minimal-zine-poster/blob/4cb0396ad4e834019f753b37e1c4f415f5e02026/LICENSE
source_license_notice: references/licenses/liamgvchi-mit.txt
adaptation_notice: Preserves the original minimal-zine composition ratios, metaphor discipline, paper material, text-or-image routes, visible ink anchor, and targeted correction in a host-neutral card.
preview_origin: Text-only image generation of a fictional scene; not based on a real person, place, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: d7796377f564a40d0aaae89028afcfb12cad1aeaf5b2736ece69c4277e9b9781
---

## 适用场景

Create exactly one vertical 3:5 minimal paper-zine poster from either a short text idea or one supplied image. Use when the concept can be reduced to one imageable metaphor, one small visual cluster, and one visible saturated ink anchor surrounded by dominant paper. This is a sparse authored print object, not a mood board, scrapbook, advertisement, or full-scene illustration.

## 输入契约

Accept exactly one of these routes: a non-empty text theme with zero images, or one current-request JPEG or PNG with optional written direction. Reject an empty theme with zero images and reject more than one image. Do not infer attachments from history or scan local folders.

For text-only input, extract one concrete imageable metaphor rather than illustrating every noun. For image input, treat the photo as private task input and preserve only its central subject, silhouette, emotional cue, and 2–4 source color roles; reduce it to a small paper anchor rather than retaining a full photographic field. Do not expose its path, browse for alternatives, commit it, or retain extra copies.

## 视觉编译规则

- Use a strict vertical 3:5 canvas with aged or warm matte paper, flat orthographic scan behavior, visible but restrained fibers, xerox softness, and no artificial perspective.
- Reserve 70–90% of the page as quiet paper. Keep all active illustration, supplied-image reduction, typography, and ink within one coherent cluster occupying roughly 8–25% of the canvas.
- Build exactly one imageable metaphor from the theme or source. Give it one dominant silhouette and at most two supporting fragments. Omit decorative objects that do not strengthen that metaphor.
- Use one primary paper grammar such as torn-paper collage, photocopy, dry ink, typewriter, relief print, or sparse cut-paper geometry, with at most one quiet supporting texture.
- Add one clearly visible saturated ink anchor in a single hue. It must be large enough to read at thumbnail size and structurally attach to the metaphor or cluster, never float as a token swatch. Warm paper and neutral black, graphite, or brown inks are not additional hues.
- Typography must be sparse and exact. Use supplied wording verbatim when present; otherwise derive one short line from the theme. Keep it subordinate, legible, and integrated through typewriter, letterpress, pencil, or dry-ink texture. Add no metadata, attribution, slogan, or second text block.
- Balance the cluster asymmetrically with broad uninterrupted paper. Let one edge, axis, or baseline connect image, ink, and text.

## 硬性禁止项

Do not fill the page, build multiple clusters, illustrate every idea, retain a full photo, add multiple metaphors, use more than one saturated hue, hide the ink anchor, scatter decorative scraps, use gradients, neon glow, glossy lighting, 3D, depth of field, mockup perspective, commercial advertising hierarchy, CTA, logos, QR codes, icons, frames, rounded cards, drop shadows, large display copy, pseudo-text, invented quotations, signatures, watermarks, or UI.

## 质量检查

Confirm the output is exactly 3:5; quiet paper occupies 70–90%; one coherent cluster occupies 8–25%; there is exactly one imageable metaphor and no competing narrative; one saturated ink anchor is visible at thumbnail size and attached to the composition; image mode retains only truthful core cues rather than a full photo; text mode turns a non-empty theme into a concrete form; typography is exact, sparse, and legible; the material reads as flat aged paper; and no brand, commercial UI, signature, or watermark appears.

On a hard failure in ratio, paper share, cluster size, metaphor clarity, source fidelity, ink visibility, or text, regenerate at most once with a correction limited to that defect.

## 交付要求

Deliver one final poster through the host's native image-delivery path and a 1–3 sentence rationale naming the metaphor, paper/cluster balance, and ink anchor. Do not reveal a private input path or the full prompt unless requested.
