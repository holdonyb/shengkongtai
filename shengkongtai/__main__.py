from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys

from . import __version__
from .config import config_dir, data_dir, initialize_config, load_config, model_dir, xdg_path, save_model_selection
from .catalog import MODELS


def doctor(config: dict) -> int:
    from .desktop import is_wayland
    from .model import verified
    failures = []
    for name in ("tkinter", "numpy", "sounddevice", "onnxruntime", "gguf", "scipy", "pynput"):
        try:
            ok = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            ok = False
        print(f"{'OK' if ok else '缺少'}  {name}")
        if not ok:
            failures.append(name)
    for name in (["wl-copy"] if is_wayland() else ["xclip", "xdotool", "xprop"]):
        ok = bool(shutil.which(name))
        print(f"{'OK' if ok else '缺少'}  {name}")
        if not ok:
            failures.append(name)
    ok = verified(model_dir(config), config["model_type"])
    print(f"{'OK' if ok else '缺少或校验失败'}  离线模型: {model_dir(config)}")
    if not ok:
        failures.append("model")
    from .runtime import verified_runtime
    if verified_runtime():
        print("OK  llama.cpp b7798 Linux 运行库")
    else:
        print("缺少或校验失败  llama.cpp b7798 Linux 运行库")
        failures.append("runtime")
    try:
        import sounddevice as sd
        device = sd.query_devices(config["input_device"], "input")
        print(f"OK  麦克风: {device['name']}")
    except Exception as exc:
        print(f"不可用  麦克风: {exc}")
        failures.append("microphone")
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        print("OK  图形会话")
    except Exception as exc:
        print(f"不可用  图形会话：{exc}；请在桌面终端运行，Wayland 需启用 XWayland")
        failures.append("display")
    print("桌面模式: " + ("Wayland（系统快捷键 + 剪贴板）" if is_wayland() else "X11（全局热键 + 自动粘贴）"))
    print(f"配置: {config_dir() / 'config.json'}")
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="声控台 Linux 离线语音输入")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    for name in ("toggle", "start", "stop", "cancel", "quit", "show", "doctor", "devices"):
        sub.add_parser(name)
    selection = sub.add_parser("model", help="查看或切换识别模型，切换后重新打开应用")
    selection.add_argument("name", choices=tuple(MODELS), nargs="?")
    download = sub.add_parser("download-model", help="导入已有模型（需提供目录或 ZIP）")
    download.add_argument("--from-dir", type=Path)
    download.add_argument("--archive", type=Path)
    transcribe = sub.add_parser("transcribe", help="转写 PCM16 WAV，结果输出到终端")
    transcribe.add_argument("file", type=Path)
    auto = sub.add_parser("autostart", help="当前用户登录后自动启动")
    auto.add_argument("mode", choices=("on", "off"))
    args = parser.parse_args(argv)
    if not sys.platform.startswith("linux"):
        parser.error("此入口用于 Linux；Windows 请使用原有客户端")
    try:
        if args.command in {"toggle", "start", "stop", "cancel", "quit", "show"}:
            from .desktop import send_control
            send_control(args.command)
            return 0
        if args.command == "autostart":
            path = xdg_path("XDG_CONFIG_HOME", ".config") / "autostart" / "shengkongtai.desktop"
            if args.mode == "on":
                source = xdg_path("XDG_DATA_HOME", ".local/share") / "applications" / "shengkongtai.desktop"
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, path)
            else:
                path.unlink(missing_ok=True)
            print("自启动已" + ("开启" if args.mode == "on" else "关闭"))
            return 0
        initialize_config()
        config = load_config()
        if args.command == "model":
            from .model import verified
            if args.name:
                selected = dict(config, model_type=args.name, model_dir="")
                if not verified(model_dir(selected), args.name):
                    raise ValueError("该模型尚未安装，请重新运行含模型安装包")
                save_model_selection(args.name)
                print(f"已选择 {MODELS[args.name]['name']}，请退出并重新打开 声控台。")
            else:
                print(f"当前模型：{MODELS[config['model_type']]['name']}")
                for key, item in MODELS.items():
                    directory = model_dir(dict(config, model_type=key, model_dir=""))
                    print(f"{key}: {item['name']}（{'已安装' if verified(directory, key) else '未安装'}）")
            return 0
        if args.command == "download-model":
            from .model import install_model
            install_model(model_dir(config), args.from_dir, args.archive, config["model_type"])
            return 0
        if args.command == "doctor":
            return doctor(config)
        if args.command == "devices":
            import sounddevice
            print(sounddevice.query_devices())
            return 0
        if args.command == "transcribe":
            import wave
            import numpy as np
            from .model import Recognizer
            with wave.open(str(args.file), "rb") as stream:
                if stream.getsampwidth() != 2 or stream.getcomptype() != "NONE":
                    raise ValueError("请使用 PCM 16-bit WAV 文件")
                if stream.getnframes() > stream.getframerate() * 120:
                    raise ValueError("单次 WAV 转写限 120 秒")
                samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32) / 32768
                samples = samples.reshape(-1, stream.getnchannels()).mean(axis=1)
                rate = stream.getframerate()
            recognizer = Recognizer(model_dir(config), config["language"], config["num_threads"], config["model_type"])
            print(recognizer.transcribe(samples, rate))
            return 0
        from .desktop import Control, send_control
        control = Control()
        if not control.acquire():
            send_control("show")
            return 0
        try:
            import tkinter as tk
            from .app import App
            root = tk.Tk()
            app = App(root, config, control)
            import signal
            # Python 信号处理器只入队，Tk 资源清理在下一轮事件处理。
            signal.signal(signal.SIGTERM, lambda *_: app.events.put(("quit", None)))
            signal.signal(signal.SIGINT, lambda *_: app.events.put(("quit", None)))
            root.mainloop()
        finally:
            control.close()
        return 0
    except Exception as exc:
        print(f"声控台: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
