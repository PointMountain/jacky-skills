import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

import {
  buildRunTemplate,
  finalizeRun,
  initRun,
  isPathInside,
  parseProbeStatuses,
  resolveSkillRoot,
  validateRunId,
  validateRunMarkdown,
} from "../scripts/usage-ledger.mjs";

const REQUIRED_SECTIONS = [
  "任务",
  "候选探测",
  "路由决定",
  "实际使用的 Skills",
  "证据",
  "复盘",
];

function probeBlock({
  id = "chrome-devtools",
  status = "available",
  evidence = "E0",
} = {}) {
  return `### ${id}

- 状态：${status}
- 检查时间：2026-07-11T10:00:00.000Z
- 版本：未知
- 状态证据引用：${evidence}`;
}

function skillBlock({
  id = "chrome-devtools",
  capability = "无登录态浏览器控制",
  result = "passed",
  evidence = "E1",
} = {}) {
  return `### ${id}

- 承担能力：${capability}
- 来源：测试候选
- 版本：未知
- 实际动作：navigate、snapshot
- 输入：target、intent
- 输出：browser_result、evidence
- 结果：${result}
- 证据引用：${evidence}
- 摩擦：无`;
}

function evidenceBlock(id, type = id === "E0" ? "observation" : "artifact") {
  return `### ${id}

- 类型：${type}
- 引用：run://evidence-${id}
- 证明：${id} 对应的可验证短结论`;
}

function validRun({
  runId = "sample-run",
  probes = [{ id: "chrome-devtools", status: "available", evidence: "E0" }],
  taskResult = "passed",
  mode = "primary",
  routeChain = "browser-control → chrome-devtools",
  usedSkills,
  newline = "\n",
  extra = "",
} = {}) {
  const skills =
    usedSkills ??
    [
      {
        id: "chrome-devtools",
        result: taskResult,
        evidence: "E1",
      },
    ];
  const evidenceIds = new Set([
    ...probes.map((probe) => probe.evidence),
    ...skills.map((skill) => skill.evidence),
  ]);
  const overallResult = taskResult === "passed" ? "success" : taskResult;
  const markdown = `# Browser Control Run: ${runId}

## 任务

- 时间：2026-07-11T10:00:00.000Z
- 类型：static-page
- 需要已有登录态：否

## 候选探测

${probes.map((probe) => probeBlock(probe)).join("\n\n")}

## 路由决定

- 能力槽位：browser_without_existing_login
- 检查候选：${probes.map((probe) => probe.id).join("、")}
- 实际链路：${routeChain}
- 模式：${mode}
- 结果：${taskResult}

## 实际使用的 Skills

${skills.map((skill) => skillBlock(skill)).join("\n\n")}

## 证据

${[...evidenceIds].map((id) => evidenceBlock(id)).join("\n\n")}

## 复盘

- 总体结果：${overallResult}
- 有效模式：测试中的可验证模式
- 已验证根因：无
- 下次规则候选：无
- 建议归宿：none${extra}
`;

  return newline === "\n" ? markdown : markdown.replaceAll("\n", newline);
}

function statusBlock({
  candidate = "chrome-devtools",
  status = "available",
  runId = "old-run",
  newline = "\n",
} = {}) {
  const markdown = `<!-- browser-control:status:${candidate}:start -->
### ${candidate}

- 状态：${status}
- 检查时间：2026-07-10T10:00:00.000Z
- 状态证据引用：runs.local/${runId}.md#E0
<!-- browser-control:status:${candidate}:end -->`;
  return newline === "\n" ? markdown : markdown.replaceAll("\n", newline);
}

function experienceMarkdown({ body = statusBlock(), newline = "\n" } = {}) {
  const markdown = `# Browser Control 本机经验

## 当前能力地图

${body}

## 经晋升经验

- 手写经验：保留这段内容
`;
  return newline === "\n" ? markdown : markdown.replaceAll("\n", newline);
}

async function temporarySkillRoot(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "browser-control-ledger-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  return root;
}

