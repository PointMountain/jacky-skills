# 数据提取脚本

## 视频数据提取（修复版）

原始脚本存在播放量、时长、日期提取不完整的问题。以下为修复后的版本。

### 问题修复记录

| 问题 | 原因 | 修复 |
|------|------|------|
| 播放量丢失 | 正则 `([\d.]+万?)` 匹配到标题中的数字 | 改为 `([\d.]+万?)\n\d+\n` 匹配播放+弹幕区域 |
| 时长丢失 | 正则 `(\d+:\d{2})\s*$` 要求行尾空白 | 改为 `(\d{1,2}:\d{2}(?::\d{2})?)` 不要求行尾 |
| 日期丢失 | 只匹配 `\d{2}-\d{2}` 格式 | 改为取 `innerText` 最后一行（兼容"17小时前"等） |

### 卡片 DOM 结构

```
.upload-video-card
  ├── 标签区：最新 / 抢先看
  ├── 播放量 + 弹幕数："41.5万\n5981\n"
  ├── 时长："41:42"
  ├── 标题链接：a[href*="bilibili.com/video/"] 内含 BV 号
  └── 日期："17小时前" 或 "04-02"
```

`card.innerText` 示例：
```
最新\n41.5万\n5981\n41:42\n北漂猛男，十几年来靠打游戏...\n17小时前
```

### 完整提取脚本

```javascript
JSON.stringify({
  videos: Array.from(document.querySelectorAll('.upload-video-card')).map(card => {
    const link = card.querySelector('a[href*="bilibili.com/video/"]');
    const href = link ? link.href : '';
    const bvid = (href.match(/BV[\w]+/) || [''])[0] || '';
    const titleEl = card.querySelector('.bili-video-card__title a, .video-title');
    const title = titleEl ? titleEl.textContent.trim() : '';
    const rawText = card.innerText;
    // 播放量：匹配 "数字万?\n数字\n" 模式（播放量后跟弹幕数）
    const playMatch = rawText.match(/([\d.]+万?)\n\d+\n/);
    const play = playMatch ? playMatch[1] : '';
    // 时长：匹配 HH:MM:SS 或 MM:SS 格式
    const durationMatch = rawText.match(/(\d{1,2}:\d{2}(?::\d{2})?)/);
    const duration = durationMatch ? durationMatch[1] : '';
    // 日期：取最后一行（兼容"17小时前"/"04-02"/"2025-12-31"）
    const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
    const date = lines[lines.length - 1] || '';
    return { bvid, title, play, duration, date, url: 'https://www.bilibili.com/video/' + bvid };
  }),
  count: document.querySelectorAll('.upload-video-card').length
})
```

### 使用方式

```bash
agent-browser eval --stdin <<'EVALEOF'
# 上面的脚本内容
EVALEOF
```

## 翻页脚本

```javascript
const nextBtn = Array.from(document.querySelectorAll('button'))
  .find(b => b.textContent.includes('下一页'));
if (nextBtn) { nextBtn.click(); 'clicked'; } else { 'last_page'; }
```

## 排序切换脚本

排序按钮是 `.radio-filter__item`（div，不是 button），需要用 JS 点击：

```javascript
const items = document.querySelectorAll('.radio-filter__item');
items.forEach(item => {
  if (item.textContent.trim().includes('最多播放')) item.click();
  // 或 '最多收藏'
});
'done'
```

**不要用** `agent-browser snapshot -s ".video-order-filter"` 后 click ref 的方式，
该选择器会匹配到 10 个元素导致 strict mode 报错。

## JSON 输出格式

```json
{
  "uploader": "摩的司机徐师傅",
  "uid": "3493117728656046",
  "order": "click",
  "totalVideos": 416,
  "fetchedPages": 11,
  "fetchDate": "2026-04-06T22:00:00+08:00",
  "videos": [
    {
      "bvid": "BV1FkUxBbEcs",
      "title": "我13岁开始吸毒...",
      "play": "1631.0万",
      "duration": "37:06",
      "date": "2025-11-27",
      "url": "https://www.bilibili.com/video/BV1FkUxBbEcs"
    }
  ]
}
```

文件名：`~/Downloads/bilibili-video-list/{UP主名}_{排序}_{日期}.json`
