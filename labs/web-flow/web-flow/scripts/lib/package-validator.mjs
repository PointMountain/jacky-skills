import { lstat, readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { assertNoSensitiveContent } from './sensitive-scan.mjs';

const REQUIRED_FILES = Object.freeze([
  'web-flow/SKILL.md',
  'web-flow/references/workflow.md',
  'web-flow/references/runtime-state.md',
  'web-flow/references/external-capabilities.md',
]);
const EXCLUDED_DIRECTORIES = new Set(['archive', 'memory']);
const LEGACY_REFERENCES = new RegExp(
  `\\b(?:workflow|external-skills)\\.${'ya?ml'}\\b`,
  'iu',
);

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return (
    relative === '' ||
    (relative !== '..' &&
      !relative.startsWith(`..${path.sep}`) &&
      !path.isAbsolute(relative))
  );
}

async function collectActiveFiles(root, relativeParent = '') {
  const files = [];
  const directory = path.join(root, relativeParent);
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const relativePath = relativeParent
      ? `${relativeParent}/${entry.name}`
      : entry.name;
    if (entry.isSymbolicLink()) {
      throw new Error(`active package 拒绝符号链接：${relativePath}`);
    }
    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRECTORIES.has(entry.name)) {
        files.push(...(await collectActiveFiles(root, relativePath)));
      }
    } else if (entry.isFile()) {
      files.push(relativePath);
    }
  }
  return files;
}

async function requireFiles(root, activeFiles) {
  const activeSet = new Set(activeFiles);
  for (const relativePath of REQUIRED_FILES) {
    if (!activeSet.has(relativePath)) {
      throw new Error(`required file 缺少：${relativePath}`);
    }
    const stats = await lstat(path.join(root, relativePath));
    if (!stats.isFile() || stats.isSymbolicLink()) {
      throw new Error(`required file 必须是普通文件：${relativePath}`);
    }
  }
}

function parseFrontmatterName(contents, relativePath) {
  const normalized = contents.replaceAll('\r\n', '\n');
  if (!normalized.startsWith('---\n')) {
    throw new Error(`${relativePath} 缺少 frontmatter`);
  }
  const closing = normalized.indexOf('\n---\n', 4);
  if (closing === -1) {
    throw new Error(`${relativePath} frontmatter 未闭合`);
  }
  const frontmatter = normalized.slice(4, closing);
  const match = /^name:\s*["']?([^\s"']+)["']?\s*$/imu.exec(frontmatter);
  if (!match) throw new Error(`${relativePath} frontmatter 缺少 name`);
  return match[1];
}

function stripFencedCode(contents) {
  return contents.replace(/```[\s\S]*?```|~~~[\s\S]*?~~~/gu, '');
}

function collectMarkdownTargets(contents) {
  const source = stripFencedCode(contents);
  const targets = [];
  for (const match of source.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/gu)) {
    targets.push(match[1]);
  }
  for (const match of source.matchAll(/^\s*\[[^\]]+\]:\s*(\S+)/gmu)) {
    targets.push(match[1]);
  }
  return targets;
}

function normalizeLinkTarget(rawTarget) {
  const trimmed = rawTarget.trim();
  const target = trimmed.startsWith('<')
    ? trimmed.slice(1, trimmed.indexOf('>'))
    : trimmed.split(/\s+/u)[0];
  if (
    target === '' ||
    target.startsWith('#') ||
    /^[a-z][a-z0-9+.-]*:/iu.test(target)
  ) {
    return null;
  }
  const withoutFragment = target.split('#', 1)[0].split('?', 1)[0];
  try {
    return decodeURIComponent(withoutFragment);
  } catch (error) {
    throw new Error(`Markdown link URL 编码无效：${target}`, { cause: error });
  }
}

async function validateMarkdownLinks(root, relativePath, contents) {
  for (const rawTarget of collectMarkdownTargets(contents)) {
    const target = normalizeLinkTarget(rawTarget);
    if (target === null) continue;
    if (path.isAbsolute(target)) {
      throw new Error(`${relativePath} Markdown 链接必须是相对路径：${target}`);
    }
    const absoluteTarget = path.resolve(
      root,
      path.dirname(relativePath),
      target,
    );
    if (!isWithin(root, absoluteTarget)) {
      throw new Error(`${relativePath} Markdown 链接逃逸 package：${target}`);
    }
    try {
      await lstat(absoluteTarget);
    } catch (error) {
      if (error?.code === 'ENOENT') {
        throw new Error(`${relativePath} broken Markdown 链接：${target}`);
      }
      throw error;
    }
  }
}

export async function validatePackage(packageRoot) {
  const defaultRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    '../../..',
  );
  const root = path.resolve(packageRoot ?? defaultRoot);
  const rootStats = await lstat(root);
  if (!rootStats.isDirectory() || rootStats.isSymbolicLink()) {
    throw new Error('packageRoot 必须是普通目录');
  }
  const activeFiles = await collectActiveFiles(root);
  await requireFiles(root, activeFiles);

  const yamlFiles = activeFiles.filter((relativePath) => /\.ya?ml$/iu.test(relativePath));
  if (yamlFiles.length > 0) {
    throw new Error(`active package 禁止独立 YAML/YML：${yamlFiles.join(', ')}`);
  }

  const markdownFiles = activeFiles.filter((relativePath) => relativePath.endsWith('.md'));
  let skillCount = 0;
  for (const relativePath of markdownFiles) {
    const contents = await readFile(path.join(root, relativePath), 'utf8');
    assertNoSensitiveContent(contents, relativePath);
    if (LEGACY_REFERENCES.test(contents)) {
      throw new Error(`${relativePath} 仍引用旧的独立 YAML 导航文件`);
    }
    if (path.basename(relativePath) === 'SKILL.md') {
      skillCount += 1;
      const actualName = parseFrontmatterName(contents, relativePath);
      const expectedName = path.basename(path.dirname(relativePath));
      if (actualName !== expectedName) {
        throw new Error(
          `${relativePath} frontmatter name=${actualName} 必须匹配目录 ${expectedName}`,
        );
      }
    }
    await validateMarkdownLinks(root, relativePath, contents);
  }

  return {
    valid: true,
    packageRoot: root,
    skillCount,
    markdownCount: markdownFiles.length,
    activeFileCount: activeFiles.length,
  };
}