async function fileExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function writeRunFixture(t, { runId, markdown, experience }) {
  const skillRoot = await temporarySkillRoot(t);
  const runsDirectory = path.join(skillRoot, "runs.local");
  await mkdir(runsDirectory, { recursive: true });
  await writeFile(path.join(runsDirectory, `${runId}.md`), markdown, "utf8");
  if (experience !== undefined) {
    await writeFile(path.join(skillRoot, "experience.local.md"), experience, "utf8");
  }
  return skillRoot;
}

function assertNoBareLf(value) {
  assert.doesNotMatch(value, /(^|[^\r])\n/);
}

function startCli(scriptPath, args, cwd) {
  const child = spawn(process.execPath, [scriptPath, ...args], { cwd });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    stdout += chunk;
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });

  return new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("close", (code, signal) => resolve({ code, signal, stdout, stderr }));
  });
}

test("init 创建完整模板，但不创建空 experience.local.md", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const runId = "first-run";
  const markdown = buildRunTemplate(runId);

  for (const section of REQUIRED_SECTIONS) {
    assert.match(markdown, new RegExp(`^## ${section}$`, "m"));
  }

  await initRun(runId, { skillRoot, markdown });

  assert.equal(
    await readFile(path.join(skillRoot, "runs.local", `${runId}.md`), "utf8"),
    markdown,
  );
  assert.equal(await fileExists(path.join(skillRoot, "experience.local.md")), false);
});

test("两个并发 init 仅一个成功，且失败者不能覆盖首份内容", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const runId = "concurrent-run";
  const templates = [
    `${buildRunTemplate(runId)}\n- 竞争标记：A\n`,
    `${buildRunTemplate(runId)}\n- 竞争标记：B\n`,
  ];

  const results = await Promise.allSettled(
    templates.map((markdown) => initRun(runId, { skillRoot, markdown })),
  );
  const fulfilled = results
    .map((result, index) => ({ result, index }))
    .filter(({ result }) => result.status === "fulfilled");
  const rejected = results.filter((result) => result.status === "rejected");

  assert.equal(fulfilled.length, 1);
  assert.equal(rejected.length, 1);
  assert.match(String(rejected[0].reason), /exist|存在|EEXIST/i);
  assert.equal(
    await readFile(path.join(skillRoot, "runs.local", `${runId}.md`), "utf8"),
    templates[fulfilled[0].index],
  );
});

test("两个真实 Node CLI 子进程并发 init 时仅发布一份完整首稿", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const scriptsDirectory = path.join(skillRoot, "scripts");
  const copiedScript = path.join(scriptsDirectory, "usage-ledger.mjs");
  const sourceScript = new URL("../scripts/usage-ledger.mjs", import.meta.url);
  const runId = "same-run-id";
  await mkdir(scriptsDirectory, { recursive: true });
  await copyFile(sourceScript, copiedScript);

  const processes = [
    startCli(copiedScript, ["init", runId], skillRoot),
    startCli(copiedScript, ["init", runId], skillRoot),
  ];
  await Promise.race(processes);
  const runPath = path.join(skillRoot, "runs.local", `${runId}.md`);
  const firstPublishedBytes = await readFile(runPath, "utf8");
  const results = await Promise.all(processes);
  const finalBytes = await readFile(runPath, "utf8");

  assert.equal(results.filter(({ code }) => code === 0).length, 1);
  assert.equal(results.filter(({ code }) => code !== 0).length, 1);
  const failed = results.find(({ code }) => code !== 0);
  assert.match(`${failed.stdout}\n${failed.stderr}`, /EEXIST|exist|已存在/i);
  assert.equal(finalBytes, firstPublishedBytes);
  assert.match(finalBytes, new RegExp(`^# Browser Control Run: ${runId}$`, "m"));
  for (const section of REQUIRED_SECTIONS) {
    assert.match(finalBytes, new RegExp(`^## ${section}$`, "m"));
  }
});

