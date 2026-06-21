#!/usr/bin/env python3
"""web-connect 整页截图工具。

web-access 的 /screenshot 是视口截图，长页截不全。本脚本分段滚动逐屏截图，
再按 devicePixelRatio 精确裁掉重叠、纵向拼接成一张整页长图。

用法:
    python3 fullpage-shot.py <targetId> <output.png> [proxyPort]

前提:
    - web-access cdp-proxy 运行中（默认 localhost:3456）
    - 已安装 imagemagick（magick 命令）

返回: 打印输出文件路径。
"""
import sys, json, time, subprocess, tempfile, os
import urllib.request


def main():
    if len(sys.argv) < 3:
        print("用法: python3 fullpage-shot.py <targetId> <output.png> [proxyPort]")
        sys.exit(1)
    target, out = sys.argv[1], sys.argv[2]
    port = sys.argv[3] if len(sys.argv) > 3 else "3456"
    base = f"http://localhost:{port}"

    def ev(js):
        d = json.loads(urllib.request.urlopen(f"{base}/eval?target={target}", data=js.encode()).read())
        return d.get("value")

    def get(p):
        urllib.request.urlopen(f"{base}{p}").read()

    dpr = int(float(ev("JSON.stringify(window.devicePixelRatio)")))
    vw = int(ev("JSON.stringify(window.innerWidth)"))
    vh = int(ev("JSON.stringify(window.innerHeight)"))
    doc_h = int(ev("JSON.stringify(document.body.scrollHeight)"))

    # 计算分段滚动位置（覆盖整页，末段对齐底部）
    positions, p = [], 0
    while p < doc_h:
        positions.append(min(p, max(0, doc_h - vh)))
        p += vh
    positions = sorted(set(positions))

    tmp = tempfile.mkdtemp(prefix="webconnect_shot_")
    parts, prev_bottom = [], 0
    for i, pos in enumerate(positions):
        ev(f'window.scrollTo(0,{pos});"ok"')
        time.sleep(0.4)  # 等渲染 + 懒加载
        seg = os.path.join(tmp, f"seg{i}.png")
        get(f"/screenshot?target={target}&file={seg}")
        # 该段覆盖文档 [pos, pos+vh]；裁掉与上一段重叠的顶部
        crop_top = max(0, prev_bottom - pos) * dpr
        seg_bottom = min(pos + vh, doc_h)
        keep = (seg_bottom - max(prev_bottom, pos)) * dpr
        part = os.path.join(tmp, f"part{i}.png")
        subprocess.run(["magick", seg, "-crop", f"{vw*dpr}x{keep}+0+{crop_top}", "+repage", part], check=True)
        parts.append(part)
        prev_bottom = seg_bottom

    ev('window.scrollTo(0,0);"ok"')
    subprocess.run(["magick"] + parts + ["-append", out], check=True)
    print(out)


if __name__ == "__main__":
    main()
