#!/usr/bin/env node

import { readFile } from 'node:fs/promises';

import {
  addArtifact,
  importArtifact,
} from './lib/artifact-ledger.mjs';
import {
  recordDeploymentPreflight,
  recordDeploymentPublish,
} from './lib/deployment-store.mjs';
import { finalizeRun } from './lib/finalize-store.mjs';
import { validatePackage } from './lib/package-validator.mjs';
import { recordGateDecision } from './lib/gate-store.mjs';
import { recordReview } from './lib/review-store.mjs';
import { validateRun } from './lib/validators.mjs';
import {
  initializeRun,
  recordSourcePlan,
  recordWorkflowTransition,
  reconcileRun,
  verifySourceChanges,
} from './lib/runtime-store.mjs';

function readFlag(args, name) {
  const index = args.indexOf(name);
  if (index === -1 || !args[index + 1]) {
    throw new Error(`缺少 ${name} 参数`);
  }
  return args[index + 1];
}

function readFlags(args, name) {
  const values = [];
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === name && args[index + 1]) values.push(args[index + 1]);
  }
  return values;
}

async function readJson(filePath, label) {
  try {
    return JSON.parse(await readFile(filePath, 'utf8'));
  } catch (error) {
    throw new Error(`${label} 读取失败：${error.message}`, { cause: error });
  }
}

export async function main(args = process.argv.slice(2)) {
  const [command, target, ...options] = args;

  if (command === 'artifact') {
    const [runDir, ...artifactOptions] = options;
    if (!runDir) throw new Error(`artifact ${target ?? ''} 需要 runDir`);
    const common = {
      runDir,
      artifactId: readFlag(artifactOptions, '--artifact-id'),
      artifactPath: readFlag(artifactOptions, '--path'),
      producer: readFlag(artifactOptions, '--producer'),
      createdAt: readFlag(artifactOptions, '--created-at'),
    };
    if (target === 'add') return addArtifact(common);
    if (target === 'import') {
      return importArtifact({
        ...common,
        reusedFrom: {
          runId: readFlag(artifactOptions, '--reused-from-run'),
          artifactRef: readFlag(
            artifactOptions,
            '--reused-from-artifact',
          ),
          sha256: readFlag(artifactOptions, '--reused-from-sha256'),
        },
      });
    }
    throw new Error(`未知 artifact 命令：${target ?? ''}`);
  }

  if (command === 'review') {
    const [runDir, ...reviewOptions] = options;
    if (target !== 'record' || !runDir) {
      throw new Error('review 仅支持 record <runDir>');
    }
    const input = await readJson(
      readFlag(reviewOptions, '--input-file'),
      'review input',
    );
    return recordReview({ runDir, ...input });
  }

  if (command === 'gate') {
    const [runDir, ...gateOptions] = options;
    if (target !== 'decide' || !runDir) {
      throw new Error('gate 仅支持 decide <runDir>');
    }
    const input = await readJson(
      readFlag(gateOptions, '--input-file'),
      'gate input',
    );
    return recordGateDecision({ runDir, ...input });
  }

  if (command === 'deploy') {
    const [runDir, ...deployOptions] = options;
    if (target !== 'record' || !runDir) {
      throw new Error('deploy 仅支持 record <runDir>');
    }
    const mode = readFlag(deployOptions, '--mode');
    const input = await readJson(
      readFlag(deployOptions, '--input-file'),
      'deployment input',
    );
    if (mode === 'preflight') {
      return recordDeploymentPreflight({ runDir, ...input });
    }
    if (mode === 'publish') {
      return recordDeploymentPublish({ runDir, ...input });
    }
    throw new Error('deploy record mode 必须是 preflight 或 publish');
  }

  if (command === 'source') {
    const [runDir, ...sourceOptions] = options;
    if (!runDir) throw new Error(`source ${target ?? ''} 需要 runDir`);
    if (target === 'plan') {
      return recordSourcePlan({
        runDir,
        allowlist: readFlags(sourceOptions, '--allow'),
        confirmedDirtyPaths: readFlags(sourceOptions, '--confirm-dirty'),
        metadata: {
          eventId: readFlag(sourceOptions, '--event-id'),
          at: readFlag(sourceOptions, '--at'),
          actor: readFlag(sourceOptions, '--actor'),
        },
      });
    }
    if (target === 'verify') {
      if (sourceOptions.length > 0) {
        throw new Error('source verify 仅接受 runDir');
      }
      return verifySourceChanges(runDir);
    }
    throw new Error(`未知 source 命令：${target ?? ''}`);
  }

  if (command === 'init') {
    if (!target) throw new Error('init 需要 projectRoot');
    const input = await readJson(readFlag(options, '--input-file'), '初始化输入');
    const metadata = await readJson(
      readFlag(options, '--metadata-file'),
      '事件元数据',
    );
    return initializeRun({ projectRoot: target, input, metadata });
  }

  if (command === 'transition') {
    if (!target) throw new Error('transition 需要 runDir');
    const eventInput = await readJson(
      readFlag(options, '--event-file'),
      'workflow event',
    );
    return recordWorkflowTransition(target, eventInput);
  }

  if (command === 'reconcile') {
    if (!target || options.length > 0) {
      throw new Error('reconcile 仅接受 runDir');
    }
    return reconcileRun(target);
  }

  if (command === 'validate-run') {
    if (!target) throw new Error('validate-run 需要 runDir');
    const requireTerminal = options.includes('--require-terminal');
    const allowed = requireTerminal ? ['--require-terminal'] : [];
    if (options.some((option) => !allowed.includes(option))) {
      throw new Error('validate-run 仅支持 --require-terminal');
    }
    return validateRun(target, { requireTerminal });
  }

  if (command === 'finalize') {
    if (!target) throw new Error('finalize 需要 runDir');
    const input = await readJson(
      readFlag(options, '--input-file'),
      'finalize input',
    );
    return finalizeRun({ runDir: target, ...input });
  }

  if (command === 'validate-package') {
    if (options.length > 0) {
      throw new Error('validate-package 最多接受一个 packageRoot');
    }
    return validatePackage(target);
  }

  throw new Error(`未知命令：${command ?? ''}`);
}

try {
  const result = await main();
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
}