test("两个真实 Node CLI 子进程并发 finalize 时仅一个成功", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const scriptsDirectory = path.join(skillRoot, "scripts");
  const copiedScript = path.join(scriptsDirectory, "usage-ledger.mjs");
  const sourceScript = new URL("../scripts/usage-ledger.mjs", import.meta.url);
  const runId = "concurrent-finalize";
  await mkdir(scriptsDirectory, { recursive: true });
  await copyFile(sourceScript, copiedScript);
  await mkdir(path.join(skillRoot, "runs.local"), { recursive: true });
  await writeFile(
    path.join(skillRoot, "runs.local", `${runId}.md`),
    validRun({ runId }),
    "utf8",
  );

  const results = await Promise.all([
    startCli(copiedScript, ["finalize", runId], skillRoot),
    startCli(copiedScript, ["finalize", runId], skillRoot),
  ]);

  assert.equal(results.filter(({ code }) => code === 0).length, 1);
  assert.equal(results.filter(({ code }) => code !== 0).length, 1);
  assert.match(
    results.find(({ code }) => code !== 0).stderr,
    /finalized|归档|锁定|进行中/i,
  );
  const finalized = await readFile(
    path.join(skillRoot, "runs.local", `${runId}.md`),
    "utf8",
  );
  assert.equal(finalized.match(/^- 账本状态：finalized$/gm)?.length, 1);
  const experience = await readFile(
    path.join(skillRoot, "experience.local.md"),
    "utf8",
  );
  assert.equal(
    experience.match(/browser-control:status:chrome-devtools:start/g)?.length,
    1,
  );
});

test("finalize 可回收死进程遗留锁", async (t) => {
  const runId = "stale-lock-run";
  const skillRoot = await writeRunFixture(t, {
    runId,
    markdown: validRun({ runId }),
  });
  const lockPath = path.join(skillRoot, ".usage-ledger.lock");
  await mkdir(lockPath);
  await writeFile(
    path.join(lockPath, "owner.md"),
    "# Usage Ledger Lock\n\n- PID：99999999\n- Token：dead-owner\n",
    "utf8",
  );

  await finalizeRun(runId, { skillRoot });

  assert.equal(await fileExists(lockPath), false);
  assert.match(
    await readFile(path.join(skillRoot, "runs.local", `${runId}.md`), "utf8"),
    /^- 账本状态：finalized$/m,
  );
});

test("finalize 可重放崩溃后留下的 finalizing 事务", async (t) => {
  const runId = "resume-finalizing";
  const markdown = `${validRun({ runId })}\n## 账本状态\n\n- 账本状态：finalizing\n`;
  const skillRoot = await writeRunFixture(t, { runId, markdown });

  await finalizeRun(runId, { skillRoot });

  const after = await readFile(
    path.join(skillRoot, "runs.local", `${runId}.md`),
    "utf8",
  );
  assert.doesNotMatch(after, /^- 账本状态：finalizing$/m);
  assert.equal(after.match(/^- 账本状态：finalized$/gm)?.length, 1);
  assert.equal(await fileExists(path.join(skillRoot, "experience.local.md")), true);
});

test("parseProbeStatuses 保留四种候选探测状态", () => {
  const expected = ["available", "degraded", "missing", "not_checked"];
  const probes = expected.map((status, index) => ({
    id: `candidate-${index}`,
    status,
    evidence: "E0",
  }));

  const parsed = parseProbeStatuses(validRun({ probes }));

  assert.deepEqual(
    probes.map(({ id }) => parsed.get(id).status),
    expected,
  );
});

test("候选 ID 必须是安全的 kebab-case", () => {
  const base = validRun();
  for (const candidate of [
    "chrome --> injected",
    "chrome:devtools",
    "chrome devtools",
    "Chrome-DevTools",
    "-chrome",
    "chrome-",
  ]) {
    assert.throws(() =>
      validateRunMarkdown(base.replaceAll("chrome-devtools", candidate)),
    );
  }
});

