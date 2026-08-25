import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  fingerprintTargetUrl,
  lookupLoginState,
  recordLoginState,
} from "../scripts/login-state-registry.mjs";

async function temporarySkillRoot(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "browser-login-state-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  return root;
}

test("登录态注册表只保存 URL 指纹，不保存原始链接", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const targetUrl = "https://example.test/session/private-value";

  const recorded = await recordLoginState({
    skillRoot,
    targetUrl,
    needsExistingLogin: true,
    source: "user_confirmation",
    now: "2026-07-31T09:00:00.000Z",
  });
  const registry = await readFile(
    path.join(skillRoot, "login-state.local.json"),
    "utf8",
  );

  assert.equal(recorded.fingerprint, fingerprintTargetUrl(targetUrl));
  assert.doesNotMatch(registry, /example\.test|private-value/);
  assert.match(registry, new RegExp(recorded.fingerprint));
});

test("相同链接可以读取本地登录态判断", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const targetUrl = "https://example.test/session/abc";

  await recordLoginState({
    skillRoot,
    targetUrl,
    needsExistingLogin: true,
    source: "user_confirmation",
  });

  assert.deepEqual(await lookupLoginState({ skillRoot, targetUrl }), {
    found: true,
    fingerprint: fingerprintTargetUrl(targetUrl),
    needsExistingLogin: true,
    source: "user_confirmation",
  });
  assert.deepEqual(
    await lookupLoginState({
      skillRoot,
      targetUrl: "https://example.test/session/other",
    }),
    {
      found: false,
      fingerprint: fingerprintTargetUrl(
        "https://example.test/session/other",
      ),
    },
  );
});

test("用户当前确认可以覆盖同一链接的旧记录", async (t) => {
  const skillRoot = await temporarySkillRoot(t);
  const targetUrl = "https://example.test/session/abc";

  await recordLoginState({
    skillRoot,
    targetUrl,
    needsExistingLogin: false,
    source: "user_confirmation",
    now: "2026-07-31T09:00:00.000Z",
  });
  await recordLoginState({
    skillRoot,
    targetUrl,
    needsExistingLogin: true,
    source: "user_confirmation",
    now: "2026-07-31T09:01:00.000Z",
  });

  const result = await lookupLoginState({ skillRoot, targetUrl });
  assert.equal(result.needsExistingLogin, true);
  assert.equal(result.source, "user_confirmation");
});

test("拒绝非法 URL、判断值和判断来源", async (t) => {
  const skillRoot = await temporarySkillRoot(t);

  assert.throws(() => fingerprintTargetUrl("not-a-url"));
  await assert.rejects(() =>
    recordLoginState({
      skillRoot,
      targetUrl: "https://example.test/",
      needsExistingLogin: "yes",
      source: "user_confirmation",
    }),
  );
  await assert.rejects(() =>
    recordLoginState({
      skillRoot,
      targetUrl: "https://example.test/",
      needsExistingLogin: true,
      source: "guess",
    }),
  );
});
