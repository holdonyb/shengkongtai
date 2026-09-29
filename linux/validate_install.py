"""使用独立临时 HOME 验证真实安装、升级、失败回滚与卸载。"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model-archive", type=Path)
    parser.add_argument("--desktop-smoke", action="store_true")
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--wav", type=Path, help="在安装后的独立目录实际验证两种模型转写")
    args = parser.parse_args()
    if args.wav and not args.wav.is_file():
        parser.error(f"音频夹具不存在：{args.wav}")
    # Runtime sockets need a native Linux filesystem even when TMPDIR is on a
    # Windows-mounted disk for the larger model/venv installation fixtures.
    with tempfile.TemporaryDirectory(prefix="shengkongtai install ") as temp, \
            tempfile.TemporaryDirectory(prefix="skt-runtime-", dir="/tmp") as runtime:
        root = Path(temp)
        environment = dict(os.environ, HOME=str(root), XDG_DATA_HOME=str(root / "data"),
                           XDG_CONFIG_HOME=str(root / "config"), XDG_RUNTIME_DIR=runtime)
        # 复用测试期间已下载的 wheels；不改用户默认缓存。
        environment.setdefault("PIP_CACHE_DIR", str(Path.home() / ".cache/shengkongtai-linux-validation/.cache/pip"))
        with tarfile.open(args.release) as archive:
            archive.extractall(root, filter="data")
        source = root / "ShengKongTai-Linux"
        install = ["bash", str(source / "install-linux.sh"), "--skip-system-deps"]
        if args.runtime_archive:
            install += ["--runtime-archive", str(args.runtime_archive)]
        if args.model_dir:
            install += ["--model-dir", str(args.model_dir)]
        if args.model_archive:
            install += ["--model-archive", str(args.model_archive)]
        subprocess.run(install + ["--autostart"], env=environment, check=True)
        launcher = root / ".local/bin/shengkongtai"
        subprocess.run([str(launcher), "--version"], env=environment, check=True)
        subprocess.run([str(launcher), "model"], env=environment, check=True)
        def transcribe():
            if args.wav:
                result = subprocess.run([str(launcher), "transcribe", str(args.wav.resolve())],
                                        env=environment, capture_output=True, text=True, check=True, timeout=180)
                assert any(s in result.stdout for s in ("9", "九")) and any(s in result.stdout for s in ("5", "五")), result.stdout
                print("PASS: 安装目录中真实模型转写: " + result.stdout.strip(), flush=True)
        transcribe()
        if args.desktop_smoke:
            if not args.wav:
                parser.error("--desktop-smoke 需要 --wav")
            manifest = json.loads((root / "data/shengkongtai/install.json").read_text())
            python = root / "data/shengkongtai/releases" / manifest["release"] / ".venv/bin/python"
            subprocess.run(["xvfb-run", "-a", str(python), str(Path(__file__).with_name("smoke_test.py")),
                            "--model", "fun_asr_nano", "--wav", str(args.wav.resolve())],
                           env=environment, check=True, timeout=240)
        if (source / "models/Fun-ASR-Nano").is_dir() and (source / "models/Qwen3-ASR-1.7B").is_dir():
            subprocess.run([str(launcher), "model", "fun_asr_nano"], env=environment, check=True)
            transcribe()
            subprocess.run([str(launcher), "model", "qwen_asr"], env=environment, check=True)
        subprocess.run(["desktop-file-validate", str(root / "data/applications/shengkongtai.desktop")], check=True)
        config_file = root / "config/shengkongtai/config.json"
        config = json.loads(config_file.read_text())
        config["hotkey"] = "f9"
        config_file.write_text(json.dumps(config))
        before = launcher.read_text()
        # 已有校验通过的模型不会重复下载；升级保留用户配置。
        subprocess.run(install, env=environment, check=True)
        assert json.loads(config_file.read_text())["hotkey"] == "f9"
        assert launcher.read_text() != before
        assert (root / "config/autostart/shengkongtai.desktop").exists()
        print("PASS: 发行包安装、空格路径、桌面文件、自启动、升级保留配置", flush=True)
        current = launcher.read_text()
        # 故意破坏新包 requirements，只影响新版本的 staging。
        (source / "requirements-linux.txt").write_text("shengkongtai-deliberately-nonexistent-package==0\n")
        fail_env = dict(environment, PIP_NO_INDEX="1")
        failed = subprocess.run(install + ["--skip-model"], env=fail_env, capture_output=True, text=True)
        assert failed.returncode != 0
        assert launcher.read_text() == current
        subprocess.run([str(launcher), "--version"], env=environment, check=True)
        print("PASS: 升级依赖失败保留旧启动入口", flush=True)
        subprocess.run(install + ["--uninstall"], env=environment, check=True)
        assert not launcher.exists()
        assert not (root / "data/applications/shengkongtai.desktop").exists()
        assert not (root / "config/autostart/shengkongtai.desktop").exists()
        assert not (root / "data/shengkongtai/releases").exists()
        assert config_file.exists()
        if (source / "models/Fun-ASR-Nano").is_dir():
            assert (root / "data/shengkongtai/models/fun-asr-nano/Fun-ASR-Nano-Decoder.q5_k.gguf").exists()
        if (source / "models/Qwen3-ASR-1.7B").is_dir():
            assert (root / "data/shengkongtai/models/qwen3-asr-1.7b/qwen3_asr_llm.q4_k.gguf").exists()
        print("PASS: 卸载保留模型和用户配置", flush=True)


if __name__ == "__main__":
    main()
