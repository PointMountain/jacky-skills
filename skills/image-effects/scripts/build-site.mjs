#!/usr/bin/env node

import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { build } from 'vite';

import { PUBLIC_MEDIA_BASE_URL } from '../gallery/gallery-config.mjs';
import viteConfig from '../gallery/vite.config.mjs';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(SCRIPT_DIR, '..');
const GALLERY_ROOT = path.join(SKILL_ROOT, 'gallery');
const DEFAULT_OUTPUT = path.join(SKILL_ROOT, 'site-dist');
const STATIC_DIRECTORIES = Object.freeze(['api', 'source']);

function publicPreviewUrl(effect) {
  const expectedPrefix = `./media/${effect.ref}.`;
  if (typeof effect.previewUrl !== 'string' || !effect.previewUrl.startsWith(expectedPrefix)) {
    throw new Error(`Invalid managed preview URL for ${effect.ref}.`);
  }
  const extension = effect.previewUrl.slice(expectedPrefix.length);
  if (!['jpg', 'jpeg', 'png'].includes(extension)) {
    throw new Error(`Unsupported preview extension for ${effect.ref}.`);
  }
  return new URL(`${effect.ref}.${extension}`, PUBLIC_MEDIA_BASE_URL).href;
}

async function rewritePreviewUrls(outputRoot) {
  const libraryPath = path.join(outputRoot, 'api', 'library.json');
  const library = JSON.parse(await readFile(libraryPath, 'utf8'));
  if (!Array.isArray(library.effects)) {
    throw new Error('Gallery library effects must be an array.');
  }
  for (const effect of library.effects) effect.previewUrl = publicPreviewUrl(effect);
  await writeFile(libraryPath, `${JSON.stringify(library, null, 2)}\n`);
}

export async function buildGallerySite({ outputRoot = DEFAULT_OUTPUT } = {}) {
  const resolvedOutput = path.resolve(outputRoot);
  await build({
    ...viteConfig,
    build: {
      ...viteConfig.build,
      outDir: resolvedOutput,
      emptyOutDir: true,
    },
  });

  await Promise.all(
    STATIC_DIRECTORIES.map((directory) =>
      cp(path.join(GALLERY_ROOT, directory), path.join(resolvedOutput, directory), {
        recursive: true,
        force: true,
      }),
    ),
  );
  await rewritePreviewUrls(resolvedOutput);
  await mkdir(resolvedOutput, { recursive: true });
  await writeFile(path.join(resolvedOutput, '.nojekyll'), '');
  return resolvedOutput;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  buildGallerySite().catch((error) => {
    console.error(`Gallery build failed: ${error.message}`);
    process.exitCode = 1;
  });
}
