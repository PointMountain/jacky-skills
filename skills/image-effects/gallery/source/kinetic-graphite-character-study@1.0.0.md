---
id: kinetic-graphite-character-study
version: 1.0.0
title_en: Kinetic Graphite Character Study
title_zh: 动势石墨人物速写
summary_en: Redraw one person as a loose monochrome graphite character study with recognizable identity, pressure-varied searching contours, irregular structural hatching, blocked-in hair masses, and purposeful unfinished paper.
summary_zh: 将单人照片重绘为松散的黑白石墨人物速写，保留身份与姿态，以粗细压力变化明显的探索线、不规则结构排线、概括发块和有意识的未完成纸面表现手绘感。
category: portrait
execution_kind: host-image-generation
input_mode: image
input_min: 1
input_max: 1
input_formats: jpeg,png
output_count: 1
preview: assets/previews/kinetic-graphite-character-study.png
source_repository: ConardLi/garden-skills
source_revision: aaf9a82f5efd73e87cc0998edc398e75bfc35901
source_paths: skills/gpt-image-2/references/avatars-and-profile/style-transfer-selfie.md,LICENSE
source_sha256s: 67021faabdbd9e5d5db6851eb2e5bc6a650a76ef399a4f0949fdae0f93989461,1126322e2cc8d165adc4c792eeb195717de2bcc7b39be1ce77959d78e87ef685
source_license_spdx: MIT
source_license_url: https://github.com/ConardLi/garden-skills/blob/aaf9a82f5efd73e87cc0998edc398e75bfc35901/LICENSE
source_license_notice: references/licenses/conardli-garden-skills-mit.txt
adaptation_notice: Adapts the pinned single-image style-transfer workflow into a monochrome graphite character study with pose preservation, gesture-aware framing, explicit mark hierarchy, private-input handling, and one targeted retry.
preview_origin: Text-only image generation of a fictional adult urban courier in an original pose; not based on a real person, character, brand, or third-party image.
preview_author: wangjs-jacky
preview_license_spdx: CC-BY-4.0
preview_sha256: fb70bd6a65adbdf66a64225db4da442934e72ad8cf45be2d5a78011d52513cbb
---

## 适用场景

Transform exactly one supplied image whose intentional primary subject is one person into exactly one hand-drawn monochrome graphite character study. Preserve the subject's identity, expression class, pose, body proportions, clothing silhouette, and movement logic while replacing every source pixel with authored pencil marks on warm-white paper. The result may be a close portrait, half-body study, or full figure according to the source; it is never a fixed bust template, photo filter, polished comic panel, or rendered scene.

The visual hierarchy is fixed: one readable subject, one dominant gesture line, four visibly separated graphite levels, 45–70% quiet paper, and no color. The page may remain spacious, but the subject must not become clean digital line art: pressure changes, dry paper-tooth breaks, partial searching lines, irregular structural hatching, and selective unfinished passages must remain physically visible while the face, hands, and joint connections stay coherent.

## 输入契约

Require exactly one JPEG or PNG from the current request. Reject zero images, multiple images, unsupported formats, or a source without one intentional primary person. Do not infer an attachment from conversation history or scan local folders.

Treat the supplied image as private task input. Send only the final compiled prompt and the required image to the host-native image capability. Do not browse for substitutes, commit the source, expose its local path, redistribute it, or retain additional copies. A continuation must reuse the original supplied image rather than the previous generated result.

Before generation, build a compact Character and Gesture Map containing: primary subject count; face silhouette; feature spacing; age range; gender presentation; hair mass and rhythm; expression class; gaze; shoulder and hip axes; limb directions; hand visibility; clothing silhouette; one defining garment, accessory, or prop; and the dominant action curve. Select 5–7 recognition anchors from those observations. Preserve ethnicity and stable visible traits without inventing an identity or biography.

If the source is a screenshot or contains interface chrome, captions, borders, other pictures, passersby, reflections, or background people, treat them as disposable context. Reconstruct only the intentional person and any explicitly requested handheld prop.

## 视觉编译规则

### Composition and gesture

- Choose portrait, half-body, or full-body framing from the source so the defining pose remains truthful. Do not force every input into the same crop.
- Keep one dominant gesture line running through the head, torso, and weight-bearing or leading limb. Preserve shoulder and hip counter-angle, balance, foreshortening, gaze direction, and the action's center of gravity.
- Use an asymmetrical page placement with 45–70% quiet warm-white paper. Let selected hair, garment, or limb edges approach the page boundary when that strengthens motion, but do not crop away identity anchors or required hands and feet.
- Remove the photographic background. Permit only 2–5 faint construction arcs, erased starts, or detached graphite masses that reinforce the source movement; they must not rebuild a room, street, landscape, or frame.

### Graphite mark hierarchy

