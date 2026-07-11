import assert from 'node:assert/strict';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { validatePackage } from '../scripts/lib/package-validator.mjs';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);
const webFlowRoot = new URL('../../', import.meta.url);

async function readActiveSkill(skillName) {
  return readFile(new URL(`${skillName}/SKILL.md`, webFlowRoot), 'utf8');
}

async function writeFixtureFile(root, relativePath, contents) {
  const absolutePath = path.join(root, relativePath);
  await mkdir(path.dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, contents, 'utf8');
}

async function createPackageFixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'web-flow-package-'));
  await writeFixtureFile(
    root,
    'web-flow/SKILL.md',
    `---
name: web-flow
description: fixture
---

# Web Flow

- [Workflow](references/workflow.md)
- [Runtime](references/runtime-state.md)
- [Capabilities](references/external-capabilities.md)
`,
  );
  await writeFixtureFile(
    root,
    'web-flow/references/workflow.md',
    '# Workflow\n\n[Runtime](runtime-state.md#state)\n',
  );
  await writeFixtureFile(
    root,
    'web-flow/references/runtime-state.md',
    '# Runtime State\n\n<a id="state"></a>\nRelative path: `reviews/build/result.md`.\n',
  );
  await writeFixtureFile(
    root,
    'web-flow/references/external-capabilities.md',
    '# External Capabilities\n\nPublic URL: https://example.com/docs\n',
  );
  await writeFixtureFile(
    root,
    'web-flow-build/SKILL.md',
    `---
name: web-flow-build
description: fixture
---

# Build

[Main package](../web-flow/SKILL.md)
`,
  );
  await writeFixtureFile(root, 'web-flow/archive/legacy.yaml', 'legacy: true\n');
  await writeFixtureFile(root, 'web-flow/memory/cache.yml', 'private: true\n');
  return root;
}

