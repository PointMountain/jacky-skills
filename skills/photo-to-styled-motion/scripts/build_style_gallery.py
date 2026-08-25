#!/usr/bin/env python3

# Pillow provides deterministic image fitting plus CJK font rendering for the
# numbered gallery; this is the repository's documented Python ecosystem case.

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CJK_FONT_PATHS = (
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
)


def fail(message: str) -> None:
    raise SystemExit(f"build_style_gallery: {message}")


def load_font(size: int, cjk: bool = False) -> ImageFont.FreeTypeFont:
    candidates = list(CJK_FONT_PATHS) if cjk else [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    fail("no suitable font found")


def load_manifest(path: Path) -> list[dict]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read manifest: {error}")

    candidates = value.get("candidates") if isinstance(value, dict) else value
    if not isinstance(candidates, list) or not candidates:
        fail("manifest must contain a non-empty candidates array")

    required = {"id", "slug", "label", "image"}
    seen_ids = set()
    seen_slugs = set()
    normalized = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict) or not required.issubset(item):
            fail(f"candidate {index + 1} requires id, slug, label, and image")
        candidate_id = item["id"]
        if not isinstance(candidate_id, int) or candidate_id < 1 or candidate_id > 99:
            fail(f"candidate {index + 1} id must be an integer from 1 to 99")
        if candidate_id in seen_ids:
            fail(f"duplicate candidate id: {candidate_id}")
        slug = str(item["slug"]).strip()
        label = str(item["label"]).strip()
        if not slug or not label:
            fail(f"candidate {candidate_id} has an empty slug or label")
        if slug in seen_slugs:
            fail(f"duplicate candidate slug: {slug}")

        image_path = Path(str(item["image"])).expanduser()
        if not image_path.is_absolute():
            image_path = (path.parent / image_path).resolve()
        if not image_path.is_file():
            fail(f"candidate {candidate_id} image not found: {image_path}")

        seen_ids.add(candidate_id)
        seen_slugs.add(slug)
        normalized.append(
            {
                "id": candidate_id,
                "slug": slug,
                "label": label,
                "image": str(image_path),
            }
        )

    return sorted(normalized, key=lambda candidate: candidate["id"])


def make_tile(
    candidate: dict,
    width: int,
    image_height: int,
    label_height: int,
    number_font: ImageFont.FreeTypeFont,
    label_font: ImageFont.FreeTypeFont,
) -> Image.Image:
    with Image.open(candidate["image"]) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        preview = ImageOps.fit(
            source,
            (width, image_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.42),
        )

    tile = Image.new("RGB", (width, image_height + label_height), "#111317")
    tile.paste(preview, (0, 0))
    draw = ImageDraw.Draw(tile)

    number = f"{candidate['id']:02d}"
    number_box = draw.textbbox((0, 0), number, font=number_font)
    badge_width = number_box[2] - number_box[0] + 34
    badge_height = number_box[3] - number_box[1] + 24
    draw.rounded_rectangle(
        (18, 18, 18 + badge_width, 18 + badge_height),
        radius=8,
        fill="#111317",
    )
    draw.text((35, 24 - number_box[1]), number, font=number_font, fill="#FFFFFF")

    label = candidate["label"]
    label_box = draw.textbbox((0, 0), label, font=label_font)
    label_width = label_box[2] - label_box[0]
    if label_width > width - 40:
        fail(f"candidate {candidate['id']} label is too long for the tile: {label}")
    label_x = (width - label_width) // 2
    label_y = image_height + (label_height - (label_box[3] - label_box[1])) // 2 - label_box[1]
    draw.text((label_x, label_y), label, font=label_font, fill="#FFFFFF")
    return tile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a numbered style-selection gallery from standalone candidate images."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mapping-output", type=Path)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--tile-width", type=int, default=560)
    parser.add_argument("--tile-ratio", default="3:4")
    parser.add_argument("--jpeg-quality", type=int, default=92)
    args = parser.parse_args()

    if args.columns < 1 or args.columns > 6:
        fail("--columns must be from 1 to 6")
    if args.tile_width < 240 or args.tile_width > 1200:
        fail("--tile-width must be from 240 to 1200")
    try:
        ratio_width, ratio_height = (int(part) for part in args.tile_ratio.split(":"))
    except (TypeError, ValueError):
        fail("--tile-ratio must look like 3:4")
    if ratio_width < 1 or ratio_height < 1:
        fail("--tile-ratio values must be positive")
    if args.jpeg_quality < 70 or args.jpeg_quality > 100:
        fail("--jpeg-quality must be from 70 to 100")

    candidates = load_manifest(args.manifest.resolve())
    image_height = round(args.tile_width * ratio_height / ratio_width)
    label_height = max(84, round(args.tile_width * 0.16))
    gap = max(12, round(args.tile_width * 0.025))
    margin = gap
    rows = math.ceil(len(candidates) / args.columns)
    canvas_width = margin * 2 + args.columns * args.tile_width + (args.columns - 1) * gap
    canvas_height = margin * 2 + rows * (image_height + label_height) + (rows - 1) * gap
    canvas = Image.new("RGB", (canvas_width, canvas_height), "#E9EBEF")

    number_font = load_font(max(38, round(args.tile_width * 0.09)))
    label_font = load_font(max(28, round(args.tile_width * 0.058)), cjk=True)
    for index, candidate in enumerate(candidates):
        row, column = divmod(index, args.columns)
        tile = make_tile(
            candidate,
            args.tile_width,
            image_height,
            label_height,
            number_font,
            label_font,
        )
        x = margin + column * (args.tile_width + gap)
        y = margin + row * (image_height + label_height + gap)
        canvas.paste(tile, (x, y))

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        canvas.save(output_path, "JPEG", quality=args.jpeg_quality, optimize=True)
    elif suffix == ".png":
        canvas.save(output_path, "PNG", optimize=True)
    else:
        fail("--output must end in .jpg, .jpeg, or .png")

    mapping_path = (
        args.mapping_output.expanduser().resolve()
        if args.mapping_output
        else output_path.with_suffix(".mapping.json")
    )
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping = {
        "gallery": str(output_path),
        "candidates": candidates,
    }
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "mapping": str(mapping_path),
                "candidates": len(candidates),
                "columns": args.columns,
                "rows": rows,
                "width": canvas_width,
                "height": canvas_height,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
