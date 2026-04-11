#!/usr/bin/env python3
"""
B站 API 方式获取 UP 主视频列表

使用 WBI 签名 + Cookie 直接调用 B 站接口，无需浏览器。

用法：
    python3 api-fetch.py --mid 1039025435 --order pubdate
    python3 api-fetch.py --mid 1039025435 --order click --limit 50
    python3 api-fetch.py --name "摩的司机徐师傅" --order click

配置 Cookie（自动 + 手动，优先级从高到低）：
    1. 命令行参数：--sessdata YOUR_SESSDATA
    2. 环境变量：export BILIBILI_SESSDATA=YOUR_SESSDATA
    3. 配置文件：~/.config/bilibili-cookies.json
    4. 自动提取：从 Chrome / Edge 浏览器 Cookie 数据库读取（macOS）
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("需要 requests 库，运行：pip3 install requests", file=sys.stderr)
    sys.exit(1)


# ============ WBI 签名 ============

# WBI 混淆表（B 站前端内置，可能不定期更新）
MIXIN_KEY_ENC_TAB = [
    46, 47, 18,  2, 53,  8, 23, 32, 15, 50, 10, 31, 58,  3, 45, 35,
    27, 43,  5, 49, 33,  9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 16,
    55, 57, 51, 44, 24,  6, 17, 54, 36, 13, 34,  7, 48, 20, 25, 22,
    40, 21, 37, 11,  1, 52, 26,  4, 30,  0, 56, 59, 60, 61, 62, 63
]


def get_mixin_key(orig: str) -> str:
    """通过混淆表生成签名密钥（取前 32 位）"""
    return ''.join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def wbi_sign(params: dict, img_key: str, sub_key: str) -> dict:
    """对请求参数进行 WBI 签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    params = dict(params)
    params['wts'] = int(time.time())
    # 按 key 排序
    params = dict(sorted(params.items()))
    # URL 编码后移除特殊字符
    query = urllib.parse.urlencode(params)
    query = re.sub(r"[!'()*]", '', query)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = w_rid
    return params


# ============ Cookie 管理 ============

DEFAULT_CONFIG_PATH = Path.home() / '.config' / 'bilibili-cookies.json'


