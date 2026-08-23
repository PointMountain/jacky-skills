#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const defaultRoot = resolve(scriptDir, "..");
const requiredSections = [
  "目标",
  "前置条件与授权",
  "入口",
  "已验证步骤",
  "检查点",
  "成功标准",
  "失败模式与恢复",
  "验证证据",
];
const placeholderPattern = /\b(?:todo|tbd|placeholder|required)\b/i;
const sensitivePattern = /(?:authorization|bearer|cookie|password|private[_ -]?key|\bjwt\b)/i;
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const datePattern = /^\d{4}-\d{2}-\d{2}$/;

function usage(exitCode = 0) {
  console.log("用法：node validate-knowledge.mjs [--root <skill-dir>]");
  process.exit(exitCode);
}

function rootFromArgs(argv) {
  if (argv.length === 0) return defaultRoot;
  if (argv.length === 2 && argv[0] === "--root") return resolve(argv[1]);
  if (argv.length === 1 && ["--help", "-h"].includes(argv[0])) usage();
  usage(1);
}

function contentOf(file, issues) {
  try {
    return readFileSync(file, "utf8");
  } catch (error) {
    issues.push(`${file}: 无法读取（${error.message}）`);
    return "";
  }
}

function frontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  if (!match) return null;
  const value = {};
  for (const line of match[1].split("\n")) {
    const pair = line.match(/^([a-z_]+):\s*(.*)$/);
    if (pair) value[pair[1]] = pair[2];
  }
  return value;
}

function markdownFiles(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...markdownFiles(file));
    else if (entry.isFile() && extname(entry.name) === ".md") files.push(file);
  }
  return files;
}

function checkSharedContent(file, content, issues) {
  if (placeholderPattern.test(content)) issues.push(`${file}: 包含未完成占位符`);
  if (sensitivePattern.test(content)) issues.push(`${file}: 包含疑似认证材料字段`);
}

function checkSiteIndex(file, site, sitesDir, rootIndex, issues) {
  const content = contentOf(file, issues);
  checkSharedContent(file, content, issues);
  const fields = frontmatter(content);
  if (!fields) {
    issues.push(`${file}: 缺少 frontmatter`);
    return [];
  }
  if (fields.site !== site) issues.push(`${file}: site 与目录不一致`);
  if (!fields.updated || !datePattern.test(fields.updated)) issues.push(`${file}: updated 日期无效`);
  if (!content.match(/^domains:\n\s*-\s+\S+/m)) issues.push(`${file}: domains 不能为空`);
  if (!content.match(/^aliases:\n\s*-\s+\S+/m)) issues.push(`${file}: aliases 不能为空`);
  if (!content.includes("## 平台特征") || !content.includes("## 操作目录")) {
    issues.push(`${file}: 缺少站点索引章节`);
  }
  if (!content.includes("| operation |")) issues.push(`${file}: 缺少 operation 表格`);
  const rootContent = contentOf(rootIndex, issues);
  if (!rootContent.includes(`](${site}/index.md)`)) issues.push(`${rootIndex}: 未索引站点 ${site}`);
  return markdownFiles(join(dirname(file), "operations"));
}

function checkOperation(file, site, issues) {
  const content = contentOf(file, issues);
  checkSharedContent(file, content, issues);
  const fields = frontmatter(content);
  const operation = file.slice(file.lastIndexOf("/") + 1, -3);
  if (!fields) {
    issues.push(`${file}: 缺少 frontmatter`);
    return;
  }
  if (fields.site !== site) issues.push(`${file}: site 与父目录不一致`);
  if (fields.operation !== operation) issues.push(`${file}: operation 与文件名不一致`);
  if (!fields.title) issues.push(`${file}: 缺少 title`);
  if (!["low", "medium", "high"].includes(fields.risk)) issues.push(`${file}: risk 无效`);
  if (!datePattern.test(fields.last_verified ?? "")) issues.push(`${file}: last_verified 日期无效`);
  for (const section of requiredSections) {
    if (!content.includes(`## ${section}`)) issues.push(`${file}: 缺少章节「${section}」`);
  }
  const siteIndex = join(dirname(dirname(file)), "index.md");
  const indexContent = contentOf(siteIndex, issues);
  if (!indexContent.includes(`](operations/${operation}.md)`)) {
    issues.push(`${siteIndex}: 未索引 operation ${operation}`);
  }
}

function main() {
  const root = rootFromArgs(process.argv.slice(2));
  const sitesDir = join(root, "references", "sites");
  const rootIndex = join(sitesDir, "index.md");
  const issues = [];
  if (!existsSync(rootIndex)) issues.push(`${rootIndex}: 缺少一级站点索引`);
  const rootContent = existsSync(rootIndex) ? contentOf(rootIndex, issues) : "";
  const rootFields = frontmatter(rootContent);
  if (rootContent) {
    checkSharedContent(rootIndex, rootContent, issues);
    if (!rootFields || rootFields.format !== "ego-site-index") issues.push(`${rootIndex}: format 无效`);
    if (!rootFields?.updated || !datePattern.test(rootFields.updated)) issues.push(`${rootIndex}: updated 日期无效`);
    if (!rootContent.includes("| site |")) issues.push(`${rootIndex}: 缺少站点表格`);
  }
  const siteDirectories = existsSync(sitesDir)
    ? readdirSync(sitesDir, { withFileTypes: true }).filter((entry) => entry.isDirectory())
    : [];
  for (const entry of siteDirectories) {
    if (!slugPattern.test(entry.name)) {
      issues.push(`${join(sitesDir, entry.name)}: 站点目录必须为 kebab-case`);
      continue;
    }
    const operationFiles = checkSiteIndex(join(sitesDir, entry.name, "index.md"), entry.name, sitesDir, rootIndex, issues);
    for (const operationFile of operationFiles) checkOperation(operationFile, entry.name, issues);
  }
  if (issues.length) {
    console.error(`知识库校验失败（${issues.length} 项）：`);
    for (const issue of issues) console.error(`- ${relative(root, issue).replace(/^$/, issue)}`);
    process.exitCode = 1;
  } else {
    console.log(`知识库校验通过：${siteDirectories.length} 个站点。`);
  }
}

main();
