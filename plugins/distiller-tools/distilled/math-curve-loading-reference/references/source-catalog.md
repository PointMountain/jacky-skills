# Source Catalog

## Source snapshot

- Repository: <https://github.com/Paidax01/math-curve-loaders>
- Live gallery: <https://paidax01.github.io/math-curve-loaders/>
- Snapshot: `70f4e00a6d452532039ff7c2ccb4c379ec90c772`
- Stack: plain HTML, CSS, JavaScript, and SVG
- Shape: gallery, modal previews, formula notes, tunable controls, copyable snippets, and standalone demos
- License at capture time: none declared

Use the live gallery for visual selection. Use the repository only to understand curve families and parameter relationships. Reimplement from mathematical definitions when shipping code.

## Curve families in the gallery

| Family | Included variants | Character | Useful for |
| --- | --- | --- | --- |
| Custom rose trail | Original Thinking, Thinking Five, Thinking Nine | Braided floral orbit | Branded, expressive waiting states |
| Polar rose | Rose Orbit, Rose Curve, Rose Two/Three/Four | Symmetric petals | Calm loops with obvious rhythm |
| Lissajous | Lissajous Drift | Balanced crossing orbit | Compact first-paint loaders |
| Lemniscate | Lemniscate Bloom | Figure-eight continuity | Neutral, technical interfaces |
| Hypotrochoid | Hypotrochoid Loop, Three- to Six-Petal Spiral | Mechanical/spirograph motion | Tools and creative apps |
| Organic curves | Butterfly Phase, Cardioid Glow/Heart, Heart Wave | Recognizable organic silhouette | Friendly or expressive products |
| Open/compound paths | Spiral Search, Fourier Flow | Searching or flowing motion | Longer exploratory waits |

## Reusable animation model

Treat each curve as a function `point(progress, shapeState, config) -> {x, y}` where `progress` wraps to `[0, 1)`.

For particle `i` among `N` particles:

```text
tailOffset = i / (N - 1)
sampleProgress = headProgress - tailOffset * trailSpan
position = point(wrap(sampleProgress), shapeState, config)
fade = (1 - tailOffset)^gamma
radius = minRadius + fade * radiusRange
opacity = minOpacity + fade * opacityRange
```

Animate `headProgress` over a loop duration. Optional slow rotation and breathing should use separate durations so the motion does not feel mechanically synchronized.

## Paws Lissajous choice

Paws selected a compact 3:4 Lissajous curve:

```text
x(t) = centerX + amplitudeX * sin(3t + phase)
y(t) = centerY + amplitudeY * sin(4t)
```

The useful properties are:

- closed, centered path with balanced visual weight;
- enough crossings to feel distinctive at a small size;
- deterministic sampling for static fallback and runtime tests;
- easy control of aspect ratio, phase, density, trail span, and duration.

The shipped Paws loader uses 36 particles. That is a product-specific choice, not a source-repository default.

## Parameters worth exposing during exploration

- `particleCount`: density and perceived smoothness
- `trailSpan`: fraction of the curve occupied by the tail
- `durationMs`: head loop speed
- `pulseDurationMs`: breathing cadence
- `rotationDurationMs`: slow global rotation
- `strokeWidth`: background path prominence
- curve-specific frequency, phase, radius, amplitude, petal count, and scale

Do not expose all controls in production UI. Use them as design-time variables, then lock intentional values in the implementation and tests.