test("运行记录 H1 必须唯一、合法并与 expected run-id 一致", () => {
  const runId = "identity-run";
  const base = validRun({ runId });

  assert.doesNotThrow(() =>
    validateRunMarkdown(base, { expectedRunId: runId }),
  );
  assert.throws(() =>
    validateRunMarkdown(base, { expectedRunId: "different-run" }),
  );
  assert.throws(() =>
    validateRunMarkdown(base.replace(`# Browser Control Run: ${runId}\n`, "")),
  );
  assert.throws(() =>
    validateRunMarkdown(`${base}\n# Browser Control Run: ${runId}\n`),
  );
  assert.throws(() =>
    validateRunMarkdown(base.replace(runId, "INVALID/RUN")),
  );
});

test("候选检查时间必须是有效的 ISO-8601 时间", () => {
  const base = validRun();
  const withCheckedAt = (checkedAt) =>
    base.replace(
      "- 检查时间：2026-07-11T10:00:00.000Z",
      `- 检查时间：${checkedAt}`,
    );

  for (const checkedAt of [
    "2026-07-11T10:00:00Z",
    "2026-07-11T10:00:00.123+08:00",
  ]) {
    assert.doesNotThrow(() => validateRunMarkdown(withCheckedAt(checkedAt)));
  }

  for (const checkedAt of [
    "not-a-time",
    "2026-02-30T10:00:00Z",
    "2026-07-11",
    "2026-07-11T25:00:00Z",
  ]) {
    assert.throws(() => validateRunMarkdown(withCheckedAt(checkedAt)));
  }
});

test("任务时间必须是有效的 ISO-8601 时间", () => {
  const base = validRun();
  const withTaskTime = (taskTime) =>
    base.replace(
      "- 时间：2026-07-11T10:00:00.000Z",
      `- 时间：${taskTime}`,
    );

  for (const taskTime of [
    "2026-07-11T10:00:00Z",
    "2026-07-11T10:00:00.123+08:00",
  ]) {
    assert.doesNotThrow(() => validateRunMarkdown(withTaskTime(taskTime)));
  }

  for (const taskTime of ["not-a-time", "2026-02-30T10:00:00Z"]) {
    assert.throws(() => validateRunMarkdown(withTaskTime(taskTime)));
  }
});

test("available 候选上的任务失败不会被解释为 missing", () => {
  const result = validateRunMarkdown(validRun({ taskResult: "failed" }));

  assert.equal(result.probes.get("chrome-devtools").status, "available");
  assert.equal(result.taskResult, "failed");
});

test("not_checked 不覆盖已有能力状态", async (t) => {
  const runId = "not-checked-run";
  const before = experienceMarkdown();
  const skillRoot = await writeRunFixture(t, {
    runId,
    markdown: validRun({
      runId,
      probes: [{ id: "chrome-devtools", status: "not_checked", evidence: "E0" }],
    }),
    experience: before,
  });

  await finalizeRun(runId, { skillRoot });

  assert.equal(await readFile(path.join(skillRoot, "experience.local.md"), "utf8"), before);
});

test("缺失或重复必需标题时拒绝运行记录", () => {
  const markdown = validRun();
  const invalidDocuments = [
    markdown.replace("## 证据\n", "## 缺少证据标题\n"),
    `${markdown}\n## 任务\n\n- 扩展：重复标题\n`,
  ];

  for (const document of invalidDocuments) {
    assert.throws(() => validateRunMarkdown(document));
  }
});

