# API 模式（Cookie + WBI 签名）

## 概述

API 模式通过 B 站官方接口直接获取视频列表，无需浏览器，速度快且数据精确。

## 前置条件

1. **Python 3.10+** 和 `requests` 库
2. **B 站登录 Cookie**（SESSDATA）

## Cookie 获取方法

### 方法一：浏览器 DevTools（推荐）

1. 在浏览器中登录 [bilibili.com](https://www.bilibili.com)
2. 按 `F12` 打开开发者工具
3. 切换到 **Application** 标签
4. 左侧 **Cookies** → `https://www.bilibili.com`
5. 找到 `SESSDATA`，复制其值

### 方法二：Console 快速获取

在 B 站任意页面的控制台执行：

```javascript
document.cookie.match(/SESSDATA=([^;]+)/)?.[1] || '未登录'
```

## Cookie 配置方式（三选一）

### 1. 配置文件（推荐，长期使用）

```bash
# 创建配置目录
mkdir -p ~/.config

# 写入配置
cat > ~/.config/bilibili-cookies.json << 'EOF'
{
  "SESSDATA": "你的 SESSDATA 值",
  "bili_jct": "你的 bili_jct 值（可选）",
  "DedeUserID": "你的 UID（可选）"
}
EOF

# 设置文件权限（仅自己可读）
chmod 600 ~/.config/bilibili-cookies.json
```

### 2. 环境变量

```bash
export BILIBILI_SESSDATA="你的 SESSDATA 值"
```

可在 `~/.zshrc` 或 `~/.bashrc` 中添加。

### 3. 命令行参数（一次性使用）

```bash
python3 scripts/api-fetch.py --mid UID --sessdata "你的 SESSDATA 值"
```

## 脚本路径

```
plugins/video-processing/skills/bilibili-video-list/scripts/api-fetch.py
```

## 用法示例

```bash
# 获取指定 UID 的全部视频（按最新发布排序）
python3 scripts/api-fetch.py --mid 1039025435

# 按播放量排序
python3 scripts/api-fetch.py --mid 1039025435 --order click

# 按收藏排序
python3 scripts/api-fetch.py --mid 1039025435 --order stow

# 只获取前 50 个
python3 scripts/api-fetch.py --mid 1039025435 --limit 50

# 通过 UP 主名字搜索
python3 scripts/api-fetch.py --name "摩的司机徐师傅" --order click

# 指定输出文件
python3 scripts/api-fetch.py --mid 1039025435 --output ./result.json

# 格式化 JSON 输出
python3 api-fetch.py --mid 1039025435 --pretty

# 缓存相关
python3 api-fetch.py --mid 1039025435                    # 首次 → API，后续 24h 内读缓存
python3 api-fetch.py --mid 1039025435 --no-cache         # 强制刷新
python3 api-fetch.py --mid 1039025435 --cache-ttl 3600   # 自定义缓存 1 小时
```

## 输出格式

```json
{
  "uploader": "UP 主名称",
  "uid": "UID",
  "order": "click",
  "totalVideos": 416,
  "fetchedVideos": 416,
  "fetchedPages": 9,
  "fetchDate": "2026-04-06T22:00:00+08:00",
  "source": "api",
  "cacheCreatedAt": "2026-04-06T22:00:00+08:00",
  "cacheExpiresAt": "2026-04-07T22:00:00+08:00",
  "videos": [
    {
      "bvid": "BV1FkUxBbEcs",
      "aid": 11345678901234,
      "title": "视频标题",
      "play": 16310000,
      "comment": 8234,
      "favorites": 56789,
      "danmaku": 5981,
      "duration": "37:06",
      "date": "2025-11-27",
      "description": "视频简介",
      "url": "https://www.bilibili.com/video/BV1FkUxBbEcs"
    }
  ]
}
```

## 与浏览器模式的对比

| 维度 | API 模式 | 浏览器模式 |
|------|----------|------------|
| **速度** | 极快（每页 50 条，1 秒/页） | 慢（每页 30 条，4 秒/页） |
| **数据精度** | 精确数值（如 16310000） | 近似值（如 1631.0万） |
| **额外字段** | 评论数、收藏数、弹幕数、简介 | 仅基础字段 |
| **依赖** | Python + requests | agent-browser |
| **风控风险** | 低（需登录 Cookie） | 高（-352 错误） |
| **DOM 依赖** | 无 | 有（DOM 变化会导致提取失败） |
| **Cookie** | 必需 | 不需要 |

## API 接口说明

| 接口 | 用途 | 需要 WBI 签名 |
|------|------|---------------|
| `/x/web-interface/nav` | 获取 WBI 密钥 | 否 |
| `/x/space/wbi/acc/info` | 获取 UP 主信息 | 是 |
| `/x/space/wbi/arc/search` | 获取视频列表 | 是 |
| `/x/web-interface/search/type` | 搜索 UP 主 | 否 |

## WBI 签名机制

B 站自 2023 年起对部分接口增加了 WBI 签名验证：

1. 调用 `/x/web-interface/nav` 获取 `img_key` 和 `sub_key`
2. 拼接 `img_key + sub_key`，通过内置混淆表重排字符
3. 取前 32 位作为签名密钥
4. 对请求参数排序、URL 编码、移除特殊字符
5. 拼接密钥后 MD5，生成 `w_rid` 参数

混淆表可能会不定期更新，脚本中已内置当前版本的混淆表。

## 注意事项

- `SESSDATA` 有效期约 30 天，过期需重新获取
- 请求间隔 1 秒，避免触发频率限制
- 搜索 UP 主名字也需要 Cookie
- 配置文件权限建议设为 `600`（仅自己可读）
- 缓存默认 24 小时有效，存储在 `~/.cache/bilibili-video-list/{uid}.json`
- 缓存按 UID + 排序方式匹配，换排序会触发重新获取

## 常见错误

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| `-352` / 风控校验失败 | Cookie 无效或过期 | 重新获取 SESSDATA |
| `-400` / 请求错误 | 参数错误 | 检查 UID 是否正确 |
| `-403` | 无权限 | 确认 Cookie 有效 |
| `ConnectionError` | 网络问题 | 检查网络连接和代理设置 |
