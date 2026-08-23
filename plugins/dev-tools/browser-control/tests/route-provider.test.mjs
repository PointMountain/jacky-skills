import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, symlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const routerPath = fileURLToPath(
  new URL("../scripts/route-provider.mjs", import.meta.url),
);

function runRouter(state) {
  const result = spawnSync(process.execPath, [routerPath], {
    encoding: "utf8",
    input: JSON.stringify(state),
  });

  return {
    ...result,
    json: result.status === 0 ? JSON.parse(result.stdout) : null,
  };
}

function runRouterInput(input) {
  return spawnSync(process.execPath, [routerPath], {
    encoding: "utf8",
    input,
  });
}

test("通过安装符号链接启动时仍执行 CLI 主函数", async (t) => {
  const directory = await mkdtemp(
    path.join(os.tmpdir(), "browser-control-router-"),
  );
  t.after(() => rm(directory, { recursive: true, force: true }));

  const linkedRouter = path.join(directory, "route-provider.mjs");
  await symlink(routerPath, linkedRouter);

  const result = spawnSync(process.execPath, [linkedRouter], {
    encoding: "utf8",
    input: JSON.stringify({
      slot: "browser_with_existing_login",
      providers: {
        "codex-browser-control": {
          status: "missing",
          attempt: "not_attempted",
        },
        "ego-ops": { status: "available", attempt: "not_attempted" },
      },
    }),
  });

  assert.equal(result.status, 0, result.stderr);
  const json = JSON.parse(result.stdout);
  assert.equal(json.action, "use");
  assert.equal(json.provider, "ego-ops");
});

test("登录态任务固定按 Codex Browser Control 到 Ego Ops 排序", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(result.json, {
    schemaVersion: 1,
    slot: "browser_with_existing_login",
    priority: ["codex-browser-control", "ego-ops"],
    action: "probe",
    provider: "codex-browser-control",
    reason: "provider_not_checked",
  });
});

test("Codex Browser Control 与 Ego Ops 都可用时优先选择 Codex Browser Control", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "available",
        attempt: "not_attempted",
      },
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "use");
  assert.equal(result.json.provider, "codex-browser-control");
  assert.equal(result.json.reason, "provider_available");
});

test("Codex Browser Control 完成后路由器直接结束，不再进入 Ego Ops", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": { status: "available", attempt: "passed" },
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "complete");
  assert.equal(result.json.provider, "codex-browser-control");
  assert.equal(result.json.reason, "provider_passed");
});

test("Codex Browser Control 局部证据降级时仍由主能力完成", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "available",
        attempt: "degraded",
      },
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "complete");
  assert.equal(result.json.provider, "codex-browser-control");
  assert.equal(result.json.reason, "provider_degraded_but_usable");
  assert.deepEqual(result.json.priority, ["codex-browser-control", "ego-ops"]);
});

test("Codex Browser Control 缺失时自动使用 Ego Ops", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "missing",
        attempt: "not_attempted",
      },
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "use");
  assert.equal(result.json.provider, "ego-ops");
  assert.equal(result.json.reason, "provider_available");
  assert.deepEqual(result.json.priority, ["codex-browser-control", "ego-ops"]);
});

test("Codex Browser Control 调用失败时探测 Ego Ops", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": { status: "available", attempt: "failed" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "probe");
  assert.equal(result.json.provider, "ego-ops");
  assert.deepEqual(result.json.priority, ["codex-browser-control", "ego-ops"]);
});

test("Codex Browser Control 缺失且 Ego Ops 已验证可用时直接使用 Ego Ops", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "missing",
        attempt: "not_attempted",
      },
      "ego-ops": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "use");
  assert.equal(result.json.provider, "ego-ops");
});

test("Codex Browser Control 调用失败后探测 Ego Ops", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": { status: "available", attempt: "failed" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "probe");
  assert.equal(result.json.provider, "ego-ops");
});

test("所有登录态候选都不可用时明确阻断", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "missing",
        attempt: "not_attempted",
      },
      "ego-ops": { status: "degraded", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "blocked");
  assert.equal(result.json.provider, null);
  assert.equal(result.json.reason, "no_provider_available");
});

test("低优先级 provider 被提前调用时拒绝非法历史", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "not_checked",
        attempt: "not_attempted",
      },
      "ego-ops": { status: "available", attempt: "passed" },
    },
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /低优先级.*提前/);
});

test("WebAccess 作为登录态 provider 时被直接拒绝", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "web-access": { status: "available", attempt: "passed" },
    },
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /不属于能力槽位/);
});

test("旧的外部后备授权字段被拒绝", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    allowExternalFallback: true,
    providers: {},
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /allowExternalFallback.*已废弃/);
});

test("无登录态槽位保持 Chrome DevTools 优先", () => {
  const result = runRouter({
    slot: "browser_without_existing_login",
    providers: {
      "in-app-browser": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "probe");
  assert.equal(result.json.provider, "chrome-devtools");
  assert.deepEqual(result.json.priority, [
    "chrome-devtools",
    "in-app-browser",
  ]);
});

test("信息发现槽位只委派 web-search", () => {
  const result = runRouter({
    slot: "web_information_discovery",
    providers: {
      "web-search": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "use");
  assert.equal(result.json.provider, "web-search");
  assert.deepEqual(result.json.priority, ["web-search"]);
});

test("未知能力槽位会被拒绝", () => {
  const result = runRouter({
    slot: "unknown_slot",
    providers: {},
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /不支持的能力槽位/);
});

test("非法 provider 状态会被拒绝", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "sometimes",
        attempt: "not_attempted",
      },
    },
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /非法 status/);
});

test("不可用 provider 不能伪造调用结果", () => {
  const result = runRouter({
    slot: "browser_with_existing_login",
    providers: {
      "codex-browser-control": {
        status: "missing",
        attempt: "passed",
      },
    },
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /状态不一致/);
});

test("能力槽位之外的 provider 会被拒绝", () => {
  const result = runRouter({
    slot: "web_information_discovery",
    providers: {
      "web-search": { status: "available", attempt: "not_attempted" },
      "web-access": { status: "available", attempt: "not_attempted" },
    },
  });

  assert.equal(result.status, 2);
  assert.match(result.stderr, /不属于能力槽位/);
});

test("空输入和非法 JSON 会返回稳定错误码", () => {
  const empty = runRouterInput("");
  const malformed = runRouterInput("{");

  assert.equal(empty.status, 2);
  assert.match(empty.stderr, /必须通过 stdin/);
  assert.equal(malformed.status, 2);
  assert.match(malformed.stderr, /JSON/);
});
