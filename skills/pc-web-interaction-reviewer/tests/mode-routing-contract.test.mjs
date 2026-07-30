import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const skillRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

async function read(relativePath) {
  return readFile(path.join(skillRoot, relativePath), "utf8");
}

test("SKILL 只承担三种主模式的语义路由与全局门禁", async () => {
  const skill = await read("SKILL.md");

  assert.match(skill, /截图评审[\s\S]*screenshot-review\.md/);
  assert.match(skill, /全站交互 E2E 走查[\s\S]*full-site-e2e-walkthrough\.md/);
  assert.match(skill, /回归验收[\s\S]*regression-acceptance\.md/);
  assert.match(skill, /每个评审阶段只声明一个主模式/);
  assert.match(skill, /截图基线 → E2E 走查 → 修复后回归/);
  assert.match(skill, /录屏指定帧/);
  assert.match(skill, /happy-pc-feedback-baseline\.md/);
  assert.match(skill, /browser-control/);
  assert.match(skill, /web-e2e/);
  assert.match(skill, /安全门/);
  assert.match(skill, /auto memory/);
  assert.ok(skill.split("\n").length <= 100, "SKILL.md 应保持精简");
});

test("截图评审保持静态证据边界，不冒充交互 E2E", async () => {
  const mode = await read("references/screenshot-review.md");

  assert.match(mode, /静态视觉审查/);
  assert.match(mode, /不执行页面交互/);
  assert.match(mode, /不能证明按钮可用、键盘行为、焦点顺序、动画、请求结果/);
  assert.match(mode, /验证问题/);
  assert.match(mode, /验证动作/);
  assert.match(mode, /判定标准/);
  assert.match(mode, /不执行点击遍历、Console\/Network 检查或回归判定/);
});

test("全站 E2E 遍历动态入口并比较动作前后四类证据", async () => {
  const mode = await read("references/full-site-e2e-walkthrough.md");

  assert.match(mode, /所有可点击或可键盘激活的入口/);
  assert.match(mode, /DOM 明显变化[\s\S]*重新获取入口/);
  assert.match(mode, /动作前/);
  assert.match(mode, /动作后/);
  assert.match(mode, /再次截图/);
  assert.match(mode, /Console 与 Network/);
  assert.match(mode, /失败 XHR\/Fetch/);
  assert.match(mode, /实际变化是否符合预期/);
  assert.match(mode, /未点完的入口必须明确列出/);
});

test("回归验收冻结既定 Case，禁止无边界探索", async () => {
  const mode = await read("references/regression-acceptance.md");

  assert.match(mode, /既定问题、验收点或 E2E Case/);
  assert.match(mode, /冻结回归范围/);
  assert.match(mode, /不展开全站入口发现/);
  assert.match(mode, /严格按固定步骤/);
  assert.match(mode, /已修复/);
  assert.match(mode, /仍失败/);
  assert.match(mode, /证据不足/);
  assert.match(mode, /阻断/);
  assert.match(mode, /不得用回归验收名义扩展为全站探索/);
});
