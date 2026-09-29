"""在 xvfb-run + Openbox 中运行，不触碰用户桌面或真实麦克风。

真实模型、真实 X11 热键、真实中文粘贴；仅用官方 WAV 代替麦克风音频。
用法：xvfb-run -a python linux/smoke_test.py --wav /path/to/zh.wav
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--model", choices=("qwen_asr", "fun_asr_nano"), default="qwen_asr")
    args = parser.parse_args()
    # 只能在专门的虚拟显示器里运行，避免向用户窗口输入测试内容。
    display = os.environ.get("DISPLAY", "")
    if not display.startswith(":") or int(display[1:].split(".")[0]) < 90:
        raise RuntimeError("请通过 xvfb-run -a 执行（测试显示号须 >= 90）")
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ["XDG_SESSION_TYPE"] = "x11"
    import numpy as np
    import tkinter as tk
    from shengkongtai.app import App
    from shengkongtai.config import load_config
    from shengkongtai.desktop import Control, active_window, send_control, paste_text
    from shengkongtai.audio import Recorder

    wm = subprocess.Popen(["openbox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    control = Control()
    root = target = app = None
    try:
        time.sleep(0.4)
        assert control.acquire()
        root = tk.Tk()
        config = load_config()
        config.update(model_type=args.model, model_dir="", language="auto")
        app = App(root, config, control)

        def wait(predicate, timeout=120):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                root.update()
                if predicate():
                    return
                time.sleep(0.02)
            raise AssertionError("等待超时: " + app.status.get())

        wait(lambda: app.ready)
        assert not app.hotkey_error, app.hotkey_error
        with wave.open(str(args.wav)) as stream:
            rate = stream.getframerate()
            samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32) / 32768

        class FixtureRecorder(Recorder):
            def start(self):
                self.frames, self.count, self.error, self.limit_reached = [], 0, "", False
                self.sample_rate = rate
                self._callback(samples.reshape(-1, 1), len(samples), None, None)

        app.recorder = FixtureRecorder()
        # 第二个 Tk 使用独立 X 连接，作为真实目标输入框。
        target = tk.Tk(className="ShengKongTaiSmokeTarget")
        target.title("ShengKongTai Linux Input Test")
        field = tk.Text(target)
        field.pack()
        target.update()
        result = subprocess.run(["xdotool", "search", "--name", "^ShengKongTai Linux Input Test$"],
                                capture_output=True, text=True, check=True)
        target_id = result.stdout.strip().splitlines()[-1]
        subprocess.run(["xdotool", "windowactivate", "--sync", target_id], check=True)
        field.focus_force()
        root.update()
        assert active_window() == target_id
        subprocess.run(["xdotool", "keydown", "F8"], check=True)
        wait(lambda: app.recording)
        # 跨过 X11 键盘自动重复延迟，确保长按不会被拆成多段录音。
        held_until = time.monotonic() + 1.2
        while time.monotonic() < held_until:
            root.update()
            assert app.recording
            time.sleep(0.02)
        subprocess.run(["xdotool", "keyup", "F8"], check=True)
        wait(lambda: not app.recording and not app.busy and bool(field.get("1.0", "end-1c")))
        recognized = app.result.get("1.0", "end-1c")
        assert field.get("1.0", "end-1c") == recognized
        assert any(s in recognized for s in ("9", "九")) and any(s in recognized for s in ("5", "五"))
        print(f"PASS: F8 → 录音缓存 → 真实 {args.model} → 中文自动粘贴:", recognized, flush=True)
        print("STATUS:", app.status.get(), flush=True)

        # 通过同一 worker 验证 48kHz，避免同时加载两个 1.7B 模型。
        app.busy = True
        app.target = None
        app.jobs.put_nowait((app.generation, np.repeat(samples, 3), rate * 3))
        wait(lambda: not app.busy)
        text_48k = app.result.get("1.0", "end-1c")
        assert any(s in text_48k for s in ("9", "九")) and any(s in text_48k for s in ("5", "五"))
        print("PASS: 48kHz 音频重采样:", text_48k, flush=True)

        # 取消后绝不上屏；再测试控制 socket 的独立命令。
        previous = field.get("1.0", "end-1c")
        send_control("start")
        wait(lambda: app.recording)
        send_control("cancel")
        wait(lambda: not app.recording)
        assert field.get("1.0", "end-1c") == previous
        print("PASS: 控制套接字开始/取消", flush=True)

        wrong_target = "123456789"
        assert "窗口已切换" in paste_text("焦点保护", wrong_target, True)
        root.update()
        assert field.get("1.0", "end-1c") == previous
        print("PASS: 焦点变更阻止自动粘贴", flush=True)
        if args.screenshot:
            root.deiconify()
            root.lift()
            root.update()
            time.sleep(0.2)
            subprocess.run(["scrot", str(args.screenshot)], check=True)
    finally:
        if app and not app.closed:
            app.close()
        if target:
            target.destroy()
        control.close()
        wm.terminate()
        wm.wait(timeout=5)


if __name__ == "__main__":
    main()
