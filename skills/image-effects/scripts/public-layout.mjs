import { existsSync } from 'node:fs';
import path from 'node:path';

const PUBLIC_TEMPLATE_FILES = new Set([
  '.github/workflows/pages.yml',
  'LICENSE',
  'README.md',
  'README_CN.md',
  'THIRD_PARTY_NOTICES.md',
  'THIRD_PARTY_NOTICES.header.md',
]);

function assertTemplateFile(fileName) {
  if (!PUBLIC_TEMPLATE_FILES.has(fileName)) {
    throw new Error(`Unsupported public template file: ${fileName}`);
  }
}

export function usesExportedPublicLayout(root) {
  return !existsSync(path.join(root, 'assets/public-repo/THIRD_PARTY_NOTICES.header.md'))
    && existsSync(path.join(root, 'THIRD_PARTY_NOTICES.header.md'));
}

export function publicTemplatePath(root, fileName) {
  assertTemplateFile(fileName);
  return usesExportedPublicLayout(root)
    ? path.join(root, fileName)
    : path.join(root, 'assets/public-repo', fileName);
}

export function generatedPublicNoticePath(root) {
  return usesExportedPublicLayout(root)
    ? 'THIRD_PARTY_NOTICES.md'
    : 'assets/public-repo/THIRD_PARTY_NOTICES.md';
}
