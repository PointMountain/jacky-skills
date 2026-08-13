---
name: photo-to-styled-motion
description: "Turn a user portrait or photo into an identity-preserving styled motion clip, with a numbered Human-in-the-loop style gallery when the user has not chosen a look: create standalone candidates, build one selection sheet, generate and verify a MiniMax H3 MP4, then create a verified Android Motion Photo. Use for selfies, portraits, anime, manga, cinematic, graphic-novel, abstract, Live Photo, or motion-photo transformations."
---

# Photo To Styled Motion

Use `fast` mode when the user already chose a style. Otherwise use a numbered Human-in-the-loop `gallery` before video generation: generate the standalone style candidates, combine previews into one selection sheet, and let the user type a number or style name. An H3 submission is billable and always requires explicit confirmation for the exact batch.

## Required capabilities

- Use the host image generation/editing tool when available. Otherwise use the installed `gpt-image-2` skill according to its mode rules.
- Use `minimax-h3` from `PATH` for MiniMax H3. It reads credentials from Keychain; never print or persist the key.
- Use `ffmpeg` and `ffprobe` for media conversion and verification.
- Use [scripts/build_style_gallery.py](scripts/build_style_gallery.py) to create numbered selection sheets. It requires Pillow and outputs both the gallery and an exact ID-to-source mapping.
- Use the installed `android-live-photo` dependency for the standard Android Motion Photo output:

```sh
node "${CODEX_HOME:-$HOME/.codex}/skills/android-live-photo/scripts/convert_motion_photo.mjs" \
  --input final.mp4 \
  --output final-motion-photo.jpg
```

- Require the converter to report `validation: passed`. It preserves the MP4 bytes unchanged inside the JPEG. Do not duplicate or replace this converter with an ad hoc wrapper.
- In Happy, send the gallery and selected first-frame preview with `mcp__happy__send_image`, and every MP4 with `mcp__happy__send_file`. Do not flood the chat with every standalone candidate unless the user requests close inspection.

## Gallery interaction rule

After sending a numbered style gallery, ask for selection in ordinary text only. Do not use structured answer tools, XML `<options>`, buttons, chips, menus, or a repeated text list of every style. The gallery already contains the choices.

Use one short prompt such as: `请输入图片中的编号或风格名，例如 02。`

Accept a bare integer (`2`), zero-padded ID (`02`), exact display label, or unique preset slug. Resolve it through the generated `.mapping.json`. If the input is missing, ambiguous, or invalid, ask the user to type a valid number or style name in ordinary text; do not fall back to structured options.

## Workflow

### 1. Inspect the input

Use the exact user-provided attachment path. Inspect dimensions, format, identity anchors, pose, visible objects, and background.

If the input may be a motion photo, check for embedded `ftyp`/`moov` data. Extract frames only when useful for reference. Keep the original file when Honor-style dynamic JPEG output may be requested; its vendor metadata and private MP4 `uuid` box are needed for best compatibility.

### 2. Give one complete brief

Before generating any image or submitting a video, read [references/style-presets.md](references/style-presets.md) and give one compact brief containing:

- the available styles and a context-aware recommendation;
- the mode: `fast` (one chosen first frame, no review pause) or `gallery` (all available presets as numbered static candidates, then selection);
- the exact static batch in `gallery` mode, including candidate count and whether the active image backend is billable; obtain confirmation before a billable multi-image static batch;
- the exact paid batch: task count, resolution, duration, current public price estimate when available, actual invoice controls, and no automatic paid retry;
- output chain: verified MP4 followed by a standard Android Motion Photo.

Offer a single combined decision. For example: `日系胶片电影，极速模式，确认 1 个 768P/5 秒付费任务`.

If the user explicitly invokes this skill and chooses a style plus paid confirmation in that one response, continue without further human checkpoints: generate the first frame, inspect it, submit once, verify the MP4, and create the Motion Photo. A prior confirmation covers only the exact described batch.

