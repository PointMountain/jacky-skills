# Style Presets

Use these as prompt modules. Always prepend the input-specific identity, pose, prop, composition, and background invariants.

## Stable gallery order

Use these IDs unchanged in Human-in-the-loop galleries. Never renumber a subset; omitted styles leave gaps so a user's selection always maps to the same preset.

| ID | Slug | Display label |
|---:|---|---|
| 01 | `japanese-cinema-film` | 日系真人电影 |
| 02 | `handdrawn-anime-film` | 手绘动画电影 |
| 03 | `90s-cel-animation` | 90年代赛璐璐 |
| 04 | `seinen-manga-bw` | 黑白青年漫画 |
| 05 | `cyberpunk-graphic-novel` | 赛博朋克绘本 |
| 06 | `abstract-screenprint-collage` | 抽象丝网拼贴 |
| 07 | `ink-wash-portrait` | 水墨肖像 |
| 08 | `vintage-editorial-film` | 复古杂志胶片 |
| 09 | `cinematic-realism` | 电影写实 |

## `japanese-cinema-film`

Contemporary Japanese live-action cinema still; natural photographic likeness; restrained 35mm film grain; soft practical lighting; quiet observational mood; realistic skin texture; muted, balanced color; gently lifted blacks; shallow but believable depth of field. Preserve the original location and adult proportions. This is a photographic film look, not animation.

Animation: one natural breath, one blink, a small gaze shift, minute fabric movement, and subtle practical-light variation. Fixed camera, stable face, hands, glasses, and scene geometry.

## `handdrawn-anime-film`

High-fidelity Japanese animated feature-film frame; refined 2D hand drawing; soft variable pencil-and-ink contours; clean cel-painted skin and fabric; watercolor-gouache background texture; subtle film grain; nuanced adult facial acting. Preserve realistic facial proportions and recognizable identity. Avoid named studios/artists, oversized eyes, childlike proportions, 3D, and glossy vector rendering.

Animation: natural breathing, one blink, slight chin/gaze shift, millimetric prop movement, subtle cloth motion, fixed camera, stable linework and color.

Origin: derived from the gallery's style-transfer-selfie hand-drawn animation example plus the anime key-visual template, then adapted for identity-locked image-to-video. It was not originally a standalone gallery preset.

## `90s-cel-animation`

Premium 1990s hand-inked cel animation; confident dark contours; elegant two-step cel shading; hand-painted background; subtle analog grain and registration texture; sophisticated adult character design; restrained palette.

Animation: slow head tilt, one blink, breathing, subtle prop adjustment, gentle practical-light flicker. Avoid modern glossy anime and neon overload.

## `seinen-manga-bw`

Professional black-and-white adult manga splash image; precise likeness; controlled contour variation; feathered shadows; stable halftone screentones; sparse cross-hatching; crisp whites and deep blacks; pure grayscale.

Animation: limited restrained movement. Explicitly require stable screen-tone density with no shimmering or crawling patterns. This preset carries a higher flicker risk in video.

## `cyberpunk-graphic-novel`

High-end color graphic novel; bold clean ink contours; painterly cel shading; selective halftone; realistic adult proportions; cyan edge light and restrained magenta reflection while keeping the face warm and readable. Keep the original location recognizable; do not add armor, implants, or weapons unless requested.

Animation: rain trails, slow reflected-light drift, breathing, one blink, slight head and prop motion.

## `abstract-screenprint-collage`

Experimental editorial screen print, risograph, and cut-paper collage. Simplify the face into asymmetrical geometric planes; hair into jagged shards; clothing into overlapping paper shapes; background into sparse architectural bars, circles, silhouettes, and negative space. Use five dominant inks: warm peach, signal red, cobalt blue, carbon black, and off-white. No gradients or photorealistic skin.

Animation: paper-edge flutter, subtle registration drift, halftone movement, and shape parallax. Prefer graphic motion over realistic blinking. Keep key identity anchors readable.

## `ink-wash-portrait`

Contemporary East Asian ink-wash portrait; preserve recognisable adult likeness and realistic proportions; layered black and charcoal brushwork; soft mineral-gray washes; restrained cinnabar accent; generous paper texture and controlled negative space. Keep the source scene recognisable through simplified equipment silhouettes. Avoid calligraphy, seals, text, fantasy costumes, and decorative borders.

Animation: extremely restrained breathing and blink; ink wash blooms slowly only in the background, while face, glasses, body, and equipment outlines remain stable.

## `vintage-editorial-film`

Premium 1970s-1990s editorial film photograph; natural likeness; tactile 35mm grain; subtle flash or window-light falloff; realistic fabric and skin; slightly faded but balanced palette; authentic magazine portrait composition. Preserve the real location, clothing, pose, and adult proportions. No printed masthead, caption, borders, or fake magazine layout.

Animation: small breath and blink, minimal eye movement, quiet dust motes and practical-light fluctuation. Keep camera, framing, facial identity, and props stable.

## `cinematic-realism`

High-end live-action cinematic portrait; preserve the exact photographic identity, skin texture, pose, clothing, accessories, and location geometry; controlled key light, believable practical reflections, refined contrast, and subtle filmic color grade. No illustration treatment and no synthetic beauty-filter skin.

Animation: natural breathing, one blink, minute head or gaze shift, restrained fabric movement, and gentle environmental light change. Fixed camera and stable hands, glasses, props, and background.

## Selection guidance

- Best photographic identity fidelity: `cinematic-realism`, `japanese-cinema-film`
- Best illustrated identity fidelity: `handdrawn-anime-film`, `seinen-manga-bw`
- Best general H3 stability: `cinematic-realism`, `japanese-cinema-film`, `90s-cel-animation`
- Strongest scene transformation: `cyberpunk-graphic-novel`
- Least photorealistic: `abstract-screenprint-collage`
- Highest texture-flicker risk: `seinen-manga-bw`, `abstract-screenprint-collage`, `ink-wash-portrait`
