import { randomUUID } from "node:crypto";
import { realpathSync } from "node:fs";
import {
  link,
  mkdir,
  open,
  readFile,
  rename,
  rm,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const RUN_ID_RE = /^[a-z0-9](?:[a-z0-9-]{0,62})$/;
export const CANDIDATE_ID_RE = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

const REQUIRED_SECTIONS = [
  "任务",
  "候选探测",
  "路由决定",
  "实际使用的 Skills",
  "证据",
  "复盘",
];
const PROBE_STATUSES = new Set([
  "available",
  "degraded",
  "missing",
  "not_checked",
]);
const TASK_RESULTS = new Set(["passed", "degraded", "failed"]);
const LOGIN_DECISIONS = new Set(["是", "否"]);
const LOGIN_DECISION_SOURCES = new Set([
  "user_confirmation",
  "explicit_request",
  "local_record",
  "intrinsic_context",
]);
const ROUTE_MODES = new Set(["primary", "fallback"]);
const CAPABILITY_SLOTS = new Set([
  "browser_without_existing_login",
  "browser_with_existing_login",
  "web_information_discovery",
]);
const EVIDENCE_TYPES = new Set([
  "artifact",
  "test",
  "observation",
  "user_confirmation",
]);
const MAX_BYTES = 64 * 1024;
const MAX_ITEM_LENGTH = 500;
const MAX_PROOF_LENGTH = 240;
const EVIDENCE_ID_RE = /^E[0-9]+$/;

export function resolveSkillRoot(metaUrl = import.meta.url) {
  return path.resolve(path.dirname(fileURLToPath(metaUrl)), "..");
}

export function validateRunId(runId) {
  if (typeof runId !== "string" || !RUN_ID_RE.test(runId)) {
    throw new Error("非法 run_id");
  }
  return runId;
}

function validateCandidateId(candidateId) {
  if (typeof candidateId !== "string" || !CANDIDATE_ID_RE.test(candidateId)) {
    throw new Error("候选 ID 必须是安全的 kebab-case");
  }
  return candidateId;
}

export function isPathInside(rootPath, targetPath, pathApi = path) {
  const root = pathApi.resolve(rootPath);
  const target = pathApi.resolve(targetPath);
  const relative = pathApi.relative(root, target);

  return (
    relative === "" ||
    (!pathApi.isAbsolute(relative) &&
      relative !== ".." &&
      !relative.startsWith(`..${pathApi.sep}`))
  );
}

export function buildRunTemplate(runId) {
  const safeRunId = validateRunId(runId);
  return `# Browser Control Run: ${safeRunId}

## 任务

- 时间：${new Date().toISOString()}
- 类型：待填写
- 需要已有登录态：待填写
- 登录态判断来源：待填写

## 候选探测

- 待填写：候选、状态与状态证据

## 路由决定

- 能力槽位：待填写
- 检查候选：待填写
- 实际链路：browser-control
- 模式：待填写
- 结果：待填写

## 实际使用的 Skills

- 待填写：实际调用链、结果与证据

## 证据

- 待填写：只记录脱敏后的可验证短结论

## 复盘

- 总体结果：待填写
- 有效模式：无
- 已验证根因：无
- 下次规则候选：无
- 建议归宿：none
`;
}

function splitLines(markdown) {
  if (typeof markdown !== "string") {
    throw new Error("运行记录必须是 Markdown 文本");
  }
  const normalized = markdown.replaceAll("\r\n", "\n");
  if (normalized.includes("\r")) {
    throw new Error("运行记录包含不支持的换行符");
  }
  return normalized.split("\n");
}

function sectionLines(lines, title) {
  const marker = `## ${title}`;
  const starts = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index] === marker) starts.push(index);
  }
  if (starts.length !== 1) {
    throw new Error(`必需标题 ${marker} 必须且只能出现一次`);
  }

  const start = starts[0] + 1;
  let end = lines.length;
  for (let index = start; index < lines.length; index += 1) {
    if (/^## (?!#)/.test(lines[index])) {
      end = index;
      break;
    }
  }
  return lines.slice(start, end);
}

