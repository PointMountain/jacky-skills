---
id: scene-distillation-zine
version: 1.0.0
title_en: Scene Distillation Zine
title_zh: 场景蒸馏纸刊
summary_en: Distill one photo into a mostly quiet paper proposition with no retained pixels, one tension, one metaphor, and one accent system.
summary_zh: 将一张照片蒸馏为大面积安静纸面的命题，不保留照片像素，只留一种张力、一个隐喻和一套强调色。
category: zine
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/scene-distillation-zine.png
source_repository: Zeejay0/gathered-scenes-zine-skill
source_revision: e764b7fd243d7cc501723b9d325279bf6dd852c2
source_paths: skills/scene-distillation-zine-v1-3/SKILL.md,LICENSE
source_sha256s: 088116c2bbf70b4891e5ece8191ed729d6e8074555895df2c16780ebd5800fbc,7d063a2fe4a45ac0adf349ab8d568de5bc93206aaa3982a243dd8d067a3e2f4a
source_license_spdx: MIT
source_license_url: https://github.com/Zeejay0/gathered-scenes-zine-skill/blob/e764b7fd243d7cc501723b9d325279bf6dd852c2/LICENSE
source_license_notice: references/licenses/gathered-scenes-zine-contributors-mit.txt
adaptation_notice: Preserves original identity Zeejay0/scene-distillation-zine-v1-3@921390baac518c85d60a6d98709f1dd657eec720 while verifying identical-author public mirror bytes and retaining its full distillation protocol.
preview_origin: Text-only image generation of a fictional scene; not based on a real person, place, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: 912552322668018ef62ed2a4a2e3b452f696daf3c9fa136cfc6cc94b83224ac2
---

## 适用场景

Transform exactly one supplied photo into one original flat paper-zine illustration with no retained photographic pixels. Use when the desired result is a conceptual distillation rather than a collage: one proposition, one tension, one imageable metaphor, 68–85% quiet paper, and a small authorial cluster. The output should preserve the source's semantic minimum while removing 65–90% of visible detail.

## 输入契约

Require exactly one JPEG or PNG explicitly attached to this request. Do not browse or infer another source from history or the filesystem. Treat it as private task input, disclose no path, and retain no unnecessary copy.

Build a Scene Thesis before generation. Record the semantic minimum, one source proposition, one tension between two forces, one metaphor grounded in a visible object or relationship, 1–3 identity-bearing forms, dominant axis, native paper-compatible palette, intended quiet-paper share, cluster location, and optional wording. The metaphor must simplify the scene rather than add unrelated symbolism.

## 视觉编译规则

- Remove all photographic pixels. Reconstruct only the semantic minimum with original ink, torn-paper, cut-paper, xerox, relief-print, or sparse geometric marks.
- Remove 65–90% of source detail. Preserve no more than the 1–3 forms needed to carry the proposition, tension, and metaphor. Merge repeated objects and textures into broad shapes or one directional trace.
- Reserve 68–85% of the page as genuinely quiet warm paper. Concentrate the illustrative vignette and dense texture into a controlled 15–32% field. Authorial typography may deliberately cross, leave, interrupt, or disperse beyond that field when doing so strengthens the proposition, while the overall figure–ground relationship must still preserve the intended quiet space.
- Use one primary illustration grammar and at most one restrained supporting texture. Keep the result flat, matte, scanned, and authorial rather than glossy or cinematic.
- Standard accent mode uses one vivid source-resonant hue as a small structural anchor plus neutral paper inks. It must derive from the thesis and alter balance or meaning.
- If and only if the user explicitly requests `单色块模式`, use exactly one saturated flat color block as the sole chromatic field, with warm paper and neutral ink only. The block must be one source-derived counterform or structural mass, not a swatch, gradient, outline, or decorative sticker.
- Treat text as fully free authorial material and decide freely whether the work needs it. Do not impose a preset language, word count, character count, copy length, type voice, hierarchy, or legibility threshold. Also do not preset font family or consistency, alignment, baseline, direction, placement, color relationship, degree of completion, or role. Use English, Chinese, bilingual material, invented language, marks, fragments, repeated words, long passages, quotation, private notation, or no text according to the strongest expression.
- Text may act as caption, countervoice, title, interruption, rhythm, architecture, surface, field, path, or the primary subject. It may be tiny, oversized, cropped, scattered, stacked, rotated, curved, obscured, fragmented, or overwritten; it may use one type voice or many; and it may enter, leave, overlap, hide behind, or reshape the illustration. Its only decision rule is that wording, material presence, and arrangement deepen the proposition, tension, metaphor, or interpretive opening. Never default to a neat caption merely because text is present.

## 硬性禁止项

Reject retained photo pixels, filters, photorealistic fragments, a descriptive full scene, multiple propositions, multiple metaphors, crowded illustration detail, purposeless decoration spread across quiet paper, more than one primary illustration grammar, multiple bright hues, arbitrary color blocks, gradients, detached swatches, commercial advertising hierarchy, generic symbols, icons, collage kits, lifted-paper shadows, glossy mockups, 3D, cinematic lighting, logos, UI, QR codes, signatures, and watermarks. Accidental tool-generated gibberish is a failure only when it was not deliberately chosen as authorial invented language, marks, or fragments.

## 质量检查

Confirm no photographic pixel remains; 65–90% of detail is removed; exactly one proposition, one tension, and one source-grounded metaphor are legible; 68–85% of the page is quiet warm paper; illustrative material retains a controlled hierarchy; no more than one primary illustration grammar and one support texture are present; standard mode has one structural accent, or explicit `单色块模式` has exactly one saturated flat block; every typography decision is purposeful under the free Typography Director rather than forced into a preset; and scene identity survives through the semantic minimum rather than literal depiction.

Regenerate at most once when a hard failure retains photography, loses the thesis, crowds quiet paper, adds competing metaphors or colors, misuses `单色块模式`, or produces accidental text with no chosen authorial purpose. Correct only that failure.

## 交付要求

Deliver exactly one final zine image through the host's native delivery path, followed by a compact rationale naming the proposition, tension, metaphor, quiet-paper share, and accent mode. Do not disclose the private input path or full prompt unless asked.
