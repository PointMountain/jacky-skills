#!/usr/bin/env python3
"""
音频转字幕工具 - 本地 MLX-Whisper + 豆包云端 API

用法:
    # 交互模式（推荐，会引导选择引擎和参数）
    python3 transcribe.py audio.mp3

    # 指定引擎
    python3 transcribe.py audio.mp3 --engine local
    python3 transcribe.py audio.mp3 --engine doubao

    # 指定输出格式
    python3 transcribe.py audio.mp3 -f vtt

    # 批量转录
    python3 transcribe.py ~/Downloads/audio/ --batch
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Optional


# ============================================================
# 配置文件管理
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
        "resource_id": "",  # 上次探测成功的 resource_id
    },
}

# 豆包 ASR resource_id 列表（按优先级排列）
DOUBAO_RESOURCE_IDS = [
    "volc.bigasr.auc_turbo",       # 大模型录音文件极速版（4.5 元/小时）
    "volc.bigasr.auc",              # 录音文件识别
    "volc.bigasr.sauc.duration",    # 按时长计费
    "volc.bigasr.sauc.offline",     # 闲时版
]

# 豆包 ASR 标准版 resource_id（submit + query 轮询模式）
DOUBAO_STANDARD_RESOURCE_IDS = [
    "volc.seedasr.auc",      # 豆包录音文件识别模型2.0（已验证可用）
]


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并默认配置
            cfg = {**DEFAULT_CONFIG, **saved}
            if "doubao" not in cfg:
                cfg["doubao"] = DEFAULT_CONFIG["doubao"]
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
# 数据结构
# ============================================================

@dataclass
class Segment:
    """字幕段落"""
    start: float  # 秒
    end: float    # 秒
    text: str

@dataclass
class TranscriptionResult:
    """转录结果"""
    segments: list[Segment] = field(default_factory=list)
    language: str = ""
    duration: float = 0.0
    text: str = ""


# ============================================================
# 音频预处理
# ============================================================

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


def preprocess_audio(input_path: str, output_path: str) -> None:
    """使用 ffmpeg 将音频/视频转为 WAV 16kHz 单声道"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 预处理失败: {result.stderr}")


# ============================================================
# 本地转录引擎（MLX-Whisper）
# ============================================================

MLX_MODELS = {
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "tiny": "mlx-community/whisper-tiny-mlx",
}


def transcribe_local(
    audio_path: str,
    model_name: str = "large-v3-turbo",
    language: Optional[str] = None,
    quantize: bool = True,
) -> TranscriptionResult:
    """使用 MLX-Whisper 本地转录"""
    try:
        import mlx_whisper
    except ImportError:
        print("❌ mlx-whisper 未安装，请运行: pip install mlx-whisper")
        sys.exit(1)

    # 清理 SOCKS5 代理（httpx 不支持 socks5h:// scheme）
    for var in ["ALL_PROXY", "all_proxy"]:
        val = os.environ.pop(var, None)
        if val and "socks" in (val or "").lower():
            print(f"⚠️  已清除冲突代理 {var}={val}")

    model_repo = MLX_MODELS.get(model_name)
    if not model_repo:
        print(f"❌ 未知模型: {model_name}")
        print(f"   可选模型: {', '.join(MLX_MODELS.keys())}")
        sys.exit(1)

    print(f"🔊 模型: {model_name} ({model_repo})")
    print(f"📊 量化: {'4-bit' if quantize else '无'}")
    print(f"🌐 语言: {language or '自动检测'}")
    print("⏳ 开始转录...")

    transcribe_kwargs = {
        "path_or_hf_repo": model_repo,
        "verbose": True,
    }
    if language:
        transcribe_kwargs["language"] = language

    result = mlx_whisper.transcribe(audio_path, **transcribe_kwargs)

    segments = []
    for seg in result.get("segments", []):
        segments.append(Segment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip(),
        ))

    full_text = result.get("text", "").strip()
    detected_lang = result.get("language", language or "unknown")

    print(f"✅ 转录完成: {len(segments)} 个段落, 检测语言: {detected_lang}")

    return TranscriptionResult(
        segments=segments,
        language=detected_lang,
        duration=segments[-1].end if segments else 0,
        text=full_text,
    )