test("任务、路由和复盘的必填字段缺失或为空时拒绝运行记录", () => {
  const base = validRun();
  const requiredItems = [
    "- 时间：2026-07-11T10:00:00.000Z",
    "- 类型：static-page",
    "- 需要已有登录态：否",
    "- 能力槽位：browser_without_existing_login",
    "- 检查候选：chrome-devtools",
    "- 实际链路：browser-control → chrome-devtools",
    "- 模式：primary",
    "- 结果：passed",
    "- 总体结果：success",
    "- 有效模式：测试中的可验证模式",
    "- 已验证根因：无",
    "- 下次规则候选：无",
    "- 建议归宿：none",
  ];

  for (const item of requiredItems) {
    assert.throws(() => validateRunMarkdown(base.replace(`${item}\n`, "")));
  }
  assert.throws(() =>
    validateRunMarkdown(
      base.replace(
        "- 实际链路：browser-control → chrome-devtools",
        "- 实际链路：",
      ),
    ),
  );

  for (const [from, to] of [
    ["- 需要已有登录态：否", "- 需要已有登录态：待填写"],
    ["- 需要已有登录态：否", "- 需要已有登录态：也许"],
    ["- 模式：primary", "- 模式：待填写"],
    ["- 模式：primary", "- 模式：随便"],
    ["- 检查候选：chrome-devtools", "- 检查候选：待填写"],
    [
      "- 能力槽位：browser_without_existing_login",
      "- 能力槽位：待填写",
    ],
  ]) {
    assert.throws(() => validateRunMarkdown(base.replace(from, to)));
  }
});

test("登录态、能力槽位与候选探测事实必须彼此一致", () => {
  const base = validRun();
  const contradictory = [
    base.replace("- 需要已有登录态：否", "- 需要已有登录态：是"),
    base
      .replace(
        "- 能力槽位：browser_without_existing_login",
        "- 能力槽位：browser_with_existing_login",
      )
      .replace("- 需要已有登录态：否", "- 需要已有登录态：否"),
    base.replace("- 检查候选：chrome-devtools", "- 检查候选：web-access"),
    base.replace(
      "- 检查候选：chrome-devtools",
      "- 检查候选：chrome-devtools、web-access",
    ),
    base.replace(
      "- 检查候选：chrome-devtools",
      "- 检查候选：chrome-devtools、chrome-devtools",
    ),
  ];

  for (const markdown of contradictory) {
    assert.throws(() => validateRunMarkdown(markdown));
  }

  assert.doesNotThrow(() =>
    validateRunMarkdown(
      base
        .replace("- 需要已有登录态：否", "- 需要已有登录态：是")
        .replace(
          "- 能力槽位：browser_without_existing_login",
          "- 能力槽位：browser_with_existing_login",
        ),
    ),
  );
});

test("每个下游 Skill 都必须逐一填写完整调用事实", () => {
  const base = validRun();
  const completeBlock = skillBlock();
  const requiredItems = [
    "- 承担能力：无登录态浏览器控制",
    "- 来源：测试候选",
    "- 版本：未知",
    "- 实际动作：navigate、snapshot",
    "- 输入：target、intent",
    "- 输出：browser_result、evidence",
    "- 结果：passed",
    "- 证据引用：E1",
    "- 摩擦：无",
  ];

  for (const item of requiredItems) {
    const incompleteBlock = completeBlock.replace(item, "");
    assert.throws(() =>
      validateRunMarkdown(base.replace(completeBlock, incompleteBlock)),
    );
  }
});

test("非法候选状态、任务结果或证据类型均被拒绝", () => {
  const markdown = validRun();
  const invalidDocuments = [
    markdown.replace("- 状态：available", "- 状态：unknown"),
    markdown.replace("- 结果：passed", "- 结果：unknown"),
    markdown.replace("- 类型：observation", "- 类型：binary"),
  ];

  for (const document of invalidDocuments) {
    assert.throws(() => validateRunMarkdown(document));
  }
});

test("下游 Skill 的悬空证据引用被拒绝", () => {
  const markdown = validRun().replace("- 证据引用：E1", "- 证据引用：E9");

  assert.throws(() => validateRunMarkdown(markdown));
});