function subsectionBlocks(lines) {
  const blocks = [];
  let current;

  for (const line of lines) {
    const heading = line.match(/^### (.+)$/);
    if (heading) {
      current = { id: heading[1], lines: [] };
      blocks.push(current);
    } else if (current) {
      current.lines.push(line);
    }
  }
  return blocks;
}

function fieldsFrom(lines) {
  const fields = new Map();
  for (const line of lines) {
    const match = line.match(/^- ([^：:]+)[：:](.*)$/);
    if (!match) continue;
    const key = match[1].trim();
    const value = match[2].trim();
    if (!fields.has(key)) fields.set(key, []);
    fields.get(key).push(value);
  }
  return fields;
}

function exactlyOne(fields, key, context) {
  const values = fields.get(key) ?? [];
  if (values.length !== 1 || values[0] === "") {
    throw new Error(`${context} 的 ${key} 必须且只能填写一次`);
  }
  return values[0];
}

function isValidIsoTimestamp(value) {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(?:Z|[+-](\d{2}):(\d{2}))$/,
  );
  if (!match) return false;

  const [, yearText, monthText, dayText, hourText, minuteText, secondText] =
    match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const offsetHour = match[7] === undefined ? 0 : Number(match[7]);
  const offsetMinute = match[8] === undefined ? 0 : Number(match[8]);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [
    31,
    leapYear ? 29 : 28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
  ];

  return (
    year > 0 &&
    month >= 1 &&
    month <= 12 &&
    day >= 1 &&
    day <= daysInMonth[month - 1] &&
    hour <= 23 &&
    minute <= 59 &&
    second <= 59 &&
    offsetHour <= 23 &&
    offsetMinute <= 59 &&
    Number.isFinite(Date.parse(value))
  );
}

