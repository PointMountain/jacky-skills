#!/usr/bin/env python3
"""skill-stats.py —— Skill 使用频率统计

读取 ~/.claude/skill-usage.jsonl（由 skill-usage-log.sh 采集），输出使用排行榜。

用法：
  python3 skill-stats.py                  # 全部时间，前 30 名
  python3 skill-stats.py --days 7         # 只看近 7 天
  python3 skill-stats.py --top 10         # 只看前 10 名
  python3 skill-stats.py --source user    # 只看用户手输 /命令（ai=AI自动调用）
  python3 skill-stats.py --by-project     # 额外按项目目录分组展示
"""
import json
import os
import sys
import argparse
import datetime
import collections
import unicodedata

LOG = os.environ.get("SKILL_USAGE_LOG", os.path.expanduser("~/.claude/skill-usage.jsonl"))


def dwidth(s):
    """字符串显示宽度（中文等宽字符算 2）"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, w):
    """按显示宽度左对齐补空格"""
    s = str(s)
    return s + " " * max(0, w - dwidth(s))


def rpad(s, w):
    """按显示宽度右对齐"""
    s = str(s)
    return " " * max(0, w - dwidth(s)) + s


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


def rel_day(dt, now):
    """相对今天的人话描述"""
    if dt is None:
        return "?"
    d = (now.date() - dt.date()).days
    if d <= 0:
        return "今天"
    if d == 1:
        return "昨天"
    return f"{d}天前"


def load(path):
    recs = []
    if not os.path.exists(path):
        return recs
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                pass
    return recs


def main():
    ap = argparse.ArgumentParser(description="Skill 使用频率统计")
    ap.add_argument("--days", type=int, default=0, help="只统计近 N 天（0=全部）")
    ap.add_argument("--top", type=int, default=30, help="显示前 N 名（默认 30）")
    ap.add_argument("--source", choices=["all", "ai", "user"], default="all",
                    help="来源过滤：all/ai/user（默认 all）")
    ap.add_argument("--by-project", action="store_true", help="额外按项目目录分组")
    args = ap.parse_args()

    now = datetime.datetime.now().astimezone()
    recs = load(LOG)

    if not recs:
        print("📊 还没有任何 skill 使用记录。")
        print(f"   数据文件：{LOG}（尚为空）")
        print("   采集 hook 装好后，下次 AI 调用 skill 或你手输 /命令就会开始记录。")
        return

    # 时间窗口过滤
    cutoff = None
    if args.days > 0:
        cutoff = now - datetime.timedelta(days=args.days)

    seven_ago = now - datetime.timedelta(days=7)

    # 聚合
    total = collections.Counter()      # skill -> 总数
    by_src = collections.defaultdict(lambda: collections.Counter())  # skill -> {ai,user}
    last_seen = {}                     # skill -> 最近 datetime
    recent7 = collections.Counter()    # skill -> 近7天次数
    proj = collections.defaultdict(collections.Counter)  # cwd -> skill -> 次数

    span_min = None
    span_max = None
    used = 0

    for r in recs:
        skill = r.get("skill")
        if not skill:
            continue
        src = r.get("source", "ai")
        if args.source != "all" and src != args.source:
            continue
        ts = parse_ts(r.get("ts", ""))
        if cutoff and ts and ts < cutoff:
            continue

        used += 1
        total[skill] += 1
        by_src[skill][src] += 1
        if ts:
            if skill not in last_seen or ts > last_seen[skill]:
                last_seen[skill] = ts
            if ts >= seven_ago:
                recent7[skill] += 1
            span_min = ts if span_min is None or ts < span_min else span_min
            span_max = ts if span_max is None or ts > span_max else span_max
        if args.by_project:
            proj[r.get("cwd", "?")][skill] += 1

    if used == 0:
        print("📊 选定条件下没有记录（试试去掉 --days / --source）。")
        return

    # ---- 总览 ----
    scope = f"近 {args.days} 天" if args.days > 0 else "全部时间"
    src_label = {"all": "全部来源", "ai": "仅 AI 自动调用", "user": "仅用户手输 /命令"}[args.source]
    print(f"📊 Skill 使用频率统计  ·  {scope}  ·  {src_label}")
    print(f"   数据源：{LOG}")
    print("─" * 72)
    ai_total = sum(c.get("ai", 0) for c in by_src.values())
    user_total = sum(c.get("user", 0) for c in by_src.values())
    span = ""
    if span_min and span_max:
        days = (span_max.date() - span_min.date()).days + 1
        span = f"  ·  {span_min.date()} ~ {span_max.date()}（{days}天）"
    print(f"   总计 {used} 次调用  ·  {len(total)} 个不同 skill{span}")
    print(f"   来源：AI 自动 {ai_total} 次  ·  用户手输 {user_total} 次")
    print("─" * 72)

    # ---- 排行榜 ----
    name_w = max([dwidth(s) for s in total] + [dwidth("Skill")])
    name_w = min(name_w, 36)
    header = (
        pad("排名", 6) + pad("Skill", name_w + 2)
        + rpad("总数", 6) + rpad("AI", 6) + rpad("用户", 6)
        + rpad("近7天", 7) + "  最近使用"
    )
    print(header)
    print("·" * 72)
    for i, (skill, cnt) in enumerate(total.most_common(args.top), 1):
        ai = by_src[skill].get("ai", 0)
        us = by_src[skill].get("user", 0)
        r7 = recent7.get(skill, 0)
        last = rel_day(last_seen.get(skill), now)
        print(
            pad(f"{i:>2}", 6) + pad(skill, name_w + 2)
            + rpad(cnt, 6) + rpad(ai, 6) + rpad(us, 6)
            + rpad(r7, 7) + "  " + last
        )

    shown = min(args.top, len(total))
    if len(total) > shown:
        print(f"   …… 还有 {len(total) - shown} 个 skill（用 --top 调整）")

    # ---- 长期未使用提示 ----
    stale = sorted(
        [(s, last_seen[s]) for s in total if s in last_seen
         and (now - last_seen[s]).days > 30],
        key=lambda x: x[1],
    )
    if stale and args.days == 0:
        print("─" * 72)
        names = ", ".join(f"{s}({rel_day(dt, now)})" for s, dt in stale[:12])
        print(f"🧊 超过 30 天未再使用：{names}")
        if len(stale) > 12:
            print(f"   （共 {len(stale)} 个）")

    # ---- 按项目分组（可选）----
    if args.by_project and proj:
        print("─" * 72)
        print("📁 按项目目录分组（各项目 Top 5）：")
        for cwd, counter in sorted(proj.items(), key=lambda x: -sum(x[1].values())):
            top5 = ", ".join(f"{s}×{c}" for s, c in counter.most_common(5))
            print(f"   {cwd}")
            print(f"      {top5}")


if __name__ == "__main__":
    main()