test("证据块标题和所有状态及 Skill 证据引用必须使用 E 编号", () => {
  const base = validRun();
  const invalidDocuments = [
    base
      .replace("- 状态证据引用：E0", "- 状态证据引用：../../outside")
      .replace("### E0\n\n- 类型", "### ../../outside\n\n- 类型"),
    base
      .replace("- 证据引用：E1", "- 证据引用：arbitrary")
      .replace("### E1\n\n- 类型", "### arbitrary\n\n- 类型"),
    base.replace(
      "\n## 复盘",
      `\n### arbitrary

- 类型：artifact
- 引用：run://extra-evidence
- 证明：未被引用的证据标题也必须合法

## 复盘`,
    ),
  ];

  for (const markdown of invalidDocuments) {
    assert.throws(() => validateRunMarkdown(markdown));
  }
});

test("证据引用只允许本轮 E ID、run URI 或运行目录内相对路径", () => {
  const base = validRun();
  const withReference = (reference) =>
    base.replace("- 引用：run://evidence-E0", `- 引用：${reference}`);

  for (const reference of [
    "E0",
    "run://evidence-E0",
    "artifacts/evidence-E0.txt",
    "artifacts/evidence-E0.txt#proof",
  ]) {
    assert.doesNotThrow(() => validateRunMarkdown(withReference(reference)));
  }

  for (const reference of [
    "../../outside",
    "/tmp/outside",
    String.raw`C:\temp\outside`,
    String.raw`\\server\share\outside`,
    "file://outside",
    "ftp://outside",
    "run://evidence-E0?token=opaque",
    "artifacts/evidence-E0.txt?token=opaque",
  ]) {
    assert.throws(() => validateRunMarkdown(withReference(reference)));
  }
});

test("额外标题和短项目不破坏向前兼容", () => {
  const markdown = validRun({
    extra: "\n\n## 自定义扩展\n\n- 观察：这是一个短项目",
  });

  assert.doesNotThrow(() => validateRunMarkdown(markdown));
});

test("确定性安全扫描拒绝代码、HTML、凭证、URL 和超限内容", () => {
  const base = validRun();
  const jwt =
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
  const unsafeDocuments = [
    `${base}\n\`\`\`js\nconsole.log(1)\n\`\`\`\n`,
    `${base}\n- 扩展：<div>原始页面</div>\n`,
    `${base}\n- 扩展：http://example.invalid/private\n`,
    `${base}\n- 扩展：https://example.invalid/private\n`,
    `${base}\n- 扩展：${jwt}\n`,
    `${base}\n- 扩展：Authorization: Bearer opaque-value\n`,
    `${base}\n- 扩展：Cookie: session=opaque-value\n`,
    `${base}\n- 扩展：secret=opaque-value\n`,
    `${base}\n- 扩展：password=opaque-value\n`,
    `${base}\n- 扩展：token=opaque-value\n`,
    `${base}\n- 扩展：X-Request-Id: opaque-value\n`,
    `${base}\n- 扩展：${"x".repeat(501)}\n`,
    `${base}\n${"- 扩展：安全短项\n".repeat(5_000)}`,
  ];
  assert.ok(Buffer.byteLength(unsafeDocuments.at(-1), "utf8") > 64 * 1024);
  assert.doesNotThrow(() =>
    validateRunMarkdown(`${base}\n- 扩展：${"x".repeat(500)}\n`),
  );

  for (const document of unsafeDocuments) {
    assert.throws(() => validateRunMarkdown(document));
  }
});

test("证明字段恰好 240 字符通过，241 字符失败", () => {
  const base = validRun();
  const withProofLength = (length) =>
    base.replace(
      "- 证明：E0 对应的可验证短结论",
      `- 证明：${"证".repeat(length)}`,
    );

  assert.doesNotThrow(() => validateRunMarkdown(withProofLength(240)));
  assert.throws(() => validateRunMarkdown(withProofLength(241)));
});

