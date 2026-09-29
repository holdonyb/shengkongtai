"""事务式用户安装：先完成依赖和模型，再切换稳定 launcher。"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
import venv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shengkongtai.config import config_dir, data_dir, initialize_config, load_config, model_dir, xdg_path, save_model_selection
from shengkongtai.catalog import MODELS
from shengkongtai.model import install_model
from shengkongtai.runtime import install_runtime
from shengkongtai.package_files import SHARED_FILES


def atomic_write(path: Path, text: str, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
        out.write(text)
        temp = Path(out.name)
    temp.chmod(mode)
    os.replace(temp, path)


def desktop_quote(value: Path) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return '"' + text.replace("%", "%%") + '"'


def main():
    parser = argparse.ArgumentParser(description="安装 声控台 Linux 到当前用户目录")
    parser.add_argument("--skip-system-deps", action="store_true", help="跳过系统包安装（已由管理员安装时使用）")
    parser.add_argument("--model", choices=tuple(MODELS), help="选择识别模型；默认保留配置，新安装为 Fun-ASR-Nano")
    parser.add_argument("--model-dir", type=Path, help="导入所选模型的现有目录")
    parser.add_argument("--model-archive", type=Path, help="导入所选模型的 ZIP，按文件 SHA256 校验")
    parser.add_argument("--runtime-archive", type=Path, help="导入 llama-b7798-bin-ubuntu-x64.tar.gz")
    parser.add_argument("--skip-model", action="store_true", help="稍后用 shengkongtai download-model 安装模型")
    parser.add_argument("--autostart", action="store_true", help="用户登录桌面后启动")
    parser.add_argument("--uninstall", action="store_true", help="卸载程序和桌面入口，保留配置及模型")
    args = parser.parse_args()
    if not sys.platform.startswith("linux") or os.geteuid() == 0:
        parser.error("请以普通 Linux 桌面用户运行，勿使用 sudo")
    base = data_dir()
    launcher = Path.home() / ".local/bin/shengkongtai"
    desktop = xdg_path("XDG_DATA_HOME", ".local/share") / "applications/shengkongtai.desktop"
    autostart = xdg_path("XDG_CONFIG_HOME", ".config") / "autostart/shengkongtai.desktop"
    manifest = base / "install.json"
    if args.uninstall:
        from shengkongtai.desktop import send_control
        try:
            send_control("quit")
        except RuntimeError:
            pass
        # 只操作自己的固定子目录，不从 manifest 读取任意删除路径。
        for path in (launcher, desktop, autostart, manifest):
            path.unlink(missing_ok=True)
        releases = base / "releases"
        if releases.is_symlink():
            releases.unlink()
        elif releases.exists():
            shutil.rmtree(releases)
        print(f"已卸载，配置和模型仍保留在 {base} 及 XDG 配置目录。")
        return
    if sys.version_info < (3, 10):
        parser.error("需要 Python 3.10 或更新版本，已验证 Python 3.12")
    try:
        import tkinter  # noqa: F401
        import ctypes.util
        if not ctypes.util.find_library("portaudio"):
            raise ImportError("PortAudio")
    except ImportError as exc:
        parser.error(f"缺少系统依赖 {exc}，请去掉 --skip-system-deps 重试")
    new_config = not (config_dir() / "config.json").exists()
    initialize_config()
    config = load_config()
    bundled_models = [key for key, item in MODELS.items() if (ROOT / item["source"]).is_dir()]
    if new_config and args.model is None and len(bundled_models) == 1:
        args.model = bundled_models[0]
    if args.model:
        config.update(model_type=args.model, model_dir="")
    runtime_archive = args.runtime_archive
    bundled_runtime = ROOT / "runtime/llama-b7798-bin-ubuntu-x64.tar.gz"
    if runtime_archive is None and bundled_runtime.is_file():
        runtime_archive = bundled_runtime
    install_runtime(runtime_archive)
    if not args.skip_model:
        source = args.model_dir
        bundled = ROOT / MODELS[config["model_type"]]["source"]
        if source is None and args.model_archive is None and bundled.is_dir():
            source = bundled
        install_model(model_dir(config), source, args.model_archive, config["model_type"])
        # 含模型包安装其余可选模型，之后切换无需再次下载或运行安装器。
        for key, item in MODELS.items():
            bundled = ROOT / item["source"]
            if key != config["model_type"] and bundled.is_dir():
                install_model(data_dir() / "models" / item["directory"], bundled, model_type=key)
    release = base / "releases" / uuid.uuid4().hex[:12]
    release.mkdir(parents=True)
    try:
        shutil.copytree(ROOT / "shengkongtai", release / "shengkongtai",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "requirements-linux.txt", release / "requirements-linux.txt")
        if (ROOT / "linux/licenses").is_dir():
            shutil.copytree(ROOT / "linux/licenses", release / "licenses")
        shutil.copy2(ROOT / "LICENSE", release / "licenses/ShengKongTai-MIT.txt")
        for name in SHARED_FILES:
            destination = release / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        venv.EnvBuilder(with_pip=True).create(release / ".venv")
        python = release / ".venv/bin/python"
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "-r",
                        str(release / "requirements-linux.txt")], check=True)
        subprocess.run([str(python), "-c", "import tkinter, sounddevice, onnxruntime, gguf, scipy, numpy"], check=True)
        from shengkongtai.runtime import library_dir
        probe_env = dict(os.environ, CAPSWRITER_LLAMA_LIB_DIR=str(library_dir()))
        subprocess.run([str(python), "-c", "from util.llama.llama import init_llama_lib; init_llama_lib()"],
                       cwd=release, env=probe_env, check=True)
        subprocess.run([str(python), "-m", "shengkongtai", "--version"], cwd=release, check=True)
    except BaseException:
        shutil.rmtree(release)
        raise
    command = f"#!/bin/sh\ncd -- {shlex.quote(str(release))} || exit 1\nexec {shlex.quote(str(python))} -m shengkongtai \"$@\"\n"
    atomic_write(launcher, command, 0o755)
    entry = ("[Desktop Entry]\nType=Application\nName=ShengKongTai\nName[zh_CN]=声控台\n"
             "Comment=Offline voice typing\nComment[zh_CN]=离线语音输入\n"
             f"Exec={desktop_quote(launcher)}\nIcon=audio-input-microphone\nTerminal=false\n"
             "Categories=Utility;Accessibility;\nActions=Toggle;Quit;\n\n"
             f"[Desktop Action Toggle]\nName=开始/结束录音\nExec={desktop_quote(launcher)} toggle\n\n"
             f"[Desktop Action Quit]\nName=退出\nExec={desktop_quote(launcher)} quit\n")
    atomic_write(desktop, entry)
    if args.autostart or autostart.exists():
        atomic_write(autostart, entry)
    atomic_write(manifest, json.dumps({"version": 1, "release": release.name}, indent=2) + "\n")
    if args.model:
        save_model_selection(args.model)
    # 保留先前版本目录，避免升级破坏正在运行的进程；卸载时统一清理。
    print(f"\n安装完成。请从应用菜单打开 声控台，或运行 {launcher}")
    print(f"环境检查：{launcher} doctor")
    if args.skip_model:
        print(f"启动前请先运行：{launcher} download-model")
    if str(launcher.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print('命令行使用短名称前，请运行：export PATH="$HOME/.local/bin:$PATH"（或重新登录）')


if __name__ == "__main__":
    main()
