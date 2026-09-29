"""Linux 桌面听写窗口；所有 Tk 操作都在主线程执行。"""
from __future__ import annotations

import queue
import threading
import time

from .audio import Recorder
from .config import model_dir
from .desktop import active_window, copy_text, is_wayland, paste_text
from .model import Recognizer
from .catalog import MODELS


class App:
    def __init__(self, root, config: dict, control):
        import tkinter as tk
        from tkinter import ttk
        self.root, self.config, self.control = root, config, control
        self.events = queue.Queue()
        self.jobs = queue.Queue(maxsize=1)
        self.recorder = Recorder(config["input_device"], config["max_record_seconds"])
        self.recording = self.busy = self.ready = self.closed = False
        self.generation = 0
        self.target = None
        self.listener = None
        self.hotkey_held = False
        self.hotkey_release_at = None
        self.hotkey_error = ""
        root.title("声控台 离线语音输入")
        root.geometry("560x390")
        root.minsize(460, 330)
        root.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="声控台", font=("sans-serif", 20, "bold")).pack(anchor="w")
        hint = ("使用录音按钮，或在系统快捷键中绑定 shengkongtai toggle。\n识别完成后复制到剪贴板，按 Ctrl+V 粘贴。"
                if is_wayland() else
                f"在输入框中按住 {config['hotkey'].upper()} 说话，松开输入。\n也可以点击录音按钮，完成后复制结果。")
        ttk.Label(frame, text=hint, wraplength=510).pack(anchor="w", pady=(10, 12))
        ttk.Label(frame, text=f"识别模型：{MODELS[config['model_type']]['name']}").pack(anchor="w")
        self.status = tk.StringVar(value=f"正在加载 {MODELS[config['model_type']]['name']}…")
        ttk.Label(frame, textvariable=self.status, wraplength=510).pack(anchor="w", pady=4)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=10)
        self.button = ttk.Button(buttons, text="开始录音", command=lambda: self.toggle(from_button=True), state="disabled")
        self.button.pack(side="left")
        ttk.Button(buttons, text="取消", command=self.cancel).pack(side="left", padx=8)
        self.auto_paste = tk.BooleanVar(value=config["auto_paste"] and not is_wayland())
        ttk.Checkbutton(buttons, text="自动输入到原窗口", variable=self.auto_paste,
                        state="disabled" if is_wayland() else "normal").pack(side="left")
        self.result = tk.Text(frame, height=6, wrap="word", font=("sans-serif", 12))
        self.result.pack(fill="both", expand=True)
        ttk.Button(frame, text="复制结果", command=self.copy_result).pack(anchor="e", pady=(10, 0))
        self.worker = threading.Thread(target=self._work, daemon=True, name="LinuxASR")
        self.worker.start()
        self._start_hotkey()
        root.after(50, self.poll)

    def _work(self):
        try:
            recognizer = Recognizer(model_dir(self.config), self.config["language"], self.config["num_threads"], self.config["model_type"])
            self.events.put(("ready", None))
        except Exception as exc:
            self.events.put(("load_error", str(exc)))
            return
        while True:
            job = self.jobs.get()
            if job is None:
                return
            generation, samples, rate = job
            try:
                text = recognizer.transcribe(samples, rate)
                self.events.put(("result", (generation, text)))
            except Exception as exc:
                self.events.put(("error", (generation, str(exc))))

    def _start_hotkey(self):
        if is_wayland():
            return
        try:
            from pynput import keyboard
            hotkey = getattr(keyboard.Key, self.config["hotkey"])

            def on_press(key):
                if key == hotkey:
                    self.events.put(("hotkey_press", None))
                elif key == keyboard.Key.esc:
                    self.events.put(("cancel", None))

            def on_release(key):
                if key == hotkey:
                    self.events.put(("hotkey_release", None))

            self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.listener.start()
            self.listener.wait()
        except Exception as exc:
            self.events.put(("hotkey_error", f"全局快捷键不可用，请使用录音按钮：{exc}"))

    def start(self, from_button=False):
        if not self.ready or self.recording or self.busy:
            return
        self.target = None if from_button or self.root.focus_displayof() else active_window()
        try:
            self.recorder.start()
            self.recording = True
            self.generation += 1
            self.started = time.monotonic()
            self.button.configure(text="结束录音")
            self.status.set("正在录音…")
        except Exception as exc:
            self.status.set(f"无法打开麦克风：{exc}。可用 shengkongtai devices 查看设备。")

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self.button.configure(text="开始录音")
        try:
            samples, rate = self.recorder.stop()
        except Exception as exc:
            self.status.set(f"停止录音失败：{exc}")
            return
        if self.recorder.error:
            self.status.set(f"录音中断，请重试：{self.recorder.error}")
            return
        if len(samples) < rate * 0.25:
            self.status.set("录音太短，请按住快捷键说话")
            return
        self.busy = True
        self.button.configure(state="disabled")
        self.status.set("正在识别…")
        self.jobs.put_nowait((self.generation, samples, rate))

    def toggle(self, from_button=False):
        if self.recording:
            self.stop()
        else:
            self.start(from_button=from_button)

    def cancel(self):
        if not self.recording and not self.busy:
            return
        self.generation += 1  # 已在推理中的结果随后丢弃，不能继续上屏。
        if self.recording:
            self.recording = False
            try:
                self.recorder.stop()
            except Exception:
                pass
            self.button.configure(text="开始录音")
        self.status.set("已取消" if not self.busy else "已取消，等待当前识别结束…")

    def copy_result(self):
        text = self.result.get("1.0", "end-1c")
        if text:
            try:
                copy_text(text)
                self.status.set("已复制")
            except Exception as exc:
                self.status.set(f"复制失败：{exc}")

    def handle(self, event, payload):
        if event == "hotkey_press":
            # X11 自动重复会产生紧挨着的 KeyRelease/KeyPress，不能误停录音。
            self.hotkey_release_at = None
            if not self.hotkey_held:
                self.hotkey_held = True
                self.start()
        elif event == "hotkey_release":
            if self.hotkey_held:
                self.hotkey_release_at = time.monotonic() + 0.06
        elif event == "ready":
            self.ready = True
            self.button.configure(state="normal")
            self.status.set(self.hotkey_error or "就绪")
        elif event in {"load_error", "hotkey_error"}:
            if event == "hotkey_error":
                self.hotkey_error = payload
            self.status.set(payload)
        elif event in {"start", "stop", "toggle", "cancel", "quit", "show"}:
            if event == "quit":
                self.close()
            elif event == "show":
                self.root.deiconify()
                self.root.lift()
            else:
                getattr(self, event)()
        elif event in {"result", "error"}:
            generation, value = payload
            self.busy = False
            self.button.configure(state="normal")
            if generation != self.generation:
                self.status.set("已取消，就绪")
                return
            if event == "error":
                self.status.set(f"识别失败：{value}")
                return
            if not value:
                self.status.set("未识别到语音，请重试")
                return
            self.result.delete("1.0", "end")
            self.result.insert("1.0", value)
            try:
                self.status.set(paste_text(value, self.target, self.auto_paste.get()))
            except Exception as exc:
                # 原文始终保留在窗口里，即便桌面剪贴板服务不可用。
                self.status.set(f"识别完成，自动输入失败：{exc}。请从窗口复制结果。")

    def poll(self):
        if self.closed:
            return
        for _ in range(32):
            command = self.control.receive()
            if command:
                self.handle(command, None)
            if self.closed:
                return
            try:
                self.handle(*self.events.get_nowait())
            except queue.Empty:
                if command is None:
                    break
            if self.closed:
                return
        if self.hotkey_release_at is not None and time.monotonic() >= self.hotkey_release_at:
            self.hotkey_held = False
            self.hotkey_release_at = None
            self.stop()
        if self.recording:
            if self.recorder.limit_reached or self.recorder.error:
                self.stop()
            else:
                self.status.set(f"正在录音… {int(time.monotonic() - self.started)} 秒")
        self.root.after(50, self.poll)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel()
        if self.listener:
            self.listener.stop()
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass
        self.control.close()
        self.root.destroy()