test("run_id 与目标路径同时阻断 POSIX、盘符和 UNC 逃逸", () => {
  assert.equal(validateRunId("run-01"), "run-01");
  assert.equal(validateRunId("a".repeat(63)), "a".repeat(63));

  for (const runId of [
    "",
    "../escape",
    "folder/run",
    "/tmp/run",
    String.raw`C:\temp\run`,
    String.raw`\\server\share\run`,
    "UPPERCASE",
    "a".repeat(64),
  ]) {
    assert.throws(() => validateRunId(runId));
  }

  assert.equal(
    isPathInside("/safe/runs", "/safe/runs/run.md", path.posix),
    true,
  );
  assert.equal(
    isPathInside("/safe/runs", "/safe/escape.md", path.posix),
    false,
  );
  assert.equal(
    isPathInside("/safe/runs", "/safe/runs-evil/run.md", path.posix),
    false,
  );
  assert.equal(
    isPathInside(String.raw`C:\safe\runs`, String.raw`C:\safe\runs\run.md`, path.win32),
    true,
  );
  assert.equal(
    isPathInside(String.raw`C:\safe\runs`, String.raw`D:\safe\runs\run.md`, path.win32),
    false,
  );
  assert.equal(
    isPathInside(
      String.raw`C:\safe\runs`,
      String.raw`C:\safe\runs-evil\run.md`,
      path.win32,
    ),
    false,
  );
  assert.equal(
    isPathInside(
      String.raw`\\server\share\runs`,
      String.raw`\\server\share\runs\run.md`,
      path.win32,
    ),
    true,
  );
  assert.equal(
    isPathInside(
      String.raw`\\server\share\runs`,
      String.raw`\\server\other\runs\run.md`,
      path.win32,
    ),
    false,
  );
  assert.equal(
    isPathInside(
      String.raw`\\server\share\runs`,
      String.raw`\\server\share\runs-evil\run.md`,
      path.win32,
    ),
    false,
  );
});

test("LF 与 CRLF 均可解析，finalize 保持原换行风格", async (t) => {
  assert.doesNotThrow(() => validateRunMarkdown(validRun()));
  assert.doesNotThrow(() => validateRunMarkdown(validRun({ newline: "\r\n" })));

  const runId = "crlf-run";
  const skillRoot = await writeRunFixture(t, {
    runId,
    markdown: validRun({ runId, taskResult: "degraded", newline: "\r\n" }),
    experience: experienceMarkdown({ newline: "\r\n" }),
  });

  await finalizeRun(runId, { skillRoot });

  assertNoBareLf(
    await readFile(path.join(skillRoot, "runs.local", `${runId}.md`), "utf8"),
  );
  assertNoBareLf(await readFile(path.join(skillRoot, "experience.local.md"), "utf8"));
});

test("损坏的状态哨兵全部 fail closed", async (t) => {
  const candidate = "chrome-devtools";
  const other = "agent-browser";
  const valid = statusBlock({ candidate });
  const malformedBodies = [
    `### ${candidate}\n\n- 状态：available`,
    `${valid}\n\n${valid}`,
    `<!-- browser-control:status:${candidate}:start -->\n<!-- browser-control:status:${other}:start -->\n<!-- browser-control:status:${other}:end -->\n<!-- browser-control:status:${candidate}:end -->`,
    `<!-- browser-control:status:${candidate}:start -->\n<!-- browser-control:status:${other}:start -->\n<!-- browser-control:status:${candidate}:end -->\n<!-- browser-control:status:${other}:end -->`,
    `<!-- browser-control:status:${candidate}:start -->\n<!-- browser-control:status:${other}:end -->`,
  ];

  for (const [index, body] of malformedBodies.entries()) {
    const runId = `bad-sentinel-${index}`;
    const before = experienceMarkdown({ body });
    const skillRoot = await writeRunFixture(t, {
      runId,
      markdown: validRun({ runId }),
      experience: before,
    });

    await assert.rejects(async () => finalizeRun(runId, { skillRoot }));
    assert.equal(await readFile(path.join(skillRoot, "experience.local.md"), "utf8"), before);
  }
});

