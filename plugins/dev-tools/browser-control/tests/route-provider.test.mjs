import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const routerPath = fileURLToPath(new URL("../scripts/route-provider.mjs", import.meta.url));
function route(state) {
  const result = spawnSync(process.execPath, [routerPath], { encoding: "utf8", input: JSON.stringify(state) });
  return { ...result, json: result.status === 0 ? JSON.parse(result.stdout) : null };
}

test("only probes Ego Ops", () => {
  const result = route({ slot: "browser_automation", providers: {} });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(result.json, { schemaVersion: 1, slot: "browser_automation", priority: ["ego-ops"], action: "probe", provider: "ego-ops", reason: "provider_not_checked" });
});

test("Ego Ops is the only executable provider", () => {
  const result = route({ slot: "browser_automation", providers: { "ego-ops": { status: "available", attempt: "not_attempted" } } });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.json.action, "use");
  assert.equal(result.json.provider, "ego-ops");
});

test("unavailable or failed Ego Lite stops without fallback", () => {
  for (const state of [{ status: "missing", attempt: "not_attempted" }, { status: "available", attempt: "failed" }]) {
    const result = route({ slot: "browser_automation", providers: { "ego-ops": state } });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.json.action, "blocked");
    assert.equal(result.json.provider, null);
  }
});

test("rejects every non-Ego provider", () => {
  const result = route({ slot: "browser_automation", providers: { "another-browser": { status: "available", attempt: "not_attempted" } } });
  assert.equal(result.status, 2);
  assert.match(result.stderr, /统一 Ego Lite 路由/);
});