function scanSafety(markdown, lines) {
  if (Buffer.byteLength(markdown, "utf8") > MAX_BYTES) {
    throw new Error("运行记录超过 64 KiB");
  }
  if (/(^|\n)\s*(?:```|~~~)/.test(markdown)) {
    throw new Error("运行记录不得包含 fenced code block");
  }
  if (/<(?:!--|\/?[A-Za-z][^>]*>)/.test(markdown)) {
    throw new Error("运行记录不得包含原始 HTML");
  }
  if (/\bhttps?:\/\/\S+/i.test(markdown)) {
    throw new Error("运行记录不得包含 HTTP(S) URL");
  }
  if (/\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/.test(markdown)) {
    throw new Error("运行记录疑似包含 JWT");
  }
  if (
    /\b(?:authorization|proxy-authorization|cookie|set-cookie|secret|password|passwd|token|api[-_]?key|client[-_]?secret|session(?:id)?|x-[a-z0-9-]+)\s*[:=]/i.test(
      markdown,
    )
  ) {
    throw new Error("运行记录疑似包含凭证或请求头");
  }

  for (const line of lines) {
    if (line === "" || /^(?:#{1,6}) .+$/.test(line)) continue;
    if (!line.startsWith("- ")) {
      throw new Error("运行记录只允许标题、空行和单行项目");
    }
    const item = line.slice(2);
    const separator = item.search(/[：:]/);
    const value = separator === -1 ? item : item.slice(separator + 1).trim();
    const length = Array.from(value).length;
    if (length > MAX_ITEM_LENGTH) {
      throw new Error("单行项目值超过 500 字符");
    }
    const key = separator === -1 ? "" : item.slice(0, separator).trim();
    if (key === "证明" && length > MAX_PROOF_LENGTH) {
      throw new Error("证明字段超过 240 字符");
    }
  }
}

function validateEvidenceLocation(reference, evidenceIds) {
  if (reference.includes("?")) {
    throw new Error("证据引用不得包含 query");
  }
  if (/^E\d+$/.test(reference)) {
    if (!evidenceIds.has(reference)) {
      throw new Error(`证据引用指向未登记编号 ${reference}`);
    }
    return;
  }
  if (reference.startsWith("run://")) {
    const target = reference.slice("run://".length);
    const pathPart = target.split("#", 1)[0];
    if (
      !/^[A-Za-z0-9][A-Za-z0-9._/-]*(?:#[A-Za-z0-9._:-]+)?$/.test(target) ||
      pathPart.split("/").includes("..")
    ) {
      throw new Error("非法 run:// 证据引用");
    }
    return;
  }
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(reference)) {
    throw new Error("证据引用只允许 run:// scheme");
  }

  const pathPart = reference.split("#", 1)[0];
  const portablePath = pathPart.replaceAll("\\", "/");
  if (
    pathPart === "" ||
    path.posix.isAbsolute(portablePath) ||
    path.win32.isAbsolute(pathPart) ||
    portablePath.split("/").includes("..")
  ) {
    throw new Error("证据相对路径逃逸 runs.local");
  }
}

export function parseProbeStatuses(markdown) {
  const lines = splitLines(markdown);
  const blocks = subsectionBlocks(sectionLines(lines, "候选探测"));
  if (blocks.length === 0) {
    throw new Error("候选探测至少需要一个候选");
  }

  const probes = new Map();
  for (const block of blocks) {
    validateCandidateId(block.id);
    if (probes.has(block.id)) {
      throw new Error(`候选探测重复：${block.id}`);
    }
    const fields = fieldsFrom(block.lines);
    const status = exactlyOne(fields, "状态", `候选 ${block.id}`);
    const checkedAt = exactlyOne(fields, "检查时间", `候选 ${block.id}`);
    const evidence = exactlyOne(fields, "状态证据引用", `候选 ${block.id}`);
    if (!PROBE_STATUSES.has(status)) {
      throw new Error(`候选 ${block.id} 的状态非法`);
    }
    if (!EVIDENCE_ID_RE.test(evidence)) {
      throw new Error(`候选 ${block.id} 的状态证据引用必须是 E 编号`);
    }
    if (!isValidIsoTimestamp(checkedAt)) {
      throw new Error(`候选 ${block.id} 的检查时间不是有效 ISO-8601 时间`);
    }
    probes.set(block.id, {
      id: block.id,
      status,
      checkedAt,
      version: fields.get("版本")?.[0],
      evidence,
    });
  }
  return probes;
}

export function validateRunMarkdown(markdown, { expectedRunId } = {}) {
  const lines = splitLines(markdown);
  scanSafety(markdown, lines);

  const runHeadings = lines
    .map((line) => line.match(/^# Browser Control Run: (.+)$/)?.[1])
    .filter((value) => value !== undefined);
  if (runHeadings.length !== 1) {
    throw new Error("运行记录 H1 必须且只能出现一次");
  }
  const documentRunId = validateRunId(runHeadings[0]);
  if (expectedRunId !== undefined && documentRunId !== validateRunId(expectedRunId)) {
    throw new Error("运行记录 H1 与 run_id 不一致");
  }

  for (const title of REQUIRED_SECTIONS) sectionLines(lines, title);

  const taskFields = fieldsFrom(sectionLines(lines, "任务"));
  const task = {
    time: exactlyOne(taskFields, "时间", "任务"),
    type: exactlyOne(taskFields, "类型", "任务"),
    needsExistingLogin: exactlyOne(taskFields, "需要已有登录态", "任务"),
    loginDecisionSource: exactlyOne(
      taskFields,
      "登录态判断来源",
      "任务",
    ),
  };
  if (!isValidIsoTimestamp(task.time)) {
    throw new Error("任务时间不是有效 ISO-8601 时间");
  }
  if (task.type === "待填写") throw new Error("任务类型仍是占位值");
  if (!LOGIN_DECISIONS.has(task.needsExistingLogin)) {
    throw new Error("是否需要已有登录态只能填写是或否");
  }
  if (!LOGIN_DECISION_SOURCES.has(task.loginDecisionSource)) {
    throw new Error("登录态判断来源非法");
  }
  const probes = parseProbeStatuses(markdown);
  const routeFields = fieldsFrom(sectionLines(lines, "路由决定"));
  const capabilitySlot = exactlyOne(routeFields, "能力槽位", "路由决定");
  const checkedCandidates = exactlyOne(routeFields, "检查候选", "路由决定");
  const routeChain = exactlyOne(routeFields, "实际链路", "路由决定");
  const routeMode = exactlyOne(routeFields, "模式", "路由决定");
  const taskResult = exactlyOne(routeFields, "结果", "路由决定");
  if (!CAPABILITY_SLOTS.has(capabilitySlot)) throw new Error("能力槽位非法");
  if (checkedCandidates === "待填写") throw new Error("检查候选仍是占位值");
  if (!ROUTE_MODES.has(routeMode)) throw new Error("路由模式非法");
  const expectedLoginDecision =
    capabilitySlot === "browser_with_existing_login" ? "是" : "否";
  if (task.needsExistingLogin !== expectedLoginDecision) {
    throw new Error("登录态判断与能力槽位矛盾");
  }
  const checkedCandidateIds = checkedCandidates
    .split(/[、,，]/)
    .map((candidate) => candidate.trim())
    .filter(Boolean);
  for (const candidateId of checkedCandidateIds) validateCandidateId(candidateId);
  const checkedCandidateSet = new Set(checkedCandidateIds);
  if (
    checkedCandidateSet.size !== checkedCandidateIds.length ||
    checkedCandidateSet.size !== probes.size ||
    [...probes.keys()].some((candidateId) => !checkedCandidateSet.has(candidateId))
  ) {
    throw new Error("检查候选必须与候选探测列表完全一致");
  }
  if (!TASK_RESULTS.has(taskResult)) {
    throw new Error("任务结果非法");
  }

  const usedSkills = subsectionBlocks(
    sectionLines(lines, "实际使用的 Skills"),
  ).map((block) => {
    const fields = fieldsFrom(block.lines);
    const context = `下游 Skill ${block.id}`;
    const capability = exactlyOne(fields, "承担能力", context);
    const source = exactlyOne(fields, "来源", context);
    const version = exactlyOne(fields, "版本", context);
    const action = exactlyOne(fields, "实际动作", context);
    const input = exactlyOne(fields, "输入", context);
    const output = exactlyOne(fields, "输出", context);
    const result = exactlyOne(fields, "结果", `下游 Skill ${block.id}`);
    const evidence = exactlyOne(fields, "证据引用", `下游 Skill ${block.id}`);
    const friction = exactlyOne(fields, "摩擦", context);
    if (!TASK_RESULTS.has(result)) {
      throw new Error(`下游 Skill ${block.id} 的结果非法`);
    }
    if (!EVIDENCE_ID_RE.test(evidence)) {
      throw new Error(`下游 Skill ${block.id} 的证据引用必须是 E 编号`);
    }
    return {
      id: block.id,
      capability,
      source,
      version,
      action,
      input,
      output,
      result,
      evidence,
      friction,
      fields,
    };
  });
  if (usedSkills.length === 0) {
    throw new Error("至少需要记录一个实际使用的 Skill");
  }

  const evidence = new Map();
  for (const block of subsectionBlocks(sectionLines(lines, "证据"))) {
    if (!EVIDENCE_ID_RE.test(block.id)) {
      throw new Error(`证据块标题必须是 E 编号：${block.id}`);
    }
    if (evidence.has(block.id)) throw new Error(`证据编号重复：${block.id}`);
    const fields = fieldsFrom(block.lines);
    const type = exactlyOne(fields, "类型", `证据 ${block.id}`);
    const reference = exactlyOne(fields, "引用", `证据 ${block.id}`);
    const proof = exactlyOne(fields, "证明", `证据 ${block.id}`);
    if (!EVIDENCE_TYPES.has(type)) {
      throw new Error(`证据 ${block.id} 的类型非法`);
    }
    evidence.set(block.id, { id: block.id, type, reference, proof });
  }
  if (evidence.size === 0) throw new Error("至少需要登记一条证据");

  for (const item of evidence.values()) {
    validateEvidenceLocation(item.reference, evidence);
  }

  for (const probe of probes.values()) {
    if (!evidence.has(probe.evidence)) {
      throw new Error(`候选 ${probe.id} 引用了未登记证据 ${probe.evidence}`);
    }
  }
  for (const skill of usedSkills) {
    if (!evidence.has(skill.evidence)) {
      throw new Error(`下游 Skill ${skill.id} 引用了未登记证据 ${skill.evidence}`);
    }
  }

  const retrospectiveFields = fieldsFrom(sectionLines(lines, "复盘"));
  const retrospective = {
    overallResult: exactlyOne(retrospectiveFields, "总体结果", "复盘"),
    effectivePattern: exactlyOne(retrospectiveFields, "有效模式", "复盘"),
    verifiedRootCause: exactlyOne(retrospectiveFields, "已验证根因", "复盘"),
    nextRuleCandidate: exactlyOne(retrospectiveFields, "下次规则候选", "复盘"),
    suggestedDestination: exactlyOne(retrospectiveFields, "建议归宿", "复盘"),
  };

  return {
    runId: documentRunId,
    task,
    probes,
    taskResult,
    route: {
    capabilitySlot,
    checkedCandidates,
      chain: routeChain,
      mode: routeMode,
    },
    usedSkills,
    evidence,
    retrospective,
    newline: markdown.includes("\r\n") ? "\r\n" : "\n",
  };
}

function runPathFor(runId, skillRoot) {
  const safeRunId = validateRunId(runId);
  const runsDirectory = path.resolve(skillRoot, "runs.local");
  const runPath = path.resolve(runsDirectory, `${safeRunId}.md`);
  if (!isPathInside(runsDirectory, runPath)) {
    throw new Error("运行记录路径逃逸 runs.local");
  }
  return { runsDirectory, runPath };
}

function validateInitialMarkdown(runId, markdown) {
  const lines = splitLines(markdown);
  scanSafety(markdown, lines);
  for (const title of REQUIRED_SECTIONS) sectionLines(lines, title);
  const expectedTitle = `# Browser Control Run: ${runId}`;
  if (lines.filter((line) => line === expectedTitle).length !== 1) {
    throw new Error("运行记录标题必须与 run_id 一致且只能出现一次");
  }
}

async function writeSyncedTemporary(directory, basename, content) {
  const temporaryPath = path.join(
    directory,
    `.${basename}.${process.pid}.${randomUUID()}.tmp`,
  );
  let handle;
  try {
    handle = await open(temporaryPath, "wx", 0o600);
    await handle.writeFile(content, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    return temporaryPath;
  } catch (error) {
    if (handle) await handle.close().catch(() => {});
    await rm(temporaryPath, { force: true }).catch(() => {});
    throw error;
  }
}

async function publishExclusive(directory, targetPath, content) {
  const temporaryPath = await writeSyncedTemporary(
    directory,
    path.basename(targetPath),
    content,
  );
  try {
    await link(temporaryPath, targetPath);
  } catch (error) {
    if (error?.code === "EEXIST") {
      const existsError = new Error(`运行记录已存在：${path.basename(targetPath)}`);
      existsError.code = "EEXIST";
      throw existsError;
    }
    throw error;
  } finally {
    await rm(temporaryPath, { force: true }).catch(() => {});
  }
}

async function replaceAtomically(targetPath, content) {
  const directory = path.dirname(targetPath);
  const temporaryPath = await writeSyncedTemporary(
    directory,
    path.basename(targetPath),
    content,
  );
  try {
    await rename(temporaryPath, targetPath);
  } finally {
    await rm(temporaryPath, { force: true }).catch(() => {});
  }
}

function lockOwnerMarkdown(token) {
  return `# Usage Ledger Lock\n\n- PID：${process.pid}\n- Token：${token}\n- 创建时间：${new Date().toISOString()}\n`;
}

function parseLockOwner(markdown) {
  const pid = Number(markdown.match(/^- PID：[ ]?([0-9]+)$/m)?.[1]);
  const token = markdown.match(/^- Token：([^\r\n]+)$/m)?.[1];
  if (!Number.isSafeInteger(pid) || pid <= 0 || !token) {
    throw new Error("账本锁 owner.md 损坏；为安全起见拒绝自动删除");
  }
  return { pid, token };
}

function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (error?.code === "ESRCH") return false;
    return true;
  }
}

async function publishLockDirectory(skillRoot, lockPath, token) {
  const temporaryLock = path.resolve(
    skillRoot,
    `.usage-ledger.lock.${process.pid}.${randomUUID()}.tmp`,
  );
  await mkdir(temporaryLock, { mode: 0o700 });
  try {
    const ownerPath = path.join(temporaryLock, "owner.md");
    const handle = await open(ownerPath, "wx", 0o600);
    try {
      await handle.writeFile(lockOwnerMarkdown(token), "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporaryLock, lockPath);
  } finally {
    await rm(temporaryLock, { recursive: true, force: true }).catch(() => {});
  }
}

async function recoverDeadLock(lockPath) {
  const ownerPath = path.join(lockPath, "owner.md");
  let ownerMarkdown;
  try {
    ownerMarkdown = await readFile(ownerPath, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }
  const owner = parseLockOwner(ownerMarkdown);
  if (isProcessAlive(owner.pid)) {
    throw new Error("账本已锁定：另一个 finalize 正在进行中");
  }
  const quarantine = `${lockPath}.stale.${randomUUID()}`;
  try {
    await rename(lockPath, quarantine);
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }
  const movedOwner = parseLockOwner(
    await readFile(path.join(quarantine, "owner.md"), "utf8"),
  );
  if (movedOwner.token !== owner.token) {
    throw new Error("账本锁在恢复期间发生变化；拒绝继续");
  }
  await rm(quarantine, { recursive: true, force: true });
}

async function withFinalizeLock(skillRoot, operation) {
  const lockPath = path.resolve(skillRoot, ".usage-ledger.lock");
  if (!isPathInside(skillRoot, lockPath)) {
    throw new Error("账本锁路径逃逸 Skill 根目录");
  }
  const token = randomUUID();
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      await publishLockDirectory(skillRoot, lockPath, token);
      break;
    } catch (error) {
      if (!["EEXIST", "ENOTEMPTY", "EPERM"].includes(error?.code)) throw error;
      if (attempt === 1) {
        throw new Error("账本已锁定：另一个 finalize 正在进行中");
      }
      await recoverDeadLock(lockPath);
    }
  }

  try {
    return await operation();
  } finally {
    try {
      const owner = parseLockOwner(
        await readFile(path.join(lockPath, "owner.md"), "utf8"),
      );
      if (owner.token === token) {
        await rm(lockPath, { recursive: true, force: true });
      }
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
  }
}

export async function initRun(
  runId,
  { skillRoot = resolveSkillRoot(), markdown = buildRunTemplate(runId) } = {},
) {
  const safeRunId = validateRunId(runId);
  validateInitialMarkdown(safeRunId, markdown);
  const { runsDirectory, runPath } = runPathFor(safeRunId, skillRoot);
  await mkdir(runsDirectory, { recursive: true });
  await publishExclusive(runsDirectory, runPath, markdown);
  return runPath;
}

const STATUS_MARKER_PREFIX = "<!-- browser-control:status:";
const STATUS_MARKER_RE =
  /^<!-- browser-control:status:(.+):(start|end) -->$/;

function parseStatusMarkers(markdown) {
  const markers = [];
  const lines = markdown.match(/.*(?:\r\n|\n|$)/g) ?? [];
  let offset = 0;
  for (const lineWithEnding of lines) {
    if (lineWithEnding === "") continue;
    const line = lineWithEnding.replace(/(?:\r\n|\n)$/, "");
    const start = offset;
    const ending = lineWithEnding.match(/(?:\r\n|\n)$/)?.[0] ?? "";
    const end = offset + lineWithEnding.length - ending.length;
    offset += lineWithEnding.length;
    if (!line.includes(STATUS_MARKER_PREFIX)) continue;
    const match = line.match(STATUS_MARKER_RE);
    if (!match || match[1].trim() !== match[1] || match[1] === "") {
      throw new Error("experience.local.md 包含损坏的能力状态哨兵");
    }
    markers.push({ id: match[1], kind: match[2], start, end });
  }

  const pairs = new Map();
  let active;
  for (const marker of markers) {
    if (marker.kind === "start") {
      if (active || pairs.has(marker.id)) {
        throw new Error("能力状态哨兵重复、嵌套或交叉");
      }
      active = marker;
      continue;
    }
    if (!active || active.id !== marker.id) {
      throw new Error("能力状态哨兵错配或缺少 start");
    }
    pairs.set(marker.id, {
      start: active.start,
      end: marker.end,
    });
    active = undefined;
  }
  if (active) throw new Error("能力状态哨兵缺少 end");
  return pairs;
}

function sectionBounds(markdown, title) {
  const marker = `## ${title}`;
  const headingRe = /^## (?!#).+$/gm;
  const headings = [];
  for (const match of markdown.matchAll(headingRe)) {
    headings.push({ title: match[0], index: match.index });
  }
  const matches = headings.filter((heading) => heading.title === marker);
  if (matches.length !== 1) {
    throw new Error(`${marker} 必须且只能出现一次`);
  }
  const headingIndex = headings.indexOf(matches[0]);
  return {
    start: matches[0].index + marker.length,
    end: headings[headingIndex + 1]?.index ?? markdown.length,
  };
}

function statusBlockFor(probe, runId, newline) {
  return [
    `<!-- browser-control:status:${probe.id}:start -->`,
    `### ${probe.id}`,
    "",
    `- 状态：${probe.status}`,
    `- 检查时间：${probe.checkedAt}`,
    ...(probe.version ? [`- 版本：${probe.version}`] : []),
    `- 状态证据引用：runs.local/${runId}.md#${probe.evidence}`,
    `<!-- browser-control:status:${probe.id}:end -->`,
  ].join(newline);
}

function createExperience(probes, runId, newline) {
  const blocks = probes.map((probe) => statusBlockFor(probe, runId, newline));
  return [
    "# Browser Control 本机经验",
    "",
    "## 当前能力地图",
    "",
    blocks.join(`${newline}${newline}`),
    "",
    "## 经晋升经验",
    "",
    "- 暂无经晋升经验",
    "",
  ].join(newline);
}

function updateExperience(markdown, probes, runId, newline) {
  const pairs = parseStatusMarkers(markdown);
  const abilityBounds = sectionBounds(markdown, "当前能力地图");
  for (const pair of pairs.values()) {
    if (pair.start < abilityBounds.start || pair.end > abilityBounds.end) {
      throw new Error("能力状态哨兵必须位于当前能力地图内");
    }
  }
  if (pairs.size === 0) {
    const body = markdown.slice(abilityBounds.start, abilityBounds.end).trim();
    if (body !== "" && body !== "- 暂无能力状态") {
      throw new Error("当前能力地图存在未受哨兵保护的状态内容");
    }
  }

  const replacements = [];
  const missing = [];
  for (const probe of probes) {
    const block = statusBlockFor(probe, runId, newline);
    const pair = pairs.get(probe.id);
    if (pair) replacements.push({ ...pair, block });
    else missing.push(block);
  }
  replacements.sort((left, right) => right.start - left.start);
  let updated = markdown;
  for (const replacement of replacements) {
    updated =
      updated.slice(0, replacement.start) +
      replacement.block +
      updated.slice(replacement.end);
  }

  if (missing.length > 0) {
    const bounds = sectionBounds(updated, "当前能力地图");
    const before = updated.slice(0, bounds.end);
    const after = updated.slice(bounds.end);
    const separator = before.endsWith(`${newline}${newline}`)
      ? ""
      : before.endsWith(newline)
        ? newline
        : `${newline}${newline}`;
    updated = `${before}${separator}${missing.join(`${newline}${newline}`)}${newline}${newline}${after}`;
  }
  return updated;
}

function ledgerStatus(markdown) {
  const values = [...markdown.matchAll(/^- 账本状态：(finalizing|finalized)$/gm)].map(
    (match) => match[1],
  );
  if (values.length > 1) throw new Error("运行记录包含重复账本状态");
  return values[0];
}

function markFinalizing(markdown, newline) {
  const status = ledgerStatus(markdown);
  if (status === "finalized") {
    throw new Error("运行记录已经 finalized");
  }
  if (status === "finalizing") return markdown;
  const separator = markdown.endsWith(newline) ? newline : `${newline}${newline}`;
  return `${markdown}${separator}## 账本状态${newline}${newline}- 账本状态：finalizing${newline}`;
}

function markFinalized(markdown) {
  if (ledgerStatus(markdown) !== "finalizing") {
    throw new Error("运行记录不在 finalizing 状态");
  }
  return markdown.replace(
    /^- 账本状态：finalizing$/m,
    "- 账本状态：finalized",
  );
}

export async function finalizeRun(
  runId,
  { skillRoot = resolveSkillRoot() } = {},
) {
  const safeRunId = validateRunId(runId);
  return withFinalizeLock(skillRoot, async () => {
    const { runPath } = runPathFor(safeRunId, skillRoot);
    const markdown = await readFile(runPath, "utf8");
    if (ledgerStatus(markdown) === "finalized") {
      throw new Error("运行记录已经 finalized");
    }
    const validated = validateRunMarkdown(markdown, {
      expectedRunId: safeRunId,
    });
    const verifiedProbes = [...validated.probes.values()].filter(
      (probe) =>
        probe.status !== "not_checked" && validated.evidence.has(probe.evidence),
    );
    const experiencePath = path.resolve(skillRoot, "experience.local.md");
    let nextExperience;
    try {
      const currentExperience = await readFile(experiencePath, "utf8");
      const newline = currentExperience.includes("\r\n") ? "\r\n" : "\n";
      const updatedExperience = updateExperience(
        currentExperience,
        verifiedProbes,
        safeRunId,
        newline,
      );
      if (updatedExperience !== currentExperience) {
        nextExperience = updatedExperience;
      }
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
      if (verifiedProbes.length > 0) {
        nextExperience = createExperience(
          verifiedProbes,
          safeRunId,
          validated.newline,
        );
      }
    }

    const finalizingRun = markFinalizing(markdown, validated.newline);
    if (finalizingRun !== markdown) {
      await replaceAtomically(runPath, finalizingRun);
    }
    if (nextExperience !== undefined) {
      await replaceAtomically(experiencePath, nextExperience);
    }
    await replaceAtomically(runPath, markFinalized(finalizingRun));
    return { runPath, experienceUpdated: nextExperience !== undefined };
  });
}

async function runCli(argv) {
  const [command, runId, ...extra] = argv;
  if (!command || !runId || extra.length > 0) {
    throw new Error("用法：usage-ledger.mjs <init|validate|finalize> <run-id>");
  }
  const skillRoot = resolveSkillRoot(import.meta.url);
  if (command === "init") {
    const runPath = await initRun(runId, { skillRoot });
    process.stdout.write(`${runPath}\n`);
    return;
  }
  if (command === "validate") {
    const { runPath } = runPathFor(runId, skillRoot);
    validateRunMarkdown(await readFile(runPath, "utf8"), {
      expectedRunId: runId,
    });
    process.stdout.write(`${runPath}\n`);
    return;
  }
  if (command === "finalize") {
    const { runPath } = await finalizeRun(runId, { skillRoot });
    process.stdout.write(`${runPath}\n`);
    return;
  }
  throw new Error(`未知命令：${command}`);
}

function isDirectExecution() {
  if (!process.argv[1]) return false;
  try {
    return (
      realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))
    );
  } catch {
    return false;
  }
}

if (isDirectExecution()) {
  runCli(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error?.code ? `${error.code}: ` : ""}${error.message}\n`);
    process.exitCode = 1;
  });
}
