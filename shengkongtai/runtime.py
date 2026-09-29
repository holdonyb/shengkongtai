"""安装与现有 ctypes 绑定配套的 llama.cpp b7798 Linux 库。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shutil
import tarfile
import tempfile
import urllib.request

from .config import data_dir
from .model import sha256

RUNTIME_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b7798/llama-b7798-bin-ubuntu-x64.tar.gz"
RUNTIME_SHA256 = "13e0fbbb2e1a3379ec5ed84ee9fe230f7d0c1dedbfc1b769424f0adc37f616b8"


def library_dir() -> Path:
    return data_dir() / "runtime" / "llama-b7798-cpu"


def verified_runtime(directory: Path | None = None) -> bool:
    directory = directory or library_dir()
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        files = manifest["files"]
        return (manifest["archive_sha256"] == RUNTIME_SHA256
                and {"libllama.so", "libggml.so", "libggml-base.so"} <= set(files)
                and all(Path(name).name == name and (directory / name).is_file()
                        and sha256(directory / name) == digest for name, digest in files.items()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def install_runtime(archive: Path | None = None) -> None:
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("当前 Qwen3 安装包支持 x86_64 Linux；ARM 需要另行构建匹配的 llama.cpp")
    destination = library_dir()
    if verified_runtime(destination):
        return
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".install-", dir=destination) as temp:
        staging = Path(temp)
        if archive is None:
            archive = staging / "llama.tar.gz"
            print("下载 llama.cpp b7798 Linux CPU 运行库（约 23 MiB）…", flush=True)
            with urllib.request.urlopen(RUNTIME_URL, timeout=60) as response, archive.open("wb") as out:
                shutil.copyfileobj(response, out)
        if sha256(archive) != RUNTIME_SHA256:
            raise ValueError("llama.cpp 运行库 SHA256 校验失败")
        with tarfile.open(archive, "r:gz") as bundle:
            members = {member.name: member for member in bundle}
            for member in members.values():
                name = Path(member.name).name
                if name != "LICENSE" and not re.fullmatch(r"lib(?:llama|ggml[-\w]*)\.so(?:\.[0-9]+)*", name):
                    continue
                actual = member
                seen = set()
                while actual.issym():
                    if actual.name in seen:
                        raise ValueError("运行库链接循环")
                    seen.add(actual.name)
                    if Path(actual.linkname).name != actual.linkname:
                        raise ValueError("运行库链接超出同目录")
                    actual = members[(Path(actual.name).parent / actual.linkname).as_posix()]
                if not actual.isfile():
                    raise ValueError("运行库不是普通文件")
                with bundle.extractfile(actual) as src, (staging / name).open("wb") as out:
                    shutil.copyfileobj(src, out)
        libs = {path.name: sha256(path) for path in staging.iterdir()
                if path.name.startswith("lib") or path.name == "LICENSE"}
        if not {"libllama.so", "libggml.so", "libggml-base.so"} <= set(libs):
            raise ValueError("运行库缺少所需动态库")
        for name in libs:
            os.replace(staging / name, destination / name)
        manifest = {"archive_sha256": RUNTIME_SHA256, "files": libs}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2))
        os.replace(staging / "manifest.json", destination / "manifest.json")
    print("llama.cpp Linux 运行库校验通过。", flush=True)