# ============================================================
# 豆包 ASR API（火山引擎大模型录音文件极速版）
# ============================================================

def check_doubao_config(cfg: dict) -> tuple[str, str]:
    """检查豆包 API 配置，返回 (app_id, access_token)"""
    doubao = cfg.get("doubao", {})
    app_id = doubao.get("app_id", "") or os.environ.get("DOUBAO_APP_ID", "")
    access_token = doubao.get("access_token", "") or os.environ.get("DOUBAO_ACCESS_TOKEN", "")

    if not app_id or not access_token:
        return "", ""

    return app_id, access_token


def print_doubao_guide() -> None:
    """打印豆包 API 注册和申请指南"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              豆包语音识别 API - 注册指南                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. 注册账号                                                  ║
║     访问 https://www.volcengine.com                          ║
║     使用手机号注册并完成实名认证                                ║
║                                                              ║
║  2. 开通语音识别服务                                           ║
║     访问 https://console.volcengine.com/speech                ║
║     点击「开通服务」（有免费额度）                               ║
║                                                              ║
║  3. 创建应用并获取凭证                                         ║
║     在控制台点击「创建应用」                                    ║
║     填写应用名称，勾选「语音识别」                               ║
║     创建后在「应用管理」页面获取:                                ║
║       - APP ID (即 X-Api-App-Key)                            ║
║       - Access Token (即 X-Api-Access-Key)                   ║
║                                                              ║
║  4. 配置凭证                                                  ║
║     方式一: 运行本脚本时输入（交互式）                            ║
║     方式二: 写入配置文件 ~/.audio2subtitle/config.json          ║
║     方式三: 设置环境变量                                        ║
║       export DOUBAO_APP_ID=你的APP_ID                         ║
║       export DOUBAO_ACCESS_TOKEN=你的Access_Token             ║
║                                                              ║
║  💰 价格参考                                                   ║
║     大模型录音文件极速版: 4.5 元/小时（后付费）                   ║
║     豆包录音文件识别 2.0:    0.8 元/小时（后付费）               ║
║     新用户有免费额度，详见控制台                                  ║
║                                                              ║
║  📖 文档                                                      ║
║     https://www.volcengine.com/docs/6561/1631584              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


class DoubaoApiError(Exception):
    """豆包 API 错误，包含诊断信息，不应自动回退"""

    def __init__(self, message: str, diagnosis: list[tuple[str, str, str]] | None = None):
        super().__init__(message)
        self.diagnosis = diagnosis or []


def _build_diagnosis_report(results: list[tuple[str, str, str]]) -> str:
    """构建豆包 ASR API 诊断报告（返回字符串，供调用方展示）"""
    lines = []
    lines.append("")
    lines.append("══════════════════════════════════════════")
    lines.append("豆包 ASR API 诊断报告")
    lines.append("")
    lines.append("已尝试的 resource_id：")
    for i, (rid, code, msg) in enumerate(results, 1):
        lines.append(f"  {i}. {rid} → {code} ({msg})")
    lines.append("")
    lines.append("可能原因：")
    lines.append("  - 语音识别服务未开通")
    lines.append("  - 应用未关联对应服务")
    lines.append("")
    lines.append("请访问以下地址检查并开通对应服务：")
    lines.append("  - 应用管理: https://console.volcengine.com/speech/app")
    lines.append("  - 服务管理: https://console.volcengine.com/speech/service")
    lines.append("  - 订阅页面: https://console.volcengine.com/speech/service/subscription")
    lines.append("")
    lines.append("提示：开通服务后重新运行即可，或可选择回退到本地引擎")
    lines.append("══════════════════════════════════════════")
    return "\n".join(lines)


def _try_doubao_standard(
    app_id: str,
    access_token: str,
    audio_data: str,
    audio_format: str,
    language: str | None,
    cfg: dict,
) -> TranscriptionResult | None:
    """
    使用豆包标准版 API（submit + query 轮询，base64 直传）

    API 文档: https://www.volcengine.com/docs/6561/1354868
    - 提交任务（base64 直传） → 轮询查询结果
    - 支持最长 2 小时音频
    """
    import requests as req

    submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
    query_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"

    # 按优先级尝试标准版 resource_id
    for rid in DOUBAO_STANDARD_RESOURCE_IDS:
        request_id = str(uuid.uuid4())
        headers = {
            "X-Api-App-Key": app_id,
            "X-Api-Access-Key": access_token,
            "X-Api-Resource-Id": rid,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
        }

        body = {
            "user": {"uid": app_id},
            "audio": {
                "data": audio_data,
                "format": audio_format,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
            },
        }

        print(f"📡 尝试标准版 {rid}（base64 直传）...")

        # 提交任务
        try:
            resp = req.post(submit_url, json=body, headers=headers, timeout=120)
        except Exception as e:
            print(f"   ❌ 提交请求失败: {e}")
            continue

        status_code = resp.headers.get("X-Api-Status-Code", "")
        message = resp.headers.get("X-Api-Message", "")
        print(f"   提交响应: {status_code} ({message})")

        if status_code == "20000000":
            # 提交成功，轮询查询结果
            print("   ✅ 任务已提交，等待转录完成...")
            query_headers = {
                "X-Api-App-Key": app_id,
                "X-Api-Access-Key": access_token,
                "X-Api-Resource-Id": rid,
                "X-Api-Request-Id": request_id,
            }

            max_wait = 600  # 最长等待 10 分钟
            interval = 5    # 每 5 秒查询一次
            start_time = time.time()

            while time.time() - start_time < max_wait:
                time.sleep(interval)
                try:
                    qresp = req.post(query_url, json={}, headers=query_headers, timeout=60)
                except Exception:
                    continue

                q_status = qresp.headers.get("X-Api-Status-Code", "")
                q_message = qresp.headers.get("X-Api-Message", "")

                if q_status == "20000000":
                    # 转录完成
                    data = qresp.json()
                    result_data = data.get("result", {})
                    utterances = result_data.get("utterances", [])
                    full_text = result_data.get("text", "").strip()
                    duration_ms = data.get("audio_info", {}).get("duration", 0)

                    segments = []
                    for utt in utterances:
                        segments.append(Segment(
                            start=utt.get("start_time", 0) / 1000.0,
                            end=utt.get("end_time", 0) / 1000.0,
                            text=utt.get("text", "").strip(),
                        ))

                    detected_lang = language or "zh"
                    print(f"✅ 转录完成: {len(segments)} 个段落, 时长: {duration_ms/1000:.1f}s")

                    # 保存成功的 resource_id
                    if cfg.get("doubao", {}).get("resource_id") != rid:
                        cfg["doubao"]["resource_id"] = rid
                        save_config(cfg)
                        print(f"💾 已保存 resource_id: {rid}")

                    return TranscriptionResult(
                        segments=segments,
                        language=detected_lang,
                        duration=duration_ms / 1000.0,
                        text=full_text,
                    )

                elif q_status in ("20000001", "20000002"):
                    # 正在处理中 / 在队列中
                    elapsed = time.time() - start_time
                    print(f"   ⏳ 处理中... ({elapsed:.0f}s)")
                    continue

                elif q_status == "20000003":
                    # 静音音频
                    print("   ⚠️ 检测到静音音频")
                    return None

                else:
                    print(f"   ❌ 查询失败: {q_status} - {q_message}")
                    break

            print("   ❌ 轮询超时（等待超过 10 分钟）")
            return None

        elif status_code.startswith("45"):
            print(f"   ❌ 不支持: {message}")
            continue

        else:
            print(f"   ❌ 提交失败: {status_code} - {message}")
            continue

    return None


def transcribe_doubao(
    audio_path: str,
    cfg: dict,
    language: Optional[str] = None,
) -> TranscriptionResult:
    """
    使用豆包 ASR API 转录（大模型录音文件极速版）

    API 文档: https://www.volcengine.com/docs/6561/1631584
    - 一次 HTTP POST 直接返回结果，无需轮询
    - 支持最长 2 小时、100MB 的音频
    - 返回带时间戳的 utterances，适合生成字幕
    """
    app_id, access_token = check_doubao_config(cfg)

    # 如果没有配置，抛出错误让调用方处理（不自动回退）
    if not app_id or not access_token:
        print("⚠️  豆包 API 凭证未配置\n")
        print_doubao_guide()
        raise DoubaoApiError(
            "豆包 API 凭证未配置。请按上述指南获取 APP ID 和 Access Token，"
            "然后通过以下方式配置：\n"
            "  1. 运行 python3 scripts/transcribe.py --setup-doubao\n"
            "  2. 或写入 ~/.audio2subtitle/config.json\n"
            "  3. 或设置环境变量 DOUBAO_APP_ID + DOUBAO_ACCESS_TOKEN"
        )

    try:
        import requests
    except ImportError:
        print("❌ requests 未安装，请运行: pip install requests")
        sys.exit(1)

    print("🔊 引擎: 豆包 ASR（大模型录音文件极速版）")

    # 文件大小检查（极速版限制 100MB）
    file_size = os.path.getsize(audio_path)
    file_size_mb = file_size / 1024 / 1024
    print(f"📦 文件大小: {file_size_mb:.1f}MB")

    if file_size_mb > 100:
        print("❌ 文件超过 100MB 限制，请使用本地引擎或切分后重试")
        sys.exit(1)

    # 转换音频为 MP3 格式（豆包支持 WAV/MP3/OGG OPUS）
    file_ext = Path(audio_path).suffix.lstrip(".").lower()
    supported_exts = {"wav", "mp3", "ogg", "opus"}

    if file_ext not in supported_exts:
        print("🔄 转换音频为 MP3 格式（豆包 API 要求）...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_mp3 = tmp.name
        cmd = ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", tmp_mp3]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 转换失败: {result.stderr}")
        upload_path = tmp_mp3
        file_ext = "mp3"
    else:
        tmp_mp3 = None
        upload_path = audio_path

    try:
        # Base64 编码音频（只需做一次）
        with open(upload_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")

        # 构建 resource_id 尝试列表：上次成功的优先
        saved_resource_id = cfg.get("doubao", {}).get("resource_id", "")
        if saved_resource_id and saved_resource_id in DOUBAO_RESOURCE_IDS:
            resource_ids = [saved_resource_id] + [
                rid for rid in DOUBAO_RESOURCE_IDS if rid != saved_resource_id
            ]
        else:
            resource_ids = list(DOUBAO_RESOURCE_IDS)

        url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"

        # 多 resource_id 自动探测
        print(f"⏳ 上传音频并转录（探测可用 resource_id）...")
        diagnosis_results = []  # [(resource_id, status_code, message)]
        last_resp = None

        for rid in resource_ids:
            headers = {
                "X-Api-App-Key": app_id,
                "X-Api-Access-Key": access_token,
                "X-Api-Resource-Id": rid,
                "X-Api-Request-Id": str(uuid.uuid4()),
                "X-Api-Sequence": "-1",
            }

            body = {
                "user": {"uid": app_id},
                "audio": {"data": audio_data},
                "request": {
                    "model_name": "bigmodel",
                    "enable_itn": True,
                    "enable_punc": True,
                    "enable_ddc": True,
                    "enable_speaker_info": False,
                },
            }

            start_time = time.time()
            resp = requests.post(url, json=body, headers=headers, timeout=300)
            elapsed = time.time() - start_time

            status_code = resp.headers.get("X-Api-Status-Code", "")
            message = resp.headers.get("X-Api-Message", "")

            print(f"📡 尝试 {rid} → {status_code} ({elapsed:.1f}s)")

            # 认证失败（凭证无效），所有 resource_id 都会失败，直接退出探测
            if status_code in ("45000001", "55000031"):
                diagnosis_results.append((rid, status_code, message))
                print(f"❌ 认证失败: {message}")
                print("   请检查 APP ID 和 Access Token 是否正确")
                # 清除无效配置
                cfg["doubao"] = {"app_id": "", "access_token": ""}
                save_config(cfg)
                report = _build_diagnosis_report(diagnosis_results)
                print(report)
                raise DoubaoApiError(
                    f"豆包 API 认证失败（{status_code}: {message}）。"
                    "请检查 APP ID 和 Access Token 是否正确。\n"
                    "可通过 python3 scripts/transcribe.py --setup-doubao 重新配置。",
                    diagnosis=diagnosis_results,
                )

            # 成功
            if status_code == "20000000":
                print(f"✅ resource_id 探测成功: {rid}")
                # 保存成功的 resource_id 到配置
                if cfg.get("doubao", {}).get("resource_id") != rid:
                    cfg["doubao"]["resource_id"] = rid
                    save_config(cfg)
                    print(f"💾 已保存 resource_id: {rid}")
                last_resp = resp
                break

            # 其他错误（not granted / not allowed 等），继续尝试
            diagnosis_results.append((rid, status_code, message))
        else:
            # 极速版所有 resource_id 都失败，尝试标准版 API（submit + query）
            report = _build_diagnosis_report(diagnosis_results)
            print(report)
            print("")
            print("🔄 极速版 API 不可用，尝试标准版 API（submit + query 轮询模式）...")
            standard_result = _try_doubao_standard(
                app_id, access_token, audio_data, file_ext, language, cfg
            )
            if standard_result:
                return standard_result

            # 标准版也失败，抛出错误
            raise DoubaoApiError(
                "豆包 API 极速版和标准版均不可用。"
                "请检查火山引擎账号的语音识别服务开通情况。\n"
                "开通服务后重新运行即可，或可手动选择回退到本地引擎。",
                diagnosis=diagnosis_results,
            )

        data = last_resp.json()

        # 解析结果
        result_data = data.get("result", {})
        utterances = result_data.get("utterances", [])
        full_text = result_data.get("text", "").strip()
        duration_ms = data.get("audio_info", {}).get("duration", 0)

        segments = []
        for utt in utterances:
            segments.append(Segment(
                start=utt.get("start_time", 0) / 1000.0,
                end=utt.get("end_time", 0) / 1000.0,
                text=utt.get("text", "").strip(),
            ))

        detected_lang = language or "zh"

        print(f"✅ 转录完成: {len(segments)} 个段落, 时长: {duration_ms/1000:.1f}s")

        return TranscriptionResult(
            segments=segments,
            language=detected_lang,
            duration=duration_ms / 1000.0,
            text=full_text,
        )

    finally:
        if tmp_mp3 and os.path.exists(tmp_mp3):
            os.unlink(tmp_mp3)


# ============================================================
# 字幕格式化
# ============================================================

def format_srt_time(seconds: float) -> str:
    """格式化为 SRT 时间戳: 00:00:00,000"""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_time(seconds: float) -> str:
    """格式化为 VTT 时间戳: 00:00:00.000"""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_md_time(seconds: float) -> str:
    """格式化为可读时间: 1:23"""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def to_srt(result: TranscriptionResult) -> str:
    """生成 SRT 格式字幕"""
    lines = []
    for i, seg in enumerate(result.segments, 1):
        if not seg.text:
            continue
        lines.append(str(i))
        lines.append(f"{format_srt_time(seg.start)} --> {format_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def to_vtt(result: TranscriptionResult) -> str:
    """生成 VTT 格式字幕"""
    lines = ["WEBVTT", ""]
    for seg in result.segments:
        if not seg.text:
            continue
        lines.append(f"{format_vtt_time(seg.start)} --> {format_vtt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def to_txt(result: TranscriptionResult) -> str:
    """生成纯文本"""
    return result.text


def to_md(result: TranscriptionResult) -> str:
    """生成 Markdown（带时间轴）"""
    lines = [
        "# 音频转录",
        "",
        f"> 时长: {int(result.duration // 60)}分{int(result.duration % 60)}秒",
        f"> 语言: {result.language}",
        f"> 段落: {len(result.segments)}",
        "",
        "## 文案内容",
        "",
        result.text,
        "",
        "## 时间轴",
        "",
    ]
    for seg in result.segments:
        timestamp = format_md_time(seg.start)
        lines.append(f"- **{timestamp}** {seg.text}")
    return "\n".join(lines)


FORMATTERS = {
    "srt": to_srt,
    "vtt": to_vtt,
    "txt": to_txt,
    "md": to_md,
}


# ============================================================
# 文件输出
# ============================================================

SUPPORTED_INPUTS = {
    # 音频格式
    ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".opus",
    # 视频格式（ffmpeg 自动提取音频）
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".ts", ".flv",
}


def get_output_path(input_path: str, output_dir: Optional[str], fmt: str) -> str:
    """根据输入文件路径生成输出文件路径"""
    stem = Path(input_path).stem
    ext = f".{fmt}" if fmt != "md" else ".md"
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, f"{stem}{ext}")
    return str(Path(input_path).parent / f"{stem}{ext}")


def find_audio_files(directory: str) -> list[str]:
    """扫描目录中的所有音频文件"""
    files = []
    for f in sorted(Path(directory).iterdir()):
        if f.suffix.lower() in SUPPORTED_INPUTS:
            files.append(str(f))
    return files


# ============================================================
# 引擎交互选择
# ============================================================

def interactive_choose_engine(cfg: dict) -> str:
    """交互式选择转录引擎"""
    print("\n" + "=" * 50)
    print("  🎙️  音频转字幕 - 选择转录引擎")
    print("=" * 50)

    engines = [
        ("local", "本地 MLX-Whisper（免费、隐私、快速）"),
        ("doubao", "豆包 ASR API（云端、中文优化、需 API Key）"),
    ]

    for i, (key, desc) in enumerate(engines, 1):
        marker = " ← 上次使用" if key == cfg.get("engine") else ""
        print(f"  {i}. {desc}{marker}")

    print()

    default_choice = "1"
    if cfg.get("engine") == "doubao" and check_doubao_config(cfg) != ("", ""):
        default_choice = "2"

    choice = input(f"  请选择 [1-2]（默认 {default_choice}）: ").strip()

    if choice == "2":
        return "doubao"
    return "local"


def has_interactive_tty() -> bool:
    """检查当前是否可进行交互输入"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def interactive_choose_format(default_fmt: str) -> str:
    """交互式选择输出格式"""
    options = ["srt", "vtt", "txt", "md"]
    print("\n📝 选择输出格式:")
    for i, fmt in enumerate(options, 1):
        marker = " ← 默认" if fmt == default_fmt else ""
        print(f"  {i}. {fmt.upper()}{marker}")
    choice = input(f"  请选择 [1-4]（默认 {options.index(default_fmt) + 1}）: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return default_fmt


def interactive_choose_model(default_model: str) -> str:
    """交互式选择本地模型"""
    options = list(MLX_MODELS.keys())
    print("\n🔊 选择本地模型:")
    for i, model in enumerate(options, 1):
        marker = " ← 默认" if model == default_model else ""
        print(f"  {i}. {model}{marker}")
    choice = input(f"  请选择 [1-{len(options)}]（默认 {options.index(default_model) + 1}）: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return default_model


def interactive_prepare_run(
    cfg: dict,
    input_target: str,
    fmt: str,
    model: str,
    engine: Optional[str],
    output_dir: Optional[str],
    language: Optional[str],
) -> tuple[str, str, str, Optional[str], Optional[str]]:
    """交互式确认本次执行参数"""
    print("\n" + "=" * 50)
    print("  🧭 执行前确认（先确认再转录）")
    print("=" * 50)
    print(f"📁 输入: {input_target}")

    selected_engine = engine or interactive_choose_engine(cfg)
    selected_fmt = interactive_choose_format(fmt)
    selected_model = model
    if selected_engine == "local":
        selected_model = interactive_choose_model(model)

    default_output_hint = output_dir or "与源文件同目录"
    output_input = input(f"\n📂 输出目录（默认 {default_output_hint}）: ").strip()
    selected_output = output_input if output_input else output_dir

    default_lang_hint = language or "auto"
    lang_input = input(f"🌐 语言（默认 {default_lang_hint}，输入 auto 表示自动检测）: ").strip()
    selected_language: Optional[str]
    if not lang_input:
        selected_language = language
    elif lang_input.lower() == "auto":
        selected_language = None
    else:
        selected_language = lang_input

    print("\n--- 本次参数 ---")
    print(f"  引擎: {selected_engine}")
    print(f"  格式: {selected_fmt}")
    if selected_engine == "local":
        print(f"  模型: {selected_model}")
    print(f"  输出目录: {selected_output or '与源文件同目录'}")
    print(f"  语言: {selected_language or 'auto'}")

    confirm = input("\n✅ 确认开始转录？[Y/n]: ").strip().lower()
    if confirm in {"n", "no"}:
        print("⏹️ 已取消执行")
        sys.exit(0)

    return selected_fmt, selected_model, selected_engine, selected_output, selected_language


# ============================================================
# 主流程
# ============================================================

def process_single(
    input_path: str,
    fmt: str = "srt",
    model: str = "large-v3-turbo",
    engine: str = "local",
    language: Optional[str] = None,
    output_dir: Optional[str] = None,
    quantize: bool = True,
    cfg: Optional[dict] = None,
) -> str:
    """处理单个音频文件，返回输出文件路径"""

    if cfg is None:
        cfg = load_config()

    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_INPUTS:
        print(f"❌ 不支持的格式: {ext}")
        print(f"   支持的格式: {', '.join(SUPPORTED_INPUTS)}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"📁 输入: {input_path}")
    print(f"📝 格式: {fmt.upper()}")
    print(f"⚙️  引擎: {'本地 MLX-Whisper' if engine == 'local' else '豆包 ASR API'}")
    print(f"{'='*50}\n")

    # 预处理：本地引擎需要 WAV 16kHz
    if engine == "local":
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name

    try:
        if engine == "local":
            print("🔄 预处理音频（ffmpeg 转 WAV 16kHz）...")
            preprocess_audio(input_path, tmp_wav)
            result = transcribe_local(tmp_wav, model, language, quantize)
        elif engine == "doubao":
            result = transcribe_doubao(input_path, cfg, language)
        else:
            print(f"❌ 未知引擎: {engine}")
            print("   可选引擎: local, doubao")
            sys.exit(1)

        # 格式化输出
        formatter = FORMATTERS.get(fmt)
        if not formatter:
            print(f"❌ 未知格式: {fmt}")
            print(f"   可选格式: {', '.join(FORMATTERS.keys())}")
            sys.exit(1)

        content = formatter(result)
        output_path = get_output_path(input_path, output_dir, fmt)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 输出统计
        print(f"\n{'='*50}")
        print(f"✅ 输出: {output_path}")
        print(f"📊 段落: {len(result.segments)} | 时长: {result.duration:.1f}s | 语言: {result.language}")
        print(f"📄 大小: {os.path.getsize(output_path)} bytes")

        # 预览前 3 段
        if result.segments:
            print(f"\n--- 预览 ---")
            for seg in result.segments[:3]:
                print(f"  [{format_md_time(seg.start)}] {seg.text}")
            if len(result.segments) > 3:
                print(f"  ... 共 {len(result.segments)} 段")
        print(f"{'='*50}\n")

        # 记住这次使用的引擎
        cfg["engine"] = engine
        save_config(cfg)

        return output_path

    finally:
        if engine == "local" and os.path.exists(tmp_wav):
            os.unlink(tmp_wav)


def main():
    parser = argparse.ArgumentParser(
        description="音频转字幕工具 - 本地 MLX-Whisper + 豆包云端 API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s audio.mp3                        # 交互模式（推荐，先确认再执行）
  %(prog)s audio.mp3 --engine local         # 本地 MLX-Whisper
  %(prog)s audio.mp3 --engine doubao        # 豆包 ASR API
  %(prog)s audio.mp3 --yolo                 # YOLO 模式（跳过交互，默认 local）
  %(prog)s audio.mp3 -f vtt                 # 输出 VTT 格式
  %(prog)s ~/audio/ --batch                 # 批量处理
  %(prog)s --show-config                    # 查看当前配置
  %(prog)s --setup-doubao                   # 配置豆包 API 凭证
        """,
    )
    parser.add_argument("input", nargs="?", help="音频/视频文件路径或目录（批量模式）")
    parser.add_argument("-f", "--format", default=None,
                        choices=["srt", "vtt", "txt", "md"],
                        help="输出格式（默认: srt）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出目录（默认: 与音频同目录）")
    parser.add_argument("-m", "--model", default=None,
                        choices=list(MLX_MODELS.keys()),
                        help="Whisper 模型（默认: large-v3-turbo）")
    parser.add_argument("-e", "--engine", default=None,
                        choices=["local", "doubao"],
                        help="转录引擎（不指定则交互确认；YOLO 模式默认 local）")
    parser.add_argument("-l", "--language", default=None,
                        help="音频语言（默认: 自动检测）")
    parser.add_argument("--batch", action="store_true",
                        help="批量处理模式（输入为目录）")
    parser.add_argument("-q", "--quantize", default="4bit",
                        choices=["4bit", "8bit", "none"],
                        help="量化精度（默认: 4bit）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细输出")
    parser.add_argument("--yolo", action="store_true",
                        help="YOLO 模式：跳过交互，默认使用本地引擎")
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
        print("\n🔧 配置豆包 ASR API 凭证\n")
        print_doubao_guide()

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
        print("❌ ffmpeg 未安装，请运行: brew install ffmpeg")
        sys.exit(1)

    # 合并参数：命令行 > 配置文件 > 默认值
    fmt = args.format or cfg.get("format", "srt")
    model = args.model or cfg.get("model", "large-v3-turbo")
    language = args.language or cfg.get("language")
    quantize = args.quantize != "none"
    engine = args.engine

    if args.yolo:
        # YOLO 模式不交互，默认走本地引擎
        engine = args.engine or "local"
        print("🚀 YOLO 模式：跳过交互，默认使用本地引擎")
    else:
        if has_interactive_tty():
            fmt, model, engine, args.output, language = interactive_prepare_run(
                cfg=cfg,
                input_target=args.input,
                fmt=fmt,
                model=model,
                engine=engine,
                output_dir=args.output,
                language=language,
            )
        else:
            # 严格模式：未显式 YOLO 时必须交互确认，防止误跳过
            print("❌ 检测到非交互终端，无法进行交互确认。")
            print("   默认流程要求交互确认参数后再执行。")
            print("   如需跳过交互，请显式添加 --yolo。")
            print("   或在可交互终端（TTY）中直接运行本命令。")
            sys.exit(2)

    # 处理模式
    if args.batch:
        if not os.path.isdir(args.input):
            print(f"❌ 批量模式需要指定目录: {args.input}")
            sys.exit(1)

        files = find_audio_files(args.input)
        if not files:
            print(f"❌ 目录中没有找到音频文件: {args.input}")
            sys.exit(1)

        print(f"📂 找到 {len(files)} 个音频文件")
        results = []
        for i, f in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] 处理: {os.path.basename(f)}")
            try:
                output = process_single(
                    f, fmt, model, engine,
                    language, args.output, quantize, cfg,
                )
                results.append(output)
            except Exception as e:
                print(f"❌ 失败: {e}")
                continue

        print(f"\n🎉 批量处理完成: {len(results)}/{len(files)} 成功")

    else:
        process_single(
            args.input, fmt, model, engine,
            language, args.output, quantize, cfg,
        )


if __name__ == "__main__":
    main()
