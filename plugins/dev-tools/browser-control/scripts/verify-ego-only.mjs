#!/usr/bin/env node

import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function executableOnPath(name, pathEnv = process.env.PATH ?? "") {
  const extensions = process.platform === "win32" ? ["", ".cmd", ".exe", ".bat"] : [""];
  for (const directory of pathEnv.split(path.delimiter).filter(Boolean)) {
    for (const extension of extensions) {
      const candidate = path.join(directory, `${name}${extension}`);
      if (existsSync(candidate)) return candidate;
    }
  }
  return null;
}

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    encoding: "utf8",
    input: options.input,
    timeout: 5_000,
  });
}

function check(checks, name, passed, detail) {
  checks.push({ name, passed, detail });
}

export function verifyEgoOnly({ home = os.homedir(), pathEnv = process.env.PATH ?? "" } = {}) {
  const checks = [];
  const routerPath = path.join(SKILL_ROOT, "scripts", "route-provider.mjs");
  const route = run(process.execPath, [routerPath], {
    input: JSON.stringify({
      slot: "browser_automation",
      providers: { "ego-ops": { status: "available", attempt: "not_attempted" } },
    }),
  });
  let routeIsEgoOnly = false;
  try {
    const value = JSON.parse(route.stdout);
    routeIsEgoOnly = route.status === 0
      && value.action === "use"
      && value.provider === "ego-ops"
      && Array.isArray(value.priority)
      && value.priority.length === 1
      && value.priority[0] === "ego-ops";
  } catch {}
  check(checks, "router", routeIsEgoOnly, "Browser Control 只返回 ego-ops");

  const skill = path.join(SKILL_ROOT, "SKILL.md");
  const expectedSkill = existsSync(skill)
    && !existsSync(path.join(SKILL_ROOT, "../web-connect"));
  check(checks, "skill-layout", expectedSkill, "Browser Control 存在，旧 web-connect 不存在");

  const retiredSkillPaths = [
    path.join(home, ".agents", "skills", "agent-browser"),
    path.join(home, ".codex", "skills", "agent-browser"),
    path.join(home, ".agents", "skills", "web-access"),
    path.join(home, ".codex", "skills", "web-access"),
    path.join(home, ".agents", "skills", "opencli-ops"),
    path.join(home, ".codex", "skills", "opencli-ops"),
  ];
  const activeRetiredSkills = retiredSkillPaths.filter(existsSync);
  check(checks, "retired-skills", activeRetiredSkills.length === 0, "已退休 Skill 目录均不存在");

  check(checks, "agent-browser-command", executableOnPath("agent-browser", pathEnv) === null, "agent-browser 不在 PATH 中");
  check(checks, "ego-browser-command", executableOnPath("ego-browser", pathEnv) !== null, "ego-browser 可从 PATH 调用");

  const opencli = executableOnPath("opencli", pathEnv);
  if (!opencli) {
    check(checks, "opencli-guard", true, "opencli 不在 PATH 中，无网页入口可用");
  } else {
    const blocked = ["web", "browser"].every((command) => {
      const result = run(opencli, [command, "--help"]);
      return result.status !== 0 && /disabled locally/i.test(`${result.stdout}${result.stderr}`);
    });
    check(checks, "opencli-guard", blocked, "opencli web 与 browser 均被本机保护拒绝");
  }

  return { ok: checks.every((item) => item.passed), checks };
}

function render(result, json) {
  if (json) return JSON.stringify(result, null, 2);
  return result.checks
    .map((item) => `${item.passed ? "PASS" : "FAIL"} ${item.name}: ${item.detail}`)
    .join("\n");
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const result = verifyEgoOnly();
  process.stdout.write(`${render(result, process.argv.includes("--json"))}\n`);
  process.exitCode = result.ok ? 0 : 1;
}
