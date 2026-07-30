import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const LOGIN_STATE_SOURCES = new Set([
  "user_confirmation",
  "explicit_request",
  "local_record",
  "intrinsic_context",
]);

function registryPathFor(skillRoot) {
  return path.resolve(skillRoot, "login-state.local.json");
}

function parseTargetUrl(targetUrl) {
  if (typeof targetUrl !== "string" || targetUrl.trim() === "") {
    throw new Error("目标 URL 不能为空");
  }
  const parsed = new URL(targetUrl);
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("登录态注册表只接受 HTTP(S) URL");
  }
  return parsed.href;
}

export function fingerprintTargetUrl(targetUrl) {
  return createHash("sha256").update(parseTargetUrl(targetUrl)).digest("hex");
}

async function readRegistry(skillRoot) {
  try {
    const parsed = JSON.parse(
      await readFile(registryPathFor(skillRoot), "utf8"),
    );
    if (
      parsed?.version !== 1 ||
      parsed.records === null ||
      typeof parsed.records !== "object" ||
      Array.isArray(parsed.records)
    ) {
      throw new Error("本地登录态注册表格式无效");
    }
    return parsed;
  } catch (error) {
    if (error?.code === "ENOENT") {
      return { version: 1, records: {} };
    }
    throw error;
  }
}

export async function lookupLoginState({ skillRoot, targetUrl }) {
  const fingerprint = fingerprintTargetUrl(targetUrl);
  const registry = await readRegistry(skillRoot);
  const record = registry.records[fingerprint];
  if (record === undefined) {
    return { found: false, fingerprint };
  }
  if (
    typeof record.needsExistingLogin !== "boolean" ||
    !LOGIN_STATE_SOURCES.has(record.source)
  ) {
    throw new Error("本地登录态记录格式无效");
  }
  return {
    found: true,
    fingerprint,
    needsExistingLogin: record.needsExistingLogin,
    source: record.source,
  };
}

export async function recordLoginState({
  skillRoot,
  targetUrl,
  needsExistingLogin,
  source,
  now = new Date().toISOString(),
}) {
  if (typeof needsExistingLogin !== "boolean") {
    throw new Error("needsExistingLogin 必须是布尔值");
  }
  if (!LOGIN_STATE_SOURCES.has(source) || source === "local_record") {
    throw new Error("登录态判断来源无效");
  }
  if (!Number.isFinite(Date.parse(now))) {
    throw new Error("记录时间无效");
  }

  const fingerprint = fingerprintTargetUrl(targetUrl);
  const registry = await readRegistry(skillRoot);
  registry.records[fingerprint] = {
    needsExistingLogin,
    source,
    updatedAt: now,
  };
  await writeFile(
    registryPathFor(skillRoot),
    `${JSON.stringify(registry, null, 2)}\n`,
    { encoding: "utf8", mode: 0o600 },
  );
  return {
    fingerprint,
    needsExistingLogin,
    source,
  };
}

async function readStdinJson() {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  return JSON.parse(input);
}

async function main() {
  const command = process.argv[2];
  const payload = await readStdinJson();
  const skillRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
  );
  if (command === "lookup") {
    process.stdout.write(
      `${JSON.stringify(
        await lookupLoginState({
          skillRoot,
          targetUrl: payload.url,
        }),
      )}\n`,
    );
    return;
  }
  if (command === "record") {
    process.stdout.write(
      `${JSON.stringify(
        await recordLoginState({
          skillRoot,
          targetUrl: payload.url,
          needsExistingLogin: payload.needsExistingLogin,
          source: payload.source,
        }),
      )}\n`,
    );
    return;
  }
  throw new Error("用法：login-state-registry.mjs <lookup|record>");
}

if (
  process.argv[1] &&
  fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