Use `fast` when the user explicitly chooses a style, including in the same message that invokes the skill. Use `gallery` when no style is selected or the user asks to compare, browse, or choose. Do not manufacture a style-selection pause in `fast` mode.

### 3. Run style selection or generate the chosen first frame

Always generate one standalone image per style; never ask an image model to draw the gallery itself. This keeps every candidate eligible to become the video first frame. Preserve identity anchors explicitly:

- face shape and feature spacing
- age, ethnicity, and body proportions
- hairstyle and key accessories
- pose, hand placement, phone/props, and framing
- background layout unless the preset intentionally changes it

Avoid title text, captions, dates, logos, watermarks, extra people, extra fingers, and duplicated props.

In `fast` mode, generate and inspect the one selected style, then continue without a review pause when it passes.

In `gallery` mode:

1. Read the stable IDs from [references/style-presets.md](references/style-presets.md).
2. Generate every available preset as a standalone candidate. Keep the same ID, slug, identity invariants, crop, and output dimensions across the batch. If the static image backend is billable, submit only the user-confirmed candidate count and never retry a failed candidate without renewed approval.
3. Inspect all candidates. Exclude a failed candidate instead of showing misleading work, but never renumber the remaining styles. Regenerate a static candidate only when the image tool permits it and the user has not restricted static-generation cost.
4. Write a manifest containing `id`, `slug`, `label`, and the original candidate image path. Build one numbered gallery:

```bash
python3 scripts/build_style_gallery.py \
  --manifest style-candidates.json \
  --output style-gallery.jpg \
  --columns 3
```

Manifest shape:

```json
{
  "candidates": [
    {"id": 1, "slug": "japanese-cinema-film", "label": "日系真人电影", "image": "candidate-01.jpg"},
    {"id": 2, "slug": "handdrawn-anime-film", "label": "手绘动画电影", "image": "candidate-02.jpg"}
  ]
}
```

5. Inspect the gallery for readable numbers, labels, correct crops, and one-to-one mapping. Send only this gallery first, then use the ordinary-text prompt defined in **Gallery interaction rule**. Do not repeat the full style list outside the image.
6. Stop before every H3 call. The style selection and paid-video confirmation may be combined in the user's reply only if the exact task count, resolution, duration, and no-retry policy were already stated.
7. Resolve the typed number or style name through the generated `.mapping.json`. Show or send the selected original candidate for confirmation when useful. Never crop a tile from the gallery and never use the gallery image as an H3 first frame.

Keep the manifest, mapping, gallery, all standalone candidates, and selected candidate beside the task artifacts for reproducibility.

### 4. Confirm billable video generation

MiniMax `create` and `create-json` are billable. Before every batch, state:

- number of tasks
- resolution and duration per task
- approximate public price when a current reference is available, explicitly noting the actual invoice controls
- that each selected style gets one submission and no automatic regeneration

Do not submit until the user explicitly confirms the paid calls. The confirmation may be given in the complete brief in step 2; do not ask again when it already covers the exact task.

In `gallery` mode, a style number alone is not paid confirmation unless the user had already explicitly confirmed the exact H3 batch. Never infer paid approval from viewing or selecting a static style.

### 5. Build and submit H3 requests

Convert the selected candidate to a high-quality JPEG when inline PNG data would be unnecessarily large.

Use [scripts/build_h3_request.mjs](scripts/build_h3_request.mjs):

```bash
node scripts/build_h3_request.mjs \
  --image candidate.jpg \
  --prompt-file motion-prompt.txt \
  --output request.json \
  --resolution 768P \
  --duration 5 \
  --seed 42
```

Default to one `first_frame` image. Use first/last frames only when the user has approved both exact endpoint images; forcing the same image at both ends can create mechanical loops.

Prompt for restrained motion unless the user asks otherwise: natural breathing, one blink, subtle gaze/head/prop motion, fixed camera, stable identity, hands, glasses, props, linework, and palette. Add preset-specific environmental motion.

Submit exactly once per confirmed style:

```bash
minimax-h3 create-json request.json --confirm-cost
```

