# Image Effects

Reusable, versioned image-effect cards for AI coding agents, plus a static Gallery for browsing the available recipes.

[中文说明](./README_CN.md) · [Gallery](https://wangjs-jacky.github.io/image-effects/)

## Install

```bash
npx skills add wangjs-jacky/image-effects
```

## Use

Attach one JPEG or PNG, then ask your agent:

```text
Use $image-effects effect healing-anime-scribble-v3@1.0.0 on my uploaded image.
```

The MVP intentionally contains one effect: `healing-anime-scribble-v3@1.0.0`. Effect IDs include a version so an existing recipe can remain stable while later revisions evolve independently.

## How it works

The Skill resolves the selected effect card, validates the attached image, compiles the card into an image-editing prompt, and hands that prompt to the host's native image-generation capability. Image bytes are processed by the host; this repository does not upload them to a separate service. The library has no global generation lock, so unrelated host jobs are not serialized by the Skill.

## Contributing an effect

1. Add one versioned card under `references/effects/` with its provenance and license fields.
2. Add a metadata-free JPEG or PNG preview under `assets/previews/`.
3. Run the Gallery build and effect validation commands documented by the Skill package.
4. Review the generated index, Gallery data, preview, source copy, and third-party notice before opening a pull request.

Do not hand-edit generated Gallery files or `THIRD_PARTY_NOTICES.md`.

## Privacy and licensing

Only the explicitly attached image is passed to the host-native generator. Review your host's privacy policy before using sensitive images.

The root [LICENSE](./LICENSE) covers only original code and adaptations in this repository. It does not relicense third-party material. Upstream attribution and license details are listed in [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
