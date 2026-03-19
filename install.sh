#!/usr/bin/env bash
set -euo pipefail

# cmux installer — sets up everything in one shot
# Works on macOS, Linux, and WSL

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
DIM='\033[2m'
RESET='\033[0m'

info()  { echo -e "${GREEN}✓${RESET} $1"; }
warn()  { echo -e "${YELLOW}!${RESET} $1"; }
err()   { echo -e "${RED}✗${RESET} $1"; }
step()  { echo -e "\n${BOLD}$1${RESET}"; }

CMUX_SRC="$(cd "$(dirname "$0")" && pwd)"
CMUX_HOME="$HOME/.cmux"
SHELL_NAME="$(basename "$SHELL")"

# ─── Detect platform ─────────────────────────────────────────────────────────

detect_platform() {
    case "$(uname -s)" in
        Darwin)  PLATFORM="macos" ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                PLATFORM="wsl"
            else
                PLATFORM="linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
        *) PLATFORM="unknown" ;;
    esac
    echo "$PLATFORM"
}

PLATFORM="$(detect_platform)"

# ─── Detect Python ────────────────────────────────────────────────────────────

find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$cmd"
                return
            fi
        fi
    done
    echo ""
}

# ─── Detect shell RC file ────────────────────────────────────────────────────

get_rc_file() {
    case "$SHELL_NAME" in
        zsh)  echo "$HOME/.zshrc" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        fish) echo "$HOME/.config/fish/config.fish" ;;
        *)    echo "$HOME/.profile" ;;
    esac
}

# ─── Find where pip installs scripts ─────────────────────────────────────────

get_pip_bin_dir() {
    local python="$1"
    "$python" -c "import sysconfig; print(sysconfig.get_path('scripts', 'posix_user'))" 2>/dev/null \
        || "$python" -c "import site; print(site.getusersitepackages().replace('lib/python','bin').rsplit('/',1)[0]+'/bin')" 2>/dev/null \
        || echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}cmux installer${RESET}"
echo -e "${DIM}Platform: $PLATFORM | Shell: $SHELL_NAME${RESET}"

# ─── 1. Check Python ─────────────────────────────────────────────────────────

step "1/6  Checking Python..."

PYTHON="$(find_python)"
if [ -z "$PYTHON" ]; then
    err "Python 3.9+ is required but not found."
    if [ "$PLATFORM" = "macos" ]; then
        echo "  Install with: brew install python@3.11"
    else
        echo "  Install with: sudo apt install python3 python3-pip"
    fi
    exit 1
fi

PY_VERSION=$("$PYTHON" --version)
info "$PY_VERSION"

# ─── 2. Check tmux ───────────────────────────────────────────────────────────

step "2/6  Checking tmux..."

if command -v tmux &>/dev/null; then
    info "tmux $(tmux -V | awk '{print $2}')"
