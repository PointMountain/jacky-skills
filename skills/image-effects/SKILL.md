---
name: image-effects
description: This skill applies reusable, versioned visual effects to one explicitly attached JPEG or PNG through host-native image generation. It should be used when a user asks to browse, select, or execute an effect from the bundled image-effects library.
---

# Image Effects

Apply one library effect to one image while preserving the selected effect version, input privacy, and host-native delivery.

## Resolve the effect

1. Treat `<id>@<version>` as the stable effect reference.
2. If the user provides no ID, read `references/INDEX.md` and recommend at most five relevant effects. Do not read every effect card to make recommendations.
3. If the user provides an ID without a version, resolve it only when the library contains exactly one version of that ID. Otherwise, ask the user to choose a version.
4. If the ID or version is unknown, return nearby choices from the index and stop. Do not execute a similar effect automatically.
5. After resolving an exact reference, read only its selected card under `references/effects/`. Treat that card as the complete behavior and provenance source of truth.

## Validate the input

Accept exactly one JPEG or PNG that the user explicitly attached to the current request.

- Do not scan attachment directories, prior messages, history, or nearby files to guess the input.
- Stop before invoking an image tool when the current request has zero images, multiple images, or an unsupported format.
- Create a temporary copy only when the host transport requires one. Delete that copy when the task ends, including after failure.
- Do not add the user's source image or private path to the effect library, Gallery, logs, or output metadata.

## Execute the effect

1. Compile the selected card's full rules together with the user's stated goal into the final image-generation prompt.
2. Use the host's native image-generation or image-editing tool with only that prompt and the explicitly attached image.
3. Keep the selected effect reference and subject constraints unchanged. If the tool errors or the result violates a hard quality rule, make at most one targeted retry that addresses the specific failure.
4. If no compatible image tool is available, return the complete final prompt for the user to copy and clearly state that no image was generated. Do not write a prompt file unless requested.

Do not implement a global lock, queue, or concurrency limit. Each requested effect output succeeds or fails independently under the host's own execution model.

## Deliver the result

Use the host's native image delivery path. When running in Happy and its native image delivery tool is available, send the generated image through that tool. Keep private paths, raw commands, and tool logs out of the final response.
