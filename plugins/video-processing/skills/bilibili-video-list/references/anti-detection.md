# B 站风控绕过方案（-352 错误）

## 问题

B 站空间页对自动化浏览器有风控检测，返回 `-352` 错误码（"UPINFO_ERROR: 风控校验失败"）。

## 根因

**`navigator.webdriver = true`**

agent-browser 基于 Playwright，默认暴露 `webdriver` 标志位：

```javascript
// agent-browser 默认的浏览器指纹
{
  "userAgent": "Mozilla/5.0 Chrome/145.0.0.0",
  "webdriver": true,              // ← 被检测的关键
  "headlessChrome": false,        // UA 本身正常
  "chrome": true,
  "plugins": 5,
  "hasChromeRuntime": false       // ← 另一个检测点
}
```

B 站的前端检测逻辑：
1. 读取 `navigator.webdriver`，若为 `true` → 自动化浏览器
2. 检查 `window.chrome.runtime` 是否存在
3. 结合 IP 访问频率综合判断

## 解决方案：始终使用 --headed 模式

```bash
# ✅ 正确：有头模式，B 站对有头模式更宽容
agent-browser open --headed "https://space.bilibili.com/${UID}/upload/video"

# ❌ 错误：无头模式，100% 触发 -352
agent-browser open "https://space.bilibili.com/${UID}/upload/video"
```

### 各模式对比

| 模式 | webdriver 标志 | -352 风控 | 视频列表加载 |
|------|---------------|-----------|-------------|
| 无头（默认） | `true` | 必触发 | 无法加载 |
| 有头（--headed） | `true` | 不触发 | 正常加载 |

**关键发现**：即使 `webdriver=true`，只要是有头模式（有真实浏览器窗口），B 站就不会触发 -352。说明 B 站的检测不仅看 `webdriver` 标志，还结合了窗口/渲染环境判断。

## 错误恢复流程

```
打开空间页 → 检查视频卡片数
  ├── count > 0 → 正常，继续采集
  ├── 页面含 "-352" → 风控拦截
  │   ├── 当前是无头模式 → 关闭，改用 --headed 重试
  │   ├── 当前是有头模式 → 等待 5 分钟后重试（IP 限流）
  │   └── 持续失败 → 建议换网络或等待 15 分钟
  ├── 页面含 "还没投过视频" → UP 主确实无视频
  └── 其他 → 页面加载异常，等待 8 秒后重试
```

## 注意事项

1. **不要短时间内频繁刷新**：B 站会根据 IP 频率限流
2. **翻页间隔 2-3 秒**：模拟人类行为
3. **采集完成后立即关闭浏览器**：`agent-browser close`
4. **如持续被拦截**：可能是 IP 级别限制，等待 10-15 分钟或换网络

## 检测代码

用于诊断当前浏览器指纹状态：

```javascript
JSON.stringify({
  userAgent: navigator.userAgent,
  webdriver: navigator.webdriver,
  headlessChrome: navigator.userAgent.includes('HeadlessChrome'),
  chrome: !!window.chrome,
  plugins: navigator.plugins?.length,
  hasChromeRuntime: !!window.chrome?.runtime
})
```
