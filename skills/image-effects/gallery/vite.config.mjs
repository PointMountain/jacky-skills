import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const galleryRoot = fileURLToPath(new URL('.', import.meta.url));
const defaultOutput = fileURLToPath(new URL('../site-dist', import.meta.url));

export default defineConfig({
  root: galleryRoot,
  base: './',
  publicDir: false,
  plugins: [react()],
  build: {
    outDir: defaultOutput,
    emptyOutDir: true,
    assetsDir: 'assets',
    sourcemap: true,
  },
});