Record every task ID. Poll only those IDs. Never create a replacement task automatically after a failure or disappointing result.

### 6. Download and verify MP4

Download a succeeded task with the same CLI. Run:

```bash
node scripts/verify_video.mjs output.mp4
```

Verification must confirm:

- readable MP4 container
- H.264 video stream
- nonzero dimensions and duration
- AAC audio stream by default; use `--allow-silent` only when the user explicitly requested no audio
- full decode succeeds without errors

Inspect a contact sheet for identity, hands, props, black frames, style flicker, and scene drift. Send the MP4 only after verification.

### 7. Create standard Android Motion Photo

After every verified MP4, create the Motion Photo by default, unless the user requested MP4 only. Use the `android-live-photo` converter from Required capabilities:

```sh
node "${CODEX_HOME:-$HOME/.codex}/skills/android-live-photo/scripts/convert_motion_photo.mjs" \
  --input final.mp4 \
  --output final-motion-photo.jpg
```

Do not treat a standalone MP4 as a Live Photo. The Motion Photo is the single untouched `.jpg` binary containing a JPEG cover, standard Google Motion Photo XMP, and the byte-identical source MP4. Require `validation: passed` before delivery.

Do not send this JPEG through an image renderer or editor. If the client cannot attach arbitrary binaries, provide an untouched archive or verified download link. State precisely that social platforms supporting standard Android Motion Photos may recognize it, while Honor Gallery may not register an imported generic Motion Photo as native.

### 8. Optional GIF

Explain before conversion: GIF has no audio, usually has fewer colors, and is typically larger than an efficient MP4 for equivalent motion.

Use [scripts/export_gif.sh](scripts/export_gif.sh):

```bash
scripts/export_gif.sh input.mp4 output.gif 10 480
```

Defaults are 10 fps and 480 px wide. The script uses a two-pass palette workflow. Verify the GIF is animated and nonempty, and report its size beside the MP4 size; GIF is often much larger. In Happy, there is no general binary/GIF attachment channel; provide a download link when cross-device review is required.

### 9. Optional Honor-native dynamic JPEG

Use this only when the user explicitly requests an Honor-native format and supplies an original Honor motion-photo JPEG. It is distinct from the standard Android Motion Photo produced in step 7.

Requirements:

- an original Honor motion-photo JPEG containing `LivePhoto`, `HiHonor_OfflineData`, an embedded MP4, a private `uuid` box, and a 60-byte footer
- a selected cover JPEG
- the verified final H3 MP4

Build with [scripts/build_honor_motion.mjs](scripts/build_honor_motion.mjs):

```bash
node scripts/build_honor_motion.mjs \
  --original original-honor-motion.jpg \
  --cover selected-cover.jpg \
  --video final.mp4 \
  --output styled-motion.jpg \
  --copy-honor-uuid
```

The script preserves/injects Honor `LivePhoto` metadata, writes `HiHonor_OfflineData`, embeds the H3 MP4, optionally copies the original Honor private `uuid` box, and updates the `LIVE_<length>` footer.

Verify with [scripts/verify_honor_motion.mjs](scripts/verify_honor_motion.mjs). The verifier must extract and decode the embedded MP4 and confirm the footer length.

Do not send this output through an image-rendering channel that recompresses JPEG; recompression removes the trailing video. Deliver it as an untouched binary attachment, ZIP, or verified direct-download link. If the client only supports image display, also show the cover separately, but state that it is only a preview.

## Output policy

- Primary: verified MP4 with audio.
- Default companion: verified standard Android Motion Photo created with `android-live-photo`.
- Optional: Honor-native dynamic JPEG when an original Honor motion photo is available and the user specifically requests it.
- Optional: silent GIF derived from the final MP4.
- Keep prompts and request JSON beside task artifacts for reproducibility.
- Report task IDs, specs, actual usage returned by MiniMax, and whether retries occurred.
- Describe Motion Photo compatibility narrowly: supporting social platforms may recognize standard Android Motion Photos; Honor Gallery may not register an imported generic Motion Photo as native.
