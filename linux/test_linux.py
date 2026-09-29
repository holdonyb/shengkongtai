"""Linux 适配边界回归：无麦克风、无真实桌面副作用。"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shengkongtai import config, desktop, model


class ConfigTests(unittest.TestCase):
    def test_switch_preserves_other_settings_and_uses_separate_weights(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
            config.initialize_config()
            path = config.config_dir() / "config.json"
            path.write_text('{"hotkey":"f9","model_dir":"/old/qwen","language":"yue"}')
            config.save_model_selection("fun_asr_nano")
            value = config.load_config()
            self.assertEqual(value["hotkey"], "f9")
            self.assertEqual(value["language"], "auto")
            self.assertEqual(config.model_dir(value).name, "fun-asr-nano")

    def test_defaults_do_not_load_windows_overrides(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
            config.initialize_config()
            self.assertEqual(config.load_config()["hotkey"], "f8")
            path = config.config_dir() / "config.json"
            path.write_text('{"hotkey":"f9","api_key":"private"}', encoding="utf-8")
            config.initialize_config()
            value = config.load_config()
            self.assertEqual(value["hotkey"], "f9")
            self.assertNotIn("api_key", value)

    def test_invalid_recording_bounds_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
            config.initialize_config()
            for value in (0, 121, "60", True):
                (config.config_dir() / "config.json").write_text(json.dumps({"max_record_seconds": value}))
                with self.assertRaises(ValueError):
                    config.load_config()


class ModelTests(unittest.TestCase):
    def test_automatic_download_verifies_archive_and_each_model_file(self):
        import hashlib
        key = "fun_asr_nano"
        content = b"verified model fixture"
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as bundle:
            bundle.writestr("upstream/weights.onnx", content)
        archive = stream.getvalue()
        item = {"files": {"weights.onnx": hashlib.sha256(content).hexdigest()},
                "archive_size": len(archive), "archive_sha256": hashlib.sha256(archive).hexdigest()}
        with tempfile.TemporaryDirectory() as temp, patch.dict(model.MODELS[key], item):
            with patch.object(model.urllib.request, "urlopen", return_value=io.BytesIO(archive)) as download:
                destination = Path(temp) / "model"
                model.install_model(destination, model_type=key)
                self.assertEqual((destination / "weights.onnx").read_bytes(), content)
                self.assertEqual(list(destination.glob(".download-*")), [])
                model.install_model(destination, model_type=key)
                self.assertEqual(download.call_count, 1)

    def test_bad_download_cannot_replace_existing_model_files(self):
        key = "fun_asr_nano"
        archive = b"corrupt or substituted download"
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            (destination / "tokens.txt").write_text("existing")
            with patch.dict(model.MODELS[key], {"archive_size": len(archive)}):
                with patch.object(model.urllib.request, "urlopen", return_value=io.BytesIO(archive)):
                    with self.assertRaisesRegex(ValueError, "SHA256"):
                        model.install_model(destination, model_type=key)
            self.assertEqual((destination / "tokens.txt").read_text(), "existing")
            self.assertEqual([p.name for p in destination.iterdir()], ["tokens.txt"])

    def test_wrong_precision_archive_rejected_before_model_replace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "model.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name in model.MODELS["qwen_asr"]["files"]:
                    bundle.writestr(name, b"different weights")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                model.install_model(root / "target", archive=archive)
            self.assertEqual(list((root / "target").iterdir()), [])

    def test_bad_archive_cannot_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "model"
            target.mkdir()
            (target / "tokens.txt").write_text("old")
            archive = root / "invalid.tar.bz2"
            archive.write_bytes(b"broken")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                model.install_model(target, archive=archive)
            self.assertEqual((target / "tokens.txt").read_text(), "old")
            self.assertEqual(list(target.glob(".download-*")), [])

    def test_archive_extracts_only_verified_regular_model_files(self):
        import hashlib
        contents = {name: name.encode() for name in model.MODELS["qwen_asr"]["files"]}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "model.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name, data in {**contents, "../../outside": b"do not extract"}.items():
                    bundle.writestr("upstream/" + name, data)
            with patch.dict(model.MODELS["qwen_asr"], {"files": hashes}):
                model.install_model(root / "target", archive=archive)
                self.assertTrue(model.verified(root / "target"))
            self.assertEqual(sorted(p.name for p in (root / "target").iterdir()), sorted(contents))


class DesktopTests(unittest.TestCase):
    def test_wayland_detected_even_with_xwayland_display(self):
        with patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": ""}):
            self.assertTrue(desktop.is_wayland())

    def test_wayland_copies_without_injecting_keys(self):
        with patch.object(desktop, "is_wayland", return_value=True), patch.object(desktop, "copy_text") as copy, patch.object(desktop.subprocess, "run") as run:
            status = desktop.paste_text("中文", "12", True)
            copy.assert_called_once_with("中文")
            run.assert_not_called()
            self.assertIn("粘贴", status)

    def test_focus_change_prevents_paste(self):
        with patch.object(desktop, "is_wayland", return_value=False), patch.object(desktop, "copy_text"), patch.object(desktop, "active_window", return_value="new"), patch.object(desktop.subprocess, "run") as run:
            self.assertIn("窗口已切换", desktop.paste_text("中文", "old", True))
            run.assert_not_called()

    def test_terminal_uses_ctrl_shift_v(self):
        with patch.object(desktop, "is_wayland", return_value=False), patch.object(desktop, "copy_text"), patch.object(desktop, "active_window", return_value="42"), patch.object(desktop.subprocess, "run", return_value=Mock(stdout="org.gnome.Terminal")) as run:
            desktop.paste_text("中文", "42", True)
            self.assertEqual(run.call_args.args[0][-1], "ctrl+shift+v")

    @unittest.skipUnless(sys.platform.startswith("linux"), "POSIX 锁和 Unix socket")
    def test_single_instance_and_command_delivery(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"XDG_RUNTIME_DIR": temp}):
            first, second = desktop.Control(), desktop.Control()
            self.assertTrue(first.acquire())
            try:
                self.assertFalse(second.acquire())
                desktop.send_control("toggle")
                self.assertEqual(first.receive(), "toggle")
                self.assertEqual(first.path.stat().st_mode & 0o777, 0o600)
                # 独立进程也无法获取锁，而非仅验证同进程内实例。
                probe = "from shengkongtai.desktop import Control; c=Control(); assert not c.acquire()"
                subprocess.run([sys.executable, "-c", probe], cwd=ROOT, check=True)
            finally:
                first.close()
                second.close()
            self.assertTrue(second.acquire())
            second.close()


class RecordingTests(unittest.TestCase):
    def test_qwen_44100_audio_resampled_to_16000(self):
        import numpy as np
        samples = model.prepare_audio(np.ones(44100, dtype=np.float32), 44100)
        self.assertEqual(samples.shape, (16000,))
        self.assertEqual(samples.dtype, np.float32)

    def test_qwen_long_audio_covers_tail_without_silent_truncation(self):
        import numpy as np
        from types import SimpleNamespace
        from util import setup_logger
        with tempfile.TemporaryDirectory() as temp:
            setup_logger("server", log_dir=temp, level="ERROR")
            recorder = model.Recognizer.__new__(model.Recognizer)
            recorder.language = None
            recorder.model_type = "qwen_asr"
            stream = SimpleNamespace(result=SimpleNamespace(text="语音"), accept_waveform=Mock())
            recorder.engine = Mock()
            recorder.engine.create_stream.return_value = stream
            recorder.transcribe(np.zeros(40 * 16000, dtype=np.float32), 16000)
            lengths = [len(call.args[1]) / 16000 for call in stream.accept_waveform.call_args_list]
            self.assertEqual(lengths, [16.5, 16.5, 10.0])

    def test_x11_auto_repeat_does_not_restart_or_stop_recording(self):
        from shengkongtai.app import App
        app = App.__new__(App)
        app.hotkey_held = False
        app.hotkey_release_at = None
        app.start, app.stop = Mock(), Mock()
        app.handle("hotkey_press", None)
        for _ in range(20):
            app.handle("hotkey_release", None)
            app.handle("hotkey_press", None)
        app.start.assert_called_once()
        app.stop.assert_not_called()
        self.assertIsNone(app.hotkey_release_at)
        app.handle("hotkey_release", None)
        self.assertIsNotNone(app.hotkey_release_at)

    def test_audio_buffer_is_bounded(self):
        import numpy as np
        from shengkongtai.audio import Recorder
        recorder = Recorder(max_seconds=1)
        recorder.sample_rate = 4
        recorder._callback(np.ones((8, 1), dtype=np.float32), 8, None, None)
        recorder._callback(np.ones((8, 1), dtype=np.float32), 8, None, None)
        self.assertTrue(recorder.limit_reached)
        samples, rate = recorder.stop()
        self.assertEqual(len(samples), 4)
        self.assertEqual(rate, 4)

    def test_cancelled_recognition_never_reaches_clipboard(self):
        from shengkongtai.app import App
        app = App.__new__(App)
        app.generation = 2
        app.button, app.status, app.result = Mock(), Mock(), Mock()
        with patch("shengkongtai.app.paste_text") as paste:
            app.handle("result", (1, "已取消的语音"))
            paste.assert_not_called()
            app.result.insert.assert_not_called()
        self.assertFalse(app.busy)


class PackagingTests(unittest.TestCase):
    def test_release_excludes_private_windows_data(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_release", ROOT / "linux/build_release.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as temp:
            archive = build.build(Path(temp) / "release.tar.gz")
            with tarfile.open(archive) as bundle:
                names = bundle.getnames()
            self.assertIn("ShengKongTai-Linux/install-linux.sh", names)
            self.assertTrue(all("override" not in name and "/models/" not in name and "/LLM/" not in name for name in names))
            self.assertTrue(all(name.startswith("ShengKongTai-Linux/") for name in names))


if __name__ == "__main__":
    unittest.main()
