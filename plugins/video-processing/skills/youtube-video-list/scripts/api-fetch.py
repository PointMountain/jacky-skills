#!/usr/bin/env python3
"""
YouTube 频道视频列表获取工具

使用 yt-dlp 作为后端，无需 YouTube API Key。

用法：
    python3 api-fetch.py --name "摩的司机徐师傅"
    python3 api-fetch.py --channel-id UCWHg8GXDTAYj39Yo6XQuCLQ
    python3 api-fetch.py --handle @username
    python3 api-fetch.py --url "https://www.youtube.com/@username/videos"
    python3 api-fetch.py --name "摩的司机徐师傅" --detailed --limit 20
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

YT_DLP_BIN = os.environ.get('YT_DLP_BIN', 'yt-dlp')


def run_ytdlp(args: list[str]) -> str:
    """运行 yt-dlp 命令并返回输出"""
    cmd = [YT_DLP_BIN] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            env={**os.environ, 'LANG': 'en_US.UTF-8'}
        )
        if result.returncode != 0 and result.stderr:
            # yt-dlp 经常把正常输出写到 stderr
            pass
        return result.stdout + result.stderr
    except FileNotFoundError:
        print("错误：未找到 yt-dlp。请安装：pip3 install yt-dlp", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("错误：yt-dlp 执行超时", file=sys.stderr)
        sys.exit(1)


def search_channel(keyword: str, max_results: int = 5) -> list:
    """搜索 YouTube 频道"""
    output = run_ytdlp([
        f'ytsearch{max_results}:{keyword}',
        '--flat-playlist',
        '--print', '%(id)s|%(channel)s|%(channel_id)s|%(title)s',
    ])

    results = {}  # channel_id -> info
    for line in output.strip().split('\n'):
        if '|' not in line:
            continue
        parts = line.split('|', 3)
        if len(parts) < 4:
            continue
        video_id, channel_name, channel_id, _ = parts
        if channel_id not in results:
            results[channel_id] = {
                'channelId': channel_id,
                'name': channel_name,
            }

    return list(results.values())


def get_channel_url(identifier: str) -> str:
    """将输入统一转为 YouTube 频道 URL"""
    # channel ID
    if re.match(r'^UC[\w-]{22}$', identifier):
        return f'https://www.youtube.com/channel/{identifier}/videos'

    # URL
    if 'youtube.com' in identifier or 'youtu.be' in identifier:
        url = identifier
        if '/videos' not in url:
            url = url.rstrip('/') + '/videos'
        return url

    # @handle
    if identifier.startswith('@'):
        return f'https://www.youtube.com/{identifier}/videos'

    return identifier


def fetch_videos_fast(channel_url: str, limit: int = 0) -> list:
    """快速模式：--flat-playlist 获取列表（无播放量，速度快）"""
    args = [
        channel_url,
        '--flat-playlist',
        '--print', '%(id)s\t%(title)s\t%(duration_string)s\t%(channel)s\t%(channel_id)s',
    ]

    output = run_ytdlp(args)

    videos = []
    for line in output.strip().split('\n'):
        if '\t' not in line:
            continue
        parts = line.split('\t', 4)
        if len(parts) < 5:
            continue

        video_id, title, duration, channel_name, channel_id = parts

        videos.append({
            'videoId': video_id,
            'title': title,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'duration': duration or '',
            'channel': channel_name,
            'channelId': channel_id,
        })

        if limit > 0 and len(videos) >= limit:
            break

    return videos


def fetch_videos_detailed(video_ids: list) -> list:
    """详细模式：逐个获取视频详情（含播放量、点赞数，较慢）"""
    videos = []
    total = len(video_ids)
    batch_size = 10

    for i in range(0, total, batch_size):
        batch = video_ids[i:i+batch_size]
        print(f"获取详情中... ({i+1}-{min(i+batch_size, total)}/{total})", file=sys.stderr)

        for video_id in batch:
            try:
                output = run_ytdlp([
                    f'https://www.youtube.com/watch?v={video_id}',
                    '--dump-json', '--no-download',
                ])

                if not output.strip():
                    continue

                # 解析 JSON（yt-dlp 可能输出多行混合内容）
                json_str = output.strip()
                # 找到第一个完整的 JSON
                brace_count = 0
                json_end = 0
                for j, c in enumerate(json_str):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = j + 1
                            break

                if json_end > 0:
                    data = json.loads(json_str[:json_end])
                    videos.append({
                        'videoId': data.get('id', video_id),
                        'title': data.get('title', ''),
                        'url': f"https://www.youtube.com/watch?v={data.get('id', video_id)}",
                        'play': data.get('view_count', 0) or 0,
                        'likes': data.get('like_count', 0) or 0,
                        'comment': data.get('comment_count', 0) or 0,
                        'duration': data.get('duration_string', ''),
                        'date': (data.get('upload_date', '') or '')[:10],
                        'description': (data.get('description', '') or '')[:200],
                        'channel': data.get('channel', ''),
                        'channelId': data.get('channel_id', ''),
                    })
            except (json.JSONDecodeError, Exception) as e:
                print(f"  跳过 {video_id}: {e}", file=sys.stderr)
                continue

    return videos


# ============ 输出格式化 ============

def format_play(count: int) -> str:
    """格式化播放量"""
    if not count:
        return '-'
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def print_preview(videos: list, detailed: bool = False):
    """终端预览表格"""
    if detailed:
        print(f"\n{'序号':<4} {'播放量':>10} {'点赞':>10} {'时长':>8} {'日期':<12} 标题")
        print('-' * 90)
        for i, v in enumerate(videos[:25], 1):
            title = v.get('title', '')[:35]
            if len(v.get('title', '')) > 35:
                title += '...'
            print(
                f"{i:<4} {format_play(v.get('play', 0)):>10} "
                f"{format_play(v.get('likes', 0)):>10} "
                f"{v.get('duration', ''):>8} "
                f"{v.get('date', ''):<12} {title}"
            )
    else:
        print(f"\n{'序号':<4} {'时长':>8} 标题")
        print('-' * 70)
        for i, v in enumerate(videos[:25], 1):
            title = v.get('title', '')[:45]
            if len(v.get('title', '')) > 45:
                title += '...'
            print(f"{i:<4} {v.get('duration', ''):>8} {title}")

    if len(videos) > 25:
        print(f"... 还有 {len(videos) - 25} 个视频")


# ============ 主程序 ============

def main():
    parser = argparse.ArgumentParser(
        description='YouTube 频道视频列表获取（基于 yt-dlp，无需 API Key）'
    )
    parser.add_argument('--channel-id', type=str, help='频道 ID (UC...)')
    parser.add_argument('--handle', type=str, help='频道 handle (@username)')
    parser.add_argument('--name', type=str, help='频道名字（自动搜索）')
    parser.add_argument('--url', type=str, help='频道 URL')
    parser.add_argument('--limit', type=int, default=0, help='获取数量限制（0=全部）')
    parser.add_argument('--detailed', action='store_true',
                        help='详细模式（获取播放量/点赞数，较慢）')
    parser.add_argument('--output', type=str, help='输出文件路径（默认自动生成）')
    parser.add_argument('--pretty', action='store_true', help='格式化 JSON 输出')

    args = parser.parse_args()

    if not any([args.channel_id, args.handle, args.name, args.url]):
        parser.error('必须指定 --channel-id, --handle, --name 或 --url')

    # 解析频道标识
    channel_name = ''
    channel_id = ''

    if args.name:
        # 搜索频道
        print(f"正在搜索频道：{args.name}", file=sys.stderr)
        results = search_channel(args.name)

        if not results:
            print(f"未找到频道：{args.name}", file=sys.stderr)
            sys.exit(1)

        if len(results) == 1:
            channel_id = results[0]['channelId']
            channel_name = results[0]['name']
            print(f"找到：{channel_name} (ID: {channel_id})", file=sys.stderr)
        else:
            print(f"\n找到 {len(results)} 个频道：", file=sys.stderr)
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['name']} (ID: {r['channelId']})", file=sys.stderr)

            if not sys.stdin.isatty():
                print(f"非交互模式，自动选择：{results[0]['name']}", file=sys.stderr)
                channel_id = results[0]['channelId']
                channel_name = results[0]['name']
            else:
                choice = input("\n请选择: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        channel_id = results[idx]['channelId']
                        channel_name = results[idx]['name']
                except ValueError:
                    channel_id = results[0]['channelId']
                    channel_name = results[0]['name']

        channel_url = get_channel_url(channel_id)

    elif args.url:
        channel_url = get_channel_url(args.url)
    elif args.handle:
        handle = args.handle if args.handle.startswith('@') else f'@{args.handle}'
        channel_url = get_channel_url(handle)
    elif args.channel_id:
        channel_url = get_channel_url(args.channel_id)

    # 快速获取视频列表
    print(f"\n正在获取视频列表...", file=sys.stderr)
    videos = fetch_videos_fast(channel_url, args.limit)

    if not videos:
        print("未获取到视频", file=sys.stderr)
        sys.exit(1)

    # 提取频道信息
    if not channel_name:
        channel_name = videos[0].get('channel', 'unknown')
    if not channel_id:
        channel_id = videos[0].get('channelId', '')

    print(f"\n频道：{channel_name} (ID: {channel_id})", file=sys.stderr)
    print(f"获取到 {len(videos)} 个视频", file=sys.stderr)

    # 详细模式：获取播放量等
    if args.detailed:
        print(f"\n正在获取详细信息（含播放量）...", file=sys.stderr)
        video_ids = [v['videoId'] for v in videos]
        detailed_videos = fetch_videos_detailed(video_ids)

        # 合并（保持原始顺序）
        detail_map = {v['videoId']: v for v in detailed_videos}
        for v in videos:
            if v['videoId'] in detail_map:
                v.update(detail_map[v['videoId']])

    # 构建输出 JSON
    result = {
        'channel': channel_name,
        'channelId': channel_id,
        'fetchedVideos': len(videos),
        'fetchDate': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'source': 'yt-dlp',
        'videos': videos,
    }

    # 写入文件
    indent = 2 if args.pretty else None
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path.home() / 'Downloads' / 'youtube-video-list'
        output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{channel_name}_{date_str}.json"
        output_path = output_dir / filename

    output_path.write_text(json_str, encoding='utf-8')
    print(f"\n已保存到：{output_path}", file=sys.stderr)

    # 终端预览
    print_preview(videos, args.detailed)


if __name__ == '__main__':
    main()
