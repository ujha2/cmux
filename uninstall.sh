#!/usr/bin/env bash
set -euo pipefail

# cmux uninstaller — removes everything cleanly
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

find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            echo "$cmd"
            return
        fi
    done
    echo ""
}

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

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}cmux uninstaller${RESET}"
echo -e "${DIM}Platform: $PLATFORM${RESET}"
echo ""
echo "This will remove:"
echo "  - cmux Python package"
echo "  - ~/.cmux/ config directory (templates, skills, stats)"
echo "  - PATH entry from shell RC file"
echo "  - Right-click context menu integration"
echo "  - Any running cmux tmux sessions"
echo ""
echo -n "Proceed? [y/N] "
read -r confirm
if [[ ! "$confirm" =~ ^[Yy] ]]; then
    echo "Cancelled."
    exit 0
fi

# ─── 1. Kill tmux sessions ───────────────────────────────────────────────────

step "1/5  Stopping cmux sessions..."

if command -v tmux &>/dev/null && tmux has-session -t cmux 2>/dev/null; then
    tmux kill-session -t cmux
    info "Killed cmux tmux session"
else
    info "No cmux tmux session running"
fi

# ─── 2. Remove context menu ──────────────────────────────────────────────────

step "2/5  Removing context menu..."

PYTHON="$(find_python)"

case "$PLATFORM" in
    macos)
        removed=0
        for wf in "$HOME/Library/Services/Open cmux here.workflow" \
                   "$HOME/Library/Services/Open cmux dashboard here.workflow"; do
            if [ -d "$wf" ]; then
                rm -rf "$wf"
                info "Removed $(basename "$wf")"
                removed=1
            fi
        done
        if [ "$removed" -eq 1 ]; then
            /System/Library/CoreServices/pbs -flush 2>/dev/null || true
        fi
        [ "$removed" -eq 0 ] && info "No Finder Quick Actions found"
        ;;
    wsl|windows)
        if [ -n "$PYTHON" ]; then
            "$PYTHON" -c "
from cmux.integrations.windows_context import uninstall_context_menu
uninstall_context_menu()
" 2>/dev/null || info "No Windows context menu entries found"
        fi
        ;;
    linux)
        for script in "$HOME/.local/share/nautilus/scripts/Open cmux here" \
                       "$HOME/.local/share/nautilus/scripts/Open cmux dashboard here"; do
            if [ -f "$script" ]; then
                rm -f "$script"
                info "Removed $(basename "$script")"
            fi
        done
        info "Nautilus scripts cleaned"
        ;;
esac

# ─── 3. Uninstall Python package ─────────────────────────────────────────────

step "3/5  Uninstalling cmux package..."

if [ -n "$PYTHON" ]; then
    "$PYTHON" -m pip uninstall cmux -y --quiet 2>/dev/null && info "cmux package removed" || info "cmux package not found"
else
    warn "Python not found — skipping pip uninstall"
fi

# ─── 4. Remove PATH entry ────────────────────────────────────────────────────

step "4/5  Cleaning shell config..."

RC_FILE="$(get_rc_file)"
MARKER="# cmux — added by installer"

if [ -f "$RC_FILE" ] && grep -qF "$MARKER" "$RC_FILE"; then
    # Remove the line with our marker
    grep -vF "$MARKER" "$RC_FILE" > "$RC_FILE.cmux_tmp" && mv "$RC_FILE.cmux_tmp" "$RC_FILE"
    info "Removed PATH entry from $RC_FILE"
else
    info "No cmux PATH entry in $RC_FILE"
fi

# ─── 5. Remove config directory ──────────────────────────────────────────────

step "5/5  Removing ~/.cmux/..."

if [ -d "$CMUX_HOME" ]; then
    # Show what's there
    echo -e "  ${DIM}Contents:${RESET}"
    du -sh "$CMUX_HOME"/* 2>/dev/null | sed 's/^/    /' || true

    echo -n "  Delete ~/.cmux/ and all its contents? [y/N] "
    read -r del_config
    if [[ "$del_config" =~ ^[Yy] ]]; then
        rm -rf "$CMUX_HOME"
        info "Removed ~/.cmux/"
    else
        warn "Kept ~/.cmux/ — remove manually with: rm -rf ~/.cmux/"
    fi
else
    info "~/.cmux/ does not exist"
fi

# ─── Also clean up any cmux-output in current dir ────────────────────────────

if [ -d "./cmux-output" ]; then
    echo ""
    echo -n "  Found ./cmux-output/ in current directory. Delete? [y/N] "
    read -r del_output
    if [[ "$del_output" =~ ^[Yy] ]]; then
        rm -rf "./cmux-output"
        info "Removed ./cmux-output/"
    else
        warn "Kept ./cmux-output/"
    fi
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${GREEN}cmux uninstalled.${RESET}"
echo ""
echo -e "  ${DIM}Restart your terminal to complete PATH cleanup.${RESET}"
echo ""
