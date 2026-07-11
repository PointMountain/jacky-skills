#!/usr/bin/env python3
"""
字幕/文字转语音工具 - 豆包大模型 TTS API

用法:
    # 交互模式（推荐，会引导选择音色和参数）
    python3 synthesize.py subtitle.srt
    python3 synthesize.py text.txt

    # 指定音色
    python3 synthesize.py text.txt -s BV002_streaming

    # 指定输出格式
    python3 synthesize.py subtitle.srt -f wav

    # YOLO 模式
    python3 synthesize.py subtitle.srt --yolo
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional


# ============================================================
# 配置文件管理（与 audio-to-subtitle 共享）
# ============================================================

CONFIG_DIR = Path.home() / ".audio2subtitle"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "engine": "local",
    "model": "large-v3-turbo",
    "format": "srt",
    "language": None,
    "doubao": {
        "app_id": "",
        "access_token": "",
    },
    "tts": {
        "speaker": "BV001_streaming",
        "speed": 0,
        "format": "mp3",
        "sample_rate": 24000,
    },
}

# 豆包 TTS 音色列表
SPEAKERS = {
    # --- 1.0 音色 ---
    "BV001_streaming": "通用女声（免费）",
    "BV002_streaming": "通用男声（免费）",
    "BV700_streaming": "灿灿（免费，22种情感）",
    "BV123_streaming": "阳光青年",
    "BV120_streaming": "反卷青年",
    "BV406_streaming": "梓梓（超自然音色）",
    "BV405_streaming": "甜美小源",
    "BV026_streaming": "港剧男神（粤语）",
    "BV511_streaming": "Ava（美式英语）",
    "BV421_streaming": "天才少女（8国语言）",
    "BV503_streaming": "Ariana（美式英语，免费）",
    "BV520_streaming": "元气少女（日语）",
    # --- 2.0 音色（更便宜，支持情感变化/指令遵循/ASMR） ---
    "zh_female_vv_uranus_bigtts": "Vivi 2.0（中/日/印尼/墨西哥西班牙语）",
    "zh_female_tianmeixiaoyuan_uranus_bigtts": "甜美小源 2.0",
    "zh_female_cancan_uranus_bigtts": "知性灿灿 2.0",
    "zh_female_mizai_uranus_bigtts": "黑猫侦探社咪仔 2.0",
    "zh_female_shuangkuaisisi_uranus_bigtts": "爽快思思 2.0",
    "zh_female_qingxinnvsheng_uranus_bigtts": "清新女声 2.0",
    "zh_female_sajiaoxuemei_uranus_bigtts": "撒娇学妹 2.0",
    "zh_female_linjianvhai_uranus_bigtts": "邻家女孩 2.0",
    "zh_female_kefunvsheng_uranus_bigtts": "暖阳女声 2.0",
    "zh_female_liuchangnv_uranus_bigtts": "流畅女声 2.0",
    "zh_female_xiaoxue_uranus_bigtts": "儿童绘本 2.0",
    "zh_male_sophie_uranus_bigtts": "魅力苏菲 2.0",
    "zh_male_m191_uranus_bigtts": "云舟 2.0",
    "en_female_stokie_uranus_bigtts": "Stokie（美式英语）",
    "saturn_zh_male_tiancaitongzhuo_tob": "天才同桌 2.0（指令遵循/COT/QA）",
    "saturn_zh_female_wenwanshanshan_cs_tob": "温婉珊珊 2.0",
    "saturn_zh_female_qingyingduoduo_cs_tob": "轻盈朵朵 2.0",
}

# TTS 异步 API
TTS_SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/tts/submit"
TTS_QUERY_URL = "https://openspeech.bytedance.com/api/v3/tts/query"

# resource_id 优先级列表（2.0 更便宜，优先尝试）
TTS_RESOURCE_IDS = [
    "seed-tts-2.0",              # 豆包语音合成模型 2.0（3元/万字符，推荐）
    "volc.service_type.10029",   # 大模型语音合成 1.0（5元/万字符）
]

# 文本分段阈值
MAX_CHARS_PER_REQUEST = 10000


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = {**DEFAULT_CONFIG, **saved}
            if "doubao" not in cfg:
                cfg["doubao"] = DEFAULT_CONFIG["doubao"]
            if "tts" not in cfg:
                cfg["tts"] = DEFAULT_CONFIG["tts"]
            return cfg
        except (json.JSONDecodeError, IOError):
            pass
    return {**DEFAULT_CONFIG}


def save_config(cfg: dict) -> None:
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"✅ 配置已保存到 {CONFIG_FILE}")


# ============================================================
# 豆包 TTS 凭证检查
# ============================================================

def check_doubao_config(cfg: dict) -> tuple[str, str]:
    """检查豆包 API 配置，返回 (app_id, access_token)"""
    doubao = cfg.get("doubao", {})
    app_id = doubao.get("app_id", "") or os.environ.get("DOUBAO_APP_ID", "")
    access_token = doubao.get("access_token", "") or os.environ.get("DOUBAO_ACCESS_TOKEN", "")

    if not app_id or not access_token:
        return "", ""

    return app_id, access_token


class DoubaoTtsError(Exception):
    """豆包 TTS API 错误"""

    def __init__(self, message: str, diagnosis: str = ""):
        super().__init__(message)
        self.diagnosis = diagnosis


def print_doubao_tts_guide() -> None:
    """打印豆包 TTS API 注册和申请指南"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              豆包 TTS 语音合成 API - 注册指南                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. 注册账号                                                  ║
