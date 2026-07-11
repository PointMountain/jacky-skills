#!/usr/bin/env bash
# install.sh — 一键链接并安装 jacky-skills 中的全部活跃 Skill
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/wangjs-jacky/jacky-skills/main/install.sh | bash
#   J_SKILLS_ENVS=claude-code,codex,cursor ./install.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO_URL="${JACKY_SKILLS_REPO_URL:-https://github.com/wangjs-jacky/jacky-skills.git}"
REPO_DIR="${JACKY_SKILLS_REPO_DIR:-$HOME/jacky-github/jacky-skills}"
INSTALL_ENVS="${J_SKILLS_ENVS:-claude-code,codex}"

info() {
    echo -e "${BLUE}$*${NC}"
}

success() {
    echo -e "${GREEN}$*${NC}"
}

fail() {
    echo -e "${RED}错误: $*${NC}" >&2
    exit 1
}

read_skill_name() {
    awk '
        BEGIN { in_frontmatter = 0 }
        /^---[[:space:]]*$/ {
            if (in_frontmatter == 0) {
                in_frontmatter = 1
                next
            }
            exit
        }
        in_frontmatter && /^name:[[:space:]]*/ {
            sub(/^name:[[:space:]]*/, "", $0)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
            gsub(/^"|"$/, "", $0)
            print $0
            exit
        }
    ' "$1"
}

linked_path_for() {
    local skill_name="$1"

    printf '%s' "$LINKED_SKILLS_JSON" | node -e '
        let input = "";
        process.stdin.setEncoding("utf8");
        process.stdin.on("data", (chunk) => { input += chunk; });
        process.stdin.on("end", () => {
            const data = JSON.parse(input);
            const match = (data.skills || []).find((skill) => skill.name === process.argv[1]);
            if (match && match.path) process.stdout.write(match.path);
        });
    ' "$skill_name"
}

canonical_path() {
    if [ -d "$1" ]; then
        (cd "$1" && pwd -P)
    else
        printf '%s' "$1"
    fi
}

link_skill_dir() {
    local skill_dir="$1"
    local compatibility_link="$skill_dir/skill.md"
    local compatibility_link_created=false
    local link_status=0

    # j-skills 0.1.0 在大小写敏感文件系统上检查小写 skill.md。
    # 临时链接只用于兼容该版本，不会留在 Skill 目录。
    if [ ! -e "$compatibility_link" ]; then
        ln -s SKILL.md "$compatibility_link"
        compatibility_link_created=true
    fi

    if j-skills link "$skill_dir"; then
        link_status=0
    else
        link_status=$?
    fi

    if [ "$compatibility_link_created" = true ]; then
        rm -f "$compatibility_link"
    fi
    return "$link_status"
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         jacky-skills 一键安装（Claude Code + Codex）       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

echo -e "${YELLOW}[1/5] 检查 Node.js...${NC}"
command -v node >/dev/null 2>&1 || fail "未安装 Node.js 18+"

NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
[ "$NODE_MAJOR" -ge 18 ] || fail "Node.js 版本过低，需要 18+，当前为 $(node -v)"

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    NODE_ARCH="$(node -p 'process.arch')"
    [ "$NODE_ARCH" = "arm64" ] || fail "Apple Silicon Mac 必须使用原生 ARM64 Node.js，当前架构为 $NODE_ARCH"
fi
success "✓ Node.js $(node -v) ($(node -p 'process.arch'))"

echo -e "${YELLOW}[2/5] 检查 j-skills CLI...${NC}"
if ! command -v j-skills >/dev/null 2>&1; then
    info "正在安装 j-skills CLI..."
    npm install -g j-skills --no-audit --no-fund
fi
success "✓ $(j-skills --version)"

echo -e "${YELLOW}[3/5] 克隆或更新仓库...${NC}"
if [ -d "$REPO_DIR/.git" ]; then
    git -C "$REPO_DIR" pull --ff-only origin main
elif [ -e "$REPO_DIR" ]; then
    fail "$REPO_DIR 已存在，但不是 Git 仓库"
else
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone "$REPO_URL" "$REPO_DIR"
fi
success "✓ 仓库已就绪：$REPO_DIR"

echo -e "${YELLOW}[4/5] 链接活跃 Skills...${NC}"
LINKED_SKILLS_JSON="$(j-skills link --list --json)"
SKILL_COUNT=0

while IFS= read -r skill_file; do
    skill_dir="$(canonical_path "$(dirname "$skill_file")")"
    skill_name="$(read_skill_name "$skill_file")"
    [ -n "$skill_name" ] || fail "$skill_file 缺少有效的 frontmatter name"

    filesystem_link="$HOME/.j-skills/linked/$skill_name"
    linked_path="$(linked_path_for "$skill_name")"
    if [ -n "$linked_path" ]; then
        canonical_linked_path="$(canonical_path "$linked_path")"
        if [ ! -L "$filesystem_link" ]; then
            fail "链接冲突：$skill_name 已在注册表中，但 $filesystem_link 不是有效软链接"
        fi
        canonical_filesystem_link="$(canonical_path "$filesystem_link")"
        if [ "$canonical_linked_path" = "$skill_dir" ] && [ "$canonical_filesystem_link" = "$skill_dir" ]; then
            info "  跳过 $skill_name：已正确链接"
        else
            fail "链接冲突：$skill_name 的注册表或软链接目标不是 $skill_dir"
        fi
    else
        if [ -e "$filesystem_link" ] || [ -L "$filesystem_link" ]; then
            fail "链接冲突：$filesystem_link 已存在，但未出现在 j-skills 注册表中"
        fi
        info "  链接：$skill_name"
        link_skill_dir "$skill_dir"
        LINKED_SKILLS_JSON="$(j-skills link --list --json)"
    fi

    SKILL_COUNT=$((SKILL_COUNT + 1))
done < <(
    find "$REPO_DIR/plugins" "$REPO_DIR/skills" "$REPO_DIR/harness" \
        -type d -name archived -prune -o \
        -type f -name SKILL.md -print | sort
)
success "✓ 已核对 $SKILL_COUNT 个 Skills 的链接"

echo -e "${YELLOW}[5/5] 安装到 $INSTALL_ENVS...${NC}"
while IFS= read -r skill_file; do
    skill_name="$(read_skill_name "$skill_file")"
    [ -n "$skill_name" ] || fail "$skill_file 缺少有效的 frontmatter name"
    info "  安装：$skill_name"
    CI=1 j-skills install "$skill_name" -g --env "$INSTALL_ENVS"
done < <(
    find "$REPO_DIR/plugins" "$REPO_DIR/skills" "$REPO_DIR/harness" \
        -type d -name archived -prune -o \
        -type f -name SKILL.md -print | sort
)

success "✓ 安装完成：$SKILL_COUNT 个 Skills → $INSTALL_ENVS"
echo "仓库位置：$REPO_DIR"
echo "查看链接：j-skills link --list"
echo "查看安装：j-skills list --all"
