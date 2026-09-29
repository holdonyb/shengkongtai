"""Linux 桌面剪贴板、焦点守卫及仅当前用户可用的控制套接字。"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess

from .config import runtime_dir


def is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))


def copy_text(text: str) -> None:
    command = ["wl-copy", "--type", "text/plain;charset=utf-8"] if is_wayland() else ["xclip", "-selection", "clipboard"]
    if not shutil.which(command[0]):
        raise RuntimeError(f"缺少 {command[0]}，请重新运行安装脚本安装桌面依赖")
    # xclip/wl-copy 会派生剪贴板所有者，不能 capture_output 后等待继承的管道关闭。
    subprocess.run(command, input=text.encode("utf-8"), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True, timeout=5)


def active_window() -> str | None:
    if is_wayland() or not shutil.which("xdotool"):
        return None
    try:
        result = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True,
                                check=True, timeout=2)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def paste_text(text: str, target: str | None, auto_paste: bool) -> str:
    copy_text(text)
    if is_wayland() or not auto_paste:
        return "已复制，可在输入框中粘贴"
    if not target or active_window() != target:
        return "已复制；窗口已切换，请手动粘贴"
    # 不强制切回旧窗口。终端的粘贴快捷键与普通文本框不同。
    result = subprocess.run(["xprop", "-id", target, "WM_CLASS"],
                            capture_output=True, text=True, check=True, timeout=2)
    wm_class = result.stdout.lower()
    terminal = any(word in wm_class for word in (
        "terminal", "konsole", "xterm", "alacritty", "kitty", "wezterm", "terminator", "tilix", "st-256color",
    ))
    combo = "ctrl+shift+v" if terminal else "ctrl+v"
    if active_window() != target:
        return "已复制；窗口已切换，请手动粘贴"
    subprocess.run(["xdotool", "key", "--clearmodifiers", combo], check=True, timeout=2)
    return "已输入，结果同时保留在剪贴板"


class Control:
    """flock 随进程结束释放；旧 socket 仅在取得锁后清理。"""
    def __init__(self):
        self.lock = None
        self.socket = None
        self.path = runtime_dir() / "control.sock"

    def acquire(self) -> bool:
        import fcntl
        self.lock = (self.path.parent / "instance.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            return False
        self.path.unlink(missing_ok=True)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(str(self.path))
        self.path.chmod(0o600)
        self.socket.setblocking(False)
        return True

    def receive(self):
        try:
            return self.socket.recv(64).decode("ascii")
        except (BlockingIOError, UnicodeDecodeError):
            return None

    def close(self):
        if self.socket:
            self.socket.close()
            self.path.unlink(missing_ok=True)
            self.socket = None
        if self.lock:
            self.lock.close()
            self.lock = None


def send_control(command: str) -> None:
    if command not in {"toggle", "start", "stop", "cancel", "show", "quit"}:
        raise ValueError("未知控制命令")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
        sender.settimeout(2)
        try:
            sender.sendto(command.encode("ascii"), str(runtime_dir() / "control.sock"))
        except OSError as exc:
            raise RuntimeError("声控台 尚未启动，请先从应用菜单打开 声控台") from exc
