#!/usr/bin/env node

import path from "node:path";
import process from "node:process";
import { realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";

const STATUS_VALUES = new Set(["not_checked", "available", "degraded", "missing"]);
const ATTEMPT_VALUES = new Set(["not_attempted", "passed", "degraded", "failed"]);
const SLOT = "browser_automation";
const PROVIDER = "ego-ops";

export function decideRoute(state) {
  if (!state || typeof state !== "object" || Array.isArray(state)) throw new Error("路由状态必须是 JSON 对象");
  if (state.slot !== SLOT) throw new Error(`只支持能力槽位：${SLOT}`);
  const providers = state.providers ?? {};
  if (!providers || typeof providers !== "object" || Array.isArray(providers)) throw new Error("providers 必须是 JSON 对象");
  for (const provider of Object.keys(providers)) {
    if (provider !== PROVIDER) throw new Error(`provider ${provider} 不属于统一 Ego Lite 路由`);
  }
  const providerState = providers[PROVIDER] ?? {};
  const status = providerState.status ?? "not_checked";
  const attempt = providerState.attempt ?? "not_attempted";
  if (!STATUS_VALUES.has(status)) throw new Error(`provider ${PROVIDER} 使用了非法 status：${status}`);
  if (!ATTEMPT_VALUES.has(attempt)) throw new Error(`provider ${PROVIDER} 使用了非法 attempt：${attempt}`);
  if (status !== "available" && attempt !== "not_attempted") throw new Error(`provider ${PROVIDER} 状态不一致：${status} 不能带有调用结果 ${attempt}`);
  const base = { schemaVersion: 1, slot: SLOT, priority: [PROVIDER] };
  if (status === "not_checked") return { ...base, action: "probe", provider: PROVIDER, reason: "provider_not_checked" };
  if (status !== "available") return { ...base, action: "blocked", provider: null, reason: "ego_lite_unavailable" };
  if (attempt === "not_attempted") return { ...base, action: "use", provider: PROVIDER, reason: "provider_available" };
  if (attempt === "passed" || attempt === "degraded") return { ...base, action: "complete", provider: PROVIDER, reason: attempt === "passed" ? "provider_passed" : "provider_degraded" };
  return { ...base, action: "blocked", provider: null, reason: "ego_lite_task_failed" };
}

async function main() {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  if (!input.trim()) throw new Error("必须通过 stdin 提供路由状态 JSON");
  process.stdout.write(`${JSON.stringify(decideRoute(JSON.parse(input)), null, 2)}\n`);
}

function resolveEntryPath(target) {
  const absolutePath = path.resolve(target);
  try { return realpathSync(absolutePath); } catch { return absolutePath; }
}

const isMain = process.argv[1] && resolveEntryPath(process.argv[1]) === resolveEntryPath(fileURLToPath(import.meta.url));
if (isMain) {
  try { await main(); } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 2;
  }
}
