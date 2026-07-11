import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const skillRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const pluginRoot = path.dirname(skillRoot);
const repositoryRoot = path.resolve(pluginRoot, "../..");

async function read(relativePath) {
  return readFile(path.join(repositoryRoot, relativePath), "utf8");
}

test("browser-control 声明唯一入口与三类能力槽位", async () => {
  const [skill, capabilities] = await Promise.all([
    read("plugins/dev-tools/browser-control/SKILL.md"),
    read("plugins/dev-tools/browser-control/references/capabilities.md"),
  ]);

  assert.match(skill, /本地 AI 浏览器操控的唯一通用入口/);
  assert.match(skill, /已有登录态/);
  assert.match(skill, /不需要已有登录态/);
  assert.match(skill, /web-search/);
  assert.match(skill, /不能仅因.*(?:SPA|JS).*(?:WebAccess|web-access)/s);
  assert.match(skill, /Skill 目录.*绝对路径|绝对路径.*Skill 目录/s);
  assert.doesNotMatch(skill, /node scripts\/usage-ledger\.mjs/);

  for (const slot of [
    "browser_without_existing_login",
    "browser_with_existing_login",
    "web_information_discovery",
  ]) {
    assert.match(capabilities, new RegExp(`^## ${slot}$`, "m"));
  }
});

test("无登录态槽位使用 Chrome DevTools，且不得回退到 WebAccess", async () => {
  const capabilities = await read(
    "plugins/dev-tools/browser-control/references/capabilities.md",
  );
  const section = capabilities.match(
    /^## browser_without_existing_login$([\s\S]*?)(?=^## |\Z)/m,
  )?.[1];

  assert.ok(section);
  assert.match(section, /Chrome DevTools/);
  assert.match(section, /browser:control-in-app-browser/);
  assert.match(section, /不得.*(?:WebAccess|web-access)/);
});

test("登录态槽位使用 WebAccess，并允许 web-connect 作为当前页讲解适配器", async () => {
  const capabilities = await read(
    "plugins/dev-tools/browser-control/references/capabilities.md",
  );
  const section = capabilities.match(
    /^## browser_with_existing_login$([\s\S]*?)(?=^## |\Z)/m,
  )?.[1];

  assert.ok(section);
  assert.match(section, /WebAccess|web-access/);
  assert.match(section, /web-connect/);
  assert.match(section, /当前.*tab|当前页/);
});

test("web-connect 收窄为 browser-control 的登录态执行适配层并使用新版 POST API", async () => {
  const [skill, providers] = await Promise.all([
    read("plugins/dev-tools/web-connect/SKILL.md"),
    read("plugins/dev-tools/web-connect/references/providers.md"),
  ]);

  assert.match(skill, /browser-control/);
  assert.match(skill, /登录态/);
  assert.match(skill, /当前.*tab|当前页/);
  assert.doesNotMatch(skill, /\/new\?url=/);
  assert.match(skill, /curl[^\n]*-X POST[^\n]*--data-raw/);

  assert.match(providers, /`\/new`\s*\|\s*POST/);
  assert.match(providers, /`\/navigate`\s*\|\s*POST/);
  assert.doesNotMatch(providers, /`\/new`\s*\|\s*GET/);
  assert.doesNotMatch(providers, /`\/navigate`\s*\|\s*GET/);
});

test("web-search 的浏览器层只委派 browser-control", async () => {
  const skill = await read("plugins/dev-tools/web-search/SKILL.md");
  const layer4 = skill.match(/^## 5\. Layer 4：([\s\S]*?)(?=^## 6\.)/m)?.[1];

  assert.ok(layer4);
  assert.match(layer4, /browser-control/);
  assert.doesNotMatch(layer4, /两种 CDP 入口的 Trade-off/);
  assert.doesNotMatch(layer4, /默认建议.*opencli browser/);
});

test("插件清单、README 与 CI 暴露 browser-control", async () => {
  const [manifestText, marketplaceText, readme, workflow] = await Promise.all([
    read("plugins/dev-tools/.claude-plugin/plugin.json"),
    read(".claude-plugin/marketplace.json"),
    read("README.md"),
    read(".github/workflows/validate.yml"),
  ]);
  const manifest = JSON.parse(manifestText);
  const marketplace = JSON.parse(marketplaceText);
  const marketplacePlugin = marketplace.plugins.find(({ name }) => name === "dev-tools");

  assert.equal(manifest.version, "2.7.0");
  assert.ok(manifest.skills.includes("./browser-control/"));
  assert.match(manifest.description, /浏览器/);
  assert.equal(marketplacePlugin?.version, "2.7.0");
  assert.match(marketplacePlugin?.description ?? "", /浏览器/);
  assert.match(readme, /browser-control/);
  assert.match(workflow, /browser-control/);
  for (const runner of ["ubuntu-latest", "macos-latest", "windows-latest"]) {
    assert.match(workflow, new RegExp(runner));
  }
  assert.match(workflow, /node-version:\s*["']?18["']?/);
  assert.match(
    workflow,
    /node --test plugins\/dev-tools\/browser-control\/tests\/\*\.test\.mjs/,
  );
});