- Use graphite pencil only, from pale construction marks to dense dark graphite. No color, ink wash, charcoal-black fill, digital grayscale painting, or smooth airbrush shading.
- Maintain four physically distinct mark levels: near-invisible abandoned construction lines; dry broken fine description; pressure-sensitive medium structural contours; and rare thick blunt graphite accents at focal overlaps such as hair roots, upper eyelids, nostrils, mouth slit, collar, torso compression, or the weight-bearing side. The darkest accents should read roughly 3–5 times thicker than the faintest construction marks at normal viewing size.
- Make each important contour change pressure within the stroke: a pale or porous start, a darker swelling turn at the structural decision, and a broken or tapered exit. Allow the paper tooth to interrupt the graphite. Do not use uniform line width, mechanically smooth curves, technical-pen edges, or flawless product geometry.
- Model form primarily with irregular directional hatching and limited cross-hatching that wrap around planes. Lines within one hatch family share a broad direction but vary naturally in length, spacing, angle, curvature, pressure, and completion. Some stop early, cross, fade, or leave paper gaps. Do not use ruler-even bundles, smooth gray fill, or an all-over pencil-filter texture.
- Keep a few visible corrections, partial doubled contours, overshoots, broken edges, and incomplete passages around structural turns such as the jaw, hand, shoulder, garment edge, prop, and movement path. Let contours appear, fade, and restart. These marks must look selectively observed rather than scattered as uniform noise.
- Protect the face, fingers, and important joint connections from stray lines. Eyes share one perspective plane, hands have coherent finger counts, limbs connect, and foreshortened forms remain readable.

### Face, hair, and selective completion

- Keep the face recognizable through proportion, silhouette, feature spacing, expression, and a few decisive dark anchors rather than complete realistic rendering. Simplify the upper eyelid to one pressure-varied stroke, the lower lid to a pale broken fragment, the pupil to a small irregular dark shape, the nose bridge to a faint partial indication, the nostril base to short graphite wedges, and the mouth to one broken slit with a small lower-lip shadow.
- Give the face volume with separated irregular hatch islands at the brow and eye socket, shadow side of the nose, cheekbone, beneath the nose and lower lip, jaw turn, and jaw-to-neck transition. Leave paper between those islands. The jaw-to-neck shadow may combine several broader blunt strokes with lighter crossed lines; do not leave the face as empty clean outline, but do not fill it with photographic skin shading.
- Treat hair as approximately 5–8 rapidly blocked-in masses, never as individually rendered strands or polished manga spikes. Establish the silhouette with broken pressure-varied strokes, add only a few broad directional marks inside each mass, and concentrate repeated graphite at roots and overlaps. Leave portions of the masses as paper and let tips break away unfinished.
- Preserve a source-appropriate crop, but favor the loose observational completion gradient validated by the pose: face and visible hand most resolved; glasses, headphones, handheld prop, jaw, and neck secondary; clothing and lower body increasingly loose. Use long incomplete garment folds, pale abandoned construction lines near the head, jaw, hand, and shoulders, and let lower contours dissolve into paper.

### Identity and simplification

- Preserve 5–7 selected recognition anchors, including face shape, feature spacing, hair silhouette, expression, pose, and one garment, accessory, or prop.
- Translate skin, hair, and fabric into selective graphite structure instead of photographic texture. Keep natural asymmetry and age cues while avoiding plastic beauty retouching, realistic pores, glossy eyes, fully rendered lips and teeth, strand-by-strand hair, or uniformly completed surfaces.
- Simplify secondary clothing detail into a few fold families aligned with tension and gravity. Do not invent ornate costume features, logos, weapons, jewelry, or cultural markers absent from the source.
- For partially hidden limbs, preserve honest occlusion rather than inventing extra visible anatomy. When a hand or foot is outside the source crop, do not fabricate it merely to make a full figure.

## 硬性禁止项

Hard failures: retained source pixels; color of any kind; phone or viewer interface; black letterboxing; captions, handwriting, signatures, pseudo-text, logos, brands, or watermarks; duplicate subjects; changed identity, age range, ethnicity, gender presentation, expression class, pose logic, hair length, or defining garment; copied background scenery; polished anime inking; cel shading; vector-clean outlines; photorealistic grayscale rendering; smooth digital painting; timid or uniform linework; perfectly clean traced contours; mechanically even hatching; strand-by-strand or uniformly detailed hair; an empty flat face without structural hatch islands; random scribbles through the face; malformed hands, feet, joints, or foreshortening; invented limbs or props; a rigid centered bust when the source action requires another framing.

## 质量检查

Before delivery, confirm all of the following:

- Exactly one supplied image produced exactly one fully redrawn person.
- The selected 5–7 recognition anchors, subject count, pose, gaze, and movement logic remain recognizable.
- The crop follows the source rather than forcing a fixed portrait template.
- One dominant gesture line and all four graphite levels are visibly present, with unmistakable pressure and thickness contrast.
- Directional hatching describes the eye socket, nose side, cheek, jaw, neck, and source-relevant body planes; spacing and pressure are irregular without becoming random noise.
- Hair reads as a few rapidly blocked-in masses with rough root accents, never as carefully rendered individual strands.
- Paper tooth, partial searching lines, broken contours, corrections, and unfinished lower edges remain visible; the result does not resemble clean digital tracing.
- Quiet warm-white paper occupies 45–70% of the canvas and no complete background survives.
- The image is strictly monochrome and contains no interface, border, text, logo, signature, or watermark.
- Face, hands, feet, joint connections, and foreshortening are structurally coherent wherever visible in the source.

If identity, pose, anatomy, crop, graphite hierarchy, paper share, or monochrome discipline fails, regenerate at most once with a correction limited to the failed item while preserving the same Character and Gesture Map.

## 交付要求

Deliver the single successful image through the host's native image-delivery path. Add a concise 1–3 sentence rationale in the user's current conversation language naming the preserved recognition anchors, dominant gesture, and graphite mark hierarchy. Do not reveal the private source path, full compiled prompt, or internal parameters unless explicitly requested.
