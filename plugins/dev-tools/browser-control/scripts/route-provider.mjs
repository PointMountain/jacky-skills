#!/usr/bin/env node

import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const SCHEMA_VERSION = 1;
const STATUS_VALUES = new Set([
  "not_checked",
  "available",
  "degraded",
  "missing",
]);
const ATTEMPT_VALUES = new Set([
  "not_attempted",
  "passed",
  "degraded",
  "failed",
]);

export const SLOT_PRIORITIES = Object.freeze({
  browser_with_existing_login: Object.freeze([
    "codex-browser-control",
    "web-access",
  ]),
  browser_without_existing_login: Object.freeze([
    "chrome-devtools",
    "in-app-browser",
  ]),
  web_information_discovery: Object.freeze(["web-search"]),
});

function normalizeState(state) {
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    throw new Error("路由状态必须是 JSON 对象");
  }

  const catalogPriority = SLOT_PRIORITIES[state.slot];
  if (!catalogPriority) {
    throw new Error(`不支持的能力槽位：${String(state.slot)}`);
  }

  if (
    state.allowExternalFallback !== undefined &&
    typeof state.allowExternalFallback !== "boolean"
  ) {
    throw new Error("allowExternalFallback 必须是布尔值");
  }

  const allowExternalFallback = state.allowExternalFallback ?? false;
  const priority =
    state.slot === "browser_with_existing_login" &&
    !allowExternalFallback
      ? catalogPriority.slice(0, 1)
      : catalogPriority;

  const rawProviders = state.providers ?? {};
  if (
    typeof rawProviders !== "object" ||
    rawProviders === null ||
    Array.isArray(rawProviders)
  ) {
    throw new Error("providers 必须是 JSON 对象");
  }

  for (const provider of Object.keys(rawProviders)) {
    if (!catalogPriority.includes(provider)) {
      throw new Error(
        `provider ${provider} 不属于能力槽位 ${state.slot}`,
      );
    }
  }

  const providers = Object.fromEntries(
    catalogPriority.map((provider) => {
      const rawProvider = rawProviders[provider] ?? {};
      if (
        typeof rawProvider !== "object" ||
        rawProvider === null ||
        Array.isArray(rawProvider)
      ) {
        throw new Error(`provider ${provider} 的状态必须是 JSON 对象`);
      }

      const status = rawProvider.status ?? "not_checked";
      const attempt = rawProvider.attempt ?? "not_attempted";

      if (!STATUS_VALUES.has(status)) {
        throw new Error(`provider ${provider} 使用了非法 status：${status}`);
      }
      if (!ATTEMPT_VALUES.has(attempt)) {
        throw new Error(`provider ${provider} 使用了非法 attempt：${attempt}`);
      }
      if (status !== "available" && attempt !== "not_attempted") {
        throw new Error(
          `provider ${provider} 状态不一致：${status} 不能带有调用结果 ${attempt}`,
        );
      }

      return [provider, { status, attempt }];
    }),
  );

  if (
    state.slot === "browser_with_existing_login" &&
    !allowExternalFallback &&
    providers["web-access"].attempt !== "not_attempted"
  ) {
    throw new Error(
      "外部后备 WebAccess 未获授权，不得记录为已调用",
    );
  }

  return {
    slot: state.slot,
    priority,
    providers,
    allowExternalFallback,
  };
}

function allowsFallback(providerState) {
  if (
    providerState.status === "missing" ||
    providerState.status === "degraded"
  ) {
    return true;
  }

  return (
    providerState.status === "available" &&
    (providerState.attempt === "failed" ||
      providerState.attempt === "degraded")
  );
}

function assertLegalHistory(priority, providers) {
  for (let index = 1; index < priority.length; index += 1) {
    const provider = priority[index];
    if (providers[provider].attempt === "not_attempted") continue;

    for (let higherIndex = 0; higherIndex < index; higherIndex += 1) {
      const higherProvider = priority[higherIndex];
      if (!allowsFallback(providers[higherProvider])) {
        throw new Error(
          `低优先级 provider ${provider} 被提前调用：高优先级 provider ${higherProvider} 尚未明确失败或不可用`,
        );
      }
    }
  }
}

function decision(slot, priority, action, provider, reason) {
  return {
    schemaVersion: SCHEMA_VERSION,
    slot,
    priority: [...priority],
    action,
    provider,
    reason,
  };
}

export function decideRoute(rawState) {
  const { slot, priority, providers } = normalizeState(rawState);
  assertLegalHistory(priority, providers);

  for (const provider of priority) {
    const providerState = providers[provider];

    if (providerState.status === "not_checked") {
      return decision(
        slot,
        priority,
        "probe",
        provider,
        "provider_not_checked",
      );
    }

    if (
      slot === "browser_with_existing_login" &&
      provider === "codex-browser-control" &&
      providerState.status === "available" &&
      providerState.attempt === "degraded"
    ) {
      return decision(
        slot,
        priority,
        "complete",
        provider,
        "provider_degraded_but_usable",
      );
    }

    if (allowsFallback(providerState)) continue;

    if (providerState.attempt === "not_attempted") {
      return decision(
        slot,
        priority,
        "use",
        provider,
        "provider_available",
      );
    }

    if (providerState.attempt === "passed") {
      return decision(
        slot,
        priority,
        "complete",
        provider,
        "provider_passed",
      );
    }
  }

  return decision(
    slot,
    priority,
    "blocked",
    null,
    "no_provider_available",
  );
}

async function readStandardInput() {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  if (input.trim() === "") {
    throw new Error("必须通过 stdin 提供路由状态 JSON");
  }

  try {
    return JSON.parse(input);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`无法解析路由状态 JSON：${detail}`);
  }
}

async function main() {
  try {
    const state = await readStandardInput();
    process.stdout.write(`${JSON.stringify(decideRoute(state), null, 2)}\n`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`${message}\n`);
    process.exitCode = 2;
  }
}

const isMain =
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMain) {
  await main();
}
