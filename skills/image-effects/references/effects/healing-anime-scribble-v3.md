---
id: healing-anime-scribble-v3
version: 1.0.0
title_en: Healing Anime Scribble
title_zh: 治愈系潦草淡彩
summary_en: Redraw one portrait as an airy anime construction sketch with dense searching lines, sparse pale color, and quiet warm paper.
summary_zh: 将一张人物照片重绘为留白通透的动漫结构草图，以密集探索线条、稀薄淡彩和暖白纸张为核心。
category: portrait
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/healing-anime-scribble-v3.jpg
source_repository: ConardLi/garden-skills
source_revision: aaf9a82f5efd73e87cc0998edc398e75bfc35901
source_paths: skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md,LICENSE
source_sha256s: 67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461,1126322e2cc8d165adc4c792eeb195717de2bcc7b39be1ce77959d78e87ef685
source_license_spdx: MIT
source_license_url: https://github.com/ConardLi/garden-skills/blob/aaf9a82f5efd73e87cc0998edc398e75bfc35901/LICENSE
source_license_notice: references/licenses/conardli-garden-skills-mit.txt
adaptation_notice: Preserves the one-photo anime construction sketch behavior and adds fixed v3 ratios, host-neutral delivery, privacy gates, and one targeted retry.
preview_origin: Text-only image generation of a fictional young adult with glasses, not based on a real person.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: 70a3c534832532faed62cb80816df56002382cb661b51d2077d7eab429760daf
---

## 适用场景

Act as the Healing Anime Scribble v3 visual compiler. Transform exactly one supplied real-world photo into exactly one raw anime construction sketch. This is a complete redraw, never a photo filter or a scene-preserving style transfer.

The visual hierarchy is fixed: 80–90% of visible marks are graphite or black-ink strokes, pale translucent color covers only 8–16% of the canvas, and 55–70% remains exposed warm-white paper. These measures describe different visual layers and may overlap. Text mode is never: never render captions, handwriting, signatures, letters, pseudo-text, logos, watermarks, or interface copy, even when the source contains them.

The intentional primary subject count is one. Ignore passersby, reflections, screens, posters, and distant crowd clutter unless the user explicitly makes them primary.

## 输入契约

Treat the supplied photo plus a request to create or continue as consent for this image-generation task. Use that photo only as private task input. Send only the final prompt and required reference image to the generation service. Do not browse for substitutes, save extra copies, commit the source, redistribute it, expose its local path, or use it outside this request. A temporary or output path required for native inline delivery is allowed. A continuation must reuse the original uploaded photo, not the previous generated result.

When source or input fidelity is configurable, use low or standard fidelity so identity anchors guide the redraw without preserving photographic skin, lighting, or camera rendering.

Before generation, build a compact Character Map: intentional primary subject count, face silhouette, feature spacing, age range, gender presentation, ethnicity, glasses geometry, hair length and volume, expression class, pose, key garment or prop, and 3–5 source color roles.

Preserve recognition through 4–6 identity anchors selected from face shape, hair silhouette and rhythm, glasses geometry, expression, pose, and one key garment, accessory, or prop. Keep age range, gender presentation, hair length, gaze direction, primary subject count, and defining geometry stable. Do not preserve identity through photographic skin texture, realistic eyeballs, detailed lips or teeth, exact lighting, or camera artifacts.

For a non-human portrait, preserve species or object identity, anatomy or construction, primary count, relative scale, and defining silhouette without adding a human face.

## 视觉编译规则

### Composition

- Use one coherent portrait study on warm-white uncoated paper, never a grid, diptych, before/after pair, framed photo, or complete scene.
- Default to an airy vertical character study; use another ratio only when necessary to preserve the subject honestly. Never stretch the source.
- Center a head-and-shoulders or half-body figure slightly above the middle. Keep the face readable and let the lower torso, sleeves, hands, and outer contour dissolve into unfinished construction marks and paper.
- Remove the photographic background. At most 2–4 detached, source-derived brush flecks may remain as atmosphere, but they must not reconnect into a room, street, landscape, or full wash.

### Drawing language

- Build the face as calm, simplified anime geometry: a clean pale face plane, economical jaw, clear enlarged line-art eyes or closed crescent arcs that match the source expression, a tiny one- or two-mark nose, and a simple one- or two-line mouth. Keep eyes, mouth, and glasses unobstructed. No stray scribble may cross these critical features.
- Make dense searching contours the dominant language everywhere else: repeated graphite corrections, broken black-ink edges, looping flyaways, transparent dark masses, long exploratory arcs, incomplete ellipses, erased starts, and interrupted hatching.
- Concentrate the strongest controlled chaos around hair, outer silhouette, clothing seams, straps, accessories, and props. Hair and garment line density must visibly overwhelm the calm face.
- Leave the lower silhouette conspicuously unfinished. Lines may overshoot, double back, fade, or stop abruptly, but anatomy and object structure must remain coherent. Hands keep the correct finger count, glasses align, facial features share one head plane, and limbs connect.
- Avoid vector-clean outlines, polished line art, uniform contour weight, tidy cel-shading, minimalist dot faces, or decorative scribbles spread evenly across the page.

### Color and paper

- Restrict pale color to 8–16% of the canvas. Use 2–4 quiet colors derived from the source, such as diluted peach, dusty blue, muted coral, amber, rose, or sage. Paper and black or graphite marks must dominate immediately at thumbnail size.
- Apply color as incomplete translucent blooms, dry-brush skips, narrow garment fragments, faint cheek warmth, and tiny detached flecks. Leave paper gaps inside hair, clothing, accessories, and props.
- Preserve 55–70% broad, quiet warm-white paper. No continuous background wash, full-color fill, realistic watercolor modeling, photographic skin, complete scenery, gradients, or arbitrary neon accents.

## 硬性禁止项

Hard failures: retained source pixels; photorealism; realistic skin, eyes, lips, teeth, or lighting; photo-to-watercolor filtering; a complete background or scene; polished full-color illustration; sparse or timid linework; chaotic marks through eyes, mouth, or glasses; duplicate primary subjects; changed identity, hair length, gender presentation, pose logic, or key prop; malformed anatomy; viewer or phone UI; captions, handwriting, signatures, letters, pseudo-text, logos, or watermarks.

## 质量检查

Before delivery, confirm all of the following:

- One source photo produced one illustration.
- The chosen 4–6 identity anchors remain recognizable.
- Graphite and ink provide 80–90% of visible mark energy.
- Pale color remains within 8–16% coverage.
- 55–70% is quiet warm-white paper.
- The calm simplified anime face is protected while hair, clothing, accessories, and outer contours carry dense searching lines.
- The lower silhouette remains unfinished.
- There is no complete scenery, retained source pixel, UI, or text of any kind.
- Anatomy and object geometry are coherent.

If the result becomes a photo filter, realistic watercolor portrait, tidy finished anime illustration, timid sketch, different subject, text-bearing image, or has failed hands, glasses, identity, or subject count, regenerate at most once with a targeted correction while preserving the same Character Map.

## 交付要求

Send every successful output through the host's native image delivery path. Do not hard-code a host-specific invocation.

Then add a concise 1–3 sentence rationale in the user's current conversation language naming the preserved identity anchors, source-derived pale palette, and balance of dense searching linework, sparse color, and quiet paper. Do not reveal the full prompt, private source path, or detailed parameters unless explicitly requested.
