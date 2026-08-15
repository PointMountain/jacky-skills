import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

const REQUIRED_FIELDS = [
  'id',
  'version',
  'title_en',
  'title_zh',
  'summary_en',
  'summary_zh',
  'category',
  'execution_kind',
  'input_mode',
  'input_min',
  'input_max',
  'input_formats',
  'output_count',
  'preview',
  'source_repository',
  'source_revision',
  'source_paths',
  'source_sha256s',
  'source_license_spdx',
  'source_license_url',
  'adaptation_notice',
  'preview_origin',
  'preview_author',
  'preview_license_spdx',
  'preview_sha256',
];

const REQUIRED_FIELD_SET = new Set(REQUIRED_FIELDS);
const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SEMVER_PATTERN =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;
const GIT_SHA_PATTERN = /^[0-9a-f]{40}$/i;
const SHA256_PATTERN = /^[0-9a-f]{64}$/i;
const REPOSITORY_PATTERN = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const YAML_EMPTY_SCALAR_PATTERN = /^(?:null|~|"\s*"|'\s*')$/i;
const YAML_COMPLEX_SCALAR_PATTERN = /^["'\[\]{|}>!&*]/;
const YAML_COMMENT_PATTERN = /(?:^|[ \t])#/;

function fail(message, filePath) {
  const location = filePath ? ` in ${filePath}` : '';
  throw new Error(`${message}${location}`);
}

function parseFrontmatter(markdown, filePath) {
  if (typeof markdown !== 'string') {
    fail('Effect card must be a Markdown string', filePath);
  }

  const normalized = markdown.replaceAll('\r\n', '\n');
  const match = normalized.match(/^---\n([\s\S]*?)\n---(?:\n|$)/);
  if (!match) {
    fail('Effect card must start with simple frontmatter', filePath);
  }

  const fields = Object.create(null);
  for (const line of match[1].split('\n')) {
    const separator = line.indexOf(':');
    if (separator === -1 || /^\s/.test(line)) {
      fail('Frontmatter supports only simple single-line scalar fields', filePath);
    }

    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    if (!key) {
      fail('Frontmatter contains an empty key', filePath);
    }
    if (!REQUIRED_FIELD_SET.has(key)) {
      fail(`Unknown frontmatter field: ${key}`, filePath);
    }
    if (Object.hasOwn(fields, key)) {
      fail(`Duplicate frontmatter field: ${key}`, filePath);
    }
    if (!value) {
      fail(`Empty frontmatter value for ${key}`, filePath);
    }
    if (
      YAML_EMPTY_SCALAR_PATTERN.test(value) ||
      YAML_COMPLEX_SCALAR_PATTERN.test(value) ||
      YAML_COMMENT_PATTERN.test(value)
    ) {
      fail(`Field ${key} must be a simple single-line scalar`, filePath);
    }
    fields[key] = value;
  }

  for (const field of REQUIRED_FIELDS) {
    if (!Object.hasOwn(fields, field)) {
      fail(`Missing required field: ${field}`, filePath);
    }
  }

  const body = normalized.slice(match[0].length).trim();
  return { fields, body };
}

function parseCsv(value, field, filePath) {
  const items = value.split(',').map((item) => item.trim());
  if (items.some((item) => item.length === 0)) {
    fail(`Empty CSV item in ${field}`, filePath);
  }
  return items;
}

function assertRelativePath(value, field, filePath) {
  if (
    path.posix.isAbsolute(value) ||
    path.win32.isAbsolute(value) ||
    value.includes('\\') ||
    value.split('/').includes('..')
  ) {
    fail(`${field} must be a relative path without .. segments`, filePath);
  }
}

function assertEqual(value, expected, field, filePath) {
  if (value !== expected) {
    fail(`${field} must be ${expected}`, filePath);
  }
}

function assertHttpsUrl(value, field, filePath) {
  let url;
  try {
    url = new URL(value);
  } catch {
    fail(`${field} must be a valid HTTPS URL`, filePath);
  }
  if (url.protocol !== 'https:') {
    fail(`${field} must be a valid HTTPS URL`, filePath);
  }
}

function parseSemVer(version) {
  const match = version.match(SEMVER_PATTERN);
  if (!match) return null;
  return {
    major: match[1],
    minor: match[2],
    patch: match[3],
    prerelease: match[4]?.split('.') ?? [],
  };
}

function compareNumericIdentifier(left, right) {
  if (left.length !== right.length) return left.length - right.length;
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

function comparePrerelease(left, right) {
  if (left.length === 0 || right.length === 0) {
    return left.length === right.length ? 0 : left.length === 0 ? 1 : -1;
  }

  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    if (left[index] === undefined) return -1;
    if (right[index] === undefined) return 1;
    if (left[index] === right[index]) continue;

    const leftNumber = /^\d+$/.test(left[index]);
    const rightNumber = /^\d+$/.test(right[index]);
    if (leftNumber && rightNumber) return compareNumericIdentifier(left[index], right[index]);
    if (leftNumber !== rightNumber) return leftNumber ? -1 : 1;
    return left[index] < right[index] ? -1 : 1;
  }
  return 0;
}

function compareSemVer(left, right) {
  const a = parseSemVer(left);
  const b = parseSemVer(right);
  for (const field of ['major', 'minor', 'patch']) {
    const precedence = compareNumericIdentifier(a[field], b[field]);
    if (precedence !== 0) return precedence;
  }
  return comparePrerelease(a.prerelease, b.prerelease);
}

function sortEffects(effects) {
  return effects
    .map((effect, index) => ({ effect, index }))
    .sort(
      (left, right) =>
        left.effect.id.localeCompare(right.effect.id) ||
        compareSemVer(left.effect.version, right.effect.version) ||
        left.index - right.index,
    )
    .map(({ effect }) => effect);
}

export function parseEffect(markdown, filePath) {
  const { fields, body } = parseFrontmatter(markdown, filePath);

  if (!ID_PATTERN.test(fields.id)) fail('Invalid id; expected kebab-case', filePath);
  if (!parseSemVer(fields.version)) fail('Invalid SemVer version', filePath);
  if (!REPOSITORY_PATTERN.test(fields.source_repository)) {
    fail('source_repository must use owner/repo format', filePath);
  }
  if (!GIT_SHA_PATTERN.test(fields.source_revision)) {
    fail('source_revision must be a 40-character Git SHA', filePath);
  }
  if (!SHA256_PATTERN.test(fields.preview_sha256)) {
    fail('preview_sha256 must be a 64-character SHA-256', filePath);
  }

  assertEqual(fields.category, 'portrait', 'category', filePath);
  assertEqual(fields.execution_kind, 'host-image-generation', 'execution_kind', filePath);
  assertEqual(fields.input_mode, 'image', 'input_mode', filePath);
  assertEqual(fields.input_min, '1', 'input_min', filePath);
  assertEqual(fields.input_max, '1', 'input_max', filePath);
  assertEqual(fields.output_count, '1', 'output_count', filePath);
  assertEqual(fields.source_license_spdx, 'MIT', 'source_license_spdx', filePath);
  assertEqual(fields.preview_license_spdx, 'CC-BY-4.0', 'preview_license_spdx', filePath);
  assertHttpsUrl(fields.source_license_url, 'source_license_url', filePath);

  const formats = parseCsv(fields.input_formats, 'input_formats', filePath);
  if (formats.length !== 2 || formats[0] !== 'jpeg' || formats[1] !== 'png') {
    fail('input_formats must be jpeg,png', filePath);
  }

  assertRelativePath(fields.preview, 'preview', filePath);
  const sourcePaths = parseCsv(fields.source_paths, 'source_paths', filePath);
  const sourceHashes = parseCsv(fields.source_sha256s, 'source_sha256s', filePath);
  if (sourcePaths.length !== sourceHashes.length) {
    fail('source_paths and source_sha256s must have the same length', filePath);
  }

  const seenPaths = new Set();
  const sources = sourcePaths.map((sourcePath, index) => {
    assertRelativePath(sourcePath, 'source_paths', filePath);
    if (seenPaths.has(sourcePath)) fail(`Duplicate source path: ${sourcePath}`, filePath);
    seenPaths.add(sourcePath);

    const sha256 = sourceHashes[index];
    if (!SHA256_PATTERN.test(sha256)) {
      fail(`source_sha256s contains an invalid SHA-256 at position ${index + 1}`, filePath);
    }
    return { path: sourcePath, sha256: sha256.toLowerCase() };
  });

  return {
    ref: `${fields.id}@${fields.version}`,
    id: fields.id,
    version: fields.version,
    title: { en: fields.title_en, zh: fields.title_zh },
    summary: { en: fields.summary_en, zh: fields.summary_zh },
    category: fields.category,
    executionKind: fields.execution_kind,
    input: { mode: fields.input_mode, min: 1, max: 1, formats },
    outputCount: 1,
    preview: fields.preview,
    sourceRepository: fields.source_repository,
    sourceRevision: fields.source_revision.toLowerCase(),
    sources,
    sourceLicense: {
      spdx: fields.source_license_spdx,
      url: fields.source_license_url,
    },
    adaptationNotice: fields.adaptation_notice,
    previewProvenance: {
      origin: fields.preview_origin,
      author: fields.preview_author,
      licenseSpdx: fields.preview_license_spdx,
      sha256: fields.preview_sha256.toLowerCase(),
    },
    filePath,
    body,
  };
}

export async function loadEffects(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const markdownFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
    .map((entry) => entry.name)
    .sort();

  const effects = await Promise.all(
    markdownFiles.map(async (name) => {
      const filePath = path.join(root, name);
      return parseEffect(await readFile(filePath, 'utf8'), filePath);
    }),
  );
  return sortEffects(effects);
}

export function buildLibrary(effects, generatedAt) {
  return {
    schemaVersion: 1,
    generatedAt,
    effects: sortEffects(effects).map((effect) => ({
      ref: effect.ref,
      id: effect.id,
      version: effect.version,
      title: { ...effect.title },
      summary: { ...effect.summary },
      category: effect.category,
      input: { ...effect.input, formats: [...effect.input.formats] },
      outputCount: effect.outputCount,
      previewUrl: `./media/${path.posix.basename(effect.preview)}`,
      sourceUrl: `./source/${effect.id}.md`,
      provenance: {
        repository: effect.sourceRepository,
        revision: effect.sourceRevision,
        license: { ...effect.sourceLicense },
        preview: {
          origin: effect.previewProvenance.origin,
          author: effect.previewProvenance.author,
          licenseSpdx: effect.previewProvenance.licenseSpdx,
        },
      },
      invocation: `Use $image-effects effect ${effect.ref} on my uploaded image.`,
    })),
  };
}

export function renderThirdPartyNotices(effects, header) {
  if (typeof header !== 'string') throw new TypeError('Notice header must be a string');

  const sections = sortEffects(effects).map((effect) => {
    const sourceLines = effect.sources.map(
      (source) => `- Source: \`${source.path}\` (SHA-256: \`${source.sha256}\`)`,
    );
    return [
      `## ${effect.ref}`,
      '',
      `- Repository: \`${effect.sourceRepository}\``,
      `- Revision: \`${effect.sourceRevision}\``,
      ...sourceLines,
      `- License: [${effect.sourceLicense.spdx}](${effect.sourceLicense.url})`,
      `- Adaptation: ${effect.adaptationNotice}`,
    ].join('\n');
  });

  if (sections.length === 0) return header;
  const separator = header.endsWith('\n\n') ? '' : header.endsWith('\n') ? '\n' : '\n\n';
  return `${header}${separator}${sections.join('\n\n')}\n`;
}