test("更新能力卡时完整保留哨兵外字节", async (t) => {
  const runId = "preserve-bytes";
  const prefix = `# Browser Control 本机经验\n\n手写前言：必须逐字保留。\n\n## 当前能力地图\n\n`;
  const suffix = `\n\n## 经晋升经验\n\n- 手写经验：包括空格  \n`;
  const before = `${prefix}${statusBlock()}${suffix}`;
  const skillRoot = await writeRunFixture(t, {
    runId,
    markdown: validRun({
      runId,
      probes: [{ id: "chrome-devtools", status: "degraded", evidence: "E0" }],
      taskResult: "degraded",
    }),
    experience: before,
  });

  await finalizeRun(runId, { skillRoot });

  const after = await readFile(path.join(skillRoot, "experience.local.md"), "utf8");
  assert.ok(after.startsWith(prefix));
  assert.ok(after.endsWith(suffix));
  assert.match(after, /- 状态：degraded/);
  assert.match(after, new RegExp(`runs\\.local/${runId}\\.md#E0`));
});

test("只有可验证探测状态才会首次创建 experience.local.md", async (t) => {
  const uncheckedRunId = "unchecked-first";
  const uncheckedRoot = await writeRunFixture(t, {
    runId: uncheckedRunId,
    markdown: validRun({
      runId: uncheckedRunId,
      probes: [{ id: "chrome-devtools", status: "not_checked", evidence: "E0" }],
    }),
  });
  await finalizeRun(uncheckedRunId, { skillRoot: uncheckedRoot });
  assert.equal(await fileExists(path.join(uncheckedRoot, "experience.local.md")), false);

  const availableRunId = "available-first";
  const availableRoot = await writeRunFixture(t, {
    runId: availableRunId,
    markdown: validRun({ runId: availableRunId, taskResult: "failed" }),
  });
  await finalizeRun(availableRunId, { skillRoot: availableRoot });
  const created = await readFile(path.join(availableRoot, "experience.local.md"), "utf8");
  assert.match(created, /^## 当前能力地图$/m);
  assert.match(created, /^## 经晋升经验$/m);
  assert.match(created, /browser-control:status:chrome-devtools:start/);
  assert.match(created, /- 状态：available/);
});

test("finalize 保留多下游调用链与 fallback 事实", async (t) => {
  const runId = "fallback-chain";
  const routeChain =
    "browser-control → web-connect → web-access:web-access → agent-browser";
  const markdown = validRun({
    runId,
    mode: "fallback",
    taskResult: "degraded",
    routeChain,
    usedSkills: [
      { id: "web-connect", capability: "登录态适配", result: "passed", evidence: "E1" },
      {
        id: "web-access:web-access",
        capability: "当前页面控制",
        result: "failed",
        evidence: "E2",
      },
      { id: "agent-browser", capability: "降级浏览器控制", result: "passed", evidence: "E3" },
    ],
  });
  const skillRoot = await writeRunFixture(t, { runId, markdown });

  await finalizeRun(runId, { skillRoot });

  const after = await readFile(path.join(skillRoot, "runs.local", `${runId}.md`), "utf8");
  assert.match(after, new RegExp(`- 实际链路：${routeChain}`));
  assert.match(after, /- 模式：fallback/);
  assert.match(after, /^### web-connect$/m);
  assert.match(after, /^### web-access:web-access$/m);
  assert.match(after, /^### agent-browser$/m);
});

test("resolveSkillRoot 仅依据模块 URL，不依赖当前工作目录", async (t) => {
  const fixture = await temporarySkillRoot(t);
  const expectedRoot = path.join(fixture, "installed-skill");
  const scriptUrl = pathToFileURL(
    path.join(expectedRoot, "scripts", "usage-ledger.mjs"),
  ).href;
  const unrelatedCwd = path.join(fixture, "unrelated-cwd");
  await mkdir(unrelatedCwd);
  const originalCwd = process.cwd();

  try {
    process.chdir(unrelatedCwd);
    assert.equal(resolveSkillRoot(scriptUrl), expectedRoot);
  } finally {
    process.chdir(originalCwd);
  }
});