║     访问 https://www.volcengine.com                          ║
║     使用手机号注册并完成实名认证                                ║
║                                                              ║
║  2. 开通语音合成服务                                           ║
║     访问 https://console.volcengine.com/speech                ║
║     开通「豆包大模型语音合成」服务（有免费额度）                  ║
║                                                              ║
║  3. 创建应用并获取凭证                                         ║
║     在控制台创建应用，获取 APP ID 和 Access Token              ║
║     确保应用已绑定到语音合成服务                                ║
║                                                              ║
║  4. 配置凭证                                                  ║
║     方式一: 运行本脚本 --setup-doubao                          ║
║     方式二: 写入 ~/.audio2subtitle/config.json                ║
║     方式三: 设置环境变量                                        ║
║       export DOUBAO_APP_ID=你的APP_ID                         ║
║       export DOUBAO_ACCESS_TOKEN=你的Access_Token             ║
║                                                              ║
║  💰 价格参考                                                   ║
║     大模型 TTS 1.0: 5 元/万字符（后付费）                       ║
║     大模型 TTS 2.0: 3 元/万字符（后付费）                       ║
║     新用户有 2 万字符免费额度                                    ║
║                                                              ║
║  📖 文档                                                      ║
║     https://www.volcengine.com/docs/6561/1167803              ║
║     https://www.volcengine.com/docs/6561/97465 (音色列表)      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


# ============================================================
# SRT 解析
# ============================================================

def parse_srt(srt_path: str) -> str:
    """解析 SRT 字幕文件，提取纯文本

    Args:
        srt_path: SRT 文件路径

    Returns:
        提取的纯文本内容
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    text_lines = []

    for line in lines:
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 跳过序号行（纯数字）
        if line.isdigit():
            continue
        # 跳过时间戳行
        if re.match(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}", line):
            continue
        # 其他行是文本内容
        text_lines.append(line)

    return " ".join(text_lines)


def parse_txt(txt_path: str) -> str:
    """读取纯文本文件

    Args:
        txt_path: TXT 文件路径

    Returns:
        文本内容
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_text(input_path: str) -> str:
    """根据文件扩展名解析文本

    Args:
        input_path: 输入文件路径

    Returns:
        提取的文本内容
    """
    ext = Path(input_path).suffix.lower()
    if ext == ".srt":
        return parse_srt(input_path)
    elif ext == ".txt":
        return parse_txt(input_path)
    else:
        raise ValueError(f"不支持的输入格式: {ext}，仅支持 .srt 和 .txt")


