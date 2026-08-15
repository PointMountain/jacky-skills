import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { translations } from '../gallery/translations.js';

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const GALLERY_ROOT = path.join(SKILL_ROOT, 'gallery');
const EXPECTED_REVISION = 'aaf9a82f5efd73e87cc0998edc398e75bfc35901';
const EXPECTED_LICENSE_URL =
  `https://github.com/ConardLi/garden-skills/blob/${EXPECTED_REVISION}/LICENSE`;

function contentType(filePath) {
  return {
    '.css': 'text/css; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.md': 'text/markdown; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
  }[path.extname(filePath)] ?? 'application/octet-stream';
}

async function startStaticServer(root) {
  const server = createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url ?? '/', 'http://127.0.0.1');
      const relativePath = decodeURIComponent(requestUrl.pathname).replace(/^\/+/, '') || 'index.html';
      const filePath = path.resolve(root, relativePath);
      if (filePath !== root && !filePath.startsWith(`${root}${path.sep}`)) {
        response.writeHead(403).end('Forbidden');
        return;
      }
      if (!(await stat(filePath)).isFile()) throw new Error('Not a file');
      const body = await readFile(filePath);
      response.writeHead(200, { 'content-type': contentType(filePath) }).end(body);
    } catch {
      response.writeHead(404).end('Not found');
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert.ok(address && typeof address === 'object');
  return {
    baseUrl: `http://127.0.0.1:${address.port}/`,
    close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
  };
}

async function expectOk(url) {
  const response = await fetch(url);
  assert.equal(response.status, 200, `${url} should return HTTP 200`);
  return response;
}

test('静态站点通过真实 HTTP 提供页面、Library 及其全部相对资源', async (t) => {
  const staticServer = await startStaticServer(GALLERY_ROOT);
  t.after(() => staticServer.close());

  const indexResponse = await expectOk(staticServer.baseUrl);
  assert.match(indexResponse.headers.get('content-type') ?? '', /^text\/html/);

  const libraryUrl = new URL('api/library.json', staticServer.baseUrl);
  const libraryResponse = await expectOk(libraryUrl);
  assert.match(libraryResponse.headers.get('content-type') ?? '', /^application\/json/);
  const library = await libraryResponse.json();
  assert.ok(Array.isArray(library.effects));
  assert.ok(library.effects.length > 0);

  for (const effect of library.effects) {
    for (const field of ['previewUrl', 'sourceUrl']) {
      assert.match(effect[field], /^\.\//, `${field} must remain gallery-relative`);
      const assetUrl = new URL(effect[field], staticServer.baseUrl);
      assert.equal(assetUrl.origin, new URL(staticServer.baseUrl).origin);
      await expectOk(assetUrl);
    }
  }
});

test('Library 固定公开来源、源码许可和预览署名契约', async (t) => {
  const staticServer = await startStaticServer(GALLERY_ROOT);
  t.after(() => staticServer.close());

  const library = await (await expectOk(new URL('api/library.json', staticServer.baseUrl))).json();
  for (const effect of library.effects) {
    assert.deepEqual(effect.provenance, {
      repository: 'ConardLi/garden-skills',
      revision: EXPECTED_REVISION,
      license: {
        spdx: 'MIT',
        url: EXPECTED_LICENSE_URL,
      },
      preview: {
        origin:
          'Text-only image generation of a fictional young adult with glasses, not based on a real person.',
        author: 'wangjs-jacky',
        licenseSpdx: 'CC-BY-4.0',
      },
    });
  }
});

test('Library 的每个分类都有中英文展示标签', async () => {
  const library = JSON.parse(
    await readFile(path.join(GALLERY_ROOT, 'api/library.json'), 'utf8'),
  );
  const categories = new Set(library.effects.map((effect) => effect.category));

  for (const category of categories) {
    assert.equal(typeof translations.en.categories[category], 'string');
    assert.equal(typeof translations.zh.categories[category], 'string');
    assert.notEqual(translations.en.categories[category], translations.zh.categories[category]);
  }
});