def _extract_browser_cookie() -> str | None:
    """从 Chrome/Edge 浏览器 Cookie 数据库提取 SESSDATA（仅 macOS）。"""
    import shutil
    import struct
    import tempfile

    # macOS Chrome/Edge Cookie 路径
    browser_paths = [
        ('Chrome', Path.home() / 'Library/Application Support/Google/Chrome/Default/Cookies'),
        ('Edge', Path.home() / 'Library/Application Support/Microsoft Edge/Default/Cookies'),
    ]

    for browser_name, cookie_path in browser_paths:
        if not cookie_path.exists():
            continue

        try:
            # 复制到临时文件，避免锁定问题
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                tmp_path = Path(tmp.name)
            shutil.copy2(cookie_path, tmp_path)

            # 从 macOS Keychain 获取 Safe Storage 密钥
            safe_storage_name = f'{browser_name} Safe Storage'
            result = subprocess.run(
                ['security', 'find-generic-password', '-w', '-s', safe_storage_name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                continue

            password = result.stdout.strip().encode('utf-8')
            # Chrome v80+ 使用 PBKDF2 派生密钥
            import hashlib as _hl
            key = _hl.pbkdf2_hmac('sha1', password, b'saltysalt', 1003, dklen=16)

            # 读取加密的 Cookie
            import sqlite3
            conn = sqlite3.connect(str(tmp_path))
            cursor = conn.execute(
                "SELECT encrypted_value FROM cookies WHERE host_key LIKE '%.bilibili.com%' AND name = 'SESSDATA' LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            tmp_path.unlink(missing_ok=True)

            if not row or not row[0]:
                continue

            encrypted = row[0]
            # v10 前缀表示 AES-CBC 加密
            if encrypted[:3] == b'v10':
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend
                cipher = Cipher(algorithms.AES(key), modes.CBC(b' ' * 16), backend=default_backend())
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(encrypted[3:]) + decryptor.finalize()
                # 去除 PKCS7 填充
                pad_len = decrypted[-1]
                if 1 <= pad_len <= 16 and all(b == pad_len for b in decrypted[-pad_len:]):
                    decrypted = decrypted[:-pad_len]
                # 解密后前面可能有 Chrome 内部 metadata 字节
                # SESSDATA 是 URL 编码格式（含 %2C 等），用正则提取
                text = decrypted.decode('latin-1')
                match = re.search(r'[a-f0-9]+%2C\d+%2C', text)
                if match:
                    # 找到 SESSDATA 模式的起始位置
                    start = match.start()
                    # 从这个位置往前看看有没有更多 hex 字符
                    while start > 0 and text[start-1] in '0123456789abcdefABCDEF%':
                        start -= 1
                    sessdata = text[start:].strip()
                    if sessdata and len(sessdata) > 20:
                        print(f"从 {browser_name} 浏览器提取到 SESSDATA（长度 {len(sessdata)}）", file=sys.stderr)
                        return sessdata
        except Exception as e:
            print(f"从 {browser_name} 提取 Cookie 失败：{e}", file=sys.stderr)
            continue

    return None


def get_cookie(sessdata_arg: str | None = None) -> dict:
    """获取 Cookie 配置，优先级：命令行 > 环境变量 > 配置文件 > 浏览器自动提取"""
    cookies = {}

    # 0. 浏览器自动提取（最低优先级，作为兜底）
    browser_sessdata = _extract_browser_cookie()
    if browser_sessdata:
        cookies['SESSDATA'] = browser_sessdata

    # 1. 配置文件
    if DEFAULT_CONFIG_PATH.exists():
        try:
            data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding='utf-8'))
            cookies = data
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. 环境变量
    env_sessdata = os.environ.get('BILIBILI_SESSDATA')
    if env_sessdata:
        cookies['SESSDATA'] = env_sessdata

    # 3. 命令行参数
    if sessdata_arg:
        cookies['SESSDATA'] = sessdata_arg

    return cookies


def build_cookie_header(cookies: dict) -> str:
    """构建 Cookie 请求头"""
    parts = []
    for key in ['SESSDATA', 'bili_jct', 'DedeUserID', 'buvid3', 'buvid4']:
        if cookies.get(key):
            parts.append(f'{key}={cookies[key]}')
    return '; '.join(parts)


# ============ API 调用 ============

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.bilibili.com',
    'Origin': 'https://www.bilibili.com',
    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
}