def split_text(text: str, max_chars: int = MAX_CHARS_PER_REQUEST) -> list[str]:
    """将长文本按句子边界分段

    Args:
        text: 输入文本
        max_chars: 每段最大字符数

    Returns:
        分段后的文本列表
    """
    if len(text) <= max_chars:
        return [text]

    # 按句子标点分割
    sentences = re.split(r"([。！？；\.\!\?;])", text)

    chunks = []
    current_chunk = ""

    for i, sentence in enumerate(sentences):
        # 标点符号跟回前一句
        if re.match(r"[。！？；\.\!\?;]", sentence):
            current_chunk += sentence
        else:
            if len(current_chunk) + len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# ============================================================
# 豆包 TTS 异步 API（submit + query 轮询）
# ============================================================

def synthesize_doubao_async(
    text: str,
    speaker: str,
    audio_format: str,
    sample_rate: int,
    speed: int,
    cfg: dict,
) -> bytes:
    """
    使用豆包 TTS 异步 API 合成语音（submit + query 轮询模式）

    API 文档: https://www.volcengine.com/docs/6561/1829010
    - 提交任务 → 轮询查询结果
    - 支持最长 10 万字符

    Returns:
        音频二进制数据
    """
    try:
        import requests as req
    except ImportError:
        print("❌ requests 未安装，请运行: pip install requests")
        sys.exit(1)

    app_id, access_token = check_doubao_config(cfg)
    if not app_id or not access_token:
        print("⚠️  豆包 API 凭证未配置\n")
        print_doubao_tts_guide()
        raise DoubaoTtsError(
            "豆包 API 凭证未配置。请按上述指南获取 APP ID 和 Access Token。",
            diagnosis="missing_credentials",
        )

    request_id = str(uuid.uuid4())

    # 按优先级尝试 resource_id
    for rid in TTS_RESOURCE_IDS:
        headers = {
            "X-Api-App-Key": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": rid,
            "X-Api-Request-Id": request_id,
            "Content-Type": "application/json",
        }

        body = {
            "user": {"uid": app_id},
            "req_params": {
                "text": text,
                "speaker": speaker,
                "audio_params": {
                    "format": audio_format,
                    "sample_rate": sample_rate,
                    "speech_rate": speed,
                },
            },
        }

        print(f"📡 尝试 {rid}...")
        print(f"   文本长度: {len(text)} 字符")
        print(f"   音色: {speaker} ({SPEAKERS.get(speaker, '自定义')})")
        print(f"   格式: {audio_format} / {sample_rate}Hz")
        print(f"   语速: {speed}")

        # 提交任务
        try:
            resp = req.post(TTS_SUBMIT_URL, json=body, headers=headers, timeout=120)
        except Exception as e:
            print(f"   ❌ 提交请求失败: {e}")
            continue

        status_code = resp.headers.get("X-Api-Status-Code", "")
        message = resp.headers.get("X-Api-Message", "")
        print(f"   提交响应: {status_code} ({message})")

        if status_code != "20000000":
            # 提交失败
            if status_code.startswith("45"):
                print(f"   ❌ 客户端错误: {message}")
                # 凭证或参数问题
                if "unauthorized" in message.lower() or "auth" in message.lower():
                    raise DoubaoTtsError(
                        f"认证失败: {message}。请检查 APP ID 和 Access Token 是否正确。",
                        diagnosis="auth_failed",
                    )
                continue
            else:
                print(f"   ❌ 提交失败: {status_code} - {message}")
                continue

        # 提交成功，获取 task_id 并轮询查询结果
        submit_data = resp.json()
        task_id = submit_data.get("data", {}).get("task_id", "")
        if not task_id:
            raise DoubaoTtsError(f"提交成功但未返回 task_id。响应: {json.dumps(submit_data, ensure_ascii=False)[:500]}")

        print(f"   ✅ 任务已提交 (task_id: {task_id})，等待合成完成...")
        query_headers = {
            "X-Api-App-Key": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": rid,
            "X-Api-Request-Id": request_id,
            "Content-Type": "application/json",
        }
        query_body = {"task_id": task_id}

        max_wait = 600   # 最长等待 10 分钟
        interval = 3     # 每 3 秒查询一次
        start_time = time.time()

        while time.time() - start_time < max_wait:
            time.sleep(interval)
            try:
                qresp = req.post(TTS_QUERY_URL, json=query_body, headers=query_headers, timeout=60)
            except Exception:
                continue

            q_status = qresp.headers.get("X-Api-Status-Code", "")
            q_message = qresp.headers.get("X-Api-Message", "")

            if q_status == "20000000":
                # 查询成功，检查 task_status 判断是否真正完成
                data = qresp.json()
                result_data = data.get("data", data)
                task_status = result_data.get("task_status", 0)

                # task_status: 1=排队中/处理中, 2=完成
                if task_status != 2:
                    elapsed = time.time() - start_time
                    print(f"   ⏳ 合成中 (task_status={task_status})... ({elapsed:.0f}s)")
                    continue

                # 合成完成，尝试获取音频数据
                # 方式 1: 音频下载 URL
                audio_url = result_data.get("audio_url", "")
                if audio_url:
                    print(f"   📥 下载音频: {audio_url[:80]}...")
                    try:
                        audio_resp = req.get(audio_url, timeout=120)
                        audio_resp.raise_for_status()
                        return audio_resp.content
                    except Exception as e:
                        raise DoubaoTtsError(f"音频下载失败: {e}")

                # 方式 2: base64 编码的音频数据
                import base64
                audio_b64 = result_data.get("audio_data", result_data.get("audio", ""))
                if audio_b64:
                    print("   📦 解码 base64 音频数据...")
                    return base64.b64decode(audio_b64)

                # 方式 3: 直接在 response body 中
                resp_body = qresp.content
                if resp_body and len(resp_body) > 100:
                    # 检查是否是 JSON
                    try:
                        body_json = qresp.json()
                        # 如果是 JSON 但没有音频字段
                        raise DoubaoTtsError(
                            f"API 返回成功但未找到音频数据。响应内容: {json.dumps(body_json, ensure_ascii=False)[:500]}"
                        )
                    except (json.JSONDecodeError, ValueError):
                        # 不是 JSON，可能是原始音频数据
                        return resp_body

                raise DoubaoTtsError(
                    f"API 返回成功但音频数据为空。响应: {qresp.text[:500]}"
                )

            elif q_status in ("20000001", "20000002"):
                # 正在处理中 / 在队列中
                elapsed = time.time() - start_time
                print(f"   ⏳ 合成中... ({elapsed:.0f}s)")
                continue

            else:
                raise DoubaoTtsError(
                    f"查询失败: {q_status} - {q_message}",
                    diagnosis=f"query_error_{q_status}",
                )

        raise DoubaoTtsError("轮询超时（等待超过 10 分钟）")

    raise DoubaoTtsError(
        "豆包 TTS API 不可用。请检查火山引擎账号的语音合成服务开通情况。\n"
        "开通服务后重新运行即可。",
        diagnosis="all_resources_failed",
    )


