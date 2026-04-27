#!/usr/bin/env node
/**
 * 掘金小册提取脚本 v2
 *
 * 优化点：
 * - HTML→Markdown 自动转换（turndown）
 * - 图片高并发下载（20 并发 + keepAlive + 5s 超时）
 * - 自动检测内容格式（HTML/Markdown）
 *
 * 用法：node extract-juejin-booklet.mjs <booklet_url_or_id> [--output-dir <path>] [--download-images]
 */

import fs from 'node:fs';
import path from 'node:path';
import https from 'node:https';
import http from 'node:http';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const TurndownService = require('turndown');

// ========== 配置 ==========
const API_BASE = 'https://api.juejin.cn';
const REQUEST_DELAY = 300;
const IMAGE_CONCURRENCY = 20;
const IMAGE_TIMEOUT = 5000;

// 连接复用 agent（减少 TCP 握手开销）
const httpsAgent = new https.Agent({ keepAlive: true, maxSockets: 30 });
const httpAgent = new http.Agent({ keepAlive: true, maxSockets: 30 });

// ========== Turndown 配置 ==========
const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
  emDelimiter: '*',
  strongDelimiter: '**',
  hr: '---',
});

turndown.addRule('preformatted', {
  filter: ['pre'],
  replacement(content, node) {
    const code = node.querySelector('code');
    const lang = code ? (code.className?.replace('hljs language-', '').replace('language-', '') || '') : '';
    const text = (code || node).textContent || '';
    return `\n\n\`\`\`${lang}\n${text}\n\`\`\`\n\n`;
  },
});