class BilibiliAPI:
    """B 站 API 客户端，封装 WBI 签名和 Cookie 认证"""

    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.cookie_header = build_cookie_header(cookies)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        if self.cookie_header:
            self.session.headers['Cookie'] = self.cookie_header
        self._wbi_keys = None

    def _get_wbi_keys(self) -> tuple[str, str]:
        """获取 WBI 签名所需的 img_key 和 sub_key"""
        if self._wbi_keys:
            return self._wbi_keys

        resp = self.session.get('https://api.bilibili.com/x/web-interface/nav')
        data = resp.json()

        if data['code'] != 0:
            print(f"获取 WBI 密钥失败: {data.get('message', '未知错误')}", file=sys.stderr)
            print("请检查 Cookie 是否有效（SESSDATA 是否过期）", file=sys.stderr)
            sys.exit(1)

        img_url = data['data']['wbi_img']['img_url']
        sub_url = data['data']['wbi_img']['sub_url']

        img_key = img_url.split('/')[-1].split('.')[0]
        sub_key = sub_url.split('/')[-1].split('.')[0]

        self._wbi_keys = (img_key, sub_key)
        return self._wbi_keys

    def _signed_get(self, url: str, params: dict) -> dict:
        """带 WBI 签名的 GET 请求"""
        img_key, sub_key = self._get_wbi_keys()
        signed_params = wbi_sign(params, img_key, sub_key)
        resp = self.session.get(url, params=signed_params)

        # 412 风控拦截：等待后重试一次
        if resp.status_code == 412:
            print("遇到 412 风控，等待 3 秒后重试...", file=sys.stderr)
            time.sleep(3)
            resp = self.session.get(url, params=signed_params)

        if resp.status_code != 200:
            print(f"请求失败: HTTP {resp.status_code}", file=sys.stderr)
            return {'code': -resp.status_code, 'message': f'HTTP {resp.status_code}'}

        return resp.json()

    def get_user_info(self, mid: int) -> dict:
        """获取 UP 主基本信息"""
        data = self._signed_get(
            'https://api.bilibili.com/x/space/wbi/acc/info',
            {'mid': mid}
        )
        if data['code'] != 0:
            print(f"获取用户信息失败: {data.get('message', '未知错误')}", file=sys.stderr)
            sys.exit(1)
        return data['data']

    def search_user(self, keyword: str) -> list:
        """搜索 UP 主（通过名字），优先使用 WBI 签名搜索"""
        # 方法 1：WBI 签名搜索（最可靠）
        try:
            data = self._signed_get(
                'https://api.bilibili.com/x/web-interface/search/type',
                params={'search_type': 'bili_user', 'keyword': keyword}
            )
            if data.get('code') == 0 and data.get('data', {}).get('result'):
                results = []
                for user in data['data']['result']:
                    results.append({
                        'mid': user['mid'],
                        'name': user.get('uname', user.get('title', '')),
                        'fans': user.get('fans', 0),
                        'videos': user.get('videos', 0),
                    })
                return results
            print(f"WBI 搜索返回 code={data.get('code')}，尝试备用", file=sys.stderr)
        except Exception as e:
            print(f"WBI 搜索异常: {e}", file=sys.stderr)

        # 方法 2：直接 HTTP 请求（不经过 session）
        try:
            headers = dict(HEADERS)
            headers['Referer'] = 'https://search.bilibili.com'
            if self.cookie_header:
                headers['Cookie'] = self.cookie_header
            resp = requests.get(
                'https://api.bilibili.com/x/web-interface/search/type',
                params={'search_type': 'bili_user', 'keyword': keyword},
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and data.get('data', {}).get('result'):
                    results = []
                    for user in data['data']['result']:
                        results.append({
                            'mid': user['mid'],
                            'name': user.get('uname', user.get('title', '')),
                            'fans': user.get('fans', 0),
                            'videos': user.get('videos', 0),
                        })
                    return results
        except Exception as e:
            print(f"直接搜索也失败: {e}", file=sys.stderr)

        return []

    def get_video_list(self, mid: int, order: str = 'pubdate',
                       page: int = 1, page_size: int = 50) -> dict:
        """获取 UP 主视频列表（单页）"""
        params = {
            'mid': mid,
            'pn': page,
            'ps': page_size,
            'order': order,
        }
        data = self._signed_get(
            'https://api.bilibili.com/x/space/wbi/arc/search',
            params
        )

        if data['code'] != 0:
            print(f"获取视频列表失败: {data.get('message', '未知错误')}", file=sys.stderr)
            sys.exit(1)

        return data['data']

    def get_all_videos(self, mid: int, order: str = 'pubdate',
                       limit: int = 0) -> tuple[list, int]:
        """获取所有视频（自动翻页）"""
        all_videos = []
        page = 1
        total = None

        while True:
            print(f"正在获取第 {page} 页...", file=sys.stderr)
            data = self.get_video_list(mid, order, page, page_size=50)

            if total is None:
                total = data['page']['count']
                print(f"共 {total} 个视频", file=sys.stderr)

            vlist = data.get('list', {}).get('vlist', [])
            if not vlist:
                break

            for v in vlist:
                all_videos.append({
                    'bvid': v.get('bvid', ''),
                    'aid': v.get('aid', 0),
                    'title': v.get('title', ''),
                    'play': v.get('play', 0),
                    'comment': v.get('comment', 0),
                    'favorites': v.get('favorites', 0),
                    'danmaku': v.get('video_review', 0),
                    'duration': v.get('length', ''),
                    'date': datetime.fromtimestamp(
                        v.get('created', 0),
                        tz=timezone(timedelta(hours=8))
                    ).strftime('%Y-%m-%d') if v.get('created') else '',
                    'description': v.get('description', ''),
                    'url': f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                })

            # 数量限制
            if limit > 0 and len(all_videos) >= limit:
                all_videos = all_videos[:limit]
                break

            # 检查是否还有下一页
            if page * 50 >= total:
                break

            page += 1
            time.sleep(1)  # 请求间隔，避免触发限流

        return all_videos, total


# ============ UID 解析 ============

def resolve_uid(api: BilibiliAPI, identifier: str) -> int:
    """解析 UID（支持纯数字、空间 URL、UP 主名字）"""
    # 纯数字 → 直接作为 UID
    if identifier.isdigit():
        return int(identifier)

    # URL → 提取 UID
    url_match = re.search(r'space\.bilibili\.com/(\d+)', identifier)
    if url_match:
        return int(url_match.group(1))

    # 名字 → 搜索
    print(f"正在搜索 UP 主：{identifier}", file=sys.stderr)
    results = api.search_user(identifier)

    if not results:
        print(f"未找到 UP 主：{identifier}", file=sys.stderr)
        print("提示：搜索需要 Cookie，请确认已配置 SESSDATA", file=sys.stderr)
        sys.exit(1)

    if len(results) == 1:
        print(f"找到：{results[0]['name']} (UID: {results[0]['mid']})", file=sys.stderr)
        return results[0]['mid']

    # 多个结果 → 输出列表（非交互模式自动选第一个）
    print(f"\n找到 {len(results)} 个 UP 主：", file=sys.stderr)
    for i, r in enumerate(results[:5], 1):
        print(
            f"  {i}. {r['name']} (UID: {r['mid']}, "
            f"粉丝: {r['fans']}, 视频: {r['videos']})",
            file=sys.stderr
        )

    if not sys.stdin.isatty():
        print(f"非交互模式，自动选择：{results[0]['name']}", file=sys.stderr)
        return results[0]['mid']

    choice = input("\n请选择 (1-5): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            return results[idx]['mid']
    except ValueError:
        pass

    print("无效选择，使用第一个结果", file=sys.stderr)
    return results[0]['mid']


# ============ 缓存 ============

CACHE_DIR = Path.home() / '.cache' / 'bilibili-video-list'
DEFAULT_CACHE_TTL = 86400  # 24 hours


def get_cache_path(uid: int) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{uid}.json"


def read_cache(uid: int, order: str) -> dict | None:
    """读取缓存，返回 None 表示缓存未命中"""
    cache_path = get_cache_path(uid)
    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None

    # 检查过期
    expires_at = data.get('cacheExpiresAt', '')
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at)
        if datetime.now(timezone.utc) > expires_dt.astimezone(timezone.utc):
            return None

    # 检查排序方式是否匹配
    if data.get('order') != order:
        return None

    return data


def write_cache(uid: int, data: dict, cache_ttl: int):
    """写入缓存文件"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone(timedelta(hours=8)))
    data['cacheCreatedAt'] = now.isoformat()
    data['cacheExpiresAt'] = (
        now + timedelta(seconds=cache_ttl)
    ).isoformat()

    cache_path = get_cache_path(uid)
    try:
        cache_path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding='utf-8'
        )
    except OSError as e:
        print(f"警告：写入缓存失败：{e}", file=sys.stderr)


# ============ 输出格式化 ============

def format_play(count: int) -> str:
    """格式化播放量"""
    if count >= 100_000_000:
        return f"{count / 100_000_000:.1f}亿"
    if count >= 10_000:
        return f"{count / 10_000:.1f}万"
    return str(count)


def print_preview(videos: list):
    """终端预览表格"""
    print(f"\n{'序号':<4} {'BV 号':<14} {'播放量':>10} {'时长':>8} {'日期':<12} 标题")
    print('-' * 85)
    for i, v in enumerate(videos[:20], 1):
        title = v['title'][:30]
        if len(v['title']) > 30:
            title += '...'
        print(
            f"{i:<4} {v['bvid']:<14} "
            f"{format_play(v['play']):>10} {v['duration']:>8} "
            f"{v['date']:<12} {title}"
        )
    if len(videos) > 20:
        print(f"... 还有 {len(videos) - 20} 个视频")


def write_output(result: dict, args) -> Path:
    """写入输出文件（旧版路径，向后兼容）"""
    indent = 2 if args.pretty else None
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output)
    else:
        uploader_name = result.get('uploader', 'unknown')
        output_dir = Path.home() / 'Downloads' / 'bilibili-video-list'
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{uploader_name}_{result.get('order', 'pubdate')}_{date_str}.json"
        output_path = output_dir / filename

    output_path.write_text(json_str, encoding='utf-8')
    return output_path


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(
        description='B站 API 获取 UP 主视频列表（WBI 签名 + Cookie）'
    )
    parser.add_argument('--mid', type=str, help='UP 主 UID')
    parser.add_argument('--name', type=str, help='UP 主名字（自动搜索 UID）')
    parser.add_argument(
        '--order', type=str, default='pubdate',
        choices=['pubdate', 'click', 'stow'],
        help='排序方式：pubdate(最新) click(播放量) stow(收藏)'
    )
    parser.add_argument('--limit', type=int, default=0, help='获取数量限制（0=全部）')
    parser.add_argument('--sessdata', type=str, help='B站 SESSDATA Cookie')
    parser.add_argument('--output', type=str, help='输出文件路径（默认自动生成）')
    parser.add_argument('--pretty', action='store_true', help='格式化 JSON 输出')
    parser.add_argument(
        '--cache-ttl', type=int, default=DEFAULT_CACHE_TTL,
        help=f'缓存有效期（秒），默认 {DEFAULT_CACHE_TTL}（24小时）'
    )
    parser.add_argument(
        '--no-cache', action='store_true',
        help='强制重新获取，忽略缓存'
    )

    args = parser.parse_args()

    if not args.mid and not args.name:
        parser.error('必须指定 --mid (UID) 或 --name (UP 主名字)')

    # 获取 Cookie
    cookies = get_cookie(args.sessdata)
    if not cookies.get('SESSDATA'):
        print("NO_COOKIE: 未找到 SESSDATA Cookie", file=sys.stderr)
        print("  AI 应按以下顺序降级：", file=sys.stderr)
        print("  1. CDP 模式（Chrome DevTools MCP，复用用户浏览器）", file=sys.stderr)
        print("  2. agent-browser 模式（最后兜底，有风控风险）", file=sys.stderr)
        print("  手动配置 Cookie 方式：", file=sys.stderr)
        print("    --sessdata YOUR_SESSDATA", file=sys.stderr)
        print("    export BILIBILI_SESSDATA=YOUR_SESSDATA", file=sys.stderr)
        print(f"    配置文件：{DEFAULT_CONFIG_PATH}", file=sys.stderr)
        sys.exit(2)

    # 初始化 API 客户端
    api = BilibiliAPI(cookies)

    # 解析 UID
    identifier = args.mid or args.name
    uid = resolve_uid(api, identifier)

    # --- 缓存检查 ---
    if not args.no_cache:
        cached = read_cache(uid, args.order)
        if cached:
            print(f"从缓存读取（过期时间：{cached.get('cacheExpiresAt', '未知')}）", file=sys.stderr)
            cached['fetchDate'] = datetime.now(
                timezone(timedelta(hours=8))
            ).isoformat()
            cached['source'] = 'cache'

            output_path = write_output(cached, args)
            print(f"\n已保存到：{output_path}", file=sys.stderr)
            print(f"共 {len(cached.get('videos', []))} 个视频（来自缓存）", file=sys.stderr)
            print_preview(cached.get('videos', []))
            return

    # --- API 获取 ---
    try:
        user_info = api.get_user_info(uid)
    except SystemExit:
        # 风控校验失败时，用搜索结果中的名字代替
        user_info = {'name': args.name or args.mid, 'mid': uid}
        print(f"跳过用户验证，使用名字：{user_info['name']}", file=sys.stderr)
    uploader_name = user_info.get('name', 'unknown')
    print(f"\nUP 主：{uploader_name} (UID: {uid})", file=sys.stderr)

    videos, total = api.get_all_videos(uid, args.order, args.limit)

    result = {
        'uploader': uploader_name,
        'uid': str(uid),
        'order': args.order,
        'totalVideos': total,
        'fetchedVideos': len(videos),
        'fetchedPages': (len(videos) + 49) // 50,
        'fetchDate': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'source': 'api',
        'videos': videos,
    }

    # 写入缓存
    if not args.no_cache:
        write_cache(uid, result, args.cache_ttl)
        print(f"缓存已更新：{get_cache_path(uid)}", file=sys.stderr)

    # 写入旧版输出路径
    output_path = write_output(result, args)
    print(f"\n已保存到：{output_path}", file=sys.stderr)
    print(f"共 {len(videos)} 个视频（总计 {total} 个）", file=sys.stderr)

    # 终端预览
    print_preview(videos)


if __name__ == '__main__':
    main()