# ============================================================
# 音频处理
# ============================================================

def concat_audio_files(files: list[str], output_path: str) -> None:
    """使用 ffmpeg 拼接多个音频文件

    Args:
        files: 音频文件路径列表
        output_path: 输出文件路径
    """
    if len(files) == 1:
        # 单个文件直接重命名/复制
        os.rename(files[0], output_path)
        return

    # 创建 ffmpeg concat 文件列表
    list_content = "\n".join(f"file '{f}'" for f in files)
    list_file = output_path + ".list.txt"

    try:
        with open(list_file, "w", encoding="utf-8") as f:
            f.write(list_content)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 拼接失败: {result.stderr}")
    finally:
        if os.path.exists(list_file):
            os.unlink(list_file)
        # 清理临时文件
        for f in files:
            if os.path.exists(f):
                os.unlink(f)


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用"""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_audio_duration(file_path: str) -> float:
    """使用 ffprobe 获取音频时长（秒）"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


# ============================================================
# 文件输出
# ============================================================

SUPPORTED_INPUTS = {".srt", ".txt"}


def get_output_path(input_path: str, output_dir: Optional[str], fmt: str) -> str:
    """根据输入文件路径生成输出文件路径"""
    stem = Path(input_path).stem
    ext = f".{fmt}" if fmt != "ogg" else ".ogg"
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, f"{stem}{ext}")
    return str(Path(input_path).parent / f"{stem}{ext}")


