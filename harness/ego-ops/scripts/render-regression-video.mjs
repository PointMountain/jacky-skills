#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
} from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

const DEFAULT_BUDGET_MS = 60_000;
const DEFAULT_INPUT_FPS = 8;
const DEFAULT_OUTPUT_FPS = 30;

function fail(message) {
  throw new Error(message);
}

function positiveNumber(value, name) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    fail(`${name} 必须是正数`);
  }
  return parsed;
}

export function parseArgs(argv) {
  const options = {
    budgetMs: DEFAULT_BUDGET_MS,
    outputFps: DEFAULT_OUTPUT_FPS,
    ffmpeg: "ffmpeg",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (!flag.startsWith("--") || value === undefined) {
      fail(`无法解析参数：${flag}`);
    }
    index += 1;
    if (flag === "--frames") options.frames = value;
    else if (flag === "--output") options.output = value;
    else if (flag === "--stage-timings") options.stageTimings = value;
    else if (flag === "--budget-ms") options.budgetMs = positiveNumber(value, flag);
    else if (flag === "--input-fps") options.inputFps = positiveNumber(value, flag);
    else if (flag === "--output-fps") options.outputFps = positiveNumber(value, flag);
    else if (flag === "--ffmpeg") options.ffmpeg = value;
    else fail(`未知参数：${flag}`);
  }

  if (!options.frames) fail("缺少 --frames");
  if (!options.output) fail("缺少 --output");
  return options;
}

export function discoverFrames(frameDirectory) {
  const directory = resolve(frameDirectory);
  if (!existsSync(directory)) fail(`帧目录不存在：${directory}`);

  const frames = readdirSync(directory)
    .map((name) => {
      const match = /^frame-(\d{6})\.(jpg|jpeg|png)$/i.exec(name);
      return match ? { name, number: Number(match[1]), extension: match[2].toLowerCase() } : null;
    })
    .filter(Boolean)
    .sort((left, right) => left.number - right.number);

  if (frames.length === 0) fail("帧目录中没有 frame-000001.jpg/png 格式的文件");
  const extension = frames[0].extension;
  for (let index = 0; index < frames.length; index += 1) {
    if (frames[index].number !== index + 1) fail(`帧编号不连续：${frames[index].name}`);
    if (frames[index].extension !== extension) fail("所有帧必须使用相同扩展名");
  }

  return { directory, frames, extension };
}

export function readStageTimings(path) {
  if (!path) return { stages: {}, totalMs: 0 };
  const raw = JSON.parse(readFileSync(resolve(path), "utf8"));
  const stages = raw.stages ?? {};
  if (typeof stages !== "object" || Array.isArray(stages) || stages === null) {
    fail("阶段耗时的 stages 必须是对象");
  }

  let sum = 0;
  for (const [name, value] of Object.entries(stages)) {
    if (!Number.isFinite(value) || value < 0) fail(`阶段耗时无效：${name}`);
    sum += value;
  }
  const totalMs = raw.totalMs ?? sum;
  if (!Number.isFinite(totalMs) || totalMs < 0) fail("阶段总耗时必须是非负数");
  return { stages, totalMs };
}

export function buildFfmpegArgs({ inputPattern, inputFps, outputFps, temporaryOutput }) {
  return [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-framerate",
    String(inputFps),
    "-start_number",
    "1",
    "-i",
    inputPattern,
    "-vf",
    `fps=${outputFps},scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos:in_range=full:out_range=tv,format=yuv420p`,
    "-an",
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-crf",
    "24",
    "-movflags",
    "+faststart",
    temporaryOutput,
  ];
}

export function renderRegressionVideo(options) {
  const encoderStartedAt = performance.now();
  const discovered = discoverFrames(options.frames);
  const browserTimings = readStageTimings(options.stageTimings);
  const output = resolve(options.output);
  if (extname(output).toLowerCase() !== ".mp4") fail("--output 必须是 .mp4 文件");

  const elapsedBeforeEncodeMs = performance.now() - encoderStartedAt;
  const remainingBudgetMs = options.budgetMs - browserTimings.totalMs - elapsedBeforeEncodeMs;
  if (remainingBudgetMs <= 0) fail("浏览器阶段已经耗尽总时间预算，跳过编码");

  const derivedInputFps = browserTimings.totalMs > 0
    ? discovered.frames.length / (browserTimings.totalMs / 1000)
    : DEFAULT_INPUT_FPS;
  const inputFps = options.inputFps ?? Math.max(1, Math.min(30, derivedInputFps));
  const temporaryOutput = join(
    dirname(output),
    `.${basename(output)}.partial-${process.pid}-${Date.now()}.mp4`,
  );
  mkdirSync(dirname(output), { recursive: true });

  const inputPattern = join(discovered.directory, `frame-%06d.${discovered.extension}`);
  const ffmpegArgs = buildFfmpegArgs({
    inputPattern,
    inputFps: Number(inputFps.toFixed(6)),
    outputFps: options.outputFps,
    temporaryOutput,
  });

  const encodeStartedAt = performance.now();
  const result = spawnSync(options.ffmpeg, ffmpegArgs, {
    encoding: "utf8",
    timeout: Math.max(1, Math.floor(remainingBudgetMs)),
  });
  const encodeMs = performance.now() - encodeStartedAt;

  try {
    if (result.error) fail(`ffmpeg 执行失败：${result.error.message}`);
    if (result.status !== 0) fail(`ffmpeg 编码失败：${result.stderr.trim() || `退出码 ${result.status}`}`);
    if (!existsSync(temporaryOutput) || statSync(temporaryOutput).size === 0) {
      fail("ffmpeg 未生成有效视频文件");
    }

    const encoderTotalMs = performance.now() - encoderStartedAt;
    const workflowTotalMs = browserTimings.totalMs + encoderTotalMs;
    if (workflowTotalMs > options.budgetMs) {
      fail(`总耗时 ${Math.round(workflowTotalMs)}ms 超过预算 ${options.budgetMs}ms`);
    }
    renameSync(temporaryOutput, output);

    return {
      status: "ok",
      output,
      codec: "h264",
      frameCount: discovered.frames.length,
      estimatedDurationSeconds: Number((discovered.frames.length / inputFps).toFixed(3)),
      timings: {
        browserStages: browserTimings.stages,
        browserTotalMs: Math.round(browserTimings.totalMs),
        encoderPreflightMs: Math.round(elapsedBeforeEncodeMs),
        encodeMs: Math.round(encodeMs),
        encoderTotalMs: Math.round(encoderTotalMs),
        workflowTotalMs: Math.round(workflowTotalMs),
      },
      budget: {
        limitMs: options.budgetMs,
        remainingMs: Math.max(0, Math.round(options.budgetMs - workflowTotalMs)),
        withinBudget: true,
      },
    };
  } finally {
    if (existsSync(temporaryOutput)) rmSync(temporaryOutput, { force: true });
  }
}

function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    console.log(JSON.stringify(renderRegressionVideo(options), null, 2));
  } catch (error) {
    console.error(JSON.stringify({ status: "error", message: error.message }));
    process.exitCode = 1;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