turndown.addRule('headings', {
  filter: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
  replacement(content, node) {
    const level = parseInt(node.tagName[1]);
    const clean = content.replace(/^#+\s*/, '').trim();
    return `\n\n${'#'.repeat(level)} ${clean}\n\n`;
  },
});

// ========== 工具函数 ==========

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function safeFilename(name, maxLen = 60) {
  return name
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
    .replace(/\s+/g, '-')
    .substring(0, maxLen)
    .replace(/-+$/, '');
}

// ========== 网络请求 ==========

function fetchJSON(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const urlObj = new URL(url);
    const req = https.request({
      hostname: urlObj.hostname, port: 443, path: urlObj.pathname,
      method: 'POST', agent: httpsAgent,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
        'Origin': 'https://juejin.cn',
        'Referer': 'https://juejin.cn/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
    }, (res) => {
      let chunks = '';
      res.on('data', c => chunks += c);
      res.on('end', () => {
        try { resolve(JSON.parse(chunks)); }
        catch (e) { reject(new Error(`JSON 解析失败: ${e.message}`)); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/**
 * 下载单个文件（返回 buffer，失败快速返回 null）
 */
function downloadToBuffer(url) {
  return new Promise((resolve) => {
    const proto = url.startsWith('https') ? https : http;
    const agent = url.startsWith('https') ? httpsAgent : httpAgent;
    const req = proto.get(url, {
      agent, timeout: IMAGE_TIMEOUT,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://juejin.cn/',
      },
    }, (res) => {
      // 重定向
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        downloadToBuffer(res.headers.location).then(resolve);
        return;
      }
      if (res.statusCode !== 200) { resolve(null); return; }

      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const buf = Buffer.concat(chunks);
        resolve(buf.length > 100 ? buf : null); // 太小 = 占位图
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

/**
 * 高并发批量下载图片
 * 返回 Map<url, { filename, error? }>
 */
async function downloadImagesBatch(urls, imagesDir) {
  if (!fs.existsSync(imagesDir)) fs.mkdirSync(imagesDir, { recursive: true });

  const results = new Map();
  const queue = [...urls];
  let done = 0;

  async function worker() {
    while (queue.length > 0) {
      const url = queue.shift();
      // 用 URL hash 做文件名（去重）
      const hash = crypto.createHash('md5').update(url).digest('hex').slice(0, 12);
      const extGuess = url.match(/\.(jpg|jpeg|png|webp|gif|svg|avif)(\?|$)/i);
      const ext = extGuess ? extGuess[1].toLowerCase() : 'webp';
      const filename = `img-${hash}.${ext}`;
      const filepath = path.join(imagesDir, filename);

      // 已存在则跳过
      if (fs.existsSync(filepath)) {
        results.set(url, { filename, existed: true });
        done++;
        continue;
      }

      try {
        const buf = await downloadToBuffer(url);
        if (buf) {
          fs.writeFileSync(filepath, buf);
          results.set(url, { filename });
        } else {
          results.set(url, { error: '下载失败' });
        }
      } catch (e) {
        results.set(url, { error: e.message });
      }
      done++;
    }
  }

  const workers = Array.from({ length: Math.min(IMAGE_CONCURRENCY, queue.length) }, () => worker());
  await Promise.all(workers);
  return results;
}

// ========== HTML → Markdown ==========

/**
 * 判断内容是否为 HTML
 */
function isHtml(content) {
  return /<[a-z][\s\S]*>/i.test(content);
}

/**
 * 清理掘金 HTML：去掉 style、data-v-* 属性等
 */
function cleanHtml(html) {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/\s+data-v-[a-f0-9]+="[^"]*"/g, '')
    .replace(/\s+class="[^"]*"/g, (m) => /language-/.test(m) ? m : '')
    .replace(/<!---->/g, '')
    .replace(/\s+loading="[^"]*"/g, '')
    .replace(/\s+data-src="[^"]*"/g, '')
    .trim();
}

/**
 * HTML → Markdown
 */
function htmlToMarkdown(html) {
  const cleaned = cleanHtml(html);
  if (!cleaned) return '';
  return turndown.turndown(cleaned);
}

// ========== 内容处理 ==========

/**
 * 提取所有图片 URL（HTML + Markdown 格式）
 */
function extractImageUrls(text) {
  const urls = new Set();
  const htmlRe = /<img[^>]+src="([^"]+)"/g;
  const mdRe = /!\[([^\]]*)\]\(([^)]+)\)/g;
  let m;
  while ((m = htmlRe.exec(text)) !== null) { if (m[1].startsWith('http')) urls.add(m[1]); }
  while ((m = mdRe.exec(text)) !== null) { if (m[2].startsWith('http')) urls.add(m[2]); }
  return [...urls];
}

/**
 * 替换文本中的图片 URL 为本地路径
 */
function replaceImageUrls(text, results, relDir) {
  let result = text;
  for (const [url, r] of results) {
    if (r.error) continue;
    const local = `${relDir}/${r.filename}`;
    result = result.replaceAll(url, local);
  }
  return result;
}

// ========== 主逻辑 ==========

function parseBookletId(input) {
  const m = input.match(/juejin\.cn\/book\/(\d+)/);
  if (m) return m[1];
  if (/^\d+$/.test(input.trim())) return input.trim();
  throw new Error(`无法解析 booklet ID: ${input}`);
}

async function fetchBookletInfo(bookletId) {
  console.log(`📖 获取小册信息: ${bookletId}`);
  const res = await fetchJSON(`${API_BASE}/booklet_api/v1/booklet/get`, { booklet_id: bookletId });
  if (res.err_no !== 0) throw new Error(`API 错误: ${res.err_msg}`);

  const { booklet } = res.data;
  return {
    id: booklet.base_info.booklet_id,
    title: booklet.base_info.title,
    summary: booklet.base_info.summary,
    coverImg: booklet.base_info.cover_img,
    sectionCount: booklet.base_info.section_count,
    sectionIds: booklet.base_info.section_ids.split('|').filter(Boolean),
    authorName: booklet.user_info?.user_name || '',
    buyCount: booklet.base_info.buy_count,
  };
}

async function fetchSection(sectionId) {
  const res = await fetchJSON(`${API_BASE}/booklet_api/v1/section/get`, { section_id: sectionId });
  if (res.err_no !== 0) throw new Error(`章节 API 错误 (${sectionId}): ${res.err_msg}`);
  return res.data.section;
}

async function fetchAllSections(sectionIds) {
  const sections = [];
  for (let i = 0; i < sectionIds.length; i++) {
    const section = await fetchSection(sectionIds[i]);
    sections.push(section);
    process.stdout.write(`\r   📝 [${i + 1}/${sectionIds.length}] ${section.title || ''}`.substring(0, 80));
    if (i < sectionIds.length - 1) await sleep(REQUEST_DELAY);
  }
  console.log('');
  return sections;
}

function generateIndex(info, sections, outputDir) {
  const lines = [
    '---', `title: "${info.title}"`, `booklet_id: "${info.id}"`,
    `author: "${info.authorName}"`, `section_count: ${info.sectionCount}`,
    `source: "https://juejin.cn/book/${info.id}"`,
    `date: "${new Date().toISOString().split('T')[0]}"`, `tags: ["掘金小册"]`, '---', '',
    `# ${info.title}`, '', `> ${info.summary}`, '',
    `- **作者**: ${info.authorName}`, `- **章节数**: ${info.sectionCount}`,
    `- **来源**: [掘金小册](https://juejin.cn/book/${info.id})`, '', '## 目录', '',
  ];
  sections.forEach((s, i) => {
    const fn = `${String(i + 1).padStart(2, '0')}.md`;
    lines.push(`${i + 1}. [${s.title || `第${i + 1}章`}](./${encodeURIComponent(fn)})`);
  });
  fs.writeFileSync(path.join(outputDir, 'README.md'), lines.join('\n'), 'utf8');
}

// ========== 入口 ==========

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log('用法: node extract-juejin-booklet.mjs <booklet_url_or_id> [--output-dir <path>] [--download-images]');
    process.exit(1);
  }

  let bookletInput = args[0], outputDir = null, downloadImages = false;
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--output-dir') outputDir = args[++i];
    else if (args[i] === '--download-images') downloadImages = true;
  }

  const bookletId = parseBookletId(bookletInput);
  const info = await fetchBookletInfo(bookletId);
  console.log(`\n📚 ${info.title}`);
  console.log(`   作者: ${info.authorName} | 章节: ${info.sectionCount}`);

  const slug = safeFilename(info.title);
  const finalDir = outputDir || path.join(process.cwd(), slug);
  const imagesDir = path.join(finalDir, 'images');
  if (!fs.existsSync(finalDir)) fs.mkdirSync(finalDir, { recursive: true });

  // 下载封面
  if (downloadImages && info.coverImg) {
    try {
      const buf = await downloadToBuffer(info.coverImg);
      if (buf) {
        const ext = info.coverImg.match(/\.(jpg|jpeg|png|webp)(\?|$)/i)?.[1] || 'png';
        fs.writeFileSync(path.join(imagesDir, `cover.${ext}`), buf);
        console.log('   封面图已下载');
      }
    } catch {}
  }

  // 提取章节
  console.log(`\n📝 提取 ${info.sectionIds.length} 个章节...`);
  const sections = await fetchAllSections(info.sectionIds);

  // 处理每个章节
  let savedCount = 0, htmlConverted = 0, totalImages = 0, failedImages = 0;
  const allImageUrls = [];

  for (let i = 0; i < sections.length; i++) {
    const s = sections[i];
    let content = s.markdown_content || s.content || '';
    const title = s.title || `第${i + 1}章`;

    if (!content || content.length < 10) continue;

    // HTML → Markdown 自动转换
    if (isHtml(content)) {
      content = htmlToMarkdown(content);
      htmlConverted++;
    }

    // 收集图片 URL（稍后批量下载）
    if (downloadImages) {
      const urls = extractImageUrls(content);
      allImageUrls.push(...urls);
    }

    // 写入文件
    const frontmatter = [
      '---', `title: "${title}"`, `booklet: "${info.title}"`,
      `section_id: "${s.section_id}"`, `section_index: ${i + 1}`,
      `date: "${new Date().toISOString().split('T')[0]}"`,
      `tags: ["掘金小册", "${info.title}"]`, '---', '',
    ].join('\n');

    const markdown = content.replace(/\n{4,}/g, '\n\n\n').trim();
    const filepath = path.join(finalDir, `${String(i + 1).padStart(2, '0')}.md`);
    fs.writeFileSync(filepath, frontmatter + markdown + '\n', 'utf8');
    savedCount++;
  }

  // 批量下载图片（高并发）
  if (downloadImages && allImageUrls.length > 0) {
    // 去重
    const uniqueUrls = [...new Set(allImageUrls)];
    console.log(`\n🖼️  下载 ${uniqueUrls.length} 张图片 (${IMAGE_CONCURRENCY} 并发)...`);
    const results = await downloadImagesBatch(uniqueUrls, imagesDir);

    let downloaded = 0, existed = 0;
    for (const [, r] of results) {
      if (r.error) failedImages++;
      else if (r.existed) existed++;
      else downloaded++;
    }
    totalImages = downloaded + existed;

    // 替换所有章节文件中的图片 URL
    console.log('   🔄 替换图片路径...');
    const mdFiles = fs.readdirSync(finalDir).filter(f => f.endsWith('.md') && f !== 'README.md');
    for (const f of mdFiles) {
      const fp = path.join(finalDir, f);
      let text = fs.readFileSync(fp, 'utf8');
      text = replaceImageUrls(text, results, './images');
      fs.writeFileSync(fp, text, 'utf8');
    }
  }

  // 生成索引
  generateIndex(info, sections, finalDir);

  // 汇总
  console.log('\n========== 提取完成 ==========');
  console.log(`📚 小册: ${info.title}`);
  console.log(`📝 章节: ${savedCount}/${sections.length} 篇`);
  if (htmlConverted > 0) console.log(`🔄 HTML→MD: ${htmlConverted} 篇自动转换`);
  if (downloadImages) console.log(`🖼️  图片: ${totalImages} 张下载 | ${failedImages} 张失败`);
  console.log(`📁 目录: ${finalDir}`);
  console.log('================================');

  // 清理 agent
  httpsAgent.destroy();
  httpAgent.destroy();
}

main().catch(err => { console.error('❌ 提取失败:', err.message); process.exit(1); });