# ============================================================
# 交互选择
# ============================================================

def has_interactive_tty() -> bool:
    """检查当前是否可进行交互输入"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def interactive_choose_speaker(cfg: dict) -> str:
    """交互式选择发音人"""
    tts_cfg = cfg.get("tts", {})
    last_speaker = tts_cfg.get("speaker", "BV001_streaming")

    print("\n" + "=" * 50)
    print("  🔊  选择发音人（音色）")
    print("=" * 50)

    options = list(SPEAKERS.keys())
    for i, (voice_type, desc) in enumerate(SPEAKERS.items(), 1):
        marker = " ← 上次使用" if voice_type == last_speaker else ""
        free_tag = " [免费]" if "免费" in desc else ""
        print(f"  {i}. {desc}{free_tag}{marker}")

    print()

    default_idx = options.index(last_speaker) + 1 if last_speaker in options else 1
    choice = input(f"  请选择 [1-{len(options)}]（默认 {default_idx}）: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return last_speaker


def interactive_choose_speed(cfg: dict) -> int:
    """交互式选择语速"""
    tts_cfg = cfg.get("tts", {})
    last_speed = tts_cfg.get("speed", 0)

    print("\n" + "=" * 50)
    print("  ⏩  选择语速")
    print("=" * 50)

    speed_options = [
        (-50, "0.5x 慢速"),
        (-25, "0.75x 略慢"),
        (0, "1.0x 正常（推荐）"),
        (25, "1.25x 略快"),
        (50, "1.5x 较快"),
        (100, "2.0x 快速"),
    ]

    for i, (val, desc) in enumerate(speed_options, 1):
        marker = " ← 上次使用" if val == last_speed else ""
        print(f"  {i}. {desc}{marker}")

    print()

    default_idx = 3  # 正常速度
    for idx, (val, _) in enumerate(speed_options, 1):
        if val == last_speed:
            default_idx = idx

    choice = input(f"  请选择 [1-6]（默认 {default_idx}）: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(speed_options):
        return speed_options[int(choice) - 1][0]
    return last_speed


def interactive_choose_format(cfg: dict) -> str:
    """交互式选择输出格式"""
    tts_cfg = cfg.get("tts", {})
    last_fmt = tts_cfg.get("format", "mp3")

    print("\n" + "=" * 50)
    print("  🎵  选择输出格式")
    print("=" * 50)

    formats = [
        ("mp3", "MP3（兼容性最好，推荐）"),
        ("wav", "WAV（无损，体积较大）"),
        ("ogg_opus", "OGG Opus（体积小，适合网络）"),
    ]

    for i, (fmt, desc) in enumerate(formats, 1):
        marker = " ← 上次使用" if fmt == last_fmt else ""
        print(f"  {i}. {desc}{marker}")

    print()

    fmt_keys = [f[0] for f in formats]
    default_idx = fmt_keys.index(last_fmt) + 1 if last_fmt in fmt_keys else 1
    choice = input(f"  请选择 [1-3]（默认 {default_idx}）: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(formats):
        return formats[int(choice) - 1][0]
    return last_fmt


def interactive_prepare_run(
    cfg: dict,
    input_path: str,
    speaker: Optional[str],
    speed: Optional[int],
    fmt: Optional[str],
    output_dir: Optional[str],
) -> tuple[str, int, str, Optional[str]]:
    """交互式确认本次执行参数"""
    print("\n" + "=" * 50)
    print("  🧭  执行前确认（先确认再合成）")
    print("=" * 50)
    print(f"📁 输入: {input_path}")

    selected_speaker = speaker or interactive_choose_speaker(cfg)
    selected_speed = speed if speed is not None else interactive_choose_speed(cfg)
    selected_fmt = fmt or interactive_choose_format(cfg)

    default_output_hint = output_dir or "与源文件同目录"
    output_input = input(f"\n📂 输出目录（默认 {default_output_hint}）: ").strip()
    selected_output = output_input if output_input else output_dir

    print("\n--- 本次参数 ---")
    print(f"  音色: {selected_speaker} ({SPEAKERS.get(selected_speaker, '自定义')})")
    print(f"  语速: {selected_speed}")
    print(f"  格式: {selected_fmt}")
    print(f"  输出目录: {selected_output or '与源文件同目录'}")

    confirm = input("\n✅ 确认开始合成？[Y/n]: ").strip().lower()
    if confirm in {"n", "no"}:
        print("⏹️ 已取消执行")
        sys.exit(0)

    return selected_speaker, selected_speed, selected_fmt, selected_output


# ============================================================
# 主流程
# ============================================================

def process_single(
    input_path: str,
    speaker: str = "BV001_streaming",
    speed: int = 0,
    fmt: str = "mp3",
    sample_rate: int = 24000,
    output_dir: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> str:
    """处理单个输入文件，返回输出文件路径"""

    if cfg is None:
        cfg = load_config()

    input_path = os.path.abspath(os.path.expanduser(input_path))

    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_INPUTS:
        print(f"❌ 不支持的格式: {ext}")
        print(f"   支持的格式: {', '.join(SUPPORTED_INPUTS)}")
        sys.exit(1)

    # 提取文本
    print("📖 解析文本...")
    text = extract_text(input_path)
    char_count = len(text)

    if not text.strip():
        print("❌ 文件内容为空")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"📁 输入: {input_path}")
    print(f"📝 格式: {ext.upper()}")
    print(f"📊 字符数: {char_count}")
    print(f"🔊 音色: {speaker} ({SPEAKERS.get(speaker, '自定义')})")
    print(f"⏩ 语速: {speed}")
    print(f"🎵 输出格式: {fmt}")
    print(f"{'='*50}\n")

    # 分段处理
    chunks = split_text(text)
    if len(chunks) > 1:
        print(f"📐 文本较长，分为 {len(chunks)} 段处理")
        for i, chunk in enumerate(chunks, 1):
            print(f"   段 {i}: {len(chunk)} 字符")
        print()

    # 输出路径
    output_path = get_output_path(input_path, output_dir, fmt)

    # 逐段合成
    temp_files = []
    try:
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                print(f"\n--- 段 {i}/{len(chunks)} ({len(chunk)} 字符) ---")

            audio_data = synthesize_doubao_async(
                text=chunk,
                speaker=speaker,
                audio_format=fmt if fmt != "ogg" else "ogg_opus",
                sample_rate=sample_rate,
                speed=speed,
                cfg=cfg,
            )

            # 保存临时文件
            if len(chunks) > 1:
                temp_path = output_path + f".part{i}.tmp"
                with open(temp_path, "wb") as f:
                    f.write(audio_data)
                temp_files.append(temp_path)
                print(f"   ✅ 段 {i} 完成: {len(audio_data)} bytes")
            else:
                with open(output_path, "wb") as f:
                    f.write(audio_data)

        # 拼接多段音频
        if temp_files:
            print(f"\n🔗 拼接 {len(temp_files)} 段音频...")
            if not check_ffmpeg():
                print("⚠️  ffmpeg 未安装，无法拼接多段音频")
                print("   将保留分段文件")
                for tf in temp_files:
                    final_name = tf.replace(".tmp", "")
                    os.rename(tf, final_name)
                    print(f"   段文件: {final_name}")
                return temp_files[0].replace(".tmp", "")

            concat_audio_files(temp_files, output_path)

        # 验证输出
        if not os.path.exists(output_path):
            print(f"❌ 输出文件未生成: {output_path}")
            sys.exit(1)

        file_size = os.path.getsize(output_path)
        duration = get_audio_duration(output_path)

        # 输出统计
        print(f"\n{'='*50}")
        print(f"✅ 输出: {output_path}")
        print(f"📊 字符数: {char_count} | 段数: {len(chunks)}")
        print(f"📄 大小: {file_size / 1024:.1f} KB")
        if duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"⏱️  时长: {minutes}:{seconds:02d}")
        print(f"{'='*50}\n")

        # 保存本次参数
        cfg["tts"] = {
            "speaker": speaker,
            "speed": speed,
            "format": fmt,
            "sample_rate": sample_rate,
        }
        save_config(cfg)

        return output_path

    except DoubaoTtsError:
        # 清理临时文件
        for tf in temp_files:
            if os.path.exists(tf):
                os.unlink(tf)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="字幕/文字转语音工具 - 豆包大模型 TTS API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s subtitle.srt                    # 交互模式（推荐）
  %(prog)s text.txt -s BV002_streaming     # 指定男声音色
  %(prog)s subtitle.srt -f wav             # 输出 WAV 格式
  %(prog)s subtitle.srt -r 25              # 1.25x 语速
  %(prog)s subtitle.srt --yolo             # YOLO 模式（跳过交互）
  %(prog)s --show-config                   # 查看当前配置
  %(prog)s --setup-doubao                  # 配置豆包 API 凭证
        """,
    )
    parser.add_argument("input", nargs="?", help="SRT/TXT 文件路径")
    parser.add_argument("-f", "--format", default=None,
                        choices=["mp3", "wav", "ogg"],
                        help="输出音频格式（默认: mp3）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出目录（默认: 与输入文件同目录）")
    parser.add_argument("-s", "--speaker", default=None,
                        help=f"发音人音色（默认: BV001_streaming）")
    parser.add_argument("-r", "--speed", type=int, default=None,
                        help="语速 [-50, 100]（默认: 0 = 正常）")
    parser.add_argument("--sample-rate", type=int, default=None,
                        help="采样率（默认: 24000）")
    parser.add_argument("--yolo", action="store_true",
                        help="YOLO 模式：跳过交互，使用默认参数")
    parser.add_argument("--show-config", action="store_true",
                        help="查看当前配置")
    parser.add_argument("--setup-doubao", action="store_true",
                        help="配置豆包 API 凭证")

    args = parser.parse_args()

    # 加载配置
    cfg = load_config()

    # 查看配置
    if args.show_config:
        print(f"配置文件: {CONFIG_FILE}")
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
        return

    # 配置豆包 API
    if args.setup_doubao:
        print("\n🔧 配置豆包 TTS API 凭证\n")
        print_doubao_tts_guide()

        app_id = input("  APP ID: ").strip()
        access_token = input("  Access Token: ").strip()

        if app_id and access_token:
            cfg["doubao"] = {"app_id": app_id, "access_token": access_token}
            save_config(cfg)
            print("\n✅ 豆包 API 凭证配置完成！")
        else:
            print("\n❌ 凭证不能为空")
        return

    # 必须提供输入文件
    if not args.input:
        parser.print_help()
        return

    # 前置检查
    if not check_ffmpeg():
        print("⚠️  ffmpeg 未安装，长文本拼接功能将不可用")
        print("   建议安装: brew install ffmpeg")

    # 合并参数：命令行 > 配置文件 > 默认值
    tts_cfg = cfg.get("tts", {})
    fmt = args.format or tts_cfg.get("format", "mp3")
    speaker = args.speaker or tts_cfg.get("speaker", "BV001_streaming")
    speed = args.speed if args.speed is not None else tts_cfg.get("speed", 0)
    sample_rate = args.sample_rate or tts_cfg.get("sample_rate", 24000)

    if args.yolo:
        print("🚀 YOLO 模式：跳过交互，使用默认参数")
    else:
        if has_interactive_tty():
            speaker, speed, fmt, args.output = interactive_prepare_run(
                cfg=cfg,
                input_path=args.input,
                speaker=args.speaker,
                speed=args.speed,
                fmt=fmt,
                output_dir=args.output,
            )
        else:
            print("❌ 检测到非交互终端，无法进行交互确认。")
            print("   默认流程要求交互确认参数后再执行。")
            print("   如需跳过交互，请显式添加 --yolo。")
            sys.exit(2)

    # 执行合成
    process_single(
        input_path=args.input,
        speaker=speaker,
        speed=speed,
        fmt=fmt,
        sample_rate=sample_rate,
        output_dir=args.output,
        cfg=cfg,
    )


if __name__ == "__main__":
    main()
