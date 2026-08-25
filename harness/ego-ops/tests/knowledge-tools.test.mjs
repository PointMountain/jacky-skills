import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, appendFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDir = resolve(fileURLToPath(new URL(".", import.meta.url)));
const skillDir = resolve(testDir, "..");
const scaffold = join(skillDir, "scripts", "scaffold-operation.mjs");
const validate = join(skillDir, "scripts", "validate-knowledge.mjs");
const renderVideo = join(skillDir, "scripts", "render-regression-video.mjs");

function fixtureArgs(root) {
  return [
    scaffold,
    "--root", root,
    "--site", "demo-console",
    "--domain", "console.example.test",
    "--alias", "演示控制台",
    "--operation", "create-review",
    "--title", "创建待审对象",
    "--intent", "在已授权范围内创建一个待审对象",
    "--risk", "medium",
    "--date", "2026-08-23",
    "--entry", "从控制台的对象列表进入创建入口",
    "--step", "确认目标范围后选择创建入口",
    "--step", "提交待审对象后重新观察列表状态",
    "--checkpoint", "对象名称或目标范围不唯一时停止",
    "--success", "列表出现新对象且状态为待审",
    "--evidence", "对象列表可见新条目和待审状态",
  ];
}

test("脚手架生成可索引且可校验的 operation 知识", () => {
  const root = mkdtempSync(join(tmpdir(), "ego-ops-"));
  try {
    execFileSync(process.execPath, fixtureArgs(root), { encoding: "utf8" });
    const output = execFileSync(process.execPath, [validate, "--root", root], { encoding: "utf8" });
    assert.match(output, /知识库校验通过/);
    const operation = readFileSync(join(root, "references/sites/demo-console/operations/create-review.md"), "utf8");
    assert.match(operation, /## 验证证据/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("校验器阻止疑似认证材料进入知识库", () => {
  const root = mkdtempSync(join(tmpdir(), "ego-ops-"));
  try {
    execFileSync(process.execPath, fixtureArgs(root), { encoding: "utf8" });
    appendFileSync(join(root, "references/sites/demo-console/operations/create-review.md"), "\nprivate_key: leaked\n");
    assert.throws(
      () => execFileSync(process.execPath, [validate, "--root", root], { encoding: "utf8", stdio: "pipe" }),
      /知识库校验失败/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("快速回归脚本把连续帧编码为 H.264 并汇总全流程耗时", () => {
  const root = mkdtempSync(join(tmpdir(), "ego-ops-video-"));
  try {
    const frames = join(root, "frames");
    const output = join(root, "regression.mp4");
    const timings = join(root, "timings.json");
    const mockFfmpeg = join(root, "mock-ffmpeg.mjs");
    const capturedArgs = join(root, "ffmpeg-args.json");
    mkdirSync(frames);
    for (let index = 1; index <= 3; index += 1) {
      writeFileSync(join(frames, `frame-${String(index).padStart(6, "0")}.jpg`), `frame-${index}`);
    }
    writeFileSync(timings, JSON.stringify({ stages: { navigate: 1200, verify: 800 }, totalMs: 2000 }));
    writeFileSync(
      mockFfmpeg,
      `#!/usr/bin/env node\nimport { writeFileSync } from "node:fs";\nwriteFileSync(process.env.CAPTURED_ARGS, JSON.stringify(process.argv.slice(2)));\nwriteFileSync(process.argv.at(-1), "mock h264 video");\n`,
    );
    chmodSync(mockFfmpeg, 0o755);

    const stdout = execFileSync(process.execPath, [
      renderVideo,
      "--frames", frames,
      "--stage-timings", timings,
      "--output", output,
      "--budget-ms", "60000",
      "--ffmpeg", mockFfmpeg,
    ], { encoding: "utf8", env: { ...process.env, CAPTURED_ARGS: capturedArgs } });

    const report = JSON.parse(stdout);
    const ffmpegArgs = JSON.parse(readFileSync(capturedArgs, "utf8"));
    assert.equal(report.status, "ok");
    assert.equal(report.codec, "h264");
    assert.equal(report.frameCount, 3);
    assert.equal(report.timings.browserTotalMs, 2000);
    assert.equal(report.budget.withinBudget, true);
    assert.ok(report.timings.workflowTotalMs < 60000);
    assert.ok(existsSync(output));
    assert.ok(ffmpegArgs.includes("libx264"));
    assert.ok(ffmpegArgs.includes("veryfast"));
    assert.ok(ffmpegArgs.includes("1.5"));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("快速回归脚本在浏览器阶段耗尽预算后不启动编码", () => {
  const root = mkdtempSync(join(tmpdir(), "ego-ops-budget-"));
  try {
    const frames = join(root, "frames");
    const output = join(root, "regression.mp4");
    const timings = join(root, "timings.json");
    const marker = join(root, "ffmpeg-started");
    const mockFfmpeg = join(root, "mock-ffmpeg.mjs");
    mkdirSync(frames);
    writeFileSync(join(frames, "frame-000001.jpg"), "frame");
    writeFileSync(timings, JSON.stringify({ stages: { browser: 61000 }, totalMs: 61000 }));
    writeFileSync(mockFfmpeg, `#!/usr/bin/env node\nimport { writeFileSync } from "node:fs";\nwriteFileSync(process.env.MARKER, "started");\n`,);
    chmodSync(mockFfmpeg, 0o755);

    assert.throws(
      () => execFileSync(process.execPath, [
        renderVideo,
        "--frames", frames,
        "--stage-timings", timings,
        "--output", output,
        "--budget-ms", "60000",
        "--ffmpeg", mockFfmpeg,
      ], { encoding: "utf8", env: { ...process.env, MARKER: marker }, stdio: "pipe" }),
      /Command failed/,
    );
    assert.equal(existsSync(marker), false);
    assert.equal(existsSync(output), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("快速回归脚本拒绝缺号帧，避免静默截断视频", () => {
  const root = mkdtempSync(join(tmpdir(), "ego-ops-gap-"));
  try {
    const frames = join(root, "frames");
    mkdirSync(frames);
    writeFileSync(join(frames, "frame-000001.jpg"), "frame-1");
    writeFileSync(join(frames, "frame-000003.jpg"), "frame-3");
    assert.throws(
      () => execFileSync(process.execPath, [renderVideo, "--frames", frames, "--output", join(root, "out.mp4")], {
        encoding: "utf8",
        stdio: "pipe",
      }),
      /Command failed/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