else
    warn "tmux not found — installing..."
    if [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then
            brew install tmux
            info "tmux installed via Homebrew"
        else
            err "tmux is required. Install Homebrew first: https://brew.sh"
            exit 1
        fi
    elif [ "$PLATFORM" = "linux" ] || [ "$PLATFORM" = "wsl" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y -qq tmux
            info "tmux installed via apt"
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y tmux
            info "tmux installed via dnf"
        else
            err "tmux is required. Install it with your package manager."
            exit 1
        fi
    fi
fi

# ─── 3. Install cmux Python package ──────────────────────────────────────────

step "3/6  Installing cmux..."

PIP_LOG="$(mktemp)"

if "$PYTHON" -m pip install --user -e "$CMUX_SRC" --quiet >"$PIP_LOG" 2>&1; then
    tail -1 "$PIP_LOG" || true
    info "cmux package installed"
else
    if grep -qi "externally-managed-environment\|PEP 668" "$PIP_LOG"; then
        warn "Detected a PEP 668 managed Python environment. Retrying with --break-system-packages..."
        if "$PYTHON" -m pip install --user --break-system-packages -e "$CMUX_SRC" --quiet >"$PIP_LOG" 2>&1; then
            tail -1 "$PIP_LOG" || true
            info "cmux package installed"
        else
            err "pip install failed even after PEP 668 fallback."
            tail -40 "$PIP_LOG"
            rm -f "$PIP_LOG"
            exit 1
        fi
    else
        err "pip install failed"
        tail -40 "$PIP_LOG"
        rm -f "$PIP_LOG"
        exit 1
    fi
fi

rm -f "$PIP_LOG"

# ─── 4. Add to PATH ──────────────────────────────────────────────────────────

step "4/6  Configuring PATH..."

BIN_DIR="$(get_pip_bin_dir "$PYTHON")"
RC_FILE="$(get_rc_file)"

if [ -n "$BIN_DIR" ] && [ -d "$BIN_DIR" ]; then
    if echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
        info "$BIN_DIR already on PATH"
    else
        MARKER="# cmux — added by installer"

        if [ "$SHELL_NAME" = "fish" ]; then
            PATH_LINE="fish_add_path $BIN_DIR  $MARKER"
        else
            PATH_LINE="export PATH=\"$BIN_DIR:\$PATH\"  $MARKER"
        fi

        if grep -qF "$MARKER" "$RC_FILE" 2>/dev/null; then
            info "PATH entry already in $RC_FILE"
        else
            echo "" >> "$RC_FILE"
            echo "$PATH_LINE" >> "$RC_FILE"
            info "Added $BIN_DIR to PATH in $RC_FILE"
        fi

        # Also export for the rest of this script
        export PATH="$BIN_DIR:$PATH"
    fi
else
    warn "Could not determine pip bin directory. You may need to add cmux to PATH manually."
fi

# Verify cmux is now callable
if command -v cmux &>/dev/null; then
    info "cmux command available"
else
    # Try sourcing the RC file
    export PATH="$BIN_DIR:$PATH"
    if command -v cmux &>/dev/null; then
        info "cmux command available (after PATH update)"
    else
        warn "cmux installed but not yet on PATH. Restart your terminal or run:"
        echo "  source $RC_FILE"
    fi
fi

# ─── 5. Initialize cmux config ───────────────────────────────────────────────

step "5/6  Initializing cmux config..."

mkdir -p "$CMUX_HOME"/{templates,skills,data}

if [ ! -f "$CMUX_HOME/config.yaml" ]; then
    cat > "$CMUX_HOME/config.yaml" << 'YAML'
# cmux configuration
# Docs: cmux --help

backend:
  backend: claude
  claude_model: claude-sonnet-4-6
  claude_args: []

max_parallel_sessions: 5
output_dir: ./cmux-output

# Map templates to skills:
# template_skill_map:
#   weekly_status: [status_update]
#   ppt_style: [deck]
#   prd_structure: [prd_spec]

# Presets:
# presets:
#   morning:
#     description: "Morning workflow — pull tasks, triage email"
#     tasks:
#       - name: triage-email
#         description: "Summarize and prioritize inbox"
#         skill: status_update
YAML
    info "Created ~/.cmux/config.yaml"
else
    info "~/.cmux/config.yaml already exists"
fi

info "Directories: ~/.cmux/{templates,skills,data}"

# ─── 6. Context menu integration ─────────────────────────────────────────────

step "6/6  Right-click integration..."

case "$PLATFORM" in
    macos)
        echo -n "  Install Finder Quick Actions? (right-click → Open cmux here) [y/N] "
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            "$PYTHON" -c "from cmux.integrations.macos_context import install_context_menu; install_context_menu()"
        else
            info "Skipped — run 'cmux install-context-menu' later if you want it"
        fi
        ;;
    wsl|windows)
        echo -n "  Install Windows Explorer context menu? [y/N] "
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            "$PYTHON" -c "from cmux.integrations.windows_context import install_context_menu; install_context_menu()"
        else
            info "Skipped — run 'cmux install-context-menu' later if you want it"
        fi
        ;;
    linux)
        echo -n "  Install Nautilus right-click scripts? [y/N] "
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            "$PYTHON" -c "from cmux.integrations.platform import install_context_menu; install_context_menu()"
        else
            info "Skipped — run 'cmux install-context-menu' later if you want it"
        fi
        ;;
esac

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}cmux installed!${RESET}"
echo ""
echo "  Quick start:"
echo "    cmux skills                              # see all PM skills"
echo "    cmux add \"write a PRD for X\" --run       # add + launch a task"
echo "    cmux status                              # check running sessions"
echo "    cmux dashboard                           # productivity TUI"
echo ""
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR" 2>/dev/null; then
    echo -e "  ${YELLOW}Restart your terminal or run: source $RC_FILE${RESET}"
    echo ""
fi
