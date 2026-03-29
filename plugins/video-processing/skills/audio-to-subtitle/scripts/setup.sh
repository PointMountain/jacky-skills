#!/usr/bin/env bash
# audio-to-subtitle 依赖安装脚本
# 适用于 macOS (Apple Silicon)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ============================================================
# 1. 环境检查
# ============================================================

info "检查运行环境..."

# 检查是否为 Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    warn "当前非 Apple Silicon (arm64)，MLX-Whisper 可能无法运行"
    warn "建议在 Apple Silicon Mac 上使用本工具"
fi

# 检查 macOS
if [[ "$(uname)" != "Darwin" ]]; then
    warn "当前非 macOS 系统，部分功能可能不可用"
fi

ok "系统检查通过: $(uname -s) $(uname -m)"

# ============================================================
# 2. 检查 Homebrew
# ============================================================

if ! command -v brew &>/dev/null; then
    warn "Homebrew 未安装"
    info "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

ok "Homebrew 已就绪"

# ============================================================
# 3. 安装 ffmpeg
# ============================================================

if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg 已安装: $(ffmpeg -version | head -1)"
else
    info "安装 ffmpeg..."
    brew install ffmpeg
    ok "ffmpeg 安装完成"
fi

# ============================================================
# 4. 检查 Python3
# ============================================================

if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    ok "Python3 已安装: v${PYTHON_VERSION}"

    # 检查版本 >= 3.10
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

    if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ]]; then
        warn "Python 版本过低 (需要 >= 3.10)，建议升级"
    fi
else
    info "安装 Python3..."
    brew install python@3.12
    ok "Python3 安装完成"
fi

# ============================================================
# 5. 安装 mlx-whisper
# ============================================================

info "安装 Python 依赖..."

# 检查是否在虚拟环境中
if python3 -c "import mlx_whisper" 2>/dev/null; then
    MLX_VERSION=$(python3 -c "import mlx_whisper; print(mlx_whisper.__version__)" 2>/dev/null || echo "unknown")
    ok "mlx-whisper 已安装: v${MLX_VERSION}"
else
    info "安装 mlx-whisper（Apple Silicon 优化的 Whisper）..."
    pip3 install mlx-whisper
    ok "mlx-whisper 安装完成"
fi

# 可选：安装 requests（云端 API 支持）
if ! python3 -c "import requests" 2>/dev/null; then
    info "安装 requests（云端 API 支持）..."
    pip3 install requests
fi

# ============================================================
# 6. 验证安装
# ============================================================

echo ""
info "验证安装..."

ERRORS=0

# 检查 ffmpeg
if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg ✓"
else
    fail "ffmpeg ✗"
    ERRORS=$((ERRORS + 1))
fi

# 检查 python3
if command -v python3 &>/dev/null; then
    ok "python3 ✓"
else
    fail "python3 ✗"
    ERRORS=$((ERRORS + 1))
fi

# 检查 mlx_whisper
if python3 -c "import mlx_whisper" 2>/dev/null; then
    ok "mlx-whisper ✓"
else
    fail "mlx-whisper ✗"
    ERRORS=$((ERRORS + 1))
fi

# 检查 MLX
if python3 -c "import mlx.core" 2>/dev/null; then
    ok "mlx core ✓"
else
    warn "mlx core 未安装（可选）"
fi

echo ""

if [[ $ERRORS -eq 0 ]]; then
    ok "🎉 所有依赖安装成功！"
    echo ""
    info "使用方法:"
    echo "  python3 scripts/transcribe.py audio.mp3"
    echo "  python3 scripts/transcribe.py audio.mp3 -f vtt"
    echo "  python3 scripts/transcribe.py ~/Downloads/audio/ --batch"
else
    fail "有 $ERRORS 个依赖安装失败，请检查上方错误信息"
fi
