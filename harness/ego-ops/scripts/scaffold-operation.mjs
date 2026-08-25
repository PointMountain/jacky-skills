#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const defaults = { root: resolve(scriptDir, "..") };
const repeatable = new Set(["alias", "step", "checkpoint", "evidence"]);
const required = [
  "site",
  "domain",
  "operation",
  "title",
  "intent",
  "risk",
  "date",
  "entry",
  "step",
  "checkpoint",
  "success",
  "evidence",
];
const forbiddenPlaceholder = /\b(?:todo|tbd|placeholder|required)\b/i;

function usage(exitCode = 0) {
  console.log(`用法：node scaffold-operation.mjs [--root <skill-dir>] \\
  --site <site-slug> --domain <canonical-domain> --operation <operation-slug> \\
  --title <中文标题> --intent <目标> --risk <low|medium|high> --date <YYYY-MM-DD> \\
  --entry <入口> --step <已验证步骤> --checkpoint <检查点> \\
  --success <成功标准> --evidence <验证证据> [--alias <别名> ...]`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const result = { ...defaults };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--help" || token === "-h") usage();
    if (!token.startsWith("--")) throw new Error(`无法识别参数：${token}`);
    const key = token.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`${token} 缺少值`);
    index += 1;
    if (repeatable.has(key)) result[key] = [...(result[key] ?? []), value];
    else if (result[key] !== undefined && key !== "root") throw new Error(`${token} 不可重复`);
    else result[key] = value;
  }
  return result;
}

function assertSafeText(key, value) {
  const values = Array.isArray(value) ? value : [value];
  if (values.length === 0 || values.some((item) => !item?.trim())) {
    throw new Error(`--${key} 必须至少提供一个非空值`);
  }
  for (const item of values) {
    if (/\r|\n/.test(item) || forbiddenPlaceholder.test(item)) {
      throw new Error(`--${key} 不能包含换行或未完成占位符`);
    }
  }
}

function assertSlug(key, value) {
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value)) {
    throw new Error(`--${key} 必须为 kebab-case`);
  }
}

function assertDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new Error("--date 必须为 YYYY-MM-DD");
  }
}

function escapeCell(value) {
  return value.replaceAll("|", "\\|");
}

function writeNew(file, content) {
  if (existsSync(file)) throw new Error(`拒绝覆盖既有文件：${file}`);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, content, "utf8");
}

function upsertTableRow(file, headerStart, rowKey, row) {
  const content = readFileSync(file, "utf8");
  const lines = content.split("\n");
  const headerIndex = lines.findIndex((line) => line.trim().startsWith(headerStart));
  if (headerIndex < 0 || !lines[headerIndex + 1]?.includes("---")) {
    throw new Error(`缺少可更新的操作表格：${file}`);
  }
  const rowIndex = lines.findIndex(
    (line, index) => index > headerIndex + 1 && line.startsWith(`| ${rowKey} |`),
  );
  if (rowIndex >= 0) lines[rowIndex] = row;
  else lines.splice(headerIndex + 2, 0, row);
  writeFileSync(file, lines.join("\n"), "utf8");
}

function bulletLines(values) {
  return values.map((value) => `- ${value}`).join("\n");
}

function numberedLines(values) {
  return values.map((value, index) => `${index + 1}. ${value}`).join("\n");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  for (const key of required) assertSafeText(key, args[key]);
  assertSlug("site", args.site);
  assertSlug("operation", args.operation);
  assertDate(args.date);
  if (!["low", "medium", "high"].includes(args.risk)) {
    throw new Error("--risk 必须是 low、medium 或 high");
  }

  const sitesDir = resolve(args.root, "references/sites");
  const rootIndex = resolve(sitesDir, "index.md");
  const siteDir = resolve(sitesDir, args.site);
  const siteIndex = resolve(siteDir, "index.md");
  const operationFile = resolve(siteDir, "operations", `${args.operation}.md`);
  const aliases = args.alias ?? [];

  if (!existsSync(rootIndex)) {
    writeNew(
      rootIndex,
      `---\nformat: ego-site-index\nupdated: ${args.date}\n---\n\n# 站点索引\n\n| site | domains | aliases | last_verified | reference |\n| --- | --- | --- | --- | --- |\n`,
    );
  }
  if (!existsSync(siteIndex)) {
    writeNew(
      siteIndex,
      `---\nsite: ${args.site}\ndomains:\n- ${args.domain}\naliases:\n${aliases.length ? bulletLines(aliases) : "- 无"}\nupdated: ${args.date}\n---\n\n# ${args.site}\n\n## 平台特征\n\n仅在完成跨多个操作的实时验证后补充稳定的登录、导航或加载事实。\n\n## 操作目录\n\n| operation | intent | risk | last_verified | reference |\n| --- | --- | --- | --- | --- |\n`,
    );
  }

  writeNew(
    operationFile,
    `---\nsite: ${args.site}\noperation: ${args.operation}\ntitle: ${args.title}\nrisk: ${args.risk}\nlast_verified: ${args.date}\n---\n\n# ${args.title}\n\n## 目标\n\n${args.intent}\n\n## 前置条件与授权\n\n- 仅在当前登录、权限和用户授权范围内执行。\n- 对象不唯一、影响范围扩大或不可逆时停止并向用户确认。\n\n## 入口\n\n${args.entry}\n\n## 已验证步骤\n\n${numberedLines(args.step)}\n\n## 检查点\n\n${bulletLines(args.checkpoint)}\n\n## 成功标准\n\n${args.success}\n\n## 失败模式与恢复\n\n尚未记录经证实且可复现的失败模式；遇到结果不明时回到检查点，不更新验证日期。\n\n## 验证证据\n\n${bulletLines(args.evidence)}\n`,
  );

  upsertTableRow(
    siteIndex,
    "| operation |",
    args.operation,
    `| ${args.operation} | ${escapeCell(args.intent)} | ${args.risk} | ${args.date} | [说明](operations/${args.operation}.md) |`,
  );
  upsertTableRow(
    rootIndex,
    "| site |",
    args.site,
    `| ${args.site} | ${escapeCell(args.domain)} | ${escapeCell(aliases.join("、") || "无")} | ${args.date} | [说明](${args.site}/index.md) |`,
  );
  console.log(`已创建并索引 ${args.site}/${args.operation}；请运行 validate-knowledge.mjs。`);
}

try {
  main();
} catch (error) {
  console.error(`脚手架失败：${error.message}`);
  process.exitCode = 1;
}
