# 抖音抓取内部原理 & 自愈指南

> 仅在 `scripts/douyin-works.mjs` 抓到 0 条、字段大面积为 null、或要扩展到别的平台时才需要读本文。

## 目录
- [一、为什么走 CDP 读 fiber](#一为什么走-cdp-读-fiber)
- [二、抓取的两个关键点](#二抓取的两个关键点)
- [三、selector / fiber 失效时怎么自愈](#三selector--fiber-失效时怎么自愈)
- [四、踩过的坑（别重踩）](#四踩过的坑别重踩)
- [五、被否定过的备选方案](#五被否定过的备选方案)

## 一、为什么走 CDP 读 fiber

抖音创作者中心「作品管理」页（`creator.douyin.com/creator-micro/content/manage`）是 React SPA + **虚拟列表**：滚动时 DOM 里始终只保留约 12 个作品卡片，旧卡片被回收。所以：

- 想要的全字段（播放/赞/评/转/藏/发布时间）都在组件 props 里，不在静态 DOM 文本里；DOM 文本还是「1.2万」这种缩写。
- 解法：从卡片 DOM 元素拿 React Fiber，沿 `.return` 上溯找到挂着完整 `aweme` 数据对象的那一层，直接读 `statistics`。这条路质量等同接口 JSON。

## 二、抓取的两个关键点

**1. 卡片容器 selector**（`douyin-works.mjs` 里的 `CARD_SELECTOR`）
```
[class*="video-card-content-"]
```
class 带 hash 后缀（如 `video-card-content-a1b2c3`），**必须用前缀匹配 `class*=`**，不能写死全名。

**2. fiber 取数**（`COLLECT_JS` 核心逻辑）
```js
const k = Object.keys(el).find(k => k.startsWith('__reactFiber'));  // React 17/18 的 fiber key
let n = el[k], data = null, depth = 0;
while (n && depth < 40) {                 // 向上最多找 40 层
  const m = n.memoizedProps && n.memoizedProps.data;
  if (m && m.aweme_id) { data = m; break; }  // 找到含 aweme_id 的 data 即是完整 aweme 对象
  n = n.return; depth++;
}
```
`data` 结构（用到的字段）：
- `aweme_id` / `desc`（文案）/ `create_time`（Unix 秒）/ `duration`
- `statistics.{play_count, digg_count, comment_count, share_count, collect_count, forward_count}`
- `status.{reviewed, in_reviewing, is_private, is_delete}`

**3. 翻页**：虚拟列表懒加载要靠组合触发，单独一个常不生效——
```js
window.scrollTo(0, document.body.scrollHeight + 3000);
window.dispatchEvent(new Event('scroll'));
```
外加 `opencli browser <session> scroll down` + `sleep 2.5`。每轮 `eval` 采集后按 `aweme_id` 去重累积（脚本里用 Map），不能依赖页面侧变量持久化（见坑 ②）。

## 三、selector / fiber 失效时怎么自愈

抖音改版后按顺序排查（都用 `opencli browser dy eval '<js>'` 跑，`dy` 换成你的 session）：

1. **确认页面加载对了**：`eval 'location.href'` 应是 content/manage；`screenshot /tmp/s.png` 肉眼看有没有作品列表。
2. **找新的卡片 selector**：
   ```js
   // 列出页面上重复出现、像卡片的 class 前缀
   eval '[...document.querySelectorAll("[class*=card]")].slice(0,5).map(e=>e.className)'
   ```
   找到包裹单个作品的稳定 class 前缀，改 `CARD_SELECTOR`。
3. **确认 fiber 路径**：拿一个卡片，打印它 fiber 链上每层 `memoizedProps` 的 key，看 `data`（或新字段名）在第几层：
   ```js
   eval '(()=>{const el=document.querySelector("<新selector>");const k=Object.keys(el).find(k=>k.startsWith("__reactFiber"));let n=el[k],o=[],d=0;while(n&&d<40){o.push(Object.keys(n.memoizedProps||{}));n=n.return;d++;}return JSON.stringify(o)})()'
   ```
   若数据不在 `memoizedProps.data`，改 `COLLECT_JS` 里的取值路径（可能变成 `memoizedProps.item`、`memoizedProps.info` 之类）。
4. 改完重跑 `node scripts/douyin-works.mjs --count 5` 小样验证。

## 四、踩过的坑（别重踩）

| 坑 | 现象 | 正确做法 |
|----|------|---------|
| ① network body 截断 | `opencli browser network` 响应体硬截断到 4000 字符，`--max-body 0` 也救不回 | 作品列表接口 JSON 每条几 KB，装不下；**别走网络层抓大 JSON**，用 fiber |
| ② eval 在 isolated world | `document.cookie` 报 SecurityError、同源 `fetch` 报 Failed to fetch（被当跨域）| **别在页内 fetch 重放接口**；跨多次 eval 的页面变量可能不持久，去重放脚本侧做 |
| ③ reload 黑屏 | `location.reload()` 把页面搞成全黑/异常 | 刷新一律用 `opencli browser <session> open <url>` 重新导航 |
| ④ network 缓冲消费即清空 | 第二次 `network` 常返回 count:0 | 靠重新 `open` 触发请求流才能再抓到（但本方案不依赖它）|
| ⑤ session 页面被重置 | `eval 'location.href'` 返回 `about:blank` | 重新 `open` 作品管理页即可（脚本已内置一次重试）|

## 五、被否定过的备选方案

| 方案 | 为什么不用 |
|------|-----------|
| `opencli douyin videos` | 创作中心 adapter 只回首屏 ~6 条，`--page/--limit` 不生效 |
| `opencli douyin stats <id>` | 返回 `Douyin API error 4`，此账号不可用 |
| `opencli douyin user-videos <sec_uid>` | 公开 API，单次上限 20、需 sec_uid——抓「别人的号」可用，抓自己本号不如 fiber 全 |
| 页内 fetch 调内部接口 `work_list` | 接口存在（`creator.douyin.com/janus/douyin/creator/pc/work_list`）但 isolated world 跨域被拦 + network 截断，双重受阻 |
