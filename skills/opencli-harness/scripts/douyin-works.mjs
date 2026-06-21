#!/usr/bin/env node
/**
 * 抖音创作中心作品数据抓取引擎（OpenCLI CDP + React Fiber）
 *
 * 前提：本机已装 OpenCLI（`opencli doctor` 三项绿），且 Chrome 已登录
 *       creator.douyin.com（创作者中心）。
 *
 * 原理：创作中心「作品管理」页是虚拟列表，DOM 只渲染约 12 个卡片。
 *       从卡片 DOM 的 __reactFiber* 沿 .return 上溯，取 memoizedProps.data
 *       （完整 aweme 对象），其 statistics 含 play/digg/comment/share/collect，
 *       比 DOM 文本精确（无「万」缩写）。边滚动边采集、按 aweme_id 去重累积。
 *
 * 用法：
 *   node douyin-works.mjs [--count 30] [--out out.json] [--session dy-fetch] [--max-rounds 30]
 *   不给 --out 则打印 JSON 到 stdout；进度/日志走 stderr。
 *
 * 退出码：0 成功；2 未登录；3 抓到 0 条（页面结构可能已变，见 references/douyin-internals.md）
 */

import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

// ---------- 参数 ----------
const argv = process.argv.slice(2);
const arg = (name, def) => {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : def;
};
const COUNT = parseInt(arg('--count', '30'), 10);
const SESSION = arg('--session', 'dy-fetch');
const OUT = arg('--out', '');
const MAX_ROUNDS = parseInt(arg('--max-rounds', '30'), 10);
const MANAGE_URL = 'https://creator.douyin.com/creator-micro/content/manage';

// ---------- OpenCLI 调用封装 ----------
const NOISE = /UNDICI|trace-warnings|Update available|npm install -g|^\s*$/;
const clean = (s) => (s || '').split('\n').filter((l) => !NOISE.test(l)).join('\n').trim();

function browser(...a) {
  const r = spawnSync('opencli', ['browser', SESSION, ...a], { encoding: 'utf8', timeout: 150000 });
  return { out: clean(r.stdout), err: clean(r.stderr), code: r.status };
}
const evalJs = (js) => browser('eval', js).out;
const sleep = (sec) => spawnSync('sleep', [String(sec)]);

// ---------- 注入页面的 JS（卡片 selector + fiber 取数）----------
// 卡片容器 class 带 hash 后缀（会变），必须用前缀匹配 class*=
const CARD_SELECTOR = '[class*="video-card-content-"]';
const COLLECT_JS = `(() => {
  const cards = document.querySelectorAll('${CARD_SELECTOR}');
  const out = [];
  for (const el of cards) {
    const k = Object.keys(el).find((k) => k.startsWith('__reactFiber'));
    if (!k) continue;
    let n = el[k], data = null, depth = 0;
    while (n && depth < 40) {
      const m = n.memoizedProps && n.memoizedProps.data;
      if (m && m.aweme_id) { data = m; break; }
      n = n.return; depth++;
    }
    if (!data) continue;
    const s = data.statistics || {};
    const st = data.status || {};
    out.push({
      aweme_id: String(data.aweme_id),
      desc: data.desc || '',
      create_time: data.create_time || null,
      play_count: s.play_count ?? null,
      digg_count: s.digg_count ?? null,
      comment_count: s.comment_count ?? null,
      share_count: s.share_count ?? null,
      collect_count: s.collect_count ?? null,
      reviewed: st.reviewed ?? null,
      in_reviewing: st.in_reviewing ?? null,
      is_delete: st.is_delete ?? null,
      is_private: st.is_private ?? null
    });
  }
  return JSON.stringify(out);
})()`;

// 强制触发懒加载：滚到底 + 派发 scroll 事件，返回当前卡片数
const SCROLL_JS = `(() => {
  window.scrollTo(0, document.body.scrollHeight + 3000);
  window.dispatchEvent(new Event('scroll'));
  return document.querySelectorAll('${CARD_SELECTOR}').length;
})()`;

// ---------- 主流程 ----------
console.error(`[douyin-fetch] 目标 ${COUNT} 条，session=${SESSION}`);

console.error('打开创作中心·作品管理页…');
browser('open', MANAGE_URL);
sleep(5);

// 登录态校验：被踢到登录/passport 页即判未登录
const href = evalJs('location.href');
if (/login|passport|sso|\/user\/login/i.test(href) || href === 'about:blank') {
  // about:blank 再给一次机会重开
  if (href === 'about:blank') {
    browser('open', MANAGE_URL);
    sleep(5);
  }
  const href2 = evalJs('location.href');
  if (/login|passport|sso/i.test(href2)) {
    console.error('❌ 未登录抖音创作者中心。请先在本机 Chrome 打开并登录 https://creator.douyin.com 后重试。');
    process.exit(2);
  }
}

// 滚动 + 采集循环（按 aweme_id 去重累积）
const store = new Map();
let stagnant = 0;
for (let round = 1; round <= MAX_ROUNDS; round++) {
  const raw = evalJs(COLLECT_JS);
  let arr = [];
  try {
    arr = JSON.parse(raw);
  } catch {
    console.error(`round ${round}: 采集解析失败，输出片段「${(raw || '').slice(0, 160)}」`);
  }
  const before = store.size;
  for (const it of arr) if (it.aweme_id) store.set(it.aweme_id, it);
  const gained = store.size - before;
  console.error(`round ${round}: 可见 ${arr.length} / 累计 ${store.size}（+${gained}）`);

  if (store.size >= COUNT) break;
  stagnant = gained === 0 ? stagnant + 1 : 0;
  if (stagnant >= 3) {
    console.error('连续 3 轮无新增，停止（可能已到账号底部）');
    break;
  }
  evalJs(SCROLL_JS);
  browser('scroll', 'down');
  sleep(2.5);
}

if (store.size === 0) {
  console.error('❌ 抓到 0 条。多半是卡片 selector 或 fiber 路径变了，见 references/douyin-internals.md 自愈。');
  process.exit(3);
}

// 整理：按发布时间倒序，取前 COUNT
const pad = (n) => String(n).padStart(2, '0');
const fmtTime = (t) => {
  if (!t) return null;
  const d = new Date(t * 1000);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
const statusOf = (it) =>
  it.is_delete ? 'deleted' : it.in_reviewing ? 'reviewing' : it.is_private ? 'private' : 'published';

const result = Array.from(store.values())
  .sort((a, b) => (b.create_time || 0) - (a.create_time || 0))
  .slice(0, COUNT)
  .map((it, i) => ({
    rank: i + 1,
    aweme_id: it.aweme_id,
    title: it.desc,
    play_count: it.play_count,
    like_count: it.digg_count,
    comment_count: it.comment_count,
    share_count: it.share_count,
    collect_count: it.collect_count,
    publish_time: fmtTime(it.create_time),
    status: statusOf(it),
    video_url: `https://www.douyin.com/video/${it.aweme_id}`
  }));

const json = JSON.stringify(result, null, 2);
if (OUT) {
  writeFileSync(OUT, json);
  console.error(`✅ 已写入 ${OUT}（${result.length} 条）`);
} else {
  console.log(json);
}
console.error(`[douyin-fetch] 完成：${result.length} 条（目标 ${COUNT}）`);
