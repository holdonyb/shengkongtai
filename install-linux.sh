#!/usr/bin/env bash
# 用户级安装。只为系统依赖调用 sudo；应用和虚拟环境不用 root 运行。
set -euo pipefail
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skip_system=0
for arg in "$@"; do
    case "$arg" in
        --help|-h) exec python3 "$SOURCE_DIR/linux/install.py" --help ;;
        --skip-system-deps|--uninstall) skip_system=1 ;;
    esac
done
if [[ "$(uname -s)" != Linux ]]; then
    echo '请在 Linux 中运行此脚本。' >&2
    exit 1
fi
if [[ $EUID -eq 0 ]]; then
    echo '请以日常桌面用户运行 bash install-linux.sh，不要 sudo 整个脚本。' >&2
    exit 1
fi
if [[ $skip_system -eq 0 ]]; then
    if command -v apt-get >/dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-venv python3-dev build-essential python3-tk libportaudio2 libasound2-plugins libgomp1 xclip xdotool x11-utils wl-clipboard fonts-noto-cjk
    elif command -v dnf >/dev/null; then
        sudo dnf install -y python3 python3-pip python3-devel gcc kernel-headers python3-tkinter portaudio xclip xdotool xprop wl-clipboard google-noto-sans-cjk-fonts
    elif command -v pacman >/dev/null; then
        sudo pacman -S --needed python python-pip base-devel linux-api-headers tk portaudio xclip xdotool xorg-xprop wl-clipboard noto-fonts-cjk
    else
        echo '请先安装 Python 3.10+、venv、Python 开发头文件、C 编译器、Tk、PortAudio、xclip、xdotool 和 wl-clipboard，再加 --skip-system-deps 运行。' >&2
        exit 1
    fi
fi
exec python3 "$SOURCE_DIR/linux/install.py" "$@"
