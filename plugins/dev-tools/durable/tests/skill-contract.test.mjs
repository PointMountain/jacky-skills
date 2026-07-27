import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const skillRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(skillRoot, "..", "..", "..");
const skill = readFileSync(join(skillRoot, "SKILL.md"), "utf8");
const shaping = readFileSync(join(skillRoot, "references", "shaping.md"), "utf8");
const manifest = JSON.parse(
  readFileSync(join(repoRoot, "plugins", "dev-tools", ".claude-plugin", "plugin.json"), "utf8"),
);
const marketplace = JSON.parse(
  readFileSync(join(repoRoot, ".claude-plugin", "marketplace.json"), "utf8"),
);

test("Durable 必须由用户明确启动", () => {
  assert.match(skill, /只有用户明确.*开始.*才进入/);
  assert.match(skill, /已在本次请求中明确启动时，不重复索要同一授权/);
  assert.match(skill, /POC.*单独取得同意/);
  assert.match(skill, /不为 Durable 新建心跳、恢复协议、进度状态机/);
});

test("交付契约同时覆盖产物与真实使用链路", () => {
  assert.match(skill, /产物、完整使用链路和验证证据同时成立/);
  assert.match(skill, /从冷启动和真实入口开始/);
  assert.match(skill, /真实可达、会影响用户结果的状态/);
  assert.match(skill, /不得为满足清单而制造产品并不存在的状态/);
  assert.match(skill, /PC、移动端、桌面应用/);
  assert.match(shaping, /结果交付/);
  assert.match(shaping, /过程交付/);
});

test("塑形保持动态，并支持 Todo 交接", () => {
  assert.match(shaping, /不提供必须逐项照抄的固定问卷/);
  assert.match(shaping, /状态保存为 `shaping`/);
  assert.match(shaping, /状态保存为 `canDurable`/);
  assert.match(shaping, /现在开始 Durable/);
  assert.match(shaping, /不重复索要同一授权/);
});

test("自进化必须经过证据与回归门禁", () => {
  assert.match(skill, /审计可以得出“无需修改”/);
  assert.match(skill, /Skill 规则调整需要可复现根因/);
  assert.match(skill, /环境事实与 POC 需要可复核证据、环境边界、验证时间和失效条件/);
  assert.match(skill, /长期偏好需要用户明确表达、适用边界和与既有偏好的查重/);
  assert.match(skill, /查重、查冲突/);
  assert.match(skill, /失败则恢复修改前版本/);
});

test("Plugin 清单与 Marketplace 版本一致", () => {
  assert.ok(manifest.skills.includes("./durable/"));
  const entry = marketplace.plugins.find((plugin) => plugin.name === "dev-tools");
  assert.equal(entry.version, manifest.version);
});