test('package validation accepts required references, valid frontmatter, links, and excluded archive/memory YAML', async () => {
  const root = await createPackageFixture();
  try {
    const result = await validatePackage(root);
    assert.equal(result.valid, true);
    assert.equal(result.skillCount, 2);
    assert.ok(result.markdownCount >= 5);

    const cli = spawnSync(
      process.execPath,
      [runtimeCli.pathname, 'validate-package', root],
      { encoding: 'utf8' },
    );
    assert.equal(cli.status, 0, cli.stderr);
    assert.equal(JSON.parse(cli.stdout).valid, true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('package validation rejects missing required references and active standalone YAML', async () => {
  const root = await createPackageFixture();
  try {
    await unlink(path.join(root, 'web-flow', 'references', 'workflow.md'));
    await assert.rejects(
      () => validatePackage(root),
      /required|workflow\.md|缺少/i,
    );
    await writeFixtureFile(
      root,
      'web-flow/references/workflow.md',
      '# Workflow\n',
    );
    await writeFixtureFile(root, 'web-flow/config.yaml', 'workflow: old\n');
    await assert.rejects(
      () => validatePackage(root),
      /YAML|config\.yaml|独立/i,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('package validation rejects legacy YAML references and broken active Markdown links', async () => {
  const root = await createPackageFixture();
  try {
    await writeFixtureFile(
      root,
      'web-flow/references/workflow.md',
      `# Workflow\n\nSee \`${['workflow', 'yaml'].join('.')}\` and [missing](missing.md).\n`,
    );
    await assert.rejects(
      () => validatePackage(root),
      /workflow\.yaml|legacy|旧/i,
    );
    await writeFixtureFile(
      root,
      'web-flow/references/workflow.md',
      '# Workflow\n\n[missing](missing.md)\n',
    );
    await assert.rejects(
      () => validatePackage(root),
      /broken|missing\.md|链接/i,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('package validation rejects directory/name mismatches and sensitive active Markdown', async () => {
  const root = await createPackageFixture();
  try {
    await writeFixtureFile(
      root,
      'web-flow-build/SKILL.md',
      `---
name: wrong-name
description: fixture
---

# Build
`,
    );
    await assert.rejects(
      () => validatePackage(root),
      /frontmatter|name|web-flow-build/i,
    );
    await writeFixtureFile(
      root,
      'web-flow-build/SKILL.md',
      `---
name: web-flow-build
description: fixture
---

# Build

token = leaked-value
`,
    );
    await assert.rejects(
      () => validatePackage(root),
      /sensitive|token|凭证/i,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('research contract is Markdown-first, source-grounded, and uses exact run artifacts', async () => {
  const skill = await readActiveSkill('web-flow-research');
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  for (const artifact of [
    'research/content-spec.md',
    'research/reference-evidence.md',
    'research/asset-requirements.md',
    'research/stage-result.md',
  ]) {
    assert.match(skill, new RegExp(artifact.replace('.', '\\.')));
  }
  for (const sourceKind of [
    '用户原话',
    '项目源码',
    '已有文档',
    '参考网页',
    '截图或录屏',
  ]) {
    assert.match(skill, new RegExp(sourceKind));
  }
  assert.match(skill, /reference_observation/);
  assert.match(skill, /web-flow-benchmark/);
});

test('prototype contract owns wireframe/full artifacts, visual gates, attempts, and review versions', async () => {
  const skill = await readActiveSkill('web-flow-prototype');
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  for (const artifact of [
    'wireframe/wireframe.html',
    'wireframe/stage-result.md',
    'prototype/prototype.html',
    'prototype/stage-result.md',
  ]) {
    assert.match(skill, new RegExp(artifact.replace('.', '\\.')));
  }
  assert.match(skill, /G1/);
  assert.match(skill, /G2/);
  assert.match(skill, /attempt-<n>/);
  assert.match(skill, /round-<n>--<artifact-id>-r<revision>\.md/);
  assert.match(skill, /fast[\s\S]*G2[\s\S]*not_applicable/i);
  assert.match(skill, /artifact add/);
  assert.match(skill, /gate decide/);
});

test('design contract selects the approved profile artifact and separates evidence CSS from source styling', async () => {
  const skill = await readActiveSkill('web-flow-design');
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  assert.match(skill, /fast[\s\S]*approved wireframe/i);
  assert.match(skill, /full[\s\S]*approved prototype/i);
  for (const artifact of [
    'design/design-tokens.css',
    'design/layout-contract.md',
    'design/stage-result.md',
  ]) {
    assert.match(skill, new RegExp(artifact.replace('.', '\\.')));
  }
  assert.match(skill, /契约证据/);
  assert.match(skill, /build[\s\S]*sourceDir/i);
  assert.match(skill, /artifact add/);
  assert.match(skill, /web-flow-benchmark/);
});

test('build contract writes only sourceDir and enforces update baseline/allowlist safety around G3', async () => {
  const skill = await readActiveSkill('web-flow-build');
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  assert.match(skill, /源码只写 `sourceDir`/);
  for (const evidence of [
    'preexisting-state.md',
    'build/preview-evidence.md',
    'build/stage-result.md',
  ]) {
    assert.match(skill, new RegExp(evidence.replace('.', '\\.')));
  }
  assert.match(skill, /禁止并行写同一源码树/);
  assert.match(skill, /update[\s\S]*source plan/i);
  assert.match(skill, /dirty conflict[\s\S]*阻断/i);
  assert.match(skill, /source verify/);
  assert.match(skill, /allowlist/);
  assert.match(skill, /baseline/);
  assert.match(skill, /G3/);
});

test('benchmark contract uses Markdown rubrics/template with six stages and versioned independent reviews', async () => {
  const skill = await readActiveSkill('web-flow-benchmark');
  const rubrics = await readFile(
    new URL('web-flow-benchmark/references/rubrics.md', webFlowRoot),
    'utf8',
  );
  const template = await readFile(
    new URL('web-flow-benchmark/references/review-template.md', webFlowRoot),
    'utf8',
  );
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  assert.match(skill, /references\/rubrics\.md/);
  assert.match(skill, /references\/review-template\.md/);
  assert.match(skill, /reviews\/<stage>\/attempt-<n>\/round-<n>--<artifact-id>-r<revision>\.md/);
  assert.match(skill, /must-pass recheck/i);
  assert.match(skill, /review record/);
  for (const stage of [
    'research',
    'wireframe',
    'prototype',
    'design',
    'build',
    'deploy',
  ]) {
    assert.match(rubrics, new RegExp(`## ${stage}\\b`));
  }
  assert.match(rubrics, /must-pass/i);
  assert.match(rubrics, /权重/);
  assert.match(rubrics, /阈值/);
  assert.match(rubrics, /0[\s\S]*3[\s\S]*5/);
  assert.match(rubrics, /事实声明/);
  assert.match(rubrics, /实时 hash/i);
  assert.match(rubrics, /桌面/);
  assert.match(rubrics, /移动/);
  assert.match(rubrics, /HTTP/);
  assert.match(rubrics, /browser/i);
  assert.match(rubrics, /console/i);
  for (const field of [
    'Stage',
    'Attempt',
    'Review kind',
    'Reviewer',
    'Independence',
    'Rubric ref',
    'Artifact ref',
    'Must-pass',
    'Weighted score',
    'Decision',
    'Top fix',
    'Residual',
  ]) {
    assert.match(template, new RegExp(field, 'i'));
  }
});

test('deploy entry is provider-neutral and records late authorization plus immutable three-fact evidence', async () => {
  const skill = await readActiveSkill('web-flow-deploy');
  const cloudflare = await readFile(
    new URL(
      'web-flow-deploy/references/cloudflare-pages.md',
      webFlowRoot,
    ),
    'utf8',
  );
  const description = skill.split('---\n', 3)[1];
  assert.doesNotMatch(skill, /\.ya?ml\b/i);
  assert.doesNotMatch(description, /Cloudflare|wrangler/i);
  assert.doesNotMatch(skill, /npx wrangler|pages deploy/i);
  assert.match(skill, /provider-neutral/i);
  assert.match(skill, /references\/cloudflare-pages\.md/);
  assert.match(cloudflare, /Cloudflare Pages/);
  assert.match(cloudflare, /wrangler/);
  for (const artifact of [
    'preflight/deployment-readiness.md',
    'deploy/deployment-evidence.md',
    'deploy/stage-result.md',
  ]) {
    assert.match(skill, new RegExp(artifact.replace('.', '\\.')));
  }
  assert.match(skill, /G3[\s\S]*finalize[\s\S]*授权/);
  assert.match(skill, /publish[\s\S]*重新.*preflight/i);
  assert.match(skill, /deploy record/);
  assert.match(skill, /build hash/i);
  assert.match(skill, /HTTP/);
  assert.match(skill, /browser/i);
  assert.match(skill, /console/i);
  assert.match(skill, /失败[\s\S]*preview[\s\S]*partial/i);
});

test('README documents explicit seven-skill linking, labs boundary, archive exclusion, and Node checks', async () => {
  const readme = await readFile(new URL('README.md', webFlowRoot), 'utf8');
  for (const skillName of [
    'web-flow',
    'web-flow-research',
    'web-flow-prototype',
    'web-flow-design',
    'web-flow-build',
    'web-flow-benchmark',
    'web-flow-deploy',
  ]) {
    const command = `j-skills link "$JACKY_SKILLS_DIR/labs/web-flow/${skillName}"`;
    assert.match(readme, new RegExp(command.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.match(readme, /install\.sh[\s\S]*不[会包含扫描入][\s\S]*labs\//i);
  assert.match(readme, /archive\/[\s\S]*不参与[\s\S]*运行/);
  assert.match(readme, /Node\.js/);
  assert.match(readme, /node --test labs\/web-flow\/web-flow\/tests\/\*\.test\.mjs/);
  assert.match(readme, /validate-package labs\/web-flow/);
});
