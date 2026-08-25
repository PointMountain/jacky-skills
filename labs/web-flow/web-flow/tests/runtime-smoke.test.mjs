import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import {
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

const runtimeCli = new URL('../scripts/web-flow-runtime.mjs', import.meta.url);
const SHA256_PATTERN = /^[a-f0-9]{64}$/u;

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    encoding: 'utf8',
    ...options,
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

function cli(...args) {
  return JSON.parse(run(process.execPath, [runtimeCli.pathname, ...args]));
}

function git(projectRoot, ...args) {
  return run('git', args, { cwd: projectRoot });
}

async function writeJson(filePath, value) {
  await writeFile(filePath, `${JSON.stringify(value)}\n`, 'utf8');
}

function sha256(contents) {
  return createHash('sha256').update(contents).digest('hex');
}

test('runtime CLI completes and reconciles one real fast create run', async () => {
  const projectRoot = await mkdtemp(path.join(tmpdir(), 'web-flow-smoke-'));
  const inputFile = path.join(projectRoot, '.smoke-input.json');
  const runId = '20260712T220000Z-s1m2';
  let eventIndex = 0;
  let runDir;

  const metadata = (actor = 'agent') => {
    eventIndex += 1;
    return {
      eventId: `evt-smoke-${String(eventIndex).padStart(2, '0')}`,
      at: `2026-07-12T22:00:${String(eventIndex).padStart(2, '0')}.000Z`,
      actor,
    };
  };

  const transition = async (type, payload, actor = 'agent') => {
    await writeJson(inputFile, { ...metadata(actor), type, payload });
    return cli('transition', runDir, '--event-file', inputFile);
  };

  const addArtifact = (artifactId, artifactPath, producer) =>
    cli(
      'artifact',
      'add',
      runDir,
      '--artifact-id',
      artifactId,
      '--path',
      artifactPath,
      '--producer',
      producer,
      '--created-at',
      `2026-07-12T22:01:${String(eventIndex).padStart(2, '0')}.000Z`,
    ).artifact;

  const reviewStage = async (stage, artifactId, artifactPath, contents) => {
    await writeFile(path.join(projectRoot, artifactPath), contents, 'utf8');
    const artifact = addArtifact(artifactId, artifactPath, stage);
    const reviewPath =
      `reviews/${stage}/attempt-1/round-1--${artifactId}-r1.md`;
    const reviewContents = `# ${stage} review\n`;
    await mkdir(path.dirname(path.join(runDir, reviewPath)), {
      recursive: true,
    });
    await writeFile(path.join(runDir, reviewPath), reviewContents, 'utf8');
    await writeJson(inputFile, {
      stage,
      attempt: 1,
      kind: 'subjective',
      round: 1,
      recheck: null,
      reviewer: 'independent-reviewer',
      independence: { independent: true, limitation: null },
      rubricRef: `web-flow-benchmark/references/rubrics.md#${stage}`,
      reviewPath,
      artifactRef: `${artifactId}@1`,
      mustPass: 'passed',
      decision: 'pass',
      weightedScore: 4.2,
      metadata: metadata('independent-reviewer'),
    });
    const recorded = cli(
      'review',
      'record',
      runDir,
      '--input-file',
      inputFile,
    );
    assert.equal(recorded.event.payload.reviewSha256, sha256(reviewContents));
    assert.match(recorded.event.payload.rubricSha256, SHA256_PATTERN);
    assert.equal(recorded.event.payload.artifactSha256, artifact.sha256);
    return recorded.event;
  };

  const decideGate = async (gate, reviewEvent) => {
    const decisionPath = `gates/${gate}/decision-1.md`;
    const decisionContents = `# ${gate} approved\n`;
    await mkdir(path.dirname(path.join(runDir, decisionPath)), {
      recursive: true,
    });
    await writeFile(path.join(runDir, decisionPath), decisionContents, 'utf8');
    await writeJson(inputFile, {
      gate,
      decision: 'approved',
      decisionPath,
      metadata: metadata('user'),
    });
    const decided = cli(
      'gate',
      'decide',
      runDir,
      '--input-file',
      inputFile,
    );
    assert.equal(decided.event.payload.decisionSha256, sha256(decisionContents));
    assert.equal(
      decided.event.payload.reviewSha256,
      reviewEvent.payload.reviewSha256,
    );
    assert.equal(
      decided.event.payload.artifactSha256,
      reviewEvent.payload.artifactSha256,
    );
    return decided;
  };

  try {
    git(projectRoot, 'init', '-q');
    git(projectRoot, 'config', 'user.name', 'Web Flow Smoke');
    git(projectRoot, 'config', 'user.email', 'web-flow@example.test');
    await writeFile(path.join(projectRoot, 'README.md'), '# Fixture\n', 'utf8');
    git(projectRoot, 'add', 'README.md');
    git(projectRoot, 'commit', '-qm', 'baseline');

    await writeJson(inputFile, {
      runId,
      intent: '构建 fast profile 落地页',
      projectRoot: '.',
      source: { mode: 'create', dir: 'site' },
      interactionMode: 'attended',
      profile: { requested: 'adaptive' },
      deployment: { requested: false, authorized: false, provider: null },
    });
    const metadataFile = path.join(projectRoot, '.smoke-metadata.json');
    await writeJson(metadataFile, metadata('web-flow-runtime'));
    const initialized = cli(
      'init',
      projectRoot,
      '--input-file',
      inputFile,
      '--metadata-file',
      metadataFile,
    );
    runDir = initialized.runDir;

    const ignored = (await readFile(path.join(projectRoot, '.gitignore'), 'utf8'))
      .split(/\r?\n/u)
      .filter((line) => line.trim() === '.web-flow/');
    assert.equal(ignored.length, 1);

    await mkdir(path.join(projectRoot, 'site'));
    await transition('stage_transition', { stage: 'research', to: 'running' });
    await reviewStage(
      'research',
      'research.spec',
      'site/research.md',
      '# Research\n',
    );
    await transition('stage_transition', { stage: 'research', to: 'completed' });

    await transition('stage_transition', { stage: 'wireframe', to: 'running' });
    const wireframeReview = await reviewStage(
      'wireframe',
      'wireframe.preview',
      'site/wireframe.html',
      '<main>wireframe</main>\n',
    );
    await transition('stage_transition', {
      stage: 'wireframe',
      to: 'awaiting_gate',
    });
    const g1 = await decideGate('G1', wireframeReview);
    assert.equal(g1.state.gates.G1.decision, 'approved');

    const profiled = await transition('profile_locked', { resolved: 'fast' });
    assert.equal(profiled.state.profile.resolved, 'fast');
    assert.equal(profiled.state.stages.prototype.status, 'skipped');
    assert.equal(profiled.state.gates.G2.decision, 'not_applicable');

    await transition('stage_transition', { stage: 'design', to: 'running' });
    await reviewStage(
      'design',
      'design.contract',
      'site/design.css',
      ':root { color-scheme: dark; }\n',
    );
    await transition('stage_transition', { stage: 'design', to: 'completed' });

    await transition('stage_transition', { stage: 'build', to: 'running' });
    const buildReview = await reviewStage(
      'build',
      'build.preview',
      'site/index.html',
      '<main>production</main>\n',
    );
    await transition('stage_transition', {
      stage: 'build',
      to: 'awaiting_gate',
    });
    const g3 = await decideGate('G3', buildReview);
    assert.equal(g3.state.gates.G3.decision, 'approved');
    assert.equal(g3.state.stages.build.status, 'completed');

    await writeFile(path.join(runDir, 'skill-usage.md'), '# Skill Usage\n');
    await writeFile(path.join(runDir, 'retrospective.md'), '# Retrospective\n');
    await writeJson(inputFile, {
      status: 'success',
      reason: 'fast create smoke completed',
      supersededBy: null,
      metadata: metadata('web-flow-runtime'),
    });
    const finalized = cli(
      'finalize',
      runDir,
      '--input-file',
      inputFile,
    );
    assert.equal(finalized.state.status, 'success');
    assert.equal(finalized.state.currentStage, null);
    assert.equal(finalized.validation.valid, true);

    assert.equal((await lstat(path.join(projectRoot, 'site'))).isDirectory(), true);
    await assert.rejects(() => lstat(path.join(runDir, 'site')), {
      code: 'ENOENT',
    });

    const events = (await readFile(path.join(runDir, 'events.jsonl'), 'utf8'))
      .trimEnd()
      .split('\n')
      .map((line) => JSON.parse(line));
    assert.deepEqual(
      events.map((event) => event.sequence),
      events.map((_, index) => index + 1),
    );
    for (const event of events.filter((item) =>
      item.type === 'review_recorded' || item.type === 'gate_decided')) {
      assert.match(event.payload.reviewSha256, SHA256_PATTERN);
      assert.match(event.payload.artifactSha256, SHA256_PATTERN);
    }

    const finalStateHash = finalized.state.stateHash;
    await unlink(path.join(runDir, 'run.json'));
    const reconciled = cli('reconcile', runDir);
    assert.equal(reconciled.status, 'success');
    assert.equal(reconciled.stateHash, finalStateHash);
  } finally {
    await rm(projectRoot, { recursive: true, force: true });
  }
});
